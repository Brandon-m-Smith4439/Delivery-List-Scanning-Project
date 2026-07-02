#!/usr/bin/env python
"""Local pilot server for the delivery-list scanner web app."""

from __future__ import annotations

import json
import html
import os
import tempfile
import shutil
import subprocess
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from http.cookies import SimpleCookie
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from delivery_store import SESSION_COOKIE_NAME, create_store, request_station, request_user_name
from scanner_config import load_config


ROOT = Path(__file__).resolve().parent
CONFIG = load_config(ROOT)
STORE = create_store(CONFIG)
DEFAULT_UPDATE_REPO = "https://github.com/Brandon-m-Smith4439/Delivery-List-Scanning-Project"
DEFAULT_UPDATE_BRANCH = "main"
APP_SENTINELS = ("server.py", "index.html", "app.js", "styles.css")


def is_app_root(path: Path) -> bool:
    return all((path / name).exists() for name in APP_SENTINELS)


def find_app_root(path: Path) -> Path:
    if is_app_root(path):
        return path
    for child in path.rglob("server.py"):
        candidate = child.parent
        if is_app_root(candidate):
            return candidate
    raise ValueError("Update archive did not contain the delivery scanner web app files")


def local_repo_root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        )
        repo_root = Path(result.stdout.strip())
        return repo_root if is_app_root(repo_root) else ROOT
    except Exception:
        return ROOT


def update_repo_url() -> str:
    return os.environ.get("DLS_UPDATE_REPO_URL", DEFAULT_UPDATE_REPO).strip() or DEFAULT_UPDATE_REPO


def update_branch() -> str:
    return os.environ.get("DLS_UPDATE_BRANCH", DEFAULT_UPDATE_BRANCH).strip() or DEFAULT_UPDATE_BRANCH


def github_owner_repo(repo_url: str) -> tuple[str, str]:
    clean = repo_url.strip().rstrip("/")
    if clean.endswith(".git"):
        clean = clean[:-4]
    parts = clean.split("/")
    if len(parts) < 2:
        raise ValueError("GitHub repository URL is not configured")
    return parts[-2], parts[-1]


def http_get_bytes(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "DeliveryListScannerUpdater/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except Exception as urllib_error:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".download") as handle:
                temp_path = Path(handle.name)
            ps_command = (
                "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; "
                "$ProgressPreference = 'SilentlyContinue'; "
                "Invoke-WebRequest -UseBasicParsing "
                f"-Uri {json.dumps(url)} -OutFile {json.dumps(str(temp_path))}"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=timeout + 20,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout or "PowerShell download failed").strip())
            data = temp_path.read_bytes()
            temp_path.unlink(missing_ok=True)
            return data
        except Exception as powershell_error:
            raise RuntimeError(f"Python download failed: {urllib_error}; PowerShell fallback failed: {powershell_error}") from powershell_error


def github_update_status(error_prefix: str = "") -> dict:
    repo_url = update_repo_url()
    branch = update_branch()
    try:
        owner, repo = github_owner_repo(repo_url)
        api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
        data = json.loads(http_get_bytes(api_url, timeout=30).decode("utf-8"))
        remote = str(data.get("sha") or "")
        marker = ROOT / "data" / "update-version.json"
        local = ""
        try:
            local = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=local_repo_root(),
                text=True,
                capture_output=True,
                timeout=10,
                check=True,
            ).stdout.strip()
        except Exception:
            local = ""
        if marker.exists():
            try:
                local = local or str(json.loads(marker.read_text(encoding="utf-8")).get("commit") or "")
            except Exception:
                pass
        update_available = bool(remote and local) and remote != local
        return {
            "ok": True,
            "method": "github_zip",
            "branch": branch,
            "upstream": f"{owner}/{repo}/{branch}",
            "local": local[:12] or "unknown",
            "remote": remote[:12],
            "remoteFull": remote,
            "behind": 1 if update_available else 0,
            "updateAvailable": update_available,
            "note": error_prefix or ("Git was unavailable; checked GitHub directly." if local else "Git was unavailable and no installed version marker was found; update status is unknown."),
        }
    except Exception as exc:
        return {"ok": False, "method": "github_zip", "error": f"{error_prefix} GitHub fallback failed: {exc}".strip(), "updateAvailable": False}


def git_update_status() -> dict:
    def run_git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=local_repo_root(), text=True, capture_output=True, timeout=20, check=True).stdout.strip()

    try:
        branch = run_git("rev-parse", "--abbrev-ref", "HEAD")
        upstream = run_git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        local = run_git("rev-parse", "HEAD")
        subprocess.run(["git", "fetch", "--quiet"], cwd=local_repo_root(), text=True, capture_output=True, timeout=45, check=False)
        remote = run_git("rev-parse", upstream)
        behind_text = run_git("rev-list", "--count", f"{local}..{remote}")
        behind = int(behind_text or "0")
        return {"ok": True, "branch": branch, "upstream": upstream, "local": local[:12], "remote": remote[:12], "behind": behind, "updateAvailable": behind > 0}
    except Exception as exc:
        return github_update_status(f"Git unavailable: {exc}.")


def database_backups() -> tuple[Path, list[tuple[Path, Path]]]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = ROOT / "data" / "_update_backups" / f"{timestamp}-preserve-db"
    backup_dir.mkdir(parents=True, exist_ok=True)
    database_files = [
        CONFIG.database_path,
        CONFIG.database_path.with_name(CONFIG.database_path.name + "-wal"),
        CONFIG.database_path.with_name(CONFIG.database_path.name + "-shm"),
    ]
    backed_up: list[tuple[Path, Path]] = []
    for path in database_files:
        if path.exists():
            target = backup_dir / path.name
            shutil.copy2(path, target)
            backed_up.append((path, target))
    return backup_dir, backed_up


def restore_database_backups(backed_up: list[tuple[Path, Path]]) -> None:
    for original, backup in backed_up:
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, original)


def apply_github_zip_update(status: dict | None = None) -> dict:
    status = status or github_update_status()
    if not status.get("ok"):
        return status
    repo_url = update_repo_url()
    branch = update_branch()
    owner, repo = github_owner_repo(repo_url)
    backup_dir, backed_up = database_backups()
    zip_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"
    try:
        archive_bytes = http_get_bytes(zip_url, timeout=120)
        with tempfile.TemporaryDirectory(prefix="dls-update-") as temp_name:
            temp_dir = Path(temp_name)
            archive_path = temp_dir / "update.zip"
            archive_path.write_bytes(archive_bytes)
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(temp_dir)
            roots = [path for path in temp_dir.iterdir() if path.is_dir()]
            if not roots:
                raise ValueError("GitHub archive did not contain a project folder")
            source_root = find_app_root(roots[0])
            target_root = ROOT
            skip_names = {".git", "data", "_verification", "__pycache__"}
            for child in source_root.iterdir():
                if child.name in skip_names:
                    continue
                target = target_root / child.name
                if child.is_dir():
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(child, target)
                else:
                    shutil.copy2(child, target)
        restore_database_backups(backed_up)
        marker = ROOT / "data" / "update-version.json"
        marker.write_text(json.dumps({"commit": status.get("remoteFull") or status.get("remote", ""), "updatedAt": datetime.now().isoformat(timespec="seconds"), "method": "github_zip"}, indent=2), encoding="utf-8")
        return {"ok": True, "updated": True, "method": "github_zip", "backupDir": str(backup_dir), "restoredDatabaseFiles": [str(path) for path, _ in backed_up], "status": github_update_status()}
    except Exception as exc:
        restore_database_backups(backed_up)
        return {"ok": False, "updated": False, "method": "github_zip", "error": str(exc), "backupDir": str(backup_dir), "restoredDatabaseFiles": [str(path) for path, _ in backed_up]}


def apply_git_update() -> dict:
    status = git_update_status()
    if not status.get("ok"):
        return status
    if status.get("method") == "github_zip":
        return apply_github_zip_update(status)

    current_commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=local_repo_root(),
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    ).stdout.strip() or "unknown"
    backup_dir, backed_up = database_backups()

    pull = subprocess.run(
        ["git", "pull", "--ff-only", "--autostash"],
        cwd=local_repo_root(),
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    restore_database_backups(backed_up)
    after = git_update_status()
    return {
        "ok": pull.returncode == 0,
        "updated": pull.returncode == 0,
        "stdout": pull.stdout[-2000:],
        "stderr": pull.stderr[-2000:],
        "backupDir": str(backup_dir),
        "restoredDatabaseFiles": [str(path) for path, _ in backed_up],
        "status": after,
    }


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


CODE39 = {
    "0": "nnnwwnwnn", "1": "wnnwnnnnw", "2": "nnwwnnnnw", "3": "wnwwnnnnn", "4": "nnnwwnnnw",
    "5": "wnnwwnnnn", "6": "nnwwwnnnn", "7": "nnnwnnwnw", "8": "wnnwnnwnn", "9": "nnwwnnwnn",
    "A": "wnnnnwnnw", "B": "nnwnnwnnw", "C": "wnwnnwnnn", "D": "nnnnwwnnw", "E": "wnnnwwnnn",
    "F": "nnwnwwnnn", "G": "nnnnnwwnw", "H": "wnnnnwwnn", "I": "nnwnnwwnn", "J": "nnnnwwwnn",
    "K": "wnnnnnnww", "L": "nnwnnnnww", "M": "wnwnnnnwn", "N": "nnnnwnnww", "O": "wnnnwnnwn",
    "P": "nnwnwnnwn", "Q": "nnnnnnwww", "R": "wnnnnnwwn", "S": "nnwnnnwwn", "T": "nnnnwnwwn",
    "U": "wwnnnnnnw", "V": "nwwnnnnnw", "W": "wwwnnnnnn", "X": "nwnnwnnnw", "Y": "wwnnwnnnn",
    "Z": "nwwnwnnnn", "-": "nwnnnnwnw", ".": "wwnnnnwnn", " ": "nwwnnnwnn", "$": "nwnwnwnnn",
    "/": "nwnwnnnwn", "+": "nwnnnwnwn", "%": "nnnwnwnwn", "*": "nwnnwnwnn",
}


def code39_svg(value: str) -> str:
    text = "".join(ch for ch in str(value or "").upper() if ch in CODE39 and ch != "*")
    encoded = f"*{text}*"
    narrow, wide, gap, height = 2, 5, 2, 72
    x = 0
    rects = []
    for char in encoded:
        pattern = CODE39[char]
        for index, mark in enumerate(pattern):
            width = wide if mark == "w" else narrow
            if index % 2 == 0:
                rects.append(f'<rect x="{x}" y="0" width="{width}" height="{height}"/>')
            x += width
        x += gap
    return f'<svg class="rack-barcode" viewBox="0 0 {x} {height}" role="img" aria-label="{esc(text)}" preserveAspectRatio="none">{"".join(rects)}</svg>'


def render_item_rows(items: list[dict]) -> str:
    if not items:
        return '<tr><td colspan="8">No printable rows.</td></tr>'
    rows = []
    current_product = object()
    for item in sorted(items, key=lambda row: (str(row.get("product") or row.get("job") or ""), int(row.get("order") or 0), int(row.get("item") or 0))):
        product = item.get("product") or item.get("job") or "Unspecified Glass"
        if product != current_product:
            current_product = product
            rows.append(f'<tr class="glass-group"><td colspan="8">{esc(product)}</td></tr>')
        rows.append(
            f"""
            <tr>
              <td>{esc(item.get("job") or item.get("product"))}</td>
              <td>{esc(item.get("order"))}</td>
              <td>{esc(item.get("item"))}</td>
              <td>{esc(item.get("qty"))}</td>
              <td>{esc(item.get("dimensions"))}</td>
              <td>{esc(item.get("customer"))}</td>
              <td>{esc(item.get("route"))}</td>
              <td class="check-cell">&#9744;</td>
            </tr>
            """
        )
    return "".join(rows)


def render_sheet(title: str, subtitle: str, items: list[dict], sheet_class: str = "") -> str:
    return f"""
    <section class="sheet {sheet_class}">
      <header>
        <div>
          <h1>{esc(title)}</h1>
          <p>{esc(subtitle)}</p>
        </div>
        <div class="copy-box">Checked By: __________ Date: ________</div>
      </header>
      <table>
        <thead>
          <tr><th>Job Nr.</th><th>Order Nr.</th><th>Item Nr.</th><th>Qty.</th><th>Dimensions</th><th>Customer</th><th>Route</th><th>Check</th></tr>
        </thead>
        <tbody>{render_item_rows(items)}</tbody>
      </table>
      <div class="notes"><strong>Notes:</strong><span></span></div>
    </section>
    """


def render_rack_packing_list(payload: dict) -> str:
    rack = payload.get("rack") or {}
    barcode = rack.get("barcode") or f"RACK-{rack.get('code', '')}"
    delivery_label = rack.get("deliveryLabel") or ""
    delivery_suffix = f" - {esc(delivery_label)}" if delivery_label else ""
    rows = []
    for item in rack.get("items") or []:
        rows.append(
            f"""
            <tr>
              <td>{esc(item.get("deliveryLabel"))}</td>
              <td>{esc(item.get("job") or item.get("product"))}</td>
              <td>{esc(item.get("order"))}</td>
              <td>{esc(item.get("item"))}</td>
              <td>{esc(item.get("rackQty") or item.get("qty"))}</td>
              <td>{esc(item.get("dimensions"))}</td>
              <td>{esc(item.get("customer"))}</td>
              <td>{esc(item.get("route"))}</td>
              <td class="check-cell">&#9744;</td>
            </tr>
            """
        )
    if not rows:
        rows.append('<tr><td colspan="9">No pieces are currently assigned to this rack.</td></tr>')
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>{esc(rack.get("name") or rack.get("code"))} Packing List</title>
      <link rel="icon" href="/assets/delivery-list-scanner-icon.ico" sizes="any">
      <style>
        body {{ font-family: Arial, sans-serif; color: #071633; margin: 24px; }}
        header {{ display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; border-bottom: 3px solid #071633; padding-bottom: 14px; }}
        h1 {{ margin: 0; font-size: 28px; }}
        p {{ margin: 4px 0; }}
        .barcode-box {{ width: 320px; text-align: center; }}
        .rack-barcode {{ width: 100%; height: 72px; display: block; }}
        .barcode-text {{ font-size: 18px; font-weight: 900; letter-spacing: 1px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 12px; }}
        th, td {{ border: 1px solid #222; padding: 6px; text-align: left; }}
        th {{ background: #efefef; }}
        .check-cell {{ width: 44px; text-align: center; font-size: 20px; }}
        .notes {{ margin-top: 24px; border: 1px solid #222; min-height: 80px; padding: 8px; }}
        @media print {{ body {{ margin: 0.3in; }} button {{ display: none; }} }}
      </style>
    </head>
    <body onload="setTimeout(function(){{ window.print(); }}, 350)">
      <button onclick="window.print()">Print</button>
      <header>
        <div>
          <h1>{esc(rack.get("name") or rack.get("code"))} Packing List{delivery_suffix}</h1>
          <p>Rack Type: {esc(rack.get("type"))} | Status: {esc(rack.get("status"))} | Qty: {esc(rack.get("qty"))}</p>
          <p>Scan this rack barcode on the outbound stage to scan all active pieces on this rack.</p>
        </div>
        <div class="barcode-box">
          {code39_svg(str(barcode))}
          <div class="barcode-text">*{esc(barcode)}*</div>
        </div>
      </header>
      <table>
        <thead><tr><th>Delivery List</th><th>Job Nr.</th><th>Order Nr.</th><th>Item Nr.</th><th>Qty</th><th>Dimensions</th><th>Customer</th><th>Route</th><th>Check</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
      <div class="notes"><strong>Notes:</strong></div>
    </body>
    </html>
    """


def render_stale_bay_report(rows: list[dict]) -> str:
    body_rows = []
    for row in rows:
        body_rows.append(
            f"""
            <tr>
              <td>{esc(row.get("daysOld"))} days</td>
              <td>{esc(row.get("bayDisplay") or row.get("bayCode"))}</td>
              <td>{esc(row.get("order"))}</td>
              <td>{esc(row.get("item"))}</td>
              <td>{esc(row.get("job") or row.get("product"))}</td>
              <td>{esc(row.get("dimensions"))}</td>
              <td>{esc(row.get("customer"))}</td>
              <td>{esc(row.get("deliveryDate"))}</td>
              <td>{esc(row.get("lastScannedAt"))}</td>
              <td class="check-cell">&#9744;</td>
            </tr>
            """
        )
    if not body_rows:
        body_rows.append('<tr><td colspan="10">No bay orders are older than 10 days.</td></tr>')
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Old Bay Orders</title>
      <link rel="icon" href="/assets/delivery-list-scanner-icon.ico" sizes="any">
      <style>
        body {{ font-family: Arial, sans-serif; color: #071633; margin: 24px; }}
        header {{ display: flex; justify-content: space-between; border-bottom: 3px solid #071633; padding-bottom: 12px; }}
        h1 {{ margin: 0; font-size: 26px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 12px; }}
        th, td {{ border: 1px solid #222; padding: 6px; text-align: left; vertical-align: top; }}
        th {{ background: #efefef; }}
        .check-cell {{ width: 44px; text-align: center; font-size: 20px; }}
        @media print {{ body {{ margin: 0.3in; }} button {{ display: none; }} }}
      </style>
    </head>
    <body>
      <button onclick="window.print()">Print</button>
      <header>
        <div>
          <h1>Old Bay Orders</h1>
          <p>Orders in Indian Trail bays more than 10 days.</p>
        </div>
        <div>Checked By: __________ Date: ________</div>
      </header>
      <table>
        <thead>
          <tr><th>Age</th><th>Bay</th><th>Order</th><th>Item</th><th>Job Nr.</th><th>Dimensions</th><th>Customer</th><th>Delivery</th><th>Last Scanned</th><th>Check</th></tr>
        </thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </body>
    </html>
    """


def render_print_package(package: dict) -> str:
    sections = []
    filters = package.get("filters", {}) or {}
    rush_only = str(filters.get("rushOnly") or "").lower() in {"1", "true", "yes"}
    remake_only = str(filters.get("remakeOnly") or "").lower() in {"1", "true", "yes"}
    special_only = rush_only or remake_only
    for delivery_list in package.get("lists", []):
        remakes = delivery_list.get("remakes", [])
        rushes = delivery_list.get("rushes", [])
        normal_items = [item for item in delivery_list.get("items", []) if item not in remakes and item not in rushes]
        subtitle = f"{delivery_list.get('stage')} | {delivery_list.get('deliveryDate')} | Regular mirror rows excluded: {delivery_list.get('excludedMirrorCount', 0)}"
        if normal_items and not special_only:
            sections.append(render_sheet(str(delivery_list.get("label")), f"{subtitle} | Copy 1 of 2", normal_items, "regular"))
            sections.append(render_sheet(str(delivery_list.get("label")), f"{subtitle} | Copy 2 of 2", normal_items, "regular"))
        if rushes and not remake_only:
            sections.append(render_sheet("RUSH ORDER SHEET", str(delivery_list.get("label")), rushes, "rush"))
        if remakes and not rush_only:
            sections.append(render_sheet("REMAKE SHEET", str(delivery_list.get("label")), remakes, "remake"))
    body = "".join(sections) or '<section class="sheet"><h1>No printable rows found</h1></section>'
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Delivery List Print Package</title>
  <link rel="icon" href="/assets/delivery-list-scanner-icon.ico" sizes="any">
  <style>
    body {{ margin: 0; color: #07122f; font-family: "Segoe UI", Arial, sans-serif; background: #f6f8fb; }}
    .sheet {{ width: min(1120px, calc(100% - 32px)); margin: 16px auto; padding: 18px; background: #fff; border: 1px solid #444; border-radius: 0; }}
    header {{ display: flex; justify-content: space-between; gap: 16px; align-items: end; border-bottom: 3px solid #072a63; padding-bottom: 10px; margin-bottom: 12px; }}
    h1 {{ margin: 0; color: #041a3d; font-size: 24px; text-transform: uppercase; }}
    p {{ margin: 4px 0 0; font-weight: 700; color: #41506c; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ border: 1px solid #d9e1ee; padding: 7px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f1f1f1; color: #041a3d; }}
    .glass-group td {{ background: #e9e9e9; font-weight: 900; text-transform: uppercase; }}
    .check-cell {{ width: 28px; text-align: center; font-size: 16px; }}
    .copy-box {{ border: 1px solid #333; padding: 8px 10px; font-weight: 800; white-space: nowrap; }}
    .notes {{ margin-top: 12px; min-height: 72px; border: 1px solid #333; display: grid; grid-template-columns: auto 1fr; gap: 8px; padding: 8px; }}
    .rush {{ border: 4px double #000; }}
    .rush header {{ border-bottom: 6px double #000; }}
    .rush h1::before, .rush h1::after {{ content: " !!! "; }}
    .remake {{ border: 3px dashed #000; }}
    .remake header {{ border-bottom: 3px dashed #000; }}
    @media print {{
      body {{ background: #fff; }}
      .sheet {{ width: auto; margin: 0; border: 0; border-radius: 0; page-break-after: always; }}
    }}
  </style>
</head>
<body>
  {body}
  <script>window.addEventListener("load", () => setTimeout(() => window.print(), 250));</script>
</body>
</html>"""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, markup: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = markup.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def session_token(self) -> str:
        cookie_header = self.headers.get("Cookie", "")
        if not cookie_header:
            return ""
        cookie = SimpleCookie(cookie_header)
        morsel = cookie.get(SESSION_COOKIE_NAME)
        return morsel.value if morsel else ""

    def current_user(self) -> dict | None:
        return STORE.get_user_by_session(self.session_token())

    def require_permission(self, permission: str) -> dict | None:
        user = self.current_user()
        if not user:
            self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
            return None
        if permission not in user.get("permissions", []):
            self.send_json({"error": "Permission denied", "permission": permission}, HTTPStatus.FORBIDDEN)
            return None
        return user

    def set_session_cookie(self, token: str, expires_at: str) -> None:
        secure = "; Secure" if CONFIG.production else ""
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=43200{secure}",
        )

    def clear_session_cookie(self) -> None:
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0",
        )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            self.send_json(STORE.health())
            return

        if parsed.path == "/api/session":
            user = self.current_user()
            self.send_json({"authenticated": bool(user), "user": user})
            return

        if parsed.path == "/api/delivery-lists":
            user = self.require_permission("view_lists")
            if not user:
                return
            self.send_json({"lists": STORE.get_delivery_lists(user)})
            return

        if parsed.path == "/api/stations":
            if not self.require_permission("view_stations"):
                return
            self.send_json({"stations": STORE.get_stations()})
            return

        if parsed.path == "/api/exceptions":
            if not self.require_permission("view_exceptions"):
                return
            filters = {key: values[0] for key, values in parse_qs(parsed.query).items()}
            self.send_json({"exceptions": STORE.get_exceptions(filters)})
            return

        if parsed.path == "/api/admin/summary":
            if not self.require_permission("view_admin"):
                return
            self.send_json(STORE.admin_summary())
            return

        if parsed.path == "/api/admin/update-check":
            if not self.require_permission("view_admin"):
                return
            self.send_json(git_update_status())
            return

        if parsed.path == "/api/admin/users":
            if not self.require_permission("manage_users"):
                return
            self.send_json({"users": STORE.list_users()})
            return

        if parsed.path == "/api/admin/customer-route-rules":
            if not self.require_permission("manage_customer_route_rules"):
                return
            self.send_json({"rules": STORE.get_customer_route_rules()})
            return

        if parsed.path == "/api/admin/manual-edit-lookups":
            if not self.require_permission("edit_delivery_lists"):
                return
            self.send_json(STORE.get_manual_edit_lookups())
            return

        if parsed.path == "/api/admin/permissions":
            if not self.require_permission("manage_roles"):
                return
            self.send_json({"permissions": STORE.get_permissions()})
            return

        if parsed.path == "/api/admin/roles":
            if not self.require_permission("manage_roles"):
                return
            self.send_json({"roles": STORE.list_roles(), "permissions": STORE.get_permissions()})
            return

        if parsed.path == "/api/admin/line-items/search":
            if not self.require_permission("edit_delivery_lists"):
                return
            query = parse_qs(parsed.query).get("q", [""])[0]
            list_id = parse_qs(parsed.query).get("listId", [""])[0]
            self.send_json({"results": STORE.admin_search_line_items(query, list_id)})
            return

        if parsed.path == "/api/admin/sessions":
            if not self.require_permission("view_active_sessions"):
                return
            self.send_json({"sessions": STORE.list_active_sessions()})
            return

        if parsed.path == "/api/admin/audit":
            if not self.require_permission("view_admin"):
                return
            limit = parse_qs(parsed.query).get("limit", ["100"])[0]
            self.send_json({"events": STORE.list_audit_events(int(limit or 100))})
            return

        if parsed.path == "/api/search":
            user = self.require_permission("global_search")
            if not user:
                return
            query = parse_qs(parsed.query).get("q", [""])[0]
            self.send_json({"results": STORE.global_search(query, user)})
            return

        if parsed.path == "/api/reports/summary":
            if not self.require_permission("view_reports"):
                return
            self.send_json(STORE.reports_summary())
            return

        if parsed.path == "/api/indian-trail/summary":
            if not self.require_permission("view_indian_trail"):
                return
            self.send_json(STORE.indian_trail_summary())
            return

        if parsed.path == "/api/indian-trail/bays":
            if not self.require_permission("view_bays"):
                return
            self.send_json({"bays": STORE.get_bays()})
            return

        if parsed.path == "/api/indian-trail/layout":
            if not self.require_permission("view_bays"):
                return
            self.send_json(STORE.get_bay_layout())
            return

        if parsed.path == "/api/indian-trail/events":
            if not self.require_permission("view_bays"):
                return
            limit = parse_qs(parsed.query).get("limit", ["20"])[0]
            self.send_json({"events": STORE.get_bay_events(int(limit or 20))})
            return

        if parsed.path == "/api/indian-trail/stale-bays":
            if not self.require_permission("view_bays"):
                return
            include_snoozed = parse_qs(parsed.query).get("includeSnoozed", ["0"])[0] in {"1", "true", "yes"}
            self.send_json({"orders": STORE.get_stale_bay_orders(include_snoozed=include_snoozed)})
            return

        if parsed.path == "/api/indian-trail/stale-bays/print":
            if not self.require_permission("view_bays"):
                return
            body = render_stale_bay_report(STORE.get_stale_bay_orders(include_snoozed=True)).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/racks":
            if not self.require_permission("view_racks"):
                return
            self.send_json(STORE.get_racks())
            return

        if parsed.path == "/api/racks/packing-list":
            user = self.require_permission("view_racks")
            if not user:
                return
            params = parse_qs(parsed.query)
            rack_code = params.get("rackCode", [""])[0]
            delivery_date = params.get("deliveryDate", [""])[0]
            body = render_rack_packing_list(STORE.rack_packing_list(rack_code, delivery_date)).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path.startswith("/api/delivery-lists/"):
            user = self.require_permission("view_lists")
            if not user:
                return
            list_id = unquote(parsed.path.rsplit("/", 1)[-1])
            try:
                self.send_json(STORE.get_delivery_list(list_id, user=user))
            except PermissionError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.FORBIDDEN)
            except KeyError:
                self.send_json({"error": "Delivery list not found"}, HTTPStatus.NOT_FOUND)
            return

        if parsed.path == "/api/export.csv":
            user = self.require_permission("export_reports")
            if not user:
                return
            list_id = parse_qs(parsed.query).get("listId", [""])[0]
            if not STORE.user_can_access_list(user, list_id):
                self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                return
            body = STORE.export_csv(list_id).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=delivery-list-export.csv")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/export.xlsx":
            user = self.require_permission("export_reports")
            if not user:
                return
            list_id = parse_qs(parsed.query).get("listId", [""])[0]
            if not STORE.user_can_access_list(user, list_id):
                self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                return
            body = STORE.export_xlsx(list_id)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", "attachment; filename=delivery-list-export.xlsx")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/export/package.xlsx":
            user = self.require_permission("export_reports")
            if not user:
                return
            params = parse_qs(parsed.query)
            raw_ids = params.get("listId", [])
            list_ids = []
            for value in raw_ids:
                list_ids.extend(part for part in value.split(",") if part)
            body = STORE.export_package_xlsx(list_ids, user=user, filters={key: values[0] for key, values in params.items()})
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", "attachment; filename=delivery-list-export.xlsx")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/print/package":
            user = self.require_permission("export_reports")
            if not user:
                return
            params = parse_qs(parsed.query)
            raw_ids = params.get("listId", [])
            list_ids = []
            for value in raw_ids:
                list_ids.extend(part for part in value.split(",") if part)
            package = STORE.get_print_package(list_ids, user=user, filters={key: values[0] for key, values in params.items()})
            self.send_html(render_print_package(package))
            return

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            data = self.read_json()

            if parsed.path == "/api/login":
                try:
                    payload = STORE.authenticate_user(str(data.get("username") or ""), str(data.get("password") or ""))
                except PermissionError as exc:
                    self.send_json({"error": str(exc)}, HTTPStatus.UNAUTHORIZED)
                    return
                body = json.dumps({"authenticated": True, "user": payload["user"]}, indent=2).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.set_session_cookie(payload["token"], payload["expiresAt"])
                self.end_headers()
                self.wfile.write(body)
                return

            if parsed.path == "/api/logout":
                STORE.delete_session(self.session_token())
                body = json.dumps({"ok": True}, indent=2).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.clear_session_cookie()
                self.end_headers()
                self.wfile.write(body)
                return

            if parsed.path == "/api/scans":
                user = self.require_permission("scan")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                data["user"] = user["username"]
                self.send_json(STORE.record_scan(data))
                return

            if parsed.path == "/api/reset":
                user = self.require_permission("reset_lists")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                self.send_json(
                    STORE.reset_stage(
                        str(data.get("listId") or ""),
                        user["username"],
                        request_station(data),
                    )
                )
                return

            if parsed.path == "/api/undo":
                user = self.require_permission("undo_scan")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                self.send_json(
                    STORE.undo_last_scan(
                        str(data.get("listId") or ""),
                        user["username"],
                        request_station(data),
                    )
                )
                return

            if parsed.path == "/api/redo":
                user = self.require_permission("undo_scan")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                self.send_json(
                    STORE.redo_last_undo(
                        str(data.get("listId") or ""),
                        user["username"],
                        request_station(data),
                    )
                )
                return

            if parsed.path == "/api/stations":
                if not self.require_permission("manage_stations"):
                    return
                self.send_json(STORE.add_station(str(data.get("name") or "")))
                return

            if parsed.path == "/api/stations/remove":
                if not self.require_permission("remove_stations"):
                    return
                self.send_json(STORE.remove_station(str(data.get("name") or "")))
                return

            if parsed.path == "/api/stations/rename":
                if not self.require_permission("manage_stations"):
                    return
                self.send_json(STORE.rename_station(str(data.get("oldName") or ""), str(data.get("newName") or "")))
                return

            if parsed.path == "/api/import":
                user = self.require_permission("import_delivery_lists")
                if not user:
                    return
                data["user"] = user["username"]
                self.send_json(STORE.import_delivery_list(data))
                return

            if parsed.path == "/api/import/folder":
                user = self.require_permission("import_delivery_lists")
                if not user:
                    return
                data["user"] = user["username"]
                self.send_json(STORE.import_delivery_folder(data))
                return

            if parsed.path == "/api/import/preview":
                if not self.require_permission("preview_import"):
                    return
                self.send_json(STORE.preview_import(data.get("payload") or data))
                return

            if parsed.path == "/api/exceptions/resolve":
                user = self.require_permission("resolve_exceptions")
                if not user:
                    return
                self.send_json(STORE.resolve_exception(data, user["username"]))
                return

            if parsed.path == "/api/admin/users":
                user = self.require_permission("manage_users")
                if not user:
                    return
                self.send_json({"user": STORE.create_user(data, created_by=user["username"])})
                return

            if parsed.path == "/api/admin/users/deactivate":
                user = self.require_permission("deactivate_users")
                if not user:
                    return
                self.send_json(STORE.deactivate_user(str(data.get("username") or ""), deactivated_by=user["username"]))
                return

            if parsed.path == "/api/admin/users/reactivate":
                user = self.require_permission("reactivate_users")
                if not user:
                    return
                self.send_json(STORE.reactivate_user(str(data.get("username") or ""), activated_by=user["username"]))
                return

            if parsed.path == "/api/admin/users/password":
                user = self.require_permission("update_user_passwords")
                if not user:
                    return
                self.send_json(STORE.update_user_password(str(data.get("username") or ""), str(data.get("password") or ""), updated_by=user["username"]))
                return

            if parsed.path == "/api/admin/users/roles":
                user = self.require_permission("manage_roles")
                if not user:
                    return
                self.send_json(STORE.update_user_roles(str(data.get("username") or ""), data.get("roles") or [], updated_by=user["username"]))
                return

            if parsed.path == "/api/admin/roles/permissions":
                user = self.require_permission("manage_roles")
                if not user:
                    return
                self.send_json(STORE.update_role_permissions(str(data.get("role") or ""), data.get("permissions") or [], updated_by=user["username"]))
                return

            if parsed.path == "/api/admin/update-apply":
                user = self.require_permission("check_updates")
                if not user:
                    return
                self.send_json(apply_git_update())
                return

            if parsed.path == "/api/admin/line-item":
                user = self.require_permission("edit_delivery_lists")
                if not user:
                    return
                self.send_json(STORE.update_line_item(data, user["username"]))
                return

            if parsed.path == "/api/admin/line-item/delete":
                user = self.require_permission("edit_delivery_lists")
                if not user:
                    return
                self.send_json(STORE.delete_line_item(str(data.get("lineItemId") or ""), user["username"]))
                return

            if parsed.path == "/api/admin/customer-route-rules":
                user = self.require_permission("manage_customer_route_rules")
                if not user:
                    return
                self.send_json(STORE.add_customer_route_rule(data, user["username"]))
                return

            if parsed.path == "/api/admin/customer-route-rules/remove":
                user = self.require_permission("manage_customer_route_rules")
                if not user:
                    return
                self.send_json(STORE.remove_customer_route_rule(int(data.get("ruleId") or 0), user["username"]))
                return

            if parsed.path == "/api/admin/manual-edit-lookups":
                user = self.require_permission("edit_delivery_lists")
                if not user:
                    return
                self.send_json(STORE.add_manual_edit_lookup(data, user["username"]))
                return

            if parsed.path == "/api/admin/delete-list":
                user = self.require_permission("edit_delivery_lists")
                if not user:
                    return
                self.send_json(STORE.delete_delivery_list(str(data.get("listId") or ""), user["username"]))
                return

            if parsed.path == "/api/admin/delete-date":
                user = self.require_permission("edit_delivery_lists")
                if not user:
                    return
                self.send_json(STORE.delete_delivery_date(str(data.get("deliveryDate") or ""), user["username"]))
                return

            if parsed.path == "/api/indian-trail/receive":
                user = self.require_permission("indian_trail_receive")
                if not user:
                    return
                if data.get("listId") and not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                self.send_json(STORE.receive_indian_trail_scan(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/assign":
                user = self.require_permission("assign_bay")
                if not user:
                    return
                self.send_json(STORE.assign_bay(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/move":
                user = self.require_permission("move_bay")
                if not user:
                    return
                self.send_json(STORE.move_bay_assignment(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/clear":
                user = self.require_permission("clear_bay")
                if not user:
                    return
                self.send_json(STORE.clear_bay(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/clear-assignment":
                user = self.require_permission("clear_bay")
                if not user:
                    return
                self.send_json(STORE.clear_bay_assignment(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/restore-assignment":
                user = self.require_permission("clear_bay")
                if not user:
                    return
                self.send_json(STORE.restore_bay_assignment(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/bay-status":
                user = self.require_permission("clear_bay")
                if not user:
                    return
                self.send_json(STORE.set_bay_status(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/scan-out":
                user = self.require_permission("clear_bay")
                if not user:
                    return
                self.send_json(STORE.scan_out_bay_item(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/layout":
                user = self.require_permission("manage_bay_layout")
                if not user:
                    return
                if data.get("setGroupPosition"):
                    self.send_json(STORE.set_bay_group_position(data, user["username"]))
                elif data.get("moveGroup"):
                    self.send_json(STORE.move_bay_group(data, user["username"]))
                else:
                    self.send_json(STORE.update_bay_layout(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/bays/add":
                user = self.require_permission("manage_bay_layout")
                if not user:
                    return
                self.send_json(STORE.create_bays(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/bays/delete":
                user = self.require_permission("manage_bay_layout")
                if not user:
                    return
                self.send_json(STORE.delete_bay(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/bays/delete-group":
                user = self.require_permission("manage_bay_layout")
                if not user:
                    return
                self.send_json(STORE.delete_bay_group(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/mark-sdi":
                user = self.require_permission("mark_sdi")
                if not user:
                    return
                self.send_json(STORE.mark_sdi(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/remove-sdi":
                user = self.require_permission("remove_sdi")
                if not user:
                    return
                self.send_json(STORE.remove_sdi(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/bay-check":
                user = self.require_permission("bay_check")
                if not user:
                    return
                self.send_json(STORE.bay_check(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/stale-bays/snooze":
                user = self.require_permission("view_bays")
                if not user:
                    return
                self.send_json(STORE.snooze_stale_bay_orders(data, user["username"]))
                return

            if parsed.path == "/api/racks/scan":
                user = self.require_permission("scan_racks")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                self.send_json(STORE.scan_item_to_rack(data, user["username"]))
                return

            if parsed.path == "/api/racks/complete":
                user = self.require_permission("scan_racks")
                if not user:
                    return
                self.send_json(STORE.complete_rack(data, user["username"]))
                return

            if parsed.path == "/api/racks/uncomplete":
                user = self.require_permission("scan_racks")
                if not user:
                    return
                self.send_json(STORE.uncomplete_rack(data, user["username"]))
                return

            if parsed.path == "/api/racks/move-item":
                user = self.require_permission("manage_racks")
                if not user:
                    return
                self.send_json(STORE.move_rack_item(data, user["username"]))
                return

            if parsed.path == "/api/racks/clear-item":
                user = self.require_permission("manage_racks")
                if not user:
                    return
                self.send_json(STORE.clear_rack_item(data, user["username"]))
                return

            if parsed.path == "/api/racks/clear":
                user = self.require_permission("manage_racks")
                if not user:
                    return
                self.send_json(STORE.clear_rack(data, user["username"]))
                return

            if parsed.path == "/api/racks":
                user = self.require_permission("manage_racks")
                if not user:
                    return
                self.send_json(STORE.update_rack(data, user["username"]))
                return

            if parsed.path == "/api/racks/create-set":
                user = self.require_permission("manage_racks")
                if not user:
                    return
                self.send_json(STORE.create_rack_set(data, user["username"]))
                return

            if parsed.path == "/api/racks/delete":
                user = self.require_permission("manage_racks")
                if not user:
                    return
                self.send_json(STORE.delete_rack(data, user["username"]))
                return

            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except PermissionError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.FORBIDDEN)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def main() -> int:
    STORE.initialize()
    server = ThreadingHTTPServer((CONFIG.host, CONFIG.port), Handler)
    print(f"Delivery List Scanner running at http://{CONFIG.host}:{CONFIG.port}/")
    print(f"Database type: {CONFIG.database_type}")
    print(f"Database: {CONFIG.database_path}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
