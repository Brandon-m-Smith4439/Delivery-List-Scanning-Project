# Delivery List Scanner Code Reference
Generated from the current source by `tools/generate_code_reference.py`. Regenerate this file after structural edits so line numbers and ownership maps remain accurate.
## Architecture and source of truth
- `index.html` owns stable page/modal anchors; `app.js` owns browser state, API calls, rendering, and event wiring.
- `styles.css` owns visual presentation and responsive behavior. Update an existing ownership section before adding a late override.
- `server.py` translates HTTP requests into store calls and renders print/export responses. Business rules should remain in `delivery_store.py`.
- `Start-DeliveryScannerWebApp.bat` delegates to the documented PowerShell launcher, which validates Python, waits for health, and preserves startup diagnostics.
- `delivery_store.py` is the source of truth for authentication, imports, route resolution, scans, racks, bays, Rush/Remake workflows, reports, and persistence.
- SQLite is the active/default backend. `azure_sql_compat.py` and `azure_sql_schema.sql` preserve a deliberate future Azure SQL cutover path.
- Customer Route Rules are authoritative after the explicit CPU-Air Job Nr. override; imported route values are fallback evidence.

## Startup and request flow
1. `scanner_config.load_config()` reads environment settings.
2. `delivery_store.create_store()` selects SQLite unless Azure SQL is explicitly enabled.
3. The store initializes schema, performs versioned/idempotent repairs, and seeds required defaults.
4. `server.Handler` serves the static frontend and `/api/*` routes.
5. `app.js` authenticates, loads metadata/lists, renders the active page, and keeps scanner/rack/bay state synchronized through shared API helpers.

## Inventory totals
- Python functions/methods: **602**
- Named JavaScript functions: **704**
- PowerShell launcher functions: **7**
- API route checks: **105**
- Azure SQL tables: **31**
- Stable HTML IDs: **288**
- Documented CSS sections: **11**

## Python function and method reference
| File | Function / method | Line | Purpose | Approximate callers |
|---|---|---:|---|---|
| `azure_sql_compat.py` | `_load_sql_dependencies` | 36 | Load SQL dependencies for the delivery-list scanner workflow. | `build_merge_statement`, `connect_azure_sql`, `transpile_sqlite_sql` |
| `azure_sql_compat.py` | `AzureSqlRow.__init__` | 56 | Initialize a Azure SQL row instance and its required state. | `__init__` |
| `azure_sql_compat.py` | `AzureSqlRow.__getitem__` | 68 | Implement the getitem protocol for Azure SQL row. | — |
| `azure_sql_compat.py` | `AzureSqlRow.__iter__` | 78 | Implement the iter protocol for Azure SQL row. | — |
| `azure_sql_compat.py` | `AzureSqlRow.__len__` | 86 | Implement the len protocol for Azure SQL row. | — |
| `azure_sql_compat.py` | `AzureSqlRow.keys` | 94 | Run the keys workflow for the delivery-list scanner. | — |
| `azure_sql_compat.py` | `AzureSqlRow.values` | 102 | Run the values workflow for the delivery-list scanner. | — |
| `azure_sql_compat.py` | `AzureSqlRow.items` | 110 | Run the items workflow for the delivery-list scanner. | — |
| `azure_sql_compat.py` | `AzureSqlMemoryCursor.fetchone` | 126 | Run the fetchone workflow for the delivery-list scanner. | `execute`, `fetchone`, `test_azure_cursor_and_connection_transaction_lifecycle`, `test_azure_row_and_memory_cursor_behave_like_sqlite_rows` |
| `azure_sql_compat.py` | `AzureSqlMemoryCursor.fetchall` | 138 | Run the fetchall workflow for the delivery-list scanner. | `__iter__`, `fetchall`, `test_azure_cursor_and_connection_transaction_lifecycle`, `test_azure_row_and_memory_cursor_behave_like_sqlite_rows` |
| `azure_sql_compat.py` | `AzureSqlMemoryCursor.__iter__` | 148 | Implement the iter protocol for Azure SQL memory cursor. | — |
| `azure_sql_compat.py` | `AzureSqlCursor.__init__` | 158 | Initialize a Azure SQL cursor instance and its required state. | `__init__` |
| `azure_sql_compat.py` | `AzureSqlCursor._columns` | 169 | Run the columns workflow for the delivery-list scanner. | — |
| `azure_sql_compat.py` | `AzureSqlCursor.fetchone` | 179 | Run the fetchone workflow for the delivery-list scanner. | `execute`, `fetchone`, `test_azure_cursor_and_connection_transaction_lifecycle`, `test_azure_row_and_memory_cursor_behave_like_sqlite_rows` |
| `azure_sql_compat.py` | `AzureSqlCursor.fetchall` | 190 | Run the fetchall workflow for the delivery-list scanner. | `__iter__`, `fetchall`, `test_azure_cursor_and_connection_transaction_lifecycle`, `test_azure_row_and_memory_cursor_behave_like_sqlite_rows` |
| `azure_sql_compat.py` | `AzureSqlCursor.__iter__` | 199 | Implement the iter protocol for Azure SQL cursor. | — |
| `azure_sql_compat.py` | `_normalize_sql` | 210 | Normalize SQL for the delivery-list scanner workflow. | `execute`, `transpile_sqlite_sql` |
| `azure_sql_compat.py` | `_inline_limit_parameters` | 219 | Inline numeric LIMIT parameters before transpiling to TOP. | `execute` |
| `azure_sql_compat.py` | `_table_and_columns` | 242 | Run the table and columns workflow for the delivery-list scanner. | `build_merge_statement` |
| `azure_sql_compat.py` | `_source_value_sql` | 254 | Run the source value SQL workflow for the delivery-list scanner. | `build_merge_statement` |
| `azure_sql_compat.py` | `_update_value_sql` | 263 | Update value SQL for the delivery-list scanner workflow. | `build_merge_statement` |
| `azure_sql_compat.py` | `transform` | 271 | Run the transform workflow for the delivery-list scanner. | `_update_value_sql` |
| `azure_sql_compat.py` | `build_merge_statement` | 300 | Translate one-row SQLite INSERT OR IGNORE / ON CONFLICT into MERGE. | `execute` |
| `azure_sql_compat.py` | `transpile_sqlite_sql` | 358 | Translate ordinary SQLite statements into Azure SQL T-SQL. | `execute`, `executemany` |
| `azure_sql_compat.py` | `AzureSqlConnection.__init__` | 371 | Initialize a Azure SQL connection instance and its required state. | `__init__` |
| `azure_sql_compat.py` | `AzureSqlConnection.__enter__` | 380 | Enter the Azure SQL connection context and return the active resource. | — |
| `azure_sql_compat.py` | `AzureSqlConnection.__exit__` | 388 | Finish the Azure SQL connection context and release its resources. | `__exit__` |
| `azure_sql_compat.py` | `AzureSqlConnection.close` | 403 | Run the close workflow for the delivery-list scanner. | `__exit__`, `close` |
| `azure_sql_compat.py` | `AzureSqlConnection.commit` | 411 | Run the commit workflow for the delivery-list scanner. | `__exit__`, `commit` |
| `azure_sql_compat.py` | `AzureSqlConnection.rollback` | 419 | Run the rollback workflow for the delivery-list scanner. | `__exit__`, `rollback` |
| `azure_sql_compat.py` | `AzureSqlConnection.execute_tsql` | 427 | Execute trusted T-SQL without SQLite-dialect translation. | — |
| `azure_sql_compat.py` | `AzureSqlConnection.execute` | 434 | Run the execute workflow for the delivery-list scanner. | `connect_azure_sql`, `execute`, `execute_tsql`, `test_migration_identifier_and_column_helpers` |
| `azure_sql_compat.py` | `AzureSqlConnection.executemany` | 489 | Run the executemany workflow for the delivery-list scanner. | `executemany` |
| `azure_sql_compat.py` | `connect_azure_sql` | 502 | Run the connect Azure SQL workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `ClosingSQLiteConnection.__exit__` | 66 | Finish the closing SQLite connection context and release its resources. | `__exit__` |
| `delivery_store.py` | `now_iso` | 250 | Run the now iso workflow for the delivery-list scanner. | `acknowledge_notification`, `add_customer_route_rule`, `add_manual_edit_lookup`, `add_station`, `admin_summary`, `assign_bay`, `assign_line_items_to_bay`, `assign_transportation_from_outbound_override` (+65 more) |
| `delivery_store.py` | `parse_iso` | 259 | Parse iso for the delivery-list scanner workflow. | `bay_from_row`, `confirm_password_reset`, `get_stale_bay_orders`, `get_user_by_session` |
| `delivery_store.py` | `hash_password` | 268 | Run the hash password workflow for the delivery-list scanner. | `confirm_password_reset`, `create_user`, `seed_security_data`, `seed_user_if_missing`, `update_user_password` |
| `delivery_store.py` | `verify_password` | 283 | Run the verify password workflow for the delivery-list scanner. | `authenticate_user` |
| `delivery_store.py` | `session_token_hash` | 301 | Run the session token hash workflow for the delivery-list scanner. | `authenticate_user`, `confirm_password_reset`, `delete_session`, `get_user_by_session`, `request_password_reset` |
| `delivery_store.py` | `stage_access_for_roles` | 310 | Run the stage access for roles workflow for the delivery-list scanner. | `user_can_access_stage`, `user_from_row` |
| `delivery_store.py` | `user_can_access_stage` | 326 | Run the user can access stage workflow for the delivery-list scanner. | `_get_payload`, `get_delivery_lists`, `global_search`, `user_can_access_list` |
| `delivery_store.py` | `clean_barcode` | 341 | Run the clean barcode workflow for the delivery-list scanner. | `create_manual_bay_line_item`, `find_manual_bay_line_items`, `normalize_rack_code`, `parse_rack_barcode`, `recover_scan`, `resolve_sdi_destination_rows`, `scan_other_list_hint`, `scan_out_bay_item` |
| `delivery_store.py` | `normalize_rack_code` | 351 | Normalize rack code for the delivery-list scanner workflow. | `assign_line_item_to_rack`, `assign_transportation_from_outbound_override`, `clear_rack`, `complete_rack`, `delete_rack`, `get_rack_by_code`, `move_rack_item`, `not_on_way_rack` (+9 more) |
| `delivery_store.py` | `parse_rack_barcode` | 365 | Parse rack barcode for the delivery-list scanner workflow. | `record_scan`, `scan_rack_outbound` |
| `delivery_store.py` | `rack_barcode_text` | 390 | Run the rack barcode text workflow for the delivery-list scanner. | `rack_packing_list` |
| `delivery_store.py` | `digits_only` | 401 | Run the digits only workflow for the delivery-list scanner. | `create_manual_bay_line_item`, `find_manual_bay_line_items`, `get_print_package`, `rack_barcode_text`, `recover_scan`, `resolve_sdi_destination_rows`, `scan_out_bay_item`, `search_filters_match` |
| `delivery_store.py` | `normalized_match_text` | 410 | Run the normalized match text workflow for the delivery-list scanner. | `_indian_trail_in_transit_payload`, `bay_manual_text_is_known`, `canonical_route_designation`, `cpu_job_route_hint`, `find_sdi_line_items`, `fuzzy_contains`, `get_sdi_workspace`, `inferred_route` (+7 more) |
| `delivery_store.py` | `simplified_match_text` | 419 | Run the simplified match text workflow for the delivery-list scanner. | `fuzzy_contains` |
| `delivery_store.py` | `is_valid_email` | 431 | Validate valid email for the delivery-list scanner workflow. | `create_user`, `queue_customer_email_test`, `queue_email_message`, `update_user_roles`, `upsert_customer_email_cc`, `upsert_customer_email_contact` |
| `delivery_store.py` | `fuzzy_contains` | 441 | Run the fuzzy contains workflow for the delivery-list scanner. | `customer_email_matches`, `default_customer_route`, `destination_address_for_rack`, `rack_packing_list`, `route_from_customer_rules` |
| `delivery_store.py` | `default_customer_route` | 458 | Run the default customer route workflow for the delivery-list scanner. | `inferred_route` |
| `delivery_store.py` | `canonical_barcode` | 474 | Run the canonical barcode workflow for the delivery-list scanner. | `clone_item_for_list`, `recover_scan`, `update_line_item` |
| `delivery_store.py` | `format_display_date` | 483 | Normalize display date for the delivery-list scanner workflow. | `build_delivery_lists`, `ensure_manual_bay_delivery_list`, `ensure_manual_route_list`, `queue_ready_email_if_customer_complete`, `rack_packing_list`, `scan_other_list_hint`, `send_customer_manifests_for_import` |
| `delivery_store.py` | `parse_dimension_number` | 495 | Parse dimension number for the delivery-list scanner workflow. | `suggested_bay` |
| `delivery_store.py` | `route_signal_text` | 520 | Run the route signal text workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `cpu_job_route_hint` | 546 | Return the only supported Job Nr. destination overrides. | `canonical_route_designation`, `job_number_route_hint` |
| `delivery_store.py` | `canonical_route_designation` | 575 | Resolve an operational route designation to the stored route code. | `add_customer_route_rule`, `normalize_route_column`, `public_route_label`, `resolve_item_route` |
| `delivery_store.py` | `normalize_route_column` | 619 | Return whether ROUTE was supplied and its canonical route code. | `clone_item_for_list`, `inferred_route`, `resolve_item_route`, `update_line_item` |
| `delivery_store.py` | `job_number_route_hint` | 628 | Return the supported CPU-Air/CPU-IT override from Job Nr. | `clone_item_for_list`, `inferred_route`, `resolve_item_route` |
| `delivery_store.py` | `inferred_route` | 633 | Run the inferred route workflow for the delivery-list scanner. | `clone_item_for_list`, `custom_route_codes`, `items_for_profile`, `route_category` |
| `delivery_store.py` | `route_category` | 663 | Run the route category workflow for the delivery-list scanner. | `custom_route_codes`, `destination_for_line_item`, `is_cpu_item`, `items_for_profile`, `preassign_bay_for_outbound`, `route_matches` |
| `delivery_store.py` | `custom_route_codes` | 681 | Run the custom route codes workflow for the delivery-list scanner. | `build_delivery_lists` |
| `delivery_store.py` | `route_stage_label` | 695 | Run the route stage label workflow for the delivery-list scanner. | `build_delivery_lists`, `destination_for_line_item` |
| `delivery_store.py` | `public_route_label` | 711 | Return the route label that may appear on printed or exported documents. | `export_csv`, `export_package_xlsx`, `export_xlsx`, `send_customer_manifests_for_import` |
| `delivery_store.py` | `receiving_stage_destination` | 731 | Run the receiving stage destination workflow for the delivery-list scanner. | `_get_line_items`, `received_qty_for_rack_item` |
| `delivery_store.py` | `is_cpu_item` | 749 | Validate CPU item for the delivery-list scanner workflow. | `import_delivery_list`, `items_for_profile`, `preview_import`, `receive_indian_trail_scan`, `route_matches` |
| `delivery_store.py` | `normalized_bay_auto_assign_settings` | 758 | Run the normalized bay auto assign settings workflow for the delivery-list scanner. | `bay_auto_assign_settings_from_rows`, `suggested_bay`, `update_bay_auto_assign_settings` |
| `delivery_store.py` | `suggested_bay` | 781 | Run the suggested bay workflow for the delivery-list scanner. | `clone_item_for_list`, `preview_import`, `suggested_bay_from_settings` |
| `delivery_store.py` | `items_for_profile` | 804 | Run the items for profile workflow for the delivery-list scanner. | `build_delivery_lists` |
| `delivery_store.py` | `build_delivery_lists` | 824 | Build delivery lists for the delivery-list scanner workflow. | `import_delivery_folder`, `import_delivery_list`, `seed_demo_data` |
| `delivery_store.py` | `all_profile_list_ids` | 864 | Run the all profile list IDs workflow for the delivery-list scanner. | `import_delivery_list` |
| `delivery_store.py` | `parse_int_text` | 873 | Parse int text for the delivery-list scanner workflow. | `parse_aw_delivery_workbook`, `parse_delivery_csv`, `update_line_item` |
| `delivery_store.py` | `clean_excel_text` | 889 | Run the clean excel text workflow for the delivery-list scanner. | `read_xlsx_rows` |
| `delivery_store.py` | `format_delivery_date` | 901 | Normalize delivery date for the delivery-list scanner workflow. | `delivery_date_from_text` |
| `delivery_store.py` | `delivery_date_from_text` | 912 | Run the delivery date from text workflow for the delivery-list scanner. | `delivery_date_from_rows_or_name`, `delivery_date_from_source_header`, `import_delivery_folder`, `parse_delivery_csv` |
| `delivery_store.py` | `column_label` | 925 | Run the column label workflow for the delivery-list scanner. | `read_xlsx_rows` |
| `delivery_store.py` | `first_xlsx_sheet_path` | 935 | Run the first XLSX sheet path workflow for the delivery-list scanner. | `read_xlsx_rows` |
| `delivery_store.py` | `read_xlsx_rows` | 958 | Read XLSX rows for the delivery-list scanner workflow. | `delivery_date_from_source_header`, `parse_aw_delivery_workbook` |
| `delivery_store.py` | `delivery_date_from_rows_or_name` | 999 | Run the delivery date from rows or name workflow for the delivery-list scanner. | `delivery_date_from_source_header`, `parse_aw_delivery_workbook` |
| `delivery_store.py` | `delivery_date_from_source_header` | 1015 | Run the delivery date from source header workflow for the delivery-list scanner. | `import_delivery_folder` |
| `delivery_store.py` | `parse_aw_delivery_workbook` | 1037 | Parse aw delivery workbook for the delivery-list scanner workflow. | `load_delivery_source_payload` |
| `delivery_store.py` | `parse_delivery_csv` | 1087 | Parse a delivery-list CSV while honoring an in-file delivery date. | `load_delivery_source_payload` |
| `delivery_store.py` | `load_delivery_source_payload` | 1140 | Load delivery source payload for the delivery-list scanner workflow. | `import_delivery_folder` |
| `delivery_store.py` | `source_file_hash` | 1156 | Run the source file hash workflow for the delivery-list scanner. | `import_delivery_folder` |
| `delivery_store.py` | `is_remake_item` | 1169 | Validate remake item for the delivery-list scanner workflow. | `get_print_package`, `glass_filter_matches`, `item_payload`, `normal_printable`, `parse_aw_delivery_workbook`, `print_counts_for_items`, `should_print_delivery_item`, `upsert_delivery_list` |
| `delivery_store.py` | `is_rush_item` | 1179 | Validate rush item for the delivery-list scanner workflow. | `get_print_package`, `item_payload`, `receive_indian_trail_scan`, `upsert_delivery_list` |
| `delivery_store.py` | `is_mirror_item` | 1189 | Validate mirror item for the delivery-list scanner workflow. | `get_print_package`, `glass_filter_matches`, `normal_printable`, `print_counts_for_items`, `should_print_delivery_item` |
| `delivery_store.py` | `should_print_delivery_item` | 1199 | Run the should print delivery item workflow for the delivery-list scanner. | `normal_printable`, `print_counts_for_items` |
| `delivery_store.py` | `print_counts_for_items` | 1212 | Run the print counts for items workflow for the delivery-list scanner. | `print_candidates_from_payload` |
| `delivery_store.py` | `row_value` | 1227 | Read a named value from sqlite3.Row, AzureSqlRow, or a dictionary. | `bay_from_row`, `customer_route_rules_from_connection`, `destination_for_line_item`, `item_from_row`, `item_payload`, `mark_sdi`, `receive_indian_trail_scan`, `repair_route_stage_memberships` (+4 more) |
| `delivery_store.py` | `item_from_row` | 1238 | Run the item from row workflow for the delivery-list scanner. | `_get_line_items`, `admin_search_line_items`, `rack_from_row` |
| `delivery_store.py` | `event_from_row` | 1271 | Run the event from row workflow for the delivery-list scanner. | `_get_scan_events`, `insert_event` |
| `delivery_store.py` | `list_meta` | 1308 | Read meta for the delivery-list scanner workflow. | `_get_payload`, `get_delivery_lists` |
| `delivery_store.py` | `request_user_name` | 1325 | Run the request user name workflow for the delivery-list scanner. | `import_delivery_folder`, `import_delivery_list`, `record_scan`, `scan_rack_outbound` |
| `delivery_store.py` | `request_station` | 1334 | Run the request station workflow for the delivery-list scanner. | `receive_indian_trail_scan`, `record_scan`, `scan_item_to_rack`, `scan_out_bay_item`, `scan_rack_outbound` |
| `delivery_store.py` | `BaseDeliveryStore.initialize` | 1346 | Run the initialize workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.health` | 1354 | Run the health workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_delivery_lists` | 1362 | Read delivery lists for the delivery-list scanner workflow. | `delete_delivery_date`, `delete_delivery_list`, `import_delivery_folder`, `import_delivery_list` |
| `delivery_store.py` | `BaseDeliveryStore.get_delivery_list` | 1370 | Read delivery list for the delivery-list scanner workflow. | `get_print_package` |
| `delivery_store.py` | `BaseDeliveryStore.get_line_items` | 1378 | Read line items for the delivery-list scanner workflow. | `export_csv`, `export_xlsx` |
| `delivery_store.py` | `BaseDeliveryStore.create_app_notification` | 1386 | Create app notification for the delivery-list scanner workflow. | `mark_sdi` |
| `delivery_store.py` | `BaseDeliveryStore.get_pending_notifications` | 1442 | Read pending notifications for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.acknowledge_notification` | 1492 | Run the acknowledge notification workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.record_scan` | 1525 | Process scan for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.undo_last_scan` | 1533 | Undo last scan for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.redo_last_undo` | 1541 | Redo last undo for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.reset_stage` | 1549 | Run the reset stage workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.import_delivery_list` | 1557 | Load delivery list for the delivery-list scanner workflow. | `import_delivery_folder` |
| `delivery_store.py` | `BaseDeliveryStore.import_delivery_folder` | 1565 | Load delivery folder for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_print_package` | 1793 | Read print package for the delivery-list scanner workflow. | `export_package_xlsx` |
| `delivery_store.py` | `BaseDeliveryStore.get_scan_events` | 1801 | Read scan events for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_exceptions` | 1809 | Read exceptions for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_stations` | 1817 | Read stations for the delivery-list scanner workflow. | `add_station`, `remove_station`, `rename_station` |
| `delivery_store.py` | `BaseDeliveryStore.add_station` | 1825 | Create station for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.rename_station` | 1833 | Update station for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_station` | 1841 | Remove station for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.export_csv` | 1849 | Export CSV for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.export_xlsx` | 1857 | Export XLSX for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.export_package_xlsx` | 1865 | Export package XLSX for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.authenticate_user` | 1873 | Run the authenticate user workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_user_by_session` | 1881 | Read user by session for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.delete_session` | 1889 | Remove session for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.create_user` | 1897 | Create user for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.list_users` | 1905 | Read users for the delivery-list scanner workflow. | `deactivate_user`, `delete_user`, `reactivate_user`, `update_user_password`, `update_user_roles` |
| `delivery_store.py` | `BaseDeliveryStore.deactivate_user` | 1913 | Run the deactivate user workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.reactivate_user` | 1921 | Run the reactivate user workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.delete_user` | 1929 | Remove user for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.update_user_password` | 1937 | Update user password for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.update_user_roles` | 1945 | Update user roles for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.list_active_sessions` | 1953 | Read active sessions for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_permissions` | 1961 | Read permissions for the delivery-list scanner workflow. | `update_role_permissions` |
| `delivery_store.py` | `BaseDeliveryStore.list_roles` | 1969 | Read roles for the delivery-list scanner workflow. | `update_role_permissions` |
| `delivery_store.py` | `BaseDeliveryStore.update_role_permissions` | 1977 | Update role permissions for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.preview_import` | 1985 | Run the preview import workflow for the delivery-list scanner. | `import_delivery_folder` |
| `delivery_store.py` | `BaseDeliveryStore.admin_summary` | 1993 | Run the admin summary workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.resolve_exception` | 2001 | Resolve exception for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.global_search` | 2009 | Run the global search workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.stage_kind` | 2060 | Run the stage kind workflow for the delivery-list scanner. | `global_search`, `representative_rank` |
| `delivery_store.py` | `BaseDeliveryStore.representative_rank` | 2081 | Run the representative rank workflow for the delivery-list scanner. | `global_search` |
| `delivery_store.py` | `BaseDeliveryStore.rack_location_label` | 2109 | Run the rack location label workflow for the delivery-list scanner. | `global_search` |
| `delivery_store.py` | `BaseDeliveryStore.airport_label` | 2124 | Run the airport label workflow for the delivery-list scanner. | `global_search` |
| `delivery_store.py` | `BaseDeliveryStore.update_line_item` | 2253 | Update line item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.delete_delivery_list` | 2261 | Remove delivery list for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.delete_delivery_date` | 2269 | Remove delivery date for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.delete_line_item` | 2277 | Remove line item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_customer_route_rules` | 2285 | Read customer route rules for the delivery-list scanner workflow. | `add_customer_route_rule`, `apply_customer_route_rules_to_payload`, `remove_customer_route_rule` |
| `delivery_store.py` | `BaseDeliveryStore.add_customer_route_rule` | 2293 | Create customer route rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_customer_route_rule` | 2301 | Remove customer route rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_email_transport_config` | 2309 | Return the active server-side email transport without exposing credentials. | `acquire_graph_access_token`, `get_customer_email_settings`, `queue_customer_email_test`, `send_graph_email`, `try_send_email` |
| `delivery_store.py` | `BaseDeliveryStore.get_customer_email_settings` | 2407 | Read customer email settings for the delivery-list scanner workflow. | `queue_customer_email_test`, `remove_customer_email_cc`, `remove_customer_email_contact`, `upsert_customer_email_cc`, `upsert_customer_email_contact` |
| `delivery_store.py` | `BaseDeliveryStore.upsert_customer_email_contact` | 2484 | Run the upsert customer email contact workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_customer_email_contact` | 2523 | Remove customer email contact for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.upsert_customer_email_cc` | 2541 | Run the upsert customer email cc workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_customer_email_cc` | 2564 | Remove customer email cc for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.queue_customer_email_test` | 2582 | Create or send a customer-email test message. | — |
| `delivery_store.py` | `BaseDeliveryStore.customer_email_matches` | 2646 | Run the customer email matches workflow for the delivery-list scanner. | `queue_ready_email_if_customer_complete`, `send_customer_manifests_for_import` |
| `delivery_store.py` | `BaseDeliveryStore.customer_cc_emails` | 2661 | Run the customer cc emails workflow for the delivery-list scanner. | `queue_ready_email_if_customer_complete`, `send_customer_manifests_for_import` |
| `delivery_store.py` | `BaseDeliveryStore.queue_email_message` | 2669 | Send email message for the delivery-list scanner workflow. | `queue_ready_email_if_customer_complete`, `send_customer_manifests_for_import` |
| `delivery_store.py` | `BaseDeliveryStore.acquire_graph_access_token` | 2728 | Acquire and cache a Microsoft Graph app-only access token. | `send_graph_email` |
| `delivery_store.py` | `BaseDeliveryStore.send_graph_email` | 2826 | Send one message through Microsoft Graph as the configured mailbox. | `try_send_email` |
| `delivery_store.py` | `BaseDeliveryStore.send_smtp_email` | 2893 | Send one message through the legacy SMTP transport. | `try_send_email` |
| `delivery_store.py` | `BaseDeliveryStore.try_send_email` | 2922 | Send one email through the single configured delivery transport. | `queue_customer_email_test`, `queue_email_message` |
| `delivery_store.py` | `BaseDeliveryStore.send_customer_manifests_for_import` | 2946 | Send customer manifests for import for the delivery-list scanner workflow. | `import_delivery_list` |
| `delivery_store.py` | `BaseDeliveryStore.queue_ready_email_if_customer_complete` | 3005 | Send ready email if customer complete for the delivery-list scanner workflow. | `record_scan` |
| `delivery_store.py` | `BaseDeliveryStore.get_manual_edit_lookups` | 3041 | Read manual edit lookups for the delivery-list scanner workflow. | `add_manual_edit_lookup` |
| `delivery_store.py` | `BaseDeliveryStore.add_manual_edit_lookup` | 3049 | Create manual edit lookup for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_bay_scan_settings` | 3057 | Read bay scan settings for the delivery-list scanner workflow. | `remove_bay_manual_input_rule`, `remove_bay_scan_barcode_rule`, `upsert_bay_manual_input_rule`, `upsert_bay_scan_barcode_rule` |
| `delivery_store.py` | `BaseDeliveryStore.upsert_bay_manual_input_rule` | 3065 | Run the upsert bay manual input rule workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_bay_manual_input_rule` | 3073 | Remove bay manual input rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.upsert_bay_scan_barcode_rule` | 3081 | Run the upsert bay scan barcode rule workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_bay_scan_barcode_rule` | 3089 | Remove bay scan barcode rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.manual_assign_bay_item` | 3097 | Run the manual assign bay item workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.reports_summary` | 3105 | Run the reports summary workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_bays` | 3113 | Read bays for the delivery-list scanner workflow. | `create_bays`, `delete_bay`, `delete_bay_group`, `move_bay_group`, `set_bay_group_position`, `set_bay_status`, `update_bay_layout` |
| `delivery_store.py` | `BaseDeliveryStore.get_bay_job_details` | 3121 | Read bay job details for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_sdi_workspace` | 3129 | Return predictive SDI lookup options, exact item status, and current priority marks. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_bay_layout` | 3137 | Read bay layout for the delivery-list scanner workflow. | `seed_bays` |
| `delivery_store.py` | `BaseDeliveryStore.get_bay_events` | 3145 | Read bay events for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.indian_trail_summary` | 3153 | Run the indian trail summary workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.indian_trail_in_transit` | 3161 | Run the indian trail in transit workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.receive_indian_trail_scan` | 3169 | Process indian trail scan for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.assign_bay` | 3177 | Run the assign bay workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.move_bay_assignment` | 3185 | Run the move bay assignment workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.clear_bay` | 3193 | Remove bay for the delivery-list scanner workflow. | `bay_check` |
| `delivery_store.py` | `BaseDeliveryStore.mark_sdi` | 3201 | Run the mark SDI workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_sdi` | 3209 | Remove SDI for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.bay_check` | 3217 | Run the bay check workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.scan_out_bay_item` | 3225 | Process out bay item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.clear_bay_assignment` | 3233 | Remove bay assignment for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.restore_bay_assignment` | 3241 | Run the restore bay assignment workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.update_bay_layout` | 3249 | Update bay layout for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.set_bay_group_position` | 3257 | Update bay group position for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.__init__` | 3269 | Initialize a SQLite delivery store instance and its required state. | `__init__` |
| `delivery_store.py` | `SQLiteDeliveryStore.connect` | 3279 | Run the connect workflow for the delivery-list scanner. | `acknowledge_notification`, `add_customer_route_rule`, `add_manual_edit_lookup`, `add_station`, `admin_search_line_items`, `admin_summary`, `assign_bay`, `assign_line_item_to_rack` (+98 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.health` | 3298 | Run the health workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.initialize` | 3312 | Run the initialize workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.customer_route_rules_from_connection` | 3329 | Run the customer route rules from connection workflow for the delivery-list scanner. | `get_customer_route_rules`, `repair_route_stage_memberships`, `repair_route_stage_memberships_if_needed`, `route_stage_repair_signature` |
| `delivery_store.py` | `SQLiteDeliveryStore.route_stage_repair_signature` | 3349 | Run the route stage repair signature workflow for the delivery-list scanner. | `repair_route_stage_memberships_if_needed` |
| `delivery_store.py` | `SQLiteDeliveryStore.system_metadata_value` | 3370 | Run the system metadata value workflow for the delivery-list scanner. | `repair_route_stage_memberships_if_needed` |
| `delivery_store.py` | `SQLiteDeliveryStore.set_system_metadata_value` | 3379 | Update system metadata value for the delivery-list scanner workflow. | `repair_route_stage_memberships_if_needed` |
| `delivery_store.py` | `SQLiteDeliveryStore.repair_route_stage_memberships_if_needed` | 3396 | Reconcile route stage memberships if needed for the delivery-list scanner workflow. | `add_customer_route_rule`, `initialize`, `remove_customer_route_rule` |
| `delivery_store.py` | `SQLiteDeliveryStore.repair_route_stage_memberships` | 3414 | Repair active route copies using customer rules without slowing every startup. | `repair_route_stage_memberships_if_needed` |
| `delivery_store.py` | `SQLiteDeliveryStore.create_schema` | 3501 | Create schema for the delivery-list scanner workflow. | `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.apply_schema_migrations` | 3848 | Run the apply schema migrations workflow for the delivery-list scanner. | `create_schema` |
| `delivery_store.py` | `SQLiteDeliveryStore.ensure_column` | 3892 | Validate column for the delivery-list scanner workflow. | `apply_schema_migrations` |
| `delivery_store.py` | `SQLiteDeliveryStore.clone_item_for_list` | 3902 | Run the clone item for list workflow for the delivery-list scanner. | `insert_line_items` |
| `delivery_store.py` | `SQLiteDeliveryStore.available_line_item_id` | 3936 | Return a stable, unused line-item ID when an older stage move owns the desired ID. | `insert_line_items` |
| `delivery_store.py` | `SQLiteDeliveryStore.insert_line_items` | 3967 | Create line items for the delivery-list scanner workflow. | `upsert_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.import_order_item_key` | 4016 | Load order item key for the delivery-list scanner workflow. | `match_previous`, `upsert_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.import_business_key` | 4028 | Load business key for the delivery-list scanner workflow. | `match_previous`, `upsert_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.field` | 4034 | Run the field workflow for the delivery-list scanner. | `import_business_key` |
| `delivery_store.py` | `SQLiteDeliveryStore.upsert_delivery_list` | 4053 | Run the upsert delivery list workflow for the delivery-list scanner. | `import_delivery_list`, `seed_demo_data` |
| `delivery_store.py` | `SQLiteDeliveryStore.add_previous_to_pool` | 4108 | Create previous to pool for the delivery-list scanner workflow. | `upsert_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.pop_previous` | 4185 | Run the pop previous workflow for the delivery-list scanner. | `match_previous` |
| `delivery_store.py` | `SQLiteDeliveryStore.match_previous` | 4199 | Resolve previous for the delivery-list scanner workflow. | `upsert_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_demo_data` | 4302 | Seed the optional sample file only into a completely empty scanner database. | `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_stations` | 4332 | Create stations for the delivery-list scanner workflow. | `seed_demo_data` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_customer_route_rules` | 4342 | Create customer route rules for the delivery-list scanner workflow. | `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_security_data` | 4358 | Create security data for the delivery-list scanner workflow. | `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_user_if_missing` | 4415 | Create user if missing for the delivery-list scanner workflow. | `seed_security_data` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_bays` | 4437 | Create bays for the delivery-list scanner workflow. | `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_racks` | 4472 | Create racks for the delivery-list scanner workflow. | `get_racks`, `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.layout_bay_policy_status` | 4495 | Run the layout bay policy status workflow for the delivery-list scanner. | `seed_layout_bays` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_layout_bays` | 4511 | Create layout bays for the delivery-list scanner workflow. | `seed_bays` |
| `delivery_store.py` | `SQLiteDeliveryStore.repair_manual_assign_bay_visibility` | 4588 | Reconcile manual assign bay visibility for the delivery-list scanner workflow. | `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.list_timing_metrics` | 4632 | Read timing metrics for the delivery-list scanner workflow. | `get_delivery_lists` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_delivery_lists` | 4668 | Read delivery lists for the delivery-list scanner workflow. | `delete_delivery_date`, `delete_delivery_list`, `import_delivery_folder`, `import_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_line_items` | 4722 | Read line items for the delivery-list scanner workflow. | `export_csv`, `export_xlsx` |
| `delivery_store.py` | `SQLiteDeliveryStore._get_line_items` | 4731 | Read line items for the delivery-list scanner workflow. | `_get_payload`, `get_line_items` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_scan_events` | 4942 | Read scan events for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore._get_scan_events` | 4951 | Read scan events for the delivery-list scanner workflow. | `_get_payload`, `get_scan_events` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_delivery_list` | 4972 | Read delivery list for the delivery-list scanner workflow. | `get_print_package` |
| `delivery_store.py` | `SQLiteDeliveryStore._get_payload` | 4981 | Read payload for the delivery-list scanner workflow. | `assign_line_item_to_rack`, `delete_line_item`, `get_delivery_list`, `outbound_scan_gate`, `record_scan`, `redo_last_undo`, `reset_stage`, `scan_rack_outbound` (+2 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.user_can_access_list` | 5001 | Run the user can access list workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_stations` | 5013 | Read stations for the delivery-list scanner workflow. | `add_station`, `remove_station`, `rename_station` |
| `delivery_store.py` | `SQLiteDeliveryStore.add_station` | 5023 | Create station for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.rename_station` | 5038 | Update station for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.remove_station` | 5060 | Remove station for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_permissions` | 5077 | Read permissions for the delivery-list scanner workflow. | `update_role_permissions` |
| `delivery_store.py` | `SQLiteDeliveryStore.list_roles` | 5085 | Read roles for the delivery-list scanner workflow. | `update_role_permissions` |
| `delivery_store.py` | `SQLiteDeliveryStore.update_role_permissions` | 5108 | Update role permissions for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.user_from_row` | 5142 | Run the user from row workflow for the delivery-list scanner. | `authenticate_user`, `create_user`, `get_user_by_session`, `list_users` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_user_by_username` | 5184 | Read user by username for the delivery-list scanner workflow. | `authenticate_user`, `confirm_password_reset`, `create_user`, `deactivate_user`, `delete_user`, `reactivate_user`, `request_password_reset`, `seed_user_if_missing` (+2 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.authenticate_user` | 5200 | Run the authenticate user workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_user_by_session` | 5229 | Read user by session for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_session` | 5258 | Remove session for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.request_password_reset` | 5271 | Run the request password reset workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.confirm_password_reset` | 5306 | Run the confirm password reset workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.list_users` | 5343 | Read users for the delivery-list scanner workflow. | `deactivate_user`, `delete_user`, `reactivate_user`, `update_user_password`, `update_user_roles` |
| `delivery_store.py` | `SQLiteDeliveryStore.deactivate_user` | 5353 | Run the deactivate user workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.reactivate_user` | 5375 | Run the reactivate user workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_user` | 5394 | Remove user for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.update_user_password` | 5417 | Update user password for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.update_user_roles` | 5439 | Update user roles for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.list_active_sessions` | 5525 | Read active sessions for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.create_user` | 5557 | Create user for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_customer_route_rules` | 5596 | Read customer route rules for the delivery-list scanner workflow. | `add_customer_route_rule`, `apply_customer_route_rules_to_payload`, `remove_customer_route_rule` |
| `delivery_store.py` | `SQLiteDeliveryStore.add_customer_route_rule` | 5605 | Create customer route rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.remove_customer_route_rule` | 5673 | Remove customer route rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.send_customer_manifests_for_import` | 5693 | Send customer manifests for import for the delivery-list scanner workflow. | `import_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_manual_edit_lookups` | 5727 | Read manual edit lookups for the delivery-list scanner workflow. | `add_manual_edit_lookup` |
| `delivery_store.py` | `SQLiteDeliveryStore.add_lookup` | 5739 | Create lookup for the delivery-list scanner workflow. | `get_manual_edit_lookups` |
| `delivery_store.py` | `SQLiteDeliveryStore.add_manual_edit_lookup` | 5786 | Create manual edit lookup for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_bay_auto_assign_settings` | 5828 | Create bay auto assign settings for the delivery-list scanner workflow. | `get_bay_auto_assign_settings`, `get_bay_auto_assign_settings_con`, `initialize`, `update_bay_auto_assign_settings` |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_auto_assign_settings_from_rows` | 5845 | Run the bay auto assign settings from rows workflow for the delivery-list scanner. | `get_bay_auto_assign_settings`, `get_bay_auto_assign_settings_con` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_auto_assign_settings` | 5870 | Read bay auto assign settings for the delivery-list scanner workflow. | `update_bay_auto_assign_settings` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_auto_assign_settings_con` | 5881 | Read bay auto assign settings con for the delivery-list scanner workflow. | `bay_type_requires_manual_assignment`, `insert_line_items`, `suggested_bay_from_settings` |
| `delivery_store.py` | `SQLiteDeliveryStore.update_bay_auto_assign_settings` | 5891 | Update bay auto assign settings for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_type_requires_manual_assignment` | 5930 | Run the bay type requires manual assignment workflow for the delivery-list scanner. | `preassign_bay_for_outbound`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.suggested_bay_from_settings` | 5940 | Run the suggested bay from settings workflow for the delivery-list scanner. | `preassign_bay_for_outbound`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_manual_rule_from_row` | 5948 | Run the bay manual rule from row workflow for the delivery-list scanner. | `get_bay_scan_settings` |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_barcode_rule_from_row` | 5962 | Run the bay barcode rule from row workflow for the delivery-list scanner. | `get_bay_scan_settings` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_scan_settings` | 5975 | Read bay scan settings for the delivery-list scanner workflow. | `remove_bay_manual_input_rule`, `remove_bay_scan_barcode_rule`, `upsert_bay_manual_input_rule`, `upsert_bay_scan_barcode_rule` |
| `delivery_store.py` | `SQLiteDeliveryStore.upsert_bay_manual_input_rule` | 6001 | Run the upsert bay manual input rule workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.remove_bay_manual_input_rule` | 6030 | Remove bay manual input rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.upsert_bay_scan_barcode_rule` | 6043 | Run the upsert bay scan barcode rule workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.remove_bay_scan_barcode_rule` | 6068 | Remove bay scan barcode rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_manual_text_is_known` | 6081 | Run the bay manual text is known workflow for the delivery-list scanner. | `manual_assign_bay_item`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.find_manual_bay_line_items` | 6114 | Resolve manual bay line items for the delivery-list scanner workflow. | `find_sdi_line_items`, `manual_assign_bay_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.find_sdi_line_items` | 6157 | Resolve an SDI entry as a barcode, SO/order number, or complete Job Nr. label. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.sdi_destination_rows` | 6213 | Read one Indian Trail destination row per physical item with its active bay assignment. | `get_sdi_workspace`, `resolve_sdi_destination_rows` |
| `delivery_store.py` | `SQLiteDeliveryStore.sdi_item_presence` | 6248 | Calculate whether an Indian Trail item is physically present or still missing. | `item_payload`, `mark_sdi` |
| `delivery_store.py` | `SQLiteDeliveryStore.resolve_sdi_destination_rows` | 6274 | Resolve exact Indian Trail item rows for an SDI/Rush/Remake action. | `get_sdi_workspace`, `mark_sdi`, `remove_sdi` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_sdi_workspace` | 6338 | Build the predictive SDI modal workspace from live Indian Trail item state. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.item_payload` | 6354 | Convert one destination row into the SDI modal's item-level status payload. | `get_sdi_workspace` |
| `delivery_store.py` | `SQLiteDeliveryStore.expand_priority_line_items` | 6462 | Return every active stage clone for the selected physical glass items. | `mark_sdi`, `remove_sdi` |
| `delivery_store.py` | `SQLiteDeliveryStore.stage_rank` | 6519 | Run the stage rank workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.priority_list_context` | 6544 | Run the priority list context workflow for the delivery-list scanner. | `mark_sdi`, `remove_sdi` |
| `delivery_store.py` | `SQLiteDeliveryStore.ensure_manual_bay_delivery_list` | 6574 | Validate manual bay delivery list for the delivery-list scanner workflow. | `create_manual_bay_line_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.create_manual_bay_line_item` | 6592 | Create manual bay line item for the delivery-list scanner workflow. | `manual_assign_bay_item`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.assign_line_items_to_bay` | 6613 | Run the assign line items to bay workflow for the delivery-list scanner. | `manual_assign_bay_item`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.manual_assign_bay_item` | 6653 | Run the manual assign bay item workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.route_from_customer_rules` | 6703 | Run the route from customer rules workflow for the delivery-list scanner. | `resolve_item_route` |
| `delivery_store.py` | `SQLiteDeliveryStore.resolve_item_route` | 6728 | Resolve one item using the authoritative route order. | `apply_customer_route_rules_to_payload`, `repair_route_stage_memberships` |
| `delivery_store.py` | `SQLiteDeliveryStore.apply_customer_route_rules_to_payload` | 6747 | Run the apply customer route rules to payload workflow for the delivery-list scanner. | `import_delivery_list`, `preview_import` |
| `delivery_store.py` | `SQLiteDeliveryStore.validate_import_payload` | 6767 | Validate import payload for the delivery-list scanner workflow. | `import_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.import_delivery_list` | 6787 | Load delivery list for the delivery-list scanner workflow. | `import_delivery_folder` |
| `delivery_store.py` | `SQLiteDeliveryStore.print_candidates_from_payload` | 6889 | Run the print candidates from payload workflow for the delivery-list scanner. | `import_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.import_delivery_folder` | 6913 | Load delivery folder for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_print_package` | 7089 | Read print package for the delivery-list scanner workflow. | `export_package_xlsx` |
| `delivery_store.py` | `SQLiteDeliveryStore.has_update_marker` | 7112 | Validate update marker for the delivery-list scanner workflow. | `get_print_package` |
| `delivery_store.py` | `SQLiteDeliveryStore.route_matches` | 7121 | Run the route matches workflow for the delivery-list scanner. | `get_print_package` |
| `delivery_store.py` | `SQLiteDeliveryStore.glass_filter_matches` | 7133 | Run the glass filter matches workflow for the delivery-list scanner. | `search_filters_match` |
| `delivery_store.py` | `SQLiteDeliveryStore.search_filters_match` | 7146 | Run the search filters match workflow for the delivery-list scanner. | `get_print_package` |
| `delivery_store.py` | `SQLiteDeliveryStore.normal_printable` | 7162 | Run the normal printable workflow for the delivery-list scanner. | `get_print_package` |
| `delivery_store.py` | `SQLiteDeliveryStore.stage_sheet_kind` | 7176 | Run the stage sheet kind workflow for the delivery-list scanner. | `get_print_package` |
| `delivery_store.py` | `SQLiteDeliveryStore.find_unique_suffix_item` | 7282 | Resolve unique suffix item for the delivery-list scanner workflow. | `recover_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.find_unique_order` | 7294 | Resolve unique order for the delivery-list scanner workflow. | `recover_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.recover_scan` | 7303 | Run the recover scan workflow for the delivery-list scanner. | `receive_indian_trail_scan`, `record_scan`, `scan_item_to_rack`, `scan_other_list_hint` |
| `delivery_store.py` | `SQLiteDeliveryStore.scan_other_list_hint` | 7356 | Process other list hint for the delivery-list scanner workflow. | `receive_indian_trail_scan`, `record_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.insert_event` | 7411 | Create event for the delivery-list scanner workflow. | `auto_stage_for_outbound`, `import_delivery_list`, `mark_sdi`, `not_on_way_rack`, `outbound_scan_gate`, `receive_indian_trail_scan`, `record_scan`, `redo_last_undo` (+4 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.insert_exception` | 7455 | Create exception for the delivery-list scanner workflow. | `insert_event`, `preassign_bay_for_outbound`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.insert_audit` | 7469 | Create audit for the delivery-list scanner workflow. | `add_customer_route_rule`, `add_manual_edit_lookup`, `assign_bay`, `assign_line_item_to_rack`, `assign_transportation_from_outbound_override`, `authenticate_user`, `auto_stage_for_outbound`, `bay_check` (+66 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.record_scan` | 7493 | Process scan for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.matching_staging_row_for_outbound` | 7675 | Run the matching staging row for outbound workflow for the delivery-list scanner. | `outbound_scan_gate` |
| `delivery_store.py` | `SQLiteDeliveryStore.transportation_for_staging_row` | 7706 | Run the transportation for staging row workflow for the delivery-list scanner. | `outbound_scan_gate` |
| `delivery_store.py` | `SQLiteDeliveryStore.assign_transportation_from_outbound_override` | 7726 | Run the assign transportation from outbound override workflow for the delivery-list scanner. | `outbound_scan_gate` |
| `delivery_store.py` | `SQLiteDeliveryStore.outbound_scan_gate` | 7775 | Enforce outbound safety before a piece is scanned out. | `record_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.auto_stage_for_outbound` | 7923 | Run the auto stage for outbound workflow for the delivery-list scanner. | `outbound_scan_gate` |
| `delivery_store.py` | `SQLiteDeliveryStore.preassign_bay_for_outbound` | 8002 | Run the preassign bay for outbound workflow for the delivery-list scanner. | `record_scan`, `scan_rack_outbound` |
| `delivery_store.py` | `SQLiteDeliveryStore.reset_stage` | 8106 | Run the reset stage workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.undo_last_scan` | 8132 | Undo last scan for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.redo_last_undo` | 8172 | Redo last undo for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_exceptions` | 8217 | Read exceptions for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.preview_import` | 8259 | Run the preview import workflow for the delivery-list scanner. | `import_delivery_folder` |
| `delivery_store.py` | `SQLiteDeliveryStore.admin_summary` | 8325 | Run the admin summary workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.resolve_exception` | 8421 | Resolve exception for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.global_search` | 8448 | Run the global search workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.stage_kind` | 8499 | Run the stage kind workflow for the delivery-list scanner. | `global_search`, `representative_rank` |
| `delivery_store.py` | `SQLiteDeliveryStore.representative_rank` | 8520 | Run the representative rank workflow for the delivery-list scanner. | `global_search` |
| `delivery_store.py` | `SQLiteDeliveryStore.rack_location_label` | 8548 | Run the rack location label workflow for the delivery-list scanner. | `global_search` |
| `delivery_store.py` | `SQLiteDeliveryStore.airport_label` | 8563 | Run the airport label workflow for the delivery-list scanner. | `global_search` |
| `delivery_store.py` | `SQLiteDeliveryStore.manual_edit_sibling_rows` | 8692 | Run the manual edit sibling rows workflow for the delivery-list scanner. | `sync_manual_route_membership`, `update_line_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.manual_route_profile` | 8726 | Run the manual route profile workflow for the delivery-list scanner. | `ensure_manual_route_list`, `repair_route_stage_memberships` |
| `delivery_store.py` | `SQLiteDeliveryStore.ensure_manual_route_list` | 8745 | Validate manual route list for the delivery-list scanner workflow. | `sync_manual_route_membership` |
| `delivery_store.py` | `SQLiteDeliveryStore.merge_manual_receiving_row` | 8767 | Run the merge manual receiving row workflow for the delivery-list scanner. | `sync_manual_route_membership` |
| `delivery_store.py` | `SQLiteDeliveryStore.sync_manual_route_membership` | 8815 | Run the sync manual route membership workflow for the delivery-list scanner. | `repair_route_stage_memberships`, `update_line_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.update_line_item` | 8887 | Update line item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.update_line_item_location` | 9004 | Update line item location for the delivery-list scanner workflow. | `assign_line_item_to_rack`, `update_line_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_line_item` | 9089 | Remove line item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_delivery_list` | 9109 | Remove delivery list for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_delivery_date` | 9129 | Remove delivery date for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.reports_summary` | 9151 | Run the reports summary workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.date_clause` | 9161 | Run the date clause workflow for the delivery-list scanner. | `reports_summary` |
| `delivery_store.py` | `SQLiteDeliveryStore.delivery_list_date_clause` | 9178 | Run the delivery list date clause workflow for the delivery-list scanner. | `reports_summary` |
| `delivery_store.py` | `SQLiteDeliveryStore.list_audit_events` | 9365 | Read audit events for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_email_outbox_item` | 9403 | Read email outbox item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_from_row` | 9434 | Run the bay from row workflow for the delivery-list scanner. | `get_bays` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bays` | 9575 | Read bays for the delivery-list scanner workflow. | `create_bays`, `delete_bay`, `delete_bay_group`, `move_bay_group`, `set_bay_group_position`, `set_bay_status`, `update_bay_layout` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_job_details` | 9597 | Return live job fulfillment for one bay, including scan-in timestamps. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_layout` | 9727 | Read bay layout for the delivery-list scanner workflow. | `seed_bays` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_events` | 9739 | Return detailed Bay Map history with each item's current move target. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_stale_bay_orders` | 9800 | Read stale bay orders for the delivery-list scanner workflow. | `snooze_stale_bay_orders` |
| `delivery_store.py` | `SQLiteDeliveryStore.snooze_stale_bay_orders` | 9878 | Run the snooze stale bay orders workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.received_qty_for_rack_item` | 9910 | Run the received qty for rack item workflow for the delivery-list scanner. | `rack_from_row` |
| `delivery_store.py` | `SQLiteDeliveryStore.rack_from_row` | 9952 | Run the rack from row workflow for the delivery-list scanner. | `get_racks`, `rack_packing_list`, `scan_rack_outbound` |
| `delivery_store.py` | `SQLiteDeliveryStore.rack_summary` | 10023 | Run the rack summary workflow for the delivery-list scanner. | `get_racks`, `indian_trail_summary` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_racks` | 10042 | Read racks for the delivery-list scanner workflow. | `assign_line_item_to_rack`, `clear_rack`, `clear_rack_item`, `complete_rack`, `create_rack_set`, `delete_rack`, `move_rack_item`, `not_on_way_rack` (+5 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.get_rack_by_code` | 10053 | Read rack by code for the delivery-list scanner workflow. | `assign_line_item_to_rack`, `assign_transportation_from_outbound_override`, `clear_rack`, `complete_rack`, `delete_rack`, `move_rack_item`, `not_on_way_rack`, `outbound_scan_gate` (+6 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.scan_item_to_rack` | 10065 | Process item to rack for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.move_rack_item` | 10166 | Run the move rack item workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.clear_rack_item` | 10194 | Remove rack item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.clear_rack` | 10235 | Remove rack for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.rack_destination_value` | 10251 | Run the rack destination value workflow for the delivery-list scanner. | `destination_address_for_rack`, `rack_destinations_from_items`, `rack_packing_list`, `received_qty_for_rack_item`, `record_scan`, `scan_item_to_rack`, `scan_rack_outbound` |
| `delivery_store.py` | `SQLiteDeliveryStore.destination_for_line_item` | 10271 | Run the destination for line item workflow for the delivery-list scanner. | `rack_destinations_from_items`, `record_scan`, `repair_route_stage_memberships`, `scan_item_to_rack`, `sync_manual_route_membership`, `validate_rack_destination_for_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.rack_destinations_from_items` | 10296 | Run the rack destinations from items workflow for the delivery-list scanner. | `complete_rack`, `computed_rack_destination`, `record_scan`, `scan_item_to_rack`, `validate_rack_destination_for_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.computed_rack_destination` | 10322 | Run the computed rack destination workflow for the delivery-list scanner. | `rack_from_row`, `refresh_rack_destination` |
| `delivery_store.py` | `SQLiteDeliveryStore.refresh_rack_destination` | 10331 | Run the refresh rack destination workflow for the delivery-list scanner. | `clear_rack_item`, `move_rack_item`, `record_scan`, `repair_route_stage_memberships`, `scan_item_to_rack`, `update_line_item`, `update_line_item_location` |
| `delivery_store.py` | `SQLiteDeliveryStore.validate_rack_destination_for_item` | 10341 | Validate rack destination for item for the delivery-list scanner workflow. | `move_rack_item`, `update_line_item_location` |
| `delivery_store.py` | `SQLiteDeliveryStore.complete_rack` | 10357 | Run the complete rack workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.uncomplete_rack` | 10384 | Run the uncomplete rack workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.return_rack` | 10399 | Run the return rack workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.not_on_way_rack` | 10415 | Run the not on way rack workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.assign_line_item_to_rack` | 10522 | Run the assign line item to rack workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.update_rack` | 10609 | Update rack for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.create_rack_set` | 10648 | Create rack set for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_rack` | 10684 | Remove rack for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.destination_address_for_rack` | 10704 | Run the destination address for rack workflow for the delivery-list scanner. | `rack_packing_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.rack_packing_list` | 10757 | Run the rack packing list workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.scan_rack_outbound` | 10795 | Process rack outbound for the delivery-list scanner workflow. | `record_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.active_indian_trail_list` | 10922 | Resolve the active Indian Trail list for one explicit dashboard date. | `active_indian_trail_lists` |
| `delivery_store.py` | `SQLiteDeliveryStore.active_indian_trail_lists` | 10962 | Return every active Indian Trail list for one resolved delivery date. | `_indian_trail_in_transit_payload`, `indian_trail_summary` |
| `delivery_store.py` | `SQLiteDeliveryStore.indian_trail_physical_inventory` | 10988 | Aggregate all active Indian Trail copies into one physical item inventory. | `_indian_trail_in_transit_payload`, `indian_trail_outbound_totals`, `indian_trail_summary` |
| `delivery_store.py` | `SQLiteDeliveryStore.indian_trail_in_transit` | 11045 | Return the departed-rack manifest for the requested Indian Trail delivery date. | — |
| `delivery_store.py` | `SQLiteDeliveryStore._indian_trail_in_transit_payload` | 11054 | Return only glass on transportation methods that actually departed for Indian Trail. | `indian_trail_in_transit`, `indian_trail_summary` |
| `delivery_store.py` | `SQLiteDeliveryStore.indian_trail_outbound_totals` | 11303 | Return date-wide physical Indian Trail quantities that reached Outbound. | `indian_trail_summary` |
| `delivery_store.py` | `SQLiteDeliveryStore.indian_trail_summary` | 11389 | Return date-specific Indian Trail route totals for the Bay Map. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.transit_row_is_truck` | 11457 | Run the transit row is truck workflow for the delivery-list scanner. | `indian_trail_summary` |
| `delivery_store.py` | `SQLiteDeliveryStore.admin_search_line_items` | 11528 | Run the admin search line items workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.find_bay_for_assignment` | 11592 | Resolve bay for assignment for the delivery-list scanner workflow. | `preassign_bay_for_outbound`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_by_code` | 11622 | Read bay by code for the delivery-list scanner workflow. | `assign_bay`, `bay_check`, `clear_bay`, `manual_assign_bay_item`, `mark_sdi`, `move_bay_assignment`, `receive_indian_trail_scan`, `set_bay_status` |
| `delivery_store.py` | `SQLiteDeliveryStore.insert_bay_event` | 11633 | Create bay event for the delivery-list scanner workflow. | `assign_bay`, `assign_line_items_to_bay`, `bay_check`, `clear_bay`, `clear_bay_assignment`, `create_bays`, `delete_bay`, `delete_bay_group` (+10 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.assign_bay` | 11657 | Run the assign bay workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.receive_indian_trail_scan` | 11688 | Receive or return an item into an Indian Trail bay. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.move_bay_assignment` | 12249 | Run the move bay assignment workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.clear_bay` | 12272 | Remove bay for the delivery-list scanner workflow. | `bay_check` |
| `delivery_store.py` | `SQLiteDeliveryStore.clear_bay_assignment` | 12294 | Remove bay assignment for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.restore_bay_assignment` | 12318 | Run the restore bay assignment workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.set_bay_status` | 12345 | Update bay status for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.scan_out_bay_item` | 12381 | Scan an item out of its current bay and preserve a dated movement log. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.update_bay_layout` | 12464 | Update bay layout for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.set_bay_group_position` | 12520 | Update bay group position for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.create_bays` | 12543 | Create bays for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_bay` | 12600 | Remove bay for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_bay_group` | 12626 | Remove bay group for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.move_bay_group` | 12657 | Run the move bay group workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.mark_sdi` | 12705 | Mark exact missing items, or an explicitly selected broken item, as Rush/Remake. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.remove_sdi` | 13053 | Clear Rush/Remake from an exact item selection or a resolved job/order group. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_check` | 13176 | Run the bay check workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.export_csv` | 13196 | Export CSV for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.export_package_xlsx` | 13239 | Export package XLSX for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.cell_ref` | 13283 | Run the cell ref workflow for the delivery-list scanner. | `inline_cell` |
| `delivery_store.py` | `SQLiteDeliveryStore.inline_cell` | 13296 | Run the inline cell workflow for the delivery-list scanner. | `export_package_xlsx`, `export_xlsx` |
| `delivery_store.py` | `SQLiteDeliveryStore.export_xlsx` | 13354 | Export XLSX for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.cell_ref` | 13376 | Run the cell ref workflow for the delivery-list scanner. | `inline_cell` |
| `delivery_store.py` | `SQLiteDeliveryStore.inline_cell` | 13389 | Run the inline cell workflow for the delivery-list scanner. | `export_package_xlsx`, `export_xlsx` |
| `delivery_store.py` | `AzureSqlDeliveryStore.__init__` | 13468 | Initialize a Azure SQL delivery store instance and its required state. | `__init__` |
| `delivery_store.py` | `AzureSqlDeliveryStore.connect` | 13479 | Run the connect workflow for the delivery-list scanner. | `acknowledge_notification`, `add_customer_route_rule`, `add_manual_edit_lookup`, `add_station`, `admin_search_line_items`, `admin_summary`, `assign_bay`, `assign_line_item_to_rack` (+98 more) |
| `delivery_store.py` | `AzureSqlDeliveryStore.initialize` | 13490 | Run the initialize workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `AzureSqlDeliveryStore.health` | 13520 | Run the health workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `AzureSqlDeliveryStore.create_schema` | 13539 | Create schema for the delivery-list scanner workflow. | `initialize` |
| `delivery_store.py` | `AzureSqlDeliveryStore.ensure_column` | 13555 | Validate column for the delivery-list scanner workflow. | `apply_schema_migrations` |
| `delivery_store.py` | `create_store` | 13590 | Create store for the delivery-list scanner workflow. | — |
| `migrate_sqlite_to_azure_sql.py` | `parse_args` | 79 | Parse args for the delivery-list scanner workflow. | `main`, `parse_args` |
| `migrate_sqlite_to_azure_sql.py` | `quote_identifier` | 101 | Run the quote identifier workflow for the delivery-list scanner. | `main`, `sqlite_columns` |
| `migrate_sqlite_to_azure_sql.py` | `sqlite_columns` | 110 | Run the SQLite columns workflow for the delivery-list scanner. | `main` |
| `migrate_sqlite_to_azure_sql.py` | `azure_columns` | 119 | Run the Azure columns workflow for the delivery-list scanner. | `main` |
| `migrate_sqlite_to_azure_sql.py` | `main` | 137 | Run the main workflow for the delivery-list scanner. | `module startup` |
| `scanner_config.py` | `AppConfig.production` | 35 | Run the production workflow for the delivery-list scanner. | — |
| `scanner_config.py` | `_int_env` | 44 | Run the int env workflow for the delivery-list scanner. | `load_config` |
| `scanner_config.py` | `_bool_env` | 59 | Run the bool env workflow for the delivery-list scanner. | `load_config` |
| `scanner_config.py` | `load_config` | 71 | Load config for the delivery-list scanner workflow. | — |
| `server.py` | `esc` | 39 | Run the esc workflow for the delivery-list scanner. | `code39_svg`, `paginate_item_rows`, `render_customer_email_manifest_pdf_page`, `render_item_row`, `render_print_package`, `render_rack_packing_list`, `render_sheet`, `render_stale_bay_report` (+2 more) |
| `server.py` | `print_lifecycle_script` | 48 | Notify the app after print preview closes and close script-opened print windows. | `render_customer_email_manifest_pdf_page`, `render_print_package`, `render_rack_packing_list`, `render_stale_bay_report` |
| `server.py` | `print_display_date` | 73 | Return a plain M/D/YYYY date for printed sheets and packing lists. | `customer_date_groups`, `render_customer_email_manifest_pdf_page`, `rows_for_items`, `sheet_subtitle`, `sheet_title` |
| `server.py` | `code39_svg` | 106 | Run the code39 SVG workflow for the delivery-list scanner. | `sheet_html` |
| `server.py` | `render_item_row` | 128 | Render item row for the delivery-list scanner workflow. | `paginate_item_rows` |
| `server.py` | `paginate_item_rows` | 153 | Build explicit one-paper-page chunks for printed delivery lists. | `render_sheet` |
| `server.py` | `current_row_limit` | 174 | Run the current row limit workflow for the delivery-list scanner. | `paginate_item_rows` |
| `server.py` | `flush_page` | 182 | Run the flush page workflow for the delivery-list scanner. | `paginate_item_rows` |
| `server.py` | `render_sheet` | 229 | Render sheet for the delivery-list scanner workflow. | `render_print_package` |
| `server.py` | `printed_item_is_remake` | 305 | Return True when a printed row should be marked as a remake/RM. | `rows_for_items` |
| `server.py` | `render_rack_packing_list` | 314 | Render rack packing list for the delivery-list scanner workflow. | `do_GET` |
| `server.py` | `customer_date_groups` | 329 | Run the customer date groups workflow for the delivery-list scanner. | `render_rack_packing_list` |
| `server.py` | `rows_for_items` | 374 | Run the rows for items workflow for the delivery-list scanner. | `sheet_html` |
| `server.py` | `sheet_html` | 403 | Run the sheet HTML workflow for the delivery-list scanner. | `render_rack_packing_list` |
| `server.py` | `render_customer_email_manifest_pdf_page` | 534 | Render customer email manifest PDF page for the delivery-list scanner workflow. | `do_GET` |
| `server.py` | `render_stale_bay_report` | 630 | Render stale bay report for the delivery-list scanner workflow. | `do_GET` |
| `server.py` | `render_print_package` | 699 | Render print package for the delivery-list scanner workflow. | `do_GET` |
| `server.py` | `stage_print_name` | 713 | Short, human print name. Avoid repeating the stage in badges/subtitles. | `sheet_title` |
| `server.py` | `sheet_title` | 731 | Run the sheet title workflow for the delivery-list scanner. | `render_print_package` |
| `server.py` | `sheet_badge` | 747 | Run the sheet badge workflow for the delivery-list scanner. | `render_print_package` |
| `server.py` | `sheet_subtitle` | 761 | Run the sheet subtitle workflow for the delivery-list scanner. | `render_print_package` |
| `server.py` | `Handler.__init__` | 894 | Initialize a handler instance and its required state. | `__init__` |
| `server.py` | `Handler.end_headers` | 902 | Run the end headers workflow for the delivery-list scanner. | `do_GET`, `do_POST`, `end_headers`, `send_html`, `send_json` |
| `server.py` | `Handler.send_json` | 913 | Send JSON for the delivery-list scanner workflow. | `do_GET`, `do_POST`, `require_any_permission`, `require_confirmation_text`, `require_permission`, `require_rack_recovery_power` |
| `server.py` | `Handler.send_html` | 927 | Send HTML for the delivery-list scanner workflow. | `do_GET` |
| `server.py` | `Handler.read_json` | 941 | Read JSON for the delivery-list scanner workflow. | `do_POST` |
| `server.py` | `Handler.session_token` | 952 | Run the session token workflow for the delivery-list scanner. | `current_user`, `do_POST` |
| `server.py` | `Handler.current_user` | 965 | Run the current user workflow for the delivery-list scanner. | `do_GET`, `do_POST`, `require_any_permission`, `require_permission`, `require_rack_recovery_power` |
| `server.py` | `Handler.require_permission` | 973 | Run the require permission workflow for the delivery-list scanner. | `do_GET`, `do_POST` |
| `server.py` | `Handler.require_any_permission` | 988 | Run the require any permission workflow for the delivery-list scanner. | `do_POST` |
| `server.py` | `Handler.require_confirmation_text` | 1005 | Run the require confirmation text workflow for the delivery-list scanner. | `do_POST` |
| `server.py` | `Handler.require_rack_recovery_power` | 1020 | Allow only Admin/Supervisor-level users to manually recover rack locations. | `do_POST` |
| `server.py` | `Handler.set_session_cookie` | 1033 | Update session cookie for the delivery-list scanner workflow. | `do_POST` |
| `server.py` | `Handler.clear_session_cookie` | 1045 | Remove session cookie for the delivery-list scanner workflow. | `do_POST` |
| `server.py` | `Handler.do_GET` | 1056 | Handle get for the delivery-list scanner workflow. | `do_GET` |
| `server.py` | `Handler.do_POST` | 1370 | Handle post for the delivery-list scanner workflow. | — |
| `server.py` | `daily_import_loop` | 1946 | Run the Temp Delivery Lists import once per day at 5 PM Eastern. | — |
| `server.py` | `start_daily_import_scheduler` | 1970 | Run the start daily import scheduler workflow for the delivery-list scanner. | `main` |
| `server.py` | `write_startup_failure_log` | 1980 | Persist startup failures so the Windows launcher can show a useful diagnosis. | `module startup` |
| `server.py` | `main` | 2008 | Start the database, scheduler, and HTTP server in a diagnosable order. | `module startup` |
| `tests/conftest.py` | `app_config` | 17 | Run the app config workflow for the delivery-list scanner. | — |
| `tests/conftest.py` | `store` | 49 | Run the store workflow for the delivery-list scanner. | — |
| `tests/conftest.py` | `sample_payload` | 61 | Run the sample payload workflow for the delivery-list scanner. | — |
| `tests/conftest.py` | `imported_store` | 166 | Run the imported store workflow for the delivery-list scanner. | — |
| `tests/test_azure_adapter_and_rendering.py` | `FakeCursor.__init__` | 20 | Initialize a fake cursor instance and its required state. | `__init__` |
| `tests/test_azure_adapter_and_rendering.py` | `FakeCursor.execute` | 32 | Run the execute workflow for the delivery-list scanner. | `connect_azure_sql`, `execute`, `execute_tsql`, `test_migration_identifier_and_column_helpers` |
| `tests/test_azure_adapter_and_rendering.py` | `FakeCursor.executemany` | 41 | Run the executemany workflow for the delivery-list scanner. | `executemany` |
| `tests/test_azure_adapter_and_rendering.py` | `FakeCursor.fetchone` | 51 | Run the fetchone workflow for the delivery-list scanner. | `execute`, `fetchone`, `test_azure_cursor_and_connection_transaction_lifecycle`, `test_azure_row_and_memory_cursor_behave_like_sqlite_rows` |
| `tests/test_azure_adapter_and_rendering.py` | `FakeCursor.fetchall` | 59 | Run the fetchall workflow for the delivery-list scanner. | `__iter__`, `fetchall`, `test_azure_cursor_and_connection_transaction_lifecycle`, `test_azure_row_and_memory_cursor_behave_like_sqlite_rows` |
| `tests/test_azure_adapter_and_rendering.py` | `FakeCursor.__iter__` | 68 | Implement the iter protocol for fake cursor. | — |
| `tests/test_azure_adapter_and_rendering.py` | `FakeCursor.nextset` | 76 | Run the nextset workflow for the delivery-list scanner. | — |
| `tests/test_azure_adapter_and_rendering.py` | `FakeRawConnection.__init__` | 86 | Initialize a fake raw connection instance and its required state. | `__init__` |
| `tests/test_azure_adapter_and_rendering.py` | `FakeRawConnection.cursor` | 97 | Run the cursor workflow for the delivery-list scanner. | — |
| `tests/test_azure_adapter_and_rendering.py` | `FakeRawConnection.commit` | 105 | Run the commit workflow for the delivery-list scanner. | `__exit__`, `commit` |
| `tests/test_azure_adapter_and_rendering.py` | `FakeRawConnection.rollback` | 113 | Run the rollback workflow for the delivery-list scanner. | `__exit__`, `rollback` |
| `tests/test_azure_adapter_and_rendering.py` | `FakeRawConnection.close` | 121 | Run the close workflow for the delivery-list scanner. | `__exit__`, `close` |
| `tests/test_azure_adapter_and_rendering.py` | `test_azure_row_and_memory_cursor_behave_like_sqlite_rows` | 130 | Run the test Azure row and memory cursor behave like SQLite rows workflow for the delivery-list scanner. | — |
| `tests/test_azure_adapter_and_rendering.py` | `test_azure_cursor_and_connection_transaction_lifecycle` | 148 | Run the test Azure cursor and connection transaction lifecycle workflow for the delivery-list scanner. | — |
| `tests/test_azure_adapter_and_rendering.py` | `test_limit_parameter_inlining_preserves_remaining_parameter_order` | 171 | Run the test limit parameter inlining preserves remaining parameter order workflow for the delivery-list scanner. | — |
| `tests/test_azure_adapter_and_rendering.py` | `test_azure_dependency_and_connection_string_errors_are_explicit` | 189 | Run the test Azure dependency and connection string errors are explicit workflow for the delivery-list scanner. | — |
| `tests/test_azure_adapter_and_rendering.py` | `test_print_render_helpers_cover_pagination_barcode_and_lifecycle` | 199 | Run the test print render helpers cover pagination barcode and lifecycle workflow for the delivery-list scanner. | — |
| `tests/test_core_helpers.py` | `test_auth_and_text_helpers` | 25 | Run the test auth and text helpers workflow for the delivery-list scanner. | — |
| `tests/test_core_helpers.py` | `test_route_and_rack_helpers` | 47 | Run the test route and rack helpers workflow for the delivery-list scanner. | — |
| `tests/test_core_helpers.py` | `test_stage_generation_and_bay_suggestions` | 70 | Run the test stage generation and bay suggestions workflow for the delivery-list scanner. | — |
| `tests/test_core_helpers.py` | `test_sqlite_connection_uses_busy_timeout` | 96 | Confirm local startup tolerates short-lived SQLite file locks. | — |
| `tests/test_core_helpers.py` | `test_startup_failure_log_contains_runtime_context` | 110 | Verify startup exceptions leave a durable diagnostic file. | — |
| `tests/test_extended_workflows.py` | `_list_id` | 11 | Read ID for the delivery-list scanner workflow. | `test_manual_edits_deletes_and_audit`, `test_rack_crud_move_clear_and_packing_list` |
| `tests/test_extended_workflows.py` | `_item` | 20 | Run the item workflow for the delivery-list scanner. | `test_manual_edits_deletes_and_audit`, `test_priority_rush_and_remake_lifecycle` |
| `tests/test_extended_workflows.py` | `_scan` | 29 | Run the scan workflow for the delivery-list scanner. | `test_rack_crud_move_clear_and_packing_list` |
| `tests/test_extended_workflows.py` | `test_rack_crud_move_clear_and_packing_list` | 46 | Run the test rack crud move clear and packing list workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_bay_layout_status_creation_and_deletion` | 78 | Run the test bay layout status creation and deletion workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_manual_bay_assignment_rules_and_stale_workflow` | 123 | Run the test manual bay assignment rules and stale workflow workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_sdi_current_priority_groups_sort_earliest_date_first` | 156 | Keep the SDI current-priority queue ordered by the earliest required date. | — |
| `tests/test_extended_workflows.py` | `test_priority_rush_and_remake_lifecycle` | 211 | Run the test priority rush and remake lifecycle workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_manual_edits_deletes_and_audit` | 245 | Run the test manual edits deletes and audit workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_customer_email_and_barcode_rule_removal` | 277 | Run the test customer email and barcode rule removal workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_folder_import_update_skip_and_preview` | 299 | Run the test folder import update skip and preview workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_delete_delivery_list_and_date` | 335 | Run the test delete delivery list and date workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_sdi_workspace_missing_defaults_exact_remake_and_individual_clear` | 358 | Verify the SDI workspace distinguishes physical bay fulfillment from missing glass. | — |
| `tests/test_file_imports_and_sql_compat.py` | `test_csv_json_xlsx_import_parsers` | 13 | Run the test CSV JSON XLSX import parsers workflow for the delivery-list scanner. | — |
| `tests/test_file_imports_and_sql_compat.py` | `test_sqlite_limit_parameter_handling` | 50 | Run the test SQLite limit parameter handling workflow for the delivery-list scanner. | — |
| `tests/test_file_imports_and_sql_compat.py` | `test_sqlite_to_sql_server_translation` | 64 | Run the test SQLite to SQL server translation workflow for the delivery-list scanner. | — |
| `tests/test_graph_email.py` | `_FakeResponse.__init__` | 13 | Store one fake status code and JSON response body. | `__init__` |
| `tests/test_graph_email.py` | `_FakeResponse.__enter__` | 18 | Return this fake response to context-managed callers. | — |
| `tests/test_graph_email.py` | `_FakeResponse.__exit__` | 22 | Leave exceptions unhandled so tests observe the original failure. | `__exit__` |
| `tests/test_graph_email.py` | `_FakeResponse.read` | 26 | Serialize the configured fake JSON payload as response bytes. | — |
| `tests/test_graph_email.py` | `_FakeResponse.getcode` | 30 | Return the configured fake HTTP status code. | — |
| `tests/test_graph_email.py` | `_configure_graph` | 35 | Apply a complete local app-registration configuration for one test. | `test_graph_settings_expose_readiness_without_secret`, `test_graph_test_email_uses_client_credentials_and_sendmail`, `test_graph_token_is_cached_between_messages` |
| `tests/test_graph_email.py` | `test_graph_settings_expose_readiness_without_secret` | 47 | Graph readiness is visible to Admin UI while credentials remain server-side. | — |
| `tests/test_graph_email.py` | `test_graph_test_email_uses_client_credentials_and_sendmail` | 60 | The existing test-email workflow obtains one token and calls user sendMail. | — |
| `tests/test_graph_email.py` | `fake_urlopen` | 65 | Capture token and sendMail requests for the integration test. | — |
| `tests/test_graph_email.py` | `test_graph_token_is_cached_between_messages` | 97 | Repeated sends reuse the access token so scanning does not authenticate each time. | — |
| `tests/test_graph_email.py` | `fake_urlopen` | 103 | Count token and send calls while returning valid fake responses. | — |
| `tests/test_graph_email.py` | `test_graph_managed_identity_uses_app_service_endpoint` | 119 | Azure mode uses the App Service identity endpoint without a client secret. | — |
| `tests/test_graph_email.py` | `fake_urlopen` | 130 | Capture managed-identity and Graph requests for assertion. | — |
| `tests/test_graph_email.py` | `test_graph_setup_files_and_launcher_contract` | 145 | The release includes encrypted local setup and launcher loading support. | — |
| `tests/test_migration_tooling.py` | `FakeAzureColumnCursor.__init__` | 16 | Initialize the fake cursor with target column names. | `__init__` |
| `tests/test_migration_tooling.py` | `FakeAzureColumnCursor.execute` | 25 | Record one metadata query and return the cursor for chaining. | `connect_azure_sql`, `execute`, `execute_tsql`, `test_migration_identifier_and_column_helpers` |
| `tests/test_migration_tooling.py` | `FakeAzureColumnCursor.fetchall` | 34 | Return configured Azure column rows. | `__iter__`, `fetchall`, `test_azure_cursor_and_connection_transaction_lifecycle`, `test_azure_row_and_memory_cursor_behave_like_sqlite_rows` |
| `tests/test_migration_tooling.py` | `test_migration_identifier_and_column_helpers` | 43 | Validate identifier quoting and source/target column discovery. | — |
| `tests/test_migration_tooling.py` | `test_migration_argument_parser_and_table_order` | 64 | Verify migration CLI flags and dependency-safe table ordering. | — |
| `tests/test_server_http.py` | `free_port` | 19 | Run the free port workflow for the delivery-list scanner. | `test_http_api_end_to_end` |
| `tests/test_server_http.py` | `wait_for_server` | 30 | Run the wait for server workflow for the delivery-list scanner. | `test_http_api_end_to_end` |
| `tests/test_server_http.py` | `json_request` | 50 | Run the JSON request workflow for the delivery-list scanner. | `test_http_api_end_to_end` |
| `tests/test_server_http.py` | `test_http_api_end_to_end` | 63 | Run the test HTTP API end to end workflow for the delivery-list scanner. | — |
| `tests/test_static_integrity.py` | `test_python_and_javascript_syntax` | 14 | Run the test python and javascript syntax workflow for the delivery-list scanner. | — |
| `tests/test_static_integrity.py` | `test_html_ids_and_dom_references` | 24 | Run the test HTML IDs and dom references workflow for the delivery-list scanner. | — |
| `tests/test_static_integrity.py` | `test_css_parses_without_errors` | 36 | Run the test CSS parses without errors workflow for the delivery-list scanner. | — |
| `tests/test_static_integrity.py` | `test_no_duplicate_top_level_python_methods` | 47 | Run the test no duplicate top level python methods workflow for the delivery-list scanner. | — |
| `tests/test_static_integrity.py` | `test_client_api_paths_exist_on_server` | 61 | Run the test client API paths exist on server workflow for the delivery-list scanner. | — |
| `tests/test_static_integrity.py` | `test_all_python_functions_are_documented` | 74 | Ensure every maintained Python function or method has an inline note. | — |
| `tests/test_static_integrity.py` | `test_named_javascript_functions_have_purpose_notes` | 92 | Ensure every named JavaScript function has a nearby Purpose JSDoc note. | — |
| `tests/test_static_integrity.py` | `test_no_duplicate_top_level_javascript_functions` | 115 | Prevent parallel top-level JavaScript implementations with the same name. | — |
| `tests/test_static_integrity.py` | `test_server_store_calls_resolve_and_route_checks_are_unique` | 133 | Verify every HTTP handler delegates to an implemented store method. | — |
| `tests/test_static_integrity.py` | `test_windows_launchers_are_packaged_and_wait_for_health` | 163 | Verify the supported Windows launchers are included and diagnosable. | — |
| `tests/test_static_integrity.py` | `test_v074_asset_cache_versions_and_sqlite_default` | 201 | Verify the v074 shell cache keys and SQLite-first configuration. | — |
| `tests/test_static_integrity.py` | `test_v073_ui_polish_and_multi_filter_contracts` | 216 | Protect the maintained filter, history, profile, scrollbar, SDI, search, and Today-progress changes. | — |
| `tests/test_static_integrity.py` | `test_windows_launcher_unblocks_downloaded_powershell_script` | 240 | Verify the packaged BAT clears the downloaded-file marker before launching PowerShell. | — |
| `tests/test_static_integrity.py` | `test_v064_scan_history_language_layout_and_save_confirmation_contracts` | 252 | Protect the v064 fullscreen, Spanish layout, and save-confirmation changes. | — |
| `tests/test_static_integrity.py` | `test_v064_release_uses_one_supported_launcher_and_one_ongoing_changelog` | 270 | Keep the local release folder clean and unambiguous. | — |
| `tests/test_static_integrity.py` | `test_v064_explicit_save_workflows_use_one_shared_success_dialog` | 281 | Keep every explicit settings/data save on the shared confirmation path. | — |
| `tests/test_static_integrity.py` | `test_v065_bay_scanner_and_item_aware_sdi_contracts` | 328 | Protect the v065 Bay scanner transit control and item-aware SDI workflow. | — |
| `tests/test_static_integrity.py` | `test_v066_print_popup_permission_and_lookup_contracts` | 355 | Protect the v066 print, timed-popup, permission-help, and Lookup Manager changes. | — |
| `tests/test_static_integrity.py` | `test_v069_header_bay_sdi_and_progress_contracts` | 390 | Protect the v069 cohesive header, compact Bay command, and rebuilt SDI workspace. | — |
| `tests/test_static_integrity.py` | `test_v070_microsoft_graph_email_contracts` | 419 | Protect the v070 Graph transport, encrypted local setup, and Admin status UI. | — |
| `tests/test_static_integrity.py` | `test_v074_collapsible_sidebar_contracts` | 438 | Protect the v074 application shell, profile placement, persistence, and responsive drawer. | — |
| `tests/test_store_workflows.py` | `list_id` | 13 | Read ID for the delivery-list scanner workflow. | `test_bay_receive_move_clear_restore_and_scan_out`, `test_import_route_authority_and_exports`, `test_in_transit_manifest_requires_an_actual_outbound_rack_departure`, `test_indian_trail_outbound_summary_aggregates_lists_and_never_trails_received`, `test_indian_trail_outbound_summary_updates_after_rack_departure`, `test_rack_lifecycle_and_outbound_departure`, `test_scanning_undo_redo_reset_and_errors` |
| `tests/test_store_workflows.py` | `item_for` | 22 | Run the item for workflow for the delivery-list scanner. | `test_import_route_authority_and_exports`, `test_scanning_undo_redo_reset_and_errors` |
| `tests/test_store_workflows.py` | `scan` | 31 | Run the scan workflow for the delivery-list scanner. | `test_bay_receive_move_clear_restore_and_scan_out`, `test_in_transit_manifest_requires_an_actual_outbound_rack_departure`, `test_indian_trail_outbound_summary_updates_after_rack_departure`, `test_rack_lifecycle_and_outbound_departure`, `test_scanning_undo_redo_reset_and_errors` |
| `tests/test_store_workflows.py` | `test_import_route_authority_and_exports` | 47 | Run the test import route authority and exports workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_auth_users_roles_stations_and_password_reset` | 83 | Run the test auth users roles stations and password reset workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_scanning_undo_redo_reset_and_errors` | 133 | Run the test scanning undo redo reset and errors workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_rack_lifecycle_and_outbound_departure` | 172 | Run the test rack lifecycle and outbound departure workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_indian_trail_outbound_summary_updates_after_rack_departure` | 209 | Verify Bay Map Outbound quantities follow live Outbound scans for Indian Trail pieces. | — |
| `tests/test_store_workflows.py` | `test_indian_trail_outbound_summary_aggregates_lists_and_never_trails_received` | 251 | Verify Bay Map sent quantity survives split Outbound lists and legacy matching gaps. | — |
| `tests/test_store_workflows.py` | `test_indian_trail_summary_aggregates_every_active_inbound_copy` | 301 | Verify an updated/split Indian Trail list cannot hide received pieces from Bay Map totals. | — |
| `tests/test_store_workflows.py` | `test_in_transit_manifest_requires_an_actual_outbound_rack_departure` | 346 | Verify assigned rack glass stays out of Pieces on the Way until the rack is scanned. | — |
| `tests/test_store_workflows.py` | `test_bay_receive_move_clear_restore_and_scan_out` | 378 | Run the test bay receive move clear restore and scan out workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_admin_rules_notifications_reports_and_search` | 416 | Run the test admin rules notifications reports and search workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_email_settings_manual_lookups_and_bay_rules` | 450 | Run the test email settings manual lookups and bay rules workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_repeated_startup_skips_unchanged_route_reconciliation` | 483 | Confirm repeated SQLite startup avoids the expensive full route repair. | — |
| `tests/test_store_workflows.py` | `unexpected_repair` | 490 | Fail if unchanged startup incorrectly invokes full route reconciliation. | — |
| `tests/test_store_workflows.py` | `test_context_managed_sqlite_connection_closes_after_transaction` | 503 | Protect the shared SQLite connection-cleanup behavior used by store methods. | — |
| `tests/test_store_workflows.py` | `test_startup_skips_demo_reseed_and_refresh_avoids_cross_list_id_collision` | 519 | Protect live databases from sample reseeding and globally reused line-item IDs. | — |
| `tests/test_visual_smoke.py` | `_mock_payload_script` | 34 | Run the mock payload script workflow for the delivery-list scanner. | `test_mocked_browser_visual_and_interaction_sweep` |
| `tests/test_visual_smoke.py` | `_strip_external_assets` | 333 | Run the strip external assets workflow for the delivery-list scanner. | `test_mocked_browser_visual_and_interaction_sweep` |
| `tests/test_visual_smoke.py` | `_overlap` | 344 | Run the overlap workflow for the delivery-list scanner. | `test_mocked_browser_visual_and_interaction_sweep` |
| `tests/test_visual_smoke.py` | `test_mocked_browser_visual_and_interaction_sweep` | 359 | Run the test mocked browser visual and interaction sweep workflow for the delivery-list scanner. | — |
| `tools/generate_code_reference.py` | `maintained_python_paths` | 30 | Return every maintained Python source, test, and validation tool. | `render_reference` |
| `tools/generate_code_reference.py` | `first_doc_line` | 42 | Return the first useful summary line from a Python docstring. | `visit_FunctionDef` |
| `tools/generate_code_reference.py` | `python_inventory` | 54 | Inventory Python classes, functions, methods, and approximate callers. | `render_reference` |
| `tools/generate_code_reference.py` | `DeclVisitor.visit_ClassDef` | 70 | Run the visit class def workflow for the delivery-list scanner. | — |
| `tools/generate_code_reference.py` | `DeclVisitor.visit_FunctionDef` | 80 | Run the visit function def workflow for the delivery-list scanner. | — |
| `tools/generate_code_reference.py` | `CallVisitor.visit_FunctionDef` | 109 | Run the visit function def workflow for the delivery-list scanner. | — |
| `tools/generate_code_reference.py` | `CallVisitor.visit_Call` | 121 | Run the visit call workflow for the delivery-list scanner. | — |
| `tools/generate_code_reference.py` | `javascript_inventory` | 140 | Inventory named JavaScript functions and approximate direct callers. | `render_reference` |
| `tools/generate_code_reference.py` | `powershell_inventory` | 184 | Inventory documented PowerShell launcher functions. | `render_reference` |
| `tools/generate_code_reference.py` | `route_inventory` | 206 | Extract GET and POST API routes from the HTTP handler. | `render_reference` |
| `tools/generate_code_reference.py` | `table_inventory` | 239 | Inventory Azure SQL tables and their nearby ownership comments. | `render_reference` |
| `tools/generate_code_reference.py` | `html_inventory` | 260 | Inventory stable HTML IDs and their owning page or modal. | `render_reference` |
| `tools/generate_code_reference.py` | `css_inventory` | 279 | Inventory documented CSS ownership sections. | `render_reference` |
| `tools/generate_code_reference.py` | `join_callers` | 294 | Format a bounded caller list for Markdown tables. | `render_reference` |
| `tools/generate_code_reference.py` | `render_reference` | 308 | Generate the complete maintainer-facing code reference. | `main` |
| `tools/generate_code_reference.py` | `main` | 393 | Parse CLI arguments and generate the code reference. | `module startup` |
| `tools/run_full_validation.py` | `run` | 28 | Run one validation command from the project root. | `main`, `run`, `run_test_modules` |
| `tools/run_full_validation.py` | `run_test_modules` | 39 | Run each maintained pytest module in a fresh, time-bounded process. | `main` |
| `tools/run_full_validation.py` | `audit_release_hygiene` | 65 | Reject generated or sensitive files that do not belong in a release ZIP. | `main` |
| `tools/run_full_validation.py` | `audit_python_documentation` | 88 | Verify every Python function remains documented after future edits. | `main` |
| `tools/run_full_validation.py` | `main` | 107 | Execute the full maintained validation workflow. | `module startup` |

## JavaScript function reference
| Function | Line | Purpose | Approximate callers |
|---|---:|---|---|
| `escapeHtml` | 533 | Run the escape HTML workflow for the browser application. | `addRow`, `adminModalContent`, `assignableRacks`, `autoAssignTypeOptions`, `bayAutoAssignerModalHtml`, `bayDualProgressHtml`, `bayEditorBayRowMarkup`, `bayEventMoveControlHtml` (+139 more) |
| `pad` | 546 | Run the pad workflow for the browser application. | `buildIndexes`, `canonicalBarcode`, `dateInputValue`, `todayKey` |
| `spanishBayCategoryLabel` | 1917 | Run the spanish bay category label workflow for the browser application. | — |
| `translateDynamicUiText` | 2102 | Run the translate dynamic UI text workflow for the browser application. | `translatedUiValue` |
| `translatedUiValue` | 2122 | Run the translated UI value workflow for the browser application. | `spanishBayCategoryLabel`, `translateUiAttributes`, `translateUiTextNode` |
| `translateUiTextNode` | 2136 | Run the translate UI text node workflow for the browser application. | `applyLanguageToRoot` |
| `translateUiAttributes` | 2158 | Run the translate UI attributes workflow for the browser application. | `applyLanguageToRoot` |
| `shouldSkipUiTranslation` | 2189 | Run the should skip UI translation workflow for the browser application. | `applyLanguageToRoot` |
| `applyLanguageToRoot` | 2198 | Update the apply language to root workflow using the existing shared UI state. | `close`, `filterLookupManagerLibrary`, `initLanguageSystem`, `mountTimedScanConfirmation`, `renderLookupManagerModal`, `setAppLanguage`, `showActionFeedback`, `submit` |
| `syncLanguageControls` | 2224 | Run the sync language controls workflow for the browser application. | `initLanguageSystem`, `setAppLanguage` |
| `setAppLanguage` | 2245 | Update the set app language workflow using the existing shared UI state. | `toggleAppLanguage` |
| `toggleAppLanguage` | 2263 | Toggle the toggle app language workflow using the existing shared UI state. | `wireEvents` |
| `initLanguageSystem` | 2272 | Run the init language system workflow for the browser application. | `wireEvents` |
| `isMobileSidebarLayout` | 2294 | Determine whether the application is currently using the overlay drawer layout. | `syncSidebarState`, `toggleMobileSidebar`, `toggleSidebar` |
| `defaultSidebarCollapsedForPage` | 2303 | Provide page-aware sidebar defaults until the operator saves a preference. | `resolvedSidebarCollapsed` |
| `resolvedSidebarCollapsed` | 2312 | Resolve the desktop sidebar state from the saved operator preference or page default. | `syncSidebarState`, `toggleSidebar` |
| `syncSidebarState` | 2323 | Keep sidebar classes, controls, titles, and responsive drawer state synchronized. | `showPage`, `syncFullscreenControl`, `toggleMobileSidebar`, `toggleSidebar`, `wireEvents` |
| `toggleSidebar` | 2375 | Toggle the saved desktop sidebar preference or close the mobile drawer. | `wireEvents` |
| `toggleMobileSidebar` | 2398 | Open or close the responsive navigation drawer without changing the desktop preference. | `wireEvents` |
| `syncFullscreenStickyPanelOffset` | 2410 | Run the sync fullscreen sticky panel offset workflow for the browser application. | `syncFullscreenControl`, `wireEvents` |
| `syncFullscreenControl` | 2423 | Run the sync fullscreen control workflow for the browser application. | `wireEvents` |
| `toggleFullscreen` | 2442 | Toggle the toggle fullscreen workflow using the existing shared UI state. | `wireEvents` |
| `refreshPage` | 2457 | Load the refresh page workflow using the existing shared UI state. | `wireEvents` |
| `consumeFullscreenRefreshRequest` | 2472 | Run the consume fullscreen refresh request workflow for the browser application. | `resumeFullscreenAfterRefresh` |
| `showFullscreenRecoveryPrompt` | 2487 | Open the show fullscreen recovery prompt workflow using the existing shared UI state. | `restoreFullscreenAfterManagedPrint`, `resumeFullscreenAfterRefresh` |
| `resumeFullscreenAfterRefresh` | 2511 | Run the resume fullscreen after refresh workflow for the browser application. | `init` |
| `customSelectIsEligible` | 2547 | Run the custom select is eligible workflow for the browser application. | `enhanceCustomSelect`, `openCustomSelect` |
| `customSelectAccessibleLabel` | 2562 | Run the custom select accessible label workflow for the browser application. | `enhanceCustomSelect`, `openCustomSelect`, `syncCustomSelect` |
| `customSelectSelectedText` | 2583 | Run the custom select selected text workflow for the browser application. | `syncCustomSelect` |
| `syncCustomSelect` | 2593 | Run the sync custom select workflow for the browser application. | `closeCustomSelect`, `enhanceCustomSelect`, `initCustomSelectSystem`, `openCustomSelect`, `openSdiPanel`, `populateSdiBayOptions`, `renderBayLastScanCard`, `renderCustomSelectOptions` (+7 more) |
| `syncAllCustomSelects` | 2632 | Run the sync all custom selects workflow for the browser application. | `setAppLanguage` |
| `positionCustomSelectMenu` | 2642 | Run the position custom select menu workflow for the browser application. | `initCustomSelectSystem`, `openCustomSelect` |
| `setCustomSelectHighlight` | 2679 | Update the set custom select highlight workflow using the existing shared UI state. | `openCustomSelect`, `renderCustomSelectOptions` |
| `closeCustomSelect` | 2701 | Close the close custom select workflow using the existing shared UI state. | `initCustomSelectSystem`, `openCustomSelect`, `renderCustomSelectOptions`, `syncAllCustomSelects` |
| `customSelectOptionRows` | 2719 | Run the custom select option rows workflow for the browser application. | `renderCustomSelectOptions` |
| `renderCustomSelectOptions` | 2749 | Render the render custom select options workflow using the existing shared UI state. | `openCustomSelect` |
| `openCustomSelect` | 2815 | Open the open custom select workflow using the existing shared UI state. | `enhanceCustomSelect` |
| `enhanceCustomSelect` | 2913 | Run the enhance custom select workflow for the browser application. | `enhanceCustomSelects`, `initCustomSelectSystem` |
| `enhanceCustomSelects` | 2968 | Run the enhance custom selects workflow for the browser application. | `close`, `initCustomSelectSystem`, `mountTimedScanConfirmation` |
| `initCustomSelectSystem` | 2981 | Run the init custom select system workflow for the browser application. | `wireEvents` |
| `canonicalBarcode` | 3038 | Run the canonical barcode workflow for the browser application. | `exportStaticCsv`, `recoverScan`, `submitManualBayScan`, `submitManualScan` |
| `formatDisplayDate` | 3047 | Normalize the format display date workflow using the existing shared UI state. | `addRow`, `createDemoLists`, `customerEmailRulesModalHtml`, `deleteAdminDeliveryDateByDate`, `deleteSelectedDeliveryList`, `deliveryListAdminRows`, `groups`, `homeStatisticsRangeParts` (+24 more) |
| `formatDateTime` | 3058 | Normalize the format date time workflow using the existing shared UI state. | `addRow`, `emailDraftPreviewHtml`, `renderBaySidePanels`, `renderItemRow`, `renderRackBoardCard`, `renderRackItem`, `renderSelectedRackDetails`, `renderStaleBayPanel` (+2 more) |
| `todayKey` | 3069 | Run the today key workflow for the browser application. | `dashboardDateKey`, `latestDeliveryDate`, `renderTodayProgress` |
| `dateInputValue` | 3079 | Run the date input value workflow for the browser application. | `defaultImportFromDate`, `homeReportDateParams` |
| `defaultImportFromDate` | 3090 | Run the default import from date workflow for the browser application. | `currentImportDateWindow`, `resetImportDateWindow` |
| `resetImportDateWindow` | 3101 | Run the reset import date window workflow for the browser application. | `init`, `wireEvents` |
| `currentImportDateWindow` | 3114 | Run the current import date window workflow for the browser application. | `importTempDeliveryFolder` |
| `parseDateKey` | 3129 | Normalize the parse date key workflow using the existing shared UI state. | `activeRecentImports`, `deliveryListIsInAdminWindow`, `filterListsByOverviewRange` |
| `filterListsByOverviewRange` | 3140 | Run the filter lists by overview range workflow for the browser application. | `homeStatisticsRangeParts`, `openHomeStatisticsReport`, `renderHome`, `renderStatisticsChartModal`, `statisticsChartDataset` |
| `latestDeliveryDate` | 3160 | Run the latest delivery date workflow for the browser application. | `dashboardDateKey` |
| `dashboardDateKey` | 3170 | Run the dashboard date key workflow for the browser application. | `ids`, `indianTrailDateQuery`, `renderBayRouteFlow`, `renderPrintOptionStages`, `renderTodayProgress`, `wireEvents` |
| `progressPercent` | 3180 | Run the progress percent workflow for the browser application. | `deliveryListCard`, `renderTodayProgress` |
| `formatPercent` | 3189 | Normalize the format percent workflow using the existing shared UI state. | `bayDualProgressHtml`, `deliveryListCard`, `openHomeStatisticsReport`, `renderCounts`, `renderHome`, `renderHomeStatistics`, `renderHomeStatsChart`, `renderStackedProgress` (+5 more) |
| `stageCategory` | 3198 | Run the stage category workflow for the browser application. | `aggregateListStats`, `deliveryListCard`, `homeStageBreakdown`, `printListIsFullCoverage`, `printStageOptionLabel`, `priorityListsIncludeIndianTrail`, `renderBayRouteFlow`, `renderPrintOptionStages` (+6 more) |
| `stageLabel` | 3213 | Run the stage label workflow for the browser application. | `deliveryListCard`, `homeStageBreakdown`, `openRushNotificationList`, `renderHomeStageFilter`, `renderTodayProgress`, `showRushAlert`, `stageProgressSegments`, `statisticsChartListLabel` (+1 more) |
| `priorityListsIncludeIndianTrail` | 3228 | Run the priority lists include indian trail workflow for the browser application. | `showRushAlert`, `submitSdi` |
| `slugify` | 3237 | Run the slugify workflow for the browser application. | `checkedForEntry`, `renderRackSetCard` |
| `uniqueText` | 3249 | Run the unique text workflow for the browser application. | `addStationFromInput`, `ids`, `loadLocalStations`, `loadStations`, `manualEditProductOptions`, `removeStation`, `renderHomeStageFilter`, `renderStationOptions` (+1 more) |
| `listsByDeliveryDate` | 3266 | Run the lists by delivery date workflow for the browser application. | `activeRecentImports`, `deliveryListAdminRows`, `openPrintOptions`, `renderAdminDeleteControls`, `renderDeliveryListSelect`, `renderHome`, `wireEvents` |
| `stageSort` | 3286 | Run the stage sort workflow for the browser application. | `deliveryListAdminRows`, `listsByDeliveryDate`, `manualEditStageListsForCurrentDelivery`, `printCountSourceLists`, `renderPrintOptionStages`, `renderTodayProgress`, `stageSortForRow` |
| `selectedDeliveryDate` | 3295 | Run the selected delivery date workflow for the browser application. | `ids`, `openPrintOptions`, `renderDeliveryListSelect`, `renderPrintOptionStages` |
| `hasPermission` | 3304 | Run the has permission workflow for the browser application. | `applyPermissionUi`, `bayEventMoveControlHtml`, `canAssignRackLocation`, `hasAnyPermission`, `ids`, `loadHomeReportSummary`, `maybeShowStaleBayAlert`, `openAdminModal` (+22 more) |
| `hasAnyPermission` | 3314 | Run the has any permission workflow for the browser application. | `applyPermissionUi`, `refreshBayMapPage`, `refreshRacksPage`, `showPage` |
| `setControlAllowed` | 3323 | Update the set control allowed workflow using the existing shared UI state. | `applyPermissionUi` |
| `userAssignedStations` | 3335 | Run the user assigned stations workflow for the browser application. | `renderAdminUsersTable`, `renderStationOptions`, `userAssignedStation`, `userAssignedStationLabel` |
| `userAssignedStation` | 3351 | Run the user assigned station workflow for the browser application. | `applyPermissionUi`, `currentScanStation`, `renderAdminUsersTable` |
| `userAssignedStationLabel` | 3360 | Run the user assigned station label workflow for the browser application. | `renderStationOptions` |
| `currentScanStation` | 3371 | Run the current scan station workflow for the browser application. | `applyPermissionUi`, `processScanInternal`, `requestContext` |
| `requestContext` | 3380 | Run the request context workflow for the browser application. | `addBaysFromForm`, `addBaysToEditorGroup`, `addSpacerBay`, `applyBayLayoutSnapshot`, `clearManagedItem`, `confirmBayLayoutDraft`, `createBayEditorGroup`, `deleteAdminDeliveryDateByDate` (+19 more) |
| `showImportStatusLoading` | 3392 | Open the show import status loading workflow using the existing shared UI state. | `importTempDeliveryFolder` |
| `showImportStatusResult` | 3411 | Open the show import status result workflow using the existing shared UI state. | — |
| `waitForNextPaint` | 3432 | Run the wait for next paint workflow for the browser application. | `importTempDeliveryFolder` |
| `updateModalScrollLock` | 3445 | Update the update modal scroll lock workflow using the existing shared UI state. | `acknowledgeRushAndOpen`, `close`, `closeActionFeedback`, `closeAdminModal`, `closeBayEditorPanel`, `closeEmailDraftPreview`, `closeInTransitManifest`, `closeManageItemsPanel` (+19 more) |
| `fetchJson` | 3470 | Load the fetch JSON workflow using the existing shared UI state. | `acknowledgeUserNotification`, `activateList`, `addBaysFromForm`, `addBaysToEditorGroup`, `addSpacerBay`, `addStationFromInput`, `applyBayLayoutSnapshot`, `assignLineItemToRack` (+88 more) |
| `detectBackend` | 3502 | Run the detect backend workflow for the browser application. | `init` |
| `showLogin` | 3516 | Open the show login workflow using the existing shared UI state. | `fetchJson`, `init`, `logout` |
| `hideLogin` | 3532 | Close the hide login workflow using the existing shared UI state. | `loadSession`, `login` |
| `loadSession` | 3548 | Load the load session workflow using the existing shared UI state. | `init` |
| `login` | 3565 | Run the login workflow for the browser application. | `wireEvents` |
| `showPasswordResetPanel` | 3583 | Open the show password reset panel workflow using the existing shared UI state. | `confirmPasswordReset`, `wireEvents` |
| `setPasswordResetMessage` | 3604 | Update the set password reset message workflow using the existing shared UI state. | `requestPasswordResetCode`, `wireEvents` |
| `requestPasswordResetCode` | 3615 | Run the request password reset code workflow for the browser application. | `wireEvents` |
| `confirmPasswordReset` | 3633 | Run the confirm password reset workflow for the browser application. | `wireEvents` |
| `logout` | 3658 | Run the logout workflow for the browser application. | `wireEvents` |
| `cleanBarcode` | 3675 | Run the clean barcode workflow for the browser application. | `recoverScan` |
| `digitsOnly` | 3691 | Run the digits only workflow for the browser application. | `recoverScan`, `submitManualBayAssign`, `submitManualBayScan`, `submitManualScan` |
| `canonicalRouteDesignation` | 3704 | Run the canonical route designation workflow for the browser application. | `inferredRoute` |
| `hasToken` | 3725 | Run the has token workflow for the browser application. | — |
| `inferredRoute` | 3753 | Run the inferred route workflow for the browser application. | `routeCategory`, `routeLabel` |
| `routeCategory` | 3775 | Run the route category workflow for the browser application. | `filterItemsForProfile`, `isCpuItem`, `itemMatchesScanFilter`, `renderCounts` |
| `routeLabel` | 3788 | Run the route label workflow for the browser application. | `renderItemRow`, `renderMobileCards` |
| `isCpuItem` | 3801 | Run the is CPU item workflow for the browser application. | — |
| `filterItemsForProfile` | 3810 | Run the filter items for profile workflow for the browser application. | `createDemoLists` |
| `cloneItems` | 3823 | Run the clone items workflow for the browser application. | `applyBackendPayload`, `createDemoLists`, `ensurePrintListDetails`, `setActiveList` |
| `createDemoLists` | 3846 | Create the create demo lists workflow using the existing shared UI state. | `init` |
| `loadLocalStations` | 3887 | Load the load local stations workflow using the existing shared UI state. | `init`, `loadStations` |
| `saveLocalStations` | 3901 | Run the save local stations workflow for the browser application. | `addStationFromInput` |
| `renderStationOptions` | 3910 | Render the render station options workflow using the existing shared UI state. | `addStationFromInput`, `applyBackendPayload`, `ids`, `init`, `loadStations`, `removeStation`, `setActiveList` |
| `loadStations` | 3941 | Load the load stations workflow using the existing shared UI state. | `loadAuthenticatedApp` |
| `addStationFromInput` | 3956 | Create the add station from input workflow using the existing shared UI state. | `ids`, `wireEvents` |
| `removeStation` | 3983 | Remove the remove station workflow using the existing shared UI state. | `ids` |
| `applyBackendPayload` | 3999 | Update the apply backend payload workflow using the existing shared UI state. | `activateList`, `assignLineItemToRack`, `deleteManualLineItem`, `processScanInternal`, `resetAdminScansForList`, `resetState`, `wireEvents` |
| `loadDeliveryLists` | 4015 | Load the load delivery lists workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteManualLineItem`, `deleteSelectedDeliveryList`, `ids`, `loadAuthenticatedApp`, `resetAdminScansForDate`, `resetAdminScansForList` (+1 more) |
| `setActiveList` | 4032 | Update the set active list workflow using the existing shared UI state. | `activateList` |
| `activateList` | 4056 | Run the activate list workflow for the browser application. | `assignLineItemToRack`, `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteSelectedDeliveryList`, `ids`, `importTempDeliveryFolder`, `loadDeliveryLists`, `openRushNotificationList` (+5 more) |
| `storageKey` | 4089 | Run the storage key workflow for the browser application. | `restoreState`, `saveState` |
| `saveState` | 4098 | Run the save state workflow for the browser application. | `clearSelectedLineItem`, `ids`, `processLocalScan`, `resetState` |
| `restoreState` | 4115 | Run the restore state workflow for the browser application. | `setActiveList` |
| `itemStatus` | 4138 | Run the item status workflow for the browser application. | `getStats`, `itemMatchesScanFilter`, `renderItemRow`, `renderMobileCards`, `unresolvedPriorityItems`, `unresolvedRemakeItems`, `unresolvedRushItems` |
| `itemText` | 4149 | Run the item text workflow for the browser application. | — |
| `isRemakeItem` | 4158 | Run the is remake item workflow for the browser application. | `isRemakeOrRush`, `itemMatchesScanFilter`, `openSdiPanel`, `renderItemRow`, `selectedRangeRemakeStats`, `transitManifestRowHtml`, `unresolvedRemakeItems` |
| `isRushItem` | 4167 | Run the is rush item workflow for the browser application. | `isRemakeOrRush`, `itemMatchesScanFilter`, `openSdiPanel`, `renderItemRow`, `transitManifestRowHtml`, `unresolvedRushItems` |
| `isRemakeOrRush` | 4176 | Run the is remake or rush workflow for the browser application. | `itemMatchesScanFilter`, `unresolvedPriorityItems` |
| `isNewOrUpdatedItem` | 4185 | Run the is new or updated item workflow for the browser application. | `itemMatchesScanFilter`, `renderItemRow` |
| `hasScanError` | 4194 | Run the has scan error workflow for the browser application. | `itemMatchesScanFilter`, `renderItemRow` |
| `itemPieceQty` | 4203 | Run the item piece qty workflow for the browser application. | `addEntry`, `glassQuantitiesForStatistics`, `itemScannedPieceQty`, `pieceCount`, `selectedRangeRemakeStats`, `unscannedPieceCount` |
| `itemScannedPieceQty` | 4212 | Run the item scanned piece qty workflow for the browser application. | `ensurePrintListDetails`, `getStats`, `itemCanShowRackLocationDropdown`, `unscannedPieceCount` |
| `pieceCount` | 4221 | Run the piece count workflow for the browser application. | `ensurePrintListDetails`, `getStats`, `renderCounts` |
| `unscannedPieceCount` | 4230 | Run the unscanned piece count workflow for the browser application. | `getStats`, `renderCounts` |
| `unresolvedPriorityItems` | 4239 | Run the unresolved priority items workflow for the browser application. | — |
| `unresolvedRemakeItems` | 4248 | Run the unresolved remake items workflow for the browser application. | — |
| `unresolvedRushItems` | 4257 | Run the unresolved rush items workflow for the browser application. | — |
| `scanFlash` | 4266 | Process the scan flash workflow using the existing shared UI state. | `processLocalScan`, `processScanInternal`, `runBayScan`, `showInlineError`, `updateBayScanModeUi`, `wireEvents` |
| `getStats` | 4279 | Resolve the get stats workflow using the existing shared UI state. | `renderCounts`, `renderMobileCards` |
| `scanFilterGroup` | 4299 | Resolve which Scan-page filter group owns a filter key. | `toggleScanFilter` |
| `itemMatchesScanFilter` | 4308 | Test one delivery-list item against one normalized Scan-page filter. | `filteredItems` |
| `isScanFilterActive` | 4328 | Report whether a Scan-page filter button is currently selected. | `renderMobileCards`, `syncScanFilterButtons` |
| `syncScanFilterButtons` | 4337 | Synchronize Scan-page filter button styling and accessibility state. | `openRushNotificationList`, `renderCounts`, `renderMobileCards`, `toggleScanFilter` |
| `toggleScanFilter` | 4350 | Toggle one Scan-page filter while preserving other selected filter groups. | `ids` |
| `filteredItems` | 4366 | Filter Scan-page items using combinable status, attention, route, glass, and search criteria. | `getPagedItems` |
| `groupItemsByGlass` | 4392 | Run the group items by glass workflow for the browser application. | `getPagedItems` |
| `getPagedItems` | 4407 | Resolve the get paged items workflow using the existing shared UI state. | `renderMobileCards`, `renderTable` |
| `stageVerb` | 4447 | Run the stage verb workflow for the browser application. | `renderProcessState` |
| `renderProcessState` | 4462 | Render the render process state workflow using the existing shared UI state. | `renderItemRow` |
| `locationLabel` | 4471 | Run the location label workflow for the browser application. | `renderItemRow` |
| `clearSelectedLineItem` | 4488 | Remove the clear selected line item workflow using the existing shared UI state. | `wireEvents` |
| `canAssignRackLocation` | 4500 | Run the can assign rack location workflow for the browser application. | `ids`, `itemCanShowRackLocationDropdown` |
| `rackStatusValue` | 4514 | Run the rack status value workflow for the browser application. | `rackIsLockedForLineAssignment` |
| `rackIsLockedForLineAssignment` | 4523 | Run the rack is locked for line assignment workflow for the browser application. | `assignableRacks`, `itemCanShowRackLocationDropdown` |
| `rackForCode` | 4532 | Run the rack for code workflow for the browser application. | `itemCanShowRackLocationDropdown` |
| `itemCanShowRackLocationDropdown` | 4543 | Run the item can show rack location dropdown workflow for the browser application. | `rackLocationDropdown` |
| `locationBadgeClass` | 4559 | Run the location badge class workflow for the browser application. | `rackLocationDropdown` |
| `rackLocationDropdown` | 4577 | Run the rack location dropdown workflow for the browser application. | `renderItemRow` |
| `assignableRacks` | 4588 | Run the assignable racks workflow for the browser application. | — |
| `updateScanProgress` | 4607 | Update the shared Scan-page progress meter with consistent text, motion, and completion feedback. | `renderCounts` |
| `bayDualProgressHtml` | 4643 | Render the Bay Map scanner's mirrored Outbound and Received progress halves. | `renderBayRouteFlow` |
| `renderCounts` | 4670 | Render the render counts workflow using the existing shared UI state. | `renderScanPage` |
| `renderPagers` | 4788 | Render the render pagers workflow using the existing shared UI state. | `renderTable` |
| `render` | 4796 | Render the render workflow using the existing shared UI state. | — |
| `glassTypeLabel` | 4824 | Run the glass type label workflow for the browser application. | `addEntry`, `filteredItems`, `glassQuantitiesForStatistics`, `groupItemsByGlass`, `renderCounts`, `transitManifestRackGroups` |
| `renderItemRow` | 4833 | Render the render item row workflow using the existing shared UI state. | — |
| `renderTable` | 4878 | Render the render table workflow using the existing shared UI state. | `renderScanPage` |
| `stagingLists` | 4913 | Run the staging lists workflow for the browser application. | `renderRackSelects` |
| `refreshRacksPage` | 4922 | Load the refresh racks page workflow using the existing shared UI state. | `showPage` |
| `renderRackSelects` | 4937 | Render the render rack selects workflow using the existing shared UI state. | `renderRacksPage` |
| `rackGroupLabel` | 4963 | Run the rack group label workflow for the browser application. | `groupedRackOptionsHtml`, `rackManagerModalHtml`, `racks`, `wireEvents` |
| `groupedRackOptionsHtml` | 4972 | Run the grouped rack options HTML workflow for the browser application. | `assignableRacks`, `renderRackSelects`, `renderScanRackTools` |
| `rackCodeForScan` | 5010 | Run the rack code for scan workflow for the browser application. | `printSelectedRackPackingSlip`, `processScanInternal`, `racks`, `wireEvents` |
| `isTruckRack` | 5020 | Run the is truck rack workflow for the browser application. | `manualEditLocationOptions`, `printSelectedRackPackingSlip`, `rackManagerModalHtml`, `racks` |
| `nextTruckRackDefaults` | 5029 | Run the next truck rack defaults workflow for the browser application. | `ids` |
| `rackIsReceived` | 5046 | Run the rack is received workflow for the browser application. | `outboundRackStatusMeta`, `rackHasMoveOpen`, `rackStatusClassName`, `rackStatusLabel`, `rackVisualClass`, `renderRackBoardCard`, `renderSelectedRackDetails` |
| `rackStatusLabel` | 5055 | Run the rack status label workflow for the browser application. | `manualEditLocationOptions`, `rackManagerModalHtml`, `rackOptionLabel`, `rackStatusText` |
| `rackStatusClassName` | 5070 | Run the rack status class name workflow for the browser application. | `rackComputedStatus`, `rackStatusClass` |
| `rackOptionLabel` | 5085 | Run the rack option label workflow for the browser application. | `groupedRackOptionsHtml`, `racks`, `renderRackItem` |
| `rackDestinationLabel` | 5097 | Run the rack destination label workflow for the browser application. | `chooseRackDestination`, `outboundRackStatusMeta`, `rackDestinationClass`, `renderRackBoardCard`, `showOutboundRackTransitPrompt` |
| `rackDestinationClass` | 5111 | Run the rack destination class workflow for the browser application. | `renderRackBoardCard` |
| `rackVisualClass` | 5124 | Run the rack visual class workflow for the browser application. | `rackHasMoveOpen`, `renderRackBoardCard` |
| `rackComputedStatus` | 5138 | Run the rack computed status workflow for the browser application. | `filteredSortedRacks` |
| `rackSortNumber` | 5147 | Run the rack sort number workflow for the browser application. | `racks` |
| `filteredSortedRacks` | 5157 | Run the filtered sorted racks workflow for the browser application. | `renderRackBoardGroup` |
| `renderRacksPage` | 5186 | Render the render racks page workflow using the existing shared UI state. | `assignLineItemToRack`, `clearRack`, `clearRackItem`, `completeRack`, `createRackSet`, `deleteRackDefinition`, `deleteRackSet`, `markRackNotOnTheWay` (+10 more) |
| `renderRackItem` | 5226 | Render the render rack item workflow using the existing shared UI state. | `renderRackItems` |
| `renderRackItems` | 5298 | Render the render rack items workflow using the existing shared UI state. | `rackHasMoveOpen`, `renderSelectedRackDetails` |
| `renderRack` | 5350 | Render the render rack workflow using the existing shared UI state. | — |
| `rackHasMoveOpen` | 5361 | Run the rack has move open workflow for the browser application. | — |
| `renderRackColumnActions` | 5426 | Render the render rack column actions workflow using the existing shared UI state. | `renderRackBoardGroup` |
| `rackStatusText` | 5461 | Run the rack status text workflow for the browser application. | `renderRackBoardCard`, `renderSelectedRackDetails` |
| `rackStatusClass` | 5468 | Run the rack status class workflow for the browser application. | `renderRackBoardCard`, `renderSelectedRackDetails` |
| `renderRackBoardCard` | 5475 | Render the render rack board card workflow using the existing shared UI state. | — |
| `renderRackBoardGroup` | 5522 | Render the render rack board group workflow using the existing shared UI state. | — |
| `renderRackSetCard` | 5580 | Render the render rack set card workflow using the existing shared UI state. | — |
| `renderSelectedRackDetails` | 5611 | Render the render selected rack details workflow using the existing shared UI state. | — |
| `showRackDestinationOverrideDialog` | 5734 | Open the show rack destination override dialog workflow using the existing shared UI state. | `processScanInternal`, `submitRackScan` |
| `submitRackScan` | 5763 | Process the submit rack scan workflow using the existing shared UI state. | `wireEvents` |
| `chooseRackDestination` | 5802 | Run the choose rack destination workflow for the browser application. | — |
| `close` | 5836 | Close the close workflow using the existing shared UI state. | `notifyPrintComplete`, `submit` |
| `completeRack` | 5863 | Run the complete rack workflow for the browser application. | `wireEvents` |
| `uncompleteRack` | 5877 | Run the uncomplete rack workflow for the browser application. | `wireEvents` |
| `returnRack` | 5890 | Run the return rack workflow for the browser application. | `wireEvents` |
| `markRackNotOnTheWay` | 5921 | Run the mark rack not on the way workflow for the browser application. | `wireEvents` |
| `assignLineItemToRack` | 5946 | Run the assign line item to rack workflow for the browser application. | `wireEvents` |
| `clearRack` | 5973 | Remove the clear rack workflow using the existing shared UI state. | `wireEvents` |
| `clearRackSet` | 5999 | Remove the clear rack set workflow using the existing shared UI state. | `wireEvents` |
| `racks` | 6005 | Run the racks workflow for the browser application. | — |
| `moveRackItem` | 6040 | Run the move rack item workflow for the browser application. | `wireEvents` |
| `clearRackItem` | 6066 | Remove the clear rack item workflow using the existing shared UI state. | `wireEvents` |
| `rackPackingListUrl` | 6086 | Run the rack packing list URL workflow for the browser application. | `printSelectedRackPackingSlip`, `wireEvents` |
| `printSelectedRackPackingSlip` | 6096 | Run the print selected rack packing slip workflow for the browser application. | `wireEvents` |
| `saveRackDefinition` | 6114 | Run the save rack definition workflow for the browser application. | `wireEvents` |
| `selectedRackManagerRack` | 6136 | Run the selected rack manager rack workflow for the browser application. | `populateRackManagerQuickEdit`, `rackManagerModalHtml` |
| `populateRackManagerQuickEdit` | 6145 | Run the populate rack manager quick edit workflow for the browser application. | `wireEvents` |
| `saveRackQuickEdit` | 6164 | Run the save rack quick edit workflow for the browser application. | `wireEvents` |
| `deleteRackDefinition` | 6195 | Remove the delete rack definition workflow using the existing shared UI state. | `ids`, `wireEvents` |
| `createRackSet` | 6221 | Create the create rack set workflow using the existing shared UI state. | `wireEvents` |
| `openRackForm` | 6247 | Open the open rack form workflow using the existing shared UI state. | `ids`, `wireEvents` |
| `openRackSetForm` | 6259 | Open the open rack set form workflow using the existing shared UI state. | `ids`, `wireEvents` |
| `deleteRackSet` | 6277 | Remove the delete rack set workflow using the existing shared UI state. | `ids`, `wireEvents` |
| `renderMobileCards` | 6304 | Render the render mobile cards workflow using the existing shared UI state. | `renderScanPage` |
| `scanEntryEventLabel` | 6349 | Process the scan entry event label workflow using the existing shared UI state. | `recentScansModalHtml`, `renderRecent` |
| `scanEntryDeliveryDateHint` | 6367 | Process the scan entry delivery date hint workflow using the existing shared UI state. | `scanEntryCompactMessage`, `scanEntryFullDetail` |
| `scanEntryCompactMessage` | 6386 | Process the scan entry compact message workflow using the existing shared UI state. | `recentScansModalHtml`, `renderRecent`, `setLastScan` |
| `scanEntryFullDetail` | 6414 | Process the scan entry full detail workflow using the existing shared UI state. | `recentScansModalHtml` |
| `scanEntryRowClass` | 6438 | Process the scan entry row class workflow using the existing shared UI state. | `recentScansModalHtml`, `renderRecent` |
| `setLastScan` | 6448 | Update the set last scan workflow using the existing shared UI state. | `renderLastScan` |
| `renderLastScan` | 6471 | Render the render last scan workflow using the existing shared UI state. | `renderScanPage` |
| `sameScanEntry` | 6491 | Run the same scan entry workflow for the browser application. | `recentRowsExcludingCurrentLastScan` |
| `scanEntryIsManual` | 6506 | Process the scan entry is manual workflow using the existing shared UI state. | `scanEntryCompactMessage`, `scanEntryRowClass`, `setLastScan` |
| `mainScanRecentLimit` | 6515 | Run the main scan recent limit workflow for the browser application. | `recentRowsExcludingCurrentLastScan`, `renderRecent` |
| `recentRowsExcludingCurrentLastScan` | 6524 | Run the recent rows excluding current last scan workflow for the browser application. | `renderRecent` |
| `renderRecent` | 6536 | Render the render recent workflow using the existing shared UI state. | `renderScanPage`, `syncFullscreenControl`, `wireEvents` |
| `recentScansModalHtml` | 6568 | Run the recent scans modal HTML workflow for the browser application. | `adminModalContent` |
| `renderMeta` | 6639 | Render the render meta workflow using the existing shared UI state. | `renderScanPage` |
| `renderDeliveryListSelect` | 6658 | Render the render delivery list select workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteSelectedDeliveryList`, `loadDeliveryLists`, `renderMeta`, `resetAdminScansForDate` |
| `stageLists` | 6673 | Run the stage lists workflow for the browser application. | — |
| `applyPermissionUi` | 6692 | Update the apply permission UI workflow using the existing shared UI state. | `renderHome`, `renderScanPage` |
| `renderScanPage` | 6746 | Render the render scan page workflow using the existing shared UI state. | `activateList`, `assignLineItemToRack`, `clearSelectedLineItem`, `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteManualLineItem`, `deleteSelectedDeliveryList`, `ids` (+9 more) |
| `isStagingScanContext` | 6765 | Run the is staging scan context workflow for the browser application. | `canAssignRackLocation`, `processScanInternal`, `renderScanRackTools` |
| `isOutboundScanContext` | 6774 | Run the is outbound scan context workflow for the browser application. | `processScanInternal`, `renderOutboundRackStatusTools` |
| `ensureRacksLoaded` | 6783 | Run the ensure racks loaded workflow for the browser application. | `deleteRackSet`, `ids`, `processScanInternal`, `renderOutboundRackStatusTools`, `renderScanRackTools`, `showOutboundOverrideDialog`, `wireEvents` |
| `renderScanRackTools` | 6797 | Render the render scan rack tools workflow using the existing shared UI state. | `clearRackItem`, `completeRack`, `createRackSet`, `deleteRackDefinition`, `deleteRackSet`, `ensureRacksLoaded`, `markRackNotOnTheWay`, `racks` (+6 more) |
| `outboundRackStatusMeta` | 6851 | Run the outbound rack status meta workflow for the browser application. | `outboundRackStatusOptionsHtml`, `renderOutboundRackStatusTools` |
| `outboundRackStatusOptionsHtml` | 6894 | Run the outbound rack status options HTML workflow for the browser application. | `renderOutboundRackStatusTools` |
| `renderOutboundRackStatusTools` | 6924 | Render the render outbound rack status tools workflow using the existing shared UI state. | `ensureRacksLoaded`, `renderScanPage`, `wireEvents` |
| `isIndianTrailScanContext` | 6962 | Run the is indian trail scan context workflow for the browser application. | `scanBayOverrideVisible` |
| `renderManualAssignTools` | 6971 | Render the render manual assign tools workflow using the existing shared UI state. | `renderScanPage` |
| `ensureScanBayOverrideBays` | 6982 | Run the ensure scan bay override bays workflow for the browser application. | `renderScanBayOverrideTools`, `showIndianTrailOutboundReceiveOverride`, `showIndianTrailPlacementPrompt` |
| `scanBayOverrideVisible` | 6994 | Process the scan bay override visible workflow using the existing shared UI state. | `renderScanBayOverrideTools` |
| `bayOverrideGroupLabel` | 7003 | Run the bay override group label workflow for the browser application. | `indianTrailBayOptionsHtml`, `renderScanBayOverrideTools` |
| `bayOverrideSort` | 7012 | Run the bay override sort workflow for the browser application. | — |
| `renderScanBayOverrideTools` | 7023 | Render the render scan bay override tools workflow using the existing shared UI state. | `ensureScanBayOverrideBays`, `ids`, `renderScanPage`, `wireEvents` |
| `compatibleBayCandidates` | 7096 | Run the compatible bay candidates workflow for the browser application. | `submitManualBayAssign` |
| `submitManualBayAssign` | 7115 | Process the submit manual bay assign workflow using the existing shared UI state. | `wireEvents` |
| `miniStat` | 7149 | Run the mini stat workflow for the browser application. | `lookupManagerModalHtml`, `refreshAdminPage`, `renderBayMapPage`, `renderHomeStatistics`, `renderManageItemsPanel`, `renderRacksPage` |
| `aggregateListStats` | 7158 | Run the aggregate list stats workflow for the browser application. | `openHomeStatisticsReport`, `renderHome`, `statisticsChartKpiHtml` |
| `homeStageBreakdown` | 7188 | Run the home stage breakdown workflow for the browser application. | `openHomeStatisticsReport`, `renderHomeStatistics`, `statisticsChartDataset` |
| `homeStatisticsRangeParts` | 7215 | Run the home statistics range parts workflow for the browser application. | `homeStatisticsRangeLabel`, `renderHomeStatistics`, `renderMonthlyRemakes`, `renderStatisticsChartModal` |
| `homeStatisticsRangeLabel` | 7227 | Run the home statistics range label workflow for the browser application. | `renderStatisticsChartModal` |
| `homeReportDateParams` | 7237 | Run the home report date params workflow for the browser application. | `loadHomeReportSummary` |
| `reportActionCount` | 7254 | Run the report action count workflow for the browser application. | `renderHomeStatistics` |
| `glassQuantitiesForStatistics` | 7265 | Run the glass quantities for statistics workflow for the browser application. | `openHomeStatisticsReport`, `renderHomeStatsChart`, `statisticsChartDataset` |
| `renderHomeStatsChart` | 7297 | Render the render home stats chart workflow using the existing shared UI state. | `renderHomeStatistics` |
| `statisticsChartKpiHtml` | 7374 | Run the statistics chart kpi HTML workflow for the browser application. | `renderStatisticsChartModal` |
| `successfulScans` | 7383 | Run the successful scans workflow for the browser application. | — |
| `statisticsChartListLabel` | 7412 | Run the statistics chart list label workflow for the browser application. | `statisticsChartDataset` |
| `statisticsChartDataset` | 7422 | Run the statistics chart dataset workflow for the browser application. | `renderStatisticsChartModal` |
| `filteredStatisticsChartEntries` | 7590 | Run the filtered statistics chart entries workflow for the browser application. | `renderStatisticsChartModal` |
| `entries` | 7600 | Run the entries workflow for the browser application. | `applyBayLayoutDraft`, `bayGlassFilterOptions`, `bayPhysicalSections`, `bayTypeSections`, `checkedForEntry`, `glassQuantitiesForStatistics`, `groupItemsByGlass`, `groupedRackOptionsHtml` (+11 more) |
| `chartEntryColor` | 7627 | Run the chart entry color workflow for the browser application. | `statisticsBarChartHtml`, `statisticsDonutChartHtml` |
| `truncateChartLabel` | 7636 | Run the truncate chart label workflow for the browser application. | `statisticsBarChartHtml` |
| `statisticsChartSelectionHtml` | 7646 | Run the statistics chart selection HTML workflow for the browser application. | `renderStatisticsChartModal` |
| `statisticsBarChartHtml` | 7667 | Run the statistics bar chart HTML workflow for the browser application. | `renderStatisticsChartModal` |
| `statisticsDonutChartHtml` | 7722 | Run the statistics donut chart HTML workflow for the browser application. | `renderStatisticsChartModal` |
| `renderStatisticsChartModal` | 7792 | Render the render statistics chart modal workflow using the existing shared UI state. | `openStatisticsChartModal`, `wireEvents` |
| `openStatisticsChartModal` | 7867 | Open the open statistics chart modal workflow using the existing shared UI state. | `wireEvents` |
| `closeStatisticsChartModal` | 7880 | Close the close statistics chart modal workflow using the existing shared UI state. | `wireEvents` |
| `selectedRangeRemakeStats` | 7891 | Run the selected range remake stats workflow for the browser application. | `renderMonthlyRemakes`, `statisticsChartDataset` |
| `renderMonthlyRemakes` | 7923 | Render the render monthly remakes workflow using the existing shared UI state. | `renderHomeStatistics` |
| `renderHomeStatistics` | 7943 | Render the render home statistics workflow using the existing shared UI state. | `renderHome` |
| `loadHomeReportSummary` | 8027 | Load the load home report summary workflow using the existing shared UI state. | `loadAuthenticatedApp`, `wireEvents` |
| `openHomeStatisticsReport` | 8044 | Open the open home statistics report workflow using the existing shared UI state. | `wireEvents` |
| `notifyPrintComplete` | 8133 | Run the notify print complete workflow for the browser application. | — |
| `stageProgressSegments` | 8168 | Run the stage progress segments workflow for the browser application. | `renderStackedProgress` |
| `progressWidth` | 8189 | Run the progress width workflow for the browser application. | `deliveryListCard`, `renderStackedProgress` |
| `renderStackedProgress` | 8199 | Render the render stacked progress workflow using the existing shared UI state. | `renderHome` |
| `filteredDeliveryLists` | 8218 | Run the filtered delivery lists workflow for the browser application. | `renderHome` |
| `deliveryListCard` | 8233 | Run the delivery list card workflow for the browser application. | `renderHome` |
| `renderTodayProgress` | 8267 | Render the render today progress workflow using the existing shared UI state. | `renderHome` |
| `renderHomeStageFilter` | 8307 | Render the render home stage filter workflow using the existing shared UI state. | `renderHome` |
| `renderHome` | 8329 | Render the render home workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteSelectedDeliveryList`, `ids`, `importTempDeliveryFolder`, `loadDeliveryLists`, `loadHomeReportSummary`, `resetAdminScansForDate` (+2 more) |
| `showPage` | 8406 | Open the show page workflow using the existing shared UI state. | `activateList`, `ids`, `init`, `loadAuthenticatedApp`, `openRushNotificationList` |
| `showOutboundOverrideDialog` | 8446 | Open the show outbound override dialog workflow using the existing shared UI state. | `processScanInternal` |
| `racks` | 8453 | Run the racks workflow for the browser application. | — |
| `close` | 8501 | Close the close workflow using the existing shared UI state. | `notifyPrintComplete`, `submit` |
| `availableIndianTrailBays` | 8536 | Run the available indian trail bays workflow for the browser application. | `bayEventMoveOptionsHtml`, `indianTrailBayOptionsHtml`, `showIndianTrailOutboundReceiveOverride`, `showIndianTrailPlacementPrompt` |
| `indianTrailBayOptionsHtml` | 8548 | Run the indian trail bay options HTML workflow for the browser application. | `showIndianTrailOutboundReceiveOverride`, `showIndianTrailPlacementPrompt` |
| `showIndianTrailOutboundReceiveOverride` | 8567 | Open the show indian trail outbound receive override workflow using the existing shared UI state. | `processScanInternal`, `runBayScan` |
| `close` | 8628 | Close the close workflow using the existing shared UI state. | `notifyPrintComplete`, `submit` |
| `closeTimedScanConfirmation` | 8661 | Close the close timed scan confirmation workflow using the existing shared UI state. | `closeIndianTrailPlacementPrompt`, `mountTimedScanConfirmation`, `openHistory`, `setPaused` |
| `mountTimedScanConfirmation` | 8676 | Run the mount timed scan confirmation workflow for the browser application. | `showIndianTrailPlacementPrompt`, `showOutboundRackTransitPrompt` |
| `setPaused` | 8709 | Pause or resume the timed scan confirmation countdown. | — |
| `openHistory` | 8739 | Open the appropriate All Scans view from a timed scan confirmation. | — |
| `closeIndianTrailPlacementPrompt` | 8759 | Close the close indian trail placement prompt workflow using the existing shared UI state. | `showIndianTrailPlacementPrompt` |
| `showOutboundRackTransitPrompt` | 8768 | Open the show outbound rack transit prompt workflow using the existing shared UI state. | `processScanInternal` |
| `showIndianTrailPlacementPrompt` | 8817 | Open the show indian trail placement prompt workflow using the existing shared UI state. | `processScanInternal`, `runBayScan` |
| `processScan` | 8910 | Run the process scan workflow for the browser application. | `acknowledgeRushAndOpen`, `close`, `processScanInternal`, `submitManualScan`, `wireEvents` |
| `cleanup` | 8918 | Run the cleanup workflow for the browser application. | — |
| `processScanInternal` | 8931 | Run the process scan internal workflow for the browser application. | `processScan` |
| `submitManualScan` | 9051 | Process the submit manual scan workflow using the existing shared UI state. | `wireEvents` |
| `processLocalScan` | 9069 | Run the process local scan workflow for the browser application. | `processScanInternal` |
| `buildIndexes` | 9118 | Build the build indexes workflow using the existing shared UI state. | `recoverScan` |
| `recoverScan` | 9139 | Run the recover scan workflow for the browser application. | `processLocalScan` |
| `resetState` | 9177 | Run the reset state workflow for the browser application. | — |
| `showInlineError` | 9201 | Open the show inline error workflow using the existing shared UI state. | `close`, `email`, `ids`, `launchManagedPrint`, `notifyPrintComplete`, `openAdminModal`, `openBayLayoutManager`, `openPrintOptions` (+18 more) |
| `showFloatingNotice` | 9216 | Open the show floating notice workflow using the existing shared UI state. | `acknowledgeRushAndOpen`, `assignLineItemToRack`, `cancelBayLayoutDraft`, `close`, `closeBayLayoutManager`, `completeRack`, `confirmBayLayoutDraft`, `deleteBayEditorBay` (+24 more) |
| `closeActionFeedback` | 9238 | Close the close action feedback workflow using the existing shared UI state. | `closeWithSecondary`, `showActionFeedback`, `wireEvents` |
| `showActionFeedback` | 9249 | Open the show action feedback workflow using the existing shared UI state. | `clearRack`, `racks`, `returnRack`, `showFullscreenRecoveryPrompt`, `showSaveConfirmation`, `submitSdi` |
| `closeWithSecondary` | 9301 | Close the close with secondary workflow using the existing shared UI state. | — |
| `showSaveConfirmation` | 9328 | Confirm that an explicit save/create action completed successfully. | `addBaysFromForm`, `addBaysToEditorGroup`, `addSpacerBay`, `addStationFromInput`, `confirmBayLayoutDraft`, `createBayEditorGroup`, `createRackSet`, `createUserFromForm` (+18 more) |
| `rushNotificationIsBlocked` | 9344 | Run the rush notification is blocked workflow for the browser application. | `presentNextUserNotification`, `showRushAlert` |
| `acknowledgeUserNotification` | 9363 | Run the acknowledge user notification workflow for the browser application. | `acknowledgeRushAndOpen` |
| `rushNotificationTargetList` | 9377 | Run the rush notification target list workflow for the browser application. | `openRushNotificationList` |
| `openRushNotificationList` | 9404 | Open the open rush notification list workflow using the existing shared UI state. | `acknowledgeRushAndOpen` |
| `waitForActiveScanOperations` | 9431 | Run the wait for active scan operations workflow for the browser application. | `acknowledgeRushAndOpen` |
| `acknowledgeRushAndOpen` | 9443 | Run the acknowledge rush and open workflow for the browser application. | `showRushAlert` |
| `showRushAlert` | 9484 | Open the show rush alert workflow using the existing shared UI state. | `acknowledgeRushAndOpen`, `presentNextUserNotification` |
| `presentNextUserNotification` | 9563 | Run the present next user notification workflow for the browser application. | `acknowledgeRushAndOpen`, `cleanup`, `closeActionFeedback`, `pollUserNotifications`, `showPage` |
| `pollUserNotifications` | 9575 | Run the poll user notifications workflow for the browser application. | `showPage`, `startNotificationPolling`, `wireEvents` |
| `startNotificationPolling` | 9601 | Run the start notification polling workflow for the browser application. | `loadAuthenticatedApp` |
| `stopNotificationPolling` | 9614 | Run the stop notification polling workflow for the browser application. | `fetchJson`, `logout`, `startNotificationPolling` |
| `restoreFullscreenAfterManagedPrint` | 9628 | Run the restore fullscreen after managed print workflow for the browser application. | `afterPrint`, `finishManagedPrintSession` |
| `stopManagedPrintWindowWatch` | 9649 | Run the stop managed print window watch workflow for the browser application. | `finishManagedPrintSession`, `watchManagedPrintWindow` |
| `finishManagedPrintSession` | 9665 | Run the finish managed print session workflow for the browser application. | `checkManagedPrintWindowClosed`, `wireEvents` |
| `checkManagedPrintWindowClosed` | 9676 | Run the check managed print window closed workflow for the browser application. | `wireEvents` |
| `watchManagedPrintWindow` | 9697 | Run the watch managed print window workflow for the browser application. | `launchManagedPrint`, `notifyPrintComplete` |
| `launchManagedPrint` | 9708 | Run the launch managed print workflow for the browser application. | `ids`, `openPrintPackage`, `printSelectedRackPackingSlip`, `submitPrintOptions`, `submitSdi`, `updateBayScanModeUi`, `wireEvents` |
| `printCurrentPageManaged` | 9726 | Run the print current page managed workflow for the browser application. | `submitPrintOptions` |
| `afterPrint` | 9733 | Run the after print workflow for the browser application. | — |
| `runGlobalSearch` | 9746 | Run the run global search workflow for the browser application. | `wireEvents` |
| `globalSearchProcessClass` | 9763 | Run the global search process class workflow for the browser application. | `globalSearchStatusBadges` |
| `globalSearchStatusBadges` | 9784 | Run the global search status badges workflow for the browser application. | `renderGlobalSearchResults` |
| `renderGlobalSearchResults` | 9796 | Render the render global search results workflow using the existing shared UI state. | `runGlobalSearch` |
| `indianTrailDateQuery` | 9838 | Build the date-aware Indian Trail API suffix used by every Bay Map route request. | `openInTransitManifest`, `refreshBayMapPage`, `refreshBayRouteSummary` |
| `refreshBayRouteSummary` | 9848 | Refresh only the Bay Map Outbound, in-transit, and Received counters for live multi-user visibility. | `startPolling` |
| `refreshBayMapPage` | 9865 | Load the refresh bay map page workflow using the existing shared UI state. | `applyBayLayoutSnapshot`, `clearManagedItem`, `confirmBayLayoutDraft`, `moveManagedItem`, `postBayAction`, `processScanInternal`, `refreshBayEditorAfter`, `runBayHistory` (+3 more) |
| `renderBayRouteFlow` | 9897 | Render the render bay route flow workflow using the existing shared UI state. | `refreshBayMapPage`, `refreshBayRouteSummary` |
| `transitManifestRowHtml` | 10013 | Run the transit manifest row HTML workflow for the browser application. | — |
| `transitRackDisplayName` | 10038 | Run the transit rack display name workflow for the browser application. | `transitManifestHtml` |
| `transitRackSortValue` | 10051 | Run the transit rack sort value workflow for the browser application. | `transitManifestRackGroups` |
| `transitManifestGlassTypeClass` | 10064 | Run the transit manifest glass type class workflow for the browser application. | `transitManifestRackGroups` |
| `transitManifestSourceRows` | 10082 | Run the transit manifest source rows workflow for the browser application. | `transitManifestHtml`, `transitManifestRackGroups` |
| `transitManifestRackGroups` | 10110 | Run the transit manifest rack groups workflow for the browser application. | `transitManifestHtml` |
| `transitRackIconClass` | 10190 | Run the transit rack icon class workflow for the browser application. | `transitManifestHtml` |
| `transitManifestHtml` | 10204 | Run the transit manifest HTML workflow for the browser application. | `openInTransitManifest` |
| `openInTransitManifest` | 10279 | Open the open in transit manifest workflow using the existing shared UI state. | `ids` |
| `closeInTransitManifest` | 10311 | Close the close in transit manifest workflow using the existing shared UI state. | `ids`, `openInTransitManifest` |
| `renderIndianTrailSummary` | 10321 | Render the render indian trail summary workflow using the existing shared UI state. | `refreshBayMapPage`, `refreshBayRouteSummary` |
| `bayMatchesFilter` | 10351 | Run the bay matches filter workflow for the browser application. | `countable`, `renderBayMapPage`, `renderBaySection`, `renderBaySlotButton` |
| `bayHasErrorState` | 10382 | Run the bay has error state workflow for the browser application. | `bayMatchesFilter`, `renderBaySection` |
| `filterOptionLabel` | 10403 | Run the filter option label workflow for the browser application. | `activeBayFilterChips` |
| `selectOptionLabel` | 10413 | Run the select option label workflow for the browser application. | `activeBayFilterChips` |
| `activeBayFilterChips` | 10424 | Run the active bay filter chips workflow for the browser application. | `renderBayFilterSummary` |
| `resetBayFilters` | 10442 | Run the reset bay filters workflow for the browser application. | — |
| `renderBayFilterSummary` | 10464 | Render the render bay filter summary workflow using the existing shared UI state. | `renderBayMapPage` |
| `countable` | 10474 | Run the countable workflow for the browser application. | — |
| `normalizeFilterValue` | 10505 | Normalize the normalize filter value workflow using the existing shared UI state. | `bayGlassFilterOptions`, `bayMatchesFilter` |
| `bayGlassLabel` | 10514 | Run the bay glass label workflow for the browser application. | `bayMatchesFilter` |
| `isWorkbookLegendCell` | 10524 | Run the is workbook legend cell workflow for the browser application. | — |
| `statusAbbreviation` | 10533 | Run the status abbreviation workflow for the browser application. | `renderBaySlotButton` |
| `bayCategoryKind` | 10552 | Run the bay category kind workflow for the browser application. | `bayLayoutSnapshot`, `bayMatchesFilter`, `bayOptionGroups`, `bayOverview`, `bayPhysicalSections`, `bayStatusKind`, `bayTypeSections`, `bays` (+6 more) |
| `bayCategoryLabel` | 10571 | Run the bay category label workflow for the browser application. | `bayTypeSections`, `renderBayLayoutGroupCard`, `renderBaySection`, `renderBaySidePanels`, `renderBaySlotButton` |
| `bayCategoryOrder` | 10592 | Run the bay category order workflow for the browser application. | `bayTypeSections` |
| `bayRackLabel` | 10601 | Run the bay rack label workflow for the browser application. | `bayPhysicalSections`, `bayTypeSections`, `collapseAllPhysicalBaySections`, `runBayAction` |
| `baySearchText` | 10610 | Run the bay search text workflow for the browser application. | `countable`, `renderBayMapPage`, `renderBaySection`, `renderBaySlotButton` |
| `bayPolicyKind` | 10627 | Run the bay policy kind workflow for the browser application. | `bayEditorBayRowMarkup`, `bayMatchesFilter`, `bayOverview`, `bayStatusKind`, `bayStatusLabel`, `bays`, `policies`, `renderBaySection` (+2 more) |
| `bayStatusKind` | 10643 | Run the bay status kind workflow for the browser application. | `bayMatchesFilter`, `bayOverview`, `bayStatusLabel`, `compatibleBayCandidates`, `renderBaySection`, `renderBaySidePanels`, `renderBaySlotButton`, `renderManageItemsPanel` |
| `bayStatusLabel` | 10661 | Run the bay status label workflow for the browser application. | `renderBaySidePanels` |
| `bayUtilization` | 10678 | Run the bay utilization workflow for the browser application. | `renderBaySlotButton` |
| `bayCategoryFilterOptions` | 10690 | Run the bay category filter options workflow for the browser application. | `activeBayFilterChips`, `renderBaySidePanels` |
| `bayGlassFilterOptions` | 10709 | Run the bay glass filter options workflow for the browser application. | `renderBaySidePanels` |
| `bayOverview` | 10725 | Run the bay overview workflow for the browser application. | `renderBayMapPage`, `renderIndianTrailSummary` |
| `bayGroupPolicySummary` | 10754 | Run the bay group policy summary workflow for the browser application. | `renderBaySection` |
| `bays` | 10760 | Run the bays workflow for the browser application. | — |
| `assignmentJobKey` | 10795 | Run the assignment job key workflow for the browser application. | `groupAssignmentsByJob` |
| `assignmentJobLabel` | 10806 | Run the assignment job label workflow for the browser application. | `groupAssignmentsByJob`, `renderBaySidePanels`, `renderManageItemsPanel` |
| `groupAssignmentsByJob` | 10815 | Run the group assignments by job workflow for the browser application. | `bayAssignmentRows`, `renderBaySidePanels`, `renderBaySlotButton` |
| `bayJobDetailForGroup` | 10852 | Run the bay job detail for group workflow for the browser application. | `renderBaySidePanels` |
| `selectedBayJobItemsHtml` | 10862 | Run the selected bay job items HTML workflow for the browser application. | `renderBaySidePanels` |
| `renderBaySlotButton` | 10892 | Render the render bay slot button workflow using the existing shared UI state. | `renderBaySection`, `renderBaySidePanels` |
| `bayTypeSections` | 10955 | Run the bay type sections workflow for the browser application. | `renderBaySidePanels` |
| `bayPhysicalSections` | 10997 | Run the bay physical sections workflow for the browser application. | `bayEditorGroups`, `bayLayoutColumns`, `bayOptionGroups`, `confirmBayLayoutDraft`, `holdAllBaySections`, `initializeBayLayoutDraft`, `insertBaySectionDraft`, `openBayEditorPanel` (+1 more) |
| `initializeBayLayoutDraft` | 11021 | Run the initialize bay layout draft workflow for the browser application. | `openBayLayoutManager`, `renderBayGrid` |
| `normalizedBayGridPositions` | 11048 | Normalize the normalized bay grid positions workflow using the existing shared UI state. | — |
| `renderBaySection` | 11067 | Render the render bay section workflow using the existing shared UI state. | `renderBayGrid` |
| `bayLayoutColumns` | 11108 | Run the bay layout columns workflow for the browser application. | `ids`, `insertBaySectionDraft`, `renderBayGrid`, `shiftBaySectionDraft` |
| `renderBayLayoutDropZone` | 11126 | Render the render bay layout drop zone workflow using the existing shared UI state. | `renderBayGrid` |
| `renderBayLayoutGroupCard` | 11143 | Render the render bay layout group card workflow using the existing shared UI state. | `renderBayGrid` |
| `insertBaySectionDraft` | 11181 | Run the insert bay section draft workflow for the browser application. | `ids`, `shiftBaySectionDraft` |
| `shiftBaySectionDraft` | 11224 | Run the shift bay section draft workflow for the browser application. | `updateBayScanModeUi` |
| `renderBayGrid` | 11265 | Render the render bay grid workflow using the existing shared UI state. | `renderBayMapPage` |
| `collapseAllPhysicalBaySections` | 11360 | Run the collapse all physical bay sections workflow for the browser application. | `ids`, `resetBayFilters`, `wireEvents` |
| `syncBaySectionState` | 11369 | Run the sync bay section state workflow for the browser application. | `animateBaySectionToggle`, `renderBayMapPage` |
| `animateBaySectionToggle` | 11381 | Run the animate bay section toggle workflow for the browser application. | `renderBayMapPage` |
| `renderBayMapPage` | 11425 | Render the render bay map page workflow using the existing shared UI state. | `addBaysFromForm`, `addSpacerBay`, `applyBayLayoutDraft`, `cancelBayLayoutDraft`, `closeBayLayoutManager`, `deleteSelectedBay`, `deleteSelectedBayGroup`, `holdAllBaySections` (+12 more) |
| `renderBaySidePanels` | 11468 | Render the render bay side panels workflow using the existing shared UI state. | `loadBayJobDetails`, `renderBayMapPage` |
| `loadStaleBayOrders` | 11641 | Load the load stale bay orders workflow using the existing shared UI state. | `maybeShowStaleBayAlert`, `runBayAction` |
| `maybeShowStaleBayAlert` | 11656 | Run the maybe show stale bay alert workflow for the browser application. | `refreshBayMapPage` |
| `openStaleBayPanel` | 11672 | Open the open stale bay panel workflow using the existing shared UI state. | `maybeShowStaleBayAlert`, `runBayAction` |
| `closeStaleBayPanel` | 11685 | Close the close stale bay panel workflow using the existing shared UI state. | `updateBayScanModeUi` |
| `renderStaleBayPanel` | 11696 | Render the render stale bay panel workflow using the existing shared UI state. | `openStaleBayPanel`, `snoozeStaleBayOrders` |
| `snoozeStaleBayOrders` | 11770 | Run the snooze stale bay orders workflow for the browser application. | `ids` |
| `renderBayLegend` | 11785 | Render the render bay legend workflow using the existing shared UI state. | — |
| `formatEventType` | 11808 | Normalize the format event type workflow using the existing shared UI state. | `openBayAllScansModal`, `renderBayLastScanCard`, `renderBayRecentActions` |
| `bayEventTone` | 11819 | Run the bay event tone workflow for the browser application. | `renderBayLastScanCard`, `renderBayRecentActions` |
| `bayEventMoveOptionsHtml` | 11831 | Run the bay event move options HTML workflow for the browser application. | `bayEventMoveControlHtml`, `renderBayLastScanCard` |
| `bayEventMoveControlHtml` | 11843 | Run the bay event move control HTML workflow for the browser application. | `openBayAllScansModal`, `renderBayRecentActions` |
| `fitBayLastLocationText` | 11879 | Scale and wrap the Bay Map last-location label so long multi-word bay names remain large and fully readable. | `renderBayLastScanCard`, `setAppLanguage`, `wireEvents` |
| `renderBayLastScanCard` | 11907 | Render the Bay Map last-scan card with a prominent auto-fitted current location and shared move control. | `renderBayRecentActions` |
| `bayScanRecentLimit` | 11954 | Resolve how many Bay Map recent actions fit in the current display mode. | `renderBayRecentActions` |
| `renderBayRecentActions` | 11963 | Render the Bay Map scanner's last action and responsive recent-action history. | `renderBayMapPage`, `wireEvents` |
| `scrollToBaySearchMatch` | 11996 | Run the scroll to bay search match workflow for the browser application. | `ids`, `wireEvents` |
| `selectedBay` | 12016 | Run the selected bay workflow for the browser application. | `addSpacerBay`, `deleteSelectedBayGroup`, `match`, `openSdiPanel`, `populateBayLayoutForm`, `renderBaySidePanels`, `requireSelectedBay`, `runBayAction` (+1 more) |
| `loadBayJobDetails` | 12025 | Load the load bay job details workflow using the existing shared UI state. | `refreshBayMapPage`, `selectBay` |
| `selectBay` | 12056 | Run the select bay workflow for the browser application. | `ids`, `updateBayScanModeUi` |
| `closeSelectedBayModal` | 12077 | Close the close selected bay modal workflow using the existing shared UI state. | `runBayAction`, `updateBayScanModeUi` |
| `requireSelectedBay` | 12088 | Run the require selected bay workflow for the browser application. | `runBayAction` |
| `postBayAction` | 12102 | Run the post bay action workflow for the browser application. | `ids`, `runBayAction`, `runBayScan`, `showIndianTrailPlacementPrompt`, `submitSdi`, `updateBayScanModeUi`, `wireEvents` |
| `pushBayHistory` | 12116 | Run the push bay history workflow for the browser application. | `runBayAction`, `runBayScan`, `updateBayScanModeUi` |
| `runBayHistory` | 12127 | Run the run bay history workflow for the browser application. | `updateBayScanModeUi` |
| `runBayScan` | 12146 | Run the run bay scan workflow for the browser application. | `submitBayScanOut`, `submitManualBayScan` |
| `submitBayScanOut` | 12224 | Process the submit bay scan out workflow using the existing shared UI state. | `wireEvents` |
| `submitManualBayScan` | 12238 | Process the submit manual bay scan workflow using the existing shared UI state. | `wireEvents` |
| `selectedBayAssignment` | 12257 | Run the selected bay assignment workflow for the browser application. | `match`, `openManageItemsPanel`, `openSdiPanel` |
| `assignmentById` | 12266 | Run the assignment by ID workflow for the browser application. | `openSdiPanel`, `runAssignmentAction` |
| `match` | 12274 | Run the match workflow for the browser application. | `bayTypeSections`, `rackSortNumber`, `scanEntryDeliveryDateHint`, `translateDynamicUiText`, `translatedUiValue` |
| `bayAssignmentRows` | 12286 | Run the bay assignment rows workflow for the browser application. | `renderManageItemsPanel`, `selectedManageItem` |
| `selectedManageItem` | 12303 | Run the selected manage item workflow for the browser application. | `clearManagedItem`, `moveManagedItem`, `renderManageItemsPanel`, `updateBayScanModeUi`, `useManagedBayForScanner` |
| `bayOptionGroups` | 12314 | Run the bay option groups workflow for the browser application. | `renderManageItemsPanel` |
| `renderManageItemsPanel` | 12332 | Render the render manage items panel workflow using the existing shared UI state. | `clearManagedItem`, `moveManagedItem`, `openManageItemsPanel`, `updateBayScanModeUi` |
| `openManageItemsPanel` | 12406 | Open the open manage items panel workflow using the existing shared UI state. | `runAssignmentAction`, `runBayAction` |
| `closeManageItemsPanel` | 12422 | Close the close manage items panel workflow using the existing shared UI state. | `updateBayScanModeUi`, `useManagedBayForScanner` |
| `moveManagedItem` | 12433 | Run the move managed item workflow for the browser application. | `updateBayScanModeUi` |
| `clearManagedItem` | 12456 | Remove the clear managed item workflow using the existing shared UI state. | `updateBayScanModeUi` |
| `useManagedBayForScanner` | 12485 | Run the use managed bay for scanner workflow for the browser application. | `updateBayScanModeUi` |
| `bayEditorGroups` | 12506 | Run the bay editor groups workflow for the browser application. | `bayEditorSelectedGroupObject`, `renderBayEditorPanel` |
| `bayEditorSelectedGroupObject` | 12515 | Run the bay editor selected group object workflow for the browser application. | `addBaysToEditorGroup`, `deleteBayEditorGroup`, `renderBayEditorPanel`, `saveBayEditorGroup` |
| `bayEditorPolicyForGroup` | 12526 | Run the bay editor policy for group workflow for the browser application. | `renderBayEditorPanel` |
| `policies` | 12532 | Run the policies workflow for the browser application. | — |
| `bayEditorStatusFromPolicy` | 12543 | Run the bay editor status from policy workflow for the browser application. | `saveBayEditorGroup`, `value` |
| `renderBayEditorPanel` | 12554 | Render the render bay editor panel workflow using the existing shared UI state. | `openBayEditorPanel`, `refreshBayEditorAfter`, `saveBayEditorGroup`, `updateBayScanModeUi` |
| `bayEditorNewGroupFormMarkup` | 12631 | Run the bay editor new group form markup workflow for the browser application. | `renderBayEditorPanel` |
| `bayEditorBayRowMarkup` | 12659 | Run the bay editor bay row markup workflow for the browser application. | `renderBayEditorPanel` |
| `openBayEditorPanel` | 12690 | Open the open bay editor panel workflow using the existing shared UI state. | `runBayAction`, `updateBayScanModeUi` |
| `closeBayEditorPanel` | 12704 | Close the close bay editor panel workflow using the existing shared UI state. | `updateBayScanModeUi` |
| `refreshBayEditorAfter` | 12715 | Load the refresh bay editor after workflow using the existing shared UI state. | `addBaysToEditorGroup`, `createBayEditorGroup`, `deleteBayEditorBay`, `deleteBayEditorGroup`, `value` |
| `saveBayEditorGroup` | 12726 | Run the save bay editor group workflow for the browser application. | — |
| `createBayEditorGroup` | 12766 | Create the create bay editor group workflow using the existing shared UI state. | — |
| `addBaysToEditorGroup` | 12788 | Create the add bays to editor group workflow using the existing shared UI state. | — |
| `deleteBayEditorGroup` | 12809 | Remove the delete bay editor group workflow using the existing shared UI state. | — |
| `saveBayEditorBay` | 12833 | Run the save bay editor bay workflow for the browser application. | `updateBayScanModeUi` |
| `value` | 12842 | Run the value workflow for the browser application. | — |
| `deleteBayEditorBay` | 12870 | Remove the delete bay editor bay workflow using the existing shared UI state. | `updateBayScanModeUi` |
| `openBayAllScansModal` | 12891 | Open the open bay all scans modal workflow using the existing shared UI state. | `showIndianTrailPlacementPrompt`, `updateBayScanModeUi`, `wireEvents` |
| `populateSdiBayOptions` | 12928 | Populate the SDI bay selector from the live Bay Map while retaining a valid preferred bay. | `openSdiPanel` |
| `renderSdiLookupResults` | 12947 | Render predictive SDI job/order choices beneath the shared lookup field. | `loadSdiWorkspace` |
| `sdiSelectionType` | 12969 | Read the currently selected Rush or Remake action from the SDI form. | `ids`, `renderSdiItemSelection`, `updateSdiSelectionSummary` |
| `selectSdiMissingItems` | 12978 | Restore the safe SDI default by selecting only items that are still missing from a physical bay. | `ids` |
| `selectedSdiItems` | 12992 | Return the loaded SDI items selected by their stable destination line-item IDs. | `ids`, `updateSdiSelectionSummary` |
| `updateSdiSelectionSummary` | 13001 | Keep the SDI action card synchronized with exact item selection and handling type. | `ids`, `openSdiPanel`, `renderSdiItemSelection` |
| `renderSdiItemSelection` | 13029 | Render exact SDI item choices with physical-bay fulfillment and missing status. | `ids`, `loadSdiWorkspace`, `selectSdiMissingItems` |
| `renderSdiCurrentList` | 13075 | Render current Rush/Remake marks grouped by job with item-level clearing controls. | `ids`, `loadSdiWorkspace` |
| `groups` | 13077 | No inline documentation found. | — |
| `loadSdiWorkspace` | 13137 | Load the predictive, item-level SDI workspace from live Indian Trail bay state. | `chooseSdiLookup`, `ids`, `openSdiPanel`, `submitSdi` |
| `chooseSdiLookup` | 13160 | Apply one predictive SDI lookup choice and load its exact item workspace. | `ids` |
| `openSdiPanel` | 13171 | Open the shared SDI workspace from a selected bay assignment or as a blank predictive search. | `runAssignmentAction`, `runBayAction`, `updateBayScanModeUi` |
| `closeSdiPanel` | 13206 | Close the SDI workspace without changing any Rush, Remake, or bay data. | `submitSdi`, `updateBayScanModeUi` |
| `submitSdi` | 13220 | Submit one exact-item or safe job-level Rush/Remake mark or clear action through the existing Bay Map API. | `ids` |
| `runBayAction` | 13288 | Run the run bay action workflow for the browser application. | `ids`, `updateBayScanModeUi` |
| `renderBayLayoutSelect` | 13366 | Render the render bay layout select workflow using the existing shared UI state. | `addBaysFromForm`, `addSpacerBay`, `applyBayLayoutSnapshot`, `deleteSelectedBay`, `deleteSelectedBayGroup`, `moveBayToGroup`, `openBayLayoutManager`, `selectBay` |
| `populateBayLayoutForm` | 13380 | Run the populate bay layout form workflow for the browser application. | `addBaysFromForm`, `addSpacerBay`, `applyBayLayoutSnapshot`, `deleteSelectedBay`, `deleteSelectedBayGroup`, `ids`, `moveBayToGroup`, `openBayLayoutManager` (+1 more) |
| `openBayLayoutManager` | 13398 | Open the open bay layout manager workflow using the existing shared UI state. | `runBayAction` |
| `closeBayLayoutManager` | 13418 | Close the close bay layout manager workflow using the existing shared UI state. | `ids` |
| `holdBaySectionDraft` | 13436 | Run the hold bay section draft workflow for the browser application. | `ids` |
| `holdAllBaySections` | 13453 | Run the hold all bay sections workflow for the browser application. | `ids` |
| `applyBayLayoutDraft` | 13473 | Update the apply bay layout draft workflow using the existing shared UI state. | `runBayLayoutHistory` |
| `confirmBayLayoutDraft` | 13484 | Run the confirm bay layout draft workflow for the browser application. | `ids` |
| `cancelBayLayoutDraft` | 13519 | Run the cancel bay layout draft workflow for the browser application. | `ids` |
| `saveBayLayoutForm` | 13536 | Run the save bay layout form workflow for the browser application. | `ids` |
| `bayLayoutSnapshot` | 13563 | Run the bay layout snapshot workflow for the browser application. | `addSpacerBay`, `moveBayToGroup` |
| `applyBayLayoutSnapshot` | 13583 | Update the apply bay layout snapshot workflow using the existing shared UI state. | `runBayLayoutHistory` |
| `pushBayLayoutHistory` | 13600 | Run the push bay layout history workflow for the browser application. | `addSpacerBay`, `moveBayToGroup` |
| `runBayLayoutHistory` | 13611 | Run the run bay layout history workflow for the browser application. | `ids` |
| `moveBayToGroup` | 13635 | Run the move bay to group workflow for the browser application. | `ids` |
| `addBaysFromForm` | 13671 | Create the add bays from form workflow using the existing shared UI state. | — |
| `addSpacerBay` | 13695 | Create the add spacer bay workflow using the existing shared UI state. | — |
| `deleteSelectedBay` | 13733 | Remove the delete selected bay workflow using the existing shared UI state. | `ids` |
| `deleteSelectedBayGroup` | 13759 | Remove the delete selected bay group workflow using the existing shared UI state. | — |
| `openPrintPackage` | 13785 | Open the open print package workflow using the existing shared UI state. | — |
| `runAssignmentAction` | 13800 | Run the run assignment action workflow for the browser application. | `ids` |
| `selectedPrintStageInputs` | 13827 | Run the selected print stage inputs workflow for the browser application. | `selectedPrintListIds`, `updatePrintStageSelectState`, `wireEvents` |
| `selectedPrintListIds` | 13836 | Run the selected print list IDs workflow for the browser application. | `renderPrintGlassTypes`, `submitPrintOptions` |
| `updatePrintStageSelectState` | 13845 | Update the update print stage select state workflow using the existing shared UI state. | `renderPrintOptionStages`, `wireEvents` |
| `printGlassCategory` | 13863 | Run the print glass category workflow for the browser application. | `addEntry` |
| `printGlassCategorySort` | 13878 | Run the print glass category sort workflow for the browser application. | `addEntry` |
| `selectedPrintGlassInputs` | 13887 | Run the selected print glass inputs workflow for the browser application. | `checkedForEntry`, `renderPrintGlassTypes`, `updatePrintGlassSelectState` |
| `updatePrintGlassSelectState` | 13896 | Update the update print glass select state workflow using the existing shared UI state. | `checkedForEntry` |
| `ensurePrintListDetails` | 13923 | Run the ensure print list details workflow for the browser application. | `renderPrintGlassTypes` |
| `printListIsFullCoverage` | 13956 | Run the print list is full coverage workflow for the browser application. | — |
| `printCountSourceLists` | 13966 | Run the print count source lists workflow for the browser application. | `printGlassEntriesForLists`, `renderPrintGlassTypes` |
| `printItemsForCountList` | 13985 | Run the print items for count list workflow for the browser application. | `addEntry` |
| `printGlassEntriesForLists` | 14002 | Run the print glass entries for lists workflow for the browser application. | `availableGlassTypesForLists`, `renderPrintGlassTypes` |
| `addEntry` | 14011 | Create the add entry workflow using the existing shared UI state. | — |
| `availableGlassTypesForLists` | 14057 | Run the available glass types for lists workflow for the browser application. | — |
| `ensurePrintGlassFieldWrapper` | 14066 | Run the ensure print glass field wrapper workflow for the browser application. | `renderPrintGlassTypes` |
| `renderPrintGlassTypes` | 14091 | Render the render print glass types workflow using the existing shared UI state. | `renderPrintOptionStages`, `wireEvents` |
| `checkedForEntry` | 14137 | Run the checked for entry workflow for the browser application. | — |
| `printStageOptionLabel` | 14283 | Run the print stage option label workflow for the browser application. | `renderPrintOptionStages` |
| `renderPrintOptionStages` | 14300 | Render the render print option stages workflow using the existing shared UI state. | `openPrintOptions`, `wireEvents` |
| `openPrintOptions` | 14339 | Open the open print options workflow using the existing shared UI state. | `ids`, `wireEvents` |
| `closePrintOptions` | 14370 | Close the close print options workflow using the existing shared UI state. | `submitPrintOptions`, `wireEvents` |
| `submitPrintOptions` | 14381 | Process the submit print options workflow using the existing shared UI state. | `wireEvents` |
| `importTempDeliveryFolder` | 14422 | Run the import temp delivery folder workflow for the browser application. | `wireEvents` |
| `refreshAdminPage` | 14480 | Load the refresh admin page workflow using the existing shared UI state. | `createUserFromForm`, `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteSelectedDeliveryList`, `importTempDeliveryFolder`, `refreshAdminUsersUi`, `resetAdminScansForDate`, `saveRolePermissions` (+1 more) |
| `adminDeliveryListCutoffDate` | 14532 | Run the admin delivery list cutoff date workflow for the browser application. | `deliveryListIsInAdminWindow` |
| `deliveryListIsInAdminWindow` | 14544 | Run the delivery list is in admin window workflow for the browser application. | `adminDeliveryListHiddenOlderRows`, `deliveryListAdminRows` |
| `adminDeliveryListHiddenOlderRows` | 14557 | Run the admin delivery list hidden older rows workflow for the browser application. | `deliveryListAdminRows` |
| `adminDeliveryListWindowLabel` | 14566 | Run the admin delivery list window label workflow for the browser application. | `deliveryListAdminRows` |
| `adminDeliveryListModalResultsHtml` | 14582 | Run the admin delivery list modal results HTML workflow for the browser application. | `adminModalContent`, `renderAdminDeliveryListModalResults` |
| `renderAdminDeliveryListModalResults` | 14598 | Render the render admin delivery list modal results workflow using the existing shared UI state. | `ids`, `refreshAdminDeliveryListModal`, `wireEvents` |
| `refreshAdminDeliveryListModal` | 14611 | Load the refresh admin delivery list modal workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `resetAdminScansForDate` |
| `deliveryListAdminRows` | 14628 | Run the delivery list admin rows workflow for the browser application. | `adminDeliveryListModalResultsHtml` |
| `searchAdminDeliveryLists` | 14781 | Run the search admin delivery lists workflow for the browser application. | `refreshAdminDeliveryListModal`, `wireEvents` |
| `activeRecentImports` | 14807 | Run the active recent imports workflow for the browser application. | `renderAdminDeliveryLists`, `renderImportHistory` |
| `renderAdminDeliveryLists` | 14877 | Render the render admin delivery lists workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteSelectedDeliveryList`, `resetAdminScansForDate`, `resetAdminScansForList` |
| `openAdminModal` | 14887 | Open the open admin modal workflow using the existing shared UI state. | `createUserFromForm`, `deleteAdminDeliveryListById`, `ids`, `openBayAllScansModal`, `openManualEditForList`, `openRackForm`, `openRackSetForm`, `showOutboundRackTransitPrompt` (+1 more) |
| `closeAdminModal` | 14936 | Close the close admin modal workflow using the existing shared UI state. | `createRackSet`, `saveRackDefinition`, `updateBayScanModeUi` |
| `adminModalContent` | 14967 | Run the admin modal content workflow for the browser application. | `deleteRackDefinition`, `deleteRackSet`, `ids`, `openAdminModal`, `openRackManagerRackInlineEdit`, `openRackManagerSetEdit`, `racks`, `refreshAdminUsersUi` (+3 more) |
| `lookupTypeMeta` | 15092 | Run the lookup type meta workflow for the browser application. | — |
| `lookupBucketForType` | 15123 | Return the state bucket name used by one Lookup Manager type. | `lookupItemsForType` |
| `lookupItemsForType` | 15135 | Return all lookup rows for one type from the shared Lookup Manager state. | `lookupManagerModalHtml`, `useLookupInEditor` |
| `lookupEditorMeta` | 15145 | Return the instructional copy and examples for one Lookup Manager type. | `lookupListHtml`, `lookupManagerModalHtml`, `syncLookupManagerFormGuidance` |
| `lookupListHtml` | 15188 | Render one searchable Lookup Manager library for the active type. | `lookupManagerModalHtml` |
| `lookupManagerModalHtml` | 15246 | Render the redesigned Lookup Manager workspace. | `adminModalContent`, `renderLookupManagerModal` |
| `syncLookupManagerFormGuidance` | 15352 | Synchronize the contextual Lookup Manager fields and live preview. | `clearLookupManagerForm`, `openAdminModal`, `renderLookupManagerModal`, `useLookupInEditor`, `wireEvents` |
| `renderLookupManagerModal` | 15373 | Re-render the open Lookup Manager while preserving its single active type and search state. | `ids`, `saveManualEditLookup`, `useLookupInEditor` |
| `useLookupInEditor` | 15386 | Load one existing lookup row into the guided editor. | `ids` |
| `clearLookupManagerForm` | 15411 | Clear the current Lookup Manager editor without changing saved lookup data. | `ids` |
| `filterLookupManagerLibrary` | 15425 | Filter the visible Lookup Manager library without rebuilding the editor form. | `openAdminModal`, `renderLookupManagerModal`, `wireEvents` |
| `saveManualEditLookup` | 15460 | Save one manual-edit lookup value through the existing Lookup Manager workflow. | `wireEvents` |
| `rackManagerRackEditHtml` | 15492 | Run the rack manager rack edit HTML workflow for the browser application. | `rackManagerModalHtml` |
| `rack` | 15501 | Run the rack workflow for the browser application. | `createRackSet`, `pad` |
| `rackManagerSetEditHtml` | 15542 | Run the rack manager set edit HTML workflow for the browser application. | `rackManagerModalHtml` |
| `racks` | 15551 | Run the racks workflow for the browser application. | — |
| `focusRackManagerRackEdit` | 15593 | Run the focus rack manager rack edit workflow for the browser application. | `ids` |
| `openRackManagerRackInlineEdit` | 15602 | Open the open rack manager rack inline edit workflow using the existing shared UI state. | `focusRackManagerRackEdit` |
| `saveRackInlineEdit` | 15622 | Run the save rack inline edit workflow for the browser application. | `wireEvents` |
| `openRackManagerSetEdit` | 15657 | Open the open rack manager set edit workflow using the existing shared UI state. | `ids` |
| `saveRackSetQuickEdit` | 15676 | Run the save rack set quick edit workflow for the browser application. | `wireEvents` |
| `racks` | 15685 | Run the racks workflow for the browser application. | — |
| `rackManagerModalHtml` | 15730 | Run the rack manager modal HTML workflow for the browser application. | `adminModalContent` |
| `rackFormModalHtml` | 15829 | Run the rack form modal HTML workflow for the browser application. | `adminModalContent` |
| `rackSetFormModalHtml` | 15852 | Run the rack set form modal HTML workflow for the browser application. | `adminModalContent` |
| `permissionLabel` | 15870 | Run the permission label workflow for the browser application. | `rolePermissionCategoryHtml` |
| `permissionDescription` | 15924 | Return the short user-facing explanation for one permission. | `rolePermissionCategoryHtml` |
| `categorizedPermissions` | 15991 | Run the categorized permissions workflow for the browser application. | `rolePermissionsModalHtml` |
| `rolePermissionCategoryKey` | 16020 | Run the role permission category key workflow for the browser application. | `ids`, `rememberRolePermissionUiState`, `rolePermissionCategoryHtml` |
| `resetRolePermissionUiSession` | 16029 | Run the reset role permission UI session workflow for the browser application. | `closeAdminModal`, `openAdminModal` |
| `rememberRolePermissionUiState` | 16040 | Run the remember role permission UI state workflow for the browser application. | `saveRolePermissions` |
| `restoreRolePermissionUiScroll` | 16073 | Run the restore role permission UI scroll workflow for the browser application. | `saveRolePermissions` |
| `rolePermissionCategoryHtml` | 16086 | Run the role permission category HTML workflow for the browser application. | `rolePermissionsModalHtml` |
| `rolePermissionCountText` | 16130 | Run the role permission count text workflow for the browser application. | `rolePermissionsModalHtml` |
| `rolePermissionsModalHtml` | 16142 | Run the role permissions modal HTML workflow for the browser application. | `adminModalContent` |
| `permissionSummaryFromPermissions` | 16200 | Run the permission summary from permissions workflow for the browser application. | `permissionSummaryForUser`, `rolePermissionsModalHtml` |
| `permissionSummaryForUser` | 16215 | Run the permission summary for user workflow for the browser application. | `renderAdminUsersTable` |
| `saveRolePermissions` | 16239 | Run the save role permissions workflow for the browser application. | `ids` |
| `manualEditDeliveryDateForList` | 16281 | Run the manual edit delivery date for list workflow for the browser application. | `manualEditStageListsForCurrentDelivery` |
| `manualEditStageListsForCurrentDelivery` | 16292 | Run the manual edit stage lists for current delivery workflow for the browser application. | `manualEditModalHtml` |
| `manualEditStageSummary` | 16306 | Run the manual edit stage summary workflow for the browser application. | `manualEditModalHtml`, `runManualEditModalSearch` |
| `manualEditModalHtml` | 16321 | Run the manual edit modal HTML workflow for the browser application. | `adminModalContent` |
| `ensureManualEditLookupsLoaded` | 16369 | Run the ensure manual edit lookups loaded workflow for the browser application. | `ids`, `openManualEditForList` |
| `openManualEditForList` | 16408 | Open the open manual edit for list workflow using the existing shared UI state. | `ids` |
| `fetchManualEditResults` | 16424 | Load the fetch manual edit results workflow using the existing shared UI state. | `runManualEditModalSearch`, `runManualEditSearch` |
| `runManualEditModalSearch` | 16437 | Run the run manual edit modal search workflow for the browser application. | `deleteManualLineItem`, `ids`, `openManualEditForList`, `saveManualLineItem`, `wireEvents` |
| `renderManualEditStageOptions` | 16481 | Render the render manual edit stage options workflow using the existing shared UI state. | `refreshAdminPage` |
| `renderImportHistory` | 16499 | Render the render import history workflow using the existing shared UI state. | `refreshAdminPage` |
| `importHistoryRows` | 16518 | Run the import history rows workflow for the browser application. | `renderAdminDeliveryLists`, `renderImportHistory` |
| `stageNameForRow` | 16543 | Run the stage name for row workflow for the browser application. | `addRow`, `isStagingRow`, `stageCategoryForImportRow`, `stageRowKey`, `stageSortForRow` |
| `isStagingRow` | 16551 | Run the is staging row workflow for the browser application. | `addRow` |
| `stageCategoryForImportRow` | 16558 | Run the stage category for import row workflow for the browser application. | `addRow` |
| `updatedQtyForRow` | 16569 | Update the updated qty for row workflow using the existing shared UI state. | `addRow`, `changedQtyForRow`, `isNewStageRow`, `originalQtyForRow`, `stageRowPriority` |
| `changedQtyForRow` | 16577 | Run the changed qty for row workflow for the browser application. | `addRow`, `stageRowPriority` |
| `originalQtyForRow` | 16591 | Run the original qty for row workflow for the browser application. | `addRow`, `isNewStageRow`, `stageRowPriority` |
| `isNewStageRow` | 16624 | Run the is new stage row workflow for the browser application. | `addRow`, `stageRowPriority` |
| `stageRowsForEntry` | 16640 | Run the stage rows for entry workflow for the browser application. | `addRow` |
| `hasStageChanges` | 16665 | Run the has stage changes workflow for the browser application. | `addRow` |
| `stageRowKey` | 16676 | Run the stage row key workflow for the browser application. | `addRow`, `collapseDuplicateStageRows` |
| `stageRowPriority` | 16690 | Run the stage row priority workflow for the browser application. | `collapseDuplicateStageRows` |
| `collapseDuplicateStageRows` | 16712 | Run the collapse duplicate stage rows workflow for the browser application. | `addRow` |
| `stageSortForRow` | 16735 | Run the stage sort for row workflow for the browser application. | `addRow` |
| `allStageRowsForGroup` | 16746 | Run the all stage rows for group workflow for the browser application. | `addRow` |
| `addRow` | 16754 | Create the add row workflow using the existing shared UI state. | — |
| `renderAdminDeleteControls` | 17013 | Render the render admin delete controls workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteSelectedDeliveryList`, `refreshAdminPage`, `resetAdminScansForDate`, `wireEvents` |
| `renderAdminResetControls` | 17034 | Render the render admin reset controls workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `refreshAdminPage`, `resetAdminScansForDate` |
| `resetSelectedAdminScans` | 17048 | Run the reset selected admin scans workflow for the browser application. | `wireEvents` |
| `resetAdminScansForList` | 17058 | Run the reset admin scans for list workflow for the browser application. | `ids`, `resetSelectedAdminScans` |
| `resetAdminScansForDate` | 17089 | Run the reset admin scans for date workflow for the browser application. | `ids` |
| `deleteAdminDeliveryDateByDate` | 17143 | Remove the delete admin delivery date by date workflow using the existing shared UI state. | `ids` |
| `deleteSelectedDeliveryList` | 17201 | Remove the delete selected delivery list workflow using the existing shared UI state. | `wireEvents` |
| `deleteAdminDeliveryListById` | 17280 | Remove the delete admin delivery list by ID workflow using the existing shared UI state. | `ids` |
| `userInitials` | 17330 | Run the user initials workflow for the browser application. | `applyPermissionUi`, `renderAdminUsersTable` |
| `userAccentClass` | 17348 | Run the user accent class workflow for the browser application. | `applyPermissionUi`, `renderAdminUsersTable` |
| `userActionButtonHtml` | 17365 | Run the user action button HTML workflow for the browser application. | `renderAdminUsersTable` |
| `generateTemporaryPassword` | 17387 | Run the generate temporary password workflow for the browser application. | `ids` |
| `refreshAdminUsersUi` | 17406 | Load the refresh admin users UI workflow using the existing shared UI state. | `ids` |
| `confirmWebAppAction` | 17421 | Run the confirm web app action workflow for the browser application. | `clearManagedItem`, `clearRack`, `clearRackItem`, `closeAdminModal`, `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteBayEditorBay`, `deleteBayEditorGroup` (+19 more) |
| `keyHandler` | 17443 | Run the key handler workflow for the browser application. | — |
| `typedConfirmationMatches` | 17481 | Run the typed confirmation matches workflow for the browser application. | `close`, `syncTypedConfirmation` |
| `syncTypedConfirmation` | 17488 | Run the sync typed confirmation workflow for the browser application. | `close` |
| `close` | 17498 | Close the close workflow using the existing shared UI state. | `notifyPrintComplete`, `submit` |
| `promptWebAppAction` | 17547 | Run the prompt web app action workflow for the browser application. | `addSpacerBay` |
| `close` | 17585 | Close the close workflow using the existing shared UI state. | `notifyPrintComplete`, `submit` |
| `submit` | 17595 | Process the submit workflow using the existing shared UI state. | — |
| `confirmDeactivateUser` | 17628 | Run the confirm deactivate user workflow for the browser application. | `ids` |
| `keyHandler` | 17639 | Run the key handler workflow for the browser application. | — |
| `close` | 17665 | Close the close workflow using the existing shared UI state. | `notifyPrintComplete`, `submit` |
| `renderAdminUsers` | 17700 | Render the render admin users workflow using the existing shared UI state. | `refreshAdminPage` |
| `renderAdminUsersTable` | 17722 | Render the render admin users table workflow using the existing shared UI state. | `adminModalContent`, `renderAdminUsers` |
| `renderAdminStations` | 17938 | Render the render admin stations workflow using the existing shared UI state. | `addStationFromInput`, `ids`, `refreshAdminPage`, `removeStation` |
| `renderAdminStationsList` | 17948 | Render the render admin stations list workflow using the existing shared UI state. | `adminModalContent`, `renderAdminStations` |
| `customerRouteValue` | 17966 | Run the customer route value workflow for the browser application. | `customerRouteAddressStatus`, `customerRouteDefaultAddress`, `customerRouteDisplay`, `customerRouteFormValues`, `customerRouteOptionList`, `customerRouteOptionsHtml`, `customerRouteRuleRowsHtml`, `renderCustomerRouteRules` (+3 more) |
| `customerRouteDisplay` | 17987 | Run the customer route display workflow for the browser application. | `customerRouteRuleRowsHtml` |
| `customerRouteDefaultAddress` | 18002 | Run the customer route default address workflow for the browser application. | `customerRouteAddress`, `customerRouteFormValues`, `saveCustomerRouteRuleRow`, `wireEvents` |
| `customerRouteAddress` | 18011 | Run the customer route address workflow for the browser application. | `customerRouteAddressStatus`, `customerRouteRuleRowsHtml`, `setCustomerRouteEditForm` |
| `customerRouteAddressStatus` | 18021 | Run the customer route address status workflow for the browser application. | `customerRouteRuleRowsHtml` |
| `customerRouteOptionList` | 18035 | Run the customer route option list workflow for the browser application. | `customerRouteOptionsHtml`, `renderCustomerRouteRules` |
| `customerRouteOptionsHtml` | 18049 | Run the customer route options HTML workflow for the browser application. | `customerRouteRuleRowsHtml`, `customerRouteRulesModalHtml` |
| `customerRouteRuleRowsHtml` | 18064 | Run the customer route rule rows HTML workflow for the browser application. | `customerRouteRulesModalHtml`, `renderCustomerRouteRules` |
| `customerRouteRulesModalHtml` | 18135 | Run the customer route rules modal HTML workflow for the browser application. | `adminModalContent`, `refreshCustomerRouteModal` |
| `setCustomerRouteEditForm` | 18190 | Update the set customer route edit form workflow using the existing shared UI state. | — |
| `renderCustomerRouteRules` | 18217 | Render the render customer route rules workflow using the existing shared UI state. | `refreshAdminPage`, `refreshCustomerRouteModal` |
| `refreshCustomerRouteModal` | 18268 | Load the refresh customer route modal workflow using the existing shared UI state. | `removeCustomerRouteRule`, `saveCustomerRouteRule`, `saveCustomerRouteRuleRow` |
| `renderBayScannerRuleOverview` | 18281 | Render the render bay scanner rule overview workflow using the existing shared UI state. | `refreshAdminPage`, `refreshBayScannerRules`, `removeBayScannerRule`, `saveBayBarcodeRule`, `saveBayManualRule` |
| `autoAssignTypeOptions` | 18297 | Run the auto assign type options workflow for the browser application. | `bayAutoAssignerModalHtml` |
| `renderBayAutoAssignOverview` | 18307 | Render the render bay auto assign overview workflow using the existing shared UI state. | `refreshAdminPage`, `refreshBayAutoAssigner`, `saveBayAutoAssignerSettings` |
| `bayAutoAssignerModalHtml` | 18322 | Run the bay auto assigner modal HTML workflow for the browser application. | `adminModalContent`, `refreshBayAutoAssigner`, `saveBayAutoAssignerSettings` |
| `refreshBayAutoAssigner` | 18386 | Load the refresh bay auto assigner workflow using the existing shared UI state. | — |
| `saveBayAutoAssignerSettings` | 18401 | Run the save bay auto assigner settings workflow for the browser application. | `wireEvents` |
| `bayScannerRulesModalHtml` | 18422 | Run the bay scanner rules modal HTML workflow for the browser application. | `adminModalContent`, `refreshBayScannerRules`, `removeBayScannerRule`, `saveBayBarcodeRule`, `saveBayManualRule` |
| `refreshBayScannerRules` | 18473 | Load the refresh bay scanner rules workflow using the existing shared UI state. | — |
| `saveBayManualRule` | 18488 | Run the save bay manual rule workflow for the browser application. | `wireEvents` |
| `saveBayBarcodeRule` | 18504 | Run the save bay barcode rule workflow for the browser application. | `wireEvents` |
| `removeBayScannerRule` | 18519 | Remove the remove bay scanner rule workflow using the existing shared UI state. | `ids` |
| `renderCustomerEmailOverview` | 18531 | Render the render customer email overview workflow using the existing shared UI state. | `refreshAdminPage`, `removeCustomerEmailCc`, `removeCustomerEmailContact`, `saveCustomerEmailCc`, `saveCustomerEmailContact`, `sendCustomerEmailTest` |
| `emailAddressListText` | 18571 | Run the email address list text workflow for the browser application. | `customerEmailRulesModalHtml`, `email`, `emailDraftPreviewHtml` |
| `emailStatusLabel` | 18580 | Run the email status label workflow for the browser application. | `customerEmailRulesModalHtml`, `emailDraftPreviewHtml` |
| `customerEmailRulesModalHtml` | 18593 | Run the customer email rules modal HTML workflow for the browser application. | `adminModalContent`, `refreshCustomerEmailSettings`, `removeCustomerEmailCc`, `removeCustomerEmailContact`, `saveCustomerEmailCc`, `saveCustomerEmailContact`, `sendCustomerEmailTest` |
| `emailDraftPreviewHtml` | 18731 | Run the email draft preview HTML workflow for the browser application. | `email` |
| `openEmailDraftPreview` | 18767 | Open the open email draft preview workflow using the existing shared UI state. | `ids` |
| `email` | 18773 | Run the email workflow for the browser application. | — |
| `closeEmailDraftPreview` | 18789 | Close the close email draft preview workflow using the existing shared UI state. | `email`, `ids` |
| `copyEmailDraftBody` | 18799 | Run the copy email draft body workflow for the browser application. | `ids` |
| `email` | 18805 | Run the email workflow for the browser application. | — |
| `mailtoParam` | 18816 | Run the mailto param workflow for the browser application. | `email` |
| `openEmailDraftMailto` | 18827 | Open the open email draft mailto workflow using the existing shared UI state. | `ids` |
| `email` | 18833 | Run the email workflow for the browser application. | — |
| `refreshCustomerEmailSettings` | 18850 | Load the refresh customer email settings workflow using the existing shared UI state. | `ids` |
| `startCustomerEmailEdit` | 18864 | Run the start customer email edit workflow for the browser application. | `ids` |
| `contact` | 18870 | Run the contact workflow for the browser application. | — |
| `saveCustomerEmailContact` | 18888 | Run the save customer email contact workflow for the browser application. | `wireEvents` |
| `saveCustomerEmailCc` | 18907 | Run the save customer email cc workflow for the browser application. | `wireEvents` |
| `sendCustomerEmailTest` | 18924 | Run the send customer email test workflow for the browser application. | `wireEvents` |
| `removeCustomerEmailContact` | 18948 | Remove the remove customer email contact workflow using the existing shared UI state. | `ids` |
| `removeCustomerEmailCc` | 18963 | Remove the remove customer email cc workflow using the existing shared UI state. | `ids` |
| `customerRouteFormValues` | 18978 | Run the customer route form values workflow for the browser application. | `saveCustomerRouteRule` |
| `saveCustomerRouteRule` | 19012 | Run the save customer route rule workflow for the browser application. | `wireEvents` |
| `saveCustomerRouteRuleRow` | 19045 | Run the save customer route rule row workflow for the browser application. | `ids` |
| `removeCustomerRouteRule` | 19086 | Remove the remove customer route rule workflow using the existing shared UI state. | `ids` |
| `renderActiveSessions` | 19116 | Render the render active sessions workflow using the existing shared UI state. | `refreshAdminPage` |
| `createUserFromForm` | 19128 | Create the create user from form workflow using the existing shared UI state. | `wireEvents` |
| `runManualEditSearch` | 19162 | Run the run manual edit search workflow for the browser application. | `deleteManualLineItem`, `saveManualLineItem`, `wireEvents` |
| `renderManualEditResults` | 19173 | Render the render manual edit results workflow using the existing shared UI state. | `runManualEditSearch` |
| `manualEditOptionHasValue` | 19185 | Run the manual edit option has value workflow for the browser application. | `manualEditIsCustomChoice` |
| `lookupOptions` | 19196 | Run the lookup options workflow for the browser application. | `manualEditProcessOptions`, `manualEditRouteOptions` |
| `manualEditIsCustomChoice` | 19213 | Run the manual edit is custom choice workflow for the browser application. | `manualEditChoiceFieldHtml`, `manualEditSelectOptions` |
| `manualEditSelectOptions` | 19224 | Run the manual edit select options workflow for the browser application. | `manualEditChoiceFieldHtml` |
| `manualEditChoiceFieldHtml` | 19257 | Run the manual edit choice field HTML workflow for the browser application. | `manualEditResultsHtml` |
| `manualEditChoiceHiddenInput` | 19308 | Run the manual edit choice hidden input workflow for the browser application. | `manualEditSetChoiceValue` |
| `manualEditSetChoiceValue` | 19319 | Run the manual edit set choice value workflow for the browser application. | `manualEditApplyChoiceSelect`, `manualEditApplyCustomInput`, `manualEditShowCustomChoice`, `manualEditShowSelectChoice` |
| `manualEditShowCustomChoice` | 19337 | Run the manual edit show custom choice workflow for the browser application. | `manualEditApplyChoiceSelect`, `manualEditSyncChoiceSelect` |
| `manualEditShowSelectChoice` | 19365 | Run the manual edit show select choice workflow for the browser application. | `manualEditClearCustomChoice`, `manualEditSyncChoiceSelect` |
| `manualEditApplyChoiceSelect` | 19394 | Run the manual edit apply choice select workflow for the browser application. | `wireEvents` |
| `manualEditApplyCustomInput` | 19413 | Run the manual edit apply custom input workflow for the browser application. | `wireEvents` |
| `manualEditClearCustomChoice` | 19427 | Run the manual edit clear custom choice workflow for the browser application. | `ids` |
| `manualEditSyncChoiceSelect` | 19441 | Run the manual edit sync choice select workflow for the browser application. | `wireEvents` |
| `manualEditCurrentLocationValue` | 19466 | Run the manual edit current location value workflow for the browser application. | `manualEditResultsHtml` |
| `manualEditLocationOptions` | 19475 | Run the manual edit location options workflow for the browser application. | `manualEditResultsHtml` |
| `manualEditRouteOptions` | 19529 | Run the manual edit route options workflow for the browser application. | `manualEditResultsHtml` |
| `manualEditProcessOptions` | 19546 | Run the manual edit process options workflow for the browser application. | `manualEditResultsHtml` |
| `manualEditProductOptions` | 19565 | Run the manual edit product options workflow for the browser application. | `manualEditResultsHtml` |
| `lookup` | 19581 | Run the lookup workflow for the browser application. | — |
| `manualEditSetRowError` | 19592 | Run the manual edit set row error workflow for the browser application. | `manualEditValidateRow` |
| `manualEditValidateRow` | 19614 | Run the manual edit validate row workflow for the browser application. | `saveManualLineItem`, `wireEvents` |
| `manualEditResultsHtml` | 19658 | Run the manual edit results HTML workflow for the browser application. | `renderManualEditResults`, `runManualEditModalSearch` |
| `saveManualLineItem` | 19796 | Run the save manual line item workflow for the browser application. | `ids` |
| `deleteManualLineItem` | 19836 | Remove the delete manual line item workflow using the existing shared UI state. | `ids` |
| `exportStaticCsv` | 19861 | Run the export static CSV workflow for the browser application. | — |
| `startPolling` | 19881 | Run the start polling workflow for the browser application. | `loadAuthenticatedApp` |
| `stopPolling` | 19906 | Run the stop polling workflow for the browser application. | `logout`, `startPolling` |
| `loadAuthenticatedApp` | 19916 | Load the load authenticated app workflow using the existing shared UI state. | `init`, `wireEvents` |
| `init` | 19934 | Run the init workflow for the browser application. | `ids` |
| `replayExpandableListAnimation` | 19961 | Run the replay expandable list animation workflow for the browser application. | `wireEvents` |
| `wireEvents` | 19982 | Connect the wire events workflow using the existing shared UI state. | `init`, `module startup` |
| `updateBayScanModeUi` | 20993 | Update the update bay scan mode UI workflow using the existing shared UI state. | — |
| `ids` | 21150 | Run the IDs workflow for the browser application. | — |

## PowerShell launcher function reference
| Function | Line | Purpose |
|---|---:|---|
| `Write-LauncherLog` | 17 | Record one launcher milestone in the console and persistent log. |
| `Test-PortAvailable` | 33 | Determine whether a local TCP port can be safely bound by the server. |
| `Get-DeliveryScannerHealth` | 56 | Identify a healthy Delivery List Scanner already listening on a port. |
| `Open-DeliveryScannerBrowser` | 75 | Open the verified local web address without making browser launch a startup dependency. |
| `Resolve-PythonRuntime` | 90 | Select a supported Python 3.10+ runtime for the local SQLite server. |
| `Import-MicrosoftGraphEmailConfiguration` | 143 | Load the locally encrypted Microsoft Graph app registration settings. |
| `Show-StartupFailure` | 190 | Keep startup errors visible and point the operator to durable diagnostics. |

## HTTP API route map
| Method | Route check | Kind | Server line |
|---|---|---|---:|
| GET | `/api/health` | exact | 1064 |
| GET | `/api/session` | exact | 1068 |
| GET | `/api/notifications/pending` | exact | 1073 |
| GET | `/api/delivery-lists` | exact | 1081 |
| GET | `/api/stations` | exact | 1088 |
| GET | `/api/exceptions` | exact | 1094 |
| GET | `/api/admin/summary` | exact | 1101 |
| GET | `/api/admin/users` | exact | 1107 |
| GET | `/api/admin/customer-route-rules` | exact | 1113 |
| GET | `/api/admin/customer-emails` | exact | 1130 |
| GET | `/api/admin/bay-scanner-rules` | exact | 1136 |
| GET | `/api/admin/bay-auto-assigner` | exact | 1142 |
| GET | `/api/admin/manual-edit-lookups` | exact | 1148 |
| GET | `/api/admin/permissions` | exact | 1154 |
| GET | `/api/admin/roles` | exact | 1160 |
| GET | `/api/admin/line-items/search` | exact | 1166 |
| GET | `/api/admin/sessions` | exact | 1174 |
| GET | `/api/admin/audit` | exact | 1180 |
| GET | `/api/search` | exact | 1187 |
| GET | `/api/reports/summary` | exact | 1195 |
| GET | `/api/indian-trail/summary` | exact | 1202 |
| GET | `/api/indian-trail/in-transit` | exact | 1209 |
| GET | `/api/indian-trail/bays` | exact | 1216 |
| GET | `/api/indian-trail/bay-job-details` | exact | 1222 |
| GET | `/api/indian-trail/sdi-workspace` | exact | 1229 |
| GET | `/api/indian-trail/layout` | exact | 1238 |
| GET | `/api/indian-trail/events` | exact | 1244 |
| GET | `/api/indian-trail/stale-bays` | exact | 1251 |
| GET | `/api/indian-trail/stale-bays/print` | exact | 1258 |
| GET | `/api/racks` | exact | 1269 |
| GET | `/api/racks/packing-list` | exact | 1275 |
| GET | `/api/delivery-lists/` | prefix | 1290 |
| GET | `/api/export.csv` | exact | 1303 |
| GET | `/api/export.xlsx` | exact | 1320 |
| GET | `/api/export/package.xlsx` | exact | 1337 |
| GET | `/api/print/package` | exact | 1355 |
| POST | `/api/login` | exact | 1380 |
| POST | `/api/password-reset/request` | exact | 1396 |
| POST | `/api/password-reset/confirm` | exact | 1400 |
| POST | `/api/logout` | exact | 1410 |
| POST | `/api/notifications/acknowledge` | exact | 1422 |
| POST | `/api/scans` | exact | 1435 |
| POST | `/api/reset` | exact | 1446 |
| POST | `/api/undo` | exact | 1464 |
| POST | `/api/redo` | exact | 1480 |
| POST | `/api/stations` | exact | 1496 |
| POST | `/api/stations/remove` | exact | 1502 |
| POST | `/api/stations/rename` | exact | 1508 |
| POST | `/api/import` | exact | 1514 |
| POST | `/api/import/folder` | exact | 1522 |
| POST | `/api/import/preview` | exact | 1530 |
| POST | `/api/exceptions/resolve` | exact | 1536 |
| POST | `/api/admin/users` | exact | 1543 |
| POST | `/api/admin/users/deactivate` | exact | 1550 |
| POST | `/api/admin/users/reactivate` | exact | 1557 |
| POST | `/api/admin/users/delete` | exact | 1564 |
| POST | `/api/admin/users/password` | exact | 1571 |
| POST | `/api/admin/users/roles` | exact | 1578 |
| POST | `/api/admin/roles/permissions` | exact | 1593 |
| POST | `/api/admin/line-item` | exact | 1600 |
| POST | `/api/admin/line-item/delete` | exact | 1607 |
| POST | `/api/admin/customer-route-rules` | exact | 1614 |
| POST | `/api/admin/customer-route-rules/remove` | exact | 1621 |
| POST | `/api/admin/customer-emails` | exact | 1628 |
| POST | `/api/admin/customer-emails/remove` | exact | 1635 |
| POST | `/api/admin/customer-emails/test` | exact | 1642 |
| POST | `/api/admin/customer-emails/cc` | exact | 1649 |
| POST | `/api/admin/customer-emails/cc/remove` | exact | 1656 |
| POST | `/api/admin/bay-scanner-rules/manual` | exact | 1663 |
| POST | `/api/admin/bay-scanner-rules/manual/remove` | exact | 1670 |
| POST | `/api/admin/bay-scanner-rules/barcode` | exact | 1677 |
| POST | `/api/admin/bay-scanner-rules/barcode/remove` | exact | 1684 |
| POST | `/api/admin/bay-auto-assigner` | exact | 1691 |
| POST | `/api/admin/manual-edit-lookups` | exact | 1698 |
| POST | `/api/admin/delete-list` | exact | 1705 |
| POST | `/api/admin/delete-date` | exact | 1714 |
| POST | `/api/indian-trail/receive` | exact | 1723 |
| POST | `/api/indian-trail/manual-assign` | exact | 1733 |
| POST | `/api/indian-trail/assign` | exact | 1740 |
| POST | `/api/indian-trail/move` | exact | 1747 |
| POST | `/api/indian-trail/clear` | exact | 1754 |
| POST | `/api/indian-trail/clear-assignment` | exact | 1761 |
| POST | `/api/indian-trail/restore-assignment` | exact | 1768 |
| POST | `/api/indian-trail/bay-status` | exact | 1775 |
| POST | `/api/indian-trail/scan-out` | exact | 1782 |
| POST | `/api/indian-trail/layout` | exact | 1789 |
| POST | `/api/indian-trail/bays/add` | exact | 1801 |
| POST | `/api/indian-trail/bays/delete` | exact | 1808 |
| POST | `/api/indian-trail/bays/delete-group` | exact | 1815 |
| POST | `/api/indian-trail/mark-sdi` | exact | 1822 |
| POST | `/api/indian-trail/remove-sdi` | exact | 1829 |
| POST | `/api/indian-trail/bay-check` | exact | 1836 |
| POST | `/api/indian-trail/stale-bays/snooze` | exact | 1843 |
| POST | `/api/racks/scan` | exact | 1850 |
| POST | `/api/racks/complete` | exact | 1860 |
| POST | `/api/racks/uncomplete` | exact | 1867 |
| POST | `/api/racks/return` | exact | 1874 |
| POST | `/api/racks/not-on-way` | exact | 1881 |
| POST | `/api/racks/assign-line-item` | exact | 1890 |
| POST | `/api/racks/move-item` | exact | 1897 |
| POST | `/api/racks/clear-item` | exact | 1904 |
| POST | `/api/racks/clear` | exact | 1911 |
| POST | `/api/racks` | exact | 1918 |
| POST | `/api/racks/create-set` | exact | 1925 |
| POST | `/api/racks/delete` | exact | 1932 |

## Database table map
| Azure SQL table | Schema line | Ownership note |
|---|---:|---|
| `delivery_lists` | 12 | Table delivery_lists: One generated stage/list header per delivery date and workflow stage; referenced by line items, scans, printing, and exports. |
| `line_items` | 28 | Table line_items: Physical delivery-list item copies for each stage; source_id links the same glass through its route. |
| `scan_events` | 57 | Table scan_events: Immutable scanner, undo, redo, import, update, and movement history used by recent/all-scans views and audits. |
| `stations` | 78 | Table stations: Configured scanner/stage station names available to users and imports. |
| `customer_route_rules` | 88 | Table customer_route_rules: Customer-name routing source of truth, applied after the CPU-Air Job Nr. override. |
| `system_metadata` | 103 | Table system_metadata: Version/signature markers for idempotent repairs and startup maintenance. |
| `admin_lookup_values` | 114 | Table admin_lookup_values: Editable product, route, process, and manual-edit lookup values. |
| `imports` | 133 | Table imports: Delivery-list import/update runs, hashes, quantities, and change summaries. |
| `exceptions` | 155 | Table exceptions: Scan safety exceptions and their resolution history. |
| `audit_events` | 173 | Table audit_events: Administrative and high-impact workflow audit trail. |
| `users` | 190 | Table users: Local application user accounts and active/inactive status. |
| `roles` | 206 | Table roles: Named application roles used to group permissions and stage access. |
| `permissions` | 217 | Table permissions: Canonical permission keys available to roles. |
| `role_permissions` | 227 | Table role_permissions: Many-to-many mapping between roles and permission keys. |
| `user_roles` | 238 | Table user_roles: Many-to-many mapping between users and assigned roles. |
| `sessions` | 249 | Table sessions: Authenticated user sessions and expiration metadata. |
| `password_reset_tokens` | 264 | Table password_reset_tokens: Short-lived local password-reset codes and completion state. |
| `bays` | 279 | Table bays: Indian Trail physical bay definitions, ordering, capacity type, status, and group layout. |
| `bay_assignments` | 304 | Table bay_assignments: Current and cleared item-to-bay assignments; preserves movement history fields. |
| `bay_events` | 323 | Table bay_events: Indian Trail receive, move, clear, SDI, and bay scanner event history. |
| `racks` | 340 | Table racks: Physical rack master records, destinations, status, rack sets, and transit timestamps. |
| `rack_items` | 361 | Table rack_items: Current and historical item-to-rack assignments used by staging/outbound workflows. |
| `bay_stale_snoozes` | 381 | Table bay_stale_snoozes: Per-job temporary suppression of stale-bay alerts. |
| `bay_manual_input_rules` | 393 | Table bay_manual_input_rules: Remembered manual bay choices derived from operator-entered order/job data. |
| `bay_scan_barcode_rules` | 410 | Table bay_scan_barcode_rules: Remembered barcode-to-bay rules for Indian Trail scanning. |
| `bay_auto_assign_settings` | 425 | Table bay_auto_assign_settings: Configurable size/type thresholds used by automatic bay assignment. |
| `customer_email_contacts` | 437 | Table customer_email_contacts: Per-customer manifest and ready-notification recipient configuration. |
| `customer_email_cc` | 452 | Table customer_email_cc: Global customer-email CC recipients. |
| `email_outbox` | 465 | Table email_outbox: Queued/sent/failed email records and rendered manifest payloads. |
| `app_notifications` | 487 | Table app_notifications: Multi-user application notifications such as Rush alerts. |
| `app_notification_receipts` | 505 | Table app_notification_receipts: Per-user notification acknowledgment state so one user cannot consume another user’s alert. |

## HTML anchor map
| ID | Element | Region | Line |
|---|---|---|---:|
| `#loginPanel` | `section` | Authentication and password reset | 17 |
| `#loginLanguageToggleBtn` | `button` | Authentication and password reset | 18 |
| `#loginForm` | `form` | Authentication and password reset | 36 |
| `#loginUsername` | `input` | Authentication and password reset | 46 |
| `#loginPassword` | `input` | Authentication and password reset | 50 |
| `#forgotPasswordBtn` | `button` | Authentication and password reset | 54 |
| `#loginError` | `p` | Authentication and password reset | 56 |
| `#passwordResetPanel` | `section` | Authentication and password reset | 59 |
| `#resetIdentityInput` | `input` | Authentication and password reset | 70 |
| `#requestResetCodeBtn` | `button` | Authentication and password reset | 72 |
| `#resetCodeInput` | `input` | Authentication and password reset | 75 |
| `#resetNewPasswordInput` | `input` | Authentication and password reset | 79 |
| `#confirmPasswordResetBtn` | `button` | Authentication and password reset | 82 |
| `#cancelPasswordResetBtn` | `button` | Authentication and password reset | 83 |
| `#passwordResetMessage` | `p` | Authentication and password reset | 85 |
| `#appSidebar` | `aside` | Collapsible desktop sidebar, mobile drawer, and global utility header | 92 |
| `#sidebarToggleBtn` | `button` | Collapsible desktop sidebar, mobile drawer, and global utility header | 97 |
| `#backendStatus` | `span` | Collapsible desktop sidebar, mobile drawer, and global utility header | 112 |
| `#signedInUser` | `span` | Collapsible desktop sidebar, mobile drawer, and global utility header | 118 |
| `#signedInRole` | `small` | Collapsible desktop sidebar, mobile drawer, and global utility header | 119 |
| `#userMenuDisplayName` | `strong` | Collapsible desktop sidebar, mobile drawer, and global utility header | 127 |
| `#userMenuDetails` | `span` | Collapsible desktop sidebar, mobile drawer, and global utility header | 128 |
| `#userMenuIdentity` | `small` | Collapsible desktop sidebar, mobile drawer, and global utility header | 129 |
| `#logoutBtn` | `button` | Collapsible desktop sidebar, mobile drawer, and global utility header | 132 |
| `#sidebarScrim` | `button` | Collapsible desktop sidebar, mobile drawer, and global utility header | 137 |
| `#mobileSidebarToggleBtn` | `button` | Collapsible desktop sidebar, mobile drawer, and global utility header | 140 |
| `#headerGlobalSearchInput` | `input` | Collapsible desktop sidebar, mobile drawer, and global utility header | 147 |
| `#headerGlobalSearchBtn` | `button` | Collapsible desktop sidebar, mobile drawer, and global utility header | 149 |
| `#headerGlobalSearchResults` | `div` | Collapsible desktop sidebar, mobile drawer, and global utility header | 150 |
| `#globalPrintExportBtn` | `button` | Collapsible desktop sidebar, mobile drawer, and global utility header | 155 |
| `#languageToggleBtn` | `button` | Collapsible desktop sidebar, mobile drawer, and global utility header | 156 |
| `#refreshPageBtn` | `button` | Collapsible desktop sidebar, mobile drawer, and global utility header | 160 |
| `#fullscreenToggleBtn` | `button` | Collapsible desktop sidebar, mobile drawer, and global utility header | 163 |
| `#homePage` | `section` | Home dashboard and delivery-list overview | 172 |
| `#homeWelcome` | `p` | Home dashboard and delivery-list overview | 176 |
| `#todayDateLabel` | `span` | Home dashboard and delivery-list overview | 190 |
| `#todayStageGrid` | `div` | Home dashboard and delivery-list overview | 192 |
| `#homeListCount` | `span` | Home dashboard and delivery-list overview | 197 |
| `#homeListSearch` | `input` | Home dashboard and delivery-list overview | 202 |
| `#homeStageFilter` | `select` | Home dashboard and delivery-list overview | 204 |
| `#homePagerTop` | `div` | Home dashboard and delivery-list overview | 215 |
| `#homeListGrid` | `div` | Home dashboard and delivery-list overview | 217 |
| `#homePageSize` | `select` | Home dashboard and delivery-list overview | 221 |
| `#homePager` | `div` | Home dashboard and delivery-list overview | 227 |
| `#overviewRangeSelect` | `select` | Home dashboard and delivery-list overview | 240 |
| `#homeStatisticsRangeText` | `span` | Home dashboard and delivery-list overview | 249 |
| `#homeStatsPdfBtn` | `button` | Home dashboard and delivery-list overview | 253 |
| `#overviewStats` | `div` | Home dashboard and delivery-list overview | 258 |
| `#homeMonthlyRemakes` | `div` | Home dashboard and delivery-list overview | 259 |
| `#homeStatsChart` | `div` | Home dashboard and delivery-list overview | 262 |
| `#homeUserCard` | `div` | Home dashboard and delivery-list overview | 263 |
| `#homeRecentLists` | `div` | Home dashboard and delivery-list overview | 270 |
| `#homeActivity` | `div` | Home dashboard and delivery-list overview | 277 |
| `#scanPage` | `section` | Main stage scanning workflow | 284 |
| `#pageTitle` | `h1` | Main stage scanning workflow | 287 |
| `#stageSubtitle` | `p` | Main stage scanning workflow | 288 |
| `#deliveryDateSelect` | `select` | Main stage scanning workflow | 293 |
| `#deliveryStageSelect` | `select` | Main stage scanning workflow | 297 |
| `#stationProfileDisplay` | `span` | Main stage scanning workflow | 301 |
| `#stationSelect` | `select` | Main stage scanning workflow | 302 |
| `#operatorInput` | `input` | Main stage scanning workflow | 304 |
| `#listPanel` | `section` | Main stage scanning workflow | 309 |
| `#countAll` | `span` | Main stage scanning workflow | 314 |
| `#countRemaining` | `span` | Main stage scanning workflow | 315 |
| `#countPartial` | `span` | Main stage scanning workflow | 316 |
| `#countComplete` | `span` | Main stage scanning workflow | 317 |
| `#countRemakes` | `span` | Main stage scanning workflow | 322 |
| `#countRushes` | `span` | Main stage scanning workflow | 323 |
| `#countUpdated` | `span` | Main stage scanning workflow | 324 |
| `#countErrors` | `span` | Main stage scanning workflow | 325 |
| `#countIndianTrailRoute` | `span` | Main stage scanning workflow | 330 |
| `#countCpuRoute` | `span` | Main stage scanning workflow | 331 |
| `#countDtcRoute` | `span` | Main stage scanning workflow | 332 |
| `#countGreenvilleRoute` | `span` | Main stage scanning workflow | 333 |
| `#glassFilterTabs` | `div` | Main stage scanning workflow | 338 |
| `#searchInput` | `input` | Main stage scanning workflow | 347 |
| `#scanPagerTop` | `div` | Main stage scanning workflow | 351 |
| `#pageSize` | `select` | Main stage scanning workflow | 355 |
| `#listRows` | `tbody` | Main stage scanning workflow | 379 |
| `#totalItemsText` | `span` | Main stage scanning workflow | 384 |
| `#scanPagerBottom` | `div` | Main stage scanning workflow | 385 |
| `#pageSizeBottom` | `select` | Main stage scanning workflow | 388 |
| `#scanPanel` | `aside` | Main stage scanning workflow | 397 |
| `#scanProgressBand` | `section` | Main stage scanning workflow | 398 |
| `#stageHeading` | `h2` | Main stage scanning workflow | 400 |
| `#scanProgressTrack` | `div` | Main stage scanning workflow | 403 |
| `#progressFill` | `span` | Main stage scanning workflow | 404 |
| `#progressText` | `strong` | Main stage scanning workflow | 409 |
| `#scanRackPanel` | `section` | Main stage scanning workflow | 414 |
| `#scanRackSelect` | `select` | Main stage scanning workflow | 418 |
| `#scanRackCompleteBtn` | `button` | Main stage scanning workflow | 421 |
| `#scanRackPrintBtn` | `button` | Main stage scanning workflow | 422 |
| `#scanRackStatus` | `p` | Main stage scanning workflow | 425 |
| `#outboundRackStatusPanel` | `section` | Main stage scanning workflow | 428 |
| `#outboundRackStatusSelect` | `select` | Main stage scanning workflow | 432 |
| `#outboundRackStatusSummary` | `div` | Main stage scanning workflow | 434 |
| `#scanBayOverridePanel` | `section` | Main stage scanning workflow | 441 |
| `#scanBayOverrideSelected` | `strong` | Main stage scanning workflow | 445 |
| `#scanBayOverrideMode` | `input` | Main stage scanning workflow | 449 |
| `#scanBayOverrideSelect` | `select` | Main stage scanning workflow | 455 |
| `#scanForm` | `form` | Main stage scanning workflow | 462 |
| `#undoBtn` | `button` | Main stage scanning workflow | 466 |
| `#redoBtn` | `button` | Main stage scanning workflow | 467 |
| `#scanInput` | `input` | Main stage scanning workflow | 472 |
| `#manualScanForm` | `form` | Main stage scanning workflow | 476 |
| `#manualOrderInput` | `input` | Main stage scanning workflow | 483 |
| `#manualItemInput` | `input` | Main stage scanning workflow | 487 |
| `#manualAssignPanel` | `section` | Main stage scanning workflow | 493 |
| `#manualAssignForm` | `form` | Main stage scanning workflow | 498 |
| `#manualAssignOrderInput` | `input` | Main stage scanning workflow | 501 |
| `#manualAssignItemInput` | `input` | Main stage scanning workflow | 505 |
| `#manualAssignQtyInput` | `input` | Main stage scanning workflow | 509 |
| `#manualAssignStatus` | `div` | Main stage scanning workflow | 513 |
| `#lastScanTime` | `span` | Main stage scanning workflow | 519 |
| `#viewAllRecent` | `button` | Main stage scanning workflow | 520 |
| `#lastCard` | `div` | Main stage scanning workflow | 522 |
| `#lastJob` | `strong` | Main stage scanning workflow | 524 |
| `#lastOrder` | `b` | Main stage scanning workflow | 526 |
| `#lastItem` | `b` | Main stage scanning workflow | 527 |
| `#lastQty` | `b` | Main stage scanning workflow | 528 |
| `#lastDims` | `b` | Main stage scanning workflow | 529 |
| `#lastCustomer` | `b` | Main stage scanning workflow | 530 |
| `#recentScanCountLabel` | `span` | Main stage scanning workflow | 537 |
| `#recentRows` | `tbody` | Main stage scanning workflow | 551 |
| `#mobileListCards` | `section` | Main stage scanning workflow | 557 |
| `#summaryPanel` | `section` | Main stage scanning workflow | 559 |
| `#remainingQty` | `strong` | Main stage scanning workflow | 562 |
| `#remainingPct` | `span` | Main stage scanning workflow | 562 |
| `#partialQty` | `strong` | Main stage scanning workflow | 566 |
| `#partialPct` | `span` | Main stage scanning workflow | 566 |
| `#completeQty` | `strong` | Main stage scanning workflow | 570 |
| `#completePct` | `span` | Main stage scanning workflow | 570 |
| `#errorQty` | `strong` | Main stage scanning workflow | 574 |
| `#racksPage` | `section` | Rack status and rack-management workflow | 583 |
| `#rackSummary` | `div` | Rack status and rack-management workflow | 590 |
| `#rackEditOpenBtn` | `button` | Rack status and rack-management workflow | 592 |
| `#rackGrid` | `section` | Rack status and rack-management workflow | 597 |
| `#bayMapPage` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 601 |
| `#indianTrailSummary` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 610 |
| `#bayFlowPanel` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 614 |
| `#bayLayoutManager` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 617 |
| `#bayLayoutCloseBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 624 |
| `#bayLayoutUndoBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 627 |
| `#bayLayoutRedoBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 628 |
| `#bayCollapseAllBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 629 |
| `#bayExpandAllBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 630 |
| `#bayLayoutCancelBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 631 |
| `#bayLayoutConfirmBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 632 |
| `#bayMapSearch` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 641 |
| `#bayCheckBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 643 |
| `#bayFilterDrawer` | `details` | Indian Trail bay map, receiving scanner, and bay modals | 644 |
| `#bayActiveFilterCount` | `strong` | Indian Trail bay map, receiving scanner, and bay modals | 648 |
| `#bayStatusFilter` | `select` | Indian Trail bay map, receiving scanner, and bay modals | 653 |
| `#bayGlassFilter` | `select` | Indian Trail bay map, receiving scanner, and bay modals | 667 |
| `#baySpecialFilter` | `select` | Indian Trail bay map, receiving scanner, and bay modals | 673 |
| `#bayActiveFilterBar` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 684 |
| `#bayActiveFilterSummary` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 685 |
| `#bayClearFiltersBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 686 |
| `#baySelectedText` | `span` | Indian Trail bay map, receiving scanner, and bay modals | 695 |
| `#bayMapCanvas` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 697 |
| `#bayActionButtons` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 702 |
| `#bayPanelRouteMini` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 717 |
| `#bayScanOutForm` | `form` | Indian Trail bay map, receiving scanner, and bay modals | 739 |
| `#bayScanModeToggle` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 752 |
| `#bayScanBayInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 759 |
| `#bayTargetClearBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 761 |
| `#bayScanOutInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 767 |
| `#bayUndoBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 769 |
| `#bayRedoBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 773 |
| `#bayManualOrderInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 788 |
| `#bayManualItemInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 792 |
| `#bayManualQtyInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 794 |
| `#bayManualSubmitBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 795 |
| `#bayScanOutStatus` | `span` | Indian Trail bay map, receiving scanner, and bay modals | 803 |
| `#bayAllScansBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 804 |
| `#bayLastCard` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 806 |
| `#bayLastBay` | `b` | Indian Trail bay map, receiving scanner, and bay modals | 810 |
| `#bayLastTitle` | `strong` | Indian Trail bay map, receiving scanner, and bay modals | 811 |
| `#bayLastAction` | `b` | Indian Trail bay map, receiving scanner, and bay modals | 814 |
| `#bayLastOrder` | `b` | Indian Trail bay map, receiving scanner, and bay modals | 815 |
| `#bayLastTime` | `b` | Indian Trail bay map, receiving scanner, and bay modals | 816 |
| `#bayLastMoveSelect` | `select` | Indian Trail bay map, receiving scanner, and bay modals | 817 |
| `#bayRecentScanCountLabel` | `span` | Indian Trail bay map, receiving scanner, and bay modals | 824 |
| `#bayScanOutRecent` | `tbody` | Indian Trail bay map, receiving scanner, and bay modals | 838 |
| `#bayCategoryFilters` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 860 |
| `#bayAllBaysList` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 861 |
| `#baySelectedBackdrop` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 865 |
| `#baySelectedModal` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 866 |
| `#baySelectedCloseBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 869 |
| `#baySelectedPanel` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 871 |
| `#staleBayBackdrop` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 873 |
| `#staleBayPanel` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 874 |
| `#staleBayCloseBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 877 |
| `#staleBayList` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 880 |
| `#staleBaySnoozeAllDays` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 882 |
| `#staleBaySnoozeAllBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 883 |
| `#staleBayPrintBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 884 |
| `#staleBayOkBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 885 |
| `#sdiBackdrop` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 888 |
| `#sdiPanel` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 889 |
| `#sdiCloseBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 895 |
| `#sdiForm` | `form` | Indian Trail bay map, receiving scanner, and bay modals | 897 |
| `#sdiOrderInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 905 |
| `#sdiLookupResults` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 907 |
| `#sdiBayInput` | `select` | Indian Trail bay map, receiving scanner, and bay modals | 911 |
| `#sdiItemSelection` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 920 |
| `#sdiSelectMissingBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 927 |
| `#sdiItemSelectionList` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 929 |
| `#sdiSelectionSummary` | `span` | Indian Trail bay map, receiving scanner, and bay modals | 936 |
| `#sdiTypeInput` | `select` | Indian Trail bay map, receiving scanner, and bay modals | 940 |
| `#sdiDeliveryDateInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 948 |
| `#sdiReasonInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 953 |
| `#sdiTruckExemptInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 956 |
| `#sdiClearBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 961 |
| `#sdiCurrentList` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 966 |
| `#manageItemsBackdrop` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 969 |
| `#manageItemsPanel` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 970 |
| `#manageItemsCloseBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 976 |
| `#manageItemsSearch` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 982 |
| `#manageItemsList` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 984 |
| `#manageItemsSelected` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 987 |
| `#manageItemsTargetBay` | `select` | Indian Trail bay map, receiving scanner, and bay modals | 991 |
| `#manageItemsReason` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 995 |
| `#manageItemsMoveBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 999 |
| `#manageItemsClearBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 1000 |
| `#manageItemsScannerBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 1001 |
| `#manageItemsSdiBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 1002 |
| `#manageItemsStatus` | `p` | Indian Trail bay map, receiving scanner, and bay modals | 1004 |
| `#bayEditorBackdrop` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 1008 |
| `#bayEditorPanel` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 1009 |
| `#bayEditorCloseBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 1015 |
| `#bayEditorNewGroupBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 1019 |
| `#bayEditorGroupList` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 1020 |
| `#bayEditorGroupForm` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 1024 |
| `#bayEditorBayList` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 1025 |
| `#adminPage` | `section` | Administration, users, rules, imports, and configuration | 1032 |
| `#adminLastUpdated` | `span` | Administration, users, rules, imports, and configuration | 1038 |
| `#adminSummary` | `div` | Administration, users, rules, imports, and configuration | 1041 |
| `#folderImportBtn` | `button` | Administration, users, rules, imports, and configuration | 1050 |
| `#tempFolderInput` | `input` | Administration, users, rules, imports, and configuration | 1056 |
| `#importFromDate` | `input` | Administration, users, rules, imports, and configuration | 1059 |
| `#importToDate` | `input` | Administration, users, rules, imports, and configuration | 1060 |
| `#importWindowResetBtn` | `button` | Administration, users, rules, imports, and configuration | 1061 |
| `#importPreviewBox` | `div` | Administration, users, rules, imports, and configuration | 1064 |
| `#adminDeliveryLists` | `div` | Administration, users, rules, imports, and configuration | 1065 |
| `#importHistory` | `div` | Administration, users, rules, imports, and configuration | 1066 |
| `#adminUsers` | `div` | Administration, users, rules, imports, and configuration | 1077 |
| `#customerRouteRules` | `div` | Administration, users, rules, imports, and configuration | 1086 |
| `#customerEmailOverview` | `div` | Administration, users, rules, imports, and configuration | 1094 |
| `#bayScannerRuleOverview` | `div` | Administration, users, rules, imports, and configuration | 1116 |
| `#bayAutoAssignOverview` | `div` | Administration, users, rules, imports, and configuration | 1127 |
| `#manualEditStageSelect` | `select` | Administration, users, rules, imports, and configuration | 1134 |
| `#manualEditSearch` | `input` | Administration, users, rules, imports, and configuration | 1137 |
| `#manualEditSearchBtn` | `button` | Administration, users, rules, imports, and configuration | 1138 |
| `#manualEditResults` | `div` | Administration, users, rules, imports, and configuration | 1139 |
| `#scannerName` | `strong` | Administration, users, rules, imports, and configuration | 1146 |
| `#printOptionsBackdrop` | `div` | Global print and export modal | 1162 |
| `#printOptionsPanel` | `section` | Global print and export modal | 1163 |
| `#printOptionsClose` | `button` | Global print and export modal | 1166 |
| `#printOptionsDate` | `select` | Global print and export modal | 1174 |
| `#printOptionsStages` | `div` | Global print and export modal | 1178 |
| `#printOptionsGlassType` | `div` | Global print and export modal | 1182 |
| `#printCustomerFilter` | `input` | Global print and export modal | 1186 |
| `#printOrderFilter` | `input` | Global print and export modal | 1190 |
| `#printUpdatedOnly` | `input` | Global print and export modal | 1193 |
| `#printRushOnly` | `input` | Global print and export modal | 1194 |
| `#printRemakeOnly` | `input` | Global print and export modal | 1195 |
| `#printOptionsSubmit` | `button` | Global print and export modal | 1197 |
| `#statsChartBackdrop` | `div` | Interactive statistics chart modal | 1201 |
| `#statsChartModal` | `section` | Interactive statistics chart modal | 1202 |
| `#statsChartModalTitle` | `h2` | Interactive statistics chart modal | 1206 |
| `#statsChartModalSubtitle` | `p` | Interactive statistics chart modal | 1207 |
| `#statsChartCloseBtn` | `button` | Interactive statistics chart modal | 1209 |
| `#statsChartRangeSelect` | `select` | Interactive statistics chart modal | 1214 |
| `#statsChartMetricSelect` | `select` | Interactive statistics chart modal | 1225 |
| `#statsChartViewSelect` | `select` | Interactive statistics chart modal | 1240 |
| `#statsChartSortSelect` | `select` | Interactive statistics chart modal | 1247 |
| `#statsChartLimitSelect` | `select` | Interactive statistics chart modal | 1256 |
| `#statsChartFilterInput` | `input` | Interactive statistics chart modal | 1265 |
| `#statsChartResetBtn` | `button` | Interactive statistics chart modal | 1267 |
| `#statsChartKpis` | `div` | Interactive statistics chart modal | 1269 |
| `#statsChartResultCount` | `span` | Interactive statistics chart modal | 1271 |
| `#statsChartModalCanvas` | `div` | Interactive statistics chart modal | 1273 |
| `#adminModalBackdrop` | `div` | Shared administration editor modal | 1277 |
| `#adminModal` | `section` | Shared administration editor modal | 1278 |
| `#adminModalTitle` | `h2` | Shared administration editor modal | 1280 |
| `#adminModalClose` | `button` | Shared administration editor modal | 1281 |
| `#adminModalBody` | `div` | Shared administration editor modal | 1283 |

## CSS ownership sections
| Section | Line |
|---|---:|
| Global design tokens and base element rules | 13 |
| Authentication and password-reset presentation | 92 |
| Responsive rules; preserve desktop ownership selectors above | 350 |
| Global application header, navigation, search, and profile menu | 379 |
| Home dashboard, statistics, and delivery-list finder | 739 |
| Administration panels, users, roles, imports, and route rules | 2375 |
| Main Scan page panel, barcode workflow, history, and tables | 2860 |
| Mobile navigation and compact delivery-list presentation | 3890 |
| Shared modal/backdrop foundations used by feature dialogs | 5045 |
| Rack overview, rack scanner, status, and packing-list controls | 7515 |
| Indian Trail Bay Map, receiving scanner, and bay-management UI | 15767 |

## Safe-edit rules
1. Search for an existing function, selector, route, or translation key before adding one.
2. Keep one business workflow in the store and one rendering/event path in the browser.
3. Add schema changes as idempotent migrations that can open existing floor databases safely.
4. Preserve `source_id` across generated stage copies; stage propagation, Rush/Remake, and route repairs depend on it.
5. Keep SQLite as the default until the Azure cutover is explicitly scheduled and validated.
6. Run `python tools/run_full_validation.py` before packaging a version.
