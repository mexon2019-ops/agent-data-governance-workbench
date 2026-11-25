from app.finereport_service import extract_sql_table_references

def test_extract_from_join_and_quoted_identifiers():
    result = extract_sql_table_references("SELECT x.id FROM [dbo].[orders] x JOIN `items` i ON x.id=i.id")
    assert result["tables"] == ["dbo.orders", "items"]
    assert result["review_required"] is False

def test_string_literals_do_not_create_false_tables():
    result = extract_sql_table_references("SELECT 'FROM fake_table' AS note FROM real_table")
    assert result["tables"] == ["real_table"]

def test_empty_sql_flags_review():
    assert extract_sql_table_references("")["review_required"] is True

def test_cte_requires_review():
    result = extract_sql_table_references("WITH c AS (SELECT * FROM source_table) SELECT * FROM c")
    assert result["review_required"] is True
