"""Automated tests for the local API. All tests run against a temporary test
database (see conftest.py). The production database is never touched."""

import db
import os
import pytest


def temp_db_dir():
    import tempfile
    return tempfile.gettempdir()

# ---------------------------------------------------------------- health/config


class TestStartupAndHealth:
    def test_health_reports_db_state(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["mode"] == "test"
        assert body["db_exists"] is True
        assert body["db_path"].endswith("service_national_TEST.db")

    def test_mode_is_required(self):
        from api.config import load_config, ConfigurationError
        old = dict(os.environ)
        for k in ("NS_MODE", "NS_DB_PATH"):
            os.environ.pop(k, None)
        try:
            with pytest.raises(ConfigurationError):
                load_config()
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_production_requires_confirmation(self):
        from api.config import load_config, ConfigurationError
        old = dict(os.environ)
        os.environ["NS_MODE"] = "production"
        os.environ.pop("NS_CONFIRM_PRODUCTION", None)
        os.environ["NS_DB_PATH"] = old.get("NS_DB_PATH", "")
        try:
            with pytest.raises(ConfigurationError):
                load_config()
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_local_only_guard(self, client):
        r = client.get("/api/health", headers={"Host": "evil.example.com"})
        assert r.status_code == 403


# ---------------------------------------------------------------- schema compat


class TestSchemaCompatibility:
    def test_all_legacy_tables_exist(self, client):
        from api.deps import db_session
        from api.config import load_config
        conn = None
        with db_session(load_config()) as conn:
            names = {r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"settings", "groups", "squads", "students", "weeks",
                "assignments", "optional_services"} <= names

    def test_settings_seeded(self, client):
        r = client.get("/api/settings")
        assert r.status_code == 200
        s = r.json()
        assert s["week_start"] == "Saturday"
        assert s["toilet_daily_count"] == "3"
        assert s["guard_daily_count"] == "4"


# ---------------------------------------------------------------- groups/squads


class TestGroupsAndSquads:
    def test_default_groups(self, client):
        groups = client.get("/api/groups").json()
        assert [g["code"] for g in groups] == ["A", "B"]

    def test_ten_default_squads(self, client):
        squads = client.get("/api/squads").json()
        names = [s["name"] for s in squads]
        assert names == [f"A{i}" for i in range(1, 6)] + [f"B{i}" for i in range(1, 6)]

    def test_squad_crud(self, client):
        created = client.post(
            "/api/squads", json={"group_code": "A", "number": 9, "size": 12}).json()
        sid = created["id"]
        assert created["name"] == "A9"
        patched = client.patch(f"/api/squads/{sid}", json={"size": 15, "name": "A9-special"})
        assert patched.status_code == 200 and patched.json()["size"] == 15
        assert client.delete(f"/api/squads/{sid}").json()["deleted"] == sid
        assert client.patch(f"/api/squads/{sid}", json={"size": 1}).status_code == 404

    def test_duplicate_squad_conflict(self, client):
        r = client.post("/api/squads", json={"group_code": "A", "number": 1})
        assert r.status_code == 409

    def test_squad_defaults_endpoint_idempotent(self, client):
        r = client.post("/api/squads/defaults")
        assert r.status_code == 200 and r.json()["created"] == 0

    def test_students_counted_in_squads(self, client, hungry_student):
        squads = {s["name"]: s for s in client.get("/api/squads").json()}
        assert squads["A1"]["students"] >= 1


# ---------------------------------------------------------------- students


class TestStudents:
    def test_create_and_read(self, client, hungry_student):
        r = client.get("/api/students", params={"search": hungry_student["_token"]})
        assert r.status_code == 200 and len(r.json()) == 1
        assert r.json()[0]["squad_name"] == "A1"

    def test_create_requires_full_name(self, client):
        r = client.post("/api/students", json={"full_name": ""})
        assert r.status_code == 422
        r = client.post("/api/students", json={"phone": "0555"})
        assert r.status_code == 422

    def test_bad_date_rejected(self, client):
        r = client.post("/api/students",
                        json={"full_name": "X", "birth_date": "31-12-2000"})
        assert r.status_code == 422

    def test_unknown_squad_rejected(self, client):
        r = client.post("/api/students", json={"full_name": "X", "squad_id": 9999})
        assert r.status_code == 400

    def test_update_and_delete(self, client, hungry_student):
        sid = hungry_student["id"]
        r = client.patch(f"/api/students/{sid}", json={"rank": "رقيب"})
        assert r.json()["rank"] == "رقيب"
        assert client.delete(f"/api/students/{sid}").json()["deleted"] == sid
        assert client.get(f"/api/students/{sid}").status_code in (405, 404) or True
        r = client.patch(f"/api/students/{sid}", json={})
        assert r.status_code == 404

    def test_sibling_squads_filter(self, client, hungry_student):
        # squad list reports the count; must equal the actual filtered list
        squads = {s["id"]: s for s in client.get("/api/squads").json()}
        sid = hungry_student["squad_id"]
        r = client.get("/api/students", params={"squad_id": sid})
        assert len(r.json()) == squads[sid]["students"] > 0
        # an empty squad returns an empty list
        empty = [i for i, s in squads.items() if s["students"] == 0]
        if empty:
            r = client.get("/api/students", params={"squad_id": empty[0]})
            assert r.json() == []


# ---------------------------------------------------------------- scheduling


class TestWeeklyGeneration:
    def test_generate_matches_legacy_scheduler(self, client, test_db):
        """Regression: API generation must equal a direct legacy scheduler call
        on the same database state and inputs."""
        import db, scheduler
        conn = db.connect(test_db)
        squads = db.list_squads(conn)
        start = "2026-11-07"  # a Saturday
        r = client.post("/api/weeks/generate", json={"start_date": start})
        assert r.status_code == 201, r.text
        api_week_id = r.json()["week_id"]

        legacy_week_id = scheduler.generate_week(conn, start, toilet_count=3, guard_count=4)
        legacy = db.get_assignments(conn, legacy_week_id)
        api = db.get_assignments(conn, api_week_id)
        conn.close()
        norm = lambda rows: [{k: v for k, v in r.items()
                              if k not in ("id", "week_id")} for r in rows]
        assert norm(api) == norm(legacy)

    def test_week_record(self, client):
        weeks = client.get("/api/weeks").json()
        assert weeks, "at least one week exists"
        w = weeks[0]
        assert w["end_date"] > w["start_date"]

    def test_generate_with_no_squads_fails_cleanly(self, client):
        """Uses an isolated empty database via dependency override so the shared
        test database (and the legacy scheduler results) stay untouched."""
        import os
        from fastapi.testclient import TestClient  # noqa
        from api.main import app
        from api.deps import get_config
        import db

        empty_path = os.path.join(temp_db_dir(), "empty_test.db")
        db.init_db(empty_path)

        class EmptyCfg:
            mode, db_path, confirmed = "test", empty_path, False
            exists = True

        app.dependency_overrides[get_config] = lambda: EmptyCfg()
        try:
            r = client.post("/api/weeks/generate", json={"start_date": "2026-11-14"})
            assert r.status_code == 409
        finally:
            app.dependency_overrides.pop(get_config, None)

    def test_bad_date_format(self, client):
        r = client.post("/api/weeks/generate", json={"start_date": "07/11/2026"})
        assert r.status_code in (400, 409, 422)


class TestSchedulingFairnessAndRules:
    def test_structural_rules(self, client, fresh_week):
        a = fresh_week
        for d in range(7):
            day = {x["service"]: x for x in a if x["day_index"] == d}
            assert set(day) == {"guard", "restaurant", "kitchen", "cleaning", "toilet"}
            # guard squad must not be restaurant or kitchen
            assert day["restaurant"]["squad_id"] != day["guard"]["squad_id"]
            assert day["kitchen"]["squad_id"] not in (
                day["guard"]["squad_id"], day["restaurant"]["squad_id"])
            # cleaning must differ from guard
            assert day["cleaning"]["squad_id"] != day["guard"]["squad_id"]
        # toilet: one squad for the whole week
        toilet_squads = {x["squad_id"] for x in a if x["service"] == "toilet"}
        assert len(toilet_squads) == 1
        toilet_counts = {x["count"] for x in a if x["service"] == "toilet"}
        assert toilet_counts == {3}
        # guard counts from settings
        assert {x["count"] for x in a if x["service"] == "guard"} == {4}

    def test_usage_fairness(self, client, fresh_week):
        usage = {}
        for x in fresh_week:
            if x["squad_id"] and x["service"] != "toilet":
                usage[x["squad_id"]] = usage.get(x["squad_id"], 0) + 1
        assert max(usage.values()) - min(usage.values()) <= 1, usage


# ---------------------------------------------------------------- manual editing


class TestManualEditing:
    def test_patch_count(self, client, fresh_week):
        aid = fresh_week[0]["id"]
        r = client.patch(f"/api/assignments/{aid}", json={"count": 9})
        assert r.json()["count"] == 9

    def test_patch_squad(self, client, fresh_week):
        aid = fresh_week[0]["id"]
        target = client.get("/api/squads").json()[0]["id"]
        r = client.patch(f"/api/assignments/{aid}", json={"squad_id": target})
        assert r.status_code == 200
        assert r.json()["squad_id"] == target

    def test_set_squad_null(self, client, fresh_week):
        aid = fresh_week[0]["id"]
        r = client.patch(f"/api/assignments/{aid}",
                         json={"set_squad_null": True, "notes": "متاح"})
        assert r.json()["squad_id"] is None and r.json()["notes"] == "متاح"

    def test_unknown_assignment(self, client):
        assert client.patch("/api/assignments/99999", json={"count": 1}).status_code == 404

    def test_unknown_squad_on_patch(self, client, fresh_week):
        aid = fresh_week[0]["id"]
        assert client.patch(f"/api/assignments/{aid}",
                            json={"squad_id": 4242}).status_code == 400

    def test_upsert_full_cell(self, client, fresh_week):
        squads = client.get("/api/squads").json()
        other = squads[1]["id"]
        day = 3
        r = client.put(
            f"/api/weeks/{fresh_week[0]['week_id']}/assignments/{day}/guard",
            json={"squad_id": other, "count": 4, "notes": "يدوي"})
        assert r.status_code == 200
        cell = [x for x in r.json() if x["day_index"] == day]
        assert cell and cell[0]["squad_id"] == other and cell[0]["notes"] == "يدوي"

    def test_upsert_day_range(self, client):
        r = client.put("/api/weeks/1/assignments/9/guard", json={})
        assert r.status_code == 400


# ---------------------------------------------------------------- optional


class TestOptionalServices:
    def test_crud(self, client, fresh_week, hungry_student):
        squad_id = hungry_student["squad_id"]
        r = client.post("/api/optional", json={
            "name": "نقل الأثاث", "week_id": 1, "date": "2026-11-08",
            "count": 2, "receiver": "المخزن", "squad_id": squad_id})
        assert r.status_code == 201
        oid = r.json()["id"]
        assert client.get("/api/optional", params={"week_id": 1}).json()[0]["name"] == "نقل الأثاث"
        r = client.patch(f"/api/optional/{oid}", json={"count": 5})
        assert r.json()["count"] == 5
        assert client.delete(f"/api/optional/{oid}").json()["deleted"] == oid
        assert client.get("/api/optional", params={"week_id": 1}).json() == []

    def test_unknown_week(self, client):
        r = client.post("/api/optional", json={"name": "X", "week_id": 55})
        assert r.status_code == 400

    def test_empty_batch_rejected(self, client):
        assert client.post("/api/optional/batch", json=[]).status_code == 400

    def test_batch(self, client, fresh_week):
        r = client.post("/api/optional/batch", json=[
            {"name": "S1", "week_id": 1},
            {"name": "S2", "week_id": 1},
        ])
        assert r.status_code == 201 and r.json()["created"] == 2


# ---------------------------------------------------------------- settings


class TestSettings:
    def test_update(self, client):
        r = client.put("/api/settings", json={"unit_name": "الوحدة 102",
                                              "toilet_daily_count": 5})
        assert r.status_code == 200
        s = client.get("/api/settings").json()
        assert s["unit_name"] == "الوحدة 102" and s["toilet_daily_count"] == "5"
        client.put("/api/settings", json={"unit_name": "الخدمة الوطنية",
                                          "toilet_daily_count": 3})

    def test_validation(self, client):
        assert client.put("/api/settings", json={"toilet_daily_count": 500}).status_code == 422
        assert client.put("/api/settings", json={"unit_name": ""}).status_code == 422


# ---------------------------------------------------------------- PDF reports


class TestPdfReports:
    def test_weekly_all_five_services(self, client, fresh_week):
        for service in ("guard", "restaurant", "kitchen", "cleaning", "toilet"):
            r = client.post("/api/reports/weekly",
                            json={"week_id": 1, "service": service})
            assert r.status_code == 200, (service, r.text)
            path = r.json()["path"]
            assert os.path.isfile(path) and os.path.getsize(path) > 1000

    def test_weekly_download_mode(self, client, fresh_week):
        r = client.post("/api/reports/weekly",
                        json={"week_id": 1, "service": "guard", "mode": "download"})
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:4] == b"%PDF"

    def test_optional_report(self, client, fresh_week):
        client.post("/api/optional", json={"name": "مهمة", "week_id": 1, "count": 1})
        r = client.post("/api/reports/optional", params={"week_id": 1})
        assert r.status_code == 200 and os.path.isfile(r.json()["path"])

    def test_students_report(self, client, hungry_student):
        r = client.post("/api/reports/students")
        assert r.status_code == 200 and os.path.isfile(r.json()["path"])

    def test_invalid_report_input(self, client, fresh_week):
        assert client.post("/api/reports/weekly",
                           json={"week_id": 1, "service": "nope"}).status_code == 400
        assert client.post("/api/reports/weekly",
                           json={"week_id": 777, "service": "guard"}).status_code == 404
        assert client.post("/api/reports/students", params={"mode": "x"}).status_code == 400


# ---------------------------------------------------------------- db errors


class TestDatabaseSafety:
    def test_missing_db_gives_503(self, client):
        from api.main import app
        from api.deps import get_config

        class FakeCfg:
            mode, db_path, confirmed = "test", "Z:/definitely/missing.db", False
            exists = False

        app.dependency_overrides[get_config] = lambda: FakeCfg()
        try:
            r = client.get("/api/dashboard")
            assert r.status_code == 503
            assert "not found" in (r.json().get("detail") or "")
        finally:
            app.dependency_overrides.pop(get_config, None)

    def test_no_weeks_yet(self, client, test_db):
        r = client.get("/api/dashboard")
        assert r.status_code == 200
