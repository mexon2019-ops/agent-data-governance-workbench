import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/governance-issue-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")

from sqlalchemy import create_engine, select
from app import main


def test_issue_remediation_recheck_and_close_workflow(monkeypatch):
    main.Base.metadata.create_all(main.engine)
    source_engine = create_engine("sqlite:////tmp/governance-issue-source.db")
    with source_engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS issue_fixture")
        conn.exec_driver_sql("CREATE TABLE issue_fixture (code VARCHAR(20))")
        conn.exec_driver_sql("INSERT INTO issue_fixture (code) VALUES ('A'), ('A'), ('B')")

    try:
        with main.SessionLocal() as db:
            source_name = "governance-issue-fixture"
            old_source = db.scalar(select(main.DataSource).where(main.DataSource.name == source_name))
            if old_source:
                old_tables = db.scalars(select(main.MetadataTable).where(
                    main.MetadataTable.source_id == old_source.id
                )).all()
                old_table_ids = [item.id for item in old_tables]
                old_rules = db.scalars(select(main.QualityRule).where(
                    main.QualityRule.metadata_table_id.in_(old_table_ids or [-1])
                )).all()
                for rule in old_rules:
                    old_runs = db.scalars(select(main.QualityRun).where(main.QualityRun.rule_id == rule.id)).all()
                    old_run_ids = [item.id for item in old_runs]
                    for issue in db.scalars(select(main.GovernanceIssue).where(
                        main.GovernanceIssue.rule_id == rule.id
                    )).all():
                        db.delete(issue)
                    for old_run in old_runs:
                        db.delete(old_run)
                    db.delete(rule)
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
                source_id=source.id, schema_name="", table_name="issue_fixture",
                table_type="TABLE", column_count=1,
            )
            db.add(table)
            db.commit()
            db.refresh(table)
            column = main.MetadataColumn(
                table_id=table.id, column_name="code", data_type="VARCHAR(20)",
                nullable=True, ordinal_position=1,
            )
            db.add(column)
            db.commit()
            db.refresh(column)
            monkeypatch.setattr(main, "build_source_engine", lambda _row: source_engine)

            rule = main.create_quality_rule(
                main.QualityRuleIn(
                    rule_code="UT_ISSUE_UNIQUE", name="编码唯一性",
                    metadata_table_id=table.id, metadata_column_id=column.id,
                    rule_type="uniqueness",
                ),
                _user=object(), db=db,
            )
            initial = main.run_quality_rule(rule["id"], db)
            assert initial["failed_count"] == 2

            issue = main.create_governance_issue(
                main.GovernanceIssueCreateIn(
                    quality_run_id=initial["id"], title="客户编码重复",
                    description="检测发现重复编码", severity="高",
                ),
                _user=object(), db=db,
            )
            assert issue["status"] == "待分派"

            assigned = main.assign_governance_issue(
                issue["id"],
                main.GovernanceIssueAssignIn(
                    owner_department="主数据管理部", owner="张三",
                ),
                _user=object(), db=db,
            )
            assert assigned["status"] == "整改中"

            submitted = main.submit_issue_remediation(
                issue["id"],
                main.GovernanceIssueRemediationIn(remediation_note="已清理重复编码并补充校验"),
                _user=object(), db=db,
            )
            assert submitted["status"] == "待复测"

            with source_engine.begin() as conn:
                conn.exec_driver_sql("DELETE FROM issue_fixture")
                conn.exec_driver_sql("INSERT INTO issue_fixture (code) VALUES ('A'), ('B'), ('C')")

            rechecked = main.recheck_governance_issue(issue["id"], _user=object(), db=db)
            assert rechecked["status"] == "待关闭"
            assert rechecked["recheck_result"]["failed_count"] == 0

            closed = main.close_governance_issue(issue["id"], _user=object(), db=db)
            assert closed["status"] == "已关闭"
            assert closed["closed_at"] is not None
            db.delete(source)
            db.commit()
    finally:
        source_engine.dispose()
