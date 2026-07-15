# Delivery List Scanner v062 Code Reference
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
- Python functions/methods: **554**
- Named JavaScript functions: **665**
- PowerShell launcher functions: **6**
- API route checks: **104**
- Azure SQL tables: **31**
- Stable HTML IDs: **273**
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
| `delivery_store.py` | `ClosingSQLiteConnection.__exit__` | 50 | Finish the closing SQLite connection context and release its resources. | `__exit__` |
| `delivery_store.py` | `now_iso` | 234 | Run the now iso workflow for the delivery-list scanner. | `acknowledge_notification`, `add_customer_route_rule`, `add_manual_edit_lookup`, `add_station`, `admin_summary`, `assign_bay`, `assign_line_items_to_bay`, `assign_transportation_from_outbound_override` (+64 more) |
| `delivery_store.py` | `parse_iso` | 243 | Parse iso for the delivery-list scanner workflow. | `bay_from_row`, `confirm_password_reset`, `get_stale_bay_orders`, `get_user_by_session` |
| `delivery_store.py` | `hash_password` | 252 | Run the hash password workflow for the delivery-list scanner. | `confirm_password_reset`, `create_user`, `seed_security_data`, `seed_user_if_missing`, `update_user_password` |
| `delivery_store.py` | `verify_password` | 267 | Run the verify password workflow for the delivery-list scanner. | `authenticate_user` |
| `delivery_store.py` | `session_token_hash` | 285 | Run the session token hash workflow for the delivery-list scanner. | `authenticate_user`, `confirm_password_reset`, `delete_session`, `get_user_by_session`, `request_password_reset` |
| `delivery_store.py` | `stage_access_for_roles` | 294 | Run the stage access for roles workflow for the delivery-list scanner. | `user_can_access_stage`, `user_from_row` |
| `delivery_store.py` | `user_can_access_stage` | 310 | Run the user can access stage workflow for the delivery-list scanner. | `_get_payload`, `get_delivery_lists`, `global_search`, `user_can_access_list` |
| `delivery_store.py` | `clean_barcode` | 325 | Run the clean barcode workflow for the delivery-list scanner. | `create_manual_bay_line_item`, `find_manual_bay_line_items`, `normalize_rack_code`, `parse_rack_barcode`, `recover_scan`, `scan_other_list_hint`, `scan_out_bay_item` |
| `delivery_store.py` | `normalize_rack_code` | 335 | Normalize rack code for the delivery-list scanner workflow. | `assign_line_item_to_rack`, `assign_transportation_from_outbound_override`, `clear_rack`, `complete_rack`, `delete_rack`, `get_rack_by_code`, `move_rack_item`, `not_on_way_rack` (+9 more) |
| `delivery_store.py` | `parse_rack_barcode` | 349 | Parse rack barcode for the delivery-list scanner workflow. | `record_scan`, `scan_rack_outbound` |
| `delivery_store.py` | `rack_barcode_text` | 374 | Run the rack barcode text workflow for the delivery-list scanner. | `rack_packing_list` |
| `delivery_store.py` | `digits_only` | 385 | Run the digits only workflow for the delivery-list scanner. | `create_manual_bay_line_item`, `find_manual_bay_line_items`, `get_print_package`, `rack_barcode_text`, `recover_scan`, `scan_out_bay_item`, `search_filters_match` |
| `delivery_store.py` | `normalized_match_text` | 394 | Run the normalized match text workflow for the delivery-list scanner. | `_indian_trail_in_transit_payload`, `bay_manual_text_is_known`, `canonical_route_designation`, `cpu_job_route_hint`, `find_sdi_line_items`, `fuzzy_contains`, `inferred_route`, `manual_assign_bay_item` (+5 more) |
| `delivery_store.py` | `simplified_match_text` | 403 | Run the simplified match text workflow for the delivery-list scanner. | `fuzzy_contains` |
| `delivery_store.py` | `is_valid_email` | 415 | Validate valid email for the delivery-list scanner workflow. | `create_user`, `queue_customer_email_test`, `queue_email_message`, `update_user_roles`, `upsert_customer_email_cc`, `upsert_customer_email_contact` |
| `delivery_store.py` | `fuzzy_contains` | 425 | Run the fuzzy contains workflow for the delivery-list scanner. | `customer_email_matches`, `default_customer_route`, `destination_address_for_rack`, `rack_packing_list`, `route_from_customer_rules` |
| `delivery_store.py` | `default_customer_route` | 442 | Run the default customer route workflow for the delivery-list scanner. | `inferred_route` |
| `delivery_store.py` | `canonical_barcode` | 458 | Run the canonical barcode workflow for the delivery-list scanner. | `clone_item_for_list`, `recover_scan`, `update_line_item` |
| `delivery_store.py` | `format_display_date` | 467 | Normalize display date for the delivery-list scanner workflow. | `build_delivery_lists`, `ensure_manual_bay_delivery_list`, `ensure_manual_route_list`, `queue_ready_email_if_customer_complete`, `rack_packing_list`, `scan_other_list_hint`, `send_customer_manifests_for_import` |
| `delivery_store.py` | `parse_dimension_number` | 479 | Parse dimension number for the delivery-list scanner workflow. | `suggested_bay` |
| `delivery_store.py` | `route_signal_text` | 504 | Run the route signal text workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `cpu_job_route_hint` | 530 | Return the only supported Job Nr. destination overrides. | `canonical_route_designation`, `job_number_route_hint` |
| `delivery_store.py` | `canonical_route_designation` | 559 | Resolve an operational route designation to the stored route code. | `add_customer_route_rule`, `normalize_route_column`, `resolve_item_route` |
| `delivery_store.py` | `normalize_route_column` | 603 | Return whether ROUTE was supplied and its canonical route code. | `clone_item_for_list`, `inferred_route`, `resolve_item_route`, `update_line_item` |
| `delivery_store.py` | `job_number_route_hint` | 612 | Return the supported CPU-Air/CPU-IT override from Job Nr. | `clone_item_for_list`, `inferred_route`, `resolve_item_route` |
| `delivery_store.py` | `inferred_route` | 617 | Run the inferred route workflow for the delivery-list scanner. | `clone_item_for_list`, `custom_route_codes`, `items_for_profile`, `route_category` |
| `delivery_store.py` | `route_category` | 647 | Run the route category workflow for the delivery-list scanner. | `custom_route_codes`, `destination_for_line_item`, `is_cpu_item`, `items_for_profile`, `preassign_bay_for_outbound`, `route_matches` |
| `delivery_store.py` | `custom_route_codes` | 665 | Run the custom route codes workflow for the delivery-list scanner. | `build_delivery_lists` |
| `delivery_store.py` | `route_stage_label` | 679 | Run the route stage label workflow for the delivery-list scanner. | `build_delivery_lists`, `destination_for_line_item` |
| `delivery_store.py` | `receiving_stage_destination` | 695 | Run the receiving stage destination workflow for the delivery-list scanner. | `_get_line_items`, `received_qty_for_rack_item` |
| `delivery_store.py` | `is_cpu_item` | 713 | Validate CPU item for the delivery-list scanner workflow. | `import_delivery_list`, `items_for_profile`, `preview_import`, `receive_indian_trail_scan`, `route_matches` |
| `delivery_store.py` | `normalized_bay_auto_assign_settings` | 722 | Run the normalized bay auto assign settings workflow for the delivery-list scanner. | `bay_auto_assign_settings_from_rows`, `suggested_bay`, `update_bay_auto_assign_settings` |
| `delivery_store.py` | `suggested_bay` | 745 | Run the suggested bay workflow for the delivery-list scanner. | `clone_item_for_list`, `preview_import`, `suggested_bay_from_settings` |
| `delivery_store.py` | `items_for_profile` | 768 | Run the items for profile workflow for the delivery-list scanner. | `build_delivery_lists` |
| `delivery_store.py` | `build_delivery_lists` | 788 | Build delivery lists for the delivery-list scanner workflow. | `import_delivery_folder`, `import_delivery_list`, `seed_demo_data` |
| `delivery_store.py` | `all_profile_list_ids` | 828 | Run the all profile list IDs workflow for the delivery-list scanner. | `import_delivery_list` |
| `delivery_store.py` | `parse_int_text` | 837 | Parse int text for the delivery-list scanner workflow. | `parse_aw_delivery_workbook`, `parse_delivery_csv`, `update_line_item` |
| `delivery_store.py` | `clean_excel_text` | 853 | Run the clean excel text workflow for the delivery-list scanner. | `read_xlsx_rows` |
| `delivery_store.py` | `format_delivery_date` | 865 | Normalize delivery date for the delivery-list scanner workflow. | `delivery_date_from_text` |
| `delivery_store.py` | `delivery_date_from_text` | 876 | Run the delivery date from text workflow for the delivery-list scanner. | `delivery_date_from_rows_or_name`, `delivery_date_from_source_header`, `import_delivery_folder`, `parse_delivery_csv` |
| `delivery_store.py` | `column_label` | 889 | Run the column label workflow for the delivery-list scanner. | `read_xlsx_rows` |
| `delivery_store.py` | `first_xlsx_sheet_path` | 899 | Run the first XLSX sheet path workflow for the delivery-list scanner. | `read_xlsx_rows` |
| `delivery_store.py` | `read_xlsx_rows` | 922 | Read XLSX rows for the delivery-list scanner workflow. | `delivery_date_from_source_header`, `parse_aw_delivery_workbook` |
| `delivery_store.py` | `delivery_date_from_rows_or_name` | 963 | Run the delivery date from rows or name workflow for the delivery-list scanner. | `delivery_date_from_source_header`, `parse_aw_delivery_workbook` |
| `delivery_store.py` | `delivery_date_from_source_header` | 979 | Run the delivery date from source header workflow for the delivery-list scanner. | `import_delivery_folder` |
| `delivery_store.py` | `parse_aw_delivery_workbook` | 1001 | Parse aw delivery workbook for the delivery-list scanner workflow. | `load_delivery_source_payload` |
| `delivery_store.py` | `parse_delivery_csv` | 1051 | Parse a delivery-list CSV while honoring an in-file delivery date. | `load_delivery_source_payload` |
| `delivery_store.py` | `load_delivery_source_payload` | 1104 | Load delivery source payload for the delivery-list scanner workflow. | `import_delivery_folder` |
| `delivery_store.py` | `source_file_hash` | 1120 | Run the source file hash workflow for the delivery-list scanner. | `import_delivery_folder` |
| `delivery_store.py` | `is_remake_item` | 1133 | Validate remake item for the delivery-list scanner workflow. | `get_print_package`, `glass_filter_matches`, `normal_printable`, `parse_aw_delivery_workbook`, `print_counts_for_items`, `should_print_delivery_item`, `upsert_delivery_list` |
| `delivery_store.py` | `is_rush_item` | 1143 | Validate rush item for the delivery-list scanner workflow. | `get_print_package`, `receive_indian_trail_scan`, `upsert_delivery_list` |
| `delivery_store.py` | `is_mirror_item` | 1153 | Validate mirror item for the delivery-list scanner workflow. | `get_print_package`, `glass_filter_matches`, `normal_printable`, `print_counts_for_items`, `should_print_delivery_item` |
| `delivery_store.py` | `should_print_delivery_item` | 1163 | Run the should print delivery item workflow for the delivery-list scanner. | `normal_printable`, `print_counts_for_items` |
| `delivery_store.py` | `print_counts_for_items` | 1176 | Run the print counts for items workflow for the delivery-list scanner. | `print_candidates_from_payload` |
| `delivery_store.py` | `row_value` | 1191 | Read a named value from sqlite3.Row, AzureSqlRow, or a dictionary. | `bay_from_row`, `customer_route_rules_from_connection`, `destination_for_line_item`, `item_from_row`, `mark_sdi`, `receive_indian_trail_scan`, `repair_route_stage_memberships`, `stage_rank` (+2 more) |
| `delivery_store.py` | `item_from_row` | 1202 | Run the item from row workflow for the delivery-list scanner. | `_get_line_items`, `admin_search_line_items`, `rack_from_row` |
| `delivery_store.py` | `event_from_row` | 1235 | Run the event from row workflow for the delivery-list scanner. | `_get_scan_events`, `insert_event` |
| `delivery_store.py` | `list_meta` | 1272 | Read meta for the delivery-list scanner workflow. | `_get_payload`, `get_delivery_lists` |
| `delivery_store.py` | `request_user_name` | 1289 | Run the request user name workflow for the delivery-list scanner. | `import_delivery_folder`, `import_delivery_list`, `record_scan`, `scan_rack_outbound` |
| `delivery_store.py` | `request_station` | 1298 | Run the request station workflow for the delivery-list scanner. | `receive_indian_trail_scan`, `record_scan`, `scan_item_to_rack`, `scan_out_bay_item`, `scan_rack_outbound` |
| `delivery_store.py` | `BaseDeliveryStore.initialize` | 1310 | Run the initialize workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.health` | 1318 | Run the health workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_delivery_lists` | 1326 | Read delivery lists for the delivery-list scanner workflow. | `delete_delivery_date`, `delete_delivery_list`, `import_delivery_folder`, `import_delivery_list` |
| `delivery_store.py` | `BaseDeliveryStore.get_delivery_list` | 1334 | Read delivery list for the delivery-list scanner workflow. | `get_print_package` |
| `delivery_store.py` | `BaseDeliveryStore.get_line_items` | 1342 | Read line items for the delivery-list scanner workflow. | `export_csv`, `export_xlsx` |
| `delivery_store.py` | `BaseDeliveryStore.create_app_notification` | 1350 | Create app notification for the delivery-list scanner workflow. | `mark_sdi` |
| `delivery_store.py` | `BaseDeliveryStore.get_pending_notifications` | 1406 | Read pending notifications for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.acknowledge_notification` | 1456 | Run the acknowledge notification workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.record_scan` | 1489 | Process scan for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.undo_last_scan` | 1497 | Undo last scan for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.redo_last_undo` | 1505 | Redo last undo for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.reset_stage` | 1513 | Run the reset stage workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.import_delivery_list` | 1521 | Load delivery list for the delivery-list scanner workflow. | `import_delivery_folder` |
| `delivery_store.py` | `BaseDeliveryStore.import_delivery_folder` | 1529 | Load delivery folder for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_print_package` | 1757 | Read print package for the delivery-list scanner workflow. | `export_package_xlsx` |
| `delivery_store.py` | `BaseDeliveryStore.get_scan_events` | 1765 | Read scan events for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_exceptions` | 1773 | Read exceptions for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_stations` | 1781 | Read stations for the delivery-list scanner workflow. | `add_station`, `remove_station`, `rename_station` |
| `delivery_store.py` | `BaseDeliveryStore.add_station` | 1789 | Create station for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.rename_station` | 1797 | Update station for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_station` | 1805 | Remove station for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.export_csv` | 1813 | Export CSV for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.export_xlsx` | 1821 | Export XLSX for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.export_package_xlsx` | 1829 | Export package XLSX for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.authenticate_user` | 1837 | Run the authenticate user workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_user_by_session` | 1845 | Read user by session for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.delete_session` | 1853 | Remove session for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.create_user` | 1861 | Create user for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.list_users` | 1869 | Read users for the delivery-list scanner workflow. | `deactivate_user`, `delete_user`, `reactivate_user`, `update_user_password`, `update_user_roles` |
| `delivery_store.py` | `BaseDeliveryStore.deactivate_user` | 1877 | Run the deactivate user workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.reactivate_user` | 1885 | Run the reactivate user workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.delete_user` | 1893 | Remove user for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.update_user_password` | 1901 | Update user password for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.update_user_roles` | 1909 | Update user roles for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.list_active_sessions` | 1917 | Read active sessions for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_permissions` | 1925 | Read permissions for the delivery-list scanner workflow. | `update_role_permissions` |
| `delivery_store.py` | `BaseDeliveryStore.list_roles` | 1933 | Read roles for the delivery-list scanner workflow. | `update_role_permissions` |
| `delivery_store.py` | `BaseDeliveryStore.update_role_permissions` | 1941 | Update role permissions for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.preview_import` | 1949 | Run the preview import workflow for the delivery-list scanner. | `import_delivery_folder` |
| `delivery_store.py` | `BaseDeliveryStore.admin_summary` | 1957 | Run the admin summary workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.resolve_exception` | 1965 | Resolve exception for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.global_search` | 1973 | Run the global search workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.stage_kind` | 2024 | Run the stage kind workflow for the delivery-list scanner. | `global_search`, `representative_rank` |
| `delivery_store.py` | `BaseDeliveryStore.representative_rank` | 2045 | Run the representative rank workflow for the delivery-list scanner. | `global_search` |
| `delivery_store.py` | `BaseDeliveryStore.rack_location_label` | 2073 | Run the rack location label workflow for the delivery-list scanner. | `global_search` |
| `delivery_store.py` | `BaseDeliveryStore.airport_label` | 2088 | Run the airport label workflow for the delivery-list scanner. | `global_search` |
| `delivery_store.py` | `BaseDeliveryStore.update_line_item` | 2217 | Update line item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.delete_delivery_list` | 2225 | Remove delivery list for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.delete_delivery_date` | 2233 | Remove delivery date for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.delete_line_item` | 2241 | Remove line item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_customer_route_rules` | 2249 | Read customer route rules for the delivery-list scanner workflow. | `add_customer_route_rule`, `apply_customer_route_rules_to_payload`, `remove_customer_route_rule` |
| `delivery_store.py` | `BaseDeliveryStore.add_customer_route_rule` | 2257 | Create customer route rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_customer_route_rule` | 2265 | Remove customer route rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_customer_email_settings` | 2273 | Read customer email settings for the delivery-list scanner workflow. | `queue_customer_email_test`, `remove_customer_email_cc`, `remove_customer_email_contact`, `upsert_customer_email_cc`, `upsert_customer_email_contact` |
| `delivery_store.py` | `BaseDeliveryStore.upsert_customer_email_contact` | 2348 | Run the upsert customer email contact workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_customer_email_contact` | 2387 | Remove customer email contact for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.upsert_customer_email_cc` | 2405 | Run the upsert customer email cc workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_customer_email_cc` | 2428 | Remove customer email cc for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.queue_customer_email_test` | 2446 | Create or send a customer-email test message. | — |
| `delivery_store.py` | `BaseDeliveryStore.customer_email_matches` | 2500 | Run the customer email matches workflow for the delivery-list scanner. | `queue_ready_email_if_customer_complete`, `send_customer_manifests_for_import` |
| `delivery_store.py` | `BaseDeliveryStore.customer_cc_emails` | 2515 | Run the customer cc emails workflow for the delivery-list scanner. | `queue_ready_email_if_customer_complete`, `send_customer_manifests_for_import` |
| `delivery_store.py` | `BaseDeliveryStore.queue_email_message` | 2523 | Send email message for the delivery-list scanner workflow. | `queue_ready_email_if_customer_complete`, `send_customer_manifests_for_import` |
| `delivery_store.py` | `BaseDeliveryStore.try_send_email` | 2582 | Run the try send email workflow for the delivery-list scanner. | `queue_customer_email_test`, `queue_email_message` |
| `delivery_store.py` | `BaseDeliveryStore.send_customer_manifests_for_import` | 2610 | Send customer manifests for import for the delivery-list scanner workflow. | `import_delivery_list` |
| `delivery_store.py` | `BaseDeliveryStore.queue_ready_email_if_customer_complete` | 2669 | Send ready email if customer complete for the delivery-list scanner workflow. | `record_scan` |
| `delivery_store.py` | `BaseDeliveryStore.get_manual_edit_lookups` | 2705 | Read manual edit lookups for the delivery-list scanner workflow. | `add_manual_edit_lookup` |
| `delivery_store.py` | `BaseDeliveryStore.add_manual_edit_lookup` | 2713 | Create manual edit lookup for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_bay_scan_settings` | 2721 | Read bay scan settings for the delivery-list scanner workflow. | `remove_bay_manual_input_rule`, `remove_bay_scan_barcode_rule`, `upsert_bay_manual_input_rule`, `upsert_bay_scan_barcode_rule` |
| `delivery_store.py` | `BaseDeliveryStore.upsert_bay_manual_input_rule` | 2729 | Run the upsert bay manual input rule workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_bay_manual_input_rule` | 2737 | Remove bay manual input rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.upsert_bay_scan_barcode_rule` | 2745 | Run the upsert bay scan barcode rule workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_bay_scan_barcode_rule` | 2753 | Remove bay scan barcode rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.manual_assign_bay_item` | 2761 | Run the manual assign bay item workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.reports_summary` | 2769 | Run the reports summary workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_bays` | 2777 | Read bays for the delivery-list scanner workflow. | `create_bays`, `delete_bay`, `delete_bay_group`, `move_bay_group`, `set_bay_group_position`, `set_bay_status`, `update_bay_layout` |
| `delivery_store.py` | `BaseDeliveryStore.get_bay_job_details` | 2785 | Read bay job details for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.get_bay_layout` | 2793 | Read bay layout for the delivery-list scanner workflow. | `seed_bays` |
| `delivery_store.py` | `BaseDeliveryStore.get_bay_events` | 2801 | Read bay events for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.indian_trail_summary` | 2809 | Run the indian trail summary workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.indian_trail_in_transit` | 2817 | Run the indian trail in transit workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.receive_indian_trail_scan` | 2825 | Process indian trail scan for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.assign_bay` | 2833 | Run the assign bay workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.move_bay_assignment` | 2841 | Run the move bay assignment workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.clear_bay` | 2849 | Remove bay for the delivery-list scanner workflow. | `bay_check` |
| `delivery_store.py` | `BaseDeliveryStore.mark_sdi` | 2857 | Run the mark SDI workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.remove_sdi` | 2865 | Remove SDI for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.bay_check` | 2873 | Run the bay check workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.scan_out_bay_item` | 2881 | Process out bay item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.clear_bay_assignment` | 2889 | Remove bay assignment for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.restore_bay_assignment` | 2897 | Run the restore bay assignment workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `BaseDeliveryStore.update_bay_layout` | 2905 | Update bay layout for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `BaseDeliveryStore.set_bay_group_position` | 2913 | Update bay group position for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.__init__` | 2925 | Initialize a SQLite delivery store instance and its required state. | `__init__` |
| `delivery_store.py` | `SQLiteDeliveryStore.connect` | 2935 | Run the connect workflow for the delivery-list scanner. | `acknowledge_notification`, `add_customer_route_rule`, `add_manual_edit_lookup`, `add_station`, `admin_search_line_items`, `admin_summary`, `assign_bay`, `assign_line_item_to_rack` (+97 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.health` | 2954 | Run the health workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.initialize` | 2968 | Run the initialize workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.customer_route_rules_from_connection` | 2985 | Run the customer route rules from connection workflow for the delivery-list scanner. | `get_customer_route_rules`, `repair_route_stage_memberships`, `repair_route_stage_memberships_if_needed`, `route_stage_repair_signature` |
| `delivery_store.py` | `SQLiteDeliveryStore.route_stage_repair_signature` | 3005 | Run the route stage repair signature workflow for the delivery-list scanner. | `repair_route_stage_memberships_if_needed` |
| `delivery_store.py` | `SQLiteDeliveryStore.system_metadata_value` | 3026 | Run the system metadata value workflow for the delivery-list scanner. | `repair_route_stage_memberships_if_needed` |
| `delivery_store.py` | `SQLiteDeliveryStore.set_system_metadata_value` | 3035 | Update system metadata value for the delivery-list scanner workflow. | `repair_route_stage_memberships_if_needed` |
| `delivery_store.py` | `SQLiteDeliveryStore.repair_route_stage_memberships_if_needed` | 3052 | Reconcile route stage memberships if needed for the delivery-list scanner workflow. | `add_customer_route_rule`, `initialize`, `remove_customer_route_rule` |
| `delivery_store.py` | `SQLiteDeliveryStore.repair_route_stage_memberships` | 3070 | Repair active route copies using customer rules without slowing every startup. | `repair_route_stage_memberships_if_needed` |
| `delivery_store.py` | `SQLiteDeliveryStore.create_schema` | 3157 | Create schema for the delivery-list scanner workflow. | `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.apply_schema_migrations` | 3504 | Run the apply schema migrations workflow for the delivery-list scanner. | `create_schema` |
| `delivery_store.py` | `SQLiteDeliveryStore.ensure_column` | 3548 | Validate column for the delivery-list scanner workflow. | `apply_schema_migrations` |
| `delivery_store.py` | `SQLiteDeliveryStore.clone_item_for_list` | 3558 | Run the clone item for list workflow for the delivery-list scanner. | `insert_line_items` |
| `delivery_store.py` | `SQLiteDeliveryStore.insert_line_items` | 3592 | Create line items for the delivery-list scanner workflow. | `upsert_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.import_order_item_key` | 3633 | Load order item key for the delivery-list scanner workflow. | `match_previous`, `upsert_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.import_business_key` | 3645 | Load business key for the delivery-list scanner workflow. | `match_previous`, `upsert_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.field` | 3651 | Run the field workflow for the delivery-list scanner. | `import_business_key` |
| `delivery_store.py` | `SQLiteDeliveryStore.upsert_delivery_list` | 3670 | Run the upsert delivery list workflow for the delivery-list scanner. | `import_delivery_list`, `seed_demo_data` |
| `delivery_store.py` | `SQLiteDeliveryStore.add_previous_to_pool` | 3725 | Create previous to pool for the delivery-list scanner workflow. | `upsert_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.pop_previous` | 3802 | Run the pop previous workflow for the delivery-list scanner. | `match_previous` |
| `delivery_store.py` | `SQLiteDeliveryStore.match_previous` | 3816 | Resolve previous for the delivery-list scanner workflow. | `upsert_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_demo_data` | 3919 | Create demo data for the delivery-list scanner workflow. | `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_stations` | 3943 | Create stations for the delivery-list scanner workflow. | `seed_demo_data` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_customer_route_rules` | 3953 | Create customer route rules for the delivery-list scanner workflow. | `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_security_data` | 3969 | Create security data for the delivery-list scanner workflow. | `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_user_if_missing` | 4026 | Create user if missing for the delivery-list scanner workflow. | `seed_security_data` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_bays` | 4048 | Create bays for the delivery-list scanner workflow. | `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_racks` | 4083 | Create racks for the delivery-list scanner workflow. | `get_racks`, `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.layout_bay_policy_status` | 4106 | Run the layout bay policy status workflow for the delivery-list scanner. | `seed_layout_bays` |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_layout_bays` | 4122 | Create layout bays for the delivery-list scanner workflow. | `seed_bays` |
| `delivery_store.py` | `SQLiteDeliveryStore.repair_manual_assign_bay_visibility` | 4199 | Reconcile manual assign bay visibility for the delivery-list scanner workflow. | `initialize` |
| `delivery_store.py` | `SQLiteDeliveryStore.list_timing_metrics` | 4243 | Read timing metrics for the delivery-list scanner workflow. | `get_delivery_lists` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_delivery_lists` | 4279 | Read delivery lists for the delivery-list scanner workflow. | `delete_delivery_date`, `delete_delivery_list`, `import_delivery_folder`, `import_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_line_items` | 4333 | Read line items for the delivery-list scanner workflow. | `export_csv`, `export_xlsx` |
| `delivery_store.py` | `SQLiteDeliveryStore._get_line_items` | 4342 | Read line items for the delivery-list scanner workflow. | `_get_payload`, `get_line_items` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_scan_events` | 4553 | Read scan events for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore._get_scan_events` | 4562 | Read scan events for the delivery-list scanner workflow. | `_get_payload`, `get_scan_events` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_delivery_list` | 4583 | Read delivery list for the delivery-list scanner workflow. | `get_print_package` |
| `delivery_store.py` | `SQLiteDeliveryStore._get_payload` | 4592 | Read payload for the delivery-list scanner workflow. | `assign_line_item_to_rack`, `delete_line_item`, `get_delivery_list`, `outbound_scan_gate`, `record_scan`, `redo_last_undo`, `reset_stage`, `scan_rack_outbound` (+2 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.user_can_access_list` | 4612 | Run the user can access list workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_stations` | 4624 | Read stations for the delivery-list scanner workflow. | `add_station`, `remove_station`, `rename_station` |
| `delivery_store.py` | `SQLiteDeliveryStore.add_station` | 4634 | Create station for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.rename_station` | 4649 | Update station for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.remove_station` | 4671 | Remove station for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_permissions` | 4688 | Read permissions for the delivery-list scanner workflow. | `update_role_permissions` |
| `delivery_store.py` | `SQLiteDeliveryStore.list_roles` | 4696 | Read roles for the delivery-list scanner workflow. | `update_role_permissions` |
| `delivery_store.py` | `SQLiteDeliveryStore.update_role_permissions` | 4719 | Update role permissions for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.user_from_row` | 4753 | Run the user from row workflow for the delivery-list scanner. | `authenticate_user`, `create_user`, `get_user_by_session`, `list_users` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_user_by_username` | 4795 | Read user by username for the delivery-list scanner workflow. | `authenticate_user`, `confirm_password_reset`, `create_user`, `deactivate_user`, `delete_user`, `reactivate_user`, `request_password_reset`, `seed_user_if_missing` (+2 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.authenticate_user` | 4811 | Run the authenticate user workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_user_by_session` | 4840 | Read user by session for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_session` | 4869 | Remove session for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.request_password_reset` | 4882 | Run the request password reset workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.confirm_password_reset` | 4917 | Run the confirm password reset workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.list_users` | 4954 | Read users for the delivery-list scanner workflow. | `deactivate_user`, `delete_user`, `reactivate_user`, `update_user_password`, `update_user_roles` |
| `delivery_store.py` | `SQLiteDeliveryStore.deactivate_user` | 4964 | Run the deactivate user workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.reactivate_user` | 4986 | Run the reactivate user workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_user` | 5005 | Remove user for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.update_user_password` | 5028 | Update user password for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.update_user_roles` | 5050 | Update user roles for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.list_active_sessions` | 5136 | Read active sessions for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.create_user` | 5168 | Create user for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_customer_route_rules` | 5207 | Read customer route rules for the delivery-list scanner workflow. | `add_customer_route_rule`, `apply_customer_route_rules_to_payload`, `remove_customer_route_rule` |
| `delivery_store.py` | `SQLiteDeliveryStore.add_customer_route_rule` | 5216 | Create customer route rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.remove_customer_route_rule` | 5284 | Remove customer route rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.send_customer_manifests_for_import` | 5304 | Send customer manifests for import for the delivery-list scanner workflow. | `import_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_manual_edit_lookups` | 5338 | Read manual edit lookups for the delivery-list scanner workflow. | `add_manual_edit_lookup` |
| `delivery_store.py` | `SQLiteDeliveryStore.add_lookup` | 5350 | Create lookup for the delivery-list scanner workflow. | `get_manual_edit_lookups` |
| `delivery_store.py` | `SQLiteDeliveryStore.add_manual_edit_lookup` | 5397 | Create manual edit lookup for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.seed_bay_auto_assign_settings` | 5439 | Create bay auto assign settings for the delivery-list scanner workflow. | `get_bay_auto_assign_settings`, `get_bay_auto_assign_settings_con`, `initialize`, `update_bay_auto_assign_settings` |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_auto_assign_settings_from_rows` | 5456 | Run the bay auto assign settings from rows workflow for the delivery-list scanner. | `get_bay_auto_assign_settings`, `get_bay_auto_assign_settings_con` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_auto_assign_settings` | 5481 | Read bay auto assign settings for the delivery-list scanner workflow. | `update_bay_auto_assign_settings` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_auto_assign_settings_con` | 5492 | Read bay auto assign settings con for the delivery-list scanner workflow. | `bay_type_requires_manual_assignment`, `insert_line_items`, `suggested_bay_from_settings` |
| `delivery_store.py` | `SQLiteDeliveryStore.update_bay_auto_assign_settings` | 5502 | Update bay auto assign settings for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_type_requires_manual_assignment` | 5541 | Run the bay type requires manual assignment workflow for the delivery-list scanner. | `preassign_bay_for_outbound`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.suggested_bay_from_settings` | 5551 | Run the suggested bay from settings workflow for the delivery-list scanner. | `preassign_bay_for_outbound`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_manual_rule_from_row` | 5559 | Run the bay manual rule from row workflow for the delivery-list scanner. | `get_bay_scan_settings` |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_barcode_rule_from_row` | 5573 | Run the bay barcode rule from row workflow for the delivery-list scanner. | `get_bay_scan_settings` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_scan_settings` | 5586 | Read bay scan settings for the delivery-list scanner workflow. | `remove_bay_manual_input_rule`, `remove_bay_scan_barcode_rule`, `upsert_bay_manual_input_rule`, `upsert_bay_scan_barcode_rule` |
| `delivery_store.py` | `SQLiteDeliveryStore.upsert_bay_manual_input_rule` | 5612 | Run the upsert bay manual input rule workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.remove_bay_manual_input_rule` | 5641 | Remove bay manual input rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.upsert_bay_scan_barcode_rule` | 5654 | Run the upsert bay scan barcode rule workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.remove_bay_scan_barcode_rule` | 5679 | Remove bay scan barcode rule for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_manual_text_is_known` | 5692 | Run the bay manual text is known workflow for the delivery-list scanner. | `manual_assign_bay_item`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.find_manual_bay_line_items` | 5725 | Resolve manual bay line items for the delivery-list scanner workflow. | `find_sdi_line_items`, `manual_assign_bay_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.find_sdi_line_items` | 5768 | Resolve an SDI entry as a barcode, SO/order number, or complete Job Nr. label. | `mark_sdi`, `remove_sdi` |
| `delivery_store.py` | `SQLiteDeliveryStore.expand_priority_line_items` | 5824 | Return every active stage clone for the selected physical glass items. | `mark_sdi`, `remove_sdi` |
| `delivery_store.py` | `SQLiteDeliveryStore.stage_rank` | 5881 | Run the stage rank workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.priority_list_context` | 5906 | Run the priority list context workflow for the delivery-list scanner. | `mark_sdi`, `remove_sdi` |
| `delivery_store.py` | `SQLiteDeliveryStore.ensure_manual_bay_delivery_list` | 5936 | Validate manual bay delivery list for the delivery-list scanner workflow. | `create_manual_bay_line_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.create_manual_bay_line_item` | 5954 | Create manual bay line item for the delivery-list scanner workflow. | `manual_assign_bay_item`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.assign_line_items_to_bay` | 5975 | Run the assign line items to bay workflow for the delivery-list scanner. | `manual_assign_bay_item`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.manual_assign_bay_item` | 6015 | Run the manual assign bay item workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.route_from_customer_rules` | 6065 | Run the route from customer rules workflow for the delivery-list scanner. | `resolve_item_route` |
| `delivery_store.py` | `SQLiteDeliveryStore.resolve_item_route` | 6090 | Resolve one item using the authoritative route order. | `apply_customer_route_rules_to_payload`, `repair_route_stage_memberships` |
| `delivery_store.py` | `SQLiteDeliveryStore.apply_customer_route_rules_to_payload` | 6109 | Run the apply customer route rules to payload workflow for the delivery-list scanner. | `import_delivery_list`, `preview_import` |
| `delivery_store.py` | `SQLiteDeliveryStore.validate_import_payload` | 6129 | Validate import payload for the delivery-list scanner workflow. | `import_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.import_delivery_list` | 6149 | Load delivery list for the delivery-list scanner workflow. | `import_delivery_folder` |
| `delivery_store.py` | `SQLiteDeliveryStore.print_candidates_from_payload` | 6251 | Run the print candidates from payload workflow for the delivery-list scanner. | `import_delivery_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.import_delivery_folder` | 6275 | Load delivery folder for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_print_package` | 6451 | Read print package for the delivery-list scanner workflow. | `export_package_xlsx` |
| `delivery_store.py` | `SQLiteDeliveryStore.has_update_marker` | 6474 | Validate update marker for the delivery-list scanner workflow. | `get_print_package` |
| `delivery_store.py` | `SQLiteDeliveryStore.route_matches` | 6483 | Run the route matches workflow for the delivery-list scanner. | `get_print_package` |
| `delivery_store.py` | `SQLiteDeliveryStore.glass_filter_matches` | 6495 | Run the glass filter matches workflow for the delivery-list scanner. | `search_filters_match` |
| `delivery_store.py` | `SQLiteDeliveryStore.search_filters_match` | 6508 | Run the search filters match workflow for the delivery-list scanner. | `get_print_package` |
| `delivery_store.py` | `SQLiteDeliveryStore.normal_printable` | 6524 | Run the normal printable workflow for the delivery-list scanner. | `get_print_package` |
| `delivery_store.py` | `SQLiteDeliveryStore.stage_sheet_kind` | 6538 | Run the stage sheet kind workflow for the delivery-list scanner. | `get_print_package` |
| `delivery_store.py` | `SQLiteDeliveryStore.find_unique_suffix_item` | 6644 | Resolve unique suffix item for the delivery-list scanner workflow. | `recover_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.find_unique_order` | 6656 | Resolve unique order for the delivery-list scanner workflow. | `recover_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.recover_scan` | 6665 | Run the recover scan workflow for the delivery-list scanner. | `receive_indian_trail_scan`, `record_scan`, `scan_item_to_rack`, `scan_other_list_hint` |
| `delivery_store.py` | `SQLiteDeliveryStore.scan_other_list_hint` | 6718 | Process other list hint for the delivery-list scanner workflow. | `receive_indian_trail_scan`, `record_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.insert_event` | 6773 | Create event for the delivery-list scanner workflow. | `auto_stage_for_outbound`, `import_delivery_list`, `mark_sdi`, `not_on_way_rack`, `outbound_scan_gate`, `receive_indian_trail_scan`, `record_scan`, `redo_last_undo` (+4 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.insert_exception` | 6817 | Create exception for the delivery-list scanner workflow. | `insert_event`, `preassign_bay_for_outbound`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.insert_audit` | 6831 | Create audit for the delivery-list scanner workflow. | `add_customer_route_rule`, `add_manual_edit_lookup`, `assign_bay`, `assign_line_item_to_rack`, `assign_transportation_from_outbound_override`, `authenticate_user`, `auto_stage_for_outbound`, `bay_check` (+66 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.record_scan` | 6855 | Process scan for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.matching_staging_row_for_outbound` | 7037 | Run the matching staging row for outbound workflow for the delivery-list scanner. | `outbound_scan_gate` |
| `delivery_store.py` | `SQLiteDeliveryStore.transportation_for_staging_row` | 7068 | Run the transportation for staging row workflow for the delivery-list scanner. | `outbound_scan_gate` |
| `delivery_store.py` | `SQLiteDeliveryStore.assign_transportation_from_outbound_override` | 7088 | Run the assign transportation from outbound override workflow for the delivery-list scanner. | `outbound_scan_gate` |
| `delivery_store.py` | `SQLiteDeliveryStore.outbound_scan_gate` | 7137 | Enforce outbound safety before a piece is scanned out. | `record_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.auto_stage_for_outbound` | 7285 | Run the auto stage for outbound workflow for the delivery-list scanner. | `outbound_scan_gate` |
| `delivery_store.py` | `SQLiteDeliveryStore.preassign_bay_for_outbound` | 7364 | Run the preassign bay for outbound workflow for the delivery-list scanner. | `record_scan`, `scan_rack_outbound` |
| `delivery_store.py` | `SQLiteDeliveryStore.reset_stage` | 7468 | Run the reset stage workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.undo_last_scan` | 7494 | Undo last scan for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.redo_last_undo` | 7534 | Redo last undo for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_exceptions` | 7579 | Read exceptions for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.preview_import` | 7621 | Run the preview import workflow for the delivery-list scanner. | `import_delivery_folder` |
| `delivery_store.py` | `SQLiteDeliveryStore.admin_summary` | 7687 | Run the admin summary workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.resolve_exception` | 7783 | Resolve exception for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.global_search` | 7810 | Run the global search workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.stage_kind` | 7861 | Run the stage kind workflow for the delivery-list scanner. | `global_search`, `representative_rank` |
| `delivery_store.py` | `SQLiteDeliveryStore.representative_rank` | 7882 | Run the representative rank workflow for the delivery-list scanner. | `global_search` |
| `delivery_store.py` | `SQLiteDeliveryStore.rack_location_label` | 7910 | Run the rack location label workflow for the delivery-list scanner. | `global_search` |
| `delivery_store.py` | `SQLiteDeliveryStore.airport_label` | 7925 | Run the airport label workflow for the delivery-list scanner. | `global_search` |
| `delivery_store.py` | `SQLiteDeliveryStore.manual_edit_sibling_rows` | 8054 | Run the manual edit sibling rows workflow for the delivery-list scanner. | `sync_manual_route_membership`, `update_line_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.manual_route_profile` | 8088 | Run the manual route profile workflow for the delivery-list scanner. | `ensure_manual_route_list`, `repair_route_stage_memberships` |
| `delivery_store.py` | `SQLiteDeliveryStore.ensure_manual_route_list` | 8107 | Validate manual route list for the delivery-list scanner workflow. | `sync_manual_route_membership` |
| `delivery_store.py` | `SQLiteDeliveryStore.merge_manual_receiving_row` | 8129 | Run the merge manual receiving row workflow for the delivery-list scanner. | `sync_manual_route_membership` |
| `delivery_store.py` | `SQLiteDeliveryStore.sync_manual_route_membership` | 8177 | Run the sync manual route membership workflow for the delivery-list scanner. | `repair_route_stage_memberships`, `update_line_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.update_line_item` | 8249 | Update line item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.update_line_item_location` | 8366 | Update line item location for the delivery-list scanner workflow. | `assign_line_item_to_rack`, `update_line_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_line_item` | 8451 | Remove line item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_delivery_list` | 8471 | Remove delivery list for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_delivery_date` | 8491 | Remove delivery date for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.reports_summary` | 8513 | Run the reports summary workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.date_clause` | 8523 | Run the date clause workflow for the delivery-list scanner. | `reports_summary` |
| `delivery_store.py` | `SQLiteDeliveryStore.delivery_list_date_clause` | 8540 | Run the delivery list date clause workflow for the delivery-list scanner. | `reports_summary` |
| `delivery_store.py` | `SQLiteDeliveryStore.list_audit_events` | 8727 | Read audit events for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_email_outbox_item` | 8765 | Read email outbox item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_from_row` | 8796 | Run the bay from row workflow for the delivery-list scanner. | `get_bays` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bays` | 8937 | Read bays for the delivery-list scanner workflow. | `create_bays`, `delete_bay`, `delete_bay_group`, `move_bay_group`, `set_bay_group_position`, `set_bay_status`, `update_bay_layout` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_job_details` | 8959 | Return live job fulfillment for one bay, including scan-in timestamps. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_layout` | 9089 | Read bay layout for the delivery-list scanner workflow. | `seed_bays` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_events` | 9101 | Return detailed Bay Map history with each item's current move target. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.get_stale_bay_orders` | 9162 | Read stale bay orders for the delivery-list scanner workflow. | `snooze_stale_bay_orders` |
| `delivery_store.py` | `SQLiteDeliveryStore.snooze_stale_bay_orders` | 9240 | Run the snooze stale bay orders workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.received_qty_for_rack_item` | 9272 | Run the received qty for rack item workflow for the delivery-list scanner. | `rack_from_row` |
| `delivery_store.py` | `SQLiteDeliveryStore.rack_from_row` | 9314 | Run the rack from row workflow for the delivery-list scanner. | `get_racks`, `rack_packing_list`, `scan_rack_outbound` |
| `delivery_store.py` | `SQLiteDeliveryStore.rack_summary` | 9385 | Run the rack summary workflow for the delivery-list scanner. | `get_racks`, `indian_trail_summary` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_racks` | 9404 | Read racks for the delivery-list scanner workflow. | `assign_line_item_to_rack`, `clear_rack`, `clear_rack_item`, `complete_rack`, `create_rack_set`, `delete_rack`, `move_rack_item`, `not_on_way_rack` (+5 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.get_rack_by_code` | 9415 | Read rack by code for the delivery-list scanner workflow. | `assign_line_item_to_rack`, `assign_transportation_from_outbound_override`, `clear_rack`, `complete_rack`, `delete_rack`, `move_rack_item`, `not_on_way_rack`, `outbound_scan_gate` (+6 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.scan_item_to_rack` | 9427 | Process item to rack for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.move_rack_item` | 9528 | Run the move rack item workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.clear_rack_item` | 9556 | Remove rack item for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.clear_rack` | 9597 | Remove rack for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.rack_destination_value` | 9613 | Run the rack destination value workflow for the delivery-list scanner. | `destination_address_for_rack`, `rack_destinations_from_items`, `rack_packing_list`, `received_qty_for_rack_item`, `record_scan`, `scan_item_to_rack`, `scan_rack_outbound` |
| `delivery_store.py` | `SQLiteDeliveryStore.destination_for_line_item` | 9633 | Run the destination for line item workflow for the delivery-list scanner. | `rack_destinations_from_items`, `record_scan`, `repair_route_stage_memberships`, `scan_item_to_rack`, `sync_manual_route_membership`, `validate_rack_destination_for_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.rack_destinations_from_items` | 9658 | Run the rack destinations from items workflow for the delivery-list scanner. | `complete_rack`, `computed_rack_destination`, `record_scan`, `scan_item_to_rack`, `validate_rack_destination_for_item` |
| `delivery_store.py` | `SQLiteDeliveryStore.computed_rack_destination` | 9684 | Run the computed rack destination workflow for the delivery-list scanner. | `rack_from_row`, `refresh_rack_destination` |
| `delivery_store.py` | `SQLiteDeliveryStore.refresh_rack_destination` | 9693 | Run the refresh rack destination workflow for the delivery-list scanner. | `clear_rack_item`, `move_rack_item`, `record_scan`, `repair_route_stage_memberships`, `scan_item_to_rack`, `update_line_item`, `update_line_item_location` |
| `delivery_store.py` | `SQLiteDeliveryStore.validate_rack_destination_for_item` | 9703 | Validate rack destination for item for the delivery-list scanner workflow. | `move_rack_item`, `update_line_item_location` |
| `delivery_store.py` | `SQLiteDeliveryStore.complete_rack` | 9719 | Run the complete rack workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.uncomplete_rack` | 9746 | Run the uncomplete rack workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.return_rack` | 9761 | Run the return rack workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.not_on_way_rack` | 9777 | Run the not on way rack workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.assign_line_item_to_rack` | 9884 | Run the assign line item to rack workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.update_rack` | 9971 | Update rack for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.create_rack_set` | 10010 | Create rack set for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_rack` | 10046 | Remove rack for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.destination_address_for_rack` | 10066 | Run the destination address for rack workflow for the delivery-list scanner. | `rack_packing_list` |
| `delivery_store.py` | `SQLiteDeliveryStore.rack_packing_list` | 10119 | Run the rack packing list workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.scan_rack_outbound` | 10157 | Process rack outbound for the delivery-list scanner workflow. | `record_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.indian_trail_in_transit` | 10284 | Run the indian trail in transit workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore._indian_trail_in_transit_payload` | 10293 | Return pieces scanned outbound but not yet received at Indian Trail. | `indian_trail_in_transit`, `indian_trail_summary` |
| `delivery_store.py` | `SQLiteDeliveryStore.indian_trail_summary` | 10579 | Run the indian trail summary workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.transit_row_is_truck` | 10653 | Run the transit row is truck workflow for the delivery-list scanner. | `indian_trail_summary` |
| `delivery_store.py` | `SQLiteDeliveryStore.admin_search_line_items` | 10722 | Run the admin search line items workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.find_bay_for_assignment` | 10786 | Resolve bay for assignment for the delivery-list scanner workflow. | `preassign_bay_for_outbound`, `receive_indian_trail_scan` |
| `delivery_store.py` | `SQLiteDeliveryStore.get_bay_by_code` | 10816 | Read bay by code for the delivery-list scanner workflow. | `assign_bay`, `bay_check`, `clear_bay`, `manual_assign_bay_item`, `mark_sdi`, `move_bay_assignment`, `receive_indian_trail_scan`, `set_bay_status` |
| `delivery_store.py` | `SQLiteDeliveryStore.insert_bay_event` | 10827 | Create bay event for the delivery-list scanner workflow. | `assign_bay`, `assign_line_items_to_bay`, `bay_check`, `clear_bay`, `clear_bay_assignment`, `create_bays`, `delete_bay`, `delete_bay_group` (+10 more) |
| `delivery_store.py` | `SQLiteDeliveryStore.assign_bay` | 10851 | Run the assign bay workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.receive_indian_trail_scan` | 10882 | Receive or return an item into an Indian Trail bay. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.move_bay_assignment` | 11443 | Run the move bay assignment workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.clear_bay` | 11466 | Remove bay for the delivery-list scanner workflow. | `bay_check` |
| `delivery_store.py` | `SQLiteDeliveryStore.clear_bay_assignment` | 11488 | Remove bay assignment for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.restore_bay_assignment` | 11512 | Run the restore bay assignment workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.set_bay_status` | 11539 | Update bay status for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.scan_out_bay_item` | 11575 | Scan an item out of its current bay and preserve a dated movement log. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.update_bay_layout` | 11658 | Update bay layout for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.set_bay_group_position` | 11714 | Update bay group position for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.create_bays` | 11737 | Create bays for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_bay` | 11794 | Remove bay for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.delete_bay_group` | 11820 | Remove bay group for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.move_bay_group` | 11851 | Run the move bay group workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.mark_sdi` | 11899 | Run the mark SDI workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.remove_sdi` | 12244 | Remove SDI for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.bay_check` | 12337 | Run the bay check workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.export_csv` | 12357 | Export CSV for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.export_package_xlsx` | 12400 | Export package XLSX for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.cell_ref` | 12444 | Run the cell ref workflow for the delivery-list scanner. | `inline_cell` |
| `delivery_store.py` | `SQLiteDeliveryStore.inline_cell` | 12457 | Run the inline cell workflow for the delivery-list scanner. | `export_package_xlsx`, `export_xlsx` |
| `delivery_store.py` | `SQLiteDeliveryStore.export_xlsx` | 12515 | Export XLSX for the delivery-list scanner workflow. | — |
| `delivery_store.py` | `SQLiteDeliveryStore.cell_ref` | 12537 | Run the cell ref workflow for the delivery-list scanner. | `inline_cell` |
| `delivery_store.py` | `SQLiteDeliveryStore.inline_cell` | 12550 | Run the inline cell workflow for the delivery-list scanner. | `export_package_xlsx`, `export_xlsx` |
| `delivery_store.py` | `AzureSqlDeliveryStore.__init__` | 12629 | Initialize a Azure SQL delivery store instance and its required state. | `__init__` |
| `delivery_store.py` | `AzureSqlDeliveryStore.connect` | 12640 | Run the connect workflow for the delivery-list scanner. | `acknowledge_notification`, `add_customer_route_rule`, `add_manual_edit_lookup`, `add_station`, `admin_search_line_items`, `admin_summary`, `assign_bay`, `assign_line_item_to_rack` (+97 more) |
| `delivery_store.py` | `AzureSqlDeliveryStore.initialize` | 12651 | Run the initialize workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `AzureSqlDeliveryStore.health` | 12681 | Run the health workflow for the delivery-list scanner. | — |
| `delivery_store.py` | `AzureSqlDeliveryStore.create_schema` | 12700 | Create schema for the delivery-list scanner workflow. | `initialize` |
| `delivery_store.py` | `AzureSqlDeliveryStore.ensure_column` | 12716 | Validate column for the delivery-list scanner workflow. | `apply_schema_migrations` |
| `delivery_store.py` | `create_store` | 12751 | Create store for the delivery-list scanner workflow. | — |
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
| `server.py` | `Handler.do_POST` | 1359 | Handle post for the delivery-list scanner workflow. | — |
| `server.py` | `daily_import_loop` | 1935 | Run the Temp Delivery Lists import once per day at 5 PM Eastern. | — |
| `server.py` | `start_daily_import_scheduler` | 1959 | Run the start daily import scheduler workflow for the delivery-list scanner. | `main` |
| `server.py` | `write_startup_failure_log` | 1969 | Persist startup failures so the Windows launcher can show a useful diagnosis. | `module startup` |
| `server.py` | `main` | 1997 | Start the database, scheduler, and HTTP server in a diagnosable order. | `module startup` |
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
| `tests/test_core_helpers.py` | `test_auth_and_text_helpers` | 24 | Run the test auth and text helpers workflow for the delivery-list scanner. | — |
| `tests/test_core_helpers.py` | `test_route_and_rack_helpers` | 46 | Run the test route and rack helpers workflow for the delivery-list scanner. | — |
| `tests/test_core_helpers.py` | `test_stage_generation_and_bay_suggestions` | 64 | Run the test stage generation and bay suggestions workflow for the delivery-list scanner. | — |
| `tests/test_core_helpers.py` | `test_sqlite_connection_uses_busy_timeout` | 90 | Confirm local startup tolerates short-lived SQLite file locks. | — |
| `tests/test_core_helpers.py` | `test_startup_failure_log_contains_runtime_context` | 104 | Verify startup exceptions leave a durable diagnostic file. | — |
| `tests/test_extended_workflows.py` | `_list_id` | 11 | Read ID for the delivery-list scanner workflow. | `test_manual_edits_deletes_and_audit`, `test_rack_crud_move_clear_and_packing_list` |
| `tests/test_extended_workflows.py` | `_item` | 20 | Run the item workflow for the delivery-list scanner. | `test_manual_edits_deletes_and_audit`, `test_priority_rush_and_remake_lifecycle` |
| `tests/test_extended_workflows.py` | `_scan` | 29 | Run the scan workflow for the delivery-list scanner. | `test_rack_crud_move_clear_and_packing_list` |
| `tests/test_extended_workflows.py` | `test_rack_crud_move_clear_and_packing_list` | 46 | Run the test rack crud move clear and packing list workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_bay_layout_status_creation_and_deletion` | 78 | Run the test bay layout status creation and deletion workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_manual_bay_assignment_rules_and_stale_workflow` | 123 | Run the test manual bay assignment rules and stale workflow workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_priority_rush_and_remake_lifecycle` | 156 | Run the test priority rush and remake lifecycle workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_manual_edits_deletes_and_audit` | 190 | Run the test manual edits deletes and audit workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_customer_email_and_barcode_rule_removal` | 222 | Run the test customer email and barcode rule removal workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_folder_import_update_skip_and_preview` | 244 | Run the test folder import update skip and preview workflow for the delivery-list scanner. | — |
| `tests/test_extended_workflows.py` | `test_delete_delivery_list_and_date` | 280 | Run the test delete delivery list and date workflow for the delivery-list scanner. | — |
| `tests/test_file_imports_and_sql_compat.py` | `test_csv_json_xlsx_import_parsers` | 13 | Run the test CSV JSON XLSX import parsers workflow for the delivery-list scanner. | — |
| `tests/test_file_imports_and_sql_compat.py` | `test_sqlite_limit_parameter_handling` | 50 | Run the test SQLite limit parameter handling workflow for the delivery-list scanner. | — |
| `tests/test_file_imports_and_sql_compat.py` | `test_sqlite_to_sql_server_translation` | 64 | Run the test SQLite to SQL server translation workflow for the delivery-list scanner. | — |
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
| `tests/test_static_integrity.py` | `test_v062_asset_cache_versions_and_sqlite_default` | 200 | Verify the v062 shell cache keys and SQLite-first configuration. | — |
| `tests/test_store_workflows.py` | `list_id` | 13 | Read ID for the delivery-list scanner workflow. | `test_bay_receive_move_clear_restore_and_scan_out`, `test_import_route_authority_and_exports`, `test_rack_lifecycle_and_outbound_departure`, `test_scanning_undo_redo_reset_and_errors` |
| `tests/test_store_workflows.py` | `item_for` | 22 | Run the item for workflow for the delivery-list scanner. | `test_import_route_authority_and_exports`, `test_scanning_undo_redo_reset_and_errors` |
| `tests/test_store_workflows.py` | `scan` | 31 | Run the scan workflow for the delivery-list scanner. | `test_bay_receive_move_clear_restore_and_scan_out`, `test_rack_lifecycle_and_outbound_departure`, `test_scanning_undo_redo_reset_and_errors` |
| `tests/test_store_workflows.py` | `test_import_route_authority_and_exports` | 47 | Run the test import route authority and exports workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_auth_users_roles_stations_and_password_reset` | 83 | Run the test auth users roles stations and password reset workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_scanning_undo_redo_reset_and_errors` | 133 | Run the test scanning undo redo reset and errors workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_rack_lifecycle_and_outbound_departure` | 172 | Run the test rack lifecycle and outbound departure workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_bay_receive_move_clear_restore_and_scan_out` | 209 | Run the test bay receive move clear restore and scan out workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_admin_rules_notifications_reports_and_search` | 247 | Run the test admin rules notifications reports and search workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_email_settings_manual_lookups_and_bay_rules` | 281 | Run the test email settings manual lookups and bay rules workflow for the delivery-list scanner. | — |
| `tests/test_store_workflows.py` | `test_repeated_startup_skips_unchanged_route_reconciliation` | 314 | Confirm repeated SQLite startup avoids the expensive full route repair. | — |
| `tests/test_store_workflows.py` | `unexpected_repair` | 321 | Fail if unchanged startup incorrectly invokes full route reconciliation. | — |
| `tests/test_store_workflows.py` | `test_context_managed_sqlite_connection_closes_after_transaction` | 334 | Protect the shared SQLite connection-cleanup behavior used by store methods. | — |
| `tests/test_visual_smoke.py` | `_mock_payload_script` | 34 | Run the mock payload script workflow for the delivery-list scanner. | `test_mocked_browser_visual_and_interaction_sweep` |
| `tests/test_visual_smoke.py` | `_strip_external_assets` | 331 | Run the strip external assets workflow for the delivery-list scanner. | `test_mocked_browser_visual_and_interaction_sweep` |
| `tests/test_visual_smoke.py` | `_overlap` | 342 | Run the overlap workflow for the delivery-list scanner. | `test_mocked_browser_visual_and_interaction_sweep` |
| `tests/test_visual_smoke.py` | `test_mocked_browser_visual_and_interaction_sweep` | 357 | Run the test mocked browser visual and interaction sweep workflow for the delivery-list scanner. | — |
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
| `tools/run_full_validation.py` | `run` | 28 | Run one validation command from the project root. | `main`, `run` |
| `tools/run_full_validation.py` | `audit_release_hygiene` | 39 | Reject generated or sensitive files that do not belong in a release ZIP. | `main` |
| `tools/run_full_validation.py` | `audit_python_documentation` | 62 | Verify every Python function remains documented after future edits. | `main` |
| `tools/run_full_validation.py` | `main` | 81 | Execute the full maintained validation workflow. | `module startup` |

## JavaScript function reference
| Function | Line | Purpose | Approximate callers |
|---|---:|---|---|
| `escapeHtml` | 491 | Run the escape HTML workflow for the browser application. | `addRow`, `adminModalContent`, `assignableRacks`, `autoAssignTypeOptions`, `bayAutoAssignerModalHtml`, `bayEditorBayRowMarkup`, `bayEventMoveControlHtml`, `bayEventMoveOptionsHtml` (+134 more) |
| `pad` | 504 | Run the pad workflow for the browser application. | `buildIndexes`, `canonicalBarcode`, `dateInputValue`, `todayKey` |
| `spanishBayCategoryLabel` | 1701 | Run the spanish bay category label workflow for the browser application. | — |
| `translateDynamicUiText` | 1871 | Run the translate dynamic UI text workflow for the browser application. | `translatedUiValue` |
| `translatedUiValue` | 1891 | Run the translated UI value workflow for the browser application. | `spanishBayCategoryLabel`, `translateUiAttributes`, `translateUiTextNode` |
| `translateUiTextNode` | 1905 | Run the translate UI text node workflow for the browser application. | `applyLanguageToRoot` |
| `translateUiAttributes` | 1927 | Run the translate UI attributes workflow for the browser application. | `applyLanguageToRoot` |
| `shouldSkipUiTranslation` | 1958 | Run the should skip UI translation workflow for the browser application. | `applyLanguageToRoot` |
| `applyLanguageToRoot` | 1967 | Update the apply language to root workflow using the existing shared UI state. | `close`, `initLanguageSystem`, `mountTimedScanConfirmation`, `setAppLanguage`, `showActionFeedback`, `submit` |
| `syncLanguageControls` | 1993 | Run the sync language controls workflow for the browser application. | `initLanguageSystem`, `setAppLanguage` |
| `setAppLanguage` | 2013 | Update the set app language workflow using the existing shared UI state. | `toggleAppLanguage` |
| `toggleAppLanguage` | 2030 | Toggle the toggle app language workflow using the existing shared UI state. | `wireEvents` |
| `initLanguageSystem` | 2039 | Run the init language system workflow for the browser application. | `wireEvents` |
| `syncFullscreenStickyPanelOffset` | 2061 | Run the sync fullscreen sticky panel offset workflow for the browser application. | `syncFullscreenControl`, `wireEvents` |
| `syncFullscreenControl` | 2074 | Run the sync fullscreen control workflow for the browser application. | `wireEvents` |
| `toggleFullscreen` | 2092 | Toggle the toggle fullscreen workflow using the existing shared UI state. | `wireEvents` |
| `refreshPage` | 2107 | Load the refresh page workflow using the existing shared UI state. | `wireEvents` |
| `consumeFullscreenRefreshRequest` | 2122 | Run the consume fullscreen refresh request workflow for the browser application. | `resumeFullscreenAfterRefresh` |
| `showFullscreenRecoveryPrompt` | 2137 | Open the show fullscreen recovery prompt workflow using the existing shared UI state. | `restoreFullscreenAfterManagedPrint`, `resumeFullscreenAfterRefresh` |
| `resumeFullscreenAfterRefresh` | 2161 | Run the resume fullscreen after refresh workflow for the browser application. | `init` |
| `customSelectIsEligible` | 2197 | Run the custom select is eligible workflow for the browser application. | `enhanceCustomSelect`, `openCustomSelect` |
| `customSelectAccessibleLabel` | 2212 | Run the custom select accessible label workflow for the browser application. | `enhanceCustomSelect`, `openCustomSelect`, `syncCustomSelect` |
| `customSelectSelectedText` | 2233 | Run the custom select selected text workflow for the browser application. | `syncCustomSelect` |
| `syncCustomSelect` | 2243 | Run the sync custom select workflow for the browser application. | `closeCustomSelect`, `enhanceCustomSelect`, `initCustomSelectSystem`, `openCustomSelect`, `openSdiPanel`, `renderBayLastScanCard`, `renderCustomSelectOptions`, `renderOutboundRackStatusTools` (+6 more) |
| `syncAllCustomSelects` | 2282 | Run the sync all custom selects workflow for the browser application. | `setAppLanguage` |
| `positionCustomSelectMenu` | 2292 | Run the position custom select menu workflow for the browser application. | `initCustomSelectSystem`, `openCustomSelect` |
| `setCustomSelectHighlight` | 2329 | Update the set custom select highlight workflow using the existing shared UI state. | `openCustomSelect`, `renderCustomSelectOptions` |
| `closeCustomSelect` | 2351 | Close the close custom select workflow using the existing shared UI state. | `initCustomSelectSystem`, `openCustomSelect`, `renderCustomSelectOptions`, `syncAllCustomSelects` |
| `customSelectOptionRows` | 2369 | Run the custom select option rows workflow for the browser application. | `renderCustomSelectOptions` |
| `renderCustomSelectOptions` | 2399 | Render the render custom select options workflow using the existing shared UI state. | `openCustomSelect` |
| `openCustomSelect` | 2465 | Open the open custom select workflow using the existing shared UI state. | `enhanceCustomSelect` |
| `enhanceCustomSelect` | 2563 | Run the enhance custom select workflow for the browser application. | `enhanceCustomSelects`, `initCustomSelectSystem` |
| `enhanceCustomSelects` | 2618 | Run the enhance custom selects workflow for the browser application. | `close`, `initCustomSelectSystem`, `mountTimedScanConfirmation` |
| `initCustomSelectSystem` | 2631 | Run the init custom select system workflow for the browser application. | `wireEvents` |
| `canonicalBarcode` | 2688 | Run the canonical barcode workflow for the browser application. | `exportStaticCsv`, `recoverScan`, `submitManualBayScan`, `submitManualScan` |
| `formatDisplayDate` | 2697 | Normalize the format display date workflow using the existing shared UI state. | `addRow`, `createDemoLists`, `customerEmailRulesModalHtml`, `deleteAdminDeliveryDateByDate`, `deleteSelectedDeliveryList`, `deliveryListAdminRows`, `homeStatisticsRangeParts`, `importTempDeliveryFolder` (+24 more) |
| `formatDateTime` | 2708 | Normalize the format date time workflow using the existing shared UI state. | `addRow`, `emailDraftPreviewHtml`, `renderBaySidePanels`, `renderItemRow`, `renderRackBoardCard`, `renderRackItem`, `renderSelectedRackDetails`, `renderStaleBayPanel` (+2 more) |
| `todayKey` | 2719 | Run the today key workflow for the browser application. | `dashboardDateKey`, `latestDeliveryDate`, `renderTodayProgress` |
| `dateInputValue` | 2729 | Run the date input value workflow for the browser application. | `defaultImportFromDate`, `homeReportDateParams` |
| `defaultImportFromDate` | 2740 | Run the default import from date workflow for the browser application. | `currentImportDateWindow`, `resetImportDateWindow` |
| `resetImportDateWindow` | 2751 | Run the reset import date window workflow for the browser application. | `init`, `wireEvents` |
| `currentImportDateWindow` | 2764 | Run the current import date window workflow for the browser application. | `importTempDeliveryFolder` |
| `parseDateKey` | 2779 | Normalize the parse date key workflow using the existing shared UI state. | `activeRecentImports`, `deliveryListIsInAdminWindow`, `filterListsByOverviewRange` |
| `filterListsByOverviewRange` | 2790 | Run the filter lists by overview range workflow for the browser application. | `homeStatisticsRangeParts`, `openHomeStatisticsReport`, `renderHome`, `renderStatisticsChartModal`, `statisticsChartDataset` |
| `latestDeliveryDate` | 2810 | Run the latest delivery date workflow for the browser application. | `dashboardDateKey` |
| `dashboardDateKey` | 2820 | Run the dashboard date key workflow for the browser application. | `ids`, `renderBayRouteFlow`, `renderPrintOptionStages`, `renderTodayProgress`, `wireEvents` |
| `progressPercent` | 2830 | Run the progress percent workflow for the browser application. | `deliveryListCard`, `renderTodayProgress` |
| `formatPercent` | 2839 | Normalize the format percent workflow using the existing shared UI state. | `deliveryListCard`, `openHomeStatisticsReport`, `renderCounts`, `renderHome`, `renderHomeStatistics`, `renderHomeStatsChart`, `renderStackedProgress`, `renderTodayProgress` (+3 more) |
| `stageCategory` | 2848 | Run the stage category workflow for the browser application. | `aggregateListStats`, `deliveryListCard`, `homeStageBreakdown`, `printListIsFullCoverage`, `printStageOptionLabel`, `priorityListsIncludeIndianTrail`, `renderBayRouteFlow`, `renderPrintOptionStages` (+6 more) |
| `stageLabel` | 2863 | Run the stage label workflow for the browser application. | `deliveryListCard`, `homeStageBreakdown`, `normalizeLookup`, `openRushNotificationList`, `renderHomeStageFilter`, `renderTodayProgress`, `showRushAlert`, `stageProgressSegments` (+1 more) |
| `priorityListsIncludeIndianTrail` | 2878 | Run the priority lists include indian trail workflow for the browser application. | `normalizeLookup`, `showRushAlert` |
| `slugify` | 2887 | Run the slugify workflow for the browser application. | `checkedForEntry`, `renderRackSetCard` |
| `uniqueText` | 2899 | Run the unique text workflow for the browser application. | `addStationFromInput`, `ids`, `loadLocalStations`, `loadStations`, `manualEditProductOptions`, `removeStation`, `renderHomeStageFilter`, `renderStationOptions` (+1 more) |
| `listsByDeliveryDate` | 2916 | Run the lists by delivery date workflow for the browser application. | `activeRecentImports`, `deliveryListAdminRows`, `openPrintOptions`, `renderAdminDeleteControls`, `renderDeliveryListSelect`, `renderHome`, `wireEvents` |
| `stageSort` | 2936 | Run the stage sort workflow for the browser application. | `deliveryListAdminRows`, `listsByDeliveryDate`, `manualEditStageListsForCurrentDelivery`, `printCountSourceLists`, `renderPrintOptionStages`, `renderTodayProgress`, `stageSortForRow` |
| `selectedDeliveryDate` | 2945 | Run the selected delivery date workflow for the browser application. | `ids`, `openPrintOptions`, `renderDeliveryListSelect`, `renderPrintOptionStages` |
| `hasPermission` | 2954 | Run the has permission workflow for the browser application. | `applyPermissionUi`, `bayEventMoveControlHtml`, `canAssignRackLocation`, `hasAnyPermission`, `ids`, `loadHomeReportSummary`, `maybeShowStaleBayAlert`, `openAdminModal` (+21 more) |
| `hasAnyPermission` | 2964 | Run the has any permission workflow for the browser application. | `applyPermissionUi`, `refreshBayMapPage`, `refreshRacksPage`, `showPage` |
| `setControlAllowed` | 2973 | Update the set control allowed workflow using the existing shared UI state. | `applyPermissionUi` |
| `userAssignedStations` | 2985 | Run the user assigned stations workflow for the browser application. | `renderAdminUsersTable`, `renderStationOptions`, `userAssignedStation`, `userAssignedStationLabel` |
| `userAssignedStation` | 3001 | Run the user assigned station workflow for the browser application. | `applyPermissionUi`, `currentScanStation`, `renderAdminUsersTable` |
| `userAssignedStationLabel` | 3010 | Run the user assigned station label workflow for the browser application. | `renderStationOptions` |
| `currentScanStation` | 3021 | Run the current scan station workflow for the browser application. | `applyPermissionUi`, `processScanInternal`, `requestContext` |
| `requestContext` | 3030 | Run the request context workflow for the browser application. | `addBaysFromForm`, `addBaysToEditorGroup`, `addSpacerBay`, `applyBayLayoutSnapshot`, `clearManagedItem`, `confirmBayLayoutDraft`, `createBayEditorGroup`, `deleteAdminDeliveryDateByDate` (+19 more) |
| `showImportStatusLoading` | 3042 | Open the show import status loading workflow using the existing shared UI state. | `importTempDeliveryFolder` |
| `showImportStatusResult` | 3061 | Open the show import status result workflow using the existing shared UI state. | — |
| `waitForNextPaint` | 3082 | Run the wait for next paint workflow for the browser application. | `importTempDeliveryFolder` |
| `updateModalScrollLock` | 3095 | Update the update modal scroll lock workflow using the existing shared UI state. | `acknowledgeRushAndOpen`, `close`, `closeActionFeedback`, `closeAdminModal`, `closeBayEditorPanel`, `closeEmailDraftPreview`, `closeInTransitManifest`, `closeManageItemsPanel` (+19 more) |
| `fetchJson` | 3120 | Load the fetch JSON workflow using the existing shared UI state. | `acknowledgeUserNotification`, `activateList`, `addBaysFromForm`, `addBaysToEditorGroup`, `addSpacerBay`, `addStationFromInput`, `applyBayLayoutSnapshot`, `assignLineItemToRack` (+85 more) |
| `detectBackend` | 3152 | Run the detect backend workflow for the browser application. | `init` |
| `showLogin` | 3166 | Open the show login workflow using the existing shared UI state. | `fetchJson`, `init`, `logout` |
| `hideLogin` | 3182 | Close the hide login workflow using the existing shared UI state. | `loadSession`, `login` |
| `loadSession` | 3198 | Load the load session workflow using the existing shared UI state. | `init` |
| `login` | 3215 | Run the login workflow for the browser application. | `wireEvents` |
| `showPasswordResetPanel` | 3233 | Open the show password reset panel workflow using the existing shared UI state. | `confirmPasswordReset`, `wireEvents` |
| `setPasswordResetMessage` | 3254 | Update the set password reset message workflow using the existing shared UI state. | `requestPasswordResetCode`, `wireEvents` |
| `requestPasswordResetCode` | 3265 | Run the request password reset code workflow for the browser application. | `wireEvents` |
| `confirmPasswordReset` | 3283 | Run the confirm password reset workflow for the browser application. | `wireEvents` |
| `logout` | 3308 | Run the logout workflow for the browser application. | `wireEvents` |
| `cleanBarcode` | 3325 | Run the clean barcode workflow for the browser application. | `recoverScan` |
| `digitsOnly` | 3341 | Run the digits only workflow for the browser application. | `recoverScan`, `submitManualBayAssign`, `submitManualBayScan`, `submitManualScan` |
| `canonicalRouteDesignation` | 3354 | Run the canonical route designation workflow for the browser application. | `inferredRoute` |
| `hasToken` | 3375 | Run the has token workflow for the browser application. | — |
| `inferredRoute` | 3403 | Run the inferred route workflow for the browser application. | `routeCategory`, `routeLabel` |
| `routeCategory` | 3425 | Run the route category workflow for the browser application. | `filterItemsForProfile`, `filteredItems`, `isCpuItem`, `renderCounts` |
| `routeLabel` | 3438 | Run the route label workflow for the browser application. | `renderItemRow`, `renderMobileCards` |
| `isCpuItem` | 3451 | Run the is CPU item workflow for the browser application. | — |
| `filterItemsForProfile` | 3460 | Run the filter items for profile workflow for the browser application. | `createDemoLists` |
| `cloneItems` | 3473 | Run the clone items workflow for the browser application. | `applyBackendPayload`, `createDemoLists`, `ensurePrintListDetails`, `setActiveList` |
| `createDemoLists` | 3496 | Create the create demo lists workflow using the existing shared UI state. | `init` |
| `loadLocalStations` | 3537 | Load the load local stations workflow using the existing shared UI state. | `init`, `loadStations` |
| `saveLocalStations` | 3551 | Run the save local stations workflow for the browser application. | `addStationFromInput` |
| `renderStationOptions` | 3560 | Render the render station options workflow using the existing shared UI state. | `addStationFromInput`, `applyBackendPayload`, `ids`, `init`, `loadStations`, `removeStation`, `setActiveList` |
| `loadStations` | 3591 | Load the load stations workflow using the existing shared UI state. | `loadAuthenticatedApp` |
| `addStationFromInput` | 3606 | Create the add station from input workflow using the existing shared UI state. | `ids`, `wireEvents` |
| `removeStation` | 3632 | Remove the remove station workflow using the existing shared UI state. | `ids` |
| `applyBackendPayload` | 3648 | Update the apply backend payload workflow using the existing shared UI state. | `activateList`, `assignLineItemToRack`, `deleteManualLineItem`, `processScanInternal`, `resetAdminScansForList`, `resetState`, `wireEvents` |
| `loadDeliveryLists` | 3664 | Load the load delivery lists workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteManualLineItem`, `deleteSelectedDeliveryList`, `ids`, `loadAuthenticatedApp`, `resetAdminScansForDate`, `resetAdminScansForList` (+1 more) |
| `setActiveList` | 3681 | Update the set active list workflow using the existing shared UI state. | `activateList` |
| `activateList` | 3705 | Run the activate list workflow for the browser application. | `assignLineItemToRack`, `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteSelectedDeliveryList`, `ids`, `importTempDeliveryFolder`, `loadDeliveryLists`, `openRushNotificationList` (+5 more) |
| `storageKey` | 3738 | Run the storage key workflow for the browser application. | `restoreState`, `saveState` |
| `saveState` | 3747 | Run the save state workflow for the browser application. | `clearSelectedLineItem`, `ids`, `processLocalScan`, `resetState` |
| `restoreState` | 3764 | Run the restore state workflow for the browser application. | `setActiveList` |
| `itemStatus` | 3787 | Run the item status workflow for the browser application. | `filteredItems`, `getStats`, `renderItemRow`, `renderMobileCards`, `unresolvedPriorityItems`, `unresolvedRemakeItems`, `unresolvedRushItems` |
| `itemText` | 3798 | Run the item text workflow for the browser application. | — |
| `isRemakeItem` | 3807 | Run the is remake item workflow for the browser application. | `filteredItems`, `isRemakeOrRush`, `openSdiPanel`, `renderItemRow`, `renderSdiCurrentList`, `selectedRangeRemakeStats`, `transitManifestRowHtml`, `unresolvedRemakeItems` |
| `isRushItem` | 3816 | Run the is rush item workflow for the browser application. | `filteredItems`, `isRemakeOrRush`, `openSdiPanel`, `renderItemRow`, `renderSdiCurrentList`, `transitManifestRowHtml`, `unresolvedRushItems` |
| `isRemakeOrRush` | 3825 | Run the is remake or rush workflow for the browser application. | `filteredItems`, `unresolvedPriorityItems` |
| `isNewOrUpdatedItem` | 3834 | Run the is new or updated item workflow for the browser application. | `filteredItems`, `renderItemRow` |
| `hasScanError` | 3843 | Run the has scan error workflow for the browser application. | `filteredItems`, `renderItemRow` |
| `itemPieceQty` | 3852 | Run the item piece qty workflow for the browser application. | `addEntry`, `glassQuantitiesForStatistics`, `itemScannedPieceQty`, `pieceCount`, `selectedRangeRemakeStats`, `unscannedPieceCount` |
| `itemScannedPieceQty` | 3861 | Run the item scanned piece qty workflow for the browser application. | `ensurePrintListDetails`, `getStats`, `itemCanShowRackLocationDropdown`, `unscannedPieceCount` |
| `pieceCount` | 3870 | Run the piece count workflow for the browser application. | `ensurePrintListDetails`, `getStats`, `renderCounts` |
| `unscannedPieceCount` | 3879 | Run the unscanned piece count workflow for the browser application. | `getStats`, `renderCounts` |
| `unresolvedPriorityItems` | 3888 | Run the unresolved priority items workflow for the browser application. | — |
| `unresolvedRemakeItems` | 3897 | Run the unresolved remake items workflow for the browser application. | — |
| `unresolvedRushItems` | 3906 | Run the unresolved rush items workflow for the browser application. | — |
| `scanFlash` | 3915 | Process the scan flash workflow using the existing shared UI state. | `processLocalScan`, `processScanInternal`, `runBayScan`, `showInlineError`, `updateBayScanModeUi`, `wireEvents` |
| `getStats` | 3928 | Resolve the get stats workflow using the existing shared UI state. | `renderCounts`, `renderMobileCards` |
| `filteredItems` | 3948 | Run the filtered items workflow for the browser application. | `getPagedItems` |
| `groupItemsByGlass` | 3983 | Run the group items by glass workflow for the browser application. | `getPagedItems` |
| `getPagedItems` | 3998 | Resolve the get paged items workflow using the existing shared UI state. | `renderMobileCards`, `renderTable` |
| `stageVerb` | 4038 | Run the stage verb workflow for the browser application. | `renderCounts`, `renderProcessState` |
| `renderProcessState` | 4053 | Render the render process state workflow using the existing shared UI state. | `renderItemRow` |
| `locationLabel` | 4062 | Run the location label workflow for the browser application. | `renderItemRow` |
| `clearSelectedLineItem` | 4079 | Remove the clear selected line item workflow using the existing shared UI state. | `wireEvents` |
| `canAssignRackLocation` | 4091 | Run the can assign rack location workflow for the browser application. | `ids`, `itemCanShowRackLocationDropdown` |
| `rackStatusValue` | 4105 | Run the rack status value workflow for the browser application. | `rackIsLockedForLineAssignment` |
| `rackIsLockedForLineAssignment` | 4114 | Run the rack is locked for line assignment workflow for the browser application. | `assignableRacks`, `itemCanShowRackLocationDropdown` |
| `rackForCode` | 4123 | Run the rack for code workflow for the browser application. | `itemCanShowRackLocationDropdown` |
| `itemCanShowRackLocationDropdown` | 4134 | Run the item can show rack location dropdown workflow for the browser application. | `rackLocationDropdown` |
| `locationBadgeClass` | 4150 | Run the location badge class workflow for the browser application. | `rackLocationDropdown` |
| `rackLocationDropdown` | 4168 | Run the rack location dropdown workflow for the browser application. | `renderItemRow` |
| `assignableRacks` | 4179 | Run the assignable racks workflow for the browser application. | — |
| `renderCounts` | 4198 | Render the render counts workflow using the existing shared UI state. | `renderScanPage` |
| `renderPagers` | 4316 | Render the render pagers workflow using the existing shared UI state. | `renderTable` |
| `render` | 4324 | Render the render workflow using the existing shared UI state. | — |
| `glassTypeLabel` | 4352 | Run the glass type label workflow for the browser application. | `addEntry`, `filteredItems`, `glassQuantitiesForStatistics`, `groupItemsByGlass`, `renderCounts`, `transitManifestRackGroups` |
| `renderItemRow` | 4361 | Render the render item row workflow using the existing shared UI state. | — |
| `renderTable` | 4406 | Render the render table workflow using the existing shared UI state. | `renderScanPage` |
| `stagingLists` | 4441 | Run the staging lists workflow for the browser application. | `renderRackSelects` |
| `refreshRacksPage` | 4450 | Load the refresh racks page workflow using the existing shared UI state. | `showPage` |
| `renderRackSelects` | 4465 | Render the render rack selects workflow using the existing shared UI state. | `renderRacksPage` |
| `rackGroupLabel` | 4491 | Run the rack group label workflow for the browser application. | `groupedRackOptionsHtml`, `rackManagerModalHtml`, `racks`, `wireEvents` |
| `groupedRackOptionsHtml` | 4500 | Run the grouped rack options HTML workflow for the browser application. | `assignableRacks`, `renderRackSelects`, `renderScanRackTools` |
| `rackCodeForScan` | 4538 | Run the rack code for scan workflow for the browser application. | `printSelectedRackPackingSlip`, `processScanInternal`, `racks`, `wireEvents` |
| `isTruckRack` | 4548 | Run the is truck rack workflow for the browser application. | `manualEditLocationOptions`, `printSelectedRackPackingSlip`, `rackManagerModalHtml`, `racks` |
| `nextTruckRackDefaults` | 4557 | Run the next truck rack defaults workflow for the browser application. | `ids` |
| `rackIsReceived` | 4574 | Run the rack is received workflow for the browser application. | `outboundRackStatusMeta`, `rackHasMoveOpen`, `rackStatusClassName`, `rackStatusLabel`, `rackVisualClass`, `renderRackBoardCard`, `renderSelectedRackDetails` |
| `rackStatusLabel` | 4583 | Run the rack status label workflow for the browser application. | `manualEditLocationOptions`, `rackManagerModalHtml`, `rackOptionLabel`, `rackStatusText` |
| `rackStatusClassName` | 4598 | Run the rack status class name workflow for the browser application. | `rackComputedStatus`, `rackStatusClass` |
| `rackOptionLabel` | 4613 | Run the rack option label workflow for the browser application. | `groupedRackOptionsHtml`, `racks`, `renderRackItem` |
| `rackDestinationLabel` | 4625 | Run the rack destination label workflow for the browser application. | `chooseRackDestination`, `outboundRackStatusMeta`, `rackDestinationClass`, `renderRackBoardCard`, `showOutboundRackTransitPrompt` |
| `rackDestinationClass` | 4639 | Run the rack destination class workflow for the browser application. | `renderRackBoardCard` |
| `rackVisualClass` | 4652 | Run the rack visual class workflow for the browser application. | `rackHasMoveOpen`, `renderRackBoardCard` |
| `rackComputedStatus` | 4666 | Run the rack computed status workflow for the browser application. | `filteredSortedRacks` |
| `rackSortNumber` | 4675 | Run the rack sort number workflow for the browser application. | `racks` |
| `filteredSortedRacks` | 4685 | Run the filtered sorted racks workflow for the browser application. | `renderRackBoardGroup` |
| `renderRacksPage` | 4714 | Render the render racks page workflow using the existing shared UI state. | `assignLineItemToRack`, `clearRack`, `clearRackItem`, `completeRack`, `createRackSet`, `deleteRackDefinition`, `deleteRackSet`, `markRackNotOnTheWay` (+10 more) |
| `renderRackItem` | 4754 | Render the render rack item workflow using the existing shared UI state. | `renderRackItems` |
| `renderRackItems` | 4826 | Render the render rack items workflow using the existing shared UI state. | `rackHasMoveOpen`, `renderSelectedRackDetails` |
| `renderRack` | 4878 | Render the render rack workflow using the existing shared UI state. | — |
| `rackHasMoveOpen` | 4889 | Run the rack has move open workflow for the browser application. | — |
| `renderRackColumnActions` | 4954 | Render the render rack column actions workflow using the existing shared UI state. | `renderRackBoardGroup` |
| `rackStatusText` | 4989 | Run the rack status text workflow for the browser application. | `renderRackBoardCard`, `renderSelectedRackDetails` |
| `rackStatusClass` | 4996 | Run the rack status class workflow for the browser application. | `renderRackBoardCard`, `renderSelectedRackDetails` |
| `renderRackBoardCard` | 5003 | Render the render rack board card workflow using the existing shared UI state. | — |
| `renderRackBoardGroup` | 5050 | Render the render rack board group workflow using the existing shared UI state. | — |
| `renderRackSetCard` | 5108 | Render the render rack set card workflow using the existing shared UI state. | — |
| `renderSelectedRackDetails` | 5139 | Render the render selected rack details workflow using the existing shared UI state. | — |
| `showRackDestinationOverrideDialog` | 5262 | Open the show rack destination override dialog workflow using the existing shared UI state. | `processScanInternal`, `submitRackScan` |
| `submitRackScan` | 5291 | Process the submit rack scan workflow using the existing shared UI state. | `wireEvents` |
| `chooseRackDestination` | 5330 | Run the choose rack destination workflow for the browser application. | — |
| `close` | 5364 | Close the close workflow using the existing shared UI state. | `notifyPrintComplete`, `submit` |
| `completeRack` | 5391 | Run the complete rack workflow for the browser application. | `wireEvents` |
| `uncompleteRack` | 5405 | Run the uncomplete rack workflow for the browser application. | `wireEvents` |
| `returnRack` | 5418 | Run the return rack workflow for the browser application. | `wireEvents` |
| `markRackNotOnTheWay` | 5449 | Run the mark rack not on the way workflow for the browser application. | `wireEvents` |
| `assignLineItemToRack` | 5474 | Run the assign line item to rack workflow for the browser application. | `wireEvents` |
| `clearRack` | 5501 | Remove the clear rack workflow using the existing shared UI state. | `wireEvents` |
| `clearRackSet` | 5527 | Remove the clear rack set workflow using the existing shared UI state. | `wireEvents` |
| `racks` | 5533 | Run the racks workflow for the browser application. | — |
| `moveRackItem` | 5568 | Run the move rack item workflow for the browser application. | `wireEvents` |
| `clearRackItem` | 5594 | Remove the clear rack item workflow using the existing shared UI state. | `wireEvents` |
| `rackPackingListUrl` | 5614 | Run the rack packing list URL workflow for the browser application. | `printSelectedRackPackingSlip`, `wireEvents` |
| `printSelectedRackPackingSlip` | 5624 | Run the print selected rack packing slip workflow for the browser application. | `wireEvents` |
| `saveRackDefinition` | 5642 | Run the save rack definition workflow for the browser application. | `wireEvents` |
| `selectedRackManagerRack` | 5663 | Run the selected rack manager rack workflow for the browser application. | `populateRackManagerQuickEdit`, `rackManagerModalHtml` |
| `populateRackManagerQuickEdit` | 5672 | Run the populate rack manager quick edit workflow for the browser application. | `wireEvents` |
| `saveRackQuickEdit` | 5691 | Run the save rack quick edit workflow for the browser application. | `wireEvents` |
| `deleteRackDefinition` | 5722 | Remove the delete rack definition workflow using the existing shared UI state. | `ids`, `wireEvents` |
| `createRackSet` | 5748 | Create the create rack set workflow using the existing shared UI state. | `wireEvents` |
| `openRackForm` | 5774 | Open the open rack form workflow using the existing shared UI state. | `ids`, `wireEvents` |
| `openRackSetForm` | 5786 | Open the open rack set form workflow using the existing shared UI state. | `ids`, `wireEvents` |
| `deleteRackSet` | 5804 | Remove the delete rack set workflow using the existing shared UI state. | `ids`, `wireEvents` |
| `renderMobileCards` | 5831 | Render the render mobile cards workflow using the existing shared UI state. | `renderScanPage` |
| `scanEntryEventLabel` | 5875 | Process the scan entry event label workflow using the existing shared UI state. | `recentScansModalHtml`, `renderRecent` |
| `scanEntryDeliveryDateHint` | 5893 | Process the scan entry delivery date hint workflow using the existing shared UI state. | `scanEntryCompactMessage`, `scanEntryFullDetail` |
| `scanEntryCompactMessage` | 5912 | Process the scan entry compact message workflow using the existing shared UI state. | `recentScansModalHtml`, `renderRecent`, `setLastScan` |
| `scanEntryFullDetail` | 5940 | Process the scan entry full detail workflow using the existing shared UI state. | `recentScansModalHtml` |
| `scanEntryRowClass` | 5964 | Process the scan entry row class workflow using the existing shared UI state. | `recentScansModalHtml`, `renderRecent` |
| `setLastScan` | 5974 | Update the set last scan workflow using the existing shared UI state. | `renderLastScan` |
| `renderLastScan` | 5997 | Render the render last scan workflow using the existing shared UI state. | `renderScanPage` |
| `sameScanEntry` | 6017 | Run the same scan entry workflow for the browser application. | `recentRowsExcludingCurrentLastScan` |
| `scanEntryIsManual` | 6032 | Process the scan entry is manual workflow using the existing shared UI state. | `scanEntryCompactMessage`, `scanEntryRowClass`, `setLastScan` |
| `mainScanRecentLimit` | 6041 | Run the main scan recent limit workflow for the browser application. | `recentRowsExcludingCurrentLastScan`, `renderRecent` |
| `recentRowsExcludingCurrentLastScan` | 6050 | Run the recent rows excluding current last scan workflow for the browser application. | `renderRecent` |
| `renderRecent` | 6062 | Render the render recent workflow using the existing shared UI state. | `renderScanPage`, `syncFullscreenControl` |
| `recentScansModalHtml` | 6094 | Run the recent scans modal HTML workflow for the browser application. | `adminModalContent` |
| `renderMeta` | 6165 | Render the render meta workflow using the existing shared UI state. | `renderScanPage` |
| `renderDeliveryListSelect` | 6184 | Render the render delivery list select workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteSelectedDeliveryList`, `loadDeliveryLists`, `renderMeta`, `resetAdminScansForDate` |
| `stageLists` | 6199 | Run the stage lists workflow for the browser application. | — |
| `applyPermissionUi` | 6218 | Update the apply permission UI workflow using the existing shared UI state. | `renderHome`, `renderScanPage` |
| `renderScanPage` | 6267 | Render the render scan page workflow using the existing shared UI state. | `activateList`, `assignLineItemToRack`, `clearSelectedLineItem`, `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteManualLineItem`, `deleteSelectedDeliveryList`, `ids` (+9 more) |
| `isStagingScanContext` | 6286 | Run the is staging scan context workflow for the browser application. | `canAssignRackLocation`, `processScanInternal`, `renderScanRackTools` |
| `isOutboundScanContext` | 6295 | Run the is outbound scan context workflow for the browser application. | `processScanInternal`, `renderOutboundRackStatusTools` |
| `ensureRacksLoaded` | 6304 | Run the ensure racks loaded workflow for the browser application. | `deleteRackSet`, `ids`, `processScanInternal`, `renderOutboundRackStatusTools`, `renderScanRackTools`, `showOutboundOverrideDialog`, `wireEvents` |
| `renderScanRackTools` | 6318 | Render the render scan rack tools workflow using the existing shared UI state. | `clearRackItem`, `completeRack`, `createRackSet`, `deleteRackDefinition`, `deleteRackSet`, `ensureRacksLoaded`, `markRackNotOnTheWay`, `racks` (+6 more) |
| `outboundRackStatusMeta` | 6372 | Run the outbound rack status meta workflow for the browser application. | `outboundRackStatusOptionsHtml`, `renderOutboundRackStatusTools` |
| `outboundRackStatusOptionsHtml` | 6415 | Run the outbound rack status options HTML workflow for the browser application. | `renderOutboundRackStatusTools` |
| `renderOutboundRackStatusTools` | 6445 | Render the render outbound rack status tools workflow using the existing shared UI state. | `ensureRacksLoaded`, `renderScanPage`, `wireEvents` |
| `isIndianTrailScanContext` | 6483 | Run the is indian trail scan context workflow for the browser application. | `scanBayOverrideVisible` |
| `renderManualAssignTools` | 6492 | Render the render manual assign tools workflow using the existing shared UI state. | `renderScanPage` |
| `ensureScanBayOverrideBays` | 6503 | Run the ensure scan bay override bays workflow for the browser application. | `renderScanBayOverrideTools`, `showIndianTrailOutboundReceiveOverride`, `showIndianTrailPlacementPrompt` |
| `scanBayOverrideVisible` | 6515 | Process the scan bay override visible workflow using the existing shared UI state. | `renderScanBayOverrideTools` |
| `bayOverrideGroupLabel` | 6524 | Run the bay override group label workflow for the browser application. | `indianTrailBayOptionsHtml`, `renderScanBayOverrideTools` |
| `bayOverrideSort` | 6533 | Run the bay override sort workflow for the browser application. | — |
| `renderScanBayOverrideTools` | 6544 | Render the render scan bay override tools workflow using the existing shared UI state. | `ensureScanBayOverrideBays`, `ids`, `renderScanPage`, `wireEvents` |
| `compatibleBayCandidates` | 6617 | Run the compatible bay candidates workflow for the browser application. | `submitManualBayAssign` |
| `submitManualBayAssign` | 6636 | Process the submit manual bay assign workflow using the existing shared UI state. | `wireEvents` |
| `miniStat` | 6670 | Run the mini stat workflow for the browser application. | `lookupManagerModalHtml`, `refreshAdminPage`, `renderBayMapPage`, `renderHomeStatistics`, `renderManageItemsPanel`, `renderRacksPage` |
| `aggregateListStats` | 6679 | Run the aggregate list stats workflow for the browser application. | `openHomeStatisticsReport`, `renderHome`, `statisticsChartKpiHtml` |
| `homeStageBreakdown` | 6709 | Run the home stage breakdown workflow for the browser application. | `openHomeStatisticsReport`, `renderHomeStatistics`, `statisticsChartDataset` |
| `homeStatisticsRangeParts` | 6736 | Run the home statistics range parts workflow for the browser application. | `homeStatisticsRangeLabel`, `renderHomeStatistics`, `renderMonthlyRemakes`, `renderStatisticsChartModal` |
| `homeStatisticsRangeLabel` | 6748 | Run the home statistics range label workflow for the browser application. | `renderStatisticsChartModal` |
| `homeReportDateParams` | 6758 | Run the home report date params workflow for the browser application. | `loadHomeReportSummary` |
| `reportActionCount` | 6775 | Run the report action count workflow for the browser application. | `renderHomeStatistics` |
| `glassQuantitiesForStatistics` | 6786 | Run the glass quantities for statistics workflow for the browser application. | `openHomeStatisticsReport`, `renderHomeStatsChart`, `statisticsChartDataset` |
| `renderHomeStatsChart` | 6818 | Render the render home stats chart workflow using the existing shared UI state. | `renderHomeStatistics` |
| `statisticsChartKpiHtml` | 6895 | Run the statistics chart kpi HTML workflow for the browser application. | `renderStatisticsChartModal` |
| `successfulScans` | 6904 | Run the successful scans workflow for the browser application. | — |
| `statisticsChartListLabel` | 6933 | Run the statistics chart list label workflow for the browser application. | `statisticsChartDataset` |
| `statisticsChartDataset` | 6943 | Run the statistics chart dataset workflow for the browser application. | `renderStatisticsChartModal` |
| `filteredStatisticsChartEntries` | 7111 | Run the filtered statistics chart entries workflow for the browser application. | `renderStatisticsChartModal` |
| `entries` | 7121 | Run the entries workflow for the browser application. | `applyBayLayoutDraft`, `bayGlassFilterOptions`, `bayPhysicalSections`, `bayTypeSections`, `checkedForEntry`, `glassQuantitiesForStatistics`, `groupItemsByGlass`, `groupedRackOptionsHtml` (+10 more) |
| `chartEntryColor` | 7148 | Run the chart entry color workflow for the browser application. | `statisticsBarChartHtml`, `statisticsDonutChartHtml` |
| `truncateChartLabel` | 7157 | Run the truncate chart label workflow for the browser application. | `statisticsBarChartHtml` |
| `statisticsChartSelectionHtml` | 7167 | Run the statistics chart selection HTML workflow for the browser application. | `renderStatisticsChartModal` |
| `statisticsBarChartHtml` | 7188 | Run the statistics bar chart HTML workflow for the browser application. | `renderStatisticsChartModal` |
| `statisticsDonutChartHtml` | 7243 | Run the statistics donut chart HTML workflow for the browser application. | `renderStatisticsChartModal` |
| `renderStatisticsChartModal` | 7313 | Render the render statistics chart modal workflow using the existing shared UI state. | `openStatisticsChartModal`, `wireEvents` |
| `openStatisticsChartModal` | 7388 | Open the open statistics chart modal workflow using the existing shared UI state. | `wireEvents` |
| `closeStatisticsChartModal` | 7401 | Close the close statistics chart modal workflow using the existing shared UI state. | `wireEvents` |
| `selectedRangeRemakeStats` | 7412 | Run the selected range remake stats workflow for the browser application. | `renderMonthlyRemakes`, `statisticsChartDataset` |
| `renderMonthlyRemakes` | 7444 | Render the render monthly remakes workflow using the existing shared UI state. | `renderHomeStatistics` |
| `renderHomeStatistics` | 7464 | Render the render home statistics workflow using the existing shared UI state. | `renderHome` |
| `loadHomeReportSummary` | 7548 | Load the load home report summary workflow using the existing shared UI state. | `loadAuthenticatedApp`, `wireEvents` |
| `openHomeStatisticsReport` | 7565 | Open the open home statistics report workflow using the existing shared UI state. | `wireEvents` |
| `notifyPrintComplete` | 7654 | Run the notify print complete workflow for the browser application. | — |
| `stageProgressSegments` | 7689 | Run the stage progress segments workflow for the browser application. | `renderStackedProgress` |
| `progressWidth` | 7710 | Run the progress width workflow for the browser application. | `deliveryListCard`, `renderStackedProgress` |
| `renderStackedProgress` | 7720 | Render the render stacked progress workflow using the existing shared UI state. | `renderHome` |
| `filteredDeliveryLists` | 7739 | Run the filtered delivery lists workflow for the browser application. | `renderHome` |
| `deliveryListCard` | 7754 | Run the delivery list card workflow for the browser application. | `renderHome` |
| `renderTodayProgress` | 7788 | Render the render today progress workflow using the existing shared UI state. | `renderHome` |
| `renderHomeStageFilter` | 7824 | Render the render home stage filter workflow using the existing shared UI state. | `renderHome` |
| `renderHome` | 7846 | Render the render home workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteSelectedDeliveryList`, `ids`, `importTempDeliveryFolder`, `loadDeliveryLists`, `loadHomeReportSummary`, `resetAdminScansForDate` (+2 more) |
| `showPage` | 7923 | Open the show page workflow using the existing shared UI state. | `activateList`, `ids`, `init`, `loadAuthenticatedApp`, `openRushNotificationList` |
| `showOutboundOverrideDialog` | 7962 | Open the show outbound override dialog workflow using the existing shared UI state. | `processScanInternal` |
| `racks` | 7969 | Run the racks workflow for the browser application. | — |
| `close` | 8017 | Close the close workflow using the existing shared UI state. | `notifyPrintComplete`, `submit` |
| `availableIndianTrailBays` | 8052 | Run the available indian trail bays workflow for the browser application. | `bayEventMoveOptionsHtml`, `indianTrailBayOptionsHtml`, `showIndianTrailOutboundReceiveOverride`, `showIndianTrailPlacementPrompt` |
| `indianTrailBayOptionsHtml` | 8064 | Run the indian trail bay options HTML workflow for the browser application. | `showIndianTrailOutboundReceiveOverride`, `showIndianTrailPlacementPrompt` |
| `showIndianTrailOutboundReceiveOverride` | 8083 | Open the show indian trail outbound receive override workflow using the existing shared UI state. | `processScanInternal`, `runBayScan` |
| `close` | 8144 | Close the close workflow using the existing shared UI state. | `notifyPrintComplete`, `submit` |
| `closeTimedScanConfirmation` | 8177 | Close the close timed scan confirmation workflow using the existing shared UI state. | `closeIndianTrailPlacementPrompt`, `mountTimedScanConfirmation` |
| `mountTimedScanConfirmation` | 8192 | Run the mount timed scan confirmation workflow for the browser application. | `showIndianTrailPlacementPrompt`, `showOutboundRackTransitPrompt` |
| `closeIndianTrailPlacementPrompt` | 8232 | Close the close indian trail placement prompt workflow using the existing shared UI state. | `showIndianTrailPlacementPrompt` |
| `showOutboundRackTransitPrompt` | 8241 | Open the show outbound rack transit prompt workflow using the existing shared UI state. | `processScanInternal` |
| `showIndianTrailPlacementPrompt` | 8288 | Open the show indian trail placement prompt workflow using the existing shared UI state. | `processScanInternal`, `runBayScan` |
| `processScan` | 8379 | Run the process scan workflow for the browser application. | `acknowledgeRushAndOpen`, `close`, `processScanInternal`, `submitManualScan`, `wireEvents` |
| `cleanup` | 8387 | Run the cleanup workflow for the browser application. | — |
| `processScanInternal` | 8400 | Run the process scan internal workflow for the browser application. | `processScan` |
| `submitManualScan` | 8520 | Process the submit manual scan workflow using the existing shared UI state. | `wireEvents` |
| `processLocalScan` | 8538 | Run the process local scan workflow for the browser application. | `processScanInternal` |
| `buildIndexes` | 8587 | Build the build indexes workflow using the existing shared UI state. | `recoverScan` |
| `recoverScan` | 8608 | Run the recover scan workflow for the browser application. | `processLocalScan` |
| `resetState` | 8646 | Run the reset state workflow for the browser application. | — |
| `showInlineError` | 8670 | Open the show inline error workflow using the existing shared UI state. | `close`, `email`, `ids`, `launchManagedPrint`, `normalizeLookup`, `notifyPrintComplete`, `openAdminModal`, `openBayLayoutManager` (+18 more) |
| `showFloatingNotice` | 8685 | Open the show floating notice workflow using the existing shared UI state. | `acknowledgeRushAndOpen`, `addBaysFromForm`, `addBaysToEditorGroup`, `addSpacerBay`, `assignLineItemToRack`, `cancelBayLayoutDraft`, `close`, `closeBayLayoutManager` (+37 more) |
| `closeActionFeedback` | 8707 | Close the close action feedback workflow using the existing shared UI state. | `closeWithSecondary`, `showActionFeedback`, `wireEvents` |
| `showActionFeedback` | 8718 | Open the show action feedback workflow using the existing shared UI state. | `clearRack`, `normalizeLookup`, `racks`, `returnRack`, `showFullscreenRecoveryPrompt` |
| `closeWithSecondary` | 8770 | Close the close with secondary workflow using the existing shared UI state. | — |
| `rushNotificationIsBlocked` | 8795 | Run the rush notification is blocked workflow for the browser application. | `presentNextUserNotification`, `showRushAlert` |
| `acknowledgeUserNotification` | 8814 | Run the acknowledge user notification workflow for the browser application. | `acknowledgeRushAndOpen` |
| `rushNotificationTargetList` | 8828 | Run the rush notification target list workflow for the browser application. | `openRushNotificationList` |
| `openRushNotificationList` | 8855 | Open the open rush notification list workflow using the existing shared UI state. | `acknowledgeRushAndOpen` |
| `waitForActiveScanOperations` | 8881 | Run the wait for active scan operations workflow for the browser application. | `acknowledgeRushAndOpen` |
| `acknowledgeRushAndOpen` | 8893 | Run the acknowledge rush and open workflow for the browser application. | `showRushAlert` |
| `showRushAlert` | 8934 | Open the show rush alert workflow using the existing shared UI state. | `acknowledgeRushAndOpen`, `presentNextUserNotification` |
| `presentNextUserNotification` | 9013 | Run the present next user notification workflow for the browser application. | `acknowledgeRushAndOpen`, `cleanup`, `closeActionFeedback`, `pollUserNotifications`, `showPage` |
| `pollUserNotifications` | 9025 | Run the poll user notifications workflow for the browser application. | `showPage`, `startNotificationPolling`, `wireEvents` |
| `startNotificationPolling` | 9051 | Run the start notification polling workflow for the browser application. | `loadAuthenticatedApp` |
| `stopNotificationPolling` | 9064 | Run the stop notification polling workflow for the browser application. | `fetchJson`, `logout`, `startNotificationPolling` |
| `restoreFullscreenAfterManagedPrint` | 9078 | Run the restore fullscreen after managed print workflow for the browser application. | `afterPrint`, `finishManagedPrintSession` |
| `stopManagedPrintWindowWatch` | 9099 | Run the stop managed print window watch workflow for the browser application. | `finishManagedPrintSession`, `watchManagedPrintWindow` |
| `finishManagedPrintSession` | 9115 | Run the finish managed print session workflow for the browser application. | `checkManagedPrintWindowClosed`, `wireEvents` |
| `checkManagedPrintWindowClosed` | 9126 | Run the check managed print window closed workflow for the browser application. | `wireEvents` |
| `watchManagedPrintWindow` | 9147 | Run the watch managed print window workflow for the browser application. | `launchManagedPrint`, `notifyPrintComplete` |
| `launchManagedPrint` | 9158 | Run the launch managed print workflow for the browser application. | `ids`, `normalizeLookup`, `openPrintPackage`, `printSelectedRackPackingSlip`, `submitPrintOptions`, `updateBayScanModeUi`, `wireEvents` |
| `printCurrentPageManaged` | 9176 | Run the print current page managed workflow for the browser application. | `submitPrintOptions` |
| `afterPrint` | 9183 | Run the after print workflow for the browser application. | — |
| `runGlobalSearch` | 9196 | Run the run global search workflow for the browser application. | `wireEvents` |
| `globalSearchProcessClass` | 9213 | Run the global search process class workflow for the browser application. | `globalSearchStatusBadges` |
| `globalSearchStatusBadges` | 9234 | Run the global search status badges workflow for the browser application. | `renderGlobalSearchResults` |
| `renderGlobalSearchResults` | 9246 | Render the render global search results workflow using the existing shared UI state. | `runGlobalSearch` |
| `refreshBayMapPage` | 9288 | Load the refresh bay map page workflow using the existing shared UI state. | `applyBayLayoutSnapshot`, `clearManagedItem`, `confirmBayLayoutDraft`, `moveManagedItem`, `postBayAction`, `processScanInternal`, `refreshBayEditorAfter`, `runBayHistory` (+3 more) |
| `renderBayRouteFlow` | 9320 | Render the render bay route flow workflow using the existing shared UI state. | `refreshBayMapPage` |
| `transitManifestRowHtml` | 9432 | Run the transit manifest row HTML workflow for the browser application. | — |
| `transitRackDisplayName` | 9457 | Run the transit rack display name workflow for the browser application. | `transitManifestHtml` |
| `transitRackSortValue` | 9470 | Run the transit rack sort value workflow for the browser application. | `transitManifestRackGroups` |
| `transitManifestGlassTypeClass` | 9483 | Run the transit manifest glass type class workflow for the browser application. | `transitManifestRackGroups` |
| `transitManifestSourceRows` | 9501 | Run the transit manifest source rows workflow for the browser application. | `transitManifestHtml`, `transitManifestRackGroups` |
| `transitManifestRackGroups` | 9529 | Run the transit manifest rack groups workflow for the browser application. | `transitManifestHtml` |
| `transitRackIconClass` | 9609 | Run the transit rack icon class workflow for the browser application. | `transitManifestHtml` |
| `transitManifestHtml` | 9623 | Run the transit manifest HTML workflow for the browser application. | `openInTransitManifest` |
| `openInTransitManifest` | 9698 | Open the open in transit manifest workflow using the existing shared UI state. | `ids` |
| `closeInTransitManifest` | 9730 | Close the close in transit manifest workflow using the existing shared UI state. | `ids`, `openInTransitManifest` |
| `renderIndianTrailSummary` | 9740 | Render the render indian trail summary workflow using the existing shared UI state. | `refreshBayMapPage` |
| `bayMatchesFilter` | 9770 | Run the bay matches filter workflow for the browser application. | `countable`, `renderBayMapPage`, `renderBaySection`, `renderBaySlotButton` |
| `bayHasErrorState` | 9801 | Run the bay has error state workflow for the browser application. | `bayMatchesFilter`, `renderBaySection` |
| `filterOptionLabel` | 9822 | Run the filter option label workflow for the browser application. | `activeBayFilterChips` |
| `selectOptionLabel` | 9832 | Run the select option label workflow for the browser application. | `activeBayFilterChips` |
| `activeBayFilterChips` | 9843 | Run the active bay filter chips workflow for the browser application. | `renderBayFilterSummary` |
| `resetBayFilters` | 9861 | Run the reset bay filters workflow for the browser application. | — |
| `renderBayFilterSummary` | 9883 | Render the render bay filter summary workflow using the existing shared UI state. | `renderBayMapPage` |
| `countable` | 9893 | Run the countable workflow for the browser application. | — |
| `normalizeFilterValue` | 9924 | Normalize the normalize filter value workflow using the existing shared UI state. | `bayGlassFilterOptions`, `bayMatchesFilter` |
| `bayGlassLabel` | 9933 | Run the bay glass label workflow for the browser application. | `bayMatchesFilter` |
| `isWorkbookLegendCell` | 9943 | Run the is workbook legend cell workflow for the browser application. | — |
| `statusAbbreviation` | 9952 | Run the status abbreviation workflow for the browser application. | `renderBaySlotButton` |
| `bayCategoryKind` | 9971 | Run the bay category kind workflow for the browser application. | `bayLayoutSnapshot`, `bayMatchesFilter`, `bayOptionGroups`, `bayOverview`, `bayPhysicalSections`, `bayStatusKind`, `bayTypeSections`, `bays` (+6 more) |
| `bayCategoryLabel` | 9990 | Run the bay category label workflow for the browser application. | `bayTypeSections`, `renderBayLayoutGroupCard`, `renderBaySection`, `renderBaySidePanels`, `renderBaySlotButton` |
| `bayCategoryOrder` | 10011 | Run the bay category order workflow for the browser application. | `bayTypeSections` |
| `bayRackLabel` | 10020 | Run the bay rack label workflow for the browser application. | `bayPhysicalSections`, `bayTypeSections`, `collapseAllPhysicalBaySections`, `runBayAction` |
| `baySearchText` | 10029 | Run the bay search text workflow for the browser application. | `countable`, `renderBayMapPage`, `renderBaySection`, `renderBaySlotButton` |
| `bayPolicyKind` | 10046 | Run the bay policy kind workflow for the browser application. | `bayEditorBayRowMarkup`, `bayMatchesFilter`, `bayOverview`, `bayStatusKind`, `bayStatusLabel`, `bays`, `policies`, `renderBaySection` (+2 more) |
| `bayStatusKind` | 10062 | Run the bay status kind workflow for the browser application. | `bayMatchesFilter`, `bayOverview`, `bayStatusLabel`, `compatibleBayCandidates`, `renderBaySection`, `renderBaySidePanels`, `renderBaySlotButton`, `renderManageItemsPanel` |
| `bayStatusLabel` | 10080 | Run the bay status label workflow for the browser application. | `renderBaySidePanels` |
| `bayUtilization` | 10097 | Run the bay utilization workflow for the browser application. | `renderBaySlotButton` |
| `bayCategoryFilterOptions` | 10109 | Run the bay category filter options workflow for the browser application. | `activeBayFilterChips`, `renderBaySidePanels` |
| `bayGlassFilterOptions` | 10128 | Run the bay glass filter options workflow for the browser application. | `renderBaySidePanels` |
| `bayOverview` | 10144 | Run the bay overview workflow for the browser application. | `renderBayMapPage`, `renderIndianTrailSummary` |
| `bayGroupPolicySummary` | 10173 | Run the bay group policy summary workflow for the browser application. | `renderBaySection` |
| `bays` | 10179 | Run the bays workflow for the browser application. | — |
| `assignmentJobKey` | 10214 | Run the assignment job key workflow for the browser application. | `groupAssignmentsByJob` |
| `assignmentJobLabel` | 10225 | Run the assignment job label workflow for the browser application. | `groupAssignmentsByJob`, `renderBaySidePanels`, `renderManageItemsPanel` |
| `groupAssignmentsByJob` | 10234 | Run the group assignments by job workflow for the browser application. | `bayAssignmentRows`, `renderBaySidePanels`, `renderBaySlotButton` |
| `bayJobDetailForGroup` | 10271 | Run the bay job detail for group workflow for the browser application. | `renderBaySidePanels` |
| `selectedBayJobItemsHtml` | 10281 | Run the selected bay job items HTML workflow for the browser application. | `renderBaySidePanels` |
| `renderBaySlotButton` | 10311 | Render the render bay slot button workflow using the existing shared UI state. | `renderBaySection`, `renderBaySidePanels` |
| `bayTypeSections` | 10374 | Run the bay type sections workflow for the browser application. | `renderBaySidePanels` |
| `bayPhysicalSections` | 10416 | Run the bay physical sections workflow for the browser application. | `bayEditorGroups`, `bayLayoutColumns`, `bayOptionGroups`, `confirmBayLayoutDraft`, `holdAllBaySections`, `initializeBayLayoutDraft`, `insertBaySectionDraft`, `openBayEditorPanel` (+1 more) |
| `initializeBayLayoutDraft` | 10440 | Run the initialize bay layout draft workflow for the browser application. | `openBayLayoutManager`, `renderBayGrid` |
| `normalizedBayGridPositions` | 10467 | Normalize the normalized bay grid positions workflow using the existing shared UI state. | — |
| `renderBaySection` | 10486 | Render the render bay section workflow using the existing shared UI state. | `renderBayGrid` |
| `bayLayoutColumns` | 10527 | Run the bay layout columns workflow for the browser application. | `ids`, `insertBaySectionDraft`, `renderBayGrid`, `shiftBaySectionDraft` |
| `renderBayLayoutDropZone` | 10545 | Render the render bay layout drop zone workflow using the existing shared UI state. | `renderBayGrid` |
| `renderBayLayoutGroupCard` | 10562 | Render the render bay layout group card workflow using the existing shared UI state. | `renderBayGrid` |
| `insertBaySectionDraft` | 10600 | Run the insert bay section draft workflow for the browser application. | `ids`, `shiftBaySectionDraft` |
| `shiftBaySectionDraft` | 10643 | Run the shift bay section draft workflow for the browser application. | `updateBayScanModeUi` |
| `renderBayGrid` | 10684 | Render the render bay grid workflow using the existing shared UI state. | `renderBayMapPage` |
| `collapseAllPhysicalBaySections` | 10779 | Run the collapse all physical bay sections workflow for the browser application. | `ids`, `resetBayFilters`, `wireEvents` |
| `syncBaySectionState` | 10788 | Run the sync bay section state workflow for the browser application. | `animateBaySectionToggle`, `renderBayMapPage` |
| `animateBaySectionToggle` | 10800 | Run the animate bay section toggle workflow for the browser application. | `renderBayMapPage` |
| `renderBayMapPage` | 10844 | Render the render bay map page workflow using the existing shared UI state. | `addBaysFromForm`, `addSpacerBay`, `applyBayLayoutDraft`, `cancelBayLayoutDraft`, `closeBayLayoutManager`, `deleteSelectedBay`, `deleteSelectedBayGroup`, `holdAllBaySections` (+12 more) |
| `renderBaySidePanels` | 10887 | Render the render bay side panels workflow using the existing shared UI state. | `loadBayJobDetails`, `renderBayMapPage` |
| `loadStaleBayOrders` | 11060 | Load the load stale bay orders workflow using the existing shared UI state. | `maybeShowStaleBayAlert`, `runBayAction` |
| `maybeShowStaleBayAlert` | 11075 | Run the maybe show stale bay alert workflow for the browser application. | `refreshBayMapPage` |
| `openStaleBayPanel` | 11091 | Open the open stale bay panel workflow using the existing shared UI state. | `maybeShowStaleBayAlert`, `runBayAction` |
| `closeStaleBayPanel` | 11104 | Close the close stale bay panel workflow using the existing shared UI state. | `updateBayScanModeUi` |
| `renderStaleBayPanel` | 11115 | Render the render stale bay panel workflow using the existing shared UI state. | `openStaleBayPanel`, `snoozeStaleBayOrders` |
| `snoozeStaleBayOrders` | 11189 | Run the snooze stale bay orders workflow for the browser application. | `ids` |
| `renderBayLegend` | 11204 | Render the render bay legend workflow using the existing shared UI state. | — |
| `formatEventType` | 11227 | Normalize the format event type workflow using the existing shared UI state. | `openBayAllScansModal`, `renderBayLastScanCard`, `renderBayRecentActions` |
| `bayEventTone` | 11238 | Run the bay event tone workflow for the browser application. | `renderBayLastScanCard`, `renderBayRecentActions` |
| `bayEventMoveOptionsHtml` | 11250 | Run the bay event move options HTML workflow for the browser application. | `bayEventMoveControlHtml`, `renderBayLastScanCard` |
| `bayEventMoveControlHtml` | 11262 | Run the bay event move control HTML workflow for the browser application. | `openBayAllScansModal`, `renderBayRecentActions` |
| `renderBayLastScanCard` | 11298 | Render the render bay last scan card workflow using the existing shared UI state. | `renderBayRecentActions` |
| `renderBayRecentActions` | 11344 | Render the render bay recent actions workflow using the existing shared UI state. | `renderBayMapPage`, `wireEvents` |
| `scrollToBaySearchMatch` | 11375 | Run the scroll to bay search match workflow for the browser application. | `ids`, `wireEvents` |
| `selectedBay` | 11395 | Run the selected bay workflow for the browser application. | `addSpacerBay`, `deleteSelectedBayGroup`, `match`, `normalizeLookup`, `openSdiPanel`, `populateBayLayoutForm`, `renderBaySidePanels`, `requireSelectedBay` (+2 more) |
| `loadBayJobDetails` | 11404 | Load the load bay job details workflow using the existing shared UI state. | `refreshBayMapPage`, `selectBay` |
| `selectBay` | 11435 | Run the select bay workflow for the browser application. | `ids`, `updateBayScanModeUi` |
| `closeSelectedBayModal` | 11456 | Close the close selected bay modal workflow using the existing shared UI state. | `runBayAction`, `updateBayScanModeUi` |
| `requireSelectedBay` | 11467 | Run the require selected bay workflow for the browser application. | `runBayAction` |
| `postBayAction` | 11481 | Run the post bay action workflow for the browser application. | `ids`, `normalizeLookup`, `runBayAction`, `runBayScan`, `showIndianTrailPlacementPrompt`, `updateBayScanModeUi`, `wireEvents` |
| `pushBayHistory` | 11495 | Run the push bay history workflow for the browser application. | `runBayAction`, `runBayScan`, `updateBayScanModeUi` |
| `runBayHistory` | 11506 | Run the run bay history workflow for the browser application. | `updateBayScanModeUi` |
| `runBayScan` | 11525 | Run the run bay scan workflow for the browser application. | `submitBayScanOut`, `submitManualBayScan` |
| `submitBayScanOut` | 11603 | Process the submit bay scan out workflow using the existing shared UI state. | `wireEvents` |
| `submitManualBayScan` | 11617 | Process the submit manual bay scan workflow using the existing shared UI state. | `wireEvents` |
| `selectedBayAssignment` | 11636 | Run the selected bay assignment workflow for the browser application. | `match`, `openManageItemsPanel`, `openSdiPanel`, `submitSdi` |
| `assignmentById` | 11645 | Run the assignment by ID workflow for the browser application. | `openSdiPanel`, `runAssignmentAction`, `submitSdi` |
| `match` | 11653 | Run the match workflow for the browser application. | `bayTypeSections`, `rackSortNumber`, `scanEntryDeliveryDateHint`, `translateDynamicUiText`, `translatedUiValue` |
| `bayAssignmentRows` | 11665 | Run the bay assignment rows workflow for the browser application. | `renderManageItemsPanel`, `selectedManageItem` |
| `selectedManageItem` | 11682 | Run the selected manage item workflow for the browser application. | `clearManagedItem`, `moveManagedItem`, `renderManageItemsPanel`, `updateBayScanModeUi`, `useManagedBayForScanner` |
| `bayOptionGroups` | 11693 | Run the bay option groups workflow for the browser application. | `renderManageItemsPanel` |
| `renderManageItemsPanel` | 11711 | Render the render manage items panel workflow using the existing shared UI state. | `clearManagedItem`, `moveManagedItem`, `openManageItemsPanel`, `updateBayScanModeUi` |
| `openManageItemsPanel` | 11785 | Open the open manage items panel workflow using the existing shared UI state. | `runAssignmentAction`, `runBayAction` |
| `closeManageItemsPanel` | 11801 | Close the close manage items panel workflow using the existing shared UI state. | `updateBayScanModeUi`, `useManagedBayForScanner` |
| `moveManagedItem` | 11812 | Run the move managed item workflow for the browser application. | `updateBayScanModeUi` |
| `clearManagedItem` | 11835 | Remove the clear managed item workflow using the existing shared UI state. | `updateBayScanModeUi` |
| `useManagedBayForScanner` | 11864 | Run the use managed bay for scanner workflow for the browser application. | `updateBayScanModeUi` |
| `bayEditorGroups` | 11885 | Run the bay editor groups workflow for the browser application. | `bayEditorSelectedGroupObject`, `renderBayEditorPanel` |
| `bayEditorSelectedGroupObject` | 11894 | Run the bay editor selected group object workflow for the browser application. | `addBaysToEditorGroup`, `deleteBayEditorGroup`, `renderBayEditorPanel`, `saveBayEditorGroup` |
| `bayEditorPolicyForGroup` | 11905 | Run the bay editor policy for group workflow for the browser application. | `renderBayEditorPanel` |
| `policies` | 11911 | Run the policies workflow for the browser application. | — |
| `bayEditorStatusFromPolicy` | 11922 | Run the bay editor status from policy workflow for the browser application. | `saveBayEditorGroup`, `value` |
| `renderBayEditorPanel` | 11933 | Render the render bay editor panel workflow using the existing shared UI state. | `openBayEditorPanel`, `refreshBayEditorAfter`, `saveBayEditorGroup`, `updateBayScanModeUi` |
| `bayEditorNewGroupFormMarkup` | 12010 | Run the bay editor new group form markup workflow for the browser application. | `renderBayEditorPanel` |
| `bayEditorBayRowMarkup` | 12038 | Run the bay editor bay row markup workflow for the browser application. | `renderBayEditorPanel` |
| `openBayEditorPanel` | 12069 | Open the open bay editor panel workflow using the existing shared UI state. | `runBayAction`, `updateBayScanModeUi` |
| `closeBayEditorPanel` | 12083 | Close the close bay editor panel workflow using the existing shared UI state. | `updateBayScanModeUi` |
| `refreshBayEditorAfter` | 12094 | Load the refresh bay editor after workflow using the existing shared UI state. | `addBaysToEditorGroup`, `createBayEditorGroup`, `deleteBayEditorBay`, `deleteBayEditorGroup`, `value` |
| `saveBayEditorGroup` | 12105 | Run the save bay editor group workflow for the browser application. | — |
| `createBayEditorGroup` | 12145 | Create the create bay editor group workflow using the existing shared UI state. | — |
| `addBaysToEditorGroup` | 12167 | Create the add bays to editor group workflow using the existing shared UI state. | — |
| `deleteBayEditorGroup` | 12188 | Remove the delete bay editor group workflow using the existing shared UI state. | — |
| `saveBayEditorBay` | 12212 | Run the save bay editor bay workflow for the browser application. | `updateBayScanModeUi` |
| `value` | 12221 | Run the value workflow for the browser application. | — |
| `deleteBayEditorBay` | 12249 | Remove the delete bay editor bay workflow using the existing shared UI state. | `updateBayScanModeUi` |
| `openBayAllScansModal` | 12270 | Open the open bay all scans modal workflow using the existing shared UI state. | `updateBayScanModeUi`, `wireEvents` |
| `openSdiPanel` | 12307 | Open the open SDI panel workflow using the existing shared UI state. | `runAssignmentAction`, `runBayAction`, `updateBayScanModeUi` |
| `renderSdiCurrentList` | 12343 | Render the render SDI current list workflow using the existing shared UI state. | `openSdiPanel` |
| `closeSdiPanel` | 12373 | Close the close SDI panel workflow using the existing shared UI state. | `normalizeLookup`, `updateBayScanModeUi` |
| `submitSdi` | 12384 | Process the submit SDI workflow using the existing shared UI state. | `ids` |
| `normalizeLookup` | 12394 | Normalize the normalize lookup workflow using the existing shared UI state. | — |
| `runBayAction` | 12458 | Run the run bay action workflow for the browser application. | `ids`, `updateBayScanModeUi` |
| `renderBayLayoutSelect` | 12536 | Render the render bay layout select workflow using the existing shared UI state. | `addBaysFromForm`, `addSpacerBay`, `applyBayLayoutSnapshot`, `deleteSelectedBay`, `deleteSelectedBayGroup`, `moveBayToGroup`, `openBayLayoutManager`, `selectBay` |
| `populateBayLayoutForm` | 12550 | Run the populate bay layout form workflow for the browser application. | `addBaysFromForm`, `addSpacerBay`, `applyBayLayoutSnapshot`, `deleteSelectedBay`, `deleteSelectedBayGroup`, `ids`, `moveBayToGroup`, `openBayLayoutManager` (+1 more) |
| `openBayLayoutManager` | 12568 | Open the open bay layout manager workflow using the existing shared UI state. | `runBayAction` |
| `closeBayLayoutManager` | 12588 | Close the close bay layout manager workflow using the existing shared UI state. | `ids` |
| `holdBaySectionDraft` | 12606 | Run the hold bay section draft workflow for the browser application. | `ids` |
| `holdAllBaySections` | 12623 | Run the hold all bay sections workflow for the browser application. | `ids` |
| `applyBayLayoutDraft` | 12643 | Update the apply bay layout draft workflow using the existing shared UI state. | `runBayLayoutHistory` |
| `confirmBayLayoutDraft` | 12654 | Run the confirm bay layout draft workflow for the browser application. | `ids` |
| `cancelBayLayoutDraft` | 12689 | Run the cancel bay layout draft workflow for the browser application. | `ids` |
| `saveBayLayoutForm` | 12706 | Run the save bay layout form workflow for the browser application. | `ids` |
| `bayLayoutSnapshot` | 12731 | Run the bay layout snapshot workflow for the browser application. | `addSpacerBay`, `moveBayToGroup` |
| `applyBayLayoutSnapshot` | 12751 | Update the apply bay layout snapshot workflow using the existing shared UI state. | `runBayLayoutHistory` |
| `pushBayLayoutHistory` | 12768 | Run the push bay layout history workflow for the browser application. | `addSpacerBay`, `moveBayToGroup` |
| `runBayLayoutHistory` | 12779 | Run the run bay layout history workflow for the browser application. | `ids` |
| `moveBayToGroup` | 12803 | Run the move bay to group workflow for the browser application. | `ids` |
| `addBaysFromForm` | 12839 | Create the add bays from form workflow using the existing shared UI state. | — |
| `addSpacerBay` | 12863 | Create the add spacer bay workflow using the existing shared UI state. | — |
| `deleteSelectedBay` | 12901 | Remove the delete selected bay workflow using the existing shared UI state. | `ids` |
| `deleteSelectedBayGroup` | 12927 | Remove the delete selected bay group workflow using the existing shared UI state. | — |
| `openPrintPackage` | 12953 | Open the open print package workflow using the existing shared UI state. | — |
| `runAssignmentAction` | 12968 | Run the run assignment action workflow for the browser application. | `ids` |
| `selectedPrintStageInputs` | 12995 | Run the selected print stage inputs workflow for the browser application. | `selectedPrintListIds`, `updatePrintStageSelectState`, `wireEvents` |
| `selectedPrintListIds` | 13004 | Run the selected print list IDs workflow for the browser application. | `renderPrintGlassTypes`, `submitPrintOptions` |
| `updatePrintStageSelectState` | 13013 | Update the update print stage select state workflow using the existing shared UI state. | `renderPrintOptionStages`, `wireEvents` |
| `printGlassCategory` | 13031 | Run the print glass category workflow for the browser application. | `addEntry` |
| `printGlassCategorySort` | 13046 | Run the print glass category sort workflow for the browser application. | `addEntry` |
| `selectedPrintGlassInputs` | 13055 | Run the selected print glass inputs workflow for the browser application. | `checkedForEntry`, `renderPrintGlassTypes`, `updatePrintGlassSelectState` |
| `updatePrintGlassSelectState` | 13064 | Update the update print glass select state workflow using the existing shared UI state. | `checkedForEntry` |
| `ensurePrintListDetails` | 13091 | Run the ensure print list details workflow for the browser application. | `renderPrintGlassTypes` |
| `printListIsFullCoverage` | 13124 | Run the print list is full coverage workflow for the browser application. | — |
| `printCountSourceLists` | 13134 | Run the print count source lists workflow for the browser application. | `printGlassEntriesForLists`, `renderPrintGlassTypes` |
| `printItemsForCountList` | 13153 | Run the print items for count list workflow for the browser application. | `addEntry` |
| `printGlassEntriesForLists` | 13170 | Run the print glass entries for lists workflow for the browser application. | `availableGlassTypesForLists`, `renderPrintGlassTypes` |
| `addEntry` | 13179 | Create the add entry workflow using the existing shared UI state. | — |
| `availableGlassTypesForLists` | 13225 | Run the available glass types for lists workflow for the browser application. | — |
| `ensurePrintGlassFieldWrapper` | 13234 | Run the ensure print glass field wrapper workflow for the browser application. | `renderPrintGlassTypes` |
| `renderPrintGlassTypes` | 13259 | Render the render print glass types workflow using the existing shared UI state. | `renderPrintOptionStages`, `wireEvents` |
| `checkedForEntry` | 13305 | Run the checked for entry workflow for the browser application. | — |
| `printStageOptionLabel` | 13451 | Run the print stage option label workflow for the browser application. | `renderPrintOptionStages` |
| `renderPrintOptionStages` | 13468 | Render the render print option stages workflow using the existing shared UI state. | `openPrintOptions`, `wireEvents` |
| `openPrintOptions` | 13507 | Open the open print options workflow using the existing shared UI state. | `ids`, `wireEvents` |
| `closePrintOptions` | 13538 | Close the close print options workflow using the existing shared UI state. | `submitPrintOptions`, `wireEvents` |
| `submitPrintOptions` | 13549 | Process the submit print options workflow using the existing shared UI state. | `wireEvents` |
| `importTempDeliveryFolder` | 13590 | Run the import temp delivery folder workflow for the browser application. | `wireEvents` |
| `refreshAdminPage` | 13648 | Load the refresh admin page workflow using the existing shared UI state. | `createUserFromForm`, `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteSelectedDeliveryList`, `importTempDeliveryFolder`, `refreshAdminUsersUi`, `resetAdminScansForDate`, `saveRolePermissions` (+1 more) |
| `adminDeliveryListCutoffDate` | 13700 | Run the admin delivery list cutoff date workflow for the browser application. | `deliveryListIsInAdminWindow` |
| `deliveryListIsInAdminWindow` | 13712 | Run the delivery list is in admin window workflow for the browser application. | `adminDeliveryListHiddenOlderRows`, `deliveryListAdminRows` |
| `adminDeliveryListHiddenOlderRows` | 13725 | Run the admin delivery list hidden older rows workflow for the browser application. | `deliveryListAdminRows` |
| `adminDeliveryListWindowLabel` | 13734 | Run the admin delivery list window label workflow for the browser application. | `deliveryListAdminRows` |
| `adminDeliveryListModalResultsHtml` | 13750 | Run the admin delivery list modal results HTML workflow for the browser application. | `adminModalContent`, `renderAdminDeliveryListModalResults` |
| `renderAdminDeliveryListModalResults` | 13766 | Render the render admin delivery list modal results workflow using the existing shared UI state. | `ids`, `refreshAdminDeliveryListModal`, `wireEvents` |
| `refreshAdminDeliveryListModal` | 13779 | Load the refresh admin delivery list modal workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `resetAdminScansForDate` |
| `deliveryListAdminRows` | 13796 | Run the delivery list admin rows workflow for the browser application. | `adminDeliveryListModalResultsHtml` |
| `searchAdminDeliveryLists` | 13949 | Run the search admin delivery lists workflow for the browser application. | `refreshAdminDeliveryListModal`, `wireEvents` |
| `activeRecentImports` | 13975 | Run the active recent imports workflow for the browser application. | `renderAdminDeliveryLists`, `renderImportHistory` |
| `renderAdminDeliveryLists` | 14045 | Render the render admin delivery lists workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteSelectedDeliveryList`, `resetAdminScansForDate`, `resetAdminScansForList` |
| `openAdminModal` | 14055 | Open the open admin modal workflow using the existing shared UI state. | `createUserFromForm`, `deleteAdminDeliveryListById`, `ids`, `openBayAllScansModal`, `openManualEditForList`, `openRackForm`, `openRackSetForm`, `wireEvents` |
| `closeAdminModal` | 14100 | Close the close admin modal workflow using the existing shared UI state. | `createRackSet`, `saveRackDefinition`, `updateBayScanModeUi` |
| `adminModalContent` | 14131 | Run the admin modal content workflow for the browser application. | `deleteRackDefinition`, `deleteRackSet`, `ids`, `openAdminModal`, `openRackManagerRackInlineEdit`, `openRackManagerSetEdit`, `racks`, `refreshAdminUsersUi` (+3 more) |
| `lookupTypeMeta` | 14256 | Run the lookup type meta workflow for the browser application. | `lookupListHtml` |
| `lookupListHtml` | 14287 | Run the lookup list HTML workflow for the browser application. | `lookupManagerModalHtml` |
| `lookupManagerModalHtml` | 14328 | Run the lookup manager modal HTML workflow for the browser application. | `adminModalContent` |
| `rackManagerRackEditHtml` | 14398 | Run the rack manager rack edit HTML workflow for the browser application. | `rackManagerModalHtml` |
| `rack` | 14407 | Run the rack workflow for the browser application. | `createRackSet`, `pad` |
| `rackManagerSetEditHtml` | 14448 | Run the rack manager set edit HTML workflow for the browser application. | `rackManagerModalHtml` |
| `racks` | 14457 | Run the racks workflow for the browser application. | — |
| `focusRackManagerRackEdit` | 14499 | Run the focus rack manager rack edit workflow for the browser application. | `ids` |
| `openRackManagerRackInlineEdit` | 14508 | Open the open rack manager rack inline edit workflow using the existing shared UI state. | `focusRackManagerRackEdit` |
| `saveRackInlineEdit` | 14528 | Run the save rack inline edit workflow for the browser application. | `wireEvents` |
| `openRackManagerSetEdit` | 14563 | Open the open rack manager set edit workflow using the existing shared UI state. | `ids` |
| `saveRackSetQuickEdit` | 14582 | Run the save rack set quick edit workflow for the browser application. | `wireEvents` |
| `racks` | 14591 | Run the racks workflow for the browser application. | — |
| `rackManagerModalHtml` | 14636 | Run the rack manager modal HTML workflow for the browser application. | `adminModalContent` |
| `rackFormModalHtml` | 14735 | Run the rack form modal HTML workflow for the browser application. | `adminModalContent` |
| `rackSetFormModalHtml` | 14758 | Run the rack set form modal HTML workflow for the browser application. | `adminModalContent` |
| `permissionLabel` | 14776 | Run the permission label workflow for the browser application. | `rolePermissionCategoryHtml` |
| `categorizedPermissions` | 14846 | Run the categorized permissions workflow for the browser application. | `rolePermissionsModalHtml` |
| `rolePermissionCategoryKey` | 14875 | Run the role permission category key workflow for the browser application. | `ids`, `rememberRolePermissionUiState`, `rolePermissionCategoryHtml` |
| `resetRolePermissionUiSession` | 14884 | Run the reset role permission UI session workflow for the browser application. | `closeAdminModal`, `openAdminModal` |
| `rememberRolePermissionUiState` | 14895 | Run the remember role permission UI state workflow for the browser application. | `saveRolePermissions` |
| `restoreRolePermissionUiScroll` | 14928 | Run the restore role permission UI scroll workflow for the browser application. | `saveRolePermissions` |
| `rolePermissionCategoryHtml` | 14941 | Run the role permission category HTML workflow for the browser application. | `rolePermissionsModalHtml` |
| `rolePermissionCountText` | 14982 | Run the role permission count text workflow for the browser application. | `rolePermissionsModalHtml` |
| `rolePermissionsModalHtml` | 14994 | Run the role permissions modal HTML workflow for the browser application. | `adminModalContent` |
| `permissionSummaryFromPermissions` | 15052 | Run the permission summary from permissions workflow for the browser application. | `permissionSummaryForUser`, `rolePermissionsModalHtml` |
| `permissionSummaryForUser` | 15067 | Run the permission summary for user workflow for the browser application. | `renderAdminUsersTable` |
| `saveRolePermissions` | 15091 | Run the save role permissions workflow for the browser application. | `ids` |
| `manualEditDeliveryDateForList` | 15133 | Run the manual edit delivery date for list workflow for the browser application. | `manualEditStageListsForCurrentDelivery` |
| `manualEditStageListsForCurrentDelivery` | 15144 | Run the manual edit stage lists for current delivery workflow for the browser application. | `manualEditModalHtml` |
| `manualEditStageSummary` | 15158 | Run the manual edit stage summary workflow for the browser application. | `manualEditModalHtml`, `runManualEditModalSearch` |
| `manualEditModalHtml` | 15173 | Run the manual edit modal HTML workflow for the browser application. | `adminModalContent` |
| `ensureManualEditLookupsLoaded` | 15221 | Run the ensure manual edit lookups loaded workflow for the browser application. | `ids`, `openManualEditForList` |
| `openManualEditForList` | 15260 | Open the open manual edit for list workflow using the existing shared UI state. | `ids` |
| `fetchManualEditResults` | 15276 | Load the fetch manual edit results workflow using the existing shared UI state. | `runManualEditModalSearch`, `runManualEditSearch` |
| `runManualEditModalSearch` | 15289 | Run the run manual edit modal search workflow for the browser application. | `deleteManualLineItem`, `ids`, `openManualEditForList`, `saveManualLineItem`, `wireEvents` |
| `renderManualEditStageOptions` | 15333 | Render the render manual edit stage options workflow using the existing shared UI state. | `refreshAdminPage` |
| `renderImportHistory` | 15351 | Render the render import history workflow using the existing shared UI state. | `refreshAdminPage` |
| `importHistoryRows` | 15370 | Run the import history rows workflow for the browser application. | `renderAdminDeliveryLists`, `renderImportHistory` |
| `stageNameForRow` | 15395 | Run the stage name for row workflow for the browser application. | `addRow`, `isStagingRow`, `stageCategoryForImportRow`, `stageRowKey`, `stageSortForRow` |
| `isStagingRow` | 15403 | Run the is staging row workflow for the browser application. | `addRow` |
| `stageCategoryForImportRow` | 15410 | Run the stage category for import row workflow for the browser application. | `addRow` |
| `updatedQtyForRow` | 15421 | Update the updated qty for row workflow using the existing shared UI state. | `addRow`, `changedQtyForRow`, `isNewStageRow`, `originalQtyForRow`, `stageRowPriority` |
| `changedQtyForRow` | 15429 | Run the changed qty for row workflow for the browser application. | `addRow`, `stageRowPriority` |
| `originalQtyForRow` | 15443 | Run the original qty for row workflow for the browser application. | `addRow`, `isNewStageRow`, `stageRowPriority` |
| `isNewStageRow` | 15476 | Run the is new stage row workflow for the browser application. | `addRow`, `stageRowPriority` |
| `stageRowsForEntry` | 15492 | Run the stage rows for entry workflow for the browser application. | `addRow` |
| `hasStageChanges` | 15517 | Run the has stage changes workflow for the browser application. | `addRow` |
| `stageRowKey` | 15528 | Run the stage row key workflow for the browser application. | `addRow`, `collapseDuplicateStageRows` |
| `stageRowPriority` | 15542 | Run the stage row priority workflow for the browser application. | `collapseDuplicateStageRows` |
| `collapseDuplicateStageRows` | 15564 | Run the collapse duplicate stage rows workflow for the browser application. | `addRow` |
| `stageSortForRow` | 15587 | Run the stage sort for row workflow for the browser application. | `addRow` |
| `allStageRowsForGroup` | 15598 | Run the all stage rows for group workflow for the browser application. | `addRow` |
| `addRow` | 15606 | Create the add row workflow using the existing shared UI state. | — |
| `renderAdminDeleteControls` | 15865 | Render the render admin delete controls workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteSelectedDeliveryList`, `refreshAdminPage`, `resetAdminScansForDate`, `wireEvents` |
| `renderAdminResetControls` | 15886 | Render the render admin reset controls workflow using the existing shared UI state. | `deleteAdminDeliveryDateByDate`, `refreshAdminPage`, `resetAdminScansForDate` |
| `resetSelectedAdminScans` | 15900 | Run the reset selected admin scans workflow for the browser application. | `wireEvents` |
| `resetAdminScansForList` | 15910 | Run the reset admin scans for list workflow for the browser application. | `ids`, `resetSelectedAdminScans` |
| `resetAdminScansForDate` | 15941 | Run the reset admin scans for date workflow for the browser application. | `ids` |
| `deleteAdminDeliveryDateByDate` | 15995 | Remove the delete admin delivery date by date workflow using the existing shared UI state. | `ids` |
| `deleteSelectedDeliveryList` | 16053 | Remove the delete selected delivery list workflow using the existing shared UI state. | `wireEvents` |
| `deleteAdminDeliveryListById` | 16132 | Remove the delete admin delivery list by ID workflow using the existing shared UI state. | `ids` |
| `userInitials` | 16182 | Run the user initials workflow for the browser application. | `applyPermissionUi`, `renderAdminUsersTable` |
| `userAccentClass` | 16200 | Run the user accent class workflow for the browser application. | `applyPermissionUi`, `renderAdminUsersTable` |
| `userActionButtonHtml` | 16217 | Run the user action button HTML workflow for the browser application. | `renderAdminUsersTable` |
| `generateTemporaryPassword` | 16239 | Run the generate temporary password workflow for the browser application. | `ids` |
| `refreshAdminUsersUi` | 16258 | Load the refresh admin users UI workflow using the existing shared UI state. | `ids` |
| `confirmWebAppAction` | 16273 | Run the confirm web app action workflow for the browser application. | `clearManagedItem`, `clearRack`, `clearRackItem`, `closeAdminModal`, `deleteAdminDeliveryDateByDate`, `deleteAdminDeliveryListById`, `deleteBayEditorBay`, `deleteBayEditorGroup` (+19 more) |
| `keyHandler` | 16295 | Run the key handler workflow for the browser application. | — |
| `typedConfirmationMatches` | 16333 | Run the typed confirmation matches workflow for the browser application. | `close`, `syncTypedConfirmation` |
| `syncTypedConfirmation` | 16340 | Run the sync typed confirmation workflow for the browser application. | `close` |
| `close` | 16350 | Close the close workflow using the existing shared UI state. | `notifyPrintComplete`, `submit` |
| `promptWebAppAction` | 16399 | Run the prompt web app action workflow for the browser application. | `addSpacerBay` |
| `close` | 16437 | Close the close workflow using the existing shared UI state. | `notifyPrintComplete`, `submit` |
| `submit` | 16447 | Process the submit workflow using the existing shared UI state. | — |
| `confirmDeactivateUser` | 16480 | Run the confirm deactivate user workflow for the browser application. | `ids` |
| `keyHandler` | 16491 | Run the key handler workflow for the browser application. | — |
| `close` | 16517 | Close the close workflow using the existing shared UI state. | `notifyPrintComplete`, `submit` |
| `renderAdminUsers` | 16552 | Render the render admin users workflow using the existing shared UI state. | `refreshAdminPage` |
| `renderAdminUsersTable` | 16574 | Render the render admin users table workflow using the existing shared UI state. | `adminModalContent`, `renderAdminUsers` |
| `renderAdminStations` | 16790 | Render the render admin stations workflow using the existing shared UI state. | `addStationFromInput`, `ids`, `refreshAdminPage`, `removeStation` |
| `renderAdminStationsList` | 16800 | Render the render admin stations list workflow using the existing shared UI state. | `adminModalContent`, `renderAdminStations` |
| `customerRouteValue` | 16818 | Run the customer route value workflow for the browser application. | `customerRouteAddressStatus`, `customerRouteDefaultAddress`, `customerRouteDisplay`, `customerRouteFormValues`, `customerRouteOptionList`, `customerRouteOptionsHtml`, `customerRouteRuleRowsHtml`, `renderCustomerRouteRules` (+3 more) |
| `customerRouteDisplay` | 16839 | Run the customer route display workflow for the browser application. | `customerRouteRuleRowsHtml` |
| `customerRouteDefaultAddress` | 16854 | Run the customer route default address workflow for the browser application. | `customerRouteAddress`, `customerRouteFormValues`, `saveCustomerRouteRuleRow`, `wireEvents` |
| `customerRouteAddress` | 16863 | Run the customer route address workflow for the browser application. | `customerRouteAddressStatus`, `customerRouteRuleRowsHtml`, `setCustomerRouteEditForm` |
| `customerRouteAddressStatus` | 16873 | Run the customer route address status workflow for the browser application. | `customerRouteRuleRowsHtml` |
| `customerRouteOptionList` | 16887 | Run the customer route option list workflow for the browser application. | `customerRouteOptionsHtml`, `renderCustomerRouteRules` |
| `customerRouteOptionsHtml` | 16901 | Run the customer route options HTML workflow for the browser application. | `customerRouteRuleRowsHtml`, `customerRouteRulesModalHtml` |
| `customerRouteRuleRowsHtml` | 16916 | Run the customer route rule rows HTML workflow for the browser application. | `customerRouteRulesModalHtml`, `renderCustomerRouteRules` |
| `customerRouteRulesModalHtml` | 16987 | Run the customer route rules modal HTML workflow for the browser application. | `adminModalContent`, `refreshCustomerRouteModal` |
| `setCustomerRouteEditForm` | 17042 | Update the set customer route edit form workflow using the existing shared UI state. | — |
| `renderCustomerRouteRules` | 17069 | Render the render customer route rules workflow using the existing shared UI state. | `refreshAdminPage`, `refreshCustomerRouteModal` |
| `refreshCustomerRouteModal` | 17120 | Load the refresh customer route modal workflow using the existing shared UI state. | `removeCustomerRouteRule`, `saveCustomerRouteRule`, `saveCustomerRouteRuleRow` |
| `renderBayScannerRuleOverview` | 17133 | Render the render bay scanner rule overview workflow using the existing shared UI state. | `refreshAdminPage`, `refreshBayScannerRules`, `removeBayScannerRule`, `saveBayBarcodeRule`, `saveBayManualRule` |
| `autoAssignTypeOptions` | 17149 | Run the auto assign type options workflow for the browser application. | `bayAutoAssignerModalHtml` |
| `renderBayAutoAssignOverview` | 17159 | Render the render bay auto assign overview workflow using the existing shared UI state. | `refreshAdminPage`, `refreshBayAutoAssigner`, `saveBayAutoAssignerSettings` |
| `bayAutoAssignerModalHtml` | 17174 | Run the bay auto assigner modal HTML workflow for the browser application. | `adminModalContent`, `refreshBayAutoAssigner`, `saveBayAutoAssignerSettings` |
| `refreshBayAutoAssigner` | 17238 | Load the refresh bay auto assigner workflow using the existing shared UI state. | — |
| `saveBayAutoAssignerSettings` | 17253 | Run the save bay auto assigner settings workflow for the browser application. | `wireEvents` |
| `bayScannerRulesModalHtml` | 17274 | Run the bay scanner rules modal HTML workflow for the browser application. | `adminModalContent`, `refreshBayScannerRules`, `removeBayScannerRule`, `saveBayBarcodeRule`, `saveBayManualRule` |
| `refreshBayScannerRules` | 17325 | Load the refresh bay scanner rules workflow using the existing shared UI state. | — |
| `saveBayManualRule` | 17340 | Run the save bay manual rule workflow for the browser application. | `wireEvents` |
| `saveBayBarcodeRule` | 17355 | Run the save bay barcode rule workflow for the browser application. | `wireEvents` |
| `removeBayScannerRule` | 17369 | Remove the remove bay scanner rule workflow using the existing shared UI state. | `ids` |
| `renderCustomerEmailOverview` | 17381 | Render the render customer email overview workflow using the existing shared UI state. | `refreshAdminPage`, `removeCustomerEmailCc`, `removeCustomerEmailContact`, `saveCustomerEmailCc`, `saveCustomerEmailContact`, `sendCustomerEmailTest` |
| `emailAddressListText` | 17419 | Run the email address list text workflow for the browser application. | `customerEmailRulesModalHtml`, `email`, `emailDraftPreviewHtml` |
| `emailStatusLabel` | 17428 | Run the email status label workflow for the browser application. | `customerEmailRulesModalHtml`, `emailDraftPreviewHtml` |
| `customerEmailRulesModalHtml` | 17441 | Run the customer email rules modal HTML workflow for the browser application. | `adminModalContent`, `refreshCustomerEmailSettings`, `removeCustomerEmailCc`, `removeCustomerEmailContact`, `saveCustomerEmailCc`, `saveCustomerEmailContact`, `sendCustomerEmailTest` |
| `emailDraftPreviewHtml` | 17558 | Run the email draft preview HTML workflow for the browser application. | `email` |
| `openEmailDraftPreview` | 17594 | Open the open email draft preview workflow using the existing shared UI state. | `ids` |
| `email` | 17600 | Run the email workflow for the browser application. | — |
| `closeEmailDraftPreview` | 17616 | Close the close email draft preview workflow using the existing shared UI state. | `email`, `ids` |
| `copyEmailDraftBody` | 17626 | Run the copy email draft body workflow for the browser application. | `ids` |
| `email` | 17632 | Run the email workflow for the browser application. | — |
| `mailtoParam` | 17643 | Run the mailto param workflow for the browser application. | `email` |
| `openEmailDraftMailto` | 17654 | Open the open email draft mailto workflow using the existing shared UI state. | `ids` |
| `email` | 17660 | Run the email workflow for the browser application. | — |
| `refreshCustomerEmailSettings` | 17677 | Load the refresh customer email settings workflow using the existing shared UI state. | `ids` |
| `startCustomerEmailEdit` | 17691 | Run the start customer email edit workflow for the browser application. | `ids` |
| `contact` | 17697 | Run the contact workflow for the browser application. | — |
| `saveCustomerEmailContact` | 17715 | Run the save customer email contact workflow for the browser application. | `wireEvents` |
| `saveCustomerEmailCc` | 17733 | Run the save customer email cc workflow for the browser application. | `wireEvents` |
| `sendCustomerEmailTest` | 17749 | Run the send customer email test workflow for the browser application. | `wireEvents` |
| `removeCustomerEmailContact` | 17773 | Remove the remove customer email contact workflow using the existing shared UI state. | `ids` |
| `removeCustomerEmailCc` | 17788 | Remove the remove customer email cc workflow using the existing shared UI state. | `ids` |
| `customerRouteFormValues` | 17803 | Run the customer route form values workflow for the browser application. | `saveCustomerRouteRule` |
| `saveCustomerRouteRule` | 17837 | Run the save customer route rule workflow for the browser application. | `wireEvents` |
| `saveCustomerRouteRuleRow` | 17870 | Run the save customer route rule row workflow for the browser application. | `ids` |
| `removeCustomerRouteRule` | 17911 | Remove the remove customer route rule workflow using the existing shared UI state. | `ids` |
| `renderActiveSessions` | 17941 | Render the render active sessions workflow using the existing shared UI state. | `refreshAdminPage` |
| `createUserFromForm` | 17953 | Create the create user from form workflow using the existing shared UI state. | `wireEvents` |
| `runManualEditSearch` | 17986 | Run the run manual edit search workflow for the browser application. | `deleteManualLineItem`, `saveManualLineItem`, `wireEvents` |
| `renderManualEditResults` | 17997 | Render the render manual edit results workflow using the existing shared UI state. | `runManualEditSearch` |
| `manualEditOptionHasValue` | 18009 | Run the manual edit option has value workflow for the browser application. | `manualEditIsCustomChoice` |
| `lookupOptions` | 18020 | Run the lookup options workflow for the browser application. | `manualEditProcessOptions`, `manualEditRouteOptions` |
| `manualEditIsCustomChoice` | 18037 | Run the manual edit is custom choice workflow for the browser application. | `manualEditChoiceFieldHtml`, `manualEditSelectOptions` |
| `manualEditSelectOptions` | 18048 | Run the manual edit select options workflow for the browser application. | `manualEditChoiceFieldHtml` |
| `manualEditChoiceFieldHtml` | 18081 | Run the manual edit choice field HTML workflow for the browser application. | `manualEditResultsHtml` |
| `manualEditChoiceHiddenInput` | 18132 | Run the manual edit choice hidden input workflow for the browser application. | `manualEditSetChoiceValue` |
| `manualEditSetChoiceValue` | 18143 | Run the manual edit set choice value workflow for the browser application. | `manualEditApplyChoiceSelect`, `manualEditApplyCustomInput`, `manualEditShowCustomChoice`, `manualEditShowSelectChoice` |
| `manualEditShowCustomChoice` | 18161 | Run the manual edit show custom choice workflow for the browser application. | `manualEditApplyChoiceSelect`, `manualEditSyncChoiceSelect` |
| `manualEditShowSelectChoice` | 18189 | Run the manual edit show select choice workflow for the browser application. | `manualEditClearCustomChoice`, `manualEditSyncChoiceSelect` |
| `manualEditApplyChoiceSelect` | 18218 | Run the manual edit apply choice select workflow for the browser application. | `wireEvents` |
| `manualEditApplyCustomInput` | 18237 | Run the manual edit apply custom input workflow for the browser application. | `wireEvents` |
| `manualEditClearCustomChoice` | 18251 | Run the manual edit clear custom choice workflow for the browser application. | `ids` |
| `manualEditSyncChoiceSelect` | 18265 | Run the manual edit sync choice select workflow for the browser application. | `wireEvents` |
| `manualEditCurrentLocationValue` | 18290 | Run the manual edit current location value workflow for the browser application. | `manualEditResultsHtml` |
| `manualEditLocationOptions` | 18299 | Run the manual edit location options workflow for the browser application. | `manualEditResultsHtml` |
| `manualEditRouteOptions` | 18353 | Run the manual edit route options workflow for the browser application. | `manualEditResultsHtml` |
| `manualEditProcessOptions` | 18370 | Run the manual edit process options workflow for the browser application. | `manualEditResultsHtml` |
| `manualEditProductOptions` | 18389 | Run the manual edit product options workflow for the browser application. | `manualEditResultsHtml` |
| `lookup` | 18405 | Run the lookup workflow for the browser application. | — |
| `manualEditSetRowError` | 18416 | Run the manual edit set row error workflow for the browser application. | `manualEditValidateRow` |
| `manualEditValidateRow` | 18438 | Run the manual edit validate row workflow for the browser application. | `saveManualLineItem`, `wireEvents` |
| `manualEditResultsHtml` | 18482 | Run the manual edit results HTML workflow for the browser application. | `renderManualEditResults`, `runManualEditModalSearch` |
| `saveManualLineItem` | 18620 | Run the save manual line item workflow for the browser application. | `ids` |
| `deleteManualLineItem` | 18660 | Remove the delete manual line item workflow using the existing shared UI state. | `ids` |
| `exportStaticCsv` | 18685 | Run the export static CSV workflow for the browser application. | — |
| `startPolling` | 18705 | Run the start polling workflow for the browser application. | `loadAuthenticatedApp` |
| `stopPolling` | 18725 | Run the stop polling workflow for the browser application. | `logout`, `startPolling` |
| `loadAuthenticatedApp` | 18735 | Load the load authenticated app workflow using the existing shared UI state. | `init`, `wireEvents` |
| `init` | 18753 | Run the init workflow for the browser application. | `ids` |
| `replayExpandableListAnimation` | 18780 | Run the replay expandable list animation workflow for the browser application. | `wireEvents` |
| `wireEvents` | 18801 | Connect the wire events workflow using the existing shared UI state. | `init`, `module startup` |
| `updateBayScanModeUi` | 19769 | Update the update bay scan mode UI workflow using the existing shared UI state. | — |
| `ids` | 19926 | Run the IDs workflow for the browser application. | — |

## PowerShell launcher function reference
| Function | Line | Purpose |
|---|---:|---|
| `Write-LauncherLog` | 17 | Record one launcher milestone in the console and persistent log. |
| `Test-PortAvailable` | 33 | Determine whether a local TCP port can be safely bound by the server. |
| `Get-DeliveryScannerHealth` | 56 | Identify a healthy Delivery List Scanner already listening on a port. |
| `Open-DeliveryScannerBrowser` | 75 | Open the verified local web address without making browser launch a startup dependency. |
| `Resolve-PythonRuntime` | 90 | Select a supported Python 3.10+ runtime for the local SQLite server. |
| `Show-StartupFailure` | 141 | Keep startup errors visible and point the operator to durable diagnostics. |

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
| GET | `/api/indian-trail/in-transit` | exact | 1208 |
| GET | `/api/indian-trail/bays` | exact | 1214 |
| GET | `/api/indian-trail/bay-job-details` | exact | 1220 |
| GET | `/api/indian-trail/layout` | exact | 1227 |
| GET | `/api/indian-trail/events` | exact | 1233 |
| GET | `/api/indian-trail/stale-bays` | exact | 1240 |
| GET | `/api/indian-trail/stale-bays/print` | exact | 1247 |
| GET | `/api/racks` | exact | 1258 |
| GET | `/api/racks/packing-list` | exact | 1264 |
| GET | `/api/delivery-lists/` | prefix | 1279 |
| GET | `/api/export.csv` | exact | 1292 |
| GET | `/api/export.xlsx` | exact | 1309 |
| GET | `/api/export/package.xlsx` | exact | 1326 |
| GET | `/api/print/package` | exact | 1344 |
| POST | `/api/login` | exact | 1369 |
| POST | `/api/password-reset/request` | exact | 1385 |
| POST | `/api/password-reset/confirm` | exact | 1389 |
| POST | `/api/logout` | exact | 1399 |
| POST | `/api/notifications/acknowledge` | exact | 1411 |
| POST | `/api/scans` | exact | 1424 |
| POST | `/api/reset` | exact | 1435 |
| POST | `/api/undo` | exact | 1453 |
| POST | `/api/redo` | exact | 1469 |
| POST | `/api/stations` | exact | 1485 |
| POST | `/api/stations/remove` | exact | 1491 |
| POST | `/api/stations/rename` | exact | 1497 |
| POST | `/api/import` | exact | 1503 |
| POST | `/api/import/folder` | exact | 1511 |
| POST | `/api/import/preview` | exact | 1519 |
| POST | `/api/exceptions/resolve` | exact | 1525 |
| POST | `/api/admin/users` | exact | 1532 |
| POST | `/api/admin/users/deactivate` | exact | 1539 |
| POST | `/api/admin/users/reactivate` | exact | 1546 |
| POST | `/api/admin/users/delete` | exact | 1553 |
| POST | `/api/admin/users/password` | exact | 1560 |
| POST | `/api/admin/users/roles` | exact | 1567 |
| POST | `/api/admin/roles/permissions` | exact | 1582 |
| POST | `/api/admin/line-item` | exact | 1589 |
| POST | `/api/admin/line-item/delete` | exact | 1596 |
| POST | `/api/admin/customer-route-rules` | exact | 1603 |
| POST | `/api/admin/customer-route-rules/remove` | exact | 1610 |
| POST | `/api/admin/customer-emails` | exact | 1617 |
| POST | `/api/admin/customer-emails/remove` | exact | 1624 |
| POST | `/api/admin/customer-emails/test` | exact | 1631 |
| POST | `/api/admin/customer-emails/cc` | exact | 1638 |
| POST | `/api/admin/customer-emails/cc/remove` | exact | 1645 |
| POST | `/api/admin/bay-scanner-rules/manual` | exact | 1652 |
| POST | `/api/admin/bay-scanner-rules/manual/remove` | exact | 1659 |
| POST | `/api/admin/bay-scanner-rules/barcode` | exact | 1666 |
| POST | `/api/admin/bay-scanner-rules/barcode/remove` | exact | 1673 |
| POST | `/api/admin/bay-auto-assigner` | exact | 1680 |
| POST | `/api/admin/manual-edit-lookups` | exact | 1687 |
| POST | `/api/admin/delete-list` | exact | 1694 |
| POST | `/api/admin/delete-date` | exact | 1703 |
| POST | `/api/indian-trail/receive` | exact | 1712 |
| POST | `/api/indian-trail/manual-assign` | exact | 1722 |
| POST | `/api/indian-trail/assign` | exact | 1729 |
| POST | `/api/indian-trail/move` | exact | 1736 |
| POST | `/api/indian-trail/clear` | exact | 1743 |
| POST | `/api/indian-trail/clear-assignment` | exact | 1750 |
| POST | `/api/indian-trail/restore-assignment` | exact | 1757 |
| POST | `/api/indian-trail/bay-status` | exact | 1764 |
| POST | `/api/indian-trail/scan-out` | exact | 1771 |
| POST | `/api/indian-trail/layout` | exact | 1778 |
| POST | `/api/indian-trail/bays/add` | exact | 1790 |
| POST | `/api/indian-trail/bays/delete` | exact | 1797 |
| POST | `/api/indian-trail/bays/delete-group` | exact | 1804 |
| POST | `/api/indian-trail/mark-sdi` | exact | 1811 |
| POST | `/api/indian-trail/remove-sdi` | exact | 1818 |
| POST | `/api/indian-trail/bay-check` | exact | 1825 |
| POST | `/api/indian-trail/stale-bays/snooze` | exact | 1832 |
| POST | `/api/racks/scan` | exact | 1839 |
| POST | `/api/racks/complete` | exact | 1849 |
| POST | `/api/racks/uncomplete` | exact | 1856 |
| POST | `/api/racks/return` | exact | 1863 |
| POST | `/api/racks/not-on-way` | exact | 1870 |
| POST | `/api/racks/assign-line-item` | exact | 1879 |
| POST | `/api/racks/move-item` | exact | 1886 |
| POST | `/api/racks/clear-item` | exact | 1893 |
| POST | `/api/racks/clear` | exact | 1900 |
| POST | `/api/racks` | exact | 1907 |
| POST | `/api/racks/create-set` | exact | 1914 |
| POST | `/api/racks/delete` | exact | 1921 |

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
| `#headerGlobalSearchInput` | `input` | Global header, navigation, search, and user controls | 107 |
| `#headerGlobalSearchBtn` | `button` | Global header, navigation, search, and user controls | 109 |
| `#headerGlobalSearchResults` | `div` | Global header, navigation, search, and user controls | 110 |
| `#languageToggleBtn` | `button` | Global header, navigation, search, and user controls | 113 |
| `#refreshPageBtn` | `button` | Global header, navigation, search, and user controls | 117 |
| `#fullscreenToggleBtn` | `button` | Global header, navigation, search, and user controls | 120 |
| `#globalPrintExportBtn` | `button` | Global header, navigation, search, and user controls | 123 |
| `#backendStatus` | `span` | Global header, navigation, search, and user controls | 124 |
| `#signedInUser` | `span` | Global header, navigation, search, and user controls | 129 |
| `#signedInRole` | `small` | Global header, navigation, search, and user controls | 130 |
| `#logoutBtn` | `button` | Global header, navigation, search, and user controls | 134 |
| `#homePage` | `section` | Home dashboard and delivery-list overview | 142 |
| `#homeWelcome` | `p` | Home dashboard and delivery-list overview | 146 |
| `#todayDateLabel` | `span` | Home dashboard and delivery-list overview | 156 |
| `#todayStageGrid` | `div` | Home dashboard and delivery-list overview | 158 |
| `#homeListCount` | `span` | Home dashboard and delivery-list overview | 163 |
| `#homeListSearch` | `input` | Home dashboard and delivery-list overview | 168 |
| `#homeStageFilter` | `select` | Home dashboard and delivery-list overview | 170 |
| `#homePagerTop` | `div` | Home dashboard and delivery-list overview | 181 |
| `#homeListGrid` | `div` | Home dashboard and delivery-list overview | 183 |
| `#homePageSize` | `select` | Home dashboard and delivery-list overview | 187 |
| `#homePager` | `div` | Home dashboard and delivery-list overview | 193 |
| `#overviewRangeSelect` | `select` | Home dashboard and delivery-list overview | 206 |
| `#homeStatisticsRangeText` | `span` | Home dashboard and delivery-list overview | 215 |
| `#homeStatsPdfBtn` | `button` | Home dashboard and delivery-list overview | 219 |
| `#overviewStats` | `div` | Home dashboard and delivery-list overview | 224 |
| `#homeMonthlyRemakes` | `div` | Home dashboard and delivery-list overview | 225 |
| `#homeStatsChart` | `div` | Home dashboard and delivery-list overview | 228 |
| `#homeUserCard` | `div` | Home dashboard and delivery-list overview | 229 |
| `#homeRecentLists` | `div` | Home dashboard and delivery-list overview | 236 |
| `#homeActivity` | `div` | Home dashboard and delivery-list overview | 243 |
| `#scanPage` | `section` | Main stage scanning workflow | 250 |
| `#pageTitle` | `h1` | Main stage scanning workflow | 253 |
| `#stageSubtitle` | `p` | Main stage scanning workflow | 254 |
| `#deliveryDateSelect` | `select` | Main stage scanning workflow | 259 |
| `#deliveryStageSelect` | `select` | Main stage scanning workflow | 263 |
| `#stationProfileDisplay` | `span` | Main stage scanning workflow | 267 |
| `#stationSelect` | `select` | Main stage scanning workflow | 268 |
| `#operatorInput` | `input` | Main stage scanning workflow | 270 |
| `#listPanel` | `section` | Main stage scanning workflow | 275 |
| `#countAll` | `span` | Main stage scanning workflow | 280 |
| `#countRemaining` | `span` | Main stage scanning workflow | 281 |
| `#countPartial` | `span` | Main stage scanning workflow | 282 |
| `#countComplete` | `span` | Main stage scanning workflow | 283 |
| `#countRemakes` | `span` | Main stage scanning workflow | 288 |
| `#countRushes` | `span` | Main stage scanning workflow | 289 |
| `#countUpdated` | `span` | Main stage scanning workflow | 290 |
| `#countErrors` | `span` | Main stage scanning workflow | 291 |
| `#countIndianTrailRoute` | `span` | Main stage scanning workflow | 296 |
| `#countCpuRoute` | `span` | Main stage scanning workflow | 297 |
| `#countDtcRoute` | `span` | Main stage scanning workflow | 298 |
| `#countGreenvilleRoute` | `span` | Main stage scanning workflow | 299 |
| `#glassFilterTabs` | `div` | Main stage scanning workflow | 304 |
| `#searchInput` | `input` | Main stage scanning workflow | 312 |
| `#scanPagerTop` | `div` | Main stage scanning workflow | 316 |
| `#pageSize` | `select` | Main stage scanning workflow | 320 |
| `#listRows` | `tbody` | Main stage scanning workflow | 344 |
| `#totalItemsText` | `span` | Main stage scanning workflow | 349 |
| `#scanPagerBottom` | `div` | Main stage scanning workflow | 350 |
| `#pageSizeBottom` | `select` | Main stage scanning workflow | 353 |
| `#scanPanel` | `aside` | Main stage scanning workflow | 362 |
| `#stageHeading` | `h2` | Main stage scanning workflow | 365 |
| `#progressText` | `strong` | Main stage scanning workflow | 370 |
| `#progressFill` | `span` | Main stage scanning workflow | 372 |
| `#scanRackPanel` | `section` | Main stage scanning workflow | 376 |
| `#scanRackSelect` | `select` | Main stage scanning workflow | 380 |
| `#scanRackCompleteBtn` | `button` | Main stage scanning workflow | 383 |
| `#scanRackPrintBtn` | `button` | Main stage scanning workflow | 384 |
| `#scanRackStatus` | `p` | Main stage scanning workflow | 387 |
| `#outboundRackStatusPanel` | `section` | Main stage scanning workflow | 390 |
| `#outboundRackStatusSelect` | `select` | Main stage scanning workflow | 394 |
| `#outboundRackStatusSummary` | `div` | Main stage scanning workflow | 396 |
| `#scanBayOverridePanel` | `section` | Main stage scanning workflow | 403 |
| `#scanBayOverrideSelected` | `strong` | Main stage scanning workflow | 407 |
| `#scanBayOverrideMode` | `input` | Main stage scanning workflow | 411 |
| `#scanBayOverrideSelect` | `select` | Main stage scanning workflow | 417 |
| `#scanForm` | `form` | Main stage scanning workflow | 424 |
| `#undoBtn` | `button` | Main stage scanning workflow | 428 |
| `#redoBtn` | `button` | Main stage scanning workflow | 429 |
| `#scanInput` | `input` | Main stage scanning workflow | 434 |
| `#manualScanForm` | `form` | Main stage scanning workflow | 438 |
| `#manualOrderInput` | `input` | Main stage scanning workflow | 445 |
| `#manualItemInput` | `input` | Main stage scanning workflow | 449 |
| `#manualAssignPanel` | `section` | Main stage scanning workflow | 455 |
| `#manualAssignForm` | `form` | Main stage scanning workflow | 460 |
| `#manualAssignOrderInput` | `input` | Main stage scanning workflow | 463 |
| `#manualAssignItemInput` | `input` | Main stage scanning workflow | 467 |
| `#manualAssignQtyInput` | `input` | Main stage scanning workflow | 471 |
| `#manualAssignStatus` | `div` | Main stage scanning workflow | 475 |
| `#lastScanTime` | `span` | Main stage scanning workflow | 481 |
| `#viewAllRecent` | `button` | Main stage scanning workflow | 482 |
| `#lastCard` | `div` | Main stage scanning workflow | 484 |
| `#lastJob` | `strong` | Main stage scanning workflow | 486 |
| `#lastOrder` | `b` | Main stage scanning workflow | 488 |
| `#lastItem` | `b` | Main stage scanning workflow | 489 |
| `#lastQty` | `b` | Main stage scanning workflow | 490 |
| `#lastDims` | `b` | Main stage scanning workflow | 491 |
| `#lastCustomer` | `b` | Main stage scanning workflow | 492 |
| `#recentScanCountLabel` | `span` | Main stage scanning workflow | 499 |
| `#recentRows` | `tbody` | Main stage scanning workflow | 513 |
| `#mobileListCards` | `section` | Main stage scanning workflow | 519 |
| `#summaryPanel` | `section` | Main stage scanning workflow | 521 |
| `#remainingQty` | `strong` | Main stage scanning workflow | 524 |
| `#remainingPct` | `span` | Main stage scanning workflow | 524 |
| `#partialQty` | `strong` | Main stage scanning workflow | 528 |
| `#partialPct` | `span` | Main stage scanning workflow | 528 |
| `#completeQty` | `strong` | Main stage scanning workflow | 532 |
| `#completePct` | `span` | Main stage scanning workflow | 532 |
| `#errorQty` | `strong` | Main stage scanning workflow | 536 |
| `#racksPage` | `section` | Rack status and rack-management workflow | 545 |
| `#rackSummary` | `div` | Rack status and rack-management workflow | 552 |
| `#rackEditOpenBtn` | `button` | Rack status and rack-management workflow | 554 |
| `#rackGrid` | `section` | Rack status and rack-management workflow | 559 |
| `#bayMapPage` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 563 |
| `#indianTrailSummary` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 572 |
| `#bayFlowPanel` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 576 |
| `#bayLayoutManager` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 579 |
| `#bayLayoutCloseBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 586 |
| `#bayLayoutUndoBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 589 |
| `#bayLayoutRedoBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 590 |
| `#bayCollapseAllBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 591 |
| `#bayExpandAllBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 592 |
| `#bayLayoutCancelBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 593 |
| `#bayLayoutConfirmBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 594 |
| `#bayMapSearch` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 603 |
| `#bayCheckBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 605 |
| `#bayFilterDrawer` | `details` | Indian Trail bay map, receiving scanner, and bay modals | 606 |
| `#bayActiveFilterCount` | `strong` | Indian Trail bay map, receiving scanner, and bay modals | 610 |
| `#bayStatusFilter` | `select` | Indian Trail bay map, receiving scanner, and bay modals | 615 |
| `#bayGlassFilter` | `select` | Indian Trail bay map, receiving scanner, and bay modals | 629 |
| `#baySpecialFilter` | `select` | Indian Trail bay map, receiving scanner, and bay modals | 635 |
| `#bayActiveFilterBar` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 646 |
| `#bayActiveFilterSummary` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 647 |
| `#bayClearFiltersBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 648 |
| `#baySelectedText` | `span` | Indian Trail bay map, receiving scanner, and bay modals | 657 |
| `#bayMapCanvas` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 659 |
| `#bayActionButtons` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 664 |
| `#bayPanelRouteMini` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 679 |
| `#bayScanOutForm` | `form` | Indian Trail bay map, receiving scanner, and bay modals | 694 |
| `#bayScanModeToggle` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 706 |
| `#bayScanBayInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 714 |
| `#bayTargetClearBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 716 |
| `#bayScanOutInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 721 |
| `#bayUndoBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 723 |
| `#bayRedoBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 727 |
| `#bayManualOrderInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 742 |
| `#bayManualItemInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 746 |
| `#bayManualQtyInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 748 |
| `#bayManualSubmitBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 749 |
| `#bayScanOutStatus` | `span` | Indian Trail bay map, receiving scanner, and bay modals | 757 |
| `#bayAllScansBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 758 |
| `#bayLastCard` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 760 |
| `#bayLastBay` | `b` | Indian Trail bay map, receiving scanner, and bay modals | 764 |
| `#bayLastTitle` | `strong` | Indian Trail bay map, receiving scanner, and bay modals | 765 |
| `#bayLastAction` | `b` | Indian Trail bay map, receiving scanner, and bay modals | 768 |
| `#bayLastOrder` | `b` | Indian Trail bay map, receiving scanner, and bay modals | 769 |
| `#bayLastTime` | `b` | Indian Trail bay map, receiving scanner, and bay modals | 770 |
| `#bayLastMoveSelect` | `select` | Indian Trail bay map, receiving scanner, and bay modals | 771 |
| `#bayScanOutRecent` | `tbody` | Indian Trail bay map, receiving scanner, and bay modals | 792 |
| `#bayCategoryFilters` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 814 |
| `#bayAllBaysList` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 815 |
| `#baySelectedBackdrop` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 819 |
| `#baySelectedModal` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 820 |
| `#baySelectedCloseBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 823 |
| `#baySelectedPanel` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 825 |
| `#staleBayBackdrop` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 827 |
| `#staleBayPanel` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 828 |
| `#staleBayCloseBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 831 |
| `#staleBayList` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 834 |
| `#staleBaySnoozeAllDays` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 836 |
| `#staleBaySnoozeAllBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 837 |
| `#staleBayPrintBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 838 |
| `#staleBayOkBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 839 |
| `#sdiBackdrop` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 842 |
| `#sdiPanel` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 843 |
| `#sdiCloseBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 849 |
| `#sdiForm` | `form` | Indian Trail bay map, receiving scanner, and bay modals | 851 |
| `#sdiOrderInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 854 |
| `#sdiBayInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 859 |
| `#sdiTruckExemptInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 862 |
| `#sdiReasonInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 867 |
| `#sdiDeliveryDateInput` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 871 |
| `#sdiTypeInput` | `select` | Indian Trail bay map, receiving scanner, and bay modals | 876 |
| `#sdiCurrentList` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 882 |
| `#sdiClearBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 885 |
| `#manageItemsBackdrop` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 889 |
| `#manageItemsPanel` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 890 |
| `#manageItemsCloseBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 896 |
| `#manageItemsSearch` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 902 |
| `#manageItemsList` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 904 |
| `#manageItemsSelected` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 907 |
| `#manageItemsTargetBay` | `select` | Indian Trail bay map, receiving scanner, and bay modals | 911 |
| `#manageItemsReason` | `input` | Indian Trail bay map, receiving scanner, and bay modals | 915 |
| `#manageItemsMoveBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 919 |
| `#manageItemsClearBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 920 |
| `#manageItemsScannerBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 921 |
| `#manageItemsSdiBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 922 |
| `#manageItemsStatus` | `p` | Indian Trail bay map, receiving scanner, and bay modals | 924 |
| `#bayEditorBackdrop` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 928 |
| `#bayEditorPanel` | `section` | Indian Trail bay map, receiving scanner, and bay modals | 929 |
| `#bayEditorCloseBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 935 |
| `#bayEditorNewGroupBtn` | `button` | Indian Trail bay map, receiving scanner, and bay modals | 939 |
| `#bayEditorGroupList` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 940 |
| `#bayEditorGroupForm` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 944 |
| `#bayEditorBayList` | `div` | Indian Trail bay map, receiving scanner, and bay modals | 945 |
| `#adminPage` | `section` | Administration, users, rules, imports, and configuration | 952 |
| `#adminLastUpdated` | `span` | Administration, users, rules, imports, and configuration | 958 |
| `#adminSummary` | `div` | Administration, users, rules, imports, and configuration | 961 |
| `#folderImportBtn` | `button` | Administration, users, rules, imports, and configuration | 970 |
| `#tempFolderInput` | `input` | Administration, users, rules, imports, and configuration | 976 |
| `#importFromDate` | `input` | Administration, users, rules, imports, and configuration | 979 |
| `#importToDate` | `input` | Administration, users, rules, imports, and configuration | 980 |
| `#importWindowResetBtn` | `button` | Administration, users, rules, imports, and configuration | 981 |
| `#importPreviewBox` | `div` | Administration, users, rules, imports, and configuration | 984 |
| `#adminDeliveryLists` | `div` | Administration, users, rules, imports, and configuration | 985 |
| `#importHistory` | `div` | Administration, users, rules, imports, and configuration | 986 |
| `#adminUsers` | `div` | Administration, users, rules, imports, and configuration | 997 |
| `#customerRouteRules` | `div` | Administration, users, rules, imports, and configuration | 1006 |
| `#customerEmailOverview` | `div` | Administration, users, rules, imports, and configuration | 1014 |
| `#bayScannerRuleOverview` | `div` | Administration, users, rules, imports, and configuration | 1036 |
| `#bayAutoAssignOverview` | `div` | Administration, users, rules, imports, and configuration | 1047 |
| `#manualEditStageSelect` | `select` | Administration, users, rules, imports, and configuration | 1054 |
| `#manualEditSearch` | `input` | Administration, users, rules, imports, and configuration | 1057 |
| `#manualEditSearchBtn` | `button` | Administration, users, rules, imports, and configuration | 1058 |
| `#manualEditResults` | `div` | Administration, users, rules, imports, and configuration | 1059 |
| `#scannerName` | `strong` | Administration, users, rules, imports, and configuration | 1066 |
| `#printOptionsBackdrop` | `div` | Global print and export modal | 1082 |
| `#printOptionsPanel` | `section` | Global print and export modal | 1083 |
| `#printOptionsClose` | `button` | Global print and export modal | 1086 |
| `#printOptionsDate` | `select` | Global print and export modal | 1094 |
| `#printOptionsStages` | `div` | Global print and export modal | 1098 |
| `#printOptionsGlassType` | `div` | Global print and export modal | 1102 |
| `#printCustomerFilter` | `input` | Global print and export modal | 1106 |
| `#printOrderFilter` | `input` | Global print and export modal | 1110 |
| `#printUpdatedOnly` | `input` | Global print and export modal | 1113 |
| `#printRushOnly` | `input` | Global print and export modal | 1114 |
| `#printRemakeOnly` | `input` | Global print and export modal | 1115 |
| `#printOptionsSubmit` | `button` | Global print and export modal | 1117 |
| `#statsChartBackdrop` | `div` | Interactive statistics chart modal | 1121 |
| `#statsChartModal` | `section` | Interactive statistics chart modal | 1122 |
| `#statsChartModalTitle` | `h2` | Interactive statistics chart modal | 1126 |
| `#statsChartModalSubtitle` | `p` | Interactive statistics chart modal | 1127 |
| `#statsChartCloseBtn` | `button` | Interactive statistics chart modal | 1129 |
| `#statsChartRangeSelect` | `select` | Interactive statistics chart modal | 1134 |
| `#statsChartMetricSelect` | `select` | Interactive statistics chart modal | 1145 |
| `#statsChartViewSelect` | `select` | Interactive statistics chart modal | 1160 |
| `#statsChartSortSelect` | `select` | Interactive statistics chart modal | 1167 |
| `#statsChartLimitSelect` | `select` | Interactive statistics chart modal | 1176 |
| `#statsChartFilterInput` | `input` | Interactive statistics chart modal | 1185 |
| `#statsChartResetBtn` | `button` | Interactive statistics chart modal | 1187 |
| `#statsChartKpis` | `div` | Interactive statistics chart modal | 1189 |
| `#statsChartResultCount` | `span` | Interactive statistics chart modal | 1191 |
| `#statsChartModalCanvas` | `div` | Interactive statistics chart modal | 1193 |
| `#adminModalBackdrop` | `div` | Shared administration editor modal | 1197 |
| `#adminModal` | `section` | Shared administration editor modal | 1198 |
| `#adminModalTitle` | `h2` | Shared administration editor modal | 1200 |
| `#adminModalClose` | `button` | Shared administration editor modal | 1201 |
| `#adminModalBody` | `div` | Shared administration editor modal | 1203 |

## CSS ownership sections
| Section | Line |
|---|---:|
| Global design tokens and base element rules | 13 |
| Authentication and password-reset presentation | 92 |
| Responsive rules; preserve desktop ownership selectors above | 350 |
| Global application header, navigation, search, and profile menu | 379 |
| Home dashboard, statistics, and delivery-list finder | 739 |
| Administration panels, users, roles, imports, and route rules | 2231 |
| Main Scan page panel, barcode workflow, history, and tables | 2716 |
| Mobile navigation and compact delivery-list presentation | 3746 |
| Shared modal/backdrop foundations used by feature dialogs | 4901 |
| Rack overview, rack scanner, status, and packing-list controls | 7371 |
| Indian Trail Bay Map, receiving scanner, and bay-management UI | 15623 |

## Safe-edit rules
1. Search for an existing function, selector, route, or translation key before adding one.
2. Keep one business workflow in the store and one rendering/event path in the browser.
3. Add schema changes as idempotent migrations that can open existing floor databases safely.
4. Preserve `source_id` across generated stage copies; stage propagation, Rush/Remake, and route repairs depend on it.
5. Keep SQLite as the default until the Azure cutover is explicitly scheduled and validated.
6. Run `python tools/run_full_validation.py` before packaging a version.
