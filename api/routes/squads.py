"""Groups & squads CRUD + default squads creation (legacy behaviour preserved)."""

from fastapi import APIRouter, Depends, HTTPException

import db
from ..deps import db_session, get_config
from ..schemas import SquadIn, SquadPatch

router = APIRouter(prefix="/api", tags=["squads"])


@router.get("/groups")
def list_groups(cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        return db.list_groups(conn)


@router.get("/squads")
def list_squads(group_code: str | None = None, cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        if group_code and group_code not in ("A", "B"):
            raise HTTPException(400, "group_code must be A or B")
        rows = db.list_squads(conn, group_code)
        for r in rows:  # include student counts
            r["students"] = conn.execute(
                "SELECT COUNT(*) c FROM students WHERE squad_id=?", (r["id"],)
            ).fetchone()["c"]
        return rows


@router.post("/squads", status_code=201)
def create_squad(body: SquadIn, cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        try:
            name = body.name or f"{body.group_code}{body.number}"
            db.create_squad(conn, body.group_code, body.number, name, body.size)
        except db.sqlite3.IntegrityError:
            raise HTTPException(409, f"Squad {body.group_code}{body.number} already exists")
        except ValueError as e:
            raise HTTPException(400, str(e))
        squads = db.list_squads(conn, body.group_code)
        return squads[-1] if squads else None


@router.patch("/squads/{squad_id}")
def patch_squad(squad_id: int, body: SquadPatch, cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        if not conn.execute("SELECT 1 FROM squads WHERE id=?", (squad_id,)).fetchone():
            raise HTTPException(404, f"Squad {squad_id} not found")
        try:
            db.update_squad(conn, squad_id, **body.model_dump(exclude_none=True))
        except db.sqlite3.IntegrityError:
            raise HTTPException(409, "Squad number already used in this group")
        return db.list_squads(conn)[_index(conn, squad_id)]


@router.delete("/squads/{squad_id}")
def delete_squad(squad_id: int, cfg=Depends(get_config)):
    """Legacy behaviour: students of the squad are detached (SET NULL)."""
    with db_session(cfg) as conn:
        if not conn.execute("SELECT 1 FROM squads WHERE id=?", (squad_id,)).fetchone():
            raise HTTPException(404, f"Squad {squad_id} not found")
        db.delete_squad(conn, squad_id)
        return {"deleted": squad_id}


@router.post("/squads/defaults")
def ensure_defaults(cfg=Depends(get_config)):
    with db_session(cfg) as conn:
        before = len(db.list_squads(conn))
        db.ensure_default_squads(conn)
        return {"created": len(db.list_squads(conn)) - before}


def _index(conn, squad_id):
    for i, s in enumerate(db.list_squads(conn)):
        if s["id"] == squad_id:
            return i
    return 0
