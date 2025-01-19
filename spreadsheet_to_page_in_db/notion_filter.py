import re
import requests
from dotenv import load_dotenv
import os

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
def parse_not_in(expression: str, property_name, property_type) -> str:
  pattern = r'^(not\s+)?in\s*\[\s*([^\]]+)\s*\]$'
  m = re.match(pattern, expression.strip())
  inside_bracktes = m.group(2)
  elements = [parse_value(s) for s in inside_bracktes.split(",")]
  filters = []
  for element in elements:
    filters.append({
      "property": property_name,
      property_type: {
        "does_not_equal": element
      }
    })
  return {"or": filters}

# 'in [xx, yy]' → 'col.isin([xx, yy])'
def parse_in(expression: str, property_name, property_type) -> str:
  pattern = r'^(\s+)?in\s*\[\s*([^\]]+)\s*\]$'
  m = re.match(pattern, expression.strip())
  inside_bracktes = m.group(2)
  elements = [parse_value(s) for s in inside_bracktes.split(",")]
  filters = []
  for element in elements:
    filters.append({
      "property": property_name,
      property_type: {
        "equals": element
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
def parse_not_equal(expression:str, property_name, property_type) -> str:
  pattern = rf"not\s+(\S+)"
  m = re.match(pattern, expression)
  expression = parse_value(m.group(1))
  filter = {
    "property": property_name,
    property_type: {
      "does_not_equal": expression
    }
  }
  return filter

# ' == xx'
def parse_equal(expression:str, property_name, property_type) -> str:
  pattern = rf"=\s+(\S+)"
  m = re.match(pattern, expression)
  expression = parse_value(m.group(1))
  filter = {
    "property": property_name,
    property_type: {
      "equals": expression
    }
  }
  return filter

# ' xx or yy '
def parse_or(expression:str, property_name, property_type) -> str:
  pattern = rf'(\S+)\s+or\s+(\S+)'
  m = re.match(pattern, expression.strip())
  elements = [parse_value(m.group(1)), parse_value((m.group(2)))]
  filters = []
  for element in elements:
    filters.append({
      "property": property_name,
      property_type: {
        "equals": element
      }
    })
  return {"or": filters}

# 例: 'col like \'ABC\''
#     'col not like \'ABC\''
def parse_like(expression:str, property_name, property_type) -> str:
  pattern = rf'^(not\s+)?like\s+"([^"]+)"$'
  m = re.match(pattern, expression)
  not_like_part = m.group(1)      # 'not ' or None
  like_target = parse_value(m.group(2))        # 'ABC'
  
  if not_like_part:
    filter = {
      "property": property_name,
      property_type:{
        "does_not_contain": like_target
      }
    }
    return filter
  else:
    filter = {
      "property": property_name,
      property_type:{
        "contains": like_target
      }
    }
    return filter

# Notion -> Notion database query filter
def translate_to_query(expression: str, property_name: str, property_type) -> str:
  # 行頭の空白を削除
  expression.lstrip()
  # 'not in [xx, yy]' → '~col.isin([xx, yy])'
  #   という形に直すための置換。([^\]]+) は ']' でない文字の繰り返し
  pattern_not_in = rf'not\s+in\s*\[\s*([^\]]+)\s*\]'
  match_not_in = re.match(pattern_not_in, expression)
  if match_not_in:
    return parse_not_in(expression, property_name, property_type)

  # 'in [xx, yy]' → 'col.isin([xx, yy])'
  pattern_in = rf'in\s*\[\s*([^\]]+)\s*\]'
  match_in = re.match(pattern_in, expression)
  if match_in:
    return parse_in(expression, property_name, property_type)

  # inequality
  pattern_inequality = rf'>=|>|<=|<|＞＝|＞|＜＝|＜|≥|≤'
  match_inequality = re.match(pattern_inequality, expression)
  if match_inequality:
    return parse_inequality(expression, property_name, property_type)
  
  # 'not xx' 
  pattern_not_equal = rf'not\s+(\S+)'
  match_not_equal = re.match(pattern_not_equal, expression)
  if match_not_equal:
    return parse_not_equal(expression, property_name, property_type)
  
  # 'equal xx'
  pattern_equal = fr'=\s+\S+'
  match_equal = re.match(pattern_equal, expression)
  if match_equal:
    return parse_equal(expression, property_name, property_type)
  
  # 'xx or yy' → 'col == xx or col == yy'
  #   実際には xx, yy それぞれ文字列か数値かでクォートを付けるなど要注意
  #   ここでは簡易実装
  pattern_or = rf'(\S+)\s+or\s+(\S+)'
  match_or = re.match(pattern_or, expression)
  if match_or:
    return parse_or(expression, property_name, property_type)
  
  # 例: 'col like \'ABC\''
  #     'col not like \'ABC\''
  pattern_like = rf'^(not\s+)?like\s+"([^"]+)"$'
  match_like = re.match(pattern_like, expression)
  if match_like:
    # パターンに合わない場合はそのまま返すか、エラーにするなどの設計
    return parse_like(expression, property_name, property_type)
  # エラー処理
  raise ValueError(f' {expression} は無効な filter 条件です。（Notion側）のフィルター')

# id と 認証情報から property に関する name と type の対応関係を取得する
def fetch_property_type(output_database_id, headers):
  url = f"https://api.notion.com/v1/databases/{output_database_id}"
  res = requests.get(url=url, headers=headers)
  if res.status_code != 200:
    print("property type を 取得する際にエラーが発生しました。")
    res.raise_for_status
  properties = res.json()["properties"]
  property_dict = {}
  # p_key は property name, p_value は property の中身のjson
  for p_key, p_value in properties.items():
    property_dict[p_key] = p_value["type"]
  return property_dict

# FILTERS_BOX（中間形） -> Notion DB Query Filter Object (filters_box は 辞書のリスト, 中身の辞書は, type, name, expression)
def create_notion_filter(output_database_id, headers, filters_box):
  parsed_filters = []
  property_dict = fetch_property_type(output_database_id, headers)
  for f in filters_box:
    if f["type"] == "Property":
      expression = f["expression"]
      property_name = f["name"]
      property_type = property_dict[f["name"]]
      parsed_filter = translate_to_query(expression=expression,  property_name=property_name, property_type=property_type)
      parsed_filters.append(parsed_filter)
  return {"filter": {"or": parsed_filters}}

# --- テスト用 ---
if __name__ == "__main__":
  load_dotenv("config/.env")
  NOTION_API_KEY = os.getenv("NOTION_API_KEY")
  NOTION_VERSION = os.getenv("NOTION_VERSION")
  TEMPLATE_BOX_DATABASE_ID = os.getenv("NOTION_TEMPLATE_BOX_DATABASE_ID")
  headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
  }
  test_output_database_id = os.getenv("NOTION_TEST_TARGET_DATABASE_ID")
  print(fetch_property_type(test_output_database_id, headers=headers))
