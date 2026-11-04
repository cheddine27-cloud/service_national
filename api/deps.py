"""Per-request SQLite connection dependency. Sync endpoints are executed by
FastAPI inside a threadpool, so the blocking sqlite driver does not block the
event loop."""

from contextlib import contextmanager

import sqlite3

import db
from .config import load_config


def get_config():
    return load_config()


@contextmanager
def db_session(cfg):
    if not cfg.exists:
        raise FileNotFoundError(
            f"Database file not found: {cfg.db_path} "
            "(it is never auto-created by the API; the application creates it explicitly)"
        )
    conn = db.connect(cfg.db_path)
    try:
        yield conn
    finally:
        conn.close()
