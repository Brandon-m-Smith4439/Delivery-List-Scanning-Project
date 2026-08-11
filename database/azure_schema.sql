-- File: database/azure_schema.sql
/*
  Delivery List Scanner - Azure SQL schema
  ----------------------------------------
  This script is idempotent. The application runs it during startup when
  DLS_DATABASE_TYPE=azure-sql, so a new Azure SQL database can be initialized
  without maintaining a separate copy of the business logic.
*/

-- Table delivery_lists: One generated stage/list header per delivery date and workflow stage; referenced by line items, scans, printing, and exports.
IF OBJECT_ID(N'dbo.delivery_lists', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.delivery_lists (
        id nvarchar(256) NOT NULL PRIMARY KEY,
        label nvarchar(300) NOT NULL,
        delivery_date nvarchar(32) NOT NULL,
        stage nvarchar(120) NOT NULL,
        scanner nvarchar(120) NOT NULL,
        status nvarchar(40) NOT NULL DEFAULT (N'active'),
        revision int NOT NULL DEFAULT (1),
        created_at nvarchar(64) NOT NULL
    );
END;
GO

-- Table line_items: Physical delivery-list item copies for each stage; source_id links the same glass through its route.
IF OBJECT_ID(N'dbo.line_items', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.line_items (
        id nvarchar(320) NOT NULL PRIMARY KEY,
        list_id nvarchar(256) NOT NULL,
        source_id nvarchar(256) NOT NULL,
        barcode nvarchar(80) NOT NULL,
        order_no nvarchar(80) NOT NULL,
        item_no nvarchar(40) NOT NULL,
        qty int NOT NULL,
        scanned_qty int NOT NULL DEFAULT (0),
        dimensions nvarchar(160) NOT NULL DEFAULT (N''),
        customer nvarchar(300) NOT NULL DEFAULT (N''),
        route nvarchar(80) NOT NULL DEFAULT (N''),
        source_route nvarchar(160) NOT NULL DEFAULT (N''),
        job nvarchar(160) NOT NULL DEFAULT (N''),
        product nvarchar(300) NOT NULL DEFAULT (N''),
        process_state nvarchar(300) NOT NULL DEFAULT (N''),
        queue_state nvarchar(300) NOT NULL DEFAULT (N''),
        suggested_bay nvarchar(120) NOT NULL DEFAULT (N''),
        priority_delivery_date nvarchar(32) NOT NULL DEFAULT (N''),
        priority_direct_to_truck int NOT NULL DEFAULT (0),
        protect_from_aw_import int NOT NULL DEFAULT (0)
    );
    CREATE INDEX idx_line_items_list_id ON dbo.line_items(list_id);
    CREATE INDEX idx_line_items_order_item ON dbo.line_items(order_no, item_no);
END;
GO

-- Table scan_events: Immutable scanner, undo, redo, import, update, and movement history used by recent/all-scans views and audits.
IF OBJECT_ID(N'dbo.scan_events', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.scan_events (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        list_id nvarchar(256) NOT NULL,
        line_item_id nvarchar(320) NULL,
        barcode nvarchar(120) NOT NULL,
        canonical_barcode nvarchar(120) NOT NULL DEFAULT (N''),
        user_name nvarchar(160) NOT NULL DEFAULT (N''),
        station nvarchar(160) NOT NULL DEFAULT (N''),
        event_type nvarchar(80) NOT NULL,
        message nvarchar(1000) NOT NULL,
        reason nvarchar(max) NOT NULL DEFAULT (N''),
        qty_delta int NOT NULL DEFAULT (0),
        created_at nvarchar(64) NOT NULL
    );
    CREATE INDEX idx_scan_events_list_time ON dbo.scan_events(list_id, created_at DESC, id DESC);
END;
GO

-- Table stations: Configured scanner/stage station names available to users and imports.
IF OBJECT_ID(N'dbo.stations', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.stations (
        name nvarchar(160) NOT NULL PRIMARY KEY,
        created_at nvarchar(64) NOT NULL
    );
END;
GO

-- Table customer_route_rules: Customer-name routing source of truth, applied after the CPU-Air Job Nr. override.
IF OBJECT_ID(N'dbo.customer_route_rules', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.customer_route_rules (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        customer_pattern nvarchar(300) NOT NULL UNIQUE,
        route nvarchar(80) NOT NULL,
        customer_address nvarchar(500) NOT NULL DEFAULT (N''),
        active int NOT NULL DEFAULT (1),
        created_at nvarchar(64) NOT NULL,
        updated_at nvarchar(64) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table system_metadata: Version/signature markers for idempotent repairs and startup maintenance.
IF OBJECT_ID(N'dbo.system_metadata', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.system_metadata (
        metadata_key nvarchar(160) NOT NULL PRIMARY KEY,
        value nvarchar(max) NOT NULL DEFAULT (N''),
        updated_at nvarchar(64) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table admin_lookup_values: Editable product, route, process, and manual-edit lookup values.
IF OBJECT_ID(N'dbo.admin_lookup_values', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.admin_lookup_values (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        [type] nvarchar(100) NOT NULL,
        value nvarchar(300) NOT NULL,
        label nvarchar(300) NOT NULL,
        category nvarchar(160) NULL,
        match_terms nvarchar(max) NULL,
        is_active int NOT NULL DEFAULT (1),
        source nvarchar(80) NOT NULL DEFAULT (N'manual'),
        created_at nvarchar(64) NOT NULL,
        updated_at nvarchar(64) NOT NULL,
        CONSTRAINT uq_admin_lookup_type_value UNIQUE ([type], value)
    );
END;
GO

-- Table imports: Delivery-list import/update runs, hashes, quantities, and change summaries.
IF OBJECT_ID(N'dbo.imports', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.imports (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        delivery_date nvarchar(32) NOT NULL,
        source_name nvarchar(500) NOT NULL DEFAULT (N''),
        row_count int NOT NULL DEFAULT (0),
        total_qty int NOT NULL DEFAULT (0),
        cpu_count int NOT NULL DEFAULT (0),
        mirror_count int NOT NULL DEFAULT (0),
        status nvarchar(80) NOT NULL DEFAULT (N'published'),
        imported_by nvarchar(160) NOT NULL DEFAULT (N''),
        imported_at nvarchar(64) NOT NULL,
        source_path nvarchar(1000) NOT NULL DEFAULT (N''),
        source_hash nvarchar(160) NOT NULL DEFAULT (N''),
        import_kind nvarchar(80) NOT NULL DEFAULT (N'manual'),
        change_summary nvarchar(max) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table exceptions: Scan safety exceptions and their resolution history.
IF OBJECT_ID(N'dbo.exceptions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.exceptions (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        list_id nvarchar(256) NOT NULL,
        scan_event_id bigint NULL,
        exception_type nvarchar(120) NOT NULL,
        status nvarchar(80) NOT NULL DEFAULT (N'Open'),
        reason nvarchar(max) NOT NULL DEFAULT (N''),
        created_at nvarchar(64) NOT NULL,
        resolved_by nvarchar(160) NOT NULL DEFAULT (N''),
        resolved_at nvarchar(64) NOT NULL DEFAULT (N''),
        resolution_comment nvarchar(max) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table audit_events: Administrative and high-impact workflow audit trail.
IF OBJECT_ID(N'dbo.audit_events', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.audit_events (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        entity_type nvarchar(120) NOT NULL,
        entity_id nvarchar(320) NOT NULL,
        action nvarchar(160) NOT NULL,
        user_name nvarchar(160) NOT NULL DEFAULT (N''),
        station nvarchar(160) NOT NULL DEFAULT (N''),
        reason nvarchar(max) NOT NULL DEFAULT (N''),
        payload_json nvarchar(max) NOT NULL DEFAULT (N'{}'),
        created_at nvarchar(64) NOT NULL
    );
END;
GO

-- Table users: Local application user accounts and active/inactive status.
IF OBJECT_ID(N'dbo.users', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.users (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        username nvarchar(160) NOT NULL UNIQUE,
        email nvarchar(320) NOT NULL DEFAULT (N''),
        display_name nvarchar(240) NOT NULL DEFAULT (N''),
        password_hash nvarchar(800) NOT NULL DEFAULT (N''),
        active int NOT NULL DEFAULT (1),
        created_at nvarchar(64) NOT NULL,
        station nvarchar(160) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table roles: Named application roles used to group permissions and stage access.
IF OBJECT_ID(N'dbo.roles', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.roles (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        name nvarchar(160) NOT NULL UNIQUE,
        description nvarchar(1000) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table permissions: Canonical permission keys available to roles.
IF OBJECT_ID(N'dbo.permissions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.permissions (
        name nvarchar(160) NOT NULL PRIMARY KEY,
        description nvarchar(1000) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table role_permissions: Many-to-many mapping between roles and permission keys.
IF OBJECT_ID(N'dbo.role_permissions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.role_permissions (
        role_id bigint NOT NULL,
        permission_name nvarchar(160) NOT NULL,
        CONSTRAINT pk_role_permissions PRIMARY KEY (role_id, permission_name)
    );
END;
GO

-- Table user_roles: Many-to-many mapping between users and assigned roles.
IF OBJECT_ID(N'dbo.user_roles', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.user_roles (
        user_id bigint NOT NULL,
        role_id bigint NOT NULL,
        CONSTRAINT pk_user_roles PRIMARY KEY (user_id, role_id)
    );
END;
GO

-- Table sessions: Authenticated user sessions and expiration metadata.
IF OBJECT_ID(N'dbo.sessions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.sessions (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        user_id bigint NOT NULL,
        token_hash nvarchar(300) NOT NULL UNIQUE,
        created_at nvarchar(64) NOT NULL,
        expires_at nvarchar(64) NOT NULL,
        last_seen_at nvarchar(64) NOT NULL,
        user_agent nvarchar(1000) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table password_reset_tokens: Short-lived local password-reset codes and completion state.
IF OBJECT_ID(N'dbo.password_reset_tokens', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.password_reset_tokens (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        user_id bigint NOT NULL,
        code_hash nvarchar(500) NOT NULL,
        created_at nvarchar(64) NOT NULL,
        expires_at nvarchar(64) NOT NULL,
        used_at nvarchar(64) NOT NULL DEFAULT (N''),
        requested_by nvarchar(160) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table bays: Indian Trail physical bay definitions, ordering, capacity type, status, and group layout.
IF OBJECT_ID(N'dbo.bays', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.bays (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        bay_code nvarchar(160) NOT NULL UNIQUE,
        area nvarchar(160) NOT NULL DEFAULT (N''),
        bay_type nvarchar(160) NOT NULL DEFAULT (N'Standard'),
        capacity_qty int NOT NULL DEFAULT (0),
        max_width float NOT NULL DEFAULT (0),
        max_height float NOT NULL DEFAULT (0),
        sort_order int NOT NULL DEFAULT (0),
        active int NOT NULL DEFAULT (1),
        display_name nvarchar(300) NOT NULL DEFAULT (N''),
        map_section nvarchar(300) NOT NULL DEFAULT (N''),
        bay_category nvarchar(160) NOT NULL DEFAULT (N''),
        source_cell nvarchar(120) NOT NULL DEFAULT (N''),
        layout_row int NULL,
        layout_col int NULL,
        layout_cell nvarchar(120) NOT NULL DEFAULT (N''),
        status nvarchar(80) NOT NULL DEFAULT (N'Available')
    );
END;
GO

-- Table bay_assignments: Current and cleared item-to-bay assignments; preserves movement history fields.
IF OBJECT_ID(N'dbo.bay_assignments', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.bay_assignments (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        delivery_list_id nvarchar(256) NOT NULL,
        line_item_id nvarchar(320) NOT NULL,
        bay_id bigint NULL,
        assigned_qty int NOT NULL DEFAULT (0),
        status nvarchar(80) NOT NULL DEFAULT (N'Assigned'),
        assigned_by nvarchar(160) NOT NULL DEFAULT (N''),
        assigned_at nvarchar(64) NOT NULL,
        cleared_by nvarchar(160) NOT NULL DEFAULT (N''),
        cleared_at nvarchar(64) NOT NULL DEFAULT (N''),
        reason nvarchar(max) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table bay_events: Indian Trail receive, move, clear, SDI, and bay scanner event history.
IF OBJECT_ID(N'dbo.bay_events', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.bay_events (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        bay_id bigint NULL,
        line_item_id nvarchar(320) NOT NULL DEFAULT (N''),
        event_type nvarchar(120) NOT NULL,
        old_bay_id bigint NULL,
        new_bay_id bigint NULL,
        reason nvarchar(max) NOT NULL DEFAULT (N''),
        user_name nvarchar(160) NOT NULL DEFAULT (N''),
        created_at nvarchar(64) NOT NULL
    );
END;
GO

-- Table racks: Physical rack master records, destinations, status, rack sets, and transit timestamps.
IF OBJECT_ID(N'dbo.racks', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.racks (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        rack_code nvarchar(160) NOT NULL UNIQUE,
        display_name nvarchar(300) NOT NULL DEFAULT (N''),
        rack_type nvarchar(160) NOT NULL DEFAULT (N'Steel'),
        status nvarchar(80) NOT NULL DEFAULT (N'Open'),
        active int NOT NULL DEFAULT (1),
        sort_order int NOT NULL DEFAULT (0),
        created_at nvarchar(64) NOT NULL,
        updated_at nvarchar(64) NOT NULL DEFAULT (N''),
        destination nvarchar(160) NOT NULL DEFAULT (N''),
        completed_at nvarchar(64) NOT NULL DEFAULT (N''),
        departed_at nvarchar(64) NOT NULL DEFAULT (N''),
        returned_at nvarchar(64) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table rack_items: Current and historical item-to-rack assignments used by staging/outbound workflows.
IF OBJECT_ID(N'dbo.rack_items', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.rack_items (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        rack_id bigint NOT NULL,
        line_item_id nvarchar(320) NOT NULL,
        qty int NOT NULL DEFAULT (1),
        status nvarchar(80) NOT NULL DEFAULT (N'Active'),
        added_by nvarchar(160) NOT NULL DEFAULT (N''),
        added_at nvarchar(64) NOT NULL,
        removed_by nvarchar(160) NOT NULL DEFAULT (N''),
        removed_at nvarchar(64) NOT NULL DEFAULT (N''),
        reason nvarchar(max) NOT NULL DEFAULT (N''),
        destination_override nvarchar(160) NOT NULL DEFAULT (N''),
        CONSTRAINT uq_rack_items_rack_line UNIQUE (rack_id, line_item_id)
    );
END;
GO

-- Table bay_stale_snoozes: Per-job temporary suppression of stale-bay alerts.
IF OBJECT_ID(N'dbo.bay_stale_snoozes', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.bay_stale_snoozes (
        assignment_id bigint NOT NULL PRIMARY KEY,
        snoozed_until nvarchar(64) NOT NULL,
        snoozed_by nvarchar(160) NOT NULL DEFAULT (N''),
        updated_at nvarchar(64) NOT NULL
    );
END;
GO

-- Table bay_manual_input_rules: Remembered manual bay choices derived from operator-entered order/job data.
IF OBJECT_ID(N'dbo.bay_manual_input_rules', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.bay_manual_input_rules (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        match_type nvarchar(80) NOT NULL DEFAULT (N'exact'),
        pattern nvarchar(500) NOT NULL,
        normalized_pattern nvarchar(500) NOT NULL DEFAULT (N''),
        label nvarchar(300) NOT NULL DEFAULT (N''),
        active int NOT NULL DEFAULT (1),
        created_by nvarchar(160) NOT NULL DEFAULT (N''),
        created_at nvarchar(64) NOT NULL,
        updated_at nvarchar(64) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table bay_scan_barcode_rules: Remembered barcode-to-bay rules for Indian Trail scanning.
IF OBJECT_ID(N'dbo.bay_scan_barcode_rules', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.bay_scan_barcode_rules (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        pattern nvarchar(500) NOT NULL,
        label nvarchar(300) NOT NULL DEFAULT (N''),
        active int NOT NULL DEFAULT (1),
        created_by nvarchar(160) NOT NULL DEFAULT (N''),
        created_at nvarchar(64) NOT NULL,
        updated_at nvarchar(64) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table bay_auto_assign_settings: Configurable size/type thresholds used by automatic bay assignment.
IF OBJECT_ID(N'dbo.bay_auto_assign_settings', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.bay_auto_assign_settings (
        [key] nvarchar(160) NOT NULL PRIMARY KEY,
        value nvarchar(max) NOT NULL DEFAULT (N''),
        updated_by nvarchar(160) NOT NULL DEFAULT (N''),
        updated_at nvarchar(64) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table customer_email_contacts: Per-customer manifest and ready-notification recipient configuration.
IF OBJECT_ID(N'dbo.customer_email_contacts', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.customer_email_contacts (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        customer_pattern nvarchar(300) NOT NULL,
        email nvarchar(320) NOT NULL,
        active int NOT NULL DEFAULT (1),
        created_at nvarchar(64) NOT NULL,
        updated_at nvarchar(64) NOT NULL DEFAULT (N''),
        CONSTRAINT uq_customer_email_contact UNIQUE (customer_pattern, email)
    );
END;
GO

-- Table customer_email_cc: Global customer-email CC recipients.
IF OBJECT_ID(N'dbo.customer_email_cc', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.customer_email_cc (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        email nvarchar(320) NOT NULL UNIQUE,
        active int NOT NULL DEFAULT (1),
        created_at nvarchar(64) NOT NULL,
        updated_at nvarchar(64) NOT NULL DEFAULT (N'')
    );
END;
GO

-- Table email_outbox: Queued/sent/failed email records and rendered manifest payloads.
IF OBJECT_ID(N'dbo.email_outbox', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.email_outbox (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        email_type nvarchar(120) NOT NULL,
        customer_name nvarchar(300) NOT NULL DEFAULT (N''),
        customer_pattern nvarchar(300) NOT NULL DEFAULT (N''),
        delivery_date nvarchar(32) NOT NULL DEFAULT (N''),
        to_emails nvarchar(max) NOT NULL DEFAULT (N'[]'),
        cc_emails nvarchar(max) NOT NULL DEFAULT (N'[]'),
        subject nvarchar(1000) NOT NULL DEFAULT (N''),
        body nvarchar(max) NOT NULL DEFAULT (N''),
        status nvarchar(80) NOT NULL DEFAULT (N'draft'),
        created_at nvarchar(64) NOT NULL,
        sent_at nvarchar(64) NOT NULL DEFAULT (N''),
        error nvarchar(max) NOT NULL DEFAULT (N''),
        payload_json nvarchar(max) NOT NULL DEFAULT (N'{}')
    );
END;
GO

-- Table app_notifications: Multi-user application notifications such as Rush alerts.
IF OBJECT_ID(N'dbo.app_notifications', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.app_notifications (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        notification_type nvarchar(120) NOT NULL DEFAULT (N'notice'),
        title nvarchar(500) NOT NULL DEFAULT (N''),
        message nvarchar(max) NOT NULL DEFAULT (N''),
        payload_json nvarchar(max) NOT NULL DEFAULT (N'{}'),
        created_by nvarchar(160) NOT NULL DEFAULT (N''),
        created_at nvarchar(64) NOT NULL,
        expires_at nvarchar(64) NOT NULL DEFAULT (N''),
        active int NOT NULL DEFAULT (1)
    );
    CREATE INDEX idx_app_notifications_active_time ON dbo.app_notifications(active, created_at DESC, id DESC);
END;
GO

-- Table app_notification_receipts: Per-user notification acknowledgment state so one user cannot consume another user’s alert.
IF OBJECT_ID(N'dbo.app_notification_receipts', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.app_notification_receipts (
        notification_id bigint NOT NULL,
        user_id bigint NOT NULL,
        acknowledged_at nvarchar(64) NOT NULL,
        CONSTRAINT pk_app_notification_receipts PRIMARY KEY (notification_id, user_id)
    );
END;
GO

-- v097 canonical migration history. Checksums are written by the application
-- migration runner after this idempotent schema script completes.
IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.schema_migrations (
        version int NOT NULL PRIMARY KEY,
        name nvarchar(255) NOT NULL,
        checksum char(64) NOT NULL,
        applied_at_utc datetime2(0) NOT NULL DEFAULT (SYSUTCDATETIME()),
        execution_ms int NOT NULL DEFAULT (0),
        app_version nvarchar(32) NOT NULL DEFAULT (N''),
        CONSTRAINT ck_schema_migrations_execution_ms CHECK (execution_ms >= 0)
    );
END;
GO

-- v097 UTC audit and soft-delete fields. These are additive so an existing
-- Azure readiness database can be upgraded without replacing any table.
DECLARE @audit_tables TABLE (table_name sysname NOT NULL PRIMARY KEY);
INSERT INTO @audit_tables (table_name) VALUES
    (N'delivery_lists'), (N'line_items'), (N'users'), (N'bays'),
    (N'bay_assignments'), (N'racks'), (N'rack_items'),
    (N'customer_route_rules'), (N'admin_lookup_values');

DECLARE @table_name sysname;
DECLARE audit_cursor CURSOR LOCAL FAST_FORWARD FOR SELECT table_name FROM @audit_tables;
OPEN audit_cursor;
FETCH NEXT FROM audit_cursor INTO @table_name;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF COL_LENGTH(N'dbo.' + @table_name, N'created_at_utc') IS NULL
        EXEC(N'ALTER TABLE dbo.' + QUOTENAME(@table_name) + N' ADD created_at_utc datetime2(0) NOT NULL CONSTRAINT ' + QUOTENAME(N'df_' + @table_name + N'_created_at_utc') + N' DEFAULT (SYSUTCDATETIME()) WITH VALUES');
    IF COL_LENGTH(N'dbo.' + @table_name, N'created_by_user_id') IS NULL
        EXEC(N'ALTER TABLE dbo.' + QUOTENAME(@table_name) + N' ADD created_by_user_id bigint NULL');
    IF COL_LENGTH(N'dbo.' + @table_name, N'updated_at_utc') IS NULL
        EXEC(N'ALTER TABLE dbo.' + QUOTENAME(@table_name) + N' ADD updated_at_utc datetime2(0) NOT NULL CONSTRAINT ' + QUOTENAME(N'df_' + @table_name + N'_updated_at_utc') + N' DEFAULT (SYSUTCDATETIME()) WITH VALUES');
    IF COL_LENGTH(N'dbo.' + @table_name, N'updated_by_user_id') IS NULL
        EXEC(N'ALTER TABLE dbo.' + QUOTENAME(@table_name) + N' ADD updated_by_user_id bigint NULL');
    IF COL_LENGTH(N'dbo.' + @table_name, N'is_deleted') IS NULL
        EXEC(N'ALTER TABLE dbo.' + QUOTENAME(@table_name) + N' ADD is_deleted bit NOT NULL CONSTRAINT ' + QUOTENAME(N'df_' + @table_name + N'_is_deleted') + N' DEFAULT (0) WITH VALUES');
    IF COL_LENGTH(N'dbo.' + @table_name, N'deleted_at_utc') IS NULL
        EXEC(N'ALTER TABLE dbo.' + QUOTENAME(@table_name) + N' ADD deleted_at_utc datetime2(0) NULL');
    IF COL_LENGTH(N'dbo.' + @table_name, N'deleted_by_user_id') IS NULL
        EXEC(N'ALTER TABLE dbo.' + QUOTENAME(@table_name) + N' ADD deleted_by_user_id bigint NULL');
    FETCH NEXT FROM audit_cursor INTO @table_name;
END;
CLOSE audit_cursor;
DEALLOCATE audit_cursor;
GO

-- Future production-machine integration. Business identifiers intentionally
-- remain text even when their current values happen to be numeric.
IF OBJECT_ID(N'dbo.machines', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.machines (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        machine_code nvarchar(255) NOT NULL UNIQUE,
        display_name nvarchar(500) NOT NULL DEFAULT (N''),
        machine_type nvarchar(255) NOT NULL DEFAULT (N''),
        location nvarchar(500) NOT NULL DEFAULT (N''),
        active bit NOT NULL DEFAULT (1),
        metadata_json nvarchar(max) NOT NULL DEFAULT (N'{}'),
        created_at_utc datetime2(0) NOT NULL DEFAULT (SYSUTCDATETIME()),
        created_by_user_id bigint NULL,
        updated_at_utc datetime2(0) NOT NULL DEFAULT (SYSUTCDATETIME()),
        updated_by_user_id bigint NULL,
        is_deleted bit NOT NULL DEFAULT (0),
        deleted_at_utc datetime2(0) NULL,
        deleted_by_user_id bigint NULL,
        CONSTRAINT ck_machines_metadata_json CHECK (ISJSON(metadata_json) = 1)
    );
END;
GO

IF OBJECT_ID(N'dbo.scanners', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.scanners (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        scanner_code nvarchar(255) NOT NULL UNIQUE,
        display_name nvarchar(500) NOT NULL DEFAULT (N''),
        station_name nvarchar(255) NOT NULL DEFAULT (N''),
        machine_id bigint NULL,
        device_identifier nvarchar(500) NOT NULL DEFAULT (N''),
        active bit NOT NULL DEFAULT (1),
        last_seen_at_utc datetime2(0) NULL,
        metadata_json nvarchar(max) NOT NULL DEFAULT (N'{}'),
        created_at_utc datetime2(0) NOT NULL DEFAULT (SYSUTCDATETIME()),
        created_by_user_id bigint NULL,
        updated_at_utc datetime2(0) NOT NULL DEFAULT (SYSUTCDATETIME()),
        updated_by_user_id bigint NULL,
        is_deleted bit NOT NULL DEFAULT (0),
        deleted_at_utc datetime2(0) NULL,
        deleted_by_user_id bigint NULL,
        CONSTRAINT fk_scanners_machine FOREIGN KEY (machine_id) REFERENCES dbo.machines(id) ON DELETE SET NULL,
        CONSTRAINT ck_scanners_metadata_json CHECK (ISJSON(metadata_json) = 1)
    );
END;
GO

IF OBJECT_ID(N'dbo.machine_events', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.machine_events (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        machine_id bigint NULL,
        scanner_id bigint NULL,
        line_item_id nvarchar(255) NULL,
        event_type nvarchar(255) NOT NULL,
        event_status nvarchar(255) NOT NULL DEFAULT (N''),
        qty int NOT NULL DEFAULT (0),
        barcode nvarchar(255) NOT NULL DEFAULT (N''),
        order_no nvarchar(255) NOT NULL DEFAULT (N''),
        item_no nvarchar(255) NOT NULL DEFAULT (N''),
        metadata_json nvarchar(max) NOT NULL DEFAULT (N'{}'),
        created_at_utc datetime2(0) NOT NULL DEFAULT (SYSUTCDATETIME()),
        created_by_user_id bigint NULL,
        CONSTRAINT fk_machine_events_machine FOREIGN KEY (machine_id) REFERENCES dbo.machines(id) ON DELETE SET NULL,
        CONSTRAINT fk_machine_events_scanner FOREIGN KEY (scanner_id) REFERENCES dbo.scanners(id) ON DELETE SET NULL,
        CONSTRAINT fk_machine_events_line_item FOREIGN KEY (line_item_id) REFERENCES dbo.line_items(id) ON DELETE SET NULL,
        CONSTRAINT ck_machine_events_qty CHECK (qty >= 0),
        CONSTRAINT ck_machine_events_metadata_json CHECK (ISJSON(metadata_json) = 1)
    );
END;
GO

-- Core constraints are added only when absent and WITH CHECK validates all
-- existing rows before SQL Server begins enforcing future writes.
IF OBJECT_ID(N'dbo.ck_line_items_qty', N'C') IS NULL
    ALTER TABLE dbo.line_items WITH CHECK ADD CONSTRAINT ck_line_items_qty CHECK (qty >= 0 AND scanned_qty >= 0 AND scanned_qty <= qty);
IF OBJECT_ID(N'dbo.ck_line_items_priority_direct', N'C') IS NULL
    ALTER TABLE dbo.line_items WITH CHECK ADD CONSTRAINT ck_line_items_priority_direct CHECK (priority_direct_to_truck IN (0, 1));
IF OBJECT_ID(N'dbo.ck_rack_items_qty', N'C') IS NULL
    ALTER TABLE dbo.rack_items WITH CHECK ADD CONSTRAINT ck_rack_items_qty CHECK (qty > 0);
IF OBJECT_ID(N'dbo.ck_bay_assignments_qty', N'C') IS NULL
    ALTER TABLE dbo.bay_assignments WITH CHECK ADD CONSTRAINT ck_bay_assignments_qty CHECK (assigned_qty >= 0);
GO

-- Missing safe relationships from the v096 readiness schema.
IF OBJECT_ID(N'dbo.fk_exceptions_delivery_list', N'F') IS NULL
    ALTER TABLE dbo.exceptions WITH CHECK ADD CONSTRAINT fk_exceptions_delivery_list FOREIGN KEY (list_id) REFERENCES dbo.delivery_lists(id) ON DELETE CASCADE;
IF OBJECT_ID(N'dbo.fk_bay_assignments_delivery_list', N'F') IS NULL
    ALTER TABLE dbo.bay_assignments WITH CHECK ADD CONSTRAINT fk_bay_assignments_delivery_list FOREIGN KEY (delivery_list_id) REFERENCES dbo.delivery_lists(id) ON DELETE CASCADE;
IF OBJECT_ID(N'dbo.fk_notification_receipts_notification', N'F') IS NULL
    ALTER TABLE dbo.app_notification_receipts WITH CHECK ADD CONSTRAINT fk_notification_receipts_notification FOREIGN KEY (notification_id) REFERENCES dbo.app_notifications(id) ON DELETE CASCADE;
IF OBJECT_ID(N'dbo.fk_notification_receipts_user', N'F') IS NULL
    ALTER TABLE dbo.app_notification_receipts WITH CHECK ADD CONSTRAINT fk_notification_receipts_user FOREIGN KEY (user_id) REFERENCES dbo.users(id) ON DELETE CASCADE;
GO

-- Query-driven indexes shared logically with SQLite v097.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.delivery_lists') AND name = N'idx_delivery_lists_date_status_stage')
    CREATE INDEX idx_delivery_lists_date_status_stage ON dbo.delivery_lists(delivery_date, status, stage);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.line_items') AND name = N'idx_line_items_list_order_item')
    CREATE INDEX idx_line_items_list_order_item ON dbo.line_items(list_id, order_no, item_no);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.line_items') AND name = N'idx_line_items_source')
    CREATE INDEX idx_line_items_source ON dbo.line_items(source_id, list_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.line_items') AND name = N'idx_line_items_barcode')
    CREATE INDEX idx_line_items_barcode ON dbo.line_items(barcode, list_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.scan_events') AND name = N'idx_scan_events_line_time')
    CREATE INDEX idx_scan_events_line_time ON dbo.scan_events(line_item_id, created_at DESC, id DESC);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.imports') AND name = N'idx_imports_date_time')
    CREATE INDEX idx_imports_date_time ON dbo.imports(delivery_date, imported_at DESC, id DESC);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.exceptions') AND name = N'idx_exceptions_list_status')
    CREATE INDEX idx_exceptions_list_status ON dbo.exceptions(list_id, status, created_at DESC);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.audit_events') AND name = N'idx_audit_events_entity_time')
    CREATE INDEX idx_audit_events_entity_time ON dbo.audit_events(entity_type, entity_id, created_at DESC, id DESC);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.sessions') AND name = N'idx_sessions_user_expiry')
    CREATE INDEX idx_sessions_user_expiry ON dbo.sessions(user_id, expires_at);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.bay_assignments') AND name = N'idx_bay_assignments_line_status')
    CREATE INDEX idx_bay_assignments_line_status ON dbo.bay_assignments(line_item_id, status);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.bay_assignments') AND name = N'idx_bay_assignments_bay_status')
    CREATE INDEX idx_bay_assignments_bay_status ON dbo.bay_assignments(bay_id, status);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.bay_events') AND name = N'idx_bay_events_bay_time')
    CREATE INDEX idx_bay_events_bay_time ON dbo.bay_events(bay_id, created_at DESC, id DESC);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.rack_items') AND name = N'idx_rack_items_rack_status')
    CREATE INDEX idx_rack_items_rack_status ON dbo.rack_items(rack_id, status);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.rack_items') AND name = N'idx_rack_items_line_status')
    CREATE INDEX idx_rack_items_line_status ON dbo.rack_items(line_item_id, status);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.machine_events') AND name = N'idx_machine_events_machine_time')
    CREATE INDEX idx_machine_events_machine_time ON dbo.machine_events(machine_id, created_at_utc DESC, id DESC);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.machine_events') AND name = N'idx_machine_events_scanner_time')
    CREATE INDEX idx_machine_events_scanner_time ON dbo.machine_events(scanner_id, created_at_utc DESC, id DESC);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.machine_events') AND name = N'idx_machine_events_order_item')
    CREATE INDEX idx_machine_events_order_item ON dbo.machine_events(order_no, item_no, created_at_utc DESC);
GO

-- Immutable event histories. Corrections are represented by new reversal or
-- superseding events instead of changing the original record.
CREATE OR ALTER TRIGGER dbo.trg_scan_events_append_only
ON dbo.scan_events
INSTEAD OF UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    THROW 50001, 'scan_events is append-only; write a reversal event instead.', 1;
END;
GO

CREATE OR ALTER TRIGGER dbo.trg_audit_events_append_only
ON dbo.audit_events
INSTEAD OF UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    THROW 50002, 'audit_events is append-only; write a superseding audit event instead.', 1;
END;
GO

CREATE OR ALTER TRIGGER dbo.trg_machine_events_append_only
ON dbo.machine_events
INSTEAD OF UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    THROW 50003, 'machine_events is append-only; write a reversal event instead.', 1;
END;
GO

-- v0.230: Preserve import-preview details for source rows removed by A+W.
IF OBJECT_ID(N'dbo.line_update_notices', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.line_update_notices (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        line_item_id nvarchar(320) NOT NULL,
        list_id nvarchar(256) NOT NULL,
        delivery_date nvarchar(32) NOT NULL,
        change_type nvarchar(40) NOT NULL,
        change_token nvarchar(160) NOT NULL,
        source_hash nvarchar(160) NOT NULL DEFAULT (N''),
        snapshot_json nvarchar(max) NOT NULL DEFAULT (N'{}'),
        created_at nvarchar(64) NOT NULL,
        CONSTRAINT ck_line_update_notices_change_type_v230
            CHECK (change_type IN (N'new', N'updated', N'removed')),
        CONSTRAINT ck_line_update_notices_snapshot_json_v230
            CHECK (ISJSON(snapshot_json) = 1),
        CONSTRAINT uq_line_update_notices_token_v230
            UNIQUE (line_item_id, change_type, change_token)
    );
END;
GO

IF COL_LENGTH(N'dbo.line_update_notices', N'snapshot_json') IS NULL
BEGIN
    ALTER TABLE dbo.line_update_notices
        ADD snapshot_json nvarchar(max) NOT NULL
            CONSTRAINT df_line_update_notices_snapshot_json_v230 DEFAULT (N'{}');
END;
GO

DECLARE @line_update_change_constraint sysname;
SELECT TOP (1) @line_update_change_constraint = cc.name
FROM sys.check_constraints cc
WHERE cc.parent_object_id = OBJECT_ID(N'dbo.line_update_notices')
  AND cc.definition LIKE N'%change_type%';
IF @line_update_change_constraint IS NOT NULL
BEGIN
    EXEC(N'ALTER TABLE dbo.line_update_notices DROP CONSTRAINT ['
        + REPLACE(@line_update_change_constraint, N']', N']]') + N']');
END;
IF OBJECT_ID(N'dbo.ck_line_update_notices_change_type_v230', N'C') IS NULL
BEGIN
    ALTER TABLE dbo.line_update_notices WITH CHECK
        ADD CONSTRAINT ck_line_update_notices_change_type_v230
        CHECK (change_type IN (N'new', N'updated', N'removed'));
END;
GO

IF OBJECT_ID(N'dbo.line_update_receipts', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.line_update_receipts (
        notice_id bigint NOT NULL,
        user_id bigint NOT NULL,
        seen_at nvarchar(64) NOT NULL,
        CONSTRAINT pk_line_update_receipts PRIMARY KEY (notice_id, user_id),
        CONSTRAINT fk_line_update_receipts_notice
            FOREIGN KEY (notice_id) REFERENCES dbo.line_update_notices(id) ON DELETE CASCADE,
        CONSTRAINT fk_line_update_receipts_user
            FOREIGN KEY (user_id) REFERENCES dbo.users(id) ON DELETE CASCADE
    );
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.line_update_notices')
      AND name = N'idx_line_update_notices_list_date'
)
    CREATE INDEX idx_line_update_notices_list_date
        ON dbo.line_update_notices(list_id, delivery_date, created_at DESC, id DESC);
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.line_update_receipts')
      AND name = N'idx_line_update_receipts_user'
)
    CREATE INDEX idx_line_update_receipts_user
        ON dbo.line_update_receipts(user_id, notice_id);
GO


-- v0.236: Explicitly protect selected manual orders from authoritative A+W replacement.
IF COL_LENGTH(N'dbo.line_items', N'protect_from_aw_import') IS NULL
BEGIN
    ALTER TABLE dbo.line_items
        ADD protect_from_aw_import int NOT NULL
            CONSTRAINT df_line_items_protect_from_aw_import_v236 DEFAULT (0);
END;
GO

IF OBJECT_ID(N'dbo.manual_delivery_entries', N'U') IS NOT NULL
   AND COL_LENGTH(N'dbo.manual_delivery_entries', N'protect_from_aw_import') IS NULL
BEGIN
    ALTER TABLE dbo.manual_delivery_entries
        ADD protect_from_aw_import int NOT NULL
            CONSTRAINT df_manual_delivery_entries_protect_from_aw_import_v236 DEFAULT (0);
END;
GO


-- v0.245: Local/Admin superseded-order review decisions and exact-key evidence.
IF OBJECT_ID(N'dbo.superseded_order_reviews', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.superseded_order_reviews (
        id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        candidate_key nvarchar(500) NOT NULL UNIQUE,
        delivery_date nvarchar(32) NOT NULL,
        header_identity nvarchar(160) NOT NULL DEFAULT (N''),
        original_order_no nvarchar(120) NOT NULL,
        replacement_order_no nvarchar(120) NOT NULL,
        status nvarchar(40) NOT NULL DEFAULT (N'pending'),
        confidence nvarchar(40) NOT NULL DEFAULT (N'high'),
        evidence_json nvarchar(max) NOT NULL DEFAULT (N'{}'),
        original_items_json nvarchar(max) NOT NULL DEFAULT (N'[]'),
        replacement_items_json nvarchar(max) NOT NULL DEFAULT (N'[]'),
        source_fingerprint nvarchar(160) NOT NULL DEFAULT (N''),
        detected_at nvarchar(64) NOT NULL,
        last_seen_at nvarchar(64) NOT NULL,
        decided_at nvarchar(64) NOT NULL DEFAULT (N''),
        decided_by nvarchar(255) NOT NULL DEFAULT (N''),
        decision_reason nvarchar(1000) NOT NULL DEFAULT (N''),
        approved_remove_order_no nvarchar(120) NOT NULL DEFAULT (N''),
        active int NOT NULL DEFAULT (1),
        created_at_utc nvarchar(64) NOT NULL DEFAULT (N''),
        updated_at_utc nvarchar(64) NOT NULL DEFAULT (N''),
        CONSTRAINT ck_superseded_order_reviews_status_v245
            CHECK (status IN (N'pending', N'approved', N'keep_both', N'review_later')),
        CONSTRAINT ck_superseded_order_reviews_active_v245 CHECK (active IN (0, 1)),
        CONSTRAINT ck_superseded_order_reviews_evidence_json_v245 CHECK (ISJSON(evidence_json) = 1),
        CONSTRAINT ck_superseded_order_reviews_original_json_v245 CHECK (ISJSON(original_items_json) = 1),
        CONSTRAINT ck_superseded_order_reviews_replacement_json_v245 CHECK (ISJSON(replacement_items_json) = 1)
    );
END;
GO

-- v0.257: Admin may choose either candidate order as the exact removal target.
IF COL_LENGTH(N'dbo.superseded_order_reviews', N'approved_remove_order_no') IS NULL
BEGIN
    ALTER TABLE dbo.superseded_order_reviews
        ADD approved_remove_order_no nvarchar(120) NOT NULL
            CONSTRAINT df_superseded_order_reviews_remove_order_v257 DEFAULT (N'');
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.superseded_order_reviews')
      AND name = N'idx_superseded_order_reviews_status_date'
)
    CREATE INDEX idx_superseded_order_reviews_status_date
        ON dbo.superseded_order_reviews(status, active, delivery_date DESC, last_seen_at DESC, id DESC);
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.superseded_order_reviews')
      AND name = N'idx_superseded_order_reviews_orders'
)
    CREATE INDEX idx_superseded_order_reviews_orders
        ON dbo.superseded_order_reviews(delivery_date, original_order_no, replacement_order_no);
GO
