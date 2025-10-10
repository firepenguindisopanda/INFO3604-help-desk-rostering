#!/usr/bin/env python3
"""Clone data from the production Neon database into the local Postgres instance.

The script connects to both databases, truncates every table in the target, and
then replays the contents from source to target in dependency order. Use it when
you need a local snapshot of production data for debugging or experimentation.

Usage example:

    python scripts/sync_neon_to_local.py \
        --source-url postgresql://<neon-user>:<password>@<neon-host>/<db>?sslmode=require \
        --target-url postgresql://<local-user>:<password>@localhost:5433/info3604_helpdesk

You can also set the `SYNC_SOURCE_URL` and `SYNC_TARGET_URL` environment
variables instead of providing flags at runtime. Credentials should be supplied
through environment variables or other secure secrets management tooling; do
not hard-code them into the repository.
"""
from __future__ import annotations

import argparse
import os
from typing import Iterable, List, Optional, Sequence, Tuple

try:  # pragma: no cover - optional dependency guard
    from sqlalchemy import MetaData, Table, create_engine, select, text  # type: ignore[import]
    from sqlalchemy.engine import Connection, Engine  # type: ignore[import]
    from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError  # type: ignore[import]
except ImportError as exc:  # pragma: no cover - provide helpful error for users
    raise SystemExit(
        "SQLAlchemy is required to run this script. Install it with 'pip install SQLAlchemy'."
    ) from exc

BATCH_SIZE = 1000
DEFAULT_SCHEMA = "public"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy data from Neon to local Postgres.")
    parser.add_argument(
        "--source-url",
        default=None,
        help="SQLAlchemy URL for the source (Neon) database. Falls back to SYNC_SOURCE_URL if unset.",
    )
    parser.add_argument(
        "--target-url",
        default=None,
        help="SQLAlchemy URL for the target (local) database. Falls back to SYNC_TARGET_URL if unset.",
    )
    parser.add_argument(
        "--schema",
        default=DEFAULT_SCHEMA,
        help="Schema to replicate (defaults to 'public'). Use '*' to copy every schema.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help="Number of rows to batch per insert when copying tables",
    )
    args = parser.parse_args()

    if not args.source_url:
        args.source_url = os.getenv("SYNC_SOURCE_URL", "postgresql://neondb_owner:npg_M9NLwQJqs8tZ@ep-shiny-smoke-adsd00ve-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")
    if not args.target_url:
        args.target_url = os.getenv("SYNC_TARGET_URL", "postgresql://dev:devpass@localhost:5433/info3604_helpdesk")

    if not args.source_url:
        parser.error("A source URL must be supplied via --source-url or SYNC_SOURCE_URL")
    if not args.target_url:
        parser.error("A target URL must be supplied via --target-url or SYNC_TARGET_URL")

    return args


def qualified_name(table: Table) -> str:
    if table.schema:
        return f'"{table.schema}"."{table.name}"'
    return f'"{table.name}"'


def truncate_target(conn: Connection, tables: Sequence[Table]) -> None:
    if not tables:
        print("No tables to truncate in target database.")
        return
    table_list = ", ".join(qualified_name(table) for table in tables)
    print(f"Truncating target tables: {table_list}")
    conn.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))


def copy_table(
    source_conn: Connection,
    target_conn: Connection,
    source_table: Table,
    target_table: Table,
    batch_size: int,
) -> None:
    print(f"Copying {qualified_name(source_table)}")
    result = source_conn.execution_options(stream_results=True).execute(select(source_table))
    rows_copied = 0

    while True:
        batch = result.fetchmany(batch_size)
        if not batch:
            break
        payload = [dict(row._mapping) for row in batch]
        target_conn.execute(target_table.insert(), payload)
        rows_copied += len(payload)

    print(f"  -> {rows_copied} rows copied")


def table_matches_schema(table: Table, schema: str | None) -> bool:
    if schema in (None, "*"):
        return True
    table_schema = table.schema or DEFAULT_SCHEMA
    return table_schema == schema


def collect_table_pairs(
    source_md: MetaData,
    target_engine: Engine,
    schema: str | None,
) -> List[Tuple[Table, Table]]:
    pairs: List[Tuple[Table, Table]] = []

    for source_table in source_md.sorted_tables:
        if not table_matches_schema(source_table, schema):
            continue
        try:
            target_table = Table(
                source_table.name,
                MetaData(),
                schema=source_table.schema,
                autoload_with=target_engine,
            )
        except NoSuchTableError:
            print(f"Skipping {qualified_name(source_table)} (missing in target database)")
            continue
        pairs.append((source_table, target_table))

    return pairs


def reset_sequences(conn: Connection, schema: Optional[str]) -> None:
    """Align all serial/identity sequences with the current max primary key."""

    # Use pg_get_serial_sequence to reliably get sequence names
    sequence_rows = conn.execute(
        text(
            """
            SELECT table_schema,
                   table_name,
                   column_name,
                   pg_get_serial_sequence(table_schema||'.'||table_name, column_name) AS sequence_name
            FROM information_schema.columns
            WHERE column_default LIKE 'nextval(%'
              AND (:schema IS NULL OR table_schema = :schema)
              AND pg_get_serial_sequence(table_schema||'.'||table_name, column_name) IS NOT NULL
            """
        ),
        {"schema": None if schema in (None, "*") else schema},
    )

    rows_updated = 0
    for row in sequence_rows:
        table_identifier = f'"{row.table_schema}"."{row.table_name}"'
        column_identifier = f'"{row.column_name}"'
        sequence_name = row.sequence_name
        
        # Skip if sequence_name is empty or invalid
        if not sequence_name or sequence_name.strip() == '':
            print(f"Skipping invalid sequence for {table_identifier}.{column_identifier}")
            continue

        max_value = conn.execute(
            text(f"SELECT MAX({column_identifier}) FROM {table_identifier}")
        ).scalar()

        if max_value is None:
            # Table is empty; reset sequence start without marking as called.
            conn.execute(
                text("SELECT setval(:seq_name, 1, false)"),
                {"seq_name": sequence_name},
            )
        else:
            conn.execute(
                text("SELECT setval(:seq_name, :value, true)"),
                {"seq_name": sequence_name, "value": int(max_value)},
            )
        rows_updated += 1

    if rows_updated:
        print(f"Reset {rows_updated} sequences to match imported data.")
    else:
        print("No sequences required resetting (none found in selected schema).")


def sync_databases(
    source_url: str,
    target_url: str,
    schema: str | None,
    batch_size: int,
) -> None:
    print(f"Connecting to source: {source_url}")
    print(f"Connecting to target: {target_url}")

    source_engine = create_engine(source_url)
    target_engine = create_engine(target_url)

    source_metadata = MetaData()
    reflect_kwargs = {}
    if schema not in (None, "*"):
        reflect_kwargs["schema"] = schema
    source_metadata.reflect(bind=source_engine, **reflect_kwargs)

    table_pairs = collect_table_pairs(source_metadata, target_engine, schema if schema != "*" else None)

    if not table_pairs:
        print("No overlapping tables found. Nothing to replicate.")
        return

    target_tables = [target for _, target in table_pairs]

    with source_engine.connect() as raw_source_conn:
        source_conn = raw_source_conn.execution_options(stream_results=True)
        with target_engine.begin() as target_conn:
            truncate_target(target_conn, target_tables)
            for source_table, target_table in table_pairs:
                copy_table(source_conn, target_conn, source_table, target_table, batch_size)
            reset_sequences(target_conn, schema)

    print("Replication complete.")


def main() -> None:
    args = parse_args()
    try:
        sync_databases(
            source_url=args.source_url,
            target_url=args.target_url,
            schema=args.schema,
            batch_size=args.batch_size,
        )
    except SQLAlchemyError as exc:
        print(f"Error syncing databases: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
