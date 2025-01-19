import pytest
from spreadsheet_to_page_in_db.spreadsheet_filter import (
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
  result = parse_not_in(expression, "col")
  expected = "col not in [10, 20, 'abc']"
  assert result == expected

# === parse_in のテスト ===
def test_parse_in():
  expression = "in [5, 15, \"xyz\"]"
  result = parse_in(expression, "col")
  expected = "col in [5, 15, 'xyz']"
  assert result == expected

# === parse_inequality のテスト ===
@pytest.mark.parametrize("expression, expected", [
  (">=100", "col >= 100"),
  (">50", "col > 50"),
  ("<=30", "col <= 30"),
  ("<20", "col < 20"),
  ("≥100", "col >= 100"),
  ("＞＝200", "col >= 200"),
  ("≤50", "col <= 50"),
  ("＜＝30", "col <= 30"),
  ("＞100", "col > 100"),
  ("＜20", "col < 20"),
])
def test_parse_inequality(expression, expected):
  result = parse_inequality(expression, "col")
  assert result == expected

# === parse_not_equal のテスト ===
def test_parse_not_equal():
  expression = "not 42"
  result = parse_not_equal(expression, "col")
  expected = "col != 42"
  assert result == expected

# === parse_equal のテスト ===
def test_parse_equal():
  expression = "= 123"
  result = parse_equal(expression, "col")
  expected = "col == 123"
  assert result == expected

# === parse_or のテスト ===
def test_parse_or():
  expression = "apple or banana"
  result = parse_or(expression, "col")
  expected = "(col == 'apple') | (col == 'banana')"
  assert result == expected

# === parse_like のテスト ===
@pytest.mark.parametrize("expression, expected", [
  ('like "hello"', "col.str.contains(\"hello\")"),
  ('not like "world"', "~col.str.contains(\"world\")"),
])
def test_parse_like(expression, expected):
  result = parse_like(expression, "col")
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
