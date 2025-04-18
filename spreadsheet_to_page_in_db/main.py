import requests
from dotenv import load_dotenv
import os
import pandas as pd
import numpy as np
from rich.progress import track
from io import StringIO
import chardet
from spreadsheet_to_page_in_db.pre_process import extract_uuid_from_notion_url, pre_process_csv
from spreadsheet_to_page_in_db.make_page import make_complete_block_for_template, delete_pages, make_page_property
from spreadsheet_to_page_in_db.variables import create_cover_and_icons, create_block_var_and_column_name, create_property_and_column, create_property_or_column_filter
from spreadsheet_to_page_in_db.notion_api import create_new_page_in_db, update_notion_status_to_error, update_notion_status_to_inprogress, update_notion_status_to_ready
import sys

def main():
  # 環境変数の設定
  load_dotenv("./config/.env")
  NOTION_API_KEY = os.getenv("NOTION_API_KEY")
  NOTION_VERSION = os.getenv("NOTION_VERSION")
  TEMPLATE_BOX_DATABASE_ID = os.getenv("NOTION_TEMPLATE_BOX_DATABASE_ID")
  # 認証情報の設定
  headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
  }
  
  # 引数の読み込み。
  args = sys.argv[1:]  # TEMPLATE_ID, CSVファイルpathのペアを取得
  if len(args) % 2 != 0:
    raise ValueError("❌ 引数の数が正しくありません")
  
  df_DICT = {}
  for i in range(0, len(args), 2):
    template_id = args[i]
    csv_path = args[i+1]
    df = pd.read_csv(csv_path)
    df_DICT[template_id] = df
  
  # delete flag（scrap and build か否か）TODO: 後でdeleteしないパターンについても考えてみる。
  # delete_flag = True
  
  # Template Box から実行予定のテンプレートのデータを取得
  # 実行予約の状態にあるテンプレートのみを実行する。
  filter_for_template_box = {
    "filter": {
      "property": "Status",
      "status": {
        "equals": "実行予約"
      }
    }
  }
  url = f"https://api.notion.com/v1/databases/{TEMPLATE_BOX_DATABASE_ID}/query"
  res = requests.post(url=url, headers=headers, json=filter_for_template_box)
  if res.status_code != 200:
    raise ValueError("Template Box から テンプレートのデータを取得する際にエラーが発生しました。")
  template_jsons = res.json()["results"]
  
  # 実行 Status を 実行予約 -> 実行待機中 にまとめて変更
  for template in template_jsons:
    template_page_id = template["id"]
    update_notion_status_to_ready(template_id=template_page_id, headers=headers, is_stopped = True)
  
  # 各テンプレートからのページ作成を実行
  for index, template_page_properties_json in enumerate(template_jsons):
    # テンプレページの id と name を取得する。
    template_page_id = template_page_properties_json["id"]
    template_page_name = template_page_properties_json["properties"]["Name"]["title"][0]["text"]["content"]
    if template_page_properties_json["properties"]["Last INDEX"]["number"]:
      template_page_index = template_page_properties_json["properties"]["Last INDEX"]["number"]
    else:
      template_page_index = 0
    # ステータスを実行中に変更
    update_notion_status_to_inprogress(template_id=template_page_id, headers=headers, is_stopped=True)
    # エラーが起きた時に template をスキップする用のフラグ
    is_continue = False
    
    # Page Property などの取得
    # 出力先のデータベースの ID の取得
    output_database_id = extract_uuid_from_notion_url(template_page_properties_json["properties"]["Database Mention"]["rich_text"][0]["href"])
    if not output_database_id:
      error_message("出力先のデータベースのIDの取得に失敗しました！（ {index+1} 番目のテンプレート）")
      update_notion_status_to_error(template_id=template_page_id, error_message=error_message, headers=headers)
      continue
    # icon や cover を取得（もともと Notion にある絵文字や cover じゃないと手動登録したものは使えないので注意）カスタムは drive などにおくしかない。
    if template_page_properties_json["cover"] and template_page_properties_json["cover"]["type"] == "external":
      cover_default = template_page_properties_json["cover"]
    else:
      cover_default = None
    if template_page_properties_json["icon"] and template_page_properties_json["icon"]["type"] == "emoji":
      icon_default = template_page_properties_json["icon"]
    elif template_page_properties_json["icon"] and template_page_properties_json["icon"]["type"] == "custom_emoji":
      icon_default = {"type": "custom_emoji", "custom_emoji": {"id": template_page_properties_json["icon"]["custom_emoji"]["id"]}}
    else:
      icon_default = None
    
    # csv file の読み込み
    # TODO: csv file を colab から読み取る処理を追加する
    # Notion に csv file が登録してある場合。
    if template_page_properties_json["properties"]["CSV File"]:
      url_for_csv_file = template_page_properties_json["properties"]["CSV File"]["files"][0]["file"]["url"]
      csv_response = requests.get(url_for_csv_file)
      if csv_response.status_code == 200:
        csv_data = csv_response.content
        encoding_detected = chardet.detect(csv_data)["encoding"]
        df = pd.read_csv(StringIO(csv_data.decode(encoding_detected)))
        df = df.fillna('')
      else:
        error_message = f"csv file ({index+1}番目) を取得する際にエラーが発生しました。"
        update_notion_status_to_error(template_id=template_page_id, error_message=error_message, headers=headers)
        continue
    # Notion に csv が登録されておらず、Colab からデータを取得する場合。
    else:
      template_id = template_page_properties_json["properties"]["Template ID"]["unique_id"]["number"]
      id_number = template_id[9:]
      if template_id in df_DICT:
        df = df_DICT[template_id]
      elif id_number in df_DICT:
        df = df_DICT[id_number]
      else:
        error_message = f"(Google Colaboratory に入力した TEMPLATE_ID が不適切です。（ {index+1} 番目のテンプレート）)"
        update_notion_status_to_error(template_id=template_page_id, error_message=error_message, headers=headers)
        continue
    
    # csv の前処理フラグ
    if template_page_properties_json["properties"]["前処理"]["select"]:
      pre_process = template_page_properties_json["properties"]["前処理"]["select"]["name"]
    else:
      pre_process = "なし"
    # template page の読み込み
    url = f"https://api.notion.com/v1/blocks/{template_page_id}/children"
    res = requests.get(url=url, headers=headers)
    if res.status_code != 200:
      error_message = f"Template page ({index+1}番目) の内容を取得する際にエラーが発生しました。"
      update_notion_status_to_error(template_id=template_page_id, error_message=error_message, headers=headers)
      continue
    template_blocks = res.json()["results"]
    if pre_process != "なし":
      for template_block in template_blocks:
        if template_block["type"] == "child_database" and template_block["child_database"]["title"] == "Preprocess Column":
          block_id = template_block["id"]
          df = pre_process_csv(database_id=block_id, headers=headers, df=df, pre_process_message=pre_process)
          if not df:
            error_message = "csv の前処理に失敗しました。"
            update_notion_status_to_error(template_id=template_page_id, error_message=error_message, headers=headers)
            is_continue = True
            break
    if is_continue:
      is_continue = False
      continue
    
    # 変数の準備（トップ位置のテンプレートの取得、テンプレートの始まりから立つフラグ）
    # Notion 内部にアップロードした cover は使えないので注意！
    USE_COL_BOX = []
    template_flag = False

    # 先に spreadsheet と output database の column | property の型を取得して保持しておく
    
    # spreadsheet の列の型
    df_type_dict = df.dtypes.to_dict()
    COLUMN_NAME_TYPE_BOX = {}
    for column_name, column_type in df_type_dict.items():
      if np.issubdtype(column_type, np.number):
        COLUMN_NAME_TYPE_BOX[column_name] = "number"
      else:
        COLUMN_NAME_TYPE_BOX[column_name] = "text"
    
    # output db の property の型
    url = f"https://api.notion.com/v1/databases/{output_database_id}"
    res = requests.get(url=url, headers=headers)
    if res.status_code != 200:
      error_message = "output database properties を取得する際にエラーが発生しました。"+ "Error message: "+res.text
      update_notion_status_to_error(template_id=template_page_id, error_message=error_message, headers=headers)
      continue
    properties = res.json()["properties"]
    PROPERTY_NAME_TYPE_BOX = {}
    PROPERTY_SELECT_BOX = {}
    for property_name, property_content in properties.items():
      PROPERTY_NAME_TYPE_BOX[property_name] = property_content["type"]
      if property_content["type"] == "multi_select":
        if property_content["multi_select"]:
          PROPERTY_SELECT_BOX[property_name] = [item["name"] for item in property_content["multi_select"]["options"]]
      if property_content["type"] == "select":
        if property_content["select"]:
          PROPERTY_SELECT_BOX[property_name] = [item["name"] for item in property_content["select"]["options"]]
      if property_content["type"] == "status":
        if property_content["status"]:
          PROPERTY_SELECT_BOX[property_name] = [item["name"] for item in property_content["status"]["options"]]
    
    for index, template_block in enumerate(template_blocks):
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
            cover_icon_db_id = template_block["id"]
            COVER_ICON_DICT, error_flag = create_cover_and_icons(database_id=cover_icon_db_id, headers=headers)
            if error_flag:
              error_message = "cover icon dictionary の作成に失敗しました。"
              update_notion_status_to_error(template_id=template_page_id, error_message=error_message, headers=headers)
              is_continue = True
              break
          
          # Block Var & Column Name （ここで annotation までつける）
          elif template_block["child_database"]["title"] == "Block Var & Column Name":
            block_var_db_id = template_block["id"]
            BLOCK_VAR_BOX, error_flag = create_block_var_and_column_name(database_id=block_var_db_id, headers=headers)
            if error_flag:
              error_message = "block var & column name dictionary の作成に失敗しました。"
              update_notion_status_to_error(template_id=template_page_id, error_message=error_message, headers=headers)
              is_continue = True
              break
          
          # DB Property & Column Name
          elif template_block["child_database"]["title"] == "DB Property & Column Name":
            property_and_column_db_id = template_block["id"]
            PROPERTY_AND_COLUMN_BOX, error_flag = create_property_and_column(template_database_id=property_and_column_db_id, headers=headers, PROPERTY_NAME_TYPE_BOX=PROPERTY_NAME_TYPE_BOX, COLUMN_NAME_TYPE_BOX=COLUMN_NAME_TYPE_BOX)
            if error_flag:
              error_message = "db property & column name dictionary の作成に失敗しました。"
              update_notion_status_to_error(template_id=template_page_id, error_message=error_message, headers=headers)
              is_continue = True
              break
          
          # Filters
          elif template_block["child_database"]["title"] == "Filters":
            filters_id = template_block["id"]
            print("COLUMN_NAME_TYPE_BOX", COLUMN_NAME_TYPE_BOX)
            result, notion_delete_page_dict, error_flag = create_property_or_column_filter(template_database_id=filters_id, output_database_id=output_database_id, headers=headers, df=df, PROPERTY_NAME_TYPE_BOX=PROPERTY_NAME_TYPE_BOX, COLUMN_NAME_TYPE_BOX=COLUMN_NAME_TYPE_BOX)
            if error_flag:
              error_message = "filteres dictionary の作成に失敗しました。"
              update_notion_status_to_error(template_id=template_page_id, error_message=error_message, headers=headers)
              is_continue = True
              break
            print("result:", result)
            FILTERS_BOX= result[0]; filter_column_name_list = result[1];
            
          # その他
          else:
            continue
      # Template のトップ Block の情報を取得
      else:
        TEMPLATE_BLOCKS = template_blocks[index:]
        break
    if is_continue:
      is_continue = False
      continue
    
    # USE_COL_BOX の作成
    # cover & icon について
    if COVER_ICON_DICT["cover"]:
      USE_COL_BOX.append(COVER_ICON_DICT["cover"])
    if COVER_ICON_DICT["icon"] and (COVER_ICON_DICT["cover"] != COVER_ICON_DICT["icon"]):
      USE_COL_BOX.append(COVER_ICON_DICT["icon"])
    # BLOCK VAR について
    for _, value in BLOCK_VAR_BOX.items():
      if value["column"] not in USE_COL_BOX:
        USE_COL_BOX.append(value["column"])
    # Property & Column について
    for element in PROPERTY_AND_COLUMN_BOX:
      if element["column_name"] not in USE_COL_BOX:
        USE_COL_BOX.append(element["column_name"])
    # Filteres について
    for column_name in filter_column_name_list:
      if column_name not in USE_COL_BOX:
        USE_COL_BOX.append(column_name)
    
    # フィルターをかけて csv から data を取得（あらかじめ csv は Markdown 形式に処理されていること、orderがつけられていることを仮定する。）
    # まず必要な列だけ抜き出す。
    df = df[USE_COL_BOX]
    # 次に、order についてフィルターをかける ( common: spreadsheet を基準に spreadsheet と notion db の共通部分をとる。（spreadsheetの追加分までは削除しない) ）
    df_filter = FILTERS_BOX["common"]
    df = df.query("order in @df_filter")
    df = df.query("order > @template_page_index ")
    
    # Page の作成
    # まず、古いページを Filter に応じて削除する
    FILTERS_BOX["notion"], failed_orders_list = delete_pages(output_database_id=output_database_id, headers=headers, filtered_order=FILTERS_BOX["common"], index = template_page_index)
    # 各ページの作成
    # TODO: ページの作成に失敗した場合には削除したページを復活させたのち、そこにエラーを記録して次のページの処理に移るように修正する。
    for row in track(zip(*[df[col] for col in df.columns]), description=f"Creating Pages Now for Template (Name: {template_page_name})", total=len(df)):
      # 各列の spreadsheet のデータ
      df_row = dict(zip(df.columns, row))
      # 各ページの id 
      page_id = None
      order = df_row["order"]
      if order in notion_delete_page_dict:
        page_id = notion_delete_page_dict[order]
      if order in failed_orders_list:
        continue
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
      properties["Status"] = make_page_property(property_name="Status", property_type="status", property_content="プログラム編集済", PROPERTY_SELECT_BOX=PROPERTY_SELECT_BOX)
      for property_element in PROPERTY_AND_COLUMN_BOX:
        property_name = property_element["property_name"]
        property_type = property_element["property_type"]
        property_content = df_row[property_element["column_name"]]
        try:
          parsed_property = make_page_property(property_name=property_name, property_type=property_type, property_content=property_content, PROPERTY_SELECT_BOX=PROPERTY_SELECT_BOX)
        except Exception as e:
          error_message = f"property 作成時にエラーが発生しました。{e}"
          if page_id:
            update_notion_status_to_error(template_id=page_id, error_message=error_message, headers=headers)
          else:
            print(f"Error!: error_message")
          is_continue = True
          break
        properties[property_name] = parsed_property
      if is_continue:
        is_continue = False
        continue
      # page contents の作成
      children = []
      for template_block in TEMPLATE_BLOCKS:
        # block をテンプレートから完成させる。
        try:
          complete_block, is_blocks = make_complete_block_for_template(headers, template_block, df_row, BLOCK_VAR_BOX)
        except Exception as e:
          error_message = f"ページの ブロック作成時にエラーが発生しました。"
          if page_id:
            update_notion_status_to_error(template_id=template_page_id, error_message=error_message, headers=headers)
          else:
            print(f"Error!: error_message")
          is_continue = True
          break
        if not is_blocks:
          children.append(complete_block)
        else:
          children.extend(complete_block)
      if is_continue:
        is_continue = False
        continue
      # 作成したページの追加
      INDEX = create_new_page_in_db(headers=headers, database_id=output_database_id, cover=cover, icon=icon, properties=properties, children=children, order=order, delete_order_index=FILTERS_BOX["notion"])
      # Last INDEX を更新
      url = f"https://api.notion.com/v1/pages/{template_page_id}"
      data = {
        "properties":
          {
            "Last INDEX": {
              "number": INDEX
            }
          }
      }
      res = requests.patch(url=url, headers=headers, json=data)
      if res.status_code != 200:
        error_message = f"Last INDEX を更新する際にエラーが発生しました。(INDEX: {INDEX}) "
        update_notion_status_to_error(template_id=template_page_id, error_message=error_message, headers=headers)
        continue
    
    # 実行 Status を 実行中 -> 完了へ変更
    url = f"https://api.notion.com/v1/pages/{template_page_id}"
    data = {
      "properties":
        {
          "Status": {
            "status": {
              "name": "完了"
            }
          }
        }
    }
    res = requests.patch(url=url, headers=headers, json=data)
    if res.status_code != 200:
      error_message = f"実行中から完了に変更する際にエラーが発生しました。({index+1}番目) "
      update_notion_status_to_error(template_id=template_page_id, error_message=error_message, headers=headers)
      continue

if __name__ == "__main__":
  main()
  print("✅テンプレートの作成が完了しました！")