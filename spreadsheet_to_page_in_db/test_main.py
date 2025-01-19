import requests
from dotenv import load_dotenv
import os
import json
import pandas as pd
import re
from copy import deepcopy
from rich.progress import track
from io import StringIO
import chardet
from notion_pre_process import extract_uuid_from_notion_url
from make_page import make_complete_block_for_template, delete_pages, make_page_property
from spreadsheet_to_page_in_db.spreadsheet_filter import filter_dataframe
from variables import create_cover_and_icons, create_block_var_and_column_name, create_property_and_column, create_property_or_column_filter


def main():
  load_dotenv("config/.env")

  NOTION_API_KEY = os.getenv("NOTION_API_KEY")
  NOTION_VERSION = os.getenv("NOTION_VERSION")
  NOTION_TEMPLATE_BOX_DATABASE_ID = os.getenv("NOTION_TEMPLATE_BOX_DATABASE_ID")
  BLOCK_1_COLUMN = os.getenv("BLOCK_1_COLUMN")
  BLOCK_2_COLUMN = os.getenv("BLOCK_2_COLUMN")
  BLOCK_3_COLUMN = os.getenv("BLOCK_3_COLUMN")
  BLOCK_4_COLUMN = os.getenv("BLOCK_4_COLUMN")
  BLOCK_5_COLUMN = os.getenv("BLOCK_5_COLUMN")
  BLOCK_6_COLUMN = os.getenv("BLOCK_6_COLUMN")
  BLOCK_7_COLUMN = os.getenv("BLOCK_7_COLUMN")
  BLOCK_8_COLUMN = os.getenv("BLOCK_8_COLUMN")
  CSV_FILE_NAME = os.getenv("CSV_FILE_NAME")
  database_id = os.getenv("NOTION_DATABASE_ID")
  test_database_id = os.getenv("NOTION_TEST_DATABASE_ID")
  test_page_id = os.getenv("NOTION_TEST_PAGE_ID")
  test_block_id = "17fb95a4c61980aa8971fdd345e963ab"
  # test_database_id = "17fb95a4-c619-806b-a06f-df6e3a90c649"
  
  # TODO: template id を保持しておく。 TEMPLATE_IDS = []
  # TODO: ID を使って filter をかけて query を post する。https://developers.notion.com/reference/post-database-query-filter#id
  # TODO: CSV を複数読み込むと同時にTEMPLATE_ID と set にしておく
  
  # df = pd.read_csv(f"const/csv/math/{CSV_FILE_NAME}", header=0, usecols=[BLOCK_1_COLUMN, BLOCK_2_COLUMN, BLOCK_3_COLUMN, BLOCK_4_COLUMN, BLOCK_5_COLUMN, BLOCK_6_COLUMN, BLOCK_7_COLUMN, BLOCK_8_COLUMN])
  # df = df.fillna('')
  # url_for_page_ids = f"https://api.notion.com/v1/databases/{database_id}/query"
  url_for_template_box = f"https://api.notion.com/v1/databases/{database_id}"
  url_for_specific_template_pages = f"https://api.notion.com/v1/databases/{database_id}/query"
  url_for_test_db_properties = f"https://api.notion.com/v1/databases/{test_database_id}"
  url_for_test_db = f"https://api.notion.com/v1/databases/{test_database_id}/query"
  url_for_test_retrieve_a_page = f"https://api.notion.com/v1/pages/{test_page_id}"
  url_for_test_retrive_block_children = f"https://api.notion.com/v1/blocks/{test_page_id}/children"
  url_for_test_block = f"https://api.notion.com/v1/blocks/{test_block_id}"
  url_for_test_block_children = f"https://api.notion.com/v1/blocks/{test_block_id}/children"
  headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
  }
  # filter for template Box
  filter_for_template_box = {
    "filter": {
      "property": "order",
      "number": {
        "equals": 3
      }
    }
  }
  # filter_for_template_box = {
  #   "sorts": [
  #     {
  #       "property": "Block number",
  #       "direction": "ascending"
  #     }
  #   ]
  # }
  # filter_for_template_box = {}
  # ↑
  # |
  # |
  # |
  # ----------------------------------------------------------------------------------------------
  
  
  res = requests.post(url=url_for_test_db, headers=headers, json=filter_for_template_box)
  test_db = res.json()
  res = requests.get(url=url_for_test_db_properties, headers=headers)
  test_db_properties = res.json()
  res = requests.get(url=url_for_test_retrieve_a_page,headers=headers)
  test_page = res.json()
  res = requests.get(url=url_for_test_retrive_block_children, headers=headers)
  test_page_children = res.json()
  url_for_database_mention = test_page["properties"]["Database Mention"]["rich_text"][0]["href"]
  database_id = extract_uuid_from_notion_url(url=url_for_database_mention)
  res = requests.get(url=url_for_test_block, headers=headers)
  test_block = res.json()
  res = requests.get(url=url_for_test_block_children, headers=headers)
  test_block_children = res.json()
  
  # csv file の取得（Notion API から）
  # url_for_csv = test_page["properties"]["csv file"]["files"][0]["file"]["url"]
  # csv_response = requests.get(url_for_csv)
  # if csv_response.status_code == 200:
  #   print(f"csv_response:{csv_response}")
  #   csv_data = csv_response.content
  #   encoding_detected = chardet.detect(csv_data)["encoding"]
  #   print(f"Detected encoding: {encoding_detected}")
  #   df = pd.read_csv(StringIO(csv_data.decode(encoding_detected)))
  #   print(df.head())
  # else:
  #   print(f"Failed to download file: {csv_response.status_code}")
  print(f"test_db:{test_db}")
  print(f"test_page:{test_page}")
  print(f"test_page_children:{test_page_children}")
  print(f"test_block:{test_block}")
  print(f"test_block_children:{test_block_children}")
  print(f"test_db_properties:{test_db_properties}")
  # TODO: property_dict = { property_name, property_id, column_name } data から property_name, property_id, column_name を set にして 保存しておく。
  # TODO: block_dict = { block_name, block_id, column_name, annotation_type (list) } これも同じ、ブロック変数を保存しておく。
  
  # TODO: 
  exit()
  
if __name__ == "__main__":
  main()