# File: backend/config.py
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
    temp_delivery_lists_dir: Path
    hardware_lists_dir: Path
    sketches_dir: Path
    programs_dir: Path
    completed_wj_dir: Path
    database_type: str
    database_path: Path
    database_connection_string: str
    database_timeout_seconds: int
    database_auto_schema: bool
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
        """Purpose: Run the production workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return self.environment.lower() in {"prod", "production"}


def _int_env(name: str, default: int) -> int:
    """Purpose: Run the int env workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    """Purpose: Run the bool env workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def load_config(root: Path) -> AppConfig:
    """Purpose: Load config for the delivery-list scanner workflow.

    Effects: This function reads or updates shared application state.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    root = root.resolve()
    data_dir = root / "data"
    default_db_path = data_dir / "delivery-scanner-pilot.db"
    default_temp_delivery_lists = Path("I:/BAREFOOT-INSTALL/Glass Production/Brandon/Temp Delivery Lists")
    production_root = Path("I:/BAREFOOT-INSTALL/Glass Production")
    default_hardware_lists = production_root / "Hardware Lists"
    default_sketches = production_root / "Sketches"
    default_programs = production_root / "Programs"
    default_completed_wj = production_root / "Completed WJ"
    database_path = Path(os.environ.get("DLS_DATABASE_PATH", str(default_db_path))).expanduser()
    temp_delivery_lists_dir = Path(os.environ.get("DLS_TEMP_DELIVERY_LISTS_PATH", str(default_temp_delivery_lists))).expanduser()
    hardware_lists_dir = Path(os.environ.get("DLS_HARDWARE_LISTS_PATH", str(default_hardware_lists))).expanduser()
    sketches_dir = Path(os.environ.get("DLS_SKETCHES_PATH", str(default_sketches))).expanduser()
    programs_dir = Path(os.environ.get("DLS_PROGRAMS_PATH", str(default_programs))).expanduser()
    completed_wj_dir = Path(os.environ.get("DLS_COMPLETED_WJ_PATH", str(default_completed_wj))).expanduser()
    if not database_path.is_absolute():
        database_path = root / database_path
    if not temp_delivery_lists_dir.is_absolute():
        temp_delivery_lists_dir = root / temp_delivery_lists_dir
    # Windows drive paths are absolute on the production host. Relative overrides
    # remain project-relative for portable development/test environments.
    def normalize_share_path(value: Path) -> Path:
        if value.is_absolute() or (len(str(value)) >= 3 and str(value)[1:3] in {":/", ":\\"}):
            return value
        return root / value
    hardware_lists_dir = normalize_share_path(hardware_lists_dir)
    sketches_dir = normalize_share_path(sketches_dir)
    programs_dir = normalize_share_path(programs_dir)
    completed_wj_dir = normalize_share_path(completed_wj_dir)

    host = os.environ.get("DLS_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = _int_env("DLS_PORT", _int_env("PORT", 8765))
    base_url = os.environ.get("DLS_BASE_URL", f"http://{host}:{port}/").strip()

    return AppConfig(
        root=root,
        data_dir=data_dir,
        sample_path=Path(os.environ.get("DLS_SAMPLE_PATH", str(data_dir / "sample-delivery-list.json"))),
        temp_delivery_lists_dir=temp_delivery_lists_dir,
        hardware_lists_dir=hardware_lists_dir,
        sketches_dir=sketches_dir,
        programs_dir=programs_dir,
        completed_wj_dir=completed_wj_dir,
        database_type=os.environ.get("DLS_DATABASE_TYPE", "sqlite").strip().lower() or "sqlite",
        database_path=database_path,
        database_connection_string=os.environ.get("DLS_DATABASE_CONNECTION_STRING", "").strip(),
        database_timeout_seconds=_int_env("DLS_DATABASE_TIMEOUT_SECONDS", 30),
        database_auto_schema=_bool_env("DLS_DATABASE_AUTO_SCHEMA", True),
        host=host,
        port=port,
        base_url=base_url,
        auth_mode=os.environ.get("DLS_AUTH_MODE", "local-dev").strip().lower() or "local-dev",
        session_secret=os.environ.get("DLS_SESSION_SECRET", "dev-only-change-me"),
        default_admin_username=os.environ.get("DLS_DEFAULT_ADMIN_USERNAME", "admin").strip() or "admin",
        default_admin_password=os.environ.get("DLS_DEFAULT_ADMIN_PASSWORD", "Admin123!").strip() or "Admin123!",
        environment=os.environ.get("DLS_ENVIRONMENT", "development").strip().lower() or "development",
    )
