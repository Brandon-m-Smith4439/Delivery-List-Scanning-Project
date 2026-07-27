from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def load_patch_module():
    path = ROOT / "Apply-v142-RoleManagementPatch.py"
    spec = importlib.util.spec_from_file_location("v142_role_patch", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_v142_cache_markers_and_docs():
    index = read("index.html")
    readme = read("README.md")
    changelog = read("README_CHANGELOG.md")
    assert "20260727-v142" in index
    assert "20260727-v141" not in index
    assert "Current maintained release: **v142**" in readme
    assert changelog.startswith("## v142 -")
    assert (ROOT / "docs/V142_ROLE_AND_REJECT_REFINEMENTS.md").is_file()


def test_role_creation_ui_and_dynamic_role_options():
    app = read("app.js")
    assert 'id="createRoleForm"' in app
    assert 'fetchJson("/api/admin/roles"' in app
    assert "function createRoleFromForm" in app
    assert "function availableRoleNames" in app
    assert "data-role-create-selection=\"all\"" in app
    assert "data-role-create-selection=\"none\"" in app
    assert app.count("availableRoleNames().map") >= 3
    assert 'roles: "Roles & Permissions"' in app


def test_backend_patch_adds_create_role_contract_and_endpoint():
    patch = load_patch_module()
    store = '''from typing import Any\nPERMISSIONS=[]\nclass BaseDeliveryStore:\n    def update_role_permissions(self, role_name: str, permissions: list[str], updated_by: str = "system") -> dict[str, Any]:\n        raise NotImplementedError\n\nclass SQLiteDeliveryStore(BaseDeliveryStore):\n    def update_role_permissions(self, role_name: str, permissions: list[str], updated_by: str = "system") -> dict[str, Any]:\n        return {}\n'''
    server = '''from http import HTTPStatus
class Handler:
    def post(self):
        try:
            parsed = self.parsed
            data = {}
            if parsed.path == "/api/admin/roles/permissions":
                return
        except Exception:
            return
'''
    patched_store = patch.patch_store(store)
    patched_server = patch.patch_server(server)
    assert "DLS_V142_CREATE_ROLE_API" in patched_store
    assert patched_store.count("def create_role") == 2
    assert 'if parsed.path == "/api/admin/roles":' in patched_server
    ast.parse(patched_store)
    ast.parse(patched_server)
    assert patch.patch_store(patched_store) == patched_store
    assert patch.patch_server(patched_server) == patched_server


def test_create_user_form_uses_balanced_sections():
    app = read("app.js")
    css = read("styles.css")
    assert "user-manager-create-layout" in app
    assert "user-manager-create-section is-profile" in app
    assert "user-manager-create-section is-access" in app
    assert ".user-manager-create-layout" in css
    assert "grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.65fr);" in css
    assert ".user-manager-create-profile-grid .is-wide" in css


def test_reject_page_is_one_workspace_and_incident_details_span_table():
    index = read("index.html")
    app = read("app.js")
    css = read("styles.css")
    reject_section = index.split('id="rejectsPage"', 1)[1].split("<!-- SECTION: Indian Trail", 1)[0]
    assert "reject-workspace-v142" in reject_section
    assert reject_section.count("<h1>") == 1
    assert "rejects-command-tags" not in reject_section
    assert "Internal Reject History" not in reject_section
    assert 'class="internal-reject-detail-row"' in app
    assert 'colspan="10"' in app
    assert "Internal reject reason" in app
    assert "Broke at / machine" in app
    assert ".internal-reject-incident-strip" in css


def test_internal_reject_flag_and_glass_filters_are_readable():
    css = read("styles.css")
    ir = re.search(r"\.row-marker\.internal-reject-marker\s*\{([^}]+)\}", css)
    assert ir
    body = ir.group(1)
    assert "color: #fff" in body
    assert "animation: internalRejectFlagPulse" in body
    glass = re.search(r"\.scan-filter-glass-section \.glass-filter-tabs\s*\{([^}]+)\}", css)
    assert glass and "display: flex" in glass.group(1) and "flex-wrap: wrap" in glass.group(1)
    button = re.search(r"\.scan-filter-glass-section \.glass-filter-tab\s*\{([^}]+)\}", css)
    assert button and "width: auto" in button.group(1) and "white-space: normal" in button.group(1)


def test_sidebar_descenders_are_not_clipped():
    css = read("styles.css")
    selector = re.search(r"\.app-sidebar \.app-nav button > span:last-child\s*\{([^}]+)\}", css)
    assert selector
    body = selector.group(1)
    assert "overflow: visible" in body
    assert "line-height: 1.3" in body
    assert "padding: 2px 0 3px" in body


def test_static_html_ids_are_unique():
    ids = re.findall(r'\bid="([^"]+)"', read("index.html"))
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    assert not duplicates


def test_javascript_parses_as_balanced_source():
    app = read("app.js")
    assert app.count("{") == app.count("}")
    assert app.count("(") == app.count(")")


def test_css_braces_are_balanced():
    css = read("styles.css")
    assert css.count("{") == css.count("}")
