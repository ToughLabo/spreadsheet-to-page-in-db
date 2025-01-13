import requests
from dotenv import load_dotenv
import os
import json
import pandas as pd

def append_sibling_paragraph_to_page(headers, page_id, block_id, type, new_content):
  url = f"https://api.notion.com/v1/blocks/{page_id}/children"
  payload = {
    "children": [
      {
        type: {
          "rich_text": [
            {
              "text": {
                "content": new_content
              }
            }
          ]
        }
      }
    ],
    "after": block_id
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
  print(f"text_content:{text_content}")
  url = f"https://api.notion.com/v1/blocks/{toggle_block_id}/children"
  # TODO: いい感じに修正が必要　ひとまず上書きではなく、追加するように調整
  payload = {
    "children": [
      {
        "paragraph": {
          "rich_text": [
            {
              "text": {
                "content": text_content
              }
            }
          ]
        }
      }
    ]
  }

  res = requests.patch(url, headers=headers, data=json.dumps(payload))
  if res.status_code == 200:
    print("成功:", res.json())
  else:
    print("失敗:", res.status_code, res.text)


def main():
  load_dotenv("config/.env")

  NOTION_API_KEY = os.getenv("NOTION_API_KEY")
  NOTION_VERSION = os.getenv("NOTION_VERSION")
  database_id = os.getenv("NOTION_DATABASE_ID")
  BLOCK_1_COLUMN = os.getenv("BLOCK_1_COLUMN")
  BLOCK_2_COLUMN = os.getenv("BLOCK_2_COLUMN")
  BLOCK_3_COLUMN = os.getenv("BLOCK_3_COLUMN")
  BLOCK_4_COLUMN = os.getenv("BLOCK_4_COLUMN")
  BLOCK_5_COLUMN = os.getenv("BLOCK_5_COLUMN")
  BLOCK_6_COLUMN = os.getenv("BLOCK_6_COLUMN")
  CONDITION_COLUMN_NUMBER = os.getenv("CONDITION_COLUMN_NUMBER")
  CSV_FILE_NAME = os.getenv("CSV_FILE_NAME")
  
  df = pd.read_csv(f"const/{CSV_FILE_NAME}", header=0, usecols=[BLOCK_1_COLUMN, BLOCK_2_COLUMN, BLOCK_3_COLUMN, BLOCK_4_COLUMN, BLOCK_5_COLUMN, BLOCK_6_COLUMN])
  df = df.fillna('')
  
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

  pages = data.get("results", [])

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
    print(f"blocks:{blocks}")
    print(f"len(blocks):{len(blocks)}")
    exit()
    # 例題があるケース
    if df.at[index, CONDITION_COLUMN_NUMBER]:
      for b in blocks:
        block_type = b["type"]  # paragraph, heading_1, toggle, ...
        block_id   = b["id"]
        # heading_3 なら数学の場合には、 問題文、チェックの解答、ここで絶対に学んでほしいことの３択
        if block_type == "heading_3" and b["heading_3"]["rich_text"]:
          is_toggleable = b["heading_3"]["is_toggleable"]
          text = b["heading_3"]["rich_text"][0]["plain_text"]
          print(f"block: {b}")
          print(f"text: {text}")
          exit()
          # True なら Toggle heading 3 （問題文）False ならそれ以外
          if is_toggleable:
            if text == "問題文":
              problem_text = df.at[index, BLOCK_1_COLUMN]
              append_paragraph_to_toggle(headers, block_id, problem_text)
          # 練習問題の問題文
          elif text == "・問題文":
            practice_problem_text = df.at[index, BLOCK_5_COLUMN]
            append_sibling_paragraph_to_page(headers, page_id, block_id, "paragraph", practice_problem_text)
          # チェックの解答
          elif text == "チェックの解答":
            check_answer_text = df.at[index, BLOCK_2_COLUMN]
            append_sibling_paragraph_to_page(headers, page_id, block_id, "numbered_list_item", check_answer_text)
          # ここで絶対に学んでほしいこと
          elif text == "ここで絶対に学んでほしいこと":
            learn_text = df.at[index, BLOCK_3_COLUMN]
            append_sibling_paragraph_to_page(headers, page_id, block_id, "bulleted_list_item", learn_text)
          # 練習問題の解答
          elif text == "解答":
            practice_answer_text = df.at[index, BLOCK_6_COLUMN]
            append_paragraph_to_toggle(headers, block_id, practice_answer_text)
        elif block_type == "toggle" and b["heading3"]["rich_text"]:
          text = b["toggle"]["rich_text"][0]["plain_text"]
          # 参照のテキストを挿入
          if text == "この問題そのものに関して":
            reference_text = df.at[index, BLOCK_4_COLUMN]
            append_paragraph_to_toggle(headers, block_id, reference_text)
    
    # 例題がないケース
    else:
      for b in blocks:
        block_type = b["type"]  
        block_id   = b["id"]
        # heading_3 なら数学の場合には、 チェックの解答、ここで絶対に学んでほしいことの２択, Toggle heading_3 でも heading_3 と判定される
        if block_type == "heading_3" and b["heading_3"]["rich_text"]:
          text = b["heading_3"]["rich_text"][0]["plain_text"]
          # チェックの解答
          if text == "チェックの解答" and index == 1:
            check_answer_text = df.at[index, BLOCK_2_COLUMN]
            append_sibling_paragraph_to_page(headers, page_id, block_id, "numbered_list_item", check_answer_text)
          # ここで絶対に学んでほしいこと
          elif text == "ここで絶対に学んでほしいこと" and index == 1:
            learn_text = df.at[index, BLOCK_3_COLUMN]
            append_sibling_paragraph_to_page(headers, page_id, block_id, "bulleted_list_item", learn_text)
          # 練習問題の問題文
          elif text == "・問題文" and index == 1:
            practice_problem_text = df.at[index, BLOCK_5_COLUMN]
            append_sibling_paragraph_to_page(headers, page_id, block_id, "paragraph", practice_problem_text)
          # 練習問題の解答
          elif text == "解答" and index == 1:
            practice_answer_text = df.at[index, BLOCK_6_COLUMN]
            append_paragraph_to_toggle(headers, block_id, practice_answer_text)
        # タイプが toggle のもの
        elif block_type == "toggle" and b["toggle"]["rich_text"]:
          text = b["toggle"]["rich_text"][0]["plain_text"]
          # 参照のテキストを挿入
          if text == "この内容そのものに関して":
            reference_text = df.at[index, BLOCK_4_COLUMN]
            append_paragraph_to_toggle(headers, block_id, reference_text)
    exit()

if __name__ == "__main__":
  main()