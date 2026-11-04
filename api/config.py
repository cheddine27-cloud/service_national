"""Database path configuration with strict safety rules.

Modes (via env NS_MODE):
  * "test"        - requires NS_DB_PATH pointing to a temporary/test database.
  * "dev"         - requires NS_DB_PATH pointing to an explicitly chosen database.
  * "production"  - requires NS_CONFIRM_PRODUCTION=1 AND NS_DB_PATH set explicitly
                    (the standard path next to the old application is used only if
                    NS_DB_PATH equals it).

If the configured database file does not exist, /api/health reports it, but the
API never silently creates a new empty production database. Database files are
only created by db.init_db() which callers (the old main.py or the tests) invoke
explicitly.

Never runs destructive operations automatically.
"""

import os
from dataclasses import dataclass

STANDARD_DB_PATH = os.environ.get("NS_STANDARD_DB_PATH") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "service_national.db"
)

VALID_SERVICES = {"guard", "restaurant", "kitchen", "cleaning", "toilet"}


@dataclass
class DbConfig:
    mode: str
    db_path: str
    confirmed: bool

    @property
    def exists(self) -> bool:
        return os.path.isfile(self.db_path)


class ConfigurationError(RuntimeError):
    """Raised when the server must refuse to start in the requested mode."""


def load_config() -> DbConfig:
    mode = os.environ.get("NS_MODE", "").strip().lower()
    db_path = os.environ.get("NS_DB_PATH", "").strip()
    confirmed = os.environ.get("NS_CONFIRM_PRODUCTION", "").strip() == "1"

    if mode not in ("test", "dev", "production"):
        raise ConfigurationError(
            "NS_MODE must be one of: test, dev, production. "
            "Refusing to start without an explicit database mode."
        )

    if not db_path:
        raise ConfigurationError(
            "NS_DB_PATH is not set. This intentionally avoids silently "
            "creating or picking any database file. Set NS_DB_PATH explicitly."
        )

    if mode == "production":
        if not confirmed:
            raise ConfigurationError(
                "Production mode requires NS_CONFIRM_PRODUCTION=1 to confirm "
                "the real database path. Refusing to start."
            )
        # Establishing additional guard: explicit path must be the declared
        # standard path unless the operator set NS_STANDARD_DB_PATH themselves.
        if os.path.abspath(db_path) != os.path.abspath(STANDARD_DB_PATH):
            raise ConfigurationError(
                f"Production mode expects the standard database path "
                f"{STANDARD_DB_PATH}. Got: {db_path}"
            )

    return DbConfig(mode=mode, db_path=os.path.abspath(db_path), confirmed=confirmed)
