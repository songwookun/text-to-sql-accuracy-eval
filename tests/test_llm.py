import pytest

from text2sql.llm import extract_sql


@pytest.mark.parametrize("text, expected", [
    ("SELECT 1", "SELECT 1"),
    ("```sql\nSELECT 1\n```", "SELECT 1"),
    ("```SQL\nSELECT 1;\n```", "SELECT 1;"),
    ("```\nSELECT 1\n```", "SELECT 1"),
    ("Here you go:\n```sql\nSELECT a\nFROM t\n```\nDone.", "SELECT a\nFROM t"),
    ("", ""),
])
def test_extract_sql(text, expected):
    assert extract_sql(text) == expected
