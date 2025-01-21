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
  
  # children =  [
  #   {
  #     "type": "paragraph",
  #     "paragraph": {
  #       "rich_text": [
  #         {
  #           "type": "text",
  #           "text": {
  #             "content": "例題 ",
  #             "link": None
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": "例題 ",
  #           "href": None
  #         },
  #         {
  #           "type": "equation",
  #           "equation": {
  #             "expression": "6"
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": "6",
  #           "href": None
  #         },
  #         {
  #           "type": "text",
  #           "text": {
  #             "content": "：",
  #             "link": None
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": "：",
  #           "href": None
  #         },
  #         {
  #           "type": "equation",
  #           "equation": {
  #             "expression": "n"
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": "n",
  #           "href": None
  #         },
  #         {
  #           "type": "text",
  #           "text": {
  #             "content": " 桁の数の決定と二項定理",
  #             "link": None
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": " 桁の数の決定と二項定理",
  #           "href": None
  #         }
  #       ]
  #     },
  #     "color": "default"
  #   },
  #   {
  #     "type": "paragraph",
  #     "paragraph": {
  #       "rich_text": [
  #         {
  #           "type": "equation",
  #           "equation": {
  #             "expression": "(1)"
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": "(1)",
  #           "href": None
  #         },
  #         {
  #           "type": "text",
  #           "text": {
  #             "content": " 次の数の下位 ",
  #             "link": None
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": " 次の数の下位 ",
  #           "href": None
  #         },
  #         {
  #           "type": "equation",
  #           "equation": {
  #             "expression": "5"
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": "5",
  #           "href": None
  #         },
  #         {
  #           "type": "text",
  #           "text": {
  #             "content": " 桁を求めよ。",
  #             "link": None
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": " 桁を求めよ。",
  #           "href": None
  #         }
  #       ]
  #     },
  #     "color": "default"
  #   },
  #   {
  #     "type": "paragraph",
  #     "paragraph": {
  #       "rich_text": [
  #         {
  #           "type": "equation",
  #           "equation": {
  #             "expression": "(ア)"
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": "(ア)",
  #           "href": None
  #         },
  #         {
  #           "type": "text",
  #           "text": {
  #             "content": " ",
  #             "link": None
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": " ",
  #           "href": None
  #         },
  #         {
  #           "type": "equation",
  #           "equation": {
  #             "expression": "101^{100}"
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": "101^{100}",
  #           "href": None
  #         },
  #         {
  #           "type": "equation",
  #           "equation": {
  #             "expression": "(イ)"
  #           },
  #           # "annotations": {
  #           #   "bold": False,
  #           #   "italic": False,
  #           #   "underline": False,
  #           #   "strikethrough": False,
  #           #   "code": False,
  #           #   "color": "default"
  #           # },
  #           "plain_text": "(イ)",
  #           "href": None
  #         },
  #         {
  #           "type": "text",
  #           "text": {
  #             "content": " ",
  #             "link": None
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": " ",
  #           "href": None
  #         },
  #         {
  #           "type": "equation",
  #           "equation": {
  #             "expression": "99^{100}"
  #           },
  #           # "annotations": {
  #           #   "bold": False,
  #           #   "italic": False,
  #           #   "underline": False,
  #           #   "strikethrough": False,
  #           #   "code": False,
  #           #   "color": "default"
  #           # },
  #           "plain_text": "99^{100}",
  #           "href": None
  #         }
  #       ]
  #     },
  #     "color": "default"
  #   },
  #   {
  #     "type": "paragraph",
  #     "paragraph": {
  #       "rich_text": [
  #         {
  #           "type": "equation",
  #           "equation": {
  #             "expression": "(2)"
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": "(2)",
  #           "href": None
  #         },
  #         {
  #           "type": "text",
  #           "text": {
  #             "content": " ",
  #             "link": None
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": " ",
  #           "href": None
  #         },
  #         {
  #           "type": "equation",
  #           "equation": {
  #             "expression": "29^{51}"
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": "29^{51}",
  #           "href": None
  #         },
  #         {
  #           "type": "text",
  #           "text": {
  #             "content": " を ",
  #             "link": None
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": " を ",
  #           "href": None
  #         },
  #         {
  #           "type": "equation",
  #           "equation": {
  #             "expression": "900"
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": "900",
  #           "href": None
  #         },
  #         {
  #           "type": "text",
  #           "text": {
  #             "content": " で割ったときの余りを求めよ。",
  #             "link": None
  #           },
  #           "annotations": {
  #             "bold": False,
  #             "italic": False,
  #             "underline": False,
  #             "strikethrough": False,
  #             "code": False,
  #             "color": "default"
  #           },
  #           "plain_text": " で割ったときの余りを求めよ。",
  #           "href": None
  #         }
  #       ]
  #     },
  #     "color": "default"
  #   }
  # ]
  
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


  # children = [
	# 	{
	# 		"object": "block",
	# 		"type": "heading_2",
	# 		"heading_2": {
	# 			"rich_text": [{ "type": "text", "text": { "content": "Lacinato kale" } }]
	# 		}
	# 	}
  # ]
  
  payload = {
    "children": children
  }
  res = requests.patch(url=url, headers=headers, json=payload)
  if res.status_code != 200:
    res.raise_for_status()
    
if __name__ == "__main__":
  test_append_block_children()