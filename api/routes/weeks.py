"""Weeks, schedule generation (existing scheduler.py - unchanged) and manual
assignment editing."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

import db
import scheduler
from ..deps import db_session, get_config
from ..schemas import AssignmentPatchIn, AssignmentUpsertIn, GenerateWeekIn

router = APIRouter(prefix="/api", tags=["weeks"])


def _week_or_404(conn, week_id):
    week = db.get_week(conn, week_id)
    if not week:
        raise HTTPException(404, f"Week {week_id} not found")
    return week


def _counts_or_defaults(conn, body):
    toilet = body.toilet_count
    guard = body.guard_count
    if toilet is None:
        toilet = int(db.get_setting(conn, "toilet_daily_count", "3"))
    if guard is None:
        guard = int(db.get_setting(conn, "guard_daily_count", "4"))
    return toilet, guard


@router.get("/weeks")
def list_weeks(cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        return db.list_weeks(conn)


@router.post("/weeks/generate", status_code=201)
def generate_week(body: GenerateWeekIn, cfg=Depends(get_config)):
    """Uses scheduler.generate_week unchanged. The week start convention
    (Saturday) comes from settings; the legacy application did not enforce
    the weekday in code, so neither does the API (the UI will prefill
    Saturdays)."""
    with db_session(cfg) as conn:
        if not db.list_squads(conn):
            raise HTTPException(409, "No squads exist. Create squads first.")
        toilet_count, guard_count = _counts_or_defaults(conn, body)
        try:
            week_id = scheduler.generate_week(
                conn, body.start_date, toilet_count=toilet_count, guard_count=guard_count
            )
        except RuntimeError as e:
            raise HTTPException(409, str(e))
        except ValueError:
            raise HTTPException(400, "start_date must be YYYY-MM-DD")
        return {"week_id": week_id, "assignments": db.get_assignments(conn, week_id)}


@router.get("/weeks/{week_id}")
def get_week(week_id: int, cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        week = _week_or_404(conn, week_id)
        return {**week, "assignments": db.get_assignments(conn, week_id)}


@router.delete("/weeks/{week_id}")
def delete_week(week_id: int, cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        _week_or_404(conn, week_id)
        db.delete_week(conn, week_id)  # CASCADE deletes assignments
        return {"deleted": week_id}


@router.get("/weeks/{week_id}/assignments")
def get_assignments(week_id: int, service: str | None = None,
                    cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        _week_or_404(conn, week_id)
        if service and service not in ("guard", "restaurant", "kitchen", "cleaning", "toilet"):
            raise HTTPException(400, "Unknown service")
        return db.get_assignments(conn, week_id, service)


@router.put("/weeks/{week_id}/assignments/{day_index}/{service}")
def upsert_assignment(week_id: int, day_index: int, service: str,
                      body: AssignmentUpsertIn, cfg=Depends(get_config)):
    """Full cell upsert (legacy UNIQUE(week, day, service) semantics avaliable)."""
    if not 0 <= day_index <= 6:
        raise HTTPException(400, "day_index must be 0..6 (Saturday = 0)")
    if service not in ("guard", "restaurant", "kitchen", "cleaning", "toilet"):
        raise HTTPException(400, "Unknown service")
    with db_session(cfg) as conn:
        week = _week_or_404(conn, week_id)
        if body.squad_id is not None and not conn.execute(
            "SELECT 1 FROM squads WHERE id=?", (body.squad_id,)
        ).fetchone():
            raise HTTPException(400, f"Squad {body.squad_id} does not exist")
        from datetime import date as _d, timedelta
        date = (_d.fromisoformat(week["start_date"])
                + timedelta(days=day_index)).isoformat()
        try:
            db.upsert_assignment(conn, week_id, day_index, date, service,
                                 body.squad_id, body.count, body.notes)
        except db.sqlite3.Error as e:
            raise HTTPException(500, f"Database error: {e}")
        return db.get_assignments(conn, week_id, service)


@router.patch("/assignments/{assignment_id}")
def patch_assignment(assignment_id: int, body: AssignmentPatchIn,
                     cfg=Depends(get_config)):
    """Manual editing, exactly the legacy db.update_assignment behaviour:
    optional fields stay unchanged when omitted; with set_squad_null=True the
    squad can be explicitly cleared."""
    with db_session(cfg) as conn:
        if not conn.execute(
            "SELECT 1 FROM assignments WHERE id=?", (assignment_id,)
        ).fetchone():
            raise HTTPException(404, f"Assignment {assignment_id} not found")
        if body.squad_id is not None and not conn.execute(
            "SELECT 1 FROM squads WHERE id=?", (body.squad_id,)
        ).fetchone():
            raise HTTPException(400, f"Squad {body.squad_id} does not exist")
        if body.set_squad_null:
            conn.execute("UPDATE assignments SET squad_id=NULL WHERE id=?",
                         (assignment_id,))
            conn.commit()
        try:
            db.update_assignment(conn, assignment_id,
                                 squad_id=body.squad_id, count=body.count,
                                 notes=body.notes)
        except db.sqlite3.Error as e:
            raise HTTPException(500, f"Database error: {e}")
        row = conn.execute("SELECT * FROM assignments WHERE id=?",
                           (assignment_id,)).fetchone()
        return dict(row)
