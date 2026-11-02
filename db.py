import sqlite3
import os
from datetime import datetime

DEFAULT_DB_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "NationalService")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "service_national.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS squads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    name TEXT NOT NULL,
    size INTEGER DEFAULT 0,
    UNIQUE(group_id, number)
);
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    squad_id INTEGER REFERENCES squads(id) ON DELETE SET NULL,
    full_name TEXT NOT NULL,
    father_name TEXT,
    national_id TEXT,
    birth_date TEXT,
    phone TEXT,
    address TEXT,
    blood_type TEXT,
    rank TEXT,
    enlistment_date TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS weeks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_id INTEGER NOT NULL REFERENCES weeks(id) ON DELETE CASCADE,
    day_index INTEGER NOT NULL,
    date TEXT NOT NULL,
    service TEXT NOT NULL,
    squad_id INTEGER REFERENCES squads(id) ON DELETE SET NULL,
    count INTEGER DEFAULT 0,
    notes TEXT,
    UNIQUE(week_id, day_index, service)
);
CREATE TABLE IF NOT EXISTS optional_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_id INTEGER REFERENCES weeks(id) ON DELETE SET NULL,
    date TEXT,
    name TEXT NOT NULL,
    count INTEGER DEFAULT 0,
    receiver TEXT,
    squad_id INTEGER REFERENCES squads(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TEXT NOT NULL
);
"""

DAY_NAMES_AR = {
    0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس",
    4: "الجمعة", 5: "السبت", 6: "الأحد",
}


def get_db_path():
    # allow override via settings file? simple: env or default
    p = os.environ.get("NS_DB_PATH")
    if p:
        return p
    return DEFAULT_DB_PATH


def connect(db_path=None):
    if db_path is None:
        db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None):
    conn = connect(db_path)
    conn.executescript(SCHEMA)
    # migrate students columns for older DBs
    for col, decl in (("father_name", "TEXT"), ("address", "TEXT"), ("blood_type", "TEXT"),
                      ("enlistment_date", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE students ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    # seed groups
    for code, name in (("A", "فوج أ"), ("B", "فوج ب")):
        conn.execute("INSERT OR IGNORE INTO groups(code,name) VALUES (?,?)", (code, name))
    # default settings
    defaults = {
        "unit_name": "الخدمة الوطنية",
        "toilet_daily_count": "3",
        "guard_daily_count": "4",
        "week_start": "Saturday",
    }
    for k, v in defaults.items():
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)", (k, v))
    conn.commit()
    conn.close()


def get_setting(conn, key, default=None):
    r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default


def set_setting(conn, key, value):
    conn.execute("INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (key, value))
    conn.commit()


def dict_row(row):
    return dict(row) if row is not None else None


# ---------- Groups & Squads ----------
def list_groups(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM groups ORDER BY code").fetchall()]


def list_squads(conn, group_code=None):
    q = """SELECT s.*, g.code AS group_code, g.name AS group_name
           FROM squads s JOIN groups g ON g.id=s.group_id"""
    params = []
    if group_code:
        q += " WHERE g.code=?"
        params.append(group_code)
    q += " ORDER BY g.code, s.number"
    return [dict(r) for r in conn.execute(q, params).fetchall()]


def create_squad(conn, group_code, number, name=None, size=0):
    g = conn.execute("SELECT id FROM groups WHERE code=?", (group_code,)).fetchone()
    if not g:
        raise ValueError("group not found")
    if name is None:
        name = f"{group_code}{number}"
    conn.execute("INSERT INTO squads(group_id,number,name,size) VALUES (?,?,?,?)",
                 (g["id"], number, name, size))
    conn.commit()


def ensure_default_squads(conn):
    groups = list_groups(conn)
    for g in groups:
        existing = conn.execute("SELECT COUNT(*) c FROM squads WHERE group_id=?", (g["id"],)).fetchone()["c"]
        if existing == 0:
            for n in range(1, 6):
                create_squad(conn, g["code"], n, f"{g['code']}{n}", 0)


def update_squad(conn, squad_id, name=None, size=None, number=None):
    fields = []
    params = []
    if name is not None:
        fields.append("name=?"); params.append(name)
    if size is not None:
        fields.append("size=?"); params.append(size)
    if number is not None:
        fields.append("number=?"); params.append(number)
    if not fields:
        return
    params.append(squad_id)
    conn.execute(f"UPDATE squads SET {', '.join(fields)} WHERE id=?", params)
    conn.commit()


def delete_squad(conn, squad_id):
    conn.execute("DELETE FROM squads WHERE id=?", (squad_id,))
    conn.commit()


# ---------- Students ----------
def list_students(conn, squad_id=None, search=None):
    q = """SELECT st.*, sq.name AS squad_name, g.code AS group_code
           FROM students st LEFT JOIN squads sq ON sq.id=st.squad_id
           LEFT JOIN groups g ON g.id=sq.group_id"""
    params = []
    where = []
    if squad_id:
        where.append("st.squad_id=?"); params.append(squad_id)
    if search:
        where.append("(st.full_name LIKE ? OR st.national_id LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY st.full_name"
    return [dict(r) for r in conn.execute(q, params).fetchall()]


def create_student(conn, **kw):
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("""INSERT INTO students(squad_id,full_name,father_name,national_id,birth_date,phone,address,blood_type,rank,enlistment_date,notes,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (kw.get("squad_id"), kw["full_name"], kw.get("father_name"), kw.get("national_id"), kw.get("birth_date"),
                  kw.get("phone"), kw.get("address"), kw.get("blood_type"), kw.get("rank"), kw.get("enlistment_date"),
                  kw.get("notes"), now))
    conn.commit()


def update_student(conn, student_id, **kw):
    fields = []
    params = []
    for col in ("squad_id", "full_name", "father_name", "national_id", "birth_date", "phone", "address", "blood_type", "rank", "enlistment_date", "notes"):
        if col in kw:
            fields.append(f"{col}=?"); params.append(kw[col])
    if not fields:
        return
    params.append(student_id)
    conn.execute(f"UPDATE students SET {', '.join(fields)} WHERE id=?", params)
    conn.commit()


def delete_student(conn, student_id):
    conn.execute("DELETE FROM students WHERE id=?", (student_id,))
    conn.commit()


# ---------- Weeks & Assignments ----------
def list_weeks(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM weeks ORDER BY start_date DESC").fetchall()]


def get_week(conn, week_id):
    return dict_row(conn.execute("SELECT * FROM weeks WHERE id=?", (week_id,)).fetchone())


def create_week(conn, start_date, end_date, notes=None):
    now = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute("INSERT INTO weeks(start_date,end_date,created_at,notes) VALUES (?,?,?,?)",
                       (start_date, end_date, now, notes))
    conn.commit()
    return cur.lastrowid


def delete_week(conn, week_id):
    conn.execute("DELETE FROM weeks WHERE id=?", (week_id,))
    conn.commit()


def get_assignments(conn, week_id, service=None):
    q = """SELECT a.*, s.name AS squad_name, g.code AS group_code
           FROM assignments a LEFT JOIN squads s ON s.id=a.squad_id
           LEFT JOIN groups g ON g.id=s.group_id
           WHERE a.week_id=?"""
    params = [week_id]
    if service:
        q += " AND a.service=?"
        params.append(service)
    q += " ORDER BY a.day_index, a.service"
    return [dict(r) for r in conn.execute(q, params).fetchall()]


def upsert_assignment(conn, week_id, day_index, date, service, squad_id=None, count=0, notes=None):
    conn.execute("""INSERT INTO assignments(week_id,day_index,date,service,squad_id,count,notes)
                    VALUES (?,?,?,?,?,?,?)
                    ON CONFLICT(week_id,day_index,service) DO UPDATE SET
                      date=excluded.date, squad_id=excluded.squad_id, count=excluded.count, notes=excluded.notes""",
                 (week_id, day_index, date, service, squad_id, count, notes))
    conn.commit()


def update_assignment(conn, assignment_id, squad_id=None, count=None, notes=None):
    fields = []
    params = []
    if squad_id is not None:
        fields.append("squad_id=?"); params.append(squad_id)
    if count is not None:
        fields.append("count=?"); params.append(count)
    if notes is not None:
        fields.append("notes=?"); params.append(notes)
    if not fields:
        return
    params.append(assignment_id)
    conn.execute(f"UPDATE assignments SET {', '.join(fields)} WHERE id=?", params)
    conn.commit()


# ---------- Optional services ----------
def list_optional(conn, week_id=None):
    q = """SELECT o.*, s.name AS squad_name, g.code AS group_code
           FROM optional_services o LEFT JOIN squads s ON s.id=o.squad_id
           LEFT JOIN groups g ON g.id=s.group_id"""
    params = []
    if week_id is not None:
        q += " WHERE o.week_id=?"
        params.append(week_id)
    q += " ORDER BY o.date, o.name"
    return [dict(r) for r in conn.execute(q, params).fetchall()]


def create_optional(conn, **kw):
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("""INSERT INTO optional_services(week_id,date,name,count,receiver,squad_id,notes,created_at)
                    VALUES (?,?,?,?,?,?,?,?)""",
                 (kw.get("week_id"), kw.get("date"), kw["name"], kw.get("count", 0),
                  kw.get("receiver"), kw.get("squad_id"), kw.get("notes"), now))
    conn.commit()


def update_optional(conn, oid, **kw):
    fields = []
    params = []
    for col in ("week_id", "date", "name", "count", "receiver", "squad_id", "notes"):
        if col in kw:
            fields.append(f"{col}=?"); params.append(kw[col])
    if not fields:
        return
    params.append(oid)
    conn.execute(f"UPDATE optional_services SET {', '.join(fields)} WHERE id=?", params)
    conn.commit()


def delete_optional(conn, oid):
    conn.execute("DELETE FROM optional_services WHERE id=?", (oid,))
    conn.commit()


def squad_usage_for_week(conn, week_id):
    # count assignments per squad
    rows = conn.execute("""SELECT squad_id, COUNT(*) c FROM assignments
                          WHERE week_id=? AND squad_id IS NOT NULL GROUP BY squad_id""", (week_id,)).fetchall()
    return {r["squad_id"]: r["c"] for r in rows}
