import os

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/metadata-unit-test.db")

from sqlalchemy import create_engine, select
from app import main


def test_metadata_sync_is_repeatable_and_removes_stale_tables(monkeypatch):
    main.Base.metadata.drop_all(main.engine)
    main.Base.metadata.create_all(main.engine)

    source_engine = create_engine("sqlite:////tmp/source-metadata-fixture.db")
    with source_engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS orders")
        conn.exec_driver_sql("DROP TABLE IF EXISTS customers")
        conn.exec_driver_sql(
            "CREATE TABLE customers (id INTEGER PRIMARY KEY, code VARCHAR(30) NOT NULL, name VARCHAR(100))"
        )
        conn.exec_driver_sql(
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id), amount NUMERIC DEFAULT 0)"
        )

    try:
        with main.SessionLocal() as db:
            source = main.DataSource(
                name="fixture-mysql",
                db_type="mysql",
                host="localhost",
                port=3306,
                database="fixture",
                username="readonly",
                password_env_key="FIXTURE_PASSWORD",
            )
            db.add(source)
            db.commit()
            db.refresh(source)
            monkeypatch.setattr(main, "build_source_engine", lambda _row: source_engine)

            first = main.sync_metadata(source.id, db)
            assert first["success"] is True
            assert first["table_count"] == 2
            assert first["column_count"] == 6

            tables = db.scalars(
                select(main.MetadataTable).where(main.MetadataTable.source_id == source.id)
            ).all()
            assert {table.table_name for table in tables} == {"customers", "orders"}
            customer_table = next(table for table in tables if table.table_name == "customers")
            detail = main.get_metadata_table(customer_table.id, db)
            assert len(detail["columns"]) == 3
            assert next(c for c in detail["columns"] if c["column_name"] == "id")["is_primary_key"]

            second = main.sync_metadata(source.id, db)
            assert second["success"] is True
            assert second["table_count"] == 2
            assert len(db.scalars(
                select(main.MetadataTable).where(main.MetadataTable.source_id == source.id)
            ).all()) == 2

            with source_engine.begin() as conn:
                conn.exec_driver_sql("DROP TABLE orders")
            third = main.sync_metadata(source.id, db)
            assert third["success"] is True
            assert third["table_count"] == 1
            remaining = db.scalars(
                select(main.MetadataTable).where(main.MetadataTable.source_id == source.id)
            ).all()
            assert [table.table_name for table in remaining] == ["customers"]
            runs = db.scalars(
                select(main.MetadataSyncRun).where(main.MetadataSyncRun.source_id == source.id)
            ).all()
            assert len(runs) == 3
            assert all(run.status == "成功" and run.finished_at is not None for run in runs)
    finally:
        source_engine.dispose()
