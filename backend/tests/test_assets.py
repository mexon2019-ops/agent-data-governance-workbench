import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/asset-catalog-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")

from sqlalchemy import select
from app import main


def test_data_asset_catalog_create_filter_and_update():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        code = "UT_ASSET_CUSTOMER_MASTER"
        existing = db.scalar(select(main.DataAsset).where(main.DataAsset.asset_code == code))
        if existing:
            db.delete(existing)
            db.commit()

        old_source = db.scalar(select(main.DataSource).where(main.DataSource.name == "asset-catalog-fixture"))
        if old_source:
            old_tables = db.scalars(select(main.MetadataTable).where(main.MetadataTable.source_id == old_source.id)).all()
            for old_table in old_tables:
                db.delete(old_table)
            db.delete(old_source)
            db.commit()
        source = main.DataSource(
            name="asset-catalog-fixture",
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
        table = main.MetadataTable(
            source_id=source.id,
            schema_name="mes_test",
            table_name="dim_customer",
            table_type="TABLE",
            column_count=3,
        )
        db.add(table)
        db.commit()
        db.refresh(table)

        payload = main.DataAssetIn(
            asset_code=code,
            name="客户主数据",
            metadata_table_id=table.id,
            business_domain="销售",
            description="客户统一主数据",
            owner_department="营销中心",
            owner="张三",
            sensitivity_level="敏感",
            lifecycle_status="建设中",
            tags=["主数据", "客户", "主数据"],
        )
        created = main.create_data_asset(payload, _user=object(), db=db)
        assert created["asset_code"] == code
        assert created["tags"] == ["主数据", "客户"]
        assert created["table_name"] == "dim_customer"
        assert created["metadata_table_id"] == table.id

        filtered = main.list_data_assets(keyword="dim_customer", business_domain="销售", db=db)
        assert len(filtered) == 1
        assert filtered[0]["id"] == created["id"]

        updated = main.update_data_asset(
            created["id"],
            {"owner_department": "数据管理部", "lifecycle_status": "已发布", "tags": ["客户", "主数据"]},
            _user=object(),
            db=db,
        )
        assert updated["owner_department"] == "数据管理部"
        assert updated["lifecycle_status"] == "已发布"
        assert updated["tags"] == ["客户", "主数据"]

        main.delete_data_asset(created["id"], _user=object(), db=db)
        assert db.scalar(select(main.DataAsset).where(main.DataAsset.id == created["id"])) is None
        db.delete(source)
        db.commit()


def test_data_asset_input_rejects_invalid_asset_code_and_classification():
    import pytest

    with pytest.raises(Exception):
        main.DataAssetIn(asset_code="中文编码", name="无效编码")
    with pytest.raises(Exception):
        main.DataAssetIn(asset_code="ASSET_1", name="测试", sensitivity_level="机密")
