from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import main
from app.classification_service import suggest_field_classification


def test_sensitive_field_name_suggestions():
    assert suggest_field_classification("employee_id_card")["suggested_level"] == "高度敏感"
    assert suggest_field_classification("customer_mobile")["suggested_level"] == "敏感"
    assert suggest_field_classification("production_order_code")["suggested_level"] == "内部"
    assert suggest_field_classification("unknown_flag")["suggested_level"] == "未分级"


def test_metadata_column_classification_is_saved_and_returned():
    engine = create_engine("sqlite://")
    main.Base.metadata.create_all(engine)
    with Session(engine) as db:
        source = main.DataSource(
            name="classification-fixture", db_type="mysql", host="localhost",
            port=3306, database="fixture", username="readonly",
            password_env_key="FIXTURE_PASSWORD",
        )
        db.add(source)
        db.flush()
        table = main.MetadataTable(
            source_id=source.id, schema_name="fixture", table_name="customer",
            table_type="TABLE", column_count=1,
        )
        db.add(table)
        db.flush()
        column = main.MetadataColumn(
            table_id=table.id, column_name="customer_mobile",
            data_type="VARCHAR(20)", nullable=True, ordinal_position=1,
        )
        db.add(column)
        db.commit()
        db.refresh(column)

        suggestion = main.get_metadata_column_classification_suggestion(column.id, db=db)
        assert suggestion["suggested_level"] == "敏感"

        result = main.classify_metadata_column(
            column.id,
            main.MetadataColumnClassificationIn(
                sensitivity_level="高度敏感",
                classification_basis="业务负责人确认属于高敏个人信息",
            ),
            _user=SimpleNamespace(username="data.steward"),
            db=db,
        )
        assert result["sensitivity_level"] == "高度敏感"
        assert result["classified_by"] == "data.steward"
        assert result["classified_at"] is not None

        detail = main.get_metadata_table(table.id, db=db)
        assert detail["columns"][0]["sensitivity_level"] == "高度敏感"
        assert detail["columns"][0]["classification_basis"] == "业务负责人确认属于高敏个人信息"
