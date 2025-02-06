import re

def parse_value(token: str):
  """
  ダブルクォートで囲まれていれば文字列として扱い、
  囲まれていなければ数値 (int/float) としてパースを試みる。
  """
  token = token.strip()
  
  # ダブルクォートで始まり終わる場合 → 中身を文字列として返す
  # 例:  "abc"  ->  abc
  if len(token) >= 2 and (token[0] == '"' or token[0] == '“') and (token[-1] == '"' or token[-1] == '”'):
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
def parse_not_in(property_name, property_type, m) -> str:
  
  inside_bracktes = m.group(1)
  elements = [parse_value(s) for s in inside_bracktes.split(",")]
  filters = []
  if property_type != "multi_select":
    for element in elements:
      filters.append({
        "property": property_name,
        property_type: {
          "does_not_equal": element
        }
      })
  else:
    for element in elements:
      filters.append({
        "property": property_name,
        property_type: {
          "does_not_contain": element
        }
      })
  return {"and": filters}

# 'in [xx, yy]' → 'col.isin([xx, yy])'
def parse_in(property_name, property_type, m) -> str:
  
  inside_bracktes = m.group(1)
  elements = [parse_value(s) for s in inside_bracktes.split(",")]
  filters = []
  if property_type != "multi_select":
    for element in elements:
      filters.append({
        "property": property_name,
        property_type: {
          "equals": element
        }
      })
  else:
    for element in elements:
      filters.append({
        "property": property_name,
        property_type: {
          "contains": element
        }
      })
  return {"or": filters}

# '>= or > or <= or <'
def parse_inequality(expression:str, property_name, property_type) -> str:
  # 事前に全角記号を半角記号に統一する
  expression = (
    expression.replace("＜＝", "<=")
              .replace("＞＝", ">=")
              .translate(str.maketrans({'≥': '>=', '≤': '<=', '＞': '>', '＜': '<'}))
  )

  if expression.startswith(">="):
    return {"property": property_name, property_type: {"greater_than_or_equal_to": parse_value(expression[2:])}}
  elif expression.startswith(">"):
    return {"property": property_name, property_type: {"greater_than": parse_value(expression[1:])}}
  elif expression.startswith("<="):
    return {"property": property_name, property_type: {"less_than_or_equal_to": parse_value(expression[2:])}}
  elif expression.startswith("<"):
    return {"property": property_name, property_type: {"less_than": parse_value(expression[1:])}}
    
  raise ValueError(f' {expression} は無効な不等式の filter 条件です。（Notion側）のフィルター')

# 'not xx'
def parse_not_equal(property_name, property_type, m) -> str:
  
  expression = parse_value(m.group(1))
  if property_type != "multi_select":
    f = {
      "property": property_name,
      property_type: {
        "does_not_equal": expression
      }
    }
  else:
    f = {
      "property": property_name,
      property_type: {
        "does_not_contain": expression
      }
    }
  return f

# ' == xx'
def parse_equal(property_name, property_type, m) -> str:
  
  expression = parse_value(m.group(1))
  if property_type != "multi_select":
    f = {
      "property": property_name,
      property_type: {
        "equals": expression
      }
    }
  else:
    f = {
      "property": property_name,
      property_type: {
        "contains": expression
      }
    }
  return f

# ' xx or yy '
def parse_or(property_name, property_type, m) -> str:
  
  elements = [parse_value(m.group(1)), parse_value((m.group(2)))]
  filters = []
  if property_type != "multi_select":
    for element in elements:
      filters.append({
        "property": property_name,
        property_type: {
          "equals": element
        }
      })
  else:
    for element in elements:
      filters.append({
        "property": property_name,
        property_type: {
          "contains": element
        }
      })
  return {"or": filters}

# 例: 'col like \'ABC\''
#     'col not like \'ABC\''
def parse_like(property_name, property_type, m) -> str:
  
  not_like_part = m.group(1)      # 'not ' or None
  like_target = parse_value(m.group(2))        # 'ABC'
  
  if not_like_part:
    f = {
      "property": property_name,
      property_type:{
        "does_not_contain": like_target
      }
    }
    return f
  else:
    f = {
      "property": property_name,
      property_type:{
        "contains": like_target
      }
    }
    return f

# Notion -> Notion database query filter
def translate_to_query(expression: str, property_name: str, property_type) -> str:
  # 両サイドの空白を削除
  expression = expression.strip()
  # 'not in [xx, yy]' → '~col.isin([xx, yy])'
  #   という形に直すための置換。([^\]]+) は ']' でない文字の繰り返し
  pattern_not_in = rf'^not\s+in\s*\[\s*([^\]]+)\s*\]$'
  match_not_in = re.match(pattern_not_in, expression)
  if match_not_in:
    return parse_not_in(property_name, property_type,m=match_not_in)

  # 'in [xx, yy]' → 'col.isin([xx, yy])'
  pattern_in = rf'in\s*\[\s*([^\]]+)\s*\]'
  match_in = re.match(pattern_in, expression)
  if match_in:
    return parse_in(property_name, property_type, m=match_in)

  # inequality
  pattern_inequality = rf'>=|>|<=|<|＞＝|＞|＜＝|＜|≥|≤'
  match_inequality = re.match(pattern_inequality, expression)
  if match_inequality:
    return parse_inequality(expression, property_name, property_type)
  
  # 'not xx' 
  pattern_not_equal = rf'^not\s+(.+)'
  match_not_equal = re.match(pattern_not_equal, expression)
  if match_not_equal:
    return parse_not_equal(property_name, property_type, m=match_not_equal)
  
  # 'equal xx'
  pattern_equal = rf'=\s*(.+)'
  
  match_equal = re.match(pattern_equal, expression)
  
  
  if match_equal:
    return parse_equal(property_name, property_type, m=match_equal)
  
  # 'xx or yy' → 'col == xx or col == yy'
  #   実際には xx, yy それぞれ文字列か数値かでクォートを付けるなど要注意
  #   ここでは簡易実装
  pattern_or = rf'^(.+)\s+or\s+(.+)$'
  match_or = re.match(pattern_or, expression)
  if match_or:
    return parse_or(property_name, property_type, m=match_or)
  
  # 例: 'col like \'ABC\''
  #     'col not like \'ABC\''
  pattern_like = rf'^(not\s+)?like\s+"([^"]+)"$'
  match_like = re.match(pattern_like, expression)
  if match_like:
    # パターンに合わない場合はそのまま返すか、エラーにするなどの設計
    return parse_like(property_name, property_type, m=match_like)
  # エラー処理
  raise ValueError(f' {expression} は無効な filter 条件です。（Notion側）のフィルター')

# FILTERS_BOX（中間形） -> Notion DB Query Filter Object (filters_box は 辞書のリスト, 中身の辞書は, type, name, expression)
def create_notion_filter(filters_box):
  parsed_filters = []
  error_flag = False  # エラー発生フラグ

  for f in filters_box:
    if f["target"] == "Property":
      expression = f["expression"]
      property_name = f["name"]
      property_type = f["type"]

      try:
        parsed_filter = translate_to_query(expression=expression, property_name=property_name, property_type=property_type)
        parsed_filters.append(parsed_filter)
      except Exception as e:
        print(f"translate_to_query でエラー発生: {e} (property_name: {property_name}, expression: {expression})")
        error_flag = True  # エラーを記録

  return {"or": parsed_filters}, error_flag

# --- テスト用 ---
if __name__ == "__main__":
  pass
