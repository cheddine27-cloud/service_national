"""Students CRUD, search and filtering (legacy fields preserved)."""

from fastapi import APIRouter, Depends, HTTPException

import db
from ..deps import db_session, get_config
from ..schemas import StudentIn, StudentPatch

router = APIRouter(prefix="/api", tags=["students"])


def _check_squad(conn, squad_id):
    if squad_id is not None and not conn.execute(
        "SELECT 1 FROM squads WHERE id=?", (squad_id,)
    ).fetchone():
        raise HTTPException(400, f"Squad {squad_id} does not exist")


@router.get("/students")
def list_students(squad_id: int | None = None, search: str | None = None,
                  cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        return db.list_students(conn, squad_id, search)


@router.post("/students", status_code=201)
def create_student(body: StudentIn, cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        _check_squad(conn, body.squad_id)
        try:
            db.create_student(conn, **body.model_dump())
        except db.sqlite3.Error as e:
            raise HTTPException(500, f"Database error: {e}")
        return {"created": True, "student": db.list_students(conn)[-1]}


@router.patch("/students/{student_id}")
def patch_student(student_id: int, body: StudentPatch, cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        if not conn.execute("SELECT 1 FROM students WHERE id=?", (student_id,)).fetchone():
            raise HTTPException(404, f"Student {student_id} not found")
        data = body.model_dump(exclude_none=True)
        _check_squad(conn, data.get("squad_id", None)) if "squad_id" in data else None
        try:
            db.update_student(conn, student_id, **data)
        except db.sqlite3.Error as e:
            raise HTTPException(500, f"Database error: {e}")
        rows = [s for s in db.list_students(conn) if s["id"] == student_id]
        return rows[0] if rows else None


@router.delete("/students/{student_id}")
def delete_student(student_id: int, cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        if not conn.execute("SELECT 1 FROM students WHERE id=?", (student_id,)).fetchone():
            raise HTTPException(404, f"Student {student_id} not found")
        db.delete_student(conn, student_id)
        return {"deleted": student_id}
