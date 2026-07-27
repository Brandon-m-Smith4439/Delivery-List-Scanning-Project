# v142 Roles, Rejects, and Layout Refinements

## Custom roles

The existing database already stores roles and role-permission mappings, so v142 adds an API and interface without changing the schema. `Apply-v142-RoleManagementPatch.bat` modifies only the current `delivery_store.py` and `server.py`, after creating timestamped backups. It is safe to run again; the marker prevents duplicate insertion.

Role creation validates the name and every requested permission, rejects case-insensitive duplicates, writes the role and permission mappings in one transaction, and records an audit event. A role may intentionally start with no permissions after confirmation.

## Create User layout

The create form now uses two balanced sections:

- **Account details:** BFS email, username, display name, and temporary password.
- **Starting access:** role and station assignment with a short safety reminder.

Custom roles are read from the server-backed Admin role state, not a hard-coded dropdown list.

## Reject Tracking

The page now has one visual hierarchy rather than separate command and history headers. Search, date preset, custom date range, Refresh, and Clear controls live in one toolbar.

On the Scan page, the compact `IR` flag remains in the Flags column. Detailed incident information is rendered in a full-width strip immediately below the affected line so long reasons, machine/location names, and timestamps remain readable without distorting the Job Nr. column.

## CSS ownership

v142 reuses the current role-permission, User Manager, Reject, filter, and sidebar structures. New selectors are limited to new v142 components; existing shared controls and button primitives remain authoritative.
