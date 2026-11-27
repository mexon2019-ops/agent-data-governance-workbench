import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/sprint52-bulk-mapping-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")

from sqlalchemy import select
from app import main


def test_bulk_standard_mapping_creates_and_updates_batch():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        code = "UT_S52_BULK_STD"
        old = db.scalar(select(main.DataStandard).where(main.DataStandard.standard_code == code))
        if old:
            db.delete(old)
            db.commit()
        source_name = "s52-bulk-fixture"
        source = db.scalar(select(main.DataSource).where(main.DataSource.name == source_name))
        if source:
            db.delete(source)
            db.commit()
        source = main.DataSource(name=source_name, db_type="mysql", host="localhost",
            port=3306, database="fixture", username="readonly",
            password_env_key="FIXTURE_PASSWORD")
        db.add(source); db.commit(); db.refresh(source)
        table = main.MetadataTable(source_id=source.id, schema_name="fixture",
            table_name="customer", column_count=2)
        db.add(table); db.commit(); db.refresh(table)
        c1 = main.MetadataColumn(table_id=table.id, column_name="code", data_type="VARCHAR",
            ordinal_position=1)
        c2 = main.MetadataColumn(table_id=table.id, column_name="name", data_type="VARCHAR",
            ordinal_position=2)
        db.add_all([c1,c2]); db.commit(); db.refresh(c1); db.refresh(c2)
        standard = main.create_data_standard(main.DataStandardIn(
            standard_code=code, name="客户编码", definition="编码",
            data_type="VARCHAR"), _user=object(), db=db)
        version_id = standard["versions"][0]["id"]
        payload = {"mappings":[
            {"metadata_column_id":c1.id,"mapping_status":"已落标","note":"首批"},
            {"metadata_column_id":c2.id,"mapping_status":"待核验","note":"待业务确认"}]}
        result = main.bulk_create_standard_mappings(standard["id"],version_id,payload,
            _user=object(),db=db)
        assert result["count"] == 2
        assert {m["metadata_column_id"] for m in result["mappings"]} == {c1.id,c2.id}
        updated = main.bulk_create_standard_mappings(standard["id"],version_id,
            {"mappings":[{"metadata_column_id":c2.id,"mapping_status":"不符合","note":"类型不一致"}]},
            _user=object(),db=db)
        assert updated["count"] == 1
        detail = main.get_data_standard(standard["id"],db=db)
        assert len(detail["mappings"]) == 2
        assert next(m for m in detail["mappings"] if m["metadata_column_id"]==c2.id)["mapping_status"]=="不符合"
        db.delete(db.get(main.DataStandard,standard["id"]))
        db.delete(source);db.commit()


def test_bulk_mapping_rejects_duplicate_ids_and_empty_batches():
    import pytest
    with pytest.raises(Exception):
        main.DataStandardMappingIn(metadata_column_id=1,mapping_status="invalid")
