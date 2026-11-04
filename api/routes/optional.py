"""Optional services CRUD."""

from fastapi import APIRouter, Depends, HTTPException

import db
from ..deps import db_session, get_config
from ..schemas import OptionalServiceIn, OptionalServicePatch

router = APIRouter(prefix="/api", tags=["optional"])


def _check_optional_refs(conn, body):
    if body.week_id is not None and not conn.execute(
        "SELECT 1 FROM weeks WHERE id=?", (body.week_id,)
    ).fetchone():
        raise HTTPException(400, f"Week {body.week_id} does not exist")
    if body.squad_id is not None and not conn.execute(
        "SELECT 1 FROM squads WHERE id=?", (body.squad_id,)
    ).fetchone():
        raise HTTPException(400, f"Squad {body.squad_id} does not exist")


@router.get("/optional")
def list_optional(week_id: int | None = None, cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        if week_id is not None and not conn.execute(
            "SELECT 1 FROM weeks WHERE id=?", (week_id,)
        ).fetchone():
            raise HTTPException(404, f"Week {week_id} not found")
        return db.list_optional(conn, week_id)


@router.post("/optional", status_code=201)
def create_optional(body: OptionalServiceIn, cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        _check_optional_refs(conn, body)
        try:
            db.create_optional(conn, **body.model_dump())
        except db.sqlite3.Error as e:
            raise HTTPException(500, f"Database error: {e}")
        return db.list_optional(conn, body.week_id)[-1]


@router.patch("/optional/{oid}")
def patch_optional(oid: int, body: OptionalServicePatch, cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        if not conn.execute("SELECT 1 FROM optional_services WHERE id=?", (oid,)).fetchone():
            raise HTTPException(404, f"Optional service {oid} not found")
        data = body.model_dump(exclude_none=True)
        _check_optional_refs(conn, body) if ("week_id" in data or "squad_id" in data) else None
        try:
            db.update_optional(conn, oid, **data)
        except db.sqlite3.Error as e:
            raise HTTPException(500, f"Database error: {e}")
        rows = db.list_optional(conn)
        return next((r for r in rows if r["id"] == oid), None)


@router.delete("/optional/{oid}")
def delete_optional(oid: int, cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        if not conn.execute("SELECT 1 FROM optional_services WHERE id=?", (oid,)).fetchone():
            raise HTTPException(404, f"Optional service {oid} not found")
        db.delete_optional(conn, oid)
        return {"deleted": oid}


@router.post("/optional/batch", status_code=201)
def create_optional_batch(items: list[OptionalServiceIn], cfg=Depends(get_config)):
    """Convenience bulk endpoint (all-or-nothing), keeps same business rules."""
    with db_session(cfg) as conn:
        if not items:
            raise HTTPException(400, "Empty batch")
        for body in items:
            _check_optional_refs(conn, body)
            db.create_optional(conn, **body.model_dump())
        return {"created": len(items)}
