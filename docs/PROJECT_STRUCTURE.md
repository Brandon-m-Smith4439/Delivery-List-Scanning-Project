<!-- File: docs/PROJECT_STRUCTURE.md -->
# Delivery List Scanner Project Structure

This is the maintained source layout after the v150 organization pass.

## File Headers

Maintained text source and configuration files begin with a `File:` comment
containing their project-relative path. The comment syntax follows each file
format, and BAT headers remain after `@echo off` to avoid extra console output.
JSON, binary assets, runtime data, logs, and single-value version files are
excluded because comments would invalidate or alter them.

## Root

The root intentionally contains only application entrypoints, deployment
metadata, and primary documentation.

- `index.html` - application shell and page markup.
- `server.py` - local HTTP/API server.
- `Start-DeliveryScannerWebApp.bat` and `.ps1` - primary launchers.
- `Configure-MicrosoftGraphEmail.bat` and `Create Desktop Shortcut.bat` -
  user-facing setup entrypoints.
- `.dockerignore` - root Docker build-context exclusions.
- `pytest.ini` - root pytest discovery and marker configuration.

The paired startup BAT and PS1 intentionally remain beside `server.py`. The BAT
resolves the PS1 relative to its own location, so moving only one would break
the normal floor launcher.

## Python Packages

`backend` contains application behavior imported by `server.py`.

```text
backend/
  config.py              runtime configuration
  store.py               data access and workflow behavior
  automation_control.py  delivery automation control service
  import_safety.py       guarded import integration
  operations.py          operational feature service
  production_files.py    production-share index, live evidence, and durable observed EGL history
```

`database` owns database-specific contracts and migration tooling.

```text
database/
  contract.py                       canonical logical schema contract
  migrations.py                     numbered SQLite migrations
  integrity.py                      read-only database integrity checks
  azure_compat.py                   Azure SQL connection compatibility
  azure_schema.sql                  SQL Server/Azure SQL schema
  migrate_sqlite_to_azure_sql.py    migration command
```

Run the Azure migration command from the project root with
`py -3 -m database.migrate_sqlite_to_azure_sql`.

## Deployment

Optional Docker and Azure App Service files live under `deployment`.

```text
deployment/
  azure/
    app-service.env.example
  docker/
    Dockerfile
    requirements.txt
```

Build the optional container from the project root so `.dockerignore` applies:

```powershell
docker build -f deployment/docker/Dockerfile -t delivery-list-scanner .
```

## Browser Assets

`static` contains source loaded directly by `index.html`.

```text
static/
  css/
    styles.css    shared tokens, login, shell, navigation, modals, and controls
    rejects.css   Rejects page, reject workflow modals, timeline, and notices
    home.css      Home dashboard and delivery-list finder
    scan.css      Scan page, filters, tables, and scan feedback
    racks.css     rack overview and rack workflows
    bays.css      Indian Trail Bay Map and Bay Scanner
    admin.css     Admin dashboard and delivery automation controls
    print.css     print-only rules
  images/
    barefoot-builders-firstsource-logo.png
  js/
    app.js
```

All browser behavior is intentionally kept in `static/js/app.js`. Version
numbers belong in the query strings in `index.html`, not in filenames. This
keeps imports stable and prevents obsolete `*-vNNN.css` or `*-vNNN.js` files
from accumulating.

## Runtime Data

- `data` contains production SQLite data and must be preserved.
- `assets` contains the scanner icon and print-page assets.
- `sounds` contains runtime audio files.
- `automation` contains scheduled import/export tooling.
- `logs` is generated and may be cleared only while the app is stopped.
- `backups` contains recovery material and should be reviewed by date before
  anything is removed.

## Supporting Files

- `scripts/windows` contains PowerShell implementations launched by the
  user-facing root BAT files.
- `scripts/diagnostics` contains optional SELECT-only A+W diagnostics, including `Probe-AWBdeBreakage.ps1` for validating the live breakage contract.
- A+W breakage synchronization is configured from Automated Import > **A+W Rejects**. Raw A+W rows remain read-only source evidence; logical events mirror into Internal Reject history.
- `data/production-file-index.json` also retains exact `.egl` files that the index has observed. Historical EGL entries are evidence-only and are not treated as live/openable network files.
- `resources/aw` contains retained A+W source material that is not loaded by the
  web app.

## Safe Cleanup

The following are generated or historical and do not belong in a normal source
commit:

- Any `__pycache__` folder or `*.pyc` file.
- Contents of `logs` while the app and automation tasks are stopped.
- Old release ZIP files and extracted `vNNN_payload` folders after a verified
  backup or Git tag exists.
- Historical `README_CHANGELOG_vNNN_ENTRY.md` fragments after their content is
  present in `README_CHANGELOG.md`.
- Historical GUI integration overlays were removed. Current automation setup
  configures the runtime without copying or rewriting web-app source files.

Never delete `data`, active automation configuration, encrypted secrets, or
recent backups as part of source cleanup.

- `scripts/diagnostics/Probe-AWGlassLabels.ps1` - SELECT-only A+W optimization/glass-label discovery; v0.488 follows Order/Item -> `PROD_JOBITEM.OPTIMIZATION` -> `PROD_OPTI_SEQUENCE` and now drills into the observed `FS_POOL` `STSL*.ASC` / `STSD*.ASC` / `PRODBDAZ.000` output families plus label-control and generator-module metadata.
