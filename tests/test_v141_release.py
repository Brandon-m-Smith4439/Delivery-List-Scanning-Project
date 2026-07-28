from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_v141_cache_and_release_markers() -> None:
    index = read("index.html")
    readme = read("README.md")
    changelog = read("README_CHANGELOG.md")

    assert "20260728-v147" in index
    assert index.count("20260728-v147") == 7
    assert "Current maintained release: **v147**" in readme
    assert "Delivery_List_Scanner_v141_Changed_Files.zip" in readme
    assert changelog.startswith("## v147 - Bay Scanner Route and Sticky Refinement")


def test_edit_users_uses_card_workspace_not_wide_edit_table() -> None:
    app = read("app.js")
    start = app.index("function renderAdminUsersTable")
    end = app.index("Purpose: Render the render admin stations workflow", start)
    block = app[start:end]

    assert "user-manager-cards" in block
    assert "data-user-manager-card" in block
    assert "user-manager-card-summary" in block
    assert "user-manager-card-body" in block
    assert "users-table-head" not in block


def test_user_manager_preserves_existing_action_contracts() -> None:
    app = read("app.js")
    required = {
        'data-user-email="',
        'data-user-role-select="',
        'data-user-station-list="',
        'data-update-user-role="',
        'data-user-password="',
        'data-generate-user-password="',
        'data-toggle-password="',
        'data-update-user-password="',
        'data-deactivate-user="',
        'data-reactivate-user="',
        'data-delete-user="',
    }
    for marker in required:
        assert marker in app


def test_user_manager_filters_are_wired_and_persisted() -> None:
    app = read("app.js")
    assert "function applyUserManagerFilters()" in app
    assert "function wireUserManagerControls(saved = {})" in app
    assert 'search?.addEventListener("input", applyUserManagerFilters)' in app
    assert 'status?.addEventListener("change", applyUserManagerFilters)' in app
    assert 'role?.addEventListener("change", applyUserManagerFilters)' in app
    assert "const savedFilters = usersModalOpen" in app
    assert "wireUserManagerControls(savedFilters);" in app
    assert 'if (kind === "users") {\n    wireUserManagerControls();' in app


def test_user_manager_css_owns_responsive_containment() -> None:
    css = read("styles.css")
    required = {
        ".admin-modal-panel:has(.user-manager-v141)",
        "#adminModalBody:has(.user-manager-v141)",
        ".user-manager-directory",
        ".user-manager-card-summary",
        ".user-manager-card-body",
        ".user-manager-action-button.is-primary",
        ".user-manager-action-button.is-danger",
        "@media (max-width: 1120px)",
        "@media (max-width: 820px)",
    }
    for marker in required:
        assert marker in css

    v141 = css[css.index("17. v141 User Access Management workspace") :]
    assert "overflow-x: hidden" in v141
    assert "grid-template-columns: minmax(0, 1fr)" in v141
    assert "min-width: 1680px" not in v141


def test_static_html_ids_remain_unique_and_css_balanced() -> None:
    html = read("index.html")
    css = read("styles.css")
    ids = re.findall(r'\bid="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    assert css.count("{") == css.count("}")


def test_v141_documentation_exists() -> None:
    doc = read("docs/V141_USER_ACCESS_MANAGER.md")
    assert "User Access Management Redesign" in doc
    assert "No user API" in doc
    assert "Do not reintroduce a wide user table" in doc
