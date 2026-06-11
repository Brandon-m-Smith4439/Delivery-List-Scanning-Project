"""Configuration for the delivery-list scanner pilot.

The frontend should call relative API paths. Host names, ports, database paths,
auth mode, and future SQL connection strings belong on the server side.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    root: Path
    data_dir: Path
    sample_path: Path
    database_type: str
    database_path: Path
    database_connection_string: str
    host: str
    port: int
    base_url: str
    auth_mode: str
    session_secret: str
    default_admin_username: str
    default_admin_password: str
    environment: str

    @property
    def production(self) -> bool:
        return self.environment.lower() in {"prod", "production"}


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def load_config(root: Path) -> AppConfig:
    root = root.resolve()
    data_dir = root / "data"
    default_db_path = data_dir / "delivery-scanner-pilot.db"
    database_path = Path(os.environ.get("DLS_DATABASE_PATH", str(default_db_path))).expanduser()
    if not database_path.is_absolute():
        database_path = root / database_path

    host = os.environ.get("DLS_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = _int_env("DLS_PORT", _int_env("PORT", 8765))
    base_url = os.environ.get("DLS_BASE_URL", f"http://{host}:{port}/").strip()

    return AppConfig(
        root=root,
        data_dir=data_dir,
        sample_path=Path(os.environ.get("DLS_SAMPLE_PATH", str(data_dir / "sample-delivery-list.json"))),
        database_type=os.environ.get("DLS_DATABASE_TYPE", "sqlite").strip().lower() or "sqlite",
        database_path=database_path,
        database_connection_string=os.environ.get("DLS_DATABASE_CONNECTION_STRING", "").strip(),
        host=host,
        port=port,
        base_url=base_url,
        auth_mode=os.environ.get("DLS_AUTH_MODE", "local-dev").strip().lower() or "local-dev",
        session_secret=os.environ.get("DLS_SESSION_SECRET", "dev-only-change-me"),
        default_admin_username=os.environ.get("DLS_DEFAULT_ADMIN_USERNAME", "admin").strip() or "admin",
        default_admin_password=os.environ.get("DLS_DEFAULT_ADMIN_PASSWORD", "Admin123!").strip() or "Admin123!",
        environment=os.environ.get("DLS_ENVIRONMENT", "development").strip().lower() or "development",
    )
