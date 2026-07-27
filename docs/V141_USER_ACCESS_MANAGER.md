# v141 User Access Management Redesign

## Purpose

The Edit Users window had grown into a wide table containing identity, email, role, station assignment, permissions, password controls, status, and destructive actions. The table required too many columns to remain readable and caused account controls to compete for horizontal space.

v141 replaces that layout with one focused workspace that scales from full desktop displays down to narrow scanner screens.

## Layout

The modal now contains three owned regions:

1. **Account summary** — total, active, signed-in, and inactive counts.
2. **Create user** — an expandable guided form that remains available without permanently consuming the directory height.
3. **User directory** — search, status filter, role filter, and expandable user cards.

Each user card keeps the most important information visible while collapsed:

- Display name
- BFS email
- Username
- Primary role
- Assigned-station count
- Active/inactive state
- Signed-in/logged-out state

Expanding a card reveals:

- Access and profile settings
- Multi-station assignment
- Permission and stage-access summary
- Password generation/reset controls
- Activate/deactivate and delete actions

## Behavior preserved

The redesign reuses the existing data attributes and maintained handlers for:

- `data-update-user-role`
- `data-user-role-select`
- `data-user-station-list`
- `data-user-email`
- `data-generate-user-password`
- `data-toggle-password`
- `data-update-user-password`
- `data-deactivate-user`
- `data-reactivate-user`
- `data-delete-user`

No user API, permission model, database schema, or authentication behavior changed.

## Responsive behavior

- The modal owns a fixed-height workspace so the directory scrolls inside the dialog rather than widening the page.
- User cards use three panels on wide screens, two panels on compact desktop screens, and one column on tablet/mobile layouts.
- The collapsed user summary reorganizes into stacked metadata below 820 pixels.
- Station assignments scroll inside their own compact area when many stations exist.

## Maintenance rule

Future user-management changes should extend the `user-manager-*` component classes and reuse the existing user action attributes. Do not reintroduce a wide user table or append release-specific overrides for the same component.
