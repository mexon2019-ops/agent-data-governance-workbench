import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/connector-config-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")

from app import main


def test_all_four_database_connectors_build_expected_urls(monkeypatch):
    captured = []

    def fake_create_engine(url, **kwargs):
        captured.append((url, kwargs))
        return object()

    monkeypatch.setattr(main, "create_engine", fake_create_engine)
    cases = [
        ("sqlserver", 1433, "MES", "mssql+pymssql"),
        ("oracle", 1521, "ORCLPDB1", "oracle+oracledb"),
        ("mysql", 3306, "mes_test", "mysql+pymysql"),
        ("postgresql", 5432, "governance", "postgresql+psycopg"),
    ]
    for db_type, port, database, driver in cases:
        monkeypatch.setenv("CONNECTOR_TEST_PASSWORD", "connector-test-secret")
        source = main.DataSource(
            name="connector-" + db_type,
            db_type=db_type,
            host="db.internal",
            port=port,
            database=database,
            username="metadata_reader",
            password_env_key="CONNECTOR_TEST_PASSWORD",
        )
        engine = main.build_source_engine(source)
        assert engine is not None

    assert len(captured) == 4
    for (db_type, port, database, driver), (url, kwargs) in zip(cases, captured):
        assert url.drivername == driver
        assert url.host == "db.internal"
        assert url.port == port
        assert url.database == database
        assert url.username == "metadata_reader"
        assert url.password == "connector-test-secret"
        assert "connector-test-secret" not in str(url)
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["connect_args"]


def test_connector_requires_server_side_password_environment_variable(monkeypatch):
    monkeypatch.delenv("CONNECTOR_MISSING_PASSWORD", raising=False)
    source = main.DataSource(
        name="missing-secret",
        db_type="mysql",
        host="db.internal",
        port=3306,
        database="mes_test",
        username="metadata_reader",
        password_env_key="CONNECTOR_MISSING_PASSWORD",
    )
    import pytest
    with pytest.raises(ValueError, match="不会存入数据库"):
        main.build_source_engine(source)
