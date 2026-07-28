from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_index_local_assets_exist() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    references = re.findall(r'(?:href|src)="([^"]+)"', index)
    missing = []
    for reference in references:
        path_text = reference.split("?", 1)[0]
        if not path_text or "://" in path_text or path_text.startswith("#"):
            continue
        if not (ROOT / path_text).is_file():
            missing.append(path_text)
    assert not missing, f"Missing local assets: {missing}"


def test_page_stylesheets_are_present_and_balanced() -> None:
    css_dir = ROOT / "static" / "css"
    expected = {
        "styles.css",
        "home.css",
        "scan.css",
        "racks.css",
        "bays.css",
        "admin.css",
        "print.css",
    }
    assert {path.name for path in css_dir.glob("*.css")} == expected
    for path in css_dir.glob("*.css"):
        content = path.read_text(encoding="utf-8")
        assert content.count("{") == content.count("}"), path


def test_version_numbers_are_not_embedded_in_asset_filenames() -> None:
    versioned = []
    for folder in (ROOT / "static" / "css", ROOT / "static" / "js"):
        versioned.extend(path.name for path in folder.iterdir() if re.search(r"-v\d+", path.name))
    assert not versioned


def test_single_javascript_bundle_is_loaded() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    scripts = re.findall(r'<script\s+src="([^"]+)"', index)
    assert scripts == ["static/js/app.js?v=20260728-v151-static2"]
    app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert "DELIVERY AUTOMATION CONTROL CENTER" in app
    assert "NOTIFICATION CENTER AND LINE UPDATE REVIEW" in app


def test_python_packages_are_organized() -> None:
    expected_backend = {
        "__init__.py",
        "automation_control.py",
        "config.py",
        "import_safety.py",
        "operations.py",
        "store.py",
    }
    expected_database = {
        "__init__.py",
        "azure_compat.py",
        "azure_schema.sql",
        "contract.py",
        "integrity.py",
        "migrations.py",
        "migrate_sqlite_to_azure_sql.py",
    }
    assert {path.name for path in (ROOT / "backend").iterdir() if path.is_file()} == expected_backend
    assert {path.name for path in (ROOT / "database").iterdir() if path.is_file()} == expected_database
    assert {path.name for path in ROOT.glob("*.py")} == {"server.py"}


def test_deployment_files_are_organized() -> None:
    assert not (ROOT / "Dockerfile").exists()
    assert not (ROOT / ".env.azure.example").exists()
    assert (ROOT / ".dockerignore").is_file()
    assert (ROOT / "pytest.ini").is_file()
    assert (ROOT / "Start-DeliveryScannerWebApp.bat").is_file()
    assert (ROOT / "Start-DeliveryScannerWebApp.ps1").is_file()
    dockerfile = ROOT / "deployment" / "docker" / "Dockerfile"
    requirements = ROOT / "deployment" / "docker" / "requirements.txt"
    azure_example = ROOT / "deployment" / "azure" / "app-service.env.example"
    assert dockerfile.is_file()
    assert requirements.is_file()
    assert azure_example.is_file()
    assert "deployment/docker/requirements.txt" in dockerfile.read_text(encoding="utf-8")


if __name__ == "__main__":
    test_index_local_assets_exist()
    test_page_stylesheets_are_present_and_balanced()
    test_version_numbers_are_not_embedded_in_asset_filenames()
    test_single_javascript_bundle_is_loaded()
    test_python_packages_are_organized()
    test_deployment_files_are_organized()
    print("Static structure checks passed.")
