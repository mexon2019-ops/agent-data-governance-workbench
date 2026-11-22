import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/data-standard-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")

from sqlalchemy import select
from app import main


def test_standard_version_publish_and_field_mapping_lifecycle():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        code = "UT_STD_CUSTOMER_CODE"
        old_standard = db.scalar(select(main.DataStandard).where(main.DataStandard.standard_code == code))
        if old_standard:
            db.delete(old_standard)
            db.commit()

        source_name = "standard-mapping-fixture"
        old_source = db.scalar(select(main.DataSource).where(main.DataSource.name == source_name))
        if old_source:
            old_tables = db.scalars(select(main.MetadataTable).where(main.MetadataTable.source_id == old_source.id)).all()
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
            source_id=source.id, schema_name="mes_test", table_name="dim_customer",
            table_type="TABLE", column_count=1,
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        column = main.MetadataColumn(
            table_id=table.id, column_name="customer_code", data_type="VARCHAR(30)",
            nullable=False, ordinal_position=1,
        )
        db.add(column)
        db.commit()
        db.refresh(column)

        payload = main.DataStandardIn(
            standard_code=code, name="客户编码", business_domain="销售",
            description="企业客户唯一标识", owner_department="营销中心", owner="数据管理员",
            definition="客户主数据唯一编码", data_type="VARCHAR", max_length=30,
            required=True, format_rule="大写字母或数字", example="CUST0001",
        )
        created = main.create_data_standard(payload, _user=object(), db=db)
        assert created["standard_code"] == code
        assert created["current_version"] == 1
        assert created["versions"][0]["required"] is True

        version2 = main.create_standard_version(
            created["id"],
            main.DataStandardVersionIn(
                definition="客户主数据唯一编码，不允许重复", data_type="VARCHAR",
                max_length=40, required=True, format_rule="CUST+数字", example="CUST000001",
            ),
            _user=object(), db=db,
        )
        assert version2["version_number"] == 2
        published = main.publish_standard_version(
            created["id"], version2["id"], _user=object(), db=db
        )
        assert published["status"] == "已发布"
        assert next(v for v in published["versions"] if v["id"] == version2["id"])["status"] == "已发布"

        mapping = main.create_standard_mapping(
            created["id"], version2["id"],
            main.DataStandardMappingIn(metadata_column_id=column.id, mapping_status="已落标"),
            _user=object(), db=db,
        )
        assert mapping["mapping_status"] == "已落标"
        detail = main.get_data_standard(created["id"], db=db)
        assert len(detail["mappings"]) == 1
        assert detail["mappings"][0]["metadata_column_id"] == column.id
        metadata_detail = main.get_metadata_table(table.id, db=db)
        assert metadata_detail["columns"][0]["standard_mappings"][0]["standard_code"] == code

        db.delete(db.get(main.DataStandard, created["id"]))
        db.delete(source)
        db.commit()


def test_standard_code_and_field_constraints_are_validated():
    import pytest

    with pytest.raises(Exception):
        main.DataStandardIn(standard_code="标准 编码", name="无效")
    with pytest.raises(Exception):
        main.DataStandardVersionIn(max_length=0)
    with pytest.raises(Exception):
        main.DataStandardMappingIn(metadata_column_id=1, mapping_status="自动修复")
