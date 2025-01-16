import requests
from dotenv import load_dotenv
import os
import json
import pandas as pd
import re
from copy import deepcopy
from main import make_page_template, append_contents

# {"object":"error","status":400,"code":"validation_error","message":"body failed validation: body.children[26].toggle.children[0].paragraph.rich_text.length should
# be ≤ `100`, instead was `119`.","request_id":"b53814ac-d70a-4de9-9697-172c25383001"}に対処するためのテスト

def rich_text_test():
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
  BLOCK_7_COLUMN = os.getenv("BLOCK_7_COLUMN")
  BLOCK_8_COLUMN = os.getenv("BLOCK_8_COLUMN")
  CSV_FILE_NAME = os.getenv("CSV_FILE_NAME")
  page_id = os.getenv("TEST_PAGE_ID")
  
  df = pd.read_csv(f"const/csv/math/{CSV_FILE_NAME}", header=0, usecols=[BLOCK_1_COLUMN, BLOCK_2_COLUMN, BLOCK_3_COLUMN, BLOCK_4_COLUMN, BLOCK_5_COLUMN, BLOCK_6_COLUMN, BLOCK_7_COLUMN])
  df = df.fillna('')

  headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
  }
  # ページの中身の作成
  index = 0
  problems=df.at[index, BLOCK_1_COLUMN]; check_answer=df.at[index, BLOCK_2_COLUMN]; important_points=df.at[index, BLOCK_3_COLUMN];
  reference=df.at[index, BLOCK_4_COLUMN]; practice_problem=df.at[index, BLOCK_5_COLUMN]; practice_answer=df.at[index, BLOCK_6_COLUMN];
  # area=df.at[index, BLOCK_8_COLUMN]; 
  if(problems):
    problem_numbers=df.at[index, BLOCK_7_COLUMN]
    reference += f" チャート式基礎からの　例題{problem_numbers}"
  blocks = make_page_template(problems=problems, check_answer=check_answer, important_points=important_points, reference=reference, practice_problem=practice_problem, practice_answer=practice_answer)
  # ページの追加
  print(f"blocks[26]:{blocks[26]}")
  append_contents(headers=headers, page_id=page_id, blocks=blocks)

if __name__ == '__main__':
  rich_text_test()