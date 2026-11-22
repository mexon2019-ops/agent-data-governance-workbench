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
                db_type="sqlite",
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


def test_mysql_sync_is_scoped_to_configured_database(monkeypatch):
    main.Base.metadata.create_all(main.engine)

    class FakeInspector:
        seen_schemas = []

        def get_table_names(self, schema=None):
            self.seen_schemas.append(schema)
            return ["only_this_database"]

        def get_view_names(self, schema=None):
            return []

        def get_columns(self, table_name, schema=None):
            return [{"name": "id", "type": "INTEGER", "nullable": False, "default": None, "ordinal": 1}]

        def get_pk_constraint(self, table_name, schema=None):
            return {"constrained_columns": ["id"]}

        def get_foreign_keys(self, table_name, schema=None):
            return []

        def get_table_comment(self, table_name, schema=None):
            return {"text": "fixture table"}

    inspector = FakeInspector()

    class FakeEngine:
        def dispose(self):
            pass

    with main.SessionLocal() as db:
        source = main.DataSource(
            name="mysql-scope-test",
            db_type="mysql",
            host="mysql.internal",
            port=3306,
            database="mes_quality",
            username="metadata_reader",
            password_env_key="MYSQL_DB_PASSWORD",
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        monkeypatch.setattr(main, "build_source_engine", lambda _row: FakeEngine())
        monkeypatch.setattr(main, "sa_inspect", lambda _engine: inspector)

        result = main.sync_metadata(source.id, db)

        assert result["success"] is True
        assert result["table_count"] == 1
        assert inspector.seen_schemas == ["mes_quality"]
        saved = db.scalar(select(main.MetadataTable).where(main.MetadataTable.source_id == source.id))
        assert saved.schema_name == "mes_quality"


def test_mysql_test_datasource_auto_registration_is_opt_in_and_idempotent(monkeypatch):
    main.Base.metadata.create_all(main.engine)
    name = "MySQL 测试数据库（mes_test）"
    monkeypatch.setenv("AUTO_REGISTER_MYSQL_TEST_DATASOURCE", "true")
    monkeypatch.setenv("MYSQL_TEST_HOST", "mysql-test")
    with main.SessionLocal() as db:
        old = db.scalar(select(main.DataSource).where(main.DataSource.name == name))
        if old:
            db.delete(old)
            db.commit()

        first = main.ensure_mysql_test_datasource(db)
        second = main.ensure_mysql_test_datasource(db)

        assert first is not None
        assert first.id == second.id
        assert first.db_type == "mysql"
        assert first.host == "mysql-test"
        assert first.port == 3306
        assert first.database == "mes_test"
        assert first.username == "metadata_reader"
        assert first.password_env_key == "MYSQL_TEST_READER_PASSWORD"
        assert db.scalar(select(main.DataSource).where(main.DataSource.name == name)) is not None


def test_mysql_test_datasource_auto_registration_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AUTO_REGISTER_MYSQL_TEST_DATASOURCE", raising=False)
    with main.SessionLocal() as db:
        assert main.ensure_mysql_test_datasource(db) is None
