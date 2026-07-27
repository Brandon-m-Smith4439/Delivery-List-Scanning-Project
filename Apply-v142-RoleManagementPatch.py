#!/usr/bin/env python3
"""Install the v142 custom-role backend API into an existing scanner project.

The changed-files release cannot safely replace the complete server/store files because
those files may contain local fixes from the v122-v135 release chain. This patch adds
only the new role-creation contract and endpoint, creates timestamped backups, and
refuses to write unless both updated files parse successfully.
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

MARKER = "DLS_V142_CREATE_ROLE_API"

BASE_METHOD = '''    def create_role(self, data: dict[str, Any], created_by: str = "system") -> dict[str, Any]:
        """Create a named application role with an explicit permission set."""
        raise NotImplementedError

'''

CONCRETE_METHOD = '''    # DLS_V142_CREATE_ROLE_API
    def create_role(self, data: dict[str, Any], created_by: str = "system") -> dict[str, Any]:
        """Create one custom role and assign only the requested permissions.

        Effects: Inserts the role and role-permission rows in one transaction and records
        an audit event. Existing roles and user assignments are not modified.
        """
        clean_name = " ".join(str(data.get("name") or data.get("role") or "").split())[:60]
        description = " ".join(str(data.get("description") or "").split())[:240]
        clean_permissions = sorted({
            str(permission).strip()
            for permission in (data.get("permissions") or [])
            if str(permission).strip()
        })
        unknown = [permission for permission in clean_permissions if permission not in PERMISSIONS]

        if len(clean_name) < 2:
            raise ValueError("Role name must be at least 2 characters")
        if unknown:
            raise ValueError(f"Unknown permission: {unknown[0]}")

        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            existing = con.execute(
                "SELECT id FROM roles WHERE LOWER(name) = LOWER(?) LIMIT 1",
                (clean_name,),
            ).fetchone()
            if existing:
                raise ValueError("A role with that name already exists")

            cursor = con.execute(
                "INSERT INTO roles (name, description) VALUES (?, ?)",
                (clean_name, description),
            )
            role_id = getattr(cursor, "lastrowid", None)
            if not role_id:
                created = con.execute(
                    "SELECT id FROM roles WHERE LOWER(name) = LOWER(?) LIMIT 1",
                    (clean_name,),
                ).fetchone()
                role_id = created["id"] if created else None
            if not role_id:
                raise RuntimeError("The new role could not be read after creation")

            for permission in clean_permissions:
                con.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_name) VALUES (?, ?)",
                    (role_id, permission),
                )

            self.insert_audit(
                con,
                "role",
                clean_name,
                "create_role",
                created_by,
                "",
                description,
                {"permissions": clean_permissions},
            )
            con.commit()

        return {
            "role": clean_name,
            "roles": self.list_roles(),
            "permissions": self.get_permissions(),
        }

'''

SERVER_BLOCK = '''            # DLS_V142_CREATE_ROLE_API
            if parsed.path == "/api/admin/roles":
                user = self.require_permission("manage_roles")
                if not user:
                    return
                self.send_json(
                    STORE.create_role(data, created_by=user["username"]),
                    HTTPStatus.CREATED,
                )
                return

'''


def insert_before(text: str, anchor: str, addition: str, *, occurrence: int = 1) -> str:
    positions: list[int] = []
    start = 0
    while True:
        index = text.find(anchor, start)
        if index < 0:
            break
        positions.append(index)
        start = index + 1
    if len(positions) < occurrence:
        raise RuntimeError(f"Expected anchor occurrence {occurrence}, found {len(positions)}: {anchor[:70]!r}")
    index = positions[occurrence - 1]
    return text[:index] + addition + text[index:]


def patch_store(text: str) -> str:
    if MARKER in text:
        return text

    anchor = '    def update_role_permissions(self, role_name: str, permissions: list[str], updated_by: str = "system") -> dict[str, Any]:\n'
    positions = []
    start = 0
    while True:
        index = text.find(anchor, start)
        if index < 0:
            break
        positions.append(index)
        start = index + 1
    if len(positions) < 2:
        raise RuntimeError("Could not locate both the base and SQLite role-permission methods")

    # Insert concrete method first so the original occurrence indexes stay valid.
    concrete_index = positions[-1]
    text = text[:concrete_index] + CONCRETE_METHOD + text[concrete_index:]
    base_index = positions[0]
    text = text[:base_index] + BASE_METHOD + text[base_index:]
    return text


def patch_server(text: str) -> str:
    if MARKER in text:
        return text
    anchor = '            if parsed.path == "/api/admin/roles/permissions":\n'
    if anchor not in text:
        raise RuntimeError("Could not locate the existing role-permissions API endpoint")
    return text.replace(anchor, SERVER_BLOCK + anchor, 1)


def parse_python(path: Path, content: str) -> None:
    try:
        ast.parse(content, filename=str(path))
    except SyntaxError as exc:
        raise RuntimeError(f"Python syntax validation failed for {path.name}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parent))
    args = parser.parse_args()

    project_root = Path(str(args.project_root).strip().strip('"')).expanduser().resolve()
    store_path = project_root / "delivery_store.py"
    server_path = project_root / "server.py"
    missing = [str(path) for path in (store_path, server_path) if not path.is_file()]
    if missing:
        raise RuntimeError("Required project file was not found: " + ", ".join(missing))

    original_store = store_path.read_text(encoding="utf-8")
    original_server = server_path.read_text(encoding="utf-8")
    updated_store = patch_store(original_store)
    updated_server = patch_server(original_server)

    parse_python(store_path, updated_store)
    parse_python(server_path, updated_server)

    if updated_store == original_store and updated_server == original_server:
        print("v142 role-management backend patch is already installed.")
        return 0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = project_root / "backups" / "v142-role-management" / timestamp
    backup_root.mkdir(parents=True, exist_ok=False)
    shutil.copy2(store_path, backup_root / store_path.name)
    shutil.copy2(server_path, backup_root / server_path.name)

    try:
        store_path.write_text(updated_store, encoding="utf-8", newline="\n")
        server_path.write_text(updated_server, encoding="utf-8", newline="\n")
        parse_python(store_path, store_path.read_text(encoding="utf-8"))
        parse_python(server_path, server_path.read_text(encoding="utf-8"))
    except Exception:
        shutil.copy2(backup_root / store_path.name, store_path)
        shutil.copy2(backup_root / server_path.name, server_path)
        raise

    print("v142 custom-role backend API installed successfully.")
    print(f"Backups: {backup_root}")
    print("Restart the Delivery List Scanner server before using Create Role.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PATCH FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
