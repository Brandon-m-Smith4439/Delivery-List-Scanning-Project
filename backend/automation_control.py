#!/usr/bin/env python3
# File: backend/automation_control.py
"""Server-side control plane for the Delivery List SQL automation GUI.

The browser never receives database credentials or arbitrary command access. It
may select only the predefined exporter/importer actions exposed here.
"""

from __future__ import annotations

import errno
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


AUTOMATION_MODES = {
    "disabled",
    "folder-import-only",
    "sql-export-only",
    "sql-export-and-import",
}
RUN_ACTIONS = {
    "folder-import-only": "FolderImportOnly",
    "sql-export-only": "SqlExportOnly",
    "sql-export-and-import": "SqlExportAndImport",
    "reject-sync-only": "RejectSyncOnly",
}

# The browser control plane refreshes the complete installed automation runtime
# required by manual runs and Windows Task Scheduler. Configuration is excluded
# intentionally: saved settings are copied separately so a runtime refresh never
# replaces the operator's current network folder, schedule, or automation mode.
AUTOMATION_RUNTIME_FILES = (
    "Run-DeliveryListSqlAutomation.ps1",
    "Initialize-DeliveryListSqlAutomation.ps1",
    "Install-DeliveryListSqlAutomationTasks.ps1",
    "Remove-DeliveryListSqlAutomationTasks.ps1",
    "Show-DeliveryListSqlAutomationStatus.ps1",
    "Verify-DeliveryListSqlAutomation.ps1",
    "build_delivery_workbook.py",
    "import_delivery_folder.py",
    "delivery_import_safety.py",
    "publish_automation_notification.py",
    "validate_scanner_compatibility.py",
    "verify_delivery_import.py",
    "verified-source-exclusions.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def bounded_int(value: Any, minimum: int, maximum: int, name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a whole number") from exc
    if number < minimum or number > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return number


def clean_date(value: Any, name: str, required: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        if required:
            raise ValueError(f"{name} is required")
        return ""
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError(f"{name} must use YYYY-MM-DD") from exc


class DeliveryAutomationController:
    """Manage validated configuration, manual runs, and scheduled tasks."""

    def __init__(self, project_root: Path, scanner_config: Any, scanner_store: Any | None = None) -> None:
        self.project_root = Path(project_root).resolve()
        self.scanner_config = scanner_config
        self.scanner_store = scanner_store
        # Cache the live scanner-store identity once per web-server process.
        # The automation runtime uses this safe metadata (never credentials) to
        # prove it is importing into the same database the Scan page is reading.
        self._scanner_store_identity_cache: dict[str, str] = {}
        self._state_lock = threading.Lock()
        self._config_lock = threading.Lock()
        self._active_process: subprocess.Popen[str] | None = None
        self._active_status: dict[str, Any] = {}
        self._runtime_sync_status: dict[str, Any] = {
            "attempted": False,
            "ok": True,
            "synchronizedFiles": [],
            "error": "",
        }
        # Import History supplements durable database rows with immutable
        # PowerShell run summaries. Cache the parsed archive briefly so opening
        # or paging the modal cannot repeatedly parse hundreds of JSON files.
        self._import_history_archive_cache: dict[int, tuple[float, list[dict[str, Any]]]] = {}

        # Scheduled tasks execute the installed runtime under
        # C:\DeliveryListAutomation\Scripts without passing through start_run().
        # Refresh that runtime once when the web app starts so a scheduled task
        # cannot launch an older exporter after an application update. A sync
        # warning is surfaced on the dashboard but does not prevent app startup.
        try:
            startup_config = self._read_config(required=False)
            if startup_config:
                self._refresh_runtime_scripts_if_safe(startup_config)
        except Exception as exc:
            self._runtime_sync_status = {
                "attempted": True,
                "ok": False,
                "deferred": False,
                "synchronizedFiles": [],
                "error": str(exc),
            }

    def _candidate_config_paths(self) -> list[Path]:
        candidates: list[Path] = []
        env_path = str(os.environ.get("DLS_SQL_EXPORT_CONFIG") or "").strip()
        if env_path:
            candidates.append(Path(env_path).expanduser())
        working_root = str(os.environ.get("DLS_SQL_AUTOMATION_ROOT") or r"C:\DeliveryListAutomation").strip()
        candidates.append(Path(working_root) / "Scripts" / "sql-export.config.json")
        candidates.append(self.project_root / "automation" / "sql_delivery_export" / "sql-export.config.json")
        return candidates

    def config_path(self) -> Path:
        for path in self._candidate_config_paths():
            if path.is_file():
                return path
        return self._candidate_config_paths()[0]

    def _scanner_store_identity(self) -> dict[str, str]:
        """Return safe, stable metadata that identifies the live scanner store.

        The SQL updater runs in a separate PowerShell/Python process. Merely
        sharing ProjectRoot is not sufficient when an environment variable or
        service account can make that process resolve a different SQLite/Azure
        store. Persisting this non-secret identity lets the updater bind to and
        validate the same store before it is allowed to report an import as
        successful.
        """
        if self._scanner_store_identity_cache:
            return dict(self._scanner_store_identity_cache)
        store = self.scanner_store
        if store is None:
            return {}
        try:
            health = store.health() or {}
        except Exception:
            return {}

        mode = str(health.get("mode") or "").strip().lower()
        database = str(health.get("database") or "").strip()
        server = str(health.get("server") or "").strip()
        environment = str(health.get("environment") or "").strip()
        if not mode or not database:
            return {}

        if mode == "sqlite":
            try:
                database_path = Path(database).expanduser()
                if not database_path.is_absolute():
                    database_path = self.project_root / database_path
                database = str(database_path.resolve())
            except (OSError, RuntimeError):
                database = str(database)

        identity = {
            "Mode": mode,
            "Database": database,
        }
        if server:
            identity["Server"] = server
        if environment:
            identity["Environment"] = environment
        self._scanner_store_identity_cache = dict(identity)
        return identity

    def _read_config(self, required: bool = True, persist_repairs: bool = True) -> dict[str, Any]:
        path = self.config_path()
        if not path.is_file():
            if required:
                raise FileNotFoundError(
                    "Delivery-list automation is not installed. Run Setup-DeliveryListSqlAutomation-v121.bat first."
                )
            return {}
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("Automation configuration is not a JSON object")

        # The installed automation can outlive a renamed/copied project folder
        # or inherit a different DLS_DATABASE_PATH than the web server. Keep both
        # the project root and safe scanner-store identity pinned to this live
        # server so Import History can never report success against one database
        # while Scan/Print are reading another.
        changed = False
        configured_root = str(payload.get("ProjectRoot") or "").strip()
        current_root = str(self.project_root)
        configured_key = configured_root.replace("\\", "/").rstrip("/").lower()
        current_key = current_root.replace("\\", "/").rstrip("/").lower()
        if configured_key != current_key:
            payload["ProjectRoot"] = current_root
            changed = True
            self._runtime_sync_status = {
                **self._runtime_sync_status,
                "projectRootRepaired": True,
                "previousProjectRoot": configured_root,
                "projectRoot": current_root,
            }

        scanner_identity = self._scanner_store_identity()
        configured_scanner = payload.get("ScannerStore")
        if scanner_identity and configured_scanner != scanner_identity:
            payload["ScannerStore"] = scanner_identity
            changed = True
            self._runtime_sync_status = {
                **self._runtime_sync_status,
                "scannerStoreBound": True,
                "scannerStore": scanner_identity,
            }

        if changed and persist_repairs:
            with self._config_lock:
                self._replace_json_file(path, payload)
        return payload

    @staticmethod
    def _replace_json_file(path: Path, payload: dict[str, Any]) -> None:
        """Atomically replace one JSON file without sharing a temporary filename."""
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, path)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def _write_config(self, payload: dict[str, Any]) -> None:
        path = self.config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._config_lock:
            self._replace_json_file(path, payload)

    def _set_schedule_enabled_in_config_path(self, path: Path, enabled: bool) -> None:
        """Persist the scheduler flag to an explicit config without resetting it."""
        payload = self._read_json_file(path)
        if not payload:
            raise FileNotFoundError(f"Automation configuration could not be read: {path}")
        payload.setdefault("Automation", {})["ScheduleEnabled"] = bool(enabled)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, path)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def _runtime_paths(self, config: dict[str, Any]) -> dict[str, Path]:
        working_root = Path(str(config.get("WorkingRoot") or r"C:\DeliveryListAutomation"))
        script_root = working_root / "Scripts"
        maintained_script_root = self.project_root / "automation" / "sql_delivery_export"
        runtime_runner = script_root / "Run-DeliveryListSqlAutomation.ps1"
        return {
            "working_root": working_root,
            "script_root": script_root,
            "maintained_script_root": maintained_script_root,
            # Manual and scheduled runs now share the same installed runtime path.
            # start_run() refreshes the maintained reconciliation files first, so
            # PowerShell and every helper continue to execute from one directory.
            "runner": runtime_runner,
            "runtime_runner": runtime_runner,
            "installer": script_root / "Install-DeliveryListSqlAutomationTasks.ps1",
            "remover": script_root / "Remove-DeliveryListSqlAutomationTasks.ps1",
            "last_run": working_root / "State" / "last-run.json",
            "gui_run": working_root / "State" / "web-gui-run.json",
            "gui_summary": working_root / "State" / "web-gui-summary.json",
            "run_lock": working_root / "State" / "run.lock",
            "logs_dir": working_root / "Logs",
            "run_history_dir": working_root / "State" / "RunHistory",
            "last_import_result": working_root / "State" / "last-import-result.json",
        }

    def _sync_runtime_scripts(self, config: dict[str, Any]) -> list[str]:
        """Atomically refresh the installed files used by browser-started runs.

        v0.231 executed the project PowerShell file directly while its working
        directory and installed helpers remained under C:\\DeliveryListAutomation.
        Some Windows hosts stalled before the script emitted its first line. This
        repair restores one runtime directory while still preventing an outdated
        installed importer from bypassing current reconciliation rules.
        """
        paths = self._runtime_paths(config)
        source_root = paths["maintained_script_root"]
        target_root = paths["script_root"]
        target_root.mkdir(parents=True, exist_ok=True)
        synchronized: list[str] = []

        for file_name in AUTOMATION_RUNTIME_FILES:
            source = source_root / file_name
            target = target_root / file_name
            if not source.is_file():
                raise FileNotFoundError(f"Maintained automation file is missing: {source}")

            source_bytes = source.read_bytes()
            if target.is_file() and target.read_bytes() == source_bytes:
                continue

            temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
            try:
                temporary.write_bytes(source_bytes)
                os.replace(temporary, target)
            finally:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass
            synchronized.append(file_name)

        return synchronized

    def _ensure_installed_runtime_config(self, config: dict[str, Any]) -> Path:
        """Write the current saved settings to the stable installed runtime path.

        A local scanner can initially run from the project copy of
        ``sql-export.config.json`` before C:\\DeliveryListAutomation has been fully
        installed. Scheduled tasks need a stable config path outside the project
        tree, so materialize the currently active settings without resetting any
        operator choices.
        """
        paths = self._runtime_paths(config)
        target = paths["script_root"] / "sql-export.config.json"
        target.parent.mkdir(parents=True, exist_ok=True)

        payload = json.loads(json.dumps(config))
        payload["ProjectRoot"] = str(self.project_root)
        payload["WorkingRoot"] = str(paths["working_root"])
        scanner_identity = self._scanner_store_identity()
        if scanner_identity:
            payload["ScannerStore"] = scanner_identity
        runtime = payload.setdefault("Runtime", {})
        if not str(runtime.get("PowerShellPath") or "").strip():
            runtime["PowerShellPath"] = self._power_shell(payload)
        if not str(runtime.get("PythonPath") or "").strip():
            python_path = Path(sys.executable).resolve()
            if python_path.is_file():
                runtime["PythonPath"] = str(python_path)
                runtime["PythonArguments"] = []
        elif "PythonArguments" not in runtime:
            runtime["PythonArguments"] = []

        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, target)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        return target

    def _ensure_schedule_command_wrappers(
        self,
        config: dict[str, Any],
        runtime_config_path: Path,
    ) -> list[str]:
        """Create the two command files Windows Task Scheduler actually runs."""
        paths = self._runtime_paths(config)
        working_root = paths["working_root"]
        working_root.mkdir(parents=True, exist_ok=True)
        runner = paths["runner"]
        power_shell = self._power_shell(config)
        synchronized: list[str] = []

        for file_name, mode in (("Run-Incremental.cmd", "Incremental"), ("Run-Full.cmd", "Full")):
            target = working_root / file_name
            content = (
                "@echo off\r\n"
                f'"{power_shell}" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass '
                f'-WindowStyle Hidden -File "{runner}" -Mode {mode} -RunAction Configured '
                f'-ConfigPath "{runtime_config_path}"\r\n'
                "exit /b %errorlevel%\r\n"
            )
            encoded = content.encode("utf-8")
            if target.is_file() and target.read_bytes() == encoded:
                continue
            temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
            try:
                temporary.write_bytes(encoded)
                os.replace(temporary, target)
            finally:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass
            synchronized.append(file_name)

        return synchronized

    def _prepare_schedule_runtime(self, config: dict[str, Any]) -> dict[str, Any]:
        """Self-heal the installed scheduler runtime before install/remove actions."""
        if self._runtime_lock_busy(config):
            raise RuntimeError(
                "A delivery-list automation run is active. Wait for it to finish before changing the schedule."
            )

        synchronized_files = self._sync_runtime_scripts(config)
        runtime_config_path = self._ensure_installed_runtime_config(config)
        synchronized_commands = self._ensure_schedule_command_wrappers(config, runtime_config_path)
        paths = self._runtime_paths(config)
        required_paths = (
            paths["runner"],
            paths["installer"],
            paths["remover"],
            runtime_config_path,
            paths["working_root"] / "Run-Incremental.cmd",
            paths["working_root"] / "Run-Full.cmd",
        )
        missing = [str(path) for path in required_paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                "Automation schedule runtime could not be prepared. Missing: " + ", ".join(missing)
            )

        synchronized = [*synchronized_files, *synchronized_commands]
        self._runtime_sync_status = {
            "attempted": True,
            "ok": True,
            "deferred": False,
            "schedulePrepared": True,
            "synchronizedFiles": synchronized,
            "configPath": str(runtime_config_path),
            "error": "",
        }
        return {
            "configPath": runtime_config_path,
            "synchronizedFiles": synchronized,
        }

    def _runtime_lock_busy(self, config: dict[str, Any]) -> bool:
        """Return True when PowerShell currently owns the shared automation lock."""
        lock_path = self._runtime_paths(config)["run_lock"]
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT)
        except PermissionError:
            return True
        except OSError as exc:
            if getattr(exc, "winerror", None) in {32, 33} or exc.errno in {errno.EACCES, errno.EBUSY}:
                return True
            raise
        else:
            os.close(descriptor)
            return False

    def _refresh_runtime_scripts_if_safe(self, config: dict[str, Any]) -> None:
        """Refresh scheduled-task runtime files without modifying an active run."""
        try:
            if self._runtime_lock_busy(config):
                self._runtime_sync_status = {
                    "attempted": True,
                    "ok": False,
                    "deferred": True,
                    "synchronizedFiles": [],
                    "error": "Runtime refresh is waiting for the active automation run to finish.",
                }
                return
            synchronized = self._sync_runtime_scripts(config)
            self._runtime_sync_status = {
                "attempted": True,
                "ok": True,
                "deferred": False,
                "synchronizedFiles": synchronized,
                "error": "",
            }
        except Exception as exc:
            self._runtime_sync_status = {
                "attempted": True,
                "ok": False,
                "deferred": False,
                "synchronizedFiles": [],
                "error": str(exc),
            }

    def _power_shell(self, config: dict[str, Any]) -> str:
        runtime = config.get("Runtime") or {}
        configured = str(runtime.get("PowerShellPath") or "").strip()
        if configured:
            return configured
        return str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")

    def _read_json_file(self, path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, json.JSONDecodeError):
            return {}

    def _read_text_file(self, path: Path) -> str:
        """Read a complete UTF-8 log without silently dropping earlier lines."""
        try:
            return path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            return ""

    def _append_run_log_line(self, path: Path, message: str, level: str = "DEBUG") -> None:
        """Append a controller-side diagnostic to the same log PowerShell streams."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with path.open("a", encoding="utf-8") as handle:
                handle.write(f"{timestamp} [{level}] CONTROLLER | {message}\n")
        except OSError:
            # Logging must never prevent a delivery-list update from starting.
            return

    def _attach_complete_log(self, status: dict[str, Any]) -> dict[str, Any]:
        """Attach the full per-run log used by scheduled and browser-started runs."""
        enriched = dict(status or {})
        log_path_text = str(enriched.get("logPath") or "").strip()
        log_text = ""
        if log_path_text:
            log_text = self._read_text_file(Path(log_path_text))
        if not log_text:
            log_text = str(enriched.get("commandOutput") or enriched.get("stdout") or "")
            stderr = str(enriched.get("stderr") or "")
            if stderr:
                log_text = f"{log_text}\n{stderr}".strip()
        enriched["commandOutput"] = log_text
        enriched["outputLineCount"] = len(log_text.splitlines()) if log_text else 0
        if log_text and not enriched.get("currentStep"):
            enriched["currentStep"] = log_text.splitlines()[-1]
        return enriched

    def _schedule_installed(self) -> bool:
        if os.name != "nt":
            return False
        for task_name in (
            "BFS Delivery List Automation Incremental",
            "BFS Delivery List Automation Full Refresh",
        ):
            result = subprocess.run(
                ["schtasks.exe", "/Query", "/TN", task_name],
                capture_output=True,
                text=True,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode != 0:
                return False
        return True

    def get_dashboard(self) -> dict[str, Any]:
        config = self._read_config(required=False, persist_repairs=False)
        if config:
            self._refresh_runtime_scripts_if_safe(config)
        path = self.config_path()
        runtime_paths = self._runtime_paths(config) if config else {}
        with self._state_lock:
            live_status = dict(self._active_status)
            running = bool(self._active_process and self._active_process.poll() is None)
        gui_run = self._read_json_file(runtime_paths.get("gui_run", Path("missing"))) if runtime_paths else {}
        scheduled_run = self._read_json_file(runtime_paths.get("last_run", Path("missing"))) if runtime_paths else {}
        stored_runs = [row for row in (gui_run, scheduled_run) if row]
        stored_runs.sort(
            key=lambda row: str(row.get("completedAt") or row.get("startedAt") or ""),
            reverse=True,
        )
        last_run = live_status if running and live_status else (stored_runs[0] if stored_runs else live_status)
        # v0.487: live browser runs already stream output in memory. Re-reading
        # the entire growing log file on every one-second dashboard poll becomes
        # progressively more expensive during large A+W syncs. Read the full
        # persisted log only for completed/stored runs.
        if not running:
            last_run = self._attach_complete_log(last_run)
        automation = config.get("Automation") or {}
        schedule = config.get("Schedule") or {}
        notifications = config.get("Notifications") or {}
        reject_sync = config.get("RejectSync") or {}
        production_sync = config.get("ProductionSync") or {}
        database = config.get("Database") or {}
        return {
            "ok": True,
            "installed": bool(config),
            "configPath": str(path),
            "runtimeReady": bool(config and runtime_paths["runner"].is_file()),
            "runtimeSync": dict(self._runtime_sync_status),
            "running": running,
            "scheduleInstalled": self._schedule_installed() if config else False,
            "settings": {
                "automationMode": str(automation.get("Mode") or "sql-export-and-import"),
                "scheduleEnabled": bool(automation.get("ScheduleEnabled", False)),
                "intervalMinutes": int(schedule.get("IncrementalIntervalMinutes") or 60),
                "incrementalPastDays": int(schedule.get("IncrementalPastDays") or 2),
                "incrementalFutureDays": int(schedule.get("IncrementalFutureDays") or 14),
                "fullPastDays": int(schedule.get("FullPastDays") or 7),
                "fullFutureDays": int(schedule.get("FullFutureDays") or 90),
                "fullRefreshTime": str(schedule.get("FullRefreshTime") or "17:00"),
                "destinationFolder": str(config.get("DestinationFolder") or ""),
                "notificationsEnabled": bool(notifications.get("Enabled", True)),
                "notifyOnNoChanges": bool(notifications.get("NotifyOnNoChanges", True)),
                "rejectSyncEnabled": bool(reject_sync.get("Enabled", True)),
                "rejectIncrementalPastDays": int(reject_sync.get("IncrementalPastDays") or 30),
                "rejectFullPastDays": int(reject_sync.get("FullPastDays") or 365),
                "productionSyncEnabled": bool(production_sync.get("Enabled", True)),
                "productionScheduledEnabled": bool(production_sync.get("ScheduledEnabled", True)),
                "productionIncludeCuttingBookings": bool(production_sync.get("IncludeCuttingBookings", True)),
                "productionCuttingBookingLookbackDays": int(production_sync.get("CuttingBookingLookbackDays") or 120),
                "productionQueryBatchSize": int(production_sync.get("QueryBatchSize") or 60),
                "productionQueryTimeoutSeconds": int(production_sync.get("QueryTimeoutSeconds") or 75),
                "productionGenerationHistoryDepth": int(production_sync.get("GenerationHistoryDepth") or 4),
                "productionCrystalReportFile": str(production_sync.get("CrystalReportFile") or "Prodman_CuttingLabel_Optimisation.rpt"),
                "productionCrystalReportPrintPointId": int(production_sync.get("CrystalReportPrintPointId") or 846),
            },
            "source": {
                "server": str(database.get("Server") or ""),
                "database": str(database.get("Database") or ""),
                "authenticationMode": str(database.get("AuthenticationMode") or "Windows"),
            },
            "lastRun": last_run,
        }

    @staticmethod
    def _row_value(row: Any, *names: str, default: Any = "") -> Any:
        """Read the first available field from dict, sqlite row, or Azure row."""
        for name in names:
            if isinstance(row, dict) and name in row:
                return row.get(name)
            try:
                if name in row.keys():
                    return row[name]
            except (AttributeError, KeyError, TypeError, IndexError):
                continue
        return default

    @staticmethod
    def _parse_change_summary(value: Any) -> dict[str, Any]:
        """Return a safe change-summary dictionary from stored JSON or a mapping."""
        if isinstance(value, dict):
            return value
        text = str(value or "").strip()
        if not text:
            return {}
        try:
            payload = json.loads(text)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _normalize_import_change_summary(self, value: Any) -> dict[str, Any]:
        """Normalize legacy stage-copy totals through the scanner data layer."""
        parsed = self._parse_change_summary(value)
        store = self.scanner_store
        normalizer = getattr(store, "normalize_import_change_summary", None)
        if callable(normalizer):
            return normalizer(parsed)
        return parsed

    def _database_import_history_items(self, maximum_rows: int = 5000) -> list[dict[str, Any]]:
        """Read normalized import-audit rows from the scanner database."""
        store = self.scanner_store
        if store is None or not callable(getattr(store, "connect", None)):
            return []

        clean_maximum = max(1, min(int(maximum_rows or 5000), 20000))
        database_type = str(getattr(store, "database_type", "sqlite") or "sqlite").lower()
        columns = (
            "id, delivery_date, source_name, row_count, total_qty, status, "
            "imported_by, imported_at, source_path, source_hash, import_kind, change_summary"
        )
        with store.connect() as con:
            if database_type in {"azure", "azure_sql", "azure-sql", "sqlserver", "sql_server", "mssql"}:
                rows = con.execute(
                    f"SELECT TOP {clean_maximum} {columns} FROM imports ORDER BY id DESC"
                ).fetchall()
            else:
                rows = con.execute(
                    f"SELECT {columns} FROM imports ORDER BY id DESC LIMIT ?",
                    (clean_maximum,),
                ).fetchall()

        items: list[dict[str, Any]] = []
        for row in rows:
            change = self._normalize_import_change_summary(
                self._row_value(row, "change_summary", "changeSummary")
            )
            created_count = int(change.get("createdCount") or 0)
            reactivated_count = int(change.get("reactivatedCount") or 0)
            updated_count = int(change.get("updatedCount") or 0)
            new_delivery_list = bool(change.get("newDeliveryList"))
            changed_list_ids = [str(value) for value in (change.get("changedListIds") or []) if value]
            stage_summaries = [
                dict(value)
                for value in (change.get("stages") or change.get("stageSummaries") or [])
                if isinstance(value, dict)
            ]
            duplicate_manual_line_count = sum(
                int(value.get("duplicateManualLineCount") or 0) for value in stage_summaries
            )
            duplicate_manual_piece_qty = sum(
                int(value.get("duplicateManualPieceQty") or 0) for value in stage_summaries
            )
            status = str(self._row_value(row, "status", default="published") or "published")
            if status.lower() not in {"published", "success", "completed"}:
                classification = "failed"
            elif new_delivery_list and updated_count:
                classification = "new_updated"
            elif new_delivery_list:
                classification = "new"
            elif created_count or reactivated_count or updated_count or changed_list_ids:
                classification = "updated"
            else:
                classification = "no_changes"

            labels = {
                "new": "New",
                "updated": "Updated",
                "new_updated": "New + Updated",
                "failed": "Failed",
                "no_changes": "No Changes",
            }
            items.append(
                {
                    "id": int(self._row_value(row, "id", default=0) or 0),
                    "batchId": int(self._row_value(row, "id", default=0) or 0),
                    "runId": str(
                        change.get("runId")
                        or change.get("requestId")
                        or f"import-{int(self._row_value(row, 'id', default=0) or 0)}"
                    ),
                    "runStartedAt": str(change.get("runStartedAt") or ""),
                    "runCompletedAt": str(change.get("runCompletedAt") or self._row_value(row, "imported_at", "importedAt") or ""),
                    "deliveryDate": str(self._row_value(row, "delivery_date", "deliveryDate") or ""),
                    "sourceName": str(self._row_value(row, "source_name", "sourceName") or ""),
                    "rowCount": int(self._row_value(row, "row_count", "rowCount", default=0) or 0),
                    "totalQty": int(self._row_value(row, "total_qty", "totalQty", default=0) or 0),
                    "status": status,
                    "importedBy": str(self._row_value(row, "imported_by", "importedBy") or ""),
                    "importedAt": str(self._row_value(row, "imported_at", "importedAt") or ""),
                    "sourcePath": str(self._row_value(row, "source_path", "sourcePath") or ""),
                    "importKind": str(self._row_value(row, "import_kind", "importKind") or ""),
                    "classification": classification,
                    "classificationLabel": labels[classification],
                    "createdCount": created_count,
                    "newDeliveryList": new_delivery_list,
                    "reactivatedCount": reactivated_count,
                    "updatedCount": updated_count,
                    "newPieceQty": int(change.get("newPieceQty") or 0),
                    "addedPieceQty": int(change.get("addedPieceQty") or 0),
                    "updatedPieceQty": int(change.get("updatedPieceQty") or 0),
                    "changedPieceQty": int(change.get("changedPieceQty") or 0),
                    "removedLineCount": int(change.get("removedLineCount") or 0),
                    "removedPieceQty": int(change.get("removedPieceQty") or 0),
                    "duplicateManualLineCount": duplicate_manual_line_count,
                    "duplicateManualPieceQty": duplicate_manual_piece_qty,
                    "changedListIds": changed_list_ids,
                    "reactivatedListIds": [
                        str(value) for value in (change.get("reactivatedListIds") or []) if value
                    ],
                    "stageSummaries": stage_summaries,
                    "reason": str(change.get("reason") or ""),
                    "errors": [str(value) for value in (change.get("errors") or [])],
                    "changeSummary": change,
                }
            )
        return items

    def _archived_automation_import_items(self, maximum_runs: int = 2000) -> list[dict[str, Any]]:
        """Read immutable PowerShell run summaries so same-day history cannot disappear.

        The scanner database remains the detailed audit source. RunHistory fills the
        gap for unchanged checks, failures, and runs that happened while an older
        ProjectRoot was still configured.
        """
        clean_limit = max(1, min(int(maximum_runs or 2000), 10000))
        archive_cache = getattr(self, "_import_history_archive_cache", None)
        if not isinstance(archive_cache, dict):
            archive_cache = {}
            self._import_history_archive_cache = archive_cache
        cached = archive_cache.get(clean_limit)
        now_monotonic = time.monotonic()
        if cached and now_monotonic - cached[0] < 5.0:
            return [dict(item) for item in cached[1]]

        config = self._read_config(required=False, persist_repairs=False)
        if not config:
            return []
        history_dir = self._runtime_paths(config)["run_history_dir"]
        if not history_dir.is_dir():
            return []

        try:
            files = sorted(
                (path for path in history_dir.glob("run-*.json") if path.is_file()),
                key=lambda path: path.name,
                reverse=True,
            )[:clean_limit]
        except OSError:
            return []

        labels = {
            "new": "New",
            "updated": "Updated",
            "new_updated": "New + Updated",
            "failed": "Failed",
            "no_changes": "No Changes",
        }
        archived: list[dict[str, Any]] = []
        for run_index, path in enumerate(files):
            summary = self._read_json_file(path)
            if not summary:
                continue
            completed_at = str(summary.get("completedAt") or summary.get("startedAt") or "")
            started_at = str(summary.get("startedAt") or completed_at)
            run_id = str(
                summary.get("runId")
                or summary.get("requestId")
                or f"{str(summary.get('runOrigin') or 'automation')}:{started_at or completed_at}"
            )
            imported_by = str(
                summary.get("startedBy")
                or summary.get("createdBy")
                or "sql-auto-import"
            )
            raw_results = [
                item for item in (summary.get("importResults") or [])
                if isinstance(item, dict)
            ]
            if not raw_results:
                failed = summary.get("succeeded") is False
                checked_dates = [str(value) for value in (summary.get("checkedDates") or []) if value]
                raw_results = [
                    {
                        "classification": "failed" if failed else "no_changes",
                        "fileName": f"Delivery List {value[5:7]}-{value[8:10]}-{value[:4]}.xlsx" if len(value) >= 10 else "Automation check",
                        "deliveryDate": value,
                        "reason": str(summary.get("error") or summary.get("message") or "") if failed else "",
                        "errors": [str(summary.get("error") or summary.get("message") or "Automation failed")] if failed else [],
                    }
                    for value in checked_dates
                ]
            if not raw_results and summary.get("succeeded") is False:
                raw_results = [{
                    "classification": "failed",
                    "fileName": "Delivery-list automation run",
                    "deliveryDate": str(summary.get("dateFrom") or ""),
                    "reason": str(summary.get("error") or summary.get("message") or "Automation failed"),
                    "errors": [str(summary.get("error") or summary.get("message") or "Automation failed")],
                }]

            for item_index, item in enumerate(raw_results):
                item = self._normalize_import_change_summary(item)
                classification = str(item.get("classification") or "no_changes").lower()
                if classification not in labels:
                    classification = "no_changes"
                has_changes = any(
                    int(item.get(key) or 0)
                    for key in (
                        "createdCount", "reactivatedCount", "updatedCount",
                        "newPieceQty", "addedPieceQty", "updatedPieceQty",
                        "changedPieceQty", "removedLineCount", "removedPieceQty",
                    )
                )
                if classification != "failed":
                    if item.get("newDeliveryList") and int(item.get("updatedCount") or 0):
                        classification = "new_updated"
                    elif item.get("newDeliveryList"):
                        classification = "new"
                    elif has_changes:
                        classification = "updated"
                    else:
                        classification = "no_changes"
                list_ids = [
                    str(value)
                    for value in (item.get("listIds") or item.get("changedListIds") or [])
                    if value
                ]
                raw_changed_list_ids = item.get("changedListIds")
                if raw_changed_list_ids is None and classification != "no_changes":
                    raw_changed_list_ids = item.get("listIds") or []
                changed_list_ids = [str(value) for value in (raw_changed_list_ids or []) if value]
                archived.append({
                    "id": -1000000 - (run_index * 1000) - item_index,
                    "batchId": -1000000 - (run_index * 1000) - item_index,
                    "runId": str(item.get("runId") or run_id),
                    "runStartedAt": str(item.get("runStartedAt") or started_at),
                    "runCompletedAt": completed_at,
                    "deliveryDate": str(item.get("deliveryDate") or "").strip(),
                    "sourceName": str(item.get("fileName") or item.get("sourceName") or "Automation check").strip(),
                    "rowCount": int(item.get("rowCount") or 0),
                    "totalQty": int(item.get("totalQty") or 0),
                    "status": "failed" if classification == "failed" else "automation_archive",
                    "importedBy": imported_by,
                    "importedAt": completed_at,
                    "checkedAt": completed_at,
                    "updatedAt": completed_at,
                    "sourcePath": str(item.get("sourcePath") or ""),
                    "importKind": "automation_archive",
                    "classification": classification,
                    "classificationLabel": labels[classification],
                    "createdCount": int(item.get("createdCount") or 0),
                    "newDeliveryList": bool(item.get("newDeliveryList")),
                    "reactivatedCount": int(item.get("reactivatedCount") or 0),
                    "updatedCount": int(item.get("updatedCount") or 0),
                    "newPieceQty": int(item.get("newPieceQty") or 0),
                    "addedPieceQty": int(item.get("addedPieceQty") or 0),
                    "updatedPieceQty": int(item.get("updatedPieceQty") or 0),
                    "changedPieceQty": int(item.get("changedPieceQty") or 0),
                    "removedLineCount": int(item.get("removedLineCount") or 0),
                    "removedPieceQty": int(item.get("removedPieceQty") or 0),
                    "duplicateManualLineCount": int(item.get("duplicateManualLineCount") or 0),
                    "duplicateManualPieceQty": int(item.get("duplicateManualPieceQty") or 0),
                    "listIds": list_ids,
                    "changedListIds": changed_list_ids,
                    "reactivatedListIds": [
                        str(value) for value in (item.get("reactivatedListIds") or []) if value
                    ],
                    "stageSummaries": [
                        {
                            **dict(value),
                            "importedAt": completed_at,
                            "checkedAt": completed_at,
                            "updatedAt": completed_at,
                        }
                        for value in (item.get("stageSummaries") or item.get("stages") or [])
                        if isinstance(value, dict)
                    ],
                    "reason": str(item.get("reason") or ""),
                    "errors": [str(value) for value in (item.get("errors") or [])],
                    "changeSummary": item,
                    "historySource": "run_archive",
                })
        archive_cache[clean_limit] = (now_monotonic, [dict(item) for item in archived])
        return archived

    def _latest_automation_import_items(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Normalize the newest import-capable manual or scheduled run.

        This is the authoritative source for the Delivery List Management card.
        It deliberately reads the complete newest run instead of the paginated
        audit-history result so every checked workbook receives the same current
        run timestamp and classification.
        """
        config = self._read_config(required=False, persist_repairs=False)
        if not config:
            return [], {}
        runtime_paths = self._runtime_paths(config)
        completed_summaries = [
            summary
            for summary in (
                self._read_json_file(runtime_paths["gui_run"]),
                self._read_json_file(runtime_paths["last_run"]),
            )
            if summary and str(summary.get("completedAt") or "").strip()
        ]
        if not completed_summaries:
            return [], {}

        def is_import_capable(summary: dict[str, Any]) -> bool:
            action = str(summary.get("runAction") or summary.get("action") or "").strip().lower()
            return action in {
                "folderimportonly",
                "sqlexportandimport",
                "folder-import-only",
                "sql-export-and-import",
            } or bool(summary.get("importResults"))

        import_summaries = [summary for summary in completed_summaries if is_import_capable(summary)]
        latest_summary = max(
            import_summaries or completed_summaries,
            key=lambda summary: str(summary.get("completedAt") or ""),
        )
        imported_at = str(latest_summary.get("completedAt") or latest_summary.get("startedAt") or "")
        imported_by = str(
            latest_summary.get("startedBy")
            or latest_summary.get("createdBy")
            or "sql-auto-import"
        )
        labels = {
            "new": "New",
            "updated": "Updated",
            "new_updated": "New + Updated",
            "failed": "Failed",
            "no_changes": "No Changes",
        }

        raw_results = [
            item for item in (latest_summary.get("importResults") or [])
            if isinstance(item, dict)
        ]

        # Older partially completed runs could write last-import-result.json before
        # last-run.json was finalized. Use it only when it belongs to the same
        # completed run window; this avoids resurfacing an unrelated stale result.
        if not raw_results:
            persisted_result = self._read_json_file(runtime_paths["last_import_result"])
            result_path = runtime_paths["last_import_result"]
            try:
                result_modified = datetime.fromtimestamp(result_path.stat().st_mtime, tz=timezone.utc)
                completed = datetime.fromisoformat(imported_at.replace("Z", "+00:00"))
                age_seconds = abs((completed - result_modified).total_seconds())
            except (OSError, ValueError, TypeError):
                age_seconds = 10**9
            if age_seconds <= 900:
                raw_results = [
                    item for item in (persisted_result.get("files") or [])
                    if isinstance(item, dict)
                ]

        # A run can fail before the folder importer has per-file results. Still
        # expose the failure in the same Delivery List Management result format.
        if not raw_results and latest_summary.get("succeeded") is False:
            raw_results = [{
                "classification": "failed",
                "fileName": "Delivery-list automation run",
                "deliveryDate": str(latest_summary.get("dateFrom") or ""),
                "reason": str(latest_summary.get("error") or latest_summary.get("message") or "Automation failed"),
                "errors": [str(latest_summary.get("error") or latest_summary.get("message") or "Automation failed")],
            }]

        run_started_at = str(latest_summary.get("startedAt") or "")
        run_id = str(
            latest_summary.get("requestId")
            or latest_summary.get("runId")
            or f"{str(latest_summary.get('runOrigin') or 'automation')}:{run_started_at or imported_at}"
        )
        items: list[dict[str, Any]] = []
        for index, item in enumerate(raw_results):
            item = self._normalize_import_change_summary(item)
            classification = str(item.get("classification") or "no_changes").lower()
            if classification not in labels:
                classification = "no_changes"
            has_changes = any(
                int(item.get(key) or 0)
                for key in (
                    "createdCount", "reactivatedCount", "updatedCount",
                    "newPieceQty", "addedPieceQty", "updatedPieceQty",
                    "changedPieceQty", "removedLineCount", "removedPieceQty",
                )
            )
            if classification != "failed":
                if item.get("newDeliveryList") and int(item.get("updatedCount") or 0):
                    classification = "new_updated"
                elif item.get("newDeliveryList"):
                    classification = "new"
                elif has_changes:
                    classification = "updated"
                else:
                    classification = "no_changes"
            list_ids = [
                str(value)
                for value in (item.get("listIds") or item.get("changedListIds") or [])
                if value
            ]
            raw_changed_list_ids = item.get("changedListIds")
            if raw_changed_list_ids is None and classification != "no_changes":
                raw_changed_list_ids = item.get("listIds") or []
            changed_list_ids = [str(value) for value in (raw_changed_list_ids or []) if value]
            items.append(
                {
                    "id": -1 - index,
                    "batchId": -1 - index,
                    "runId": str(item.get("runId") or run_id),
                    "runStartedAt": str(item.get("runStartedAt") or run_started_at),
                    "runCompletedAt": imported_at,
                    "deliveryDate": str(item.get("deliveryDate") or "").strip(),
                    "sourceName": str(item.get("fileName") or item.get("sourceName") or "").strip(),
                    "rowCount": int(item.get("rowCount") or 0),
                    "totalQty": int(item.get("totalQty") or 0),
                    "status": "failed" if classification == "failed" else "automation_result",
                    "importedBy": imported_by,
                    "importedAt": imported_at,
                    "checkedAt": imported_at,
                    "updatedAt": imported_at,
                    "sourcePath": str(item.get("sourcePath") or ""),
                    "importKind": "automation",
                    "classification": classification,
                    "classificationLabel": labels[classification],
                    "createdCount": int(item.get("createdCount") or 0),
                    "newDeliveryList": bool(item.get("newDeliveryList")),
                    "reactivatedCount": int(item.get("reactivatedCount") or 0),
                    "updatedCount": int(item.get("updatedCount") or 0),
                    "newPieceQty": int(item.get("newPieceQty") or 0),
                    "addedPieceQty": int(item.get("addedPieceQty") or 0),
                    "updatedPieceQty": int(item.get("updatedPieceQty") or 0),
                    "changedPieceQty": int(item.get("changedPieceQty") or 0),
                    "removedLineCount": int(item.get("removedLineCount") or 0),
                    "removedPieceQty": int(item.get("removedPieceQty") or 0),
                    "duplicateManualLineCount": int(item.get("duplicateManualLineCount") or 0),
                    "duplicateManualPieceQty": int(item.get("duplicateManualPieceQty") or 0),
                    "listIds": list_ids,
                    "changedListIds": changed_list_ids,
                    "reactivatedListIds": [
                        str(value) for value in (item.get("reactivatedListIds") or []) if value
                    ],
                    "stageSummaries": [
                        {
                            **dict(value),
                            "importedAt": imported_at,
                            "checkedAt": imported_at,
                            "updatedAt": imported_at,
                        }
                        for value in (item.get("stageSummaries") or item.get("stages") or [])
                        if isinstance(value, dict)
                    ],
                    "reason": str(item.get("reason") or ""),
                    "errors": [str(value) for value in (item.get("errors") or [])],
                    "changeSummary": item,
                }
            )
        return items, latest_summary

    @staticmethod
    def _history_search_text(item: dict[str, Any]) -> str:
        """Build a route-aware search document for one import-history result."""
        delivery_date = str(item.get("deliveryDate") or "")[:10]
        display_date = ""
        try:
            parsed_date = datetime.strptime(delivery_date, "%Y-%m-%d")
            display_date = f"{parsed_date.month}/{parsed_date.day}/{parsed_date.year}"
        except ValueError:
            display_date = delivery_date

        activity_text = str(
            item.get("runStartedAt")
            or item.get("runCompletedAt")
            or item.get("importedAt")
            or item.get("checkedAt")
            or ""
        )
        activity_date = activity_text[:10]
        activity_display = ""
        try:
            parsed_activity = datetime.fromisoformat(activity_text.replace("Z", "+00:00"))
            activity_display = f"{parsed_activity.month}/{parsed_activity.day}/{parsed_activity.year}"
        except ValueError:
            activity_display = activity_date

        stage_parts: list[str] = []
        route_aliases: set[str] = set()
        for stage in item.get("stageSummaries") or []:
            if not isinstance(stage, dict):
                continue
            stage_text = " ".join(
                str(stage.get(key) or "")
                for key in ("label", "stage", "scanner", "listLabel", "listId", "route", "routeCode")
            )
            stage_parts.append(stage_text)
            normalized = stage_text.lower()
            if "outbound" in normalized or "staging" in normalized or "airport" in normalized:
                route_aliases.update({"airport", "airport road", "airport rd", "all orders"})
            if "indian trail" in normalized or "receiv" in normalized or " it " in f" {normalized} ":
                route_aliases.update({"indian trail", "it"})
            if "greenville" in normalized or "gnv" in normalized:
                route_aliases.update({"greenville", "gnv"})
            if "customer pickup" in normalized or "cpu" in normalized:
                route_aliases.update({"cpu", "customer pickup"})
            if "deliver to customer" in normalized or "dtc" in normalized:
                route_aliases.update({"dtc", "deliver to customer"})

        return " ".join(
            [
                delivery_date,
                display_date,
                activity_date,
                activity_display,
                str(item.get("sourceName") or ""),
                str(item.get("fileName") or ""),
                str(item.get("importedBy") or ""),
                str(item.get("classification") or ""),
                str(item.get("classificationLabel") or ""),
                str(item.get("reason") or ""),
                " ".join(str(value) for value in (item.get("errors") or [])),
                " ".join(str(value) for value in (item.get("changedListIds") or [])),
                " ".join(stage_parts),
                " ".join(sorted(route_aliases)),
            ]
        ).lower()

    def get_latest_import_result(self) -> dict[str, Any]:
        """Return the newest import run without republishing the full list catalog.

        The Admin UI already maintains delivery-list state through the dedicated
        ``/api/delivery-lists`` heartbeat. Fetching the same catalog here made
        every Automation Control Center refresh perform an unrelated full-list
        query and then repaint catalog consumers across the application.
        """
        latest_items, latest_summary = self._latest_automation_import_items()

        completed_at = str(latest_summary.get("completedAt") or latest_summary.get("startedAt") or "")
        run_action = str(latest_summary.get("runAction") or latest_summary.get("action") or "")
        run_key = "|".join([
            completed_at,
            run_action,
            str(latest_summary.get("succeeded")),
            str(len(latest_items)),
        ])
        return {
            "ok": True,
            "latestImportResults": latest_items,
            "recentImports": latest_items,
            "lists": [],
            "lastCheckedAt": completed_at,
            "latestRunKey": run_key,
            "latestRun": {
                "runId": str(
                    (latest_items[0].get("runId") if latest_items else "")
                    or latest_summary.get("requestId")
                    or latest_summary.get("runId")
                    or f"{str(latest_summary.get('runOrigin') or 'automation')}:{str(latest_summary.get('startedAt') or completed_at)}"
                ),
                "completedAt": completed_at,
                "startedAt": str(latest_summary.get("startedAt") or ""),
                "succeeded": latest_summary.get("succeeded"),
                "mode": str(latest_summary.get("mode") or ""),
                "runAction": run_action,
                "error": str(latest_summary.get("error") or ""),
                "resultCount": len(latest_items),
                "awRejectSync": dict(latest_summary.get("awRejectSync") or {}),
            },
        }

    def get_import_history(
        self,
        page: int = 1,
        page_size: int = 20,
        query: str = "",
        classification: str = "",
        date_from: str = "",
        date_to: str = "",
        page_mode: str = "rows",
    ) -> dict[str, Any]:
        """Return searchable, filterable, newest-first import audit history.

        The maintained Automation Control Center requests ``control_center``
        pagination. Unfiltered browsing uses fixed three-week operating windows;
        filtered browsing keeps up to 25 matching activity dates together per
        page so a busy import day is never split. Legacy callers retain the
        existing row-count and one-business-week modes unless they opt in.
        """
        clean_page = max(1, int(page or 1))
        clean_page_size = max(10, min(int(page_size or 20), 2000))
        clean_page_mode = str(page_mode or "rows").strip().lower().replace("-", "_")
        if clean_page_mode not in {"rows", "business_week", "control_center"}:
            raise ValueError("Choose a valid import-history page mode")
        clean_query = str(query or "").strip().lower()[:200]
        query_terms = [term for term in clean_query.split() if term]
        clean_classification = str(classification or "").strip().lower()
        allowed_classifications = {"", "new", "updated", "new_updated", "no_changes", "failed"}
        if clean_classification not in allowed_classifications:
            raise ValueError("Choose a valid import-history status filter")
        clean_date_from = clean_date(date_from, "History start date")
        clean_date_to = clean_date(date_to, "History end date")
        if clean_date_from and clean_date_to and clean_date_from > clean_date_to:
            raise ValueError("History start date cannot be after the end date")

        filters_requested = bool(clean_query or clean_classification or clean_date_from or clean_date_to)
        # The Control Center renders a three-week operating window, so parsing
        # thousands of older database/import archive records on every ordinary
        # open only adds latency. Keep the normal browse path bounded; explicit
        # search/filter requests retain the deeper audit scan.
        database_limit = 5000 if filters_requested or clean_page_mode != "control_center" else 1500
        archive_limit = 2000 if filters_requested or clean_page_mode != "control_center" else 250
        try:
            database_items = self._database_import_history_items(maximum_rows=database_limit)
        except TypeError:
            # Compatibility for lightweight test doubles / older controller hooks.
            database_items = self._database_import_history_items()
        latest_items, latest_summary = self._latest_automation_import_items()
        try:
            archived_items = self._archived_automation_import_items(maximum_runs=archive_limit)
        except TypeError:
            # Compatibility for lightweight test doubles / older controller hooks.
            archived_items = self._archived_automation_import_items()
        runtime_items = [*latest_items, *archived_items]

        def parsed_timestamp(value: Any) -> datetime | None:
            """Return an aware UTC timestamp so mixed local/UTC history can be compared safely."""
            text_value = str(value or "").strip()
            if not text_value:
                return None
            try:
                parsed = datetime.fromisoformat(text_value.replace("Z", "+00:00"))
            except ValueError:
                return None
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)

        def history_activity_date(item: dict[str, Any]) -> date:
            """Return the local activity date used by both filters and week paging.

            Import History is organized by when the updater/import actually ran,
            so its From/Through controls must filter that same timeline rather
            than the delivery date contained inside the workbook.
            """
            timestamp = (
                item.get("runStartedAt")
                or item.get("runCompletedAt")
                or item.get("importedAt")
                or item.get("checkedAt")
                or item.get("updatedAt")
            )
            parsed = parsed_timestamp(timestamp)
            if parsed is not None:
                return parsed.astimezone().date()
            fallback_text = str(timestamp or item.get("deliveryDate") or "")[:10]
            try:
                return date.fromisoformat(fallback_text)
            except ValueError:
                return date.min

        filter_start = date.fromisoformat(clean_date_from) if clean_date_from else None
        filter_end = date.fromisoformat(clean_date_to) if clean_date_to else None

        def import_signature(item: dict[str, Any]) -> tuple[Any, ...]:
            return (
                str(item.get("deliveryDate") or ""),
                str(item.get("sourceName") or "").strip().lower(),
                str(item.get("classification") or "no_changes").lower(),
                int(item.get("rowCount") or 0),
                int(item.get("totalQty") or 0),
                int(item.get("createdCount") or 0),
                int(item.get("updatedCount") or 0),
                int(item.get("newPieceQty") or 0),
                int(item.get("addedPieceQty") or 0),
                int(item.get("updatedPieceQty") or 0),
                int(item.get("changedPieceQty") or 0),
                int(item.get("removedLineCount") or 0),
                int(item.get("removedPieceQty") or 0),
            )

        # Database import rows are the durable history. Add a runtime item only
        # when no corresponding durable row exists. Matching by exact result
        # signature plus the closest timestamp prevents the newest run from
        # appearing twice without hiding earlier same-day imports of the same file.
        unmatched_latest: list[dict[str, Any]] = []
        database_by_signature: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
        for database_item in database_items:
            database_by_signature.setdefault(import_signature(database_item), []).append(database_item)
        for latest_item in runtime_items:
            candidates = database_by_signature.get(import_signature(latest_item), [])
            latest_run_id = str(latest_item.get("runId") or "").strip()
            meaningful_latest_run_id = latest_run_id and not latest_run_id.startswith("import-")

            if meaningful_latest_run_id:
                exact_run_match = any(
                    str(candidate.get("runId") or "").strip() == latest_run_id
                    for candidate in candidates
                )
                if exact_run_match:
                    continue

                # A different stable run ID is a different import, even when it
                # checked the same workbook and produced the same totals. Do not
                # let a nearby automated run hide a later manual run.
                candidate_run_ids = {
                    str(candidate.get("runId") or "").strip()
                    for candidate in candidates
                    if str(candidate.get("runId") or "").strip()
                    and not str(candidate.get("runId") or "").strip().startswith("import-")
                }
                if candidate_run_ids:
                    unmatched_latest.append(latest_item)
                    continue

            latest_time = parsed_timestamp(
                latest_item.get("runCompletedAt")
                or latest_item.get("importedAt")
                or latest_item.get("checkedAt")
            )
            closest_seconds: float | None = None
            for candidate in candidates:
                candidate_time = parsed_timestamp(candidate.get("importedAt"))
                if latest_time is None or candidate_time is None:
                    if str(candidate.get("importedAt") or "") == str(latest_item.get("importedAt") or ""):
                        closest_seconds = 0.0
                        break
                    continue
                seconds = abs((latest_time - candidate_time).total_seconds())
                if closest_seconds is None or seconds < closest_seconds:
                    closest_seconds = seconds
            if closest_seconds is None or closest_seconds > 15 * 60:
                unmatched_latest.append(latest_item)

        merged = unmatched_latest + database_items

        # Runtime summaries, immutable archives, and database rows can all
        # describe the same file result. Canonicalize by run start + date + file
        # before rendering. This preserves distinct runs while eliminating the
        # 9:30:36 / 9:30:38 double-card pattern from one execution.
        deduplicated: dict[tuple[str, str, str], dict[str, Any]] = {}
        unkeyed: list[dict[str, Any]] = []
        for item in merged:
            started_at = str(item.get("runStartedAt") or "").strip()
            run_id = str(item.get("runId") or "").strip()
            source_name = str(item.get("sourceName") or "").strip().lower()
            delivery_date = str(item.get("deliveryDate") or "").strip()
            run_identity = started_at or (run_id if run_id and not run_id.startswith("import-") else "")
            if not run_identity:
                unkeyed.append(item)
                continue
            key = (run_identity, delivery_date, source_name)
            current = deduplicated.get(key)
            if current is None:
                deduplicated[key] = item
                continue
            current_is_database = int(current.get("id") or 0) > 0
            incoming_is_database = int(item.get("id") or 0) > 0
            if incoming_is_database and not current_is_database:
                deduplicated[key] = item
                continue
            if incoming_is_database == current_is_database:
                current_detail = len(current.get("stageSummaries") or []) + len(current.get("changedListIds") or [])
                incoming_detail = len(item.get("stageSummaries") or []) + len(item.get("changedListIds") or [])
                if incoming_detail > current_detail:
                    deduplicated[key] = item

        merged = [*deduplicated.values(), *unkeyed]
        merged.sort(
            key=lambda item: (
                str(item.get("runStartedAt") or item.get("importedAt") or ""),
                int(item.get("id") or 0),
            ),
            reverse=True,
        )

        filtered: list[dict[str, Any]] = []
        for item in merged:
            item_classification = str(item.get("classification") or "no_changes").lower()
            activity_date = history_activity_date(item)
            if clean_classification and item_classification != clean_classification:
                continue
            if (filter_start or filter_end) and activity_date == date.min:
                continue
            if filter_start and activity_date < filter_start:
                continue
            if filter_end and activity_date > filter_end:
                continue
            if query_terms:
                search_text = self._history_search_text(item)
                if not all(term in search_text for term in query_terms):
                    continue
            filtered.append(item)

        total_count = len(filtered)
        week_start_text = ""
        week_end_text = ""
        page_start_text = ""
        page_end_text = ""
        page_date_count = 0
        page_unit = "rows"
        filters_active = bool(clean_query or clean_classification or clean_date_from or clean_date_to)

        if clean_page_mode == "control_center":
            if filters_active:
                # Filtered history is paged by distinct activity date, not rows.
                # Every import result for the selected dates stays on the same
                # page; only after 25 matching dates do we create another page.
                activity_dates = sorted(
                    {history_activity_date(item) for item in filtered if history_activity_date(item) != date.min},
                    reverse=True,
                )
                dates_per_page = 25
                total_pages = max(1, (len(activity_dates) + dates_per_page - 1) // dates_per_page)
                clean_page = min(clean_page, total_pages)
                start = (clean_page - 1) * dates_per_page
                selected_dates = activity_dates[start:start + dates_per_page]
                selected_date_set = set(selected_dates)
                page_items = [item for item in filtered if history_activity_date(item) in selected_date_set]
                page_date_count = len(selected_dates)
                clean_page_size = dates_per_page
                page_unit = "dates"
                if selected_dates:
                    page_start_text = min(selected_dates).isoformat()
                    page_end_text = max(selected_dates).isoformat()
                    week_start_text = page_start_text
                    week_end_text = page_end_text
            else:
                # Normal browsing is anchored around the operating calendar:
                # page 1 = Next Week + This Week + Previous Week. Each later
                # page moves backward exactly three business weeks.
                today = date.today()
                current_week_start = today - timedelta(days=today.weekday())
                history_weeks = [
                    activity - timedelta(days=activity.weekday())
                    for item in filtered
                    if (activity := history_activity_date(item)) != date.min
                ]
                if history_weeks:
                    oldest_week = min(history_weeks)
                    oldest_age_weeks = max(0, (current_week_start - oldest_week).days // 7)
                    total_pages = 1 if oldest_age_weeks <= 1 else 1 + ((oldest_age_weeks - 2) // 3 + 1)
                else:
                    total_pages = 1
                clean_page = min(clean_page, total_pages)

                if clean_page == 1:
                    window_start = current_week_start - timedelta(days=7)
                    window_end = current_week_start + timedelta(days=11)
                else:
                    newest_age_weeks = 2 + ((clean_page - 2) * 3)
                    oldest_age_weeks = newest_age_weeks + 2
                    window_start = current_week_start - timedelta(days=oldest_age_weeks * 7)
                    window_end = current_week_start - timedelta(days=newest_age_weeks * 7) + timedelta(days=4)

                page_items = [
                    item for item in filtered
                    if window_start <= history_activity_date(item) <= window_end
                ]
                page_date_count = len({history_activity_date(item) for item in page_items if history_activity_date(item) != date.min})
                page_unit = "weeks"
                page_start_text = window_start.isoformat()
                page_end_text = window_end.isoformat()
                week_start_text = page_start_text
                week_end_text = page_end_text
        elif clean_page_mode == "business_week":
            # Legacy one-week mode: keep every result from a Monday-Friday
            # operating week together, including multiple runs on the same day.
            week_groups: dict[date, list[dict[str, Any]]] = {}
            for item in filtered:
                activity_date = history_activity_date(item)
                week_start = activity_date - timedelta(days=activity_date.weekday())
                week_groups.setdefault(week_start, []).append(item)

            week_keys = sorted(week_groups, reverse=True)
            total_pages = max(1, len(week_keys))
            clean_page = min(clean_page, total_pages)
            if week_keys:
                selected_week_start = week_keys[clean_page - 1]
                page_items = week_groups[selected_week_start]
                week_start_text = selected_week_start.isoformat()
                week_end_text = (selected_week_start + timedelta(days=4)).isoformat()
                page_start_text = week_start_text
                page_end_text = week_end_text
                page_date_count = len({history_activity_date(item) for item in page_items})
                page_unit = "weeks"
            else:
                page_items = []
        else:
            total_pages = max(1, (total_count + clean_page_size - 1) // clean_page_size)
            clean_page = min(clean_page, total_pages)
            start = (clean_page - 1) * clean_page_size
            page_items = filtered[start:start + clean_page_size]
        last_checked_at = str(
            latest_summary.get("completedAt") or latest_summary.get("startedAt") or ""
        )

        # Import History is audit data, not a delivery-list catalog refresh. The
        # Control Center used to fetch every delivery-list summary here and then
        # force-publish that catalog in the browser, which could trigger a large
        # app-wide repaint just from opening the History tab. Keep the legacy
        # payload for older row-mode callers, but omit it from the maintained
        # Control Center path; its dedicated catalog heartbeat handles freshness.
        lists: list[dict[str, Any]] = []
        if clean_page_mode != "control_center":
            store = self.scanner_store
            getter = getattr(store, "get_delivery_lists", None) if store is not None else None
            if callable(getter):
                try:
                    lists = list(getter() or [])
                except TypeError:
                    lists = list(getter(None) or [])
                except Exception:
                    lists = []

        return {
            "ok": True,
            "recentImports": page_items,
            "imports": page_items,
            "latestImportResults": latest_items,
            "lists": lists,
            "lastCheckedAt": last_checked_at,
            "page": clean_page,
            "pageSize": clean_page_size,
            "pageItemCount": len(page_items),
            "pageMode": clean_page_mode,
            "pageUnit": page_unit,
            "pageStart": page_start_text,
            "pageEnd": page_end_text,
            "pageDateCount": page_date_count,
            "filteredPaging": filters_active if clean_page_mode == "control_center" else False,
            "weekStart": week_start_text,
            "weekEnd": week_end_text,
            "totalCount": total_count,
            "totalPages": total_pages,
            "filters": {
                "query": str(query or "").strip()[:200],
                "classification": clean_classification,
                "dateFrom": clean_date_from,
                "dateTo": clean_date_to,
                "dateBasis": "import_activity",
            },
            "latestRun": {
                "completedAt": last_checked_at,
                "succeeded": latest_summary.get("succeeded"),
                "mode": str(latest_summary.get("mode") or ""),
                "runAction": str(latest_summary.get("runAction") or latest_summary.get("action") or ""),
            },
        }

    def get_recent_imports(self, limit: int = 20) -> dict[str, Any]:
        """Backward-compatible first page used by older v109-v115 clients."""
        return self.get_import_history(page=1, page_size=limit)

    def save_settings(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        config = self._read_config(required=True)
        automation_mode = str(data.get("automationMode") or "").strip().lower()
        if automation_mode not in AUTOMATION_MODES:
            raise ValueError("Choose a valid automation mode")
        full_time = str(data.get("fullRefreshTime") or "17:00").strip()
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", full_time):
            raise ValueError("Full refresh time must use 24-hour HH:MM format")
        destination = str(data.get("destinationFolder") or config.get("DestinationFolder") or "").strip()
        if not destination:
            raise ValueError("Temp Delivery Lists folder is required")

        config.setdefault("Automation", {})["Mode"] = automation_mode
        if "scheduleEnabled" in data:
            config["Automation"]["ScheduleEnabled"] = bool(data.get("scheduleEnabled"))
        config["Automation"]["AllowWebGuiControl"] = True
        schedule = config.setdefault("Schedule", {})
        schedule["IncrementalIntervalMinutes"] = bounded_int(data.get("intervalMinutes", 60), 5, 1440, "Interval")
        schedule["IncrementalPastDays"] = bounded_int(data.get("incrementalPastDays", 2), 0, 365, "Incremental past days")
        schedule["IncrementalFutureDays"] = bounded_int(data.get("incrementalFutureDays", 14), 0, 365, "Incremental future days")
        schedule["FullPastDays"] = bounded_int(data.get("fullPastDays", 7), 0, 365, "Full past days")
        schedule["FullFutureDays"] = bounded_int(data.get("fullFutureDays", 90), 0, 365, "Full future days")
        schedule["FullRefreshTime"] = full_time
        config["DestinationFolder"] = destination
        notifications = config.setdefault("Notifications", {})
        notifications["Enabled"] = bool(data.get("notificationsEnabled", True))
        notifications["NotifyOnNoChanges"] = bool(data.get("notifyOnNoChanges", True))
        reject_sync = config.setdefault("RejectSync", {})
        reject_sync["Enabled"] = bool(data.get("rejectSyncEnabled", reject_sync.get("Enabled", True)))
        reject_sync["IncrementalPastDays"] = bounded_int(
            data.get("rejectIncrementalPastDays", reject_sync.get("IncrementalPastDays", 30)),
            1,
            3650,
            "A+W reject incremental lookback",
        )
        reject_sync["FullPastDays"] = bounded_int(
            data.get("rejectFullPastDays", reject_sync.get("FullPastDays", 365)),
            1,
            3650,
            "A+W reject full lookback",
        )
        if reject_sync["FullPastDays"] < reject_sync["IncrementalPastDays"]:
            raise ValueError("A+W reject full lookback cannot be shorter than the incremental lookback")
        production_sync = config.setdefault("ProductionSync", {})
        production_sync["Enabled"] = bool(data.get("productionSyncEnabled", production_sync.get("Enabled", True)))
        production_sync["ScheduledEnabled"] = bool(data.get("productionScheduledEnabled", production_sync.get("ScheduledEnabled", True)))
        production_sync["IncludeCuttingBookings"] = bool(data.get("productionIncludeCuttingBookings", production_sync.get("IncludeCuttingBookings", True)))
        production_sync["CuttingBookingLookbackDays"] = bounded_int(
            data.get("productionCuttingBookingLookbackDays", production_sync.get("CuttingBookingLookbackDays", 120)),
            14, 730, "A+W Cutting booking lookback",
        )
        production_sync["QueryBatchSize"] = bounded_int(
            data.get("productionQueryBatchSize", production_sync.get("QueryBatchSize", 60)),
            10, 150, "A+W production SQL batch size",
        )
        production_sync["QueryTimeoutSeconds"] = bounded_int(
            data.get("productionQueryTimeoutSeconds", production_sync.get("QueryTimeoutSeconds", 75)),
            20, 300, "A+W production SQL timeout",
        )
        production_sync["GenerationHistoryDepth"] = bounded_int(
            data.get("productionGenerationHistoryDepth", production_sync.get("GenerationHistoryDepth", 4)),
            1, 12, "A+W production generation history depth",
        )
        production_sync["CrystalReportFile"] = "Prodman_CuttingLabel_Optimisation.rpt"
        production_sync["CrystalReportPrintPointId"] = 846
        config["Version"] = "v121"
        config.setdefault("Import", {})["Mode"] = "direct-store"
        self._write_config(config)
        dashboard = self.get_dashboard()
        dashboard["message"] = f"Automation settings saved by {user}."
        return dashboard

    def _write_gui_status(self, config: dict[str, Any], status: dict[str, Any]) -> None:
        path = self._runtime_paths(config)["gui_run"]
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)

    def start_run(self, data: dict[str, Any], user: str) -> dict[str, Any]:
        config = self._read_config(required=True)
        paths = self._runtime_paths(config)
        action = str(data.get("action") or "").strip().lower()
        if action not in RUN_ACTIONS:
            raise ValueError("Choose folder import, SQL export only, or direct A+W synchronization")
        range_mode = str(data.get("rangeMode") or "custom").strip().lower()
        if range_mode not in {"one-date", "custom", "incremental", "full"}:
            raise ValueError("Choose a valid date range mode")
        if action == "reject-sync-only" and range_mode not in {"incremental", "full"}:
            raise ValueError("A+W reject checks use either the Normal or Full reject lookback window")
        date_from = clean_date(data.get("dateFrom"), "From date", required=range_mode in {"one-date", "custom"})
        date_to = clean_date(data.get("dateTo"), "Through date", required=False)
        if range_mode == "one-date":
            date_to = date_from
        if date_from and date_to and date_to < date_from:
            raise ValueError("Through date cannot be earlier than from date")

        if range_mode == "incremental":
            run_mode = "Incremental"
        elif range_mode == "full":
            run_mode = "Full"
        else:
            run_mode = "Custom"

        # Reject overlap with both browser-started and Task Scheduler runs before
        # replacing installed helper files. PowerShell repeats this check after
        # launch to close the unavoidable race between inspection and lock acquire.
        with self._state_lock:
            if self._active_process and self._active_process.poll() is None:
                raise RuntimeError("Another browser-started delivery-list update is already active")
        if self._runtime_lock_busy(config):
            raise RuntimeError(
                "A scheduled delivery-list update is currently running. Wait for it to finish, then start the manual update again."
            )

        synchronized_files = self._sync_runtime_scripts(config)
        self._runtime_sync_status = {
            "attempted": True,
            "ok": True,
            "deferred": False,
            "synchronizedFiles": synchronized_files,
            "error": "",
        }
        if not paths["runner"].is_file():
            raise FileNotFoundError("Automation runner could not be synchronized to the runtime folder.")
        if self._runtime_lock_busy(config):
            raise RuntimeError(
                "A scheduled delivery-list update started while the manual request was being prepared. Wait for it to finish and try again."
            )

        with self._state_lock:
            if self._active_process and self._active_process.poll() is None:
                raise RuntimeError("Another browser-started delivery-list update is already active")
            task_id = uuid.uuid4().hex[:12]
            log_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            log_path = paths["logs_dir"] / f"web-gui-{log_stamp}-{task_id}.log"
            summary_path = paths["gui_summary"]
            log_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                summary_path.unlink()
            except FileNotFoundError:
                pass

            synchronized_text = ", ".join(synchronized_files) if synchronized_files else "none (runtime already current)"
            self._append_run_log_line(
                log_path,
                (
                    f"Web request accepted. User={user} Action={action} RangeMode={range_mode} "
                    f"DateFrom={date_from or 'automatic'} DateTo={date_to or 'automatic'} RunMode={run_mode}."
                ),
                "INFO",
            )
            self._append_run_log_line(log_path, "Browser-run overlap and scheduled-run lock preflight passed.")
            self._append_run_log_line(
                log_path,
                f"Installed runtime synchronization completed. UpdatedFiles={synchronized_text}.",
            )
            self._append_run_log_line(
                log_path,
                f"Run files prepared. Runner={paths['runner']} Summary={summary_path} Log={log_path}.",
            )
            status = {
                "taskId": task_id,
                "running": True,
                "action": action,
                "rangeMode": range_mode,
                "dateFrom": date_from,
                "dateTo": date_to,
                "startedAt": utc_now(),
                "startedBy": user,
                "message": "Delivery-list automation started.",
                "currentStep": "Starting PowerShell automation runner...",
                "commandOutput": "",
                "outputLineCount": 0,
                "logPath": str(log_path),
                "summaryPath": str(summary_path),
                "runOrigin": "manual",
                "runnerPath": str(paths["runner"]),
                "synchronizedRuntimeFiles": synchronized_files,
            }
            self._active_status = status
            self._write_gui_status(config, status)

            command = [
                self._power_shell(config),
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(paths["runner"]),
                "-Mode",
                run_mode,
                "-RunAction",
                RUN_ACTIONS[action],
                "-ConfigPath",
                str(self.config_path()),
                "-LogPath",
                str(log_path),
                "-SummaryPath",
                str(summary_path),
                "-RequestId",
                task_id,
                "-FailIfBusy",
            ]
            if date_from:
                command.extend(["-DateFrom", date_from])
            if date_to:
                command.extend(["-DateTo", date_to])
            command_line = subprocess.list2cmdline(command)
            status["commandLine"] = command_line
            self._active_status = status
            self._write_gui_status(config, status)
            self._append_run_log_line(
                log_path,
                f"COMMAND | {command_line}",
                "INFO",
            )
            self._append_run_log_line(
                log_path,
                (
                    f"Launching PowerShell process. Executable={command[0]} Runner={paths['runner']} "
                    f"TaskId={task_id} SummaryPath={summary_path}."
                ),
            )
            status["commandOutput"] = self._read_text_file(log_path).rstrip()
            status["outputLineCount"] = len(status["commandOutput"].splitlines()) if status["commandOutput"] else 0
            self._active_status = status
            self._write_gui_status(config, status)
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(paths["script_root"]),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception as exc:
                self._append_run_log_line(log_path, f"PowerShell process launch failed: {type(exc).__name__}: {exc}", "ERROR")
                failed_status = {
                    **status,
                    "running": False,
                    "succeeded": False,
                    "completedAt": utc_now(),
                    "message": "PowerShell automation could not be started.",
                    "currentStep": str(exc),
                    "commandOutput": str(exc),
                    "outputLineCount": 1,
                    "error": str(exc),
                }
                self._active_status = failed_status
                self._write_gui_status(config, failed_status)
                raise RuntimeError(f"PowerShell automation could not be started: {exc}") from exc

            self._active_process = process
            thread = threading.Thread(
                target=self._finish_run,
                args=(config, process, status),
                name=f"delivery-automation-{task_id}",
                daemon=True,
            )
            thread.start()
        return {"ok": True, "accepted": True, "taskId": task_id, "status": status}

    def _finish_run(
        self,
        config: dict[str, Any],
        process: subprocess.Popen[str],
        initial_status: dict[str, Any],
    ) -> None:
        """Stream every runner line into the Status & Logs page until completion."""
        output_lines: list[str] = str(initial_status.get("commandOutput") or "").splitlines()
        stream = getattr(process, "stdout", None)

        if stream is not None and callable(getattr(stream, "readline", None)):
            # Keep the browser view live in memory, but throttle persistence of the
            # growing commandOutput document. Rewriting the complete JSON status
            # file for every line becomes O(n^2) and previously made large importer
            # summaries look frozen even after the database import had completed.
            last_persisted_at = 0.0
            lines_since_persist = 0
            while True:
                raw_line = stream.readline()
                if raw_line == "":
                    if process.poll() is not None:
                        break
                    continue
                line = raw_line.rstrip("\r\n")
                output_lines.append(line)
                live_status = {
                    **initial_status,
                    "running": True,
                    "message": line or "Automation is running...",
                    "currentStep": line,
                    "commandOutput": "\n".join(output_lines),
                    "outputLineCount": len(output_lines),
                }
                with self._state_lock:
                    self._active_status = live_status

                lines_since_persist += 1
                now = time.monotonic()
                if lines_since_persist >= 20 or now - last_persisted_at >= 0.5:
                    self._write_gui_status(config, live_status)
                    last_persisted_at = now
                    lines_since_persist = 0
            process.wait()
        else:
            # Compatibility path used by unit tests and unusual process wrappers.
            stdout, stderr = process.communicate()
            output_lines.extend(str(stdout or "").splitlines())
            output_lines.extend(str(stderr or "").splitlines())

        log_path_text = str(initial_status.get("logPath") or "").strip()
        if log_path_text:
            self._append_run_log_line(
                Path(log_path_text),
                f"PowerShell process exited with code {int(process.returncode or 0)}; reading final runtime summary.",
                "INFO" if int(process.returncode or 0) == 0 else "ERROR",
            )

        summary_path_text = str(initial_status.get("summaryPath") or "").strip()
        runtime_summary = self._read_json_file(Path(summary_path_text)) if summary_path_text else {}
        request_id = str(initial_status.get("taskId") or "")
        summary_request_id = str(runtime_summary.get("requestId") or "")
        if runtime_summary and summary_request_id != request_id:
            runtime_summary = {}
            output_lines.append(
                "Manual automation summary was ignored because it belonged to a different run."
            )
        runtime_summary = self._attach_complete_log(runtime_summary)

        summary_succeeded = runtime_summary.get("succeeded")
        succeeded = bool(summary_succeeded) if isinstance(summary_succeeded, bool) else process.returncode == 0
        command_output = str(runtime_summary.get("commandOutput") or "\n".join(output_lines))
        current_step = command_output.splitlines()[-1] if command_output else "Automation finished."
        status = {
            **runtime_summary,
            **initial_status,
            "running": False,
            "succeeded": succeeded,
            "exitCode": int(process.returncode or 0),
            "completedAt": str(runtime_summary.get("completedAt") or utc_now()),
            "message": "Delivery-list automation completed successfully."
            if succeeded
            else "Delivery-list automation failed. Review the complete log below.",
            "currentStep": current_step,
            "commandOutput": command_output,
            "outputLineCount": len(command_output.splitlines()) if command_output else 0,
            "stdout": command_output,
            "stderr": "",
        }
        self._write_gui_status(config, status)
        with self._state_lock:
            self._active_status = status
            self._active_process = None

    def _run_schedule_script(self, script_name: str) -> dict[str, Any]:
        config = self._read_config(required=True)
        prepared = self._prepare_schedule_runtime(config)
        paths = self._runtime_paths(config)
        script = paths[script_name]
        if not script.is_file():
            raise FileNotFoundError(f"Scheduled-task script is missing after runtime refresh: {script}")
        result = subprocess.run(
            [
                self._power_shell(config),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-ConfigPath",
                str(prepared["configPath"]),
            ],
            cwd=str(paths["script_root"]),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "Scheduled-task command failed").strip())
        return {
            "ok": True,
            "message": (result.stdout or "Scheduled-task settings updated.").strip(),
            "synchronizedRuntimeFiles": prepared["synchronizedFiles"],
            "runtimeConfigPath": str(prepared["configPath"]),
            "dashboard": self.get_dashboard(),
        }

    def install_schedule(self) -> dict[str, Any]:
        # Keep the saved flag aligned with the real Windows task state if setup
        # fails. The PowerShell installer turns it on only after both tasks are
        # created, verified, and successfully launched.
        config = self._read_config(required=True)
        config.setdefault("Automation", {})["ScheduleEnabled"] = self._schedule_installed()
        self._write_config(config)
        result = self._run_schedule_script("installer")
        runtime_config_path = Path(str(result.get("runtimeConfigPath") or ""))
        if runtime_config_path.is_file():
            self._set_schedule_enabled_in_config_path(runtime_config_path, True)
        config = self._read_config(required=True)
        config.setdefault("Automation", {})["ScheduleEnabled"] = True
        self._write_config(config)
        result["dashboard"] = self.get_dashboard()
        return result

    def remove_schedule(self) -> dict[str, Any]:
        result = self._run_schedule_script("remover")
        runtime_config_path = Path(str(result.get("runtimeConfigPath") or ""))
        if runtime_config_path.is_file():
            self._set_schedule_enabled_in_config_path(runtime_config_path, False)
        config = self._read_config(required=True)
        config.setdefault("Automation", {})["ScheduleEnabled"] = False
        self._write_config(config)
        result["dashboard"] = self.get_dashboard()
        return result
