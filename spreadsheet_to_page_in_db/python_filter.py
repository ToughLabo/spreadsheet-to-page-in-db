import re
import pandas as pd

def parse_value(token: str):
  """
  ダブルクォートで囲まれていれば文字列として扱い、
  囲まれていなければ数値 (int/float) としてパースを試みる。
  """
  token = token.strip()
  
  # ダブルクォートで始まり終わる場合 → 中身を文字列として返す
  # 例:  "abc"  ->  abc
  if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
    return token[1:-1]  # 前後の " を除去
  
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
  
  # 3) それでも変換できなければ文字列のまま
  return token

# 'not in [xx, yy]' → '~col.isin([xx, yy])'
#   という形に直すための置換。([^\]]+) は ']' でない文字の繰り返し
def parse_not_in(expression: str, column) -> str:
  expression = re.sub(
    rf'not\s+in\s*\[\s*([^\]]+)\s*\]',
    lambda m: f'{parse_value(column)} not in [{parse_value(m.group(1))}]',
    expression
  )
  return expression

# 'in [xx, yy]' → 'col.isin([xx, yy])'
def parse_in(expression: str, column) -> str:
  expression = re.sub(
    rf'in\s*\[\s*([^\]]+)\s*\]',
    lambda m: f'{parse_value(column)} in [{parse_value(m.group(1))}]',
    expression
  )
  return expression

# '>= or > or <= or <'
def parse_inequality(expression:str, column) -> str:
  expression = expression.replace('≥', '>=')
  expression = expression.replace('＞＝', '>=')
  expression = expression.replace('≤', '<=')
  expression = expression.replace('＜＝', '<=')
  expression = expression.replace('＞', '>')
  expression = expression.replace('＜', '<')
  return f'{parse_value(column)} {expression}'

# 'not xx'
def parse_not_equal(expression:str, column) -> str:
  expression = re.sub(
    rf'not\s+(\S+)',
    lambda m: f'{parse_value(column)} != {parse_value(m.group(1))}',
    expression
  )
  return expression

# ' == xx'
def parse_equal(expression:str, column) -> str:
  expression = re.sub(
    rf'=\s+(\S+)',
    lambda m: f'{parse_value(column)} == {parse_value(m.group(1))}',
    expression
  )
  return expression

# ' xx or yy '
def parse_or(expression:str, column) -> str:
  pattern_or = rf'(\S+)\s+or\s+(\S+)'
  # キャプチャした2つを両方 col==... に変換して '|' でつなぐ
  expression = re.sub(
    pattern_or,
    lambda m: f'{parse_value(column)} == {parse_value(m.group(1))} | {parse_value(column)} == {parse_value(m.group(2))}',
    expression
  )
  return expression

# 例: 'col like \'ABC\''
#     'col not like \'ABC\''
def parse_like(expression:str, column) -> str:
  pattern = rf'^\s*(not\s+)?like\s+"([^"]+)"$'
  m = re.match(pattern, expression)
  not_like_part = m.group(1)      # 'not ' or None
  like_target = parse_value(m.group(2))        # 'ABC'
  
  if not_like_part:
    return f'~{parse_value(column)}.str.contains({like_target})'
  else:
    return f'{parse_value(column)}.str.contains({like_target})'

# Notion -> df.query
def translate_to_query(expression: str, column: str) -> str:
  # 'not in [xx, yy]' → '~col.isin([xx, yy])'
  #   という形に直すための置換。([^\]]+) は ']' でない文字の繰り返し
  pattern_not_in = rf'not\s+in\s*\[\s*([^\]]+)\s*\]'
  match_not_in = re.match(pattern_not_in, expression)
  if match_not_in:
    return parse_not_in(expression, column)

  # 'in [xx, yy]' → 'col.isin([xx, yy])'
  pattern_in = rf'in\s*\[\s*([^\]]+)\s*\]'
  match_in = re.match(pattern_in, expression)
  if match_in:
    return parse_in(expression, column)

  # inequality
  pattern_inequality = rf'>=|>|<=|<|＞＝|＞|＜＝|＜|≥|≤'
  match_inequality = re.match(pattern_inequality, expression)
  if match_inequality:
    return parse_inequality(expression, column)
  
  # 'not xx' 
  pattern_not_equal = rf'not\s+(\S+)'
  match_not_equal = re.match(pattern_not_equal, expression)
  if match_not_equal:
    return parse_not_equal(expression, column)
  
  # 'equal xx'
  pattern_equal = fr'=\s+\S+'
  match_equal = re.match(pattern_equal, expression)
  if match_equal:
    return parse_equal(expression, column)
  
  # 'xx or yy' → 'col == xx or col == yy'
  #   実際には xx, yy それぞれ文字列か数値かでクォートを付けるなど要注意
  #   ここでは簡易実装
  pattern_or = rf'(\S+)\s+or\s+(\S+)'
  match_or = re.match(pattern_or, expression)
  if match_or:
    return parse_or(expression, column)
  
  # 例: 'col like \'ABC\''
  #     'col not like \'ABC\''
  pattern_like = rf'^\s*(not\s+)?like\s+"([^"]+)"$'
  match_like = re.match(pattern_like, expression)
  if match_like:
    # パターンに合わない場合はそのまま返すか、エラーにするなどの設計
    return parse_like(expression, column)
  # エラー処理
  raise ValueError(f' {expression} は無効な filter 条件です。')

# DataFrame(original) -> DataFrame(filtered)
def filter_dataframe(df_original, filters_box):
  df_filtered = df_original
  for filter in filters_box:
    if filter["type"] == "Column":
      expression = filter["expression"]
      column = filter["name"]
      query = translate_to_query(expression=expression, column=column)
      df_filtered = df_filtered.query(query)
  return df_filtered

# --- 使い方例 ---
if __name__ == "__main__":
  df = pd.DataFrame({
    'col': [10, 20, 30, 40, 50],
    'name': ['A', 'B', 'C', 'D', 'E']
  })

  dsl_condition = '10 or 20'  # 例: col が 10 or 20 の行を取りたい
  query_expr = translate_to_query(dsl_condition, column='col')
  print('query_expr:', query_expr)
  # -> query_expr: (col == 10) | (col == 20)

  filtered_df = df.query(query_expr)
  print(filtered_df)
