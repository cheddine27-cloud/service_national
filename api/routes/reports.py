"""PDF report generation endpoints - reuses reports.py unchanged.

Modes:
  path      - generate and return the file path (default)
  open      - generate and open it locally (os.startfile) - local only
  print     - generate and send to Windows print queue via shell print verb
  download  - generate and stream the PDF to the caller

Writes always go to the standard local reports folder
(%APPDATA%/NationalService/reports), never into the database folder."""

import os
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

import db
import reports

from ..schemas import WeeklyReportIn
from ..deps import db_session, get_config

router = APIRouter(prefix="/api", tags=["reports"])

WEEKLY_SERVICES = ("guard", "restaurant", "kitchen", "cleaning", "toilet")


def _deliver(path: str, mode: str):
    if mode in ("open", "print"):
        # local machine operation only; the server is bound to 127.0.0.1
        os.startfile(path, "open" if mode == "open" else "print")
        return {"path": path, "mode": mode}
    if mode == "download":
        return FileResponse(
            path, media_type="application/pdf",
            filename=os.path.basename(path),
        )
    return {"path": path, "mode": mode}


@router.post("/reports/weekly")
def weekly_report(body: dict, cfg=Depends(get_config)):
    """body: {week_id: int, service: str, mode: \"path\"|\"open\"|\"print\"|\"download\"}"""
    mode = body.get("mode", "path")
    if mode not in ("path", "open", "print", "download"):
        raise HTTPException(400, "mode must be path|open|print|download")
    try:
        data = WeeklyReportIn(
            week_id=body.get("week_id", 0),
            service=body.get("service", ""),
            mode=mode,
        )
    except ValueError as e:
        raise HTTPException(400, f"Invalid report request: {e}")
    with db_session(cfg) as conn:
        if not db.get_week(conn, data.week_id):
            raise HTTPException(404, f"Week {data.week_id} not found")
        try:
            path = reports.generate_weekly_pdf(conn, data.week_id, data.service)
        except sqlite3.Error as e:
            raise HTTPException(500, f"Database error: {e}")
        except OSError as e:
            raise HTTPException(500, f"File system error: {e}")
    return _deliver(path, data.mode)


@router.post("/reports/optional")
def optional_report(week_id: int | None = None, mode: str = "path",
                    cfg=Depends(get_config)):
    if mode not in ("path", "open", "print", "download"):
        raise HTTPException(400, "mode must be path|open|print|download")
    with db_session(cfg) as conn:
        if week_id is not None and not db.get_week(conn, week_id):
            raise HTTPException(404, f"Week {week_id} not found")
        try:
            path = reports.generate_optional_pdf(conn, week_id)
        except sqlite3.Error as e:
            raise HTTPException(500, f"Database error: {e}")
        except OSError as e:
            raise HTTPException(500, f"File system error: {e}")
    return _deliver(path, mode)


@router.post("/reports/students")
def students_report(mode: str = "path", cfg=Depends(get_config)):
    if mode not in ("path", "open", "print", "download"):
        raise HTTPException(400, "mode must be path|open|print|download")
    with db_session(cfg) as conn:
        try:
            path = reports.generate_students_pdf(conn)
        except sqlite3.Error as e:
            raise HTTPException(500, f"Database error: {e}")
        except OSError as e:
            raise HTTPException(500, f"File system error: {e}")
    return _deliver(path, mode)
