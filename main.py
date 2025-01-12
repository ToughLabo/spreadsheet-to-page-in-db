import requests
from dotenv import load_dotenv
import os
import json
import pandas as pd

def append_sibling_paragraph_to_page(headers, page_id, type, new_content):
  url = f"https://api.notion.com/v1/blocks/{page_id}/children"
  payload = {
    "children": [
      {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
          "rich_text": [
            {
              "type": type,
              "text": {
                "content": new_content
              }
            }
          ]
        }
      }
    ]
  }
  res = requests.patch(url, headers=headers, data=json.dumps(payload))
  if res.status_code != 200:
    print(f"Error: {res.status_code}")
    print(res.text)
  return res.json()

def append_paragraph_to_toggle(headers, toggle_block_id, text_content):
  """
  既存のトグルブロックに子ブロック（段落）を追加する
  """
  url = f"https://api.notion.com/v1/blocks/{toggle_block_id}/children"
  # TODO: いい感じに修正が必要　ひとまず上書きではなく、追加するように調整
  payload = {
    "children": [
      {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
          "rich_text": [
            {
              "type": "text",
              "text": {
                "content": text_content
              }
            }
          ]
        }
      }
    ]
  }

  response = requests.patch(url, headers=headers, data=json.dumps(payload))
  if response.status_code == 200:
    print("成功:", response.json())
  else:
    print("失敗:", response.status_code, response.text)


def main():
  load_dotenv("config/.env")

  NOTION_API_KEY = os.getenv("NOTION_API_KEY")
  NOTION_VERSION = os.getenv("NOTION_VERSION")
  database_id = os.getenv("NOTION_DATABASE_ID")
  BLOCK_1_COLUMN_NUMBER = os.getenv("BLOCK_1_COLUMN_NUMBER")
  BLOCK_2_COLUMN_NUMBER = os.getenv("BLOCK_2_COLUMN_NUMBER")
  BLOCK_3_COLUMN_NUMBER = os.getenv("BLOCK_3_COLUMN_NUMBER")
  BLOCK_4_COLUMN_NUMBER = os.getenv("BLOCK_4_COLUMN_NUMBER")
  BLOCK_5_COLUMN_NUMBER = os.getenv("BLOCK_5_COLUMN_NUMBER")
  BLOCK_6_COLUMN_NUMBER = os.getenv("BLOCK_6_COLUMN_NUMBER")
  CONDITION_COLUMN_NUMBER = os.getenv("CONDITION_COLUMN_NUMBER")
  
  df = pd.read_csv("const/exampole.csv", header=0)

  url_for_page_ids = f"https://api.notion.com/v1/databases/{database_id}/query"

  headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
  }

  # order property でソート順を指定
  payload = {
    "sorts": [
      {
        "property": "order",
        "direction": "ascending"
      }
    ]
  }

  res = requests.post(url_for_page_ids, headers=headers, data=json.dumps(payload))

  if res.status_code != 200:
    print(f"Error: {res.status_code}")
    print(res.text)
    exit()

  data = res.json()

  pages = data.get("results", usecols=[BLOCK_1_COLUMN_NUMBER, BLOCK_2_COLUMN_NUMBER, BLOCK_3_COLUMN_NUMBER, BLOCK_4_COLUMN_NUMBER, BLOCK_5_COLUMN_NUMBER, BLOCK_6_COLUMN_NUMBER])

  # csv の順番 と page_id の順番が一致していることを仮定する。
  for index, page in enumerate(pages):
    page_id = page["id"]
    url_for_block_ids = f"https://api.notion.com/v1/blocks/{page_id}/children"
    res = requests.get(url_for_block_ids, headers=headers)
    if res.status_code != 200:
      print(f"Error: {res.status_code}")
      print(res.text)
      exit()
      
    data = res.json()
    blocks = data["results"]
    # 例題があるケース
    if df.iloc[index, CONDITION_COLUMN_NUMBER]:
      for b in blocks:
        block_type = b["type"]  # paragraph, heading_1, toggle, ...
        block_id   = b["id"]
        # heading_3 なら数学の場合には、 問題文、チェックの解答、ここで絶対に学んでほしいことの３択
        if block_type == "heading_3":
          is_toggleable = b["heading_3"]["is_toggleable"]
          # True なら Toggle heading 3 （問題文）False ならそれ以外
          if is_toggleable:
            text = b["heading_3"]["rich_text"]["text"]["content"]
            if text == "問題文":
              problem_text = df.iloc[index, BLOCK_1_COLUMN_NUMBER]
              append_paragraph_to_toggle(headers, block_id, problem_text)
          else:
            # チェックの解答
            check_answer_text = df.iloc[index, BLOCK_2_COLUMN_NUMBER]
            append_sibling_paragraph_to_page(headers, page_id, "numbered_list_item", check_answer_text)
            # ここで絶対に学んでほしいこと
            learn_text = df.iloc[index, BLOCK_3_COLUMN_NUMBER]
            append_sibling_paragraph_to_page(headers, page_id, "bulleted_list_item", learn_text)
        elif block_type == "toggle":
          text = b["toggle"]["rich_text"]["text"]["content"]
          # 参照のテキストを挿入
          if text == "この問題そのものに関して":
            reference_text = df.iloc[index, BLOCK_4_COLUMN_NUMBER]
            append_paragraph_to_toggle(headers, block_id, reference_text)
          # 練習問題の解答
          elif text == "解答":
            practice_answer_text = df.iloc[index, BLOCK_6_COLUMN_NUMBER]
            append_paragraph_to_toggle(headers, block_id, practice_answer_text)
        # 練習問題の問題文
        elif block_type == "bulleted_list_item":
          text = b["bulleted_list_item"]["text"]["content"]
          if text == "問題文":
            practice_problem_text = df.iloc[index, BLOCK_5_COLUMN_NUMBER]
            append_sibling_paragraph_to_page(headers, page_id, "bulleted_list_item", practice_problem_text)
    # 例題がないケース
    else:
      for b in blocks:
        block_type = b["type"]  
        block_id   = b["id"]
        # heading_3 なら数学の場合には、 チェックの解答、ここで絶対に学んでほしいことの２択
        if block_type == "heading_3":
          # チェックの解答
          check_answer_text = df.iloc[index, BLOCK_2_COLUMN_NUMBER]
          append_sibling_paragraph_to_page(headers, page_id, "numbered_list_item", check_answer_text)
          # ここで絶対に学んでほしいこと
          learn_text = df.iloc[index, BLOCK_3_COLUMN_NUMBER]
          append_sibling_paragraph_to_page(headers, page_id, "bulleted_list_item", learn_text)
        elif block_type == "toggle":
          text = b["toggle"]["rich_text"]["text"]["content"]
          # 参照のテキストを挿入
          if text == "この問題そのものに関して":
            reference_text = df.iloc[index, BLOCK_4_COLUMN_NUMBER]
            append_paragraph_to_toggle(headers, block_id, reference_text)
          # 練習問題の解答
          elif text == "解答":
            practice_answer_text = df.iloc[index, BLOCK_6_COLUMN_NUMBER]
            append_paragraph_to_toggle(headers, block_id, practice_answer_text)
        # 練習問題の問題文
        elif block_type == "bulleted_list_item":
          text = b["bulleted_list_item"]["text"]["content"]
          if text == "問題文":
            practice_problem_text = df.iloc[index, BLOCK_5_COLUMN_NUMBER]
            append_sibling_paragraph_to_page(headers, page_id, "bulleted_list_item", practice_problem_text)
    
