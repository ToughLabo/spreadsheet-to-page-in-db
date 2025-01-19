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
from python_filter import filter_dataframe

# DB に新しいページを作成する
def create_new_page_in_db(headers, database_id, icon, cover, properties, children, index=None):
  url = "https://api.notion.com/v1/pages"
  parent = {"database_id": database_id}
  payload = {
    "parent": parent,
    "icon": icon,
    "cover": cover,
    "properties": properties,
    "children": children
  }
  res = requests.post(url=url, headers=headers, json=payload)
  if res.status_code != 200:
    if index:
      print(f"ページを作成する際にエラーが発生しました。index = {index}")
    else:
      print(f"ページを作成する際にエラーが発生しました。")
    res.raise_for_status()
  return res.json()

# 既存のページに追加する
def append_contents(headers, page_id, blocks):
  url = f"https://api.notion.com/v1/blocks/{page_id}/children"
  payload = {
    "children": blocks
  }
  res = requests.patch(url, headers=headers, data=json.dumps(payload))
  if res.status_code != 200:
    print(f"Error: {res.status_code}")
    print(res.text)
    payload_for_status = {
      "properties":{
        "Status": "エラー"
      }
    }
    requests.patch(f"https://api.notion.com/v1/pages/{page_id}", headers=headers, data=json.dumps(payload_for_status))
  else:
    payload_for_status = {
      "properties":{
        "Status": "プログラム編集済"
      }
    }
    requests.patch(f"https://api.notion.com/v1/pages/{page_id}", headers=headers, data=json.dumps(payload_for_status))
  return res.json()

def fetch_all_pages(headers, url, payload):
  all_pages = []
  payload["page_size"] = 100
  
  while True:
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code != 200:
      print(f"status_code:{response.status_code}")
      print(f"error message:{response.text}")
      exit()
    response_data = response.json()
    all_pages.extend(response_data.get("results", []))
    
    if not response_data.get("has_more"):
      break
    
    # Update payload with next_cursor
    payload["start_cursor"] = response_data["next_cursor"]
  
  return all_pages


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
  test_block_id = "d5803e6c-c811-4ec0-983f-46cfeac6b6a4"
  
  # TODO: template id を保持しておく。 TEMPLATE_IDS = []
  # TODO: ID を使って filter をかけて query を post する。https://developers.notion.com/reference/post-database-query-filter#id
  # TODO: CSV を複数読み込むと同時にTEMPLATE_ID と set にしておく
  
  # df = pd.read_csv(f"const/csv/math/{CSV_FILE_NAME}", header=0, usecols=[BLOCK_1_COLUMN, BLOCK_2_COLUMN, BLOCK_3_COLUMN, BLOCK_4_COLUMN, BLOCK_5_COLUMN, BLOCK_6_COLUMN, BLOCK_7_COLUMN, BLOCK_8_COLUMN])
  # df = df.fillna('')
  # url_for_page_ids = f"https://api.notion.com/v1/databases/{database_id}/query"
  url_for_template_box = f"https://api.notion.com/v1/databases/{database_id}"
  url_for_specific_template_pages = f"https://api.notion.com/v1/databases/{database_id}/query"
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
      "property": "Status",
      "status": {
        "equals": "実行予約"
      }
    }
  }
  # ↑
  # |
  # |
  # |
  # ----------------------------------------------------------------------------------------------
  
  
  res = requests.post(url=url_for_test_db, headers=headers, json=filter_for_template_box)
  test_db = res.json()
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
  # TODO: property_dict = { property_name, property_id, column_name } data から property_name, property_id, column_name を set にして 保存しておく。
  # TODO: block_dict = { block_name, block_id, column_name, annotation_type (list) } これも同じ、ブロック変数を保存しておく。
  
  # TODO: 
  exit()
  # -------------------------------------------------------------------------------------------------------------------
  # |
  # |
  # |
  # |
  # ↓
  # delete flag（scrap and build か否か）TODO: 後でdeleteしないパターンについても考えてみる。
  delete_flag = True
  # Template Box から テンプレートのデータを取得
  res_template_box = requests.post(url=url_for_template_box, headers=headers, json=filter_for_template_box)
  template_data = res_template_box.json()
  if template_data.status_code != 200:
    print("Template Box から テンプレートのデータを取得する際にエラーが発生しました。")
    print(rf"status_code:{template_data.status_code}\n error message: {res_template_box.message}")
  
  template_jsons = template_data["result"]
  # 実行 Status をまとめて変更
  for template in template_jsons:
    template_id = template["id"]
    url_for_template_property = f"https://api.notion.com/v1/pages/{template_id}"
    data = {
      "properties":[
        {
          "Status": "実行待機中"
        }
      ]
    }
    res = requests.patch(url=url_for_template_property, headers=headers, data=data)
    if res.status_code != 200:
      print("Template Box から テンプレートのデータを取得する際にエラーが発生しました。")
      res.raise_for_status()
  
  # 各テンプレートからのページ作成を実行
  for index, template_page_properties_json in enumerate(template_jsons):
    
    # 実行 Status の変更
    template_id = template_page_properties_json["id"]
    url_for_template_property = f"https://api.notion.com/v1/pages/{template_id}"
    data = {
      "properties":[
        {
          "Status": "実行中"
        }
      ]
    }
    res = requests.patch(url=url_for_template_property, headers=headers, data=data)
    if res.status_code != 200:
      print("実行待機中から実行中に変更する際にエラーが発生しました。({index+1}番目) ")
      res.raise_for_status()
    
    # Page Property などの取得
    # 出力先のデータベースの ID の取得
    output_database_id = template_page_properties_json["properties"]["Database Mention"]["rich_text"][0]["href"]
    # icon や cover を取得（もともと Notion にある絵文字や cover じゃないと手動登録したものは使えないので注意）カスタムは drive などにおくしかない。
    if template_page_properties_json["cover"] and template_page_properties_json["cover"]["type"] == external:
      cover_default = template_page_properties_json["cover"]
    else:
      cover_default = None
    if template_page_properties_json["icon"] and template_page_properties_json["icon"]["type"] == "emoji":
      icon_default = template_page_properties_json["icon"]
    elif template_page_properties_json["icon"] and template_page_properties_json["icon"]["type"] == "custom_emoji":
      icon_default = {"type": "custom_emoji", "custom_emoji": {"id": template_page_properties_json["icon"]["custom_emoji"]}}
    else:
      icon_default = None
    
    # csv file の読み込み
    # TODO: csv file を colab から読み取る処理を追加する
    # TODO: csv file に関して順番付けする。コードを書く（スタート位置を指定できるようにする。）
    
    url_for_csv = template_page_properties_json["properties"]["csv file"]["files"][0]["file"]["url"]
    csv_response = requests.get(url_for_csv)
    if csv_response.status_code == 200:
      csv_data = csv_response.content
      encoding_detected = chardet.detect(csv_data)["encoding"]
      df = pd.read_csv(StringIO(csv_data.decode(encoding_detected)))
    else:
      print("csv file ({index+1}番目) を取得する際にエラーが発生しました。")
      res.raise_for_status()
    
    # Notion と Spreadsheet を結びつける変数及び、トップ位置のテンプレートの取得
    # 変数の準備（cover & icon 列、ブロック変数・列名、DB変数・列名、作成するページのフィルター（TODO:ひとまず Spreadsheet の列名のフィルターを想定）、使う列をまとめて取得、テンプレートの始まりから立つフラグ）
    # Notion 内部にアップロードしたファイルは使えないので注意！
    COVER_ICON_DICT = {"cover": "", "icon":""}
    BLOCK_VAR_BOX = []
    DB_PROPERTY_BOX = []
    FILTERS_BOX = []
    USE_COL_BOX = []
    TEMPLATE_BLOCKS = []
    template_flag = False
    # template page の読み込み
    url_for_template_page_children = f"https://api.notion.com/v1/blocks/{template_id}/children"
    res = requests.get(url=url_for_template_page_children, headers=headers)
    if res.status_code != 200:
      print(f"Template page ({index+1}番目) の内容を取得する際にエラーが発生しました。")
      res.raise_for_status()
    template_blocks = res.json()["results"]
    for template_block in template_blocks:
      # 環境変数の取得
      if not template_flag:
        # テンプレートの開始点を取得
        if template_block["type"] == "callout" and template_block["callout"]["icon"]["type"] == "emoji" and template_block["callout"]["icon"]["emoji"] == '📋':
          template_flag = True
          continue
        # 環境変数のデータベースを検知
        elif template_block["type"] == "child_database":
          # cover & icon 
          if template_block["child_database"]["title"] == "cover & icon":
            pass
          
          # Block Var & Column Name （ここで型までつける）
          elif template_block["child_database"]["title"] == "Block Var & Column Name":
            pass
          
          # DB Property & Column Name
          elif template_block["child_database"]["title"] == "DB Property & Column Name":
            pass
          
          # Filters
          elif template_block["child_database"]["title"] == "Filters":
            pass
          
          # その他
          else:
            continue
      # Template のトップ Block の情報を取得
      else:
        block_id = block["id"]
        has_children = block["has_children"]
        block_type = block["type"]
        # rich_text があるブロック
        if block_type not in ["bookmark", "child_page", "image", "divider", "column_list", "table", "equation"]:
          rich_text = block[type]["rich_text"]
        # rich_text がないブロック
        else:
          rich_text = []
        # BLOCKを順番通りに元に戻す。
        TEMPLATE_BLOCKS.append({
          "id": block_id,
          "has_children": has_children,
          "type": block_type,
          "rich_text": rich_text
        })
    
    # フィルターをかけて csv から data を取得
    # まず必要な列だけ抜き出す。
    df = df[USE_COL_BOX]
    # 次に、フィルターをかける
    if len(FILTERS_BOX):
      df = filter_dataframe(df, FILTERS_BOX)
    
    # Page の作成
    # まず、古いページを Filter に応じて削除する
    parsed_notion_filter = delete_pages(output_database_id=output_database_id, headers=headers,FILTERS_BOX=FILTERS_BOX)
    # DB Property と Spreadsheet Column との対応関係を作る。
    url_for_output_database = f"https://api.notion.com/v1/blocks/{output_database_id}"
    # 各ページの作成
    for row in track(zip(*[df[col] for col in df.columns]), description="Creating Pages..."):
      df_row = dict(zip(df.columns, row))
      children = []
      for template_block in TEMPLATE_BLOCKS:
        # block をテンプレートから完成させる。
        complete_block = make_complete_block_for_template(template_block, df_row, BLOCK_VAR_BOX)
        children.append(complete_block)
      # cover の処理
      if COVER_ICON_DICT["cover"]:
        cover = {"type": "external", "external": {"url": df_row[COVER_ICON_DICT["cover"]]}}
      else:
        cover = cover_default
      # icon の処理
      if COVER_ICON_DICT["icon"]:
        if len(COVER_ICON_DICT["icon"]) > 1:
          icon = {"type": "custom_emoji", "custom_emoji": {"id": COVER_ICON_DICT["icon"]}}
        else:
          icon = {"type": "emoji", "emoji": COVER_ICON_DICT["icon"] }
      else:
        icon = icon_default
      # page properties の処理
      properties = {}
      for property_element in DB_PROPERTY_BOX:
        property_name = property_element["property_name"]
        property_type = property_element["property_type"]
        property_content = property_element["property_content"]
        parsed_property = make_page_property(property_name, property_type, property_content)
        properties[property_name] = parsed_property
      
      res = create_new_page_in_db(headers=headers, database_id=output_database_id, cover=cover, icon=icon, properties=properties, children=children)
      
  # ↑
  # |
  # |
  # |
  # |
  # ---------------------------------------------------------------------------------------------------------------------------
  
  

  # order property でソート順を指定
  payload = {
    "sorts": [
      {
        "property": "order",
        "direction": "ascending"
      }
    ]
  }

  pages = fetch_all_pages(url=url_for_page_ids, headers=headers, payload=payload)

  # csv の順番 と page_id の順番が一致していることを仮定する。
  for index, page in track(enumerate(pages),description="creating pages"):
    page_id = page["id"]
    url_for_block_ids = f"https://api.notion.com/v1/blocks/{page_id}/children"
    res = requests.get(url_for_block_ids, headers=headers)
    if res.status_code != 200:
      print(f"Error: {res.status_code}")
      print(res.text)
      exit()
    data = res.json()
    blocks =data["results"]
    # 既存のページを綺麗にお掃除
    for block in blocks:
      block_id_for_delete = block["id"]
      url_for_delete_blocks = f"https://api.notion.com/v1/blocks/{block_id_for_delete}"
      res = requests.delete(url_for_delete_blocks, headers=headers)
      if res.status_code != 200:
        print(f"Error: {res.status_code}")
        print(res.text)
        exit()
    # ページの中身の作成
    problems=df.at[index, BLOCK_1_COLUMN]; check_answer=df.at[index, BLOCK_2_COLUMN]; important_points=df.at[index, BLOCK_3_COLUMN];
    reference=df.at[index, BLOCK_4_COLUMN]; practice_problem=df.at[index, BLOCK_5_COLUMN]; practice_answer=df.at[index, BLOCK_6_COLUMN];
    area=df.at[index, BLOCK_8_COLUMN]; 
    if(problems):
      problem_numbers=df.at[index, BLOCK_7_COLUMN]
      reference += f" チャート式基礎からの{area}　例題{problem_numbers}"
    blocks = make_page_template(problems=problems, check_answer=check_answer, important_points=important_points, reference=reference, practice_problem=practice_problem, practice_answer=practice_answer)
    # ページの追加
    append_contents(headers=headers, page_id=page_id, blocks=blocks)

if __name__ == "__main__":
  main()