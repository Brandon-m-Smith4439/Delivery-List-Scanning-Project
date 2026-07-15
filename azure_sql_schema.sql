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
        priority_direct_to_truck int NOT NULL DEFAULT (0)
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
