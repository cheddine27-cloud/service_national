import os
import shutil
import sys
import uuid

import pytest

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture(scope="session")
def test_db(tmp_path_factory):
    """Temporary SQLite database - NEVER the user production database."""
    base = tmp_path_factory.mktemp("ns_test")
    db_path = base / "service_national_TEST.db"
    os.environ["NS_MODE"] = "test"
    os.environ["NS_DB_PATH"] = str(db_path)
    os.environ.pop("NS_CONFIRM_PRODUCTION", None)

    import db
    db.init_db(str(db_path))          # creates schema + seeds groups/settings
    conn = db.connect(str(db_path))
    db.ensure_default_squads(conn)    # A1..A5, B1..B5 (ids 1..10 deterministically)
    conn.close()
    yield str(db_path)
    shutil.rmtree(base, ignore_errors=True)


@pytest.fixture
def client(test_db):
    from fastapi.testclient import TestClient
    from api.main import app
    with TestClient(app, base_url="http://127.0.0.1") as c:
        yield c


@pytest.fixture
def hungry_student(client):
    """One test student in squad A1 with a globally unique name token (the
    suite must be order-independent)."""
    import uuid
    token = f"tok{uuid.uuid4().hex[:8]}"
    squad_id = next(s["id"] for s in client.get("/api/squads").json()
                    if s["name"] == "A1")
    r = client.post("/api/students", json={
        "full_name": f"محمد {token}", "squad_id": squad_id, "rank": "جندي",
        "blood_type": "O+", "phone": "0555000000"})
    assert r.status_code == 201, r.text
    student = r.json()["student"]
    student["_token"] = token
    return student


@pytest.fixture
def fresh_week(client):
    """Generate a week for SATURDAY 2026-11-07 with default counts and return
    its assignments."""
    r = client.post("/api/weeks/generate", json={"start_date": "2026-11-07"})
    assert r.status_code == 201, r.text
    week_id = r.json()["week_id"]
    return client.get(f"/api/weeks/{week_id}").json()["assignments"]
