# SQLite to SQL Server Mapping

`database_contract.py` owns the logical table inventory and mapping policy. SQLite migration DDL and `azure_sql_schema.sql` are validated against that contract.

| Logical value | SQLite | Azure SQL |
|---|---|---|
| Text business identifier | `TEXT` | `nvarchar(255)` |
| Short label/state | `TEXT` | `nvarchar(255)` or `nvarchar(500)` |
| Long text or optional JSON | `TEXT` | `nvarchar(max)` |
| Identity primary key | `INTEGER PRIMARY KEY AUTOINCREMENT` | `bigint IDENTITY(1,1)` |
| Ordinary quantity | `INTEGER` | `int` |
| Boolean | constrained `INTEGER` (`0/1`) | `bit` |
| Dimension/measurement | `REAL` | `decimal(18,4)` for new schema work |
| UTC timestamp | ISO-8601 `TEXT` | `datetime2(0)` |
| Optional JSON metadata | valid JSON `TEXT` | `nvarchar(max)` with `ISJSON` constraint |

## Identifier policy

The following values remain text on both databases even when a current value contains only digits:

- order number
- item number
- barcode
- source/line-item ID
- rack code
- bay code
- machine code
- scanner code

This preserves leading zeroes and prevents numeric overflow or formatting changes.

## Migration validation

`migrate_sqlite_to_azure_sql.py` normalizes values before checksum comparison:

- timezone-aware SQLite text and Azure `datetime2` compare as the same UTC second;
- SQLite `0/1` and ODBC `bit` values compare logically;
- integer, float, and decimal driver values use a canonical decimal representation;
- row order does not affect a table checksum.

The migration is committed only after every copied table passes row-count and checksum validation. A failure rolls back the target data transaction and writes a JSON report.

An explicitly requested `--replace` migration temporarily disables only the v097 append-only history triggers inside the replacement transaction. They are re-enabled before commit; routine application connections cannot update or delete history.
