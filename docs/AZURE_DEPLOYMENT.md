# Delivery List Scanner: Azure App Service and Azure SQL Deployment

## Recommended architecture

Use one Azure App Service custom Linux container for both the frontend and backend, plus one Azure SQL Database for shared application data.

- The browser loads `index.html`, `app.js`, and `styles.css` from the same App Service.
- The frontend calls the existing relative `/api/...` routes, so no CORS configuration or separate frontend URL is required.
- `server.py` handles the API and static files.
- `delivery_store.py` continues to contain one copy of the business rules.
- `azure_sql_compat.py` adapts those rules to Azure SQL through `pyodbc` and T-SQL.
- `azure_sql_schema.sql` creates or updates the SQL schema during the first deployment.

## Current database mode

Version 71 still defaults to local SQLite. No Azure setting is enabled automatically, and the existing SQLite database remains the active source of truth until `DLS_DATABASE_TYPE=azure-sql` is deliberately configured for the Azure deployment.

The Azure SQL files are readiness tooling only while SQLite is active. Do not run the SQLite and Azure SQL environments as simultaneous writable production systems during the eventual cutover.

## v071 reviewed-baseline, startup, and packaging note

The v061 full sweep added source documentation, regression tests, and connection-lifecycle cleanup; v063 repaired production startup collisions; v070 established the Microsoft Graph transport and maintained launcher behavior; v071 documents the reviewed architecture and does not activate Azure SQL. The included Azure schema and compatibility adapter remain validated as readiness components; a live Azure SQL deployment still requires the controlled cutover steps in this guide.


## v071 UI and shared-workflow readiness note

Version 71 adds no schema migration or runtime workflow change. The Microsoft Graph email delivery introduced in v070 reuses the existing outbox and automatic message workflow. The rebuilt header/profile layout, compact Bay scanner command surface, SDI item workspace, strict departed-rack manifest, and date-wide Outbound reconciliation use the existing shared application and store layers. The future Azure SQL backend follows the same business workflow, while SQLite remains active until the deliberate cutover.

## Route data readiness in v070

Version 69 retains the active Customer Route Rules as the primary routing source. The resolved route is stored in `line_items.route`, while the original imported ROUTE value is retained in `line_items.source_route`. This allows a later rule change to reroute existing items without losing the original source value.

The `system_metadata` table stores a route-repair signature. SQLite and Azure SQL run the route-stage reconciliation only when the routing logic version or active customer rules change, rather than scanning all line items during every startup. This table is included in the SQLite-to-Azure migration utility.

## What changes when Azure SQL is enabled

Set `DLS_DATABASE_TYPE=azure-sql`. At startup the application selects `AzureSqlDeliveryStore` instead of `SQLiteDeliveryStore`.

1. The app connects to Azure SQL using `DLS_DATABASE_CONNECTION_STRING`.
2. When `DLS_DATABASE_AUTO_SCHEMA=1`, the idempotent schema script runs and missing columns are added.
3. Default roles, permissions, racks, bays, route rules, and the initial administrator are seeded through the same existing startup workflow.
4. Every browser and scanner then reads and writes the same Azure SQL database.
5. The local SQLite file is no longer used by the running Azure application.

The adapter preserves one business-logic path. It translates the limited SQLite syntax already used by the project, including `LIMIT`, `INSERT OR IGNORE`, and `ON CONFLICT`, instead of maintaining a second copy of each scan/import/rack/bay method.

## Azure resources

Create these resources in the same Azure region:

1. Resource group.
2. Azure Container Registry.
3. Azure SQL logical server and Azure SQL Database.
4. Linux Azure App Service plan.
5. Web App for Containers.
6. Optional Azure Storage account and Azure Files share for delivery-list import files.

For production, use App Service and Azure SQL private networking when practical. For the first controlled deployment, SQL firewall rules can be used while the private-network design is completed.

For the public-endpoint approach, allow the Web App's outbound IP addresses through the Azure SQL firewall and review those rules whenever the App Service plan or scale configuration changes. For the private approach, use App Service virtual-network integration for outbound traffic, an Azure SQL private endpoint, and private DNS resolution.

## Build and publish the container

From the project folder:

```powershell
az login
az acr login --name <registry-name>
docker build -t <registry-name>.azurecr.io/delivery-list-scanner:v071 .
docker push <registry-name>.azurecr.io/delivery-list-scanner:v071
```

Configure the App Service to use that image. The included container listens on `0.0.0.0:8000`. Set `PORT=8000` inside the container and `WEBSITES_PORT=8000` in the App Service environment so App Service routes requests to the correct container port.

## Enable managed identity

In the Web App:

1. Open **Identity**.
2. Enable the system-assigned managed identity.
3. Save and copy the identity name/object details.

Set a Microsoft Entra administrator on the Azure SQL logical server. Connect to the target database as that administrator and run:

```sql
CREATE USER [<web-app-name>] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [<web-app-name>];
ALTER ROLE db_datawriter ADD MEMBER [<web-app-name>];
ALTER ROLE db_ddladmin ADD MEMBER [<web-app-name>];
```

`db_ddladmin` is needed while automatic schema initialization is enabled. After the first successful deployment, set `DLS_DATABASE_AUTO_SCHEMA=0`. You may then remove `db_ddladmin` if future schema upgrades will be applied through a controlled deployment account instead:

```sql
ALTER ROLE db_ddladmin DROP MEMBER [<web-app-name>];
```

## App Service environment variables

Use `.env.azure.example` as the checklist. Add the values under **Settings > Environment variables** in the Web App.

Important values:

```text
DLS_ENVIRONMENT=production
DLS_DATABASE_TYPE=azure-sql
DLS_DATABASE_CONNECTION_STRING=Driver={ODBC Driver 18 for SQL Server};Server=tcp:<server>.database.windows.net,1433;Database=<database>;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;Authentication=ActiveDirectoryMsi;
DLS_DATABASE_AUTO_SCHEMA=1
DLS_HOST=0.0.0.0
PORT=8000
WEBSITES_PORT=8000
DLS_BASE_URL=https://<web-app>.azurewebsites.net/
DLS_SESSION_SECRET=<long-random-secret>
DLS_DEFAULT_ADMIN_PASSWORD=<temporary-strong-password>
DLS_DAILY_IMPORT_ENABLED=0
```

Do not place a SQL username or password in the managed-identity connection string.

`PORT` controls the port used by `server.py` inside the container. `WEBSITES_PORT` tells Azure App Service which exposed container port should receive incoming web traffic.

## First deployment sequence

1. Keep the App Service at one running instance for the initial schema deployment.
2. Deploy the container.
3. Enable the App Service managed identity.
4. Create the Azure SQL database user and role memberships.
5. Add the environment variables.
6. Restart the Web App.
7. Open `/api/health`. Confirm that `mode` is `azure-sql` and that the Azure database/server names are returned.
8. Sign in with the configured initial administrator.
9. Change the initial administrator password immediately.
10. Confirm users, racks, bays, route rules, imports, scans, undo/redo, printing, and Spanish mode in a staging slot.
11. Set `DLS_DATABASE_AUTO_SCHEMA=0` after schema initialization is confirmed.
12. Remove `db_ddladmin` if schema changes will use a controlled deployment identity, then scale the App Service beyond one instance only after this step.

## Move the existing SQLite data

Keep the current SQLite database backed up and stop writes during the final migration window.

For a new Azure SQL database, initialize the schema and migrate in one controlled command before the production Web App begins writing data:

```powershell
$env:DLS_DATABASE_CONNECTION_STRING = '<Azure SQL ODBC connection string with migration permissions>'
python migrate_sqlite_to_azure_sql.py --initialize-schema --sqlite-path '.\data\delivery-scanner-pilot.db'
```

The migration utility:

- Can initialize the idempotent Azure SQL schema before copying.
- Copies tables in dependency order.
- Preserves identity IDs.
- Refuses to write into non-empty Azure tables unless `--replace` is supplied.
- Reseeds Azure identity values after copying.
- Prints a row count for every table.

Use `--replace` only against a backup-protected target database that is intentionally being rebuilt.

## Delivery-list import folder

The existing `I:` drive path will not exist inside Azure. Choose one of these approaches:

- Mount an Azure Files share into the App Service container, then set `DLS_TEMP_DELIVERY_LISTS_PATH` to the Linux mount path, such as `/mount/delivery-lists`.
- Keep the existing on-premises import process and upload files through an API/import screen.
- Add direct Azure Blob Storage ingestion in a later version.

Until a shared Azure path is configured, keep `DLS_DAILY_IMPORT_ENABLED=0` so the cloud server does not repeatedly look for the local plant drive.

When the Web App is scaled to multiple instances, do not enable the built-in daily importer on every instance. Run imports from one controlled worker/scheduled job, or add a database-backed distributed lock first, so the same file cannot be imported concurrently by several containers.

## Production rollout

Use an App Service deployment slot:

1. Deploy v071 to a staging slot.
2. Point the staging slot at a separate test Azure SQL database.
3. Run functional and scanner testing.
4. Back up the production SQLite database.
5. Stop the local server so no additional SQLite writes occur.
6. Run the final migration with `--initialize-schema` against a new production Azure SQL database.
7. Point the production slot to that production Azure SQL database.
8. Swap the tested staging release into production.
9. Keep the local system read-only until the Azure deployment is verified.

## Backups and monitoring

- Enable Azure SQL backup retention appropriate for the business.
- Turn on App Service logs and Azure Application Insights.
- Monitor `/api/health`.
- Configure alerts for HTTP 5xx responses, container restarts, Azure SQL connection failures, high database CPU, and storage limits.
- Never run both SQLite and Azure SQL as active writable production databases at the same time.

## Microsoft Graph email with Azure managed identity

Version 71 retains the Microsoft Graph managed-identity support introduced in v070, allowing Azure App Service email without a stored client secret.

Configure App Service settings:

```text
DLS_EMAIL_TRANSPORT=graph
DLS_GRAPH_AUTH_MODE=managed-identity
DLS_GRAPH_SENDER=BarefootNC.Glass@bldr.com
DLS_EMAIL_FROM=BarefootNC.Glass@bldr.com
DLS_EMAIL_TEST_RECIPIENT=brandon.m.smith@bldr.com
DLS_GRAPH_SAVE_TO_SENT_ITEMS=1
```

Enable the App Service system-assigned managed identity. A Microsoft 365/Exchange administrator must grant that service principal `Application Mail.Send`, preferably through Exchange Online RBAC scoped to a mail-enabled security group containing only `BarefootNC.Glass@bldr.com`. Do not add a client secret to App Service for this mode.

The runtime requests the Graph token from the App Service `IDENTITY_ENDPOINT` using the rotating `IDENTITY_HEADER` provided by Azure. For a user-assigned identity, also set `DLS_GRAPH_MANAGED_IDENTITY_CLIENT_ID`.

See `docs/MICROSOFT_GRAPH_EMAIL.md` for the complete local test and least-privilege Exchange setup.
