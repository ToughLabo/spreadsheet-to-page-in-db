import requests
from dotenv import load_dotenv
import os
import json
from notion_filter import create_filter
from parse import inline_text_to_rich_text, parse_blocks

# Block変数があるか否かを判定する関数。（TODO: rich_text の場合にのみ対応。ここでは text が BLOCK_NUM だけが入った rich_text か他の rich_text だと仮定する。）
def is_block_var(rich_text) :
  # BLOCK 変数の場合
  if len(rich_text) == 1 and rich_text[0]["type"] == "text":
    # 無駄な空白の削除
    block_var = rich_text[0]["text"]["content"].strip()
    # BLOCK変数が1桁数字の場合
    if len(block_var) == 7:
      var_num = int(block_var[6])
      return True, var_num
    elif len(block_var) == 8:
      var_num = int(block_var[6:8])
      return True, var_num
    else:
      raise ValueError("3桁以上の BLOCK 変数には対応していません。")
      return False, None
  # BLOCK変数ではない場合
  else:
    return False, None

# Template 対応ブロック作成
# callout （ custom_emoji を使えないことに注意。）
def make_callout_block(headers, callout_block, df_row, BLOCK_VAR_BOX):
  # icon の処理
  if callout_block["callout"]["icon"] and len(callout_block["callout"]["icon"]) == 1:
    icon = {"type": "emoji", "emoji": callout_block["icon"]["emoji"]}
  else:
    icon = None
  # 通常のテキストで書いている場合にのみ rich_text は空でない
  rich_text = callout_block["callout"]["rich_text"]
  is_block_var_flag, block_var_num = is_block_var(rich_text=rich_text)
  # block 変数がある場合の処理 （callout の場合には rich_text として処理してよい。）
  if is_block_var_flag:
    block_var = BLOCK_VAR_BOX[block_var_num]
    text = df_row[block_var["column"]]
    is_bold = block_var[block_var["bold"]]
    is_underline = block_var[block_var["underline"]]
    is_italic = block_var[block_var["italic"]]
    is_strikethrough = block_var[block_var["strikethrough"]]
    rich_text = inline_text_to_rich_text(inline_text=text, is_bold=is_bold, is_italic=is_italic, is_underline=is_underline, is_strikethrough=is_strikethrough)
  color = callout_block["callout"]["color"]
  # children の作成
  complete_children = []
  if callout_block["has_children"]:
    block_id = callout_block["id"]
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    res = requests.get(url=url, headers=headers)
    if res.status_code != 200:
      print("callout block の children を取得する時にエラーが発生しました。")
      res.raise_for_status()
    children = res.json()["results"]
    for child_block in children:
      complete_child_block, is_blocks = make_complete_block_for_template(headers=headers, template_block=child_block, df_row=df_row, BLOCK_VAR_BOX=BLOCK_VAR_BOX)
      if is_blocks:
        complete_children.append(complete_child_block)
      else:
        complete_children.extend(complete_child_block)
  # ブロックの作成
  complete_block = {"object":"block", "type":"callout", "callout":{"rich_text": rich_text, "icon": icon, "color": color, "children": complete_children}}
  return complete_block

# column list （ここでは BLOCK 変数を直接処理する必要はない。）
def make_column_list_block(headers, column_list_block, df_row, BLOCK_VAR_BOX):
  complete_column_list_children = []
  # まずは column を取得する
  columns_list_id = column_list_block["id"]
  url = f"https://api.notion.com/v1/blocks/{columns_list_id}/children"
  res = requests.get(url=url, headers=headers)
  if res.status_code != 200:
    print("column_list block の処理の中で children を取得する際にエラーが発生しました。")
    res.raise_for_status
  columns = res.json()["results"]
  for index, column in enumerate(columns):
    column_id = column["id"]
    has_children = column["has_children"]
    complete_column_children = []
    if has_children:
      url = f"https://api.notion.com/v1/blocks/{column_id}/children"
      res = requests.get(url=url,headers=headers)
      if res.status_code != 200:
        print(f"column list の処理の中で {index} 番目の column の内容を取得する時にエラーが発生しました。")
        res.raise_for_status()
      column_children = res.json()["results"]
      for column_child in column_children:
        complete_column_child, is_blocks = make_complete_block_for_template(headers=headers, template_block=column_child, df_row=df_row, BLOCK_VAR_BOX=BLOCK_VAR_BOX)
        if not is_blocks:
          complete_column_children.append(complete_column_child)
        else:
          complete_column_children.extend(complete_column_child)
    # column の block 作成
    column_json = {"type":"column", "column": {"children": complete_column_children}}
    complete_column_list_children.append(column_json)
  # column_list block 作成
  complete_column_list_block = {"object":"block", "type": "column_list", "column_list":{"children": complete_column_list_children}}
  return complete_column_list_block

# diveder 
def make_divider_block():
  return {"object":"block", "type":"divider", "divider": {}}

# heading
def make_heading_block(headers, heading_block, df_row, BLOCK_VAR_BOX):
  # 変数の準備
  heading_type = heading_block["type"]
  rich_text = heading_block[heading_type]["rich_text"]
  color = heading_block[heading_type]["color"]
  is_toggleable = heading_block[heading_type]["is_toggleable"]
  has_children = heading_block["has_children"]
  # ブロック変数の有無を判定
  is_block_var_flag, block_var_num = is_block_var(rich_text=rich_text)
  if is_block_var_flag:
    block_var = BLOCK_VAR_BOX[block_var_num]
    text = df_row[block_var["column"]]
    is_bold = block_var[block_var["bold"]]
    is_underline = block_var[block_var["underline"]]
    is_italic = block_var[block_var["italic"]]
    is_strikethrough = block_var[block_var["strikethrough"]]
    rich_text = inline_text_to_rich_text(inline_text=text, is_bold=is_bold, is_italic=is_italic, is_underline=is_underline, is_strikethrough=is_strikethrough)
  # トグルがあり、そのトグル内に要素が入っている場合の処理
  complete_children = []
  if has_children:
    heading_id = heading_block["id"]
    url = f"https://api.notion.com/v1/blocks/{heading_id}/children"
    res = requests.get(url=url, headers=headers)
    if res.status_code != 200:
      print("heading ブロックの children を取得する際にエラーが発生しました。")
      res.raise_for_status
    children = res.json()["results"]
    for child in children:
      complete_child, is_blocks = make_complete_block_for_template(headers=headers, template_block=child, df_row=df_row, BLOCK_VAR_BOX=BLOCK_VAR_BOX)
      if not is_blocks:
        complete_children.append(complete_child)
      else:
        complete_children.extend(complete_child)
  # ブロックの作成
  complete_block = {
    "object": "block",
    "type": heading_type,
    heading_type: {
      "rich_text": rich_text,
      "color": color,
      "is_toggleable": is_toggleable,
      "children": complete_children
    }
  }
  return complete_block

# paragraph （TODO: 今の所は paragraph の children には対応しない。（テンプレートとしてやる意味が分からん））
def make_paragraph_block(headers, paragraph_block, df_row, BLOCK_VAR_BOX):
  # 変数の準備
  rich_text = paragraph_block["paragraph"]["rich_text"]
  color = paragraph_block["paragraph"]["color"]
  # Block 変数があるか否かの判定
  is_block_var_flag, block_var_num = is_block_var(rich_text=rich_text)
  if is_block_var_flag:
    block_var = BLOCK_VAR_BOX[block_var_num]
    text = df_row[block_var["column"]]
    is_bold = block_var[block_var["bold"]]
    is_underline = block_var[block_var["underline"]]
    is_italic = block_var[block_var["italic"]]
    is_strikethrough = block_var[block_var["strikethrough"]]
    parsed_blocks = parse_blocks(text=text, index=0, is_bold=is_bold, is_italic=is_italic, is_underline=is_underline, is_strikethrough=is_strikethrough)
    return parsed_blocks, True
  # Block 変数がない場合には children に対応する
  else:
    complete_children = []
    if paragraph_block["has_children"]:
      paragraph_id = ["id"]
      url = f"https://api.notion.com/v1/blocks/{paragraph_id}/children"
      res = requests.get(url=url, headers=headers)
      if res.status_code != 200:
        print("paragraph のテンプレートについて、children を取得する際にエラーが発生しました。")
        res.raise_for_status
      children = res.json()["status"]
      for child in children:
        complete_child, is_blocks = make_complete_block_for_template(headers=headers, template_block=child, df_row=df_row, BLOCK_VAR_BOX=BLOCK_VAR_BOX)
        if not is_blocks:
          complete_children.append(complete_child)
        else:
          complete_children.extend(complete_child)
    
    complete_block = {
      "object": "block",
      "type": "paragraph",
      "paragraph": {
        "rich_text": rich_text,
        "color": color,
        "children": complete_children
      }
    }
    return complete_block, False

# toggle 
def make_toggle_block(headers, toggle_block, df_row, BLOCK_VAR_BOX):
  # 変数の準備
  rich_text = toggle_block["toggle"]["rich_text"]
  color = toggle_block["toggle"]["color"]
  has_children = toggle_block["has_children"]
  # ブロック変数の有無を判定
  is_block_var_flag, block_var_num = is_block_var(rich_text=rich_text)
  if is_block_var_flag:
    block_var = BLOCK_VAR_BOX[block_var_num]
    text = df_row[block_var["column"]]
    is_bold = block_var[block_var["bold"]]
    is_underline = block_var[block_var["underline"]]
    is_italic = block_var[block_var["italic"]]
    is_strikethrough = block_var[block_var["strikethrough"]]
    rich_text = inline_text_to_rich_text(inline_text=text, is_bold=is_bold, is_italic=is_italic, is_underline=is_underline, is_strikethrough=is_strikethrough)
  # トグルがあり、そのトグル内に要素が入っている場合の処理
  complete_children = []
  if has_children:
    toggle_id = toggle_block["id"]
    url = f"https://api.notion.com/v1/blocks/{toggle_id}/children"
    res = requests.get(url=url, headers=headers)
    if res.status_code != 200:
      print("toggle ブロックの children を取得する際にエラーが発生しました。")
      res.raise_for_status
    children = res.json()["results"]
    for child in children:
      complete_child, is_blocks = make_complete_block_for_template(headers=headers, template_block=child, df_row=df_row, BLOCK_VAR_BOX=BLOCK_VAR_BOX)
      if not is_blocks:
        complete_children.append(complete_child)
      else:
        complete_children.extend(complete_child)
  # ブロックの作成
  complete_block = {
    "object": "block",
    "type": "toggle",
    "toggle": {
      "rich_text": rich_text,
      "color": color,
      "children": complete_children
    }
  }
  return complete_block


# 未対応ブロックは一応 template_blocks を作成する時点で弾いている （ paragraph の場合だけ block のリストを返すことになるので boolean で区別する）
def make_complete_block_for_template(headers, template_block, df_row, BLOCK_VAR_BOX):
  if template_block["type"] == "callout":
    return make_callout_block(headers=headers, callout_block=template_block, df_row=df_row, BLOCK_VAR_BOX=BLOCK_VAR_BOX), False
  if template_block["type"] == "column_list":
    return make_column_list_block(headers=headers, column_list_block=template_block, df_row=df_row, BLOCK_VAR_BOX=BLOCK_VAR_BOX), False
  if template_block["type"] == "divider":
    return make_divider_block(), False
  if template_block["type"].startswith("heading_"):
    return make_heading_block(headers=headers, heading_block=template_block, df_row=df_row, BLOCK_VAR_BOX=BLOCK_VAR_BOX), False
  if template_block["type"] == "paragraph":
    return make_paragraph_block(headers=headers, paragraph_block=template_block, df_row=df_row, BLOCK_VAR_BOX=BLOCK_VAR_BOX)
  if template_block["type"] == "toggle":
    return make_toggle_block(headers=headers, toggle_block=template_block, df_row=df_row, BLOCK_VAR_BOX=BLOCK_VAR_BOX), False
  raise ValueError(f"{template_block['type']} はテンプレートブロックとしては対応していません。")

# page property を作成する関数
def make_page_property(property_type, property_content):
  # spreadsheet の仕様上 file name はないことを想定
  if property_type == "files":
    files = [{"name":"", "external":{"url": content.strip()}} for content in property_content.split(",")]
    return {"files":files}
  if property_type == "multiselect":
    mutiselect = [{"name": content.strip()} for content in property_content.split(",")]
    return {"multiselect": mutiselect}
  if property_type == "rich_text":
    return {"rich_text": inline_text_to_rich_text(property_content)}
  if property_type in ["select", "status"]:
    return {property_type: {"name":property_content}}
  if property_type == "title":
    return {"type":"title", "title": inline_text_to_rich_text(property_content)}
  if property_type in ["checkbox", "email", "number", "phone_number", "url"]:
    return {property_type: property_content}
  else :
    raise ValueError(f"page property type: {property_type} は処理できません。")

# 全てのページを削除する関数
def delete_pages(output_database_id, headers, FILTERS_BOX) :
  # filterの作成
  parsed_filter = create_filter(output_database_id, headers, FILTERS_BOX)
  # filter を通した DB への query
  url = f"https://api.notion.com/v1/databases/{output_database_id}/query"
  res = requests.post(url=url, headers=headers, json=parsed_filter)
  if res.status_code != 200:
    print("古いページの削除時に filter をかけた post request でエラーが発生しました。")
    raise res.raise_for_status()
  data_list = res.json()["results"]
  for index, data in enumerate(data_list):
    page_id = data["id"]
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"arichived": True}
    res = requests.patch(url=url, headers=headers, data=json.dumps(payload))
    if res.status_code != 200:
      print(f"ページを削除するときにエラーが発生しました。（ {index}個目のページ）")
      res.raise_for_status()
  return parsed_filter

if __name__ == "__main__":
  load_dotenv("config/.env")
  NOTION_API_KEY = os.getenv("NOTION_API_KEY")
  NOTION_VERSION = os.getenv("NOTION_VERSION")
  test_database_id = os.getenv("NOTION_TEST_DATABASE_ID")
  test_page_id = os.getenv("NOTION_TEST_PAGE_ID")
  test_block_id = "180b95a4-c619-8117-a3ea-cb5f6ed30b24"
  headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
  }
  # ブロック作成テスト
  children = [
    {
      "object": "block", 
      "type": "paragraph",
      "paragraph":{
        "rich_text": [
          {
            "type": "text",
            "text": {
              "content": "ここがタイトルになればいいな",
              "link": None
            }
          }
        ]
      }
    },
    {
      "type": "paragraph",
      "paragraph": {
        "rich_text": [
          {
            "type": "text",
            "text": {
              "content":"ここはこどもになればいいな",
              "link": None
            }
          }
        ]
      }
    }
  ]
  
  payload = {
    "children":[{
      "object": "block",
      "type": "paragraph",
      "paragraph": {
        "rich_text":[
          {
            "type": "text",
            "text": {
              "content": "ここが一応親",
              "link": None
            }
          }
        ],
        "color": "purple_background",
        "children": children
      },
    }]
  }
  url = f"https://api.notion.com/v1/blocks/{test_page_id}/children"
  # url = f"https://api.notion.com/v1/pages/{test_page_id}"
  # url = f"https://api.notion.com/v1/blocks/{test_block_id}"
  res = requests.patch(url=url,headers=headers, data=json.dumps(payload))
  if res.status_code != 200:
    raise res.raise_for_status()
  else:
    print(res.json())