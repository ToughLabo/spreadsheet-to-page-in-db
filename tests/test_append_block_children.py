import requests
import os
from dotenv import load_dotenv
import sys
from pathlib import Path
import json

# 環境変数の設定
def test_append_block_children():
  load_dotenv("./config/.env")
  NOTION_API_KEY = os.getenv("NOTION_API_KEY")
  NOTION_VERSION = os.getenv("NOTION_VERSION")
  TEMPLATE_BOX_DATABASE_ID = os.getenv("NOTION_TEMPLATE_BOX_DATABASE_ID")
  TEST_DATABASE_ID = os.getenv("NOTION_TEST_TARGET_DATABASE_ID")
  TEST_PAGE_ID = os.getenv("NOTION_TEST_TARGET_PAGE_ID")
  TEST_BLOCK_ID = os.getenv("NOTION_TEST_TARGET_BLOCK_ID")
  INDEX = 0
  
  # 認証情報の設定
  headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
  }
  
  url = f"https://api.notion.com/v1/blocks/{TEST_PAGE_ID}/children"
  
  children = [
    {
      "object": "block",
      "type": "heading_2",
      "heading_2": {
        "rich_text": [],
        "color": "default",
        "is_toggleable": True,
        "children": []
      }
    }
  ]

  payload = {
    "children": children
  }
  res = requests.patch(url=url, headers=headers, json=payload)
  if res.status_code != 200:
    res.raise_for_status()

def test_change_db_property_type():
  load_dotenv("./config/.env")
  NOTION_API_KEY = os.getenv("NOTION_API_KEY")
  NOTION_VERSION = os.getenv("NOTION_VERSION")
  # 認証情報の設定
  headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
  }
  database_id = "17fb95a4c6198011b3bfc8961c330f2b"
  url = f"https://api.notion.com/v1/databases/{database_id}"
  payload = {
    "properties": {
      "テスト": {
        'id': '%3ATtw',
        "type": "rich_text",
        "rich_text":[]
        # "select": {
        #   "options":[]
        # }
      }
    }
  }
  res = requests.get(url=url, headers=headers)
  print(res.json())
  res = requests.patch(url=url, headers=headers, json=payload)
  if res.status_code != 200:
    res.raise_for_status()

if __name__ == "__main__":
  test_change_db_property_type()