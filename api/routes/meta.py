"""Health, settings and dashboard statistics."""

from fastapi import APIRouter, Depends, HTTPException

import db
from ..config import VALID_SERVICES
from ..deps import db_session, get_config
from ..schemas import SettingsIn

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health(cfg=Depends(get_config)):
    """Startup validation surface: reports DB path, existence and mode."""
    unit = None
    if cfg.exists:
        with db_session(cfg) as conn:
            unit = db.get_setting(conn, "unit_name")
    return {
        "status": "ok" if cfg.exists else "db_missing",
        "mode": cfg.mode,
        "db_path": cfg.db_path,
        "db_exists": cfg.exists,
        "unit_name": unit,
        "services": sorted(VALID_SERVICES),
    }


@router.get("/settings")
def get_settings(cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        keys = ("unit_name", "toilet_daily_count", "guard_daily_count", "week_start")
        return {k: db.get_setting(conn, k) for k in keys}


@router.put("/settings")
def put_settings(body: SettingsIn, cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        data = body.model_dump(exclude_none=True)
        for k, v in data.items():
            db.set_setting(conn, k, str(v))
        return {"updated": sorted(data)}


@router.get("/dashboard")
def dashboard(cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        counts = {
            "students": conn.execute("SELECT COUNT(*) c FROM students").fetchone()["c"],
            "squads": conn.execute("SELECT COUNT(*) c FROM squads").fetchone()["c"],
            "weeks": conn.execute("SELECT COUNT(*) c FROM weeks").fetchone()["c"],
        }
        week = db.get_week(
            conn,
            conn.execute("SELECT id FROM weeks ORDER BY start_date DESC LIMIT 1").fetchone()["id"],
        ) if counts["weeks"] else None
        latest = None
        if week:
            rows = db.get_assignments(conn, week["id"])
            latest = {
                "week": week,
                "assignments": rows,
                "optional_count": len(db.list_optional(conn, week["id"])),
            }
        students_per_squad = [
            dict(r) for r in conn.execute(
                """SELECT sq.id, sq.name AS squad_name, g.code AS group_code,
                          COUNT(st.id) AS students
                   FROM squads sq JOIN groups g ON g.id=sq.group_id
                   LEFT JOIN students st ON st.squad_id=sq.id
                   GROUP BY sq.id, sq.name, g.code ORDER BY g.code, sq.number"""
            ).fetchall()
        ]
        return {"counts": counts, "latest_week": latest, "students_per_squad": students_per_squad}
