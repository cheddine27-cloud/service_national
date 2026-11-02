import os
import sys

# Ensure local imports work
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import db
from ui import App


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, "data")
    os.makedirs(data_dir, exist_ok=True)
    os.environ["NS_DB_PATH"] = os.path.join(data_dir, "service_national.db")
    db.init_db()
    conn = db.connect()
    # ensure default squads
    try:
        db.ensure_default_squads(conn)
    except Exception:
        pass
    app = App(conn)
    app.mainloop()
    conn.close()


if __name__ == "__main__":
    main()
