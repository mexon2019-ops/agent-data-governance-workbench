import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/quality-rule-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")

from sqlalchemy import create_engine, select
from app import main


def test_read_only_quality_rule_execution_for_core_rule_types(monkeypatch):
    main.Base.metadata.create_all(main.engine)
    source_engine = create_engine("sqlite:////tmp/quality-source-fixture.db")
    with source_engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS quality_fixture")
        conn.exec_driver_sql(
            "CREATE TABLE quality_fixture (email VARCHAR(100), age INTEGER, status VARCHAR(20))"
        )
        conn.exec_driver_sql(
            "INSERT INTO quality_fixture (email, age, status) VALUES "
            "('a@example.com', 25, 'A'), ('a@example.com', 200, 'C'), (NULL, -1, 'A')"
        )

    try:
        with main.SessionLocal() as db:
            source_name = "quality-rule-fixture"
            old_source = db.scalar(select(main.DataSource).where(main.DataSource.name == source_name))
            if old_source:
                old_rules = db.scalars(select(main.QualityRule).where(
                    main.QualityRule.metadata_table_id.in_(
                        select(main.MetadataTable.id).where(main.MetadataTable.source_id == old_source.id)
                    )
                )).all()
                for rule in old_rules:
                    db.delete(rule)
                old_tables = db.scalars(select(main.MetadataTable).where(
                    main.MetadataTable.source_id == old_source.id
                )).all()
                for old_table in old_tables:
                    db.delete(old_table)
                db.delete(old_source)
                db.commit()

            source = main.DataSource(
                name=source_name, db_type="mysql", host="localhost", port=3306,
                database="fixture", username="readonly", password_env_key="FIXTURE_PASSWORD",
            )
            db.add(source)
            db.commit()
            db.refresh(source)
            table = main.MetadataTable(
                source_id=source.id, schema_name="", table_name="quality_fixture",
                table_type="TABLE", column_count=3,
            )
            db.add(table)
            db.commit()
            db.refresh(table)
            columns = {}
            for name, data_type in [("email", "VARCHAR(100)"), ("age", "INTEGER"), ("status", "VARCHAR(20)")]:
                column = main.MetadataColumn(
                    table_id=table.id, column_name=name, data_type=data_type,
                    nullable=True, ordinal_position=len(columns) + 1,
                )
                db.add(column)
                db.flush()
                columns[name] = column
            db.commit()

            monkeypatch.setattr(main, "build_source_engine", lambda _row: source_engine)
            cases = [
                ("UT_QC_COMPLETE", "completeness", "email", {}, 1),
                ("UT_QC_UNIQUE", "uniqueness", "email", {}, 2),
                ("UT_QC_RANGE", "range", "age", {"min": 0, "max": 120}, 2),
                ("UT_QC_ENUM", "enum", "status", {"allowed_values": ["A", "B"]}, 1),
            ]
            results = {}
            for code, rule_type, column_name, config, expected_failed in cases:
                old_rule = db.scalar(select(main.QualityRule).where(main.QualityRule.rule_code == code))
                if old_rule:
                    db.delete(old_rule)
                    db.commit()
                rule = main.create_quality_rule(
                    main.QualityRuleIn(
                        rule_code=code, name=rule_type, metadata_table_id=table.id,
                        metadata_column_id=columns[column_name].id, rule_type=rule_type, config=config,
                    ),
                    _user=object(), db=db,
                )
                result = main.run_quality_rule(rule["id"], db)
                assert result["status"] == "成功"
                assert result["total_count"] == 3
                assert result["failed_count"] == expected_failed
                assert result["passed"] is False
                results[rule_type] = result

            assert results["completeness"]["pass_rate"] == 66.67
            assert results["uniqueness"]["pass_rate"] == 33.33
            assert results["range"]["pass_rate"] == 33.33
            assert results["enum"]["pass_rate"] == 66.67
            db.delete(source)
            db.commit()
    finally:
        source_engine.dispose()


def test_quality_rule_rejects_unsafe_or_invalid_configuration():
    import pytest

    with pytest.raises(Exception):
        main.QualityRuleIn(
            rule_code="BAD", name="bad range", metadata_table_id=1, metadata_column_id=1,
            rule_type="range", config={"min": 20, "max": 10},
        )
