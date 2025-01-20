import pytest
from spreadsheet_to_page_in_db.notion_filter import (
  parse_not_in,
  parse_in,
  parse_inequality,
  parse_not_equal,
  parse_equal,
  parse_or,
  parse_like,
  parse_value
)

# === parse_not_in のテスト ===
def test_parse_not_in():
  expression = "not in [10, 20, \"abc\"]"
  result = parse_not_in(expression, "TestProperty", "number")
  expected = {
    "and": [
      {"property": "TestProperty", "number": {"does_not_equal": 10}},
      {"property": "TestProperty", "number": {"does_not_equal": 20}},
      {"property": "TestProperty", "number": {"does_not_equal": "abc"}},
    ]
  }
  assert result == expected

# === parse_in のテスト ===
def test_parse_in():
  expression = "in [5, 15, \"xyz\"]"
  result = parse_in(expression, "TestProperty", "number")
  expected = {
    "or": [
      {"property": "TestProperty", "number": {"equals": 5}},
      {"property": "TestProperty", "number": {"equals": 15}},
      {"property": "TestProperty", "number": {"equals": "xyz"}},
    ]
  }
  assert result == expected

# === parse_inequality のテスト ===
@pytest.mark.parametrize("expression, expected_key, expected_value", [
  (">=100", "greater_than_or_equal_to", 100),
  (">50", "greater_than", 50),
  ("<=30", "less_than_or_equal_to", 30),
  ("<20", "less_than", 20),
  ("≥100", "greater_than_or_equal_to", 100),
  ("＞＝200", "greater_than_or_equal_to", 200),
  ("≤50", "less_than_or_equal_to", 50),
  ("＜＝30", "less_than_or_equal_to", 30),
  ("＞100", "greater_than", 100),
  ("＜20", "less_than", 20),
])
def test_parse_inequality(expression, expected_key, expected_value):
  result = parse_inequality(expression, "TestProperty", "number")
  expected = {
    "property": "TestProperty",
    "number": {expected_key: expected_value}
  }
  assert result == expected

# === parse_not_equal のテスト ===
def test_parse_not_equal():
  expression = "not 42"
  result = parse_not_equal(expression, "TestProperty", "number")
  expected = {
    "property": "TestProperty",
    "number": {"does_not_equal": 42}
  }
  assert result == expected

# === parse_equal のテスト ===
@pytest.mark.parametrize("expression, expected_key, expected_value",[
  ("= 123", "number", 123),
  ("= \"Not started\"", "select", "Not started")
])
def test_parse_equal(expression, expected_key, expected_value):
  result = parse_equal(expression, "TestProperty", expected_key)
  expected = {
    "property": "TestProperty",
    expected_key: {"equals": expected_value}
  }
  assert result == expected

# === parse_or のテスト ===
def test_parse_or():
  expression = "apple or banana"
  result = parse_or(expression, "Fruit", "text")
  expected = {
    "or": [
      {"property": "Fruit", "text": {"equals": "apple"}},
      {"property": "Fruit", "text": {"equals": "banana"}},
    ]
  }
  assert result == expected

# === parse_like のテスト ===
@pytest.mark.parametrize("expression, expected_key, expected_value", [
  ('like "hello"', "contains", "hello"),
  ('not like "world"', "does_not_contain", "world"),
])
def test_parse_like(expression, expected_key, expected_value):
  result = parse_like(expression, "TextField", "text")
  expected = {
    "property": "TextField",
    "text": {expected_key: expected_value}
  }
  assert result == expected

# === parse_value のテスト ===
@pytest.mark.parametrize("input_value, expected_output", [
  ('"hello"', "hello"),  # ダブルクォート囲み
  ("123", 123),  # 整数
  ("12.34", 12.34),  # 浮動小数点
  ("   45   ", 45),  # 空白を含む
  ("not_a_number", "not_a_number")  # 数字に変換できない文字列
])
def test_parse_value(input_value, expected_output):
  assert parse_value(input_value) == expected_output
