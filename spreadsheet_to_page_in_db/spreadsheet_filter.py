import re
import pandas as pd

# pandas df の query ではこれをかける必要はない。
def parse_value(token: str):
  """
  ダブルクォートで囲まれていれば文字列として扱い、
  囲まれていなければ数値 (int/float) としてパースを試みる。
  """
  token = token.strip()
  
  # ダブルクォートで始まり終わる場合 → 中身を文字列として返す
  # 例:  "abc"  ->  abc
  if len(token) >= 2 and (token[0] == '"' or token[0] == '“') and (token[-1] == '"' or token[-1] == '”'):
    if token[0] == '“' or token[-1] == '”':
      token = '"' + token[1:len(token)-1] + '"' 
    return token  
  
  # ダブルクォートがなければ数値として扱う
  # 1) int
  try:
    return int(token)
  except ValueError:
    pass
  
  # 2) float
  try:
    return float(token)
  except ValueError:
    pass
  
  # 3) それでも変換できなければ文字列として扱う
  return f'"{token}"'

# 'not in [xx, yy]' → '~col.isin([xx, yy])'
#   という形に直すための置換。([^\]]+) は ']' でない文字の繰り返し
def parse_not_in(column: str, m) -> str:
  
  elements = [parse_value(s.strip()) for s in m.group(1).split(",")]
  return f'{column} not in {elements}'

# 'in [xx, yy]' → 'col.isin([xx, yy])'
def parse_in(column: str, m) -> str:
  
  elements = [parse_value(s.strip()) for s in m.group(1).split(",")]
  return f"{column} in {elements}"

# '>= or > or <= or <'
def parse_inequality(expression:str, column) -> str:
  expression = re.sub(r'≥', '>=', expression)  # ≥ → >=
  expression = re.sub(r'≤', '<=', expression)  # ≤ → <=
  expression = re.sub(r'＞＝', '>=', expression)  # ＞＝ → >=
  expression = re.sub(r'＜＝', '<=', expression)  # ＜＝ → <=
  expression = re.sub(r'＞', '>', expression)  # ＞ → >
  expression = re.sub(r'＜', '<', expression)  # ＜ → <
  
  # 演算子と数値の間に確実にスペースを入れる
  expression = re.sub(r'(>=|<=|>|<)\s*', r' \1 ', expression).strip()

  return f'{column} {expression}'

# 'not xx'
def parse_not_equal(column: str, m) -> str:
  
  return f"{column} != {parse_value(m.group(1).strip())}"


# ' == xx'
def parse_equal(column: str, m) -> str:
  
  return f"{column} == {parse_value(m.group(1).strip())}"


# ' xx or yy '
def parse_or(column: str, m) -> str:
  
  left, right = parse_value(m.group(1).strip()), parse_value(m.group(2).strip())

  return f"({column} == {left}) | ({column} == {right})"



# 例: 'col like \'ABC\''
#     'col not like \'ABC\''
def parse_like(column: str, m) -> str:
  
  not_like = m.group(1) is not None
  like_target = m.group(2)

  if not_like:
    return f"~{column}.str.contains(\"{like_target}\")"
  else:
    return f"{column}.str.contains(\"{like_target}\")"


# Notion -> df.query
def translate_to_query(expression: str, column: str) -> str:
  # 両サイドの空白を削除
  expression = expression.strip()
  # 'not in [xx, yy]' → '~col.isin([xx, yy])'
  #   という形に直すための置換。([^\]]+) は ']' でない文字の繰り返し
  pattern_not_in = rf'^not\s+in\s*\[\s*([^\]]+)\s*\]$'
  match_not_in = re.match(pattern_not_in, expression)
  if match_not_in:
    return parse_not_in(column=column, m=match_not_in)

  # 'in [xx, yy]' → 'col.isin([xx, yy])'
  pattern_in = rf'in\s*\[\s*([^\]]+)\s*\]'
  match_in = re.match(pattern_in, expression)
  if match_in:
    return parse_in(column=column, m=match_in)

  # inequality
  pattern_inequality = rf'>=|>|<=|<|＞＝|＞|＜＝|＜|≥|≤'
  match_inequality = re.match(pattern_inequality, expression)
  if match_inequality:
    return parse_inequality(expression, column)
  
  # 'not xx' 
  pattern_not_equal = rf'^not\s+(.+)'
  match_not_equal = re.match(pattern_not_equal, expression)
  if match_not_equal:
    return parse_not_equal(column=column, m=match_not_equal)
  
  # 'equal xx'
  pattern_equal = rf'=\s*(.+)'
  match_equal = re.match(pattern_equal, expression)
  if match_equal:
    return parse_equal(column=column, m=match_equal)
  
  # 'xx or yy' → 'col == xx or col == yy'
  #   実際には xx, yy それぞれ文字列か数値かでクォートを付けるなど要注意
  #   ここでは簡易実装
  pattern_or = rf'^(.+)\s+or\s+(.+)$'
  match_or = re.match(pattern_or, expression)
  if match_or:
    return parse_or(column, m=match_or)
  
  # 例: 'col like \'ABC\''
  #     'col not like \'ABC\''
  pattern_like = rf'^(not\s+)?like\s+"([^"]+)"$'
  match_like = re.match(pattern_like, expression)
  if match_like:
    # パターンに合わない場合はそのまま返すか、エラーにするなどの設計
    return parse_like(column, m=match_like)
  # エラー処理
  raise ValueError(f' {expression} は無効な filter 条件です。')

# DataFrame(original) -> DataFrame(filtered)
def create_spreadsheet_filter(df_original, filters_box):
  df_filtered = df_original
  for filter_element in filters_box:
    if filter_element["target"] == "Column":
      expression = filter_element["expression"]
      column = filter_element["name"]
      query = translate_to_query(expression=expression, column=column)
      df_filtered = df_filtered.query(query)
  return df_filtered

# --- 使い方例 ---
if __name__ == "__main__":
  df = pd.DataFrame({
    'col': [10, 20, 30, 40, 50, 60],
    "col_str": ["a", "b", "c", "d", "4", "弥生時代"],
    'name': ['A', 'B', 'C', 'D', 'E', '弥生時代']
  })

  dsl_condition = '= “弥生時代”'  # 例: col が 10 or 20 の行を取りたい
  query_expr = translate_to_query(dsl_condition, column='col_str')
  print('query_expr:', query_expr)
  # -> query_expr: (col == 10) | (col == 20)

  filtered_df = df.query(query_expr)
  print(filtered_df)
