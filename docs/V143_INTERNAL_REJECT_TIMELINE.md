# V143 Internal Reject Timeline

V143 applies the approved Internal Rejects concept to the maintained page without changing reject persistence or reset behavior.

## Layout

- Quality Recovery header with a prominent Internal Rejects title and primary Log Internal Reject action.
- Compact Refresh and Clear controls.
- Search, incident range, custom date range, and live location filtering.
- One horizontal summary strip showing filtered event, location, user, and quantity totals.
- Rejects grouped by the date and time they were logged.
- A timeline card for each event showing the operational fields needed at a glance.
- Expandable detail content for customer, job, product, and investigation notes.

## Preserved behavior

- The existing `/api/rejects` history request remains authoritative.
- Search and date constraints are still applied by the server.
- Location filtering is applied locally to the loaded result set for immediate response.
- The existing Log Internal Reject modal and process-restart API are unchanged.
- Reject reasons and break locations continue to load from the maintained catalog endpoint.
