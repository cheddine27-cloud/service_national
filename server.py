"""Local launcher for the National Service API.

Usage (dev/test):
    set NS_MODE=dev
    set NS_DB_PATH=F:\\some\\safe\\dev.db
    python server.py

Production is only allowed when:
    NS_MODE=production
    NS_CONFIRM_PRODUCTION=1
    NS_DB_PATH points to the standard data\\service_national.db

The server binds 127.0.0.1 only. It never touches the network beyond
localhost and never creates or migrates the production database."""

import os
import uvicorn

from api.config import load_config, ConfigurationError
from api.main import app


def main():
    try:
        cfg = load_config()
    except ConfigurationError as e:
        print("REFUSING TO START:", e, sep="\n")
        raise SystemExit(2)

    print("=" * 60)
    print("National Service local API")
    print(f"  mode      : {cfg.mode}")
    print(f"  db path   : {cfg.db_path}")
    print(f"  db exists : {'YES' if cfg.exists else 'NO (missing)'}")
    print("  bind      : http://127.0.0.1:8765")
    print("  swagger   : http://127.0.0.1:8765/docs")
    print("=" * 60)

    if cfg.mode == "production" and not cfg.exists:
        print("REFUSING TO START: production database file not found.")
        raise SystemExit(2)

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")


if __name__ == "__main__":
    main()
