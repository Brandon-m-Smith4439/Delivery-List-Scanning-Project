"""Azure SQL compatibility layer for the delivery-list scanner.

The business layer was originally written against Python's sqlite3 connection API.
This module provides a small pyodbc-backed adapter with the same execute/fetch
shape and translates the limited SQLite SQL dialect used by the application into
T-SQL. Keeping the translation at the connection boundary prevents a second copy
of the scanner business rules from developing for Azure SQL.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any


UNIQUE_KEY_COLUMNS: dict[str, tuple[str, ...]] = {
    "app_notification_receipts": ("notification_id", "user_id"),
    "bay_auto_assign_settings": ("key",),
    "bays": ("bay_code",),
    "customer_route_rules": ("customer_pattern",),
    "permissions": ("name",),
    "racks": ("rack_code",),
    "role_permissions": ("role_id", "permission_name"),
    "roles": ("name",),
    "stations": ("name",),
    "user_roles": ("user_id", "role_id"),
}


class AzureSqlDependencyError(RuntimeError):
    """Raised when the optional Azure SQL runtime dependencies are unavailable."""


def _load_sql_dependencies():
    """Purpose: Load SQL dependencies for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    try:
        import pyodbc  # type: ignore
        import sqlglot  # type: ignore
        from sqlglot import expressions as exp  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on deployment image
        raise AzureSqlDependencyError(
            "Azure SQL mode requires the packages in requirements.txt and Microsoft ODBC Driver 18 for SQL Server."
        ) from exc
    return pyodbc, sqlglot, exp


class AzureSqlRow(Mapping[str, Any]):
    """Mapping/sequence hybrid matching the sqlite3.Row features used by the app."""

    def __init__(self, columns: Sequence[str], values: Sequence[Any]):
        """Purpose: Initialize a Azure SQL row instance and its required state.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        self._columns = tuple(str(column) for column in columns)
        self._values = tuple(values)
        self._index: dict[str, int] = {}
        for index, column in enumerate(self._columns):
            self._index.setdefault(column, index)

    def __getitem__(self, key: str | int) -> Any:
        """Purpose: Implement the getitem protocol for Azure SQL row.

        Effects: This function reads or updates shared application state.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._index[key]]

    def __iter__(self) -> Iterator[str]:
        """Purpose: Implement the iter protocol for Azure SQL row.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return iter(self._columns)

    def __len__(self) -> int:
        """Purpose: Implement the len protocol for Azure SQL row.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return len(self._columns)

    def keys(self):
        """Purpose: Run the keys workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return self._columns

    def values(self):
        """Purpose: Run the values workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return self._values

    def items(self):
        """Purpose: Run the items workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return tuple(zip(self._columns, self._values))


@dataclass
class AzureSqlMemoryCursor:
    columns: tuple[str, ...] = ()
    rows: tuple[tuple[Any, ...], ...] = ()
    rowcount: int = 0
    lastrowid: int | None = None

    def fetchone(self) -> AzureSqlRow | None:
        """Purpose: Run the fetchone workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        if not self.rows:
            return None
        row = self.rows[0]
        self.rows = self.rows[1:]
        return AzureSqlRow(self.columns, row)

    def fetchall(self) -> list[AzureSqlRow]:
        """Purpose: Run the fetchall workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        rows = [AzureSqlRow(self.columns, row) for row in self.rows]
        self.rows = ()
        return rows

    def __iter__(self) -> Iterator[AzureSqlRow]:
        """Purpose: Implement the iter protocol for Azure SQL memory cursor.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return iter(self.fetchall())


class AzureSqlCursor:
    def __init__(self, cursor: Any, *, lastrowid: int | None = None, rowcount: int | None = None):
        """Purpose: Initialize a Azure SQL cursor instance and its required state.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        self._cursor = cursor
        self.lastrowid = lastrowid
        self.rowcount = int(cursor.rowcount if rowcount is None else rowcount)

    @property
    def _columns(self) -> tuple[str, ...]:
        """Purpose: Run the columns workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        if not self._cursor.description:
            return ()
        return tuple(str(column[0]) for column in self._cursor.description)

    def fetchone(self) -> AzureSqlRow | None:
        """Purpose: Run the fetchone workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        row = self._cursor.fetchone()
        if row is None:
            return None
        return AzureSqlRow(self._columns, tuple(row))

    def fetchall(self) -> list[AzureSqlRow]:
        """Purpose: Run the fetchall workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Applies access and lookup rules, gathers the relevant records, and returns a caller-ready result.
        """
        columns = self._columns
        return [AzureSqlRow(columns, tuple(row)) for row in self._cursor.fetchall()]

    def __iter__(self) -> Iterator[AzureSqlRow]:
        """Purpose: Implement the iter protocol for Azure SQL cursor.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        columns = self._columns
        for row in self._cursor:
            yield AzureSqlRow(columns, tuple(row))


def _normalize_sql(sql: str) -> str:
    """Purpose: Normalize SQL for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Validates the supplied value, normalizes supported formats, and returns a predictable representation.
    """
    return " ".join(str(sql or "").strip().split())


def _inline_limit_parameters(sql: str, parameters: Sequence[Any]) -> tuple[str, tuple[Any, ...]]:
    """Inline numeric LIMIT parameters before transpiling to TOP.

    SQL Server moves TOP to the beginning of a SELECT. Inlining the bounded
    integer keeps the remaining qmark parameter order unchanged for pyodbc.
    """

    working_sql = str(sql or "")
    working_params = list(parameters)
    while True:
        match = re.search(r"\bLIMIT\s+\?", working_sql, flags=re.IGNORECASE)
        if not match:
            break
        parameter_index = working_sql[: match.start()].count("?")
        if parameter_index >= len(working_params):
            raise ValueError("LIMIT placeholder does not have a matching parameter")
        limit = int(working_params.pop(parameter_index))
        if limit < 0:
            raise ValueError("LIMIT must be non-negative")
        working_sql = working_sql[: match.start()] + f"LIMIT {limit}" + working_sql[match.end() :]
    return working_sql, tuple(working_params)


def _table_and_columns(insert_expression: Any) -> tuple[str, list[str]]:
    """Purpose: Run the table and columns workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    schema = insert_expression.this
    table = schema.this.name
    columns = [column.name for column in schema.expressions]
    return table, columns


def _source_value_sql(expression: Any) -> str:
    """Purpose: Run the source value SQL workflow for the delivery-list scanner.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    return expression.sql(dialect="tsql")


def _update_value_sql(expression: Any, table: str, insert_columns: set[str], exp: Any) -> str:
    """Purpose: Update value SQL for the delivery-list scanner workflow.

    Effects: Performs an in-memory calculation and returns data without intentional external side effects.
    Flow: Validates inputs, performs the requested change, records related state when required, and returns the updated result.
    """
    copied = expression.copy()

    def transform(node: Any) -> Any:
        """Purpose: Run the transform workflow for the delivery-list scanner.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        if not isinstance(node, exp.Column):
            return node
        table_name = node.table
        if table_name == "excluded":
            return exp.column(node.name, table="source")
        if table_name == table:
            return exp.column(node.name, table="target")
        if table_name:
            return node

        parent = node.parent
        while parent is not None:
            if isinstance(parent, exp.Select):
                return node
            parent = parent.parent
        if node.name in insert_columns:
            return exp.column(node.name, table="target")
        return node

    copied = copied.transform(transform)
    return copied.sql(dialect="tsql")


def build_merge_statement(sql: str) -> str:
    """Translate one-row SQLite INSERT OR IGNORE / ON CONFLICT into MERGE."""

    _, sqlglot, exp = _load_sql_dependencies()
    expression = sqlglot.parse_one(sql, read="sqlite")
    if not isinstance(expression, exp.Insert):
        raise ValueError("MERGE translation requires an INSERT statement")

    table, columns = _table_and_columns(expression)
    values_expression = expression.expression
    if not isinstance(values_expression, exp.Values) or len(values_expression.expressions) != 1:
        raise ValueError("Azure SQL upsert translation only supports one VALUES row")
    value_tuple = values_expression.expressions[0]
    values = list(value_tuple.expressions)
    if len(values) != len(columns):
        raise ValueError("INSERT column/value count mismatch")

    conflict = expression.args.get("conflict")
    ignore = str(expression.args.get("alternative") or "").upper() == "IGNORE"
    if conflict is not None:
        conflict_columns = [column.name for column in conflict.args.get("conflict_keys") or []]
    else:
        conflict_columns = list(UNIQUE_KEY_COLUMNS.get(table, ()))
    if not conflict_columns:
        raise ValueError(f"No Azure SQL unique-key mapping is configured for INSERT OR IGNORE on {table}")

    source_columns = ",\n        ".join(
        f"{_source_value_sql(value)} AS [{column}]" for column, value in zip(columns, values)
    )
    match_clause = " AND ".join(
        f"target.[{column}] = source.[{column}]" for column in conflict_columns
    )

    update_clause = ""
    if conflict is not None and "NOTHING" not in str(conflict.args.get("action") or "").upper():
        assignments = []
        insert_column_set = set(columns)
        for assignment in conflict.expressions:
            if not isinstance(assignment, exp.EQ):
                continue
            target_column = assignment.this.name
            value_sql = _update_value_sql(assignment.expression, table, insert_column_set, exp)
            assignments.append(f"target.[{target_column}] = {value_sql}")
        if assignments:
            update_clause = "\nWHEN MATCHED THEN\n    UPDATE SET " + ",\n        ".join(assignments)

    insert_columns = ", ".join(f"[{column}]" for column in columns)
    insert_values = ", ".join(f"source.[{column}]" for column in columns)
    return (
        f"MERGE INTO [{table}] WITH (HOLDLOCK) AS target\n"
        f"USING (\n    SELECT {source_columns}\n) AS source\n"
        f"ON {match_clause}"
        f"{update_clause}\n"
        f"WHEN NOT MATCHED THEN\n"
        f"    INSERT ({insert_columns}) VALUES ({insert_values});"
    )


def transpile_sqlite_sql(sql: str) -> str:
    """Translate ordinary SQLite statements into Azure SQL T-SQL."""

    _, sqlglot, _ = _load_sql_dependencies()
    normalized = _normalize_sql(sql)
    if not normalized:
        return ""
    return sqlglot.transpile(sql, read="sqlite", write="tsql")[0]


class AzureSqlConnection:
    """Context-managed pyodbc connection exposing the sqlite3 methods in use."""

    def __init__(self, raw_connection: Any):
        """Purpose: Initialize a Azure SQL connection instance and its required state.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        self._raw = raw_connection
        self._last_identity: int | None = None

    def __enter__(self) -> "AzureSqlConnection":
        """Purpose: Enter the Azure SQL connection context and return the active resource.

        Effects: Performs an in-memory calculation and returns data without intentional external side effects.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        """Purpose: Finish the Azure SQL connection context and release its resources.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        try:
            if exc_type is None:
                self._raw.commit()
            else:
                self._raw.rollback()
        finally:
            self._raw.close()
        return False

    def close(self) -> None:
        """Purpose: Run the close workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        self._raw.close()

    def commit(self) -> None:
        """Purpose: Run the commit workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        self._raw.commit()

    def rollback(self) -> None:
        """Purpose: Run the rollback workflow for the delivery-list scanner.

        Effects: This function reads or updates shared application state.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        self._raw.rollback()

    def execute_tsql(self, sql: str, parameters: Sequence[Any] | None = None):
        """Execute trusted T-SQL without SQLite-dialect translation."""

        cursor = self._raw.cursor()
        cursor.execute(str(sql or ""), tuple(parameters or ()))
        return AzureSqlCursor(cursor, lastrowid=self._last_identity)

    def execute(self, sql: str, parameters: Sequence[Any] | None = None):
        """Purpose: Run the execute workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        params = tuple(parameters or ())
        sql, params = _inline_limit_parameters(sql, params)
        normalized = _normalize_sql(sql)
        upper = normalized.upper()

        if upper == "BEGIN IMMEDIATE":
            # pyodbc uses an explicit transaction because autocommit is disabled.
            # Connections are configured as SERIALIZABLE to retain SQLite's
            # write-serialization intent for scan/update workflows.
            return AzureSqlMemoryCursor()
        if upper.startswith("PRAGMA "):
            return AzureSqlMemoryCursor()
        if upper.startswith("SELECT LAST_INSERT_ROWID()"):
            return AzureSqlMemoryCursor(
                columns=("last_insert_rowid()",),
                rows=((self._last_identity,),),
                rowcount=1,
                lastrowid=self._last_identity,
            )

        cursor = self._raw.cursor()
        is_upsert = " ON CONFLICT" in upper or upper.startswith("INSERT OR IGNORE")
        if is_upsert:
            translated = build_merge_statement(sql)
            cursor.execute(translated, params)
            return AzureSqlCursor(cursor, lastrowid=self._last_identity)

        translated = transpile_sqlite_sql(sql)
        if upper.startswith("INSERT "):
            batch = (
                "SET NOCOUNT ON;\n"
                f"{translated.rstrip().rstrip(';')};\n"
                "SELECT CAST(SCOPE_IDENTITY() AS bigint) AS dls_lastrowid;"
            )
            cursor.execute(batch, params)
            identity: int | None = None
            while True:
                if cursor.description:
                    row = cursor.fetchone()
                    if row is not None and str(cursor.description[0][0]).lower() == "dls_lastrowid":
                        identity = int(row[0]) if row[0] is not None else None
                if not cursor.nextset():
                    break
            self._last_identity = identity
            return AzureSqlMemoryCursor(lastrowid=identity, rowcount=1)

        cursor.execute(translated, params)
        return AzureSqlCursor(cursor, lastrowid=self._last_identity)

    def executemany(self, sql: str, parameter_rows: Iterable[Sequence[Any]]):
        """Purpose: Run the executemany workflow for the delivery-list scanner.

        Effects: This function reads or changes database records.
        Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
        """
        translated = transpile_sqlite_sql(sql)
        cursor = self._raw.cursor()
        cursor.fast_executemany = True
        cursor.executemany(translated, list(parameter_rows))
        return AzureSqlCursor(cursor, lastrowid=self._last_identity)


def connect_azure_sql(connection_string: str, *, timeout_seconds: int = 30) -> AzureSqlConnection:
    """Purpose: Run the connect Azure SQL workflow for the delivery-list scanner.

    Effects: This function reads or changes database records.
    Flow: Normalizes inputs, executes the named responsibility, and returns the result expected by its callers.
    """
    pyodbc, _, _ = _load_sql_dependencies()
    clean = str(connection_string or "").strip()
    if not clean:
        raise ValueError("DLS_DATABASE_CONNECTION_STRING is required when DLS_DATABASE_TYPE=azure-sql")
    raw = pyodbc.connect(clean, autocommit=False, timeout=max(int(timeout_seconds), 1))
    raw.execute("SET XACT_ABORT ON")
    raw.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
    return AzureSqlConnection(raw)
