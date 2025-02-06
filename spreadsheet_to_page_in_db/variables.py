import requests
from spreadsheet_to_page_in_db.notion_filter import create_notion_filter
from spreadsheet_to_page_in_db.spreadsheet_filter import create_spreadsheet_filter

# cover & icon から環境変数を作成 ( cover or icon が key, column name が value)
def create_cover_and_icons(database_id, headers):
  error_flag = False  # エラー発生フラグ
  cover_and_icon_dict = {}

  try:
    # まずは database から内容を取得
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload = {}
    res = requests.post(url=url, headers=headers, json=payload)
    
    if res.status_code != 200:
      print("cover & icon データベースから環境変数を取得する際にエラーが発生しました。")
      res.raise_for_status()
    
    variable_pairs = res.json().get("results", [])

    # 環境変数についての辞書を作成
    for i in range(2):  # 2つのデータを処理
      try:
        select_name = variable_pairs[i]["properties"]["Select"]["select"]["name"]
        title_data = variable_pairs[i]["properties"]["Column name"]["title"]
        
        if title_data:
          cover_and_icon_dict[select_name] = title_data[0]["text"]["content"]
        else:
          cover_and_icon_dict[select_name] = None
      except KeyError as e:
        print(f"カラム '{i+1}' のデータ取得中にエラー発生: {e}")
        error_flag = True  # エラー発生

  except requests.RequestException as e:
    print(f"Notion API へのリクエスト中にエラー発生: {e}")
    return None, True  # APIエラー時

  except Exception as e:
    print(f"create_cover_and_icons 関数内で予期せぬエラーが発生: {e}")
    return None, True  # その他のエラー時

  return cover_and_icon_dict, error_flag


# Block Var & Column Name から環境変数を作成 ( 変数の数を key, value は 辞書、その辞書の中には column, bold, italic, underline strikethrough が入っている)
def create_block_var_and_column_name(database_id, headers):
  error_flag = False  # エラー発生フラグ
  result_dict = {}

  try:
    # まずは database から内容を取得
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload = {
      "sorts": [
        {
          "property": "Block number",
          "direction": "ascending"
        }
      ]
    }
    res = requests.post(url=url, headers=headers, json=payload)

    try:
      res.raise_for_status()  # HTTPエラーをキャッチ
    except requests.exceptions.HTTPError as e:
      print(f"Notion API からのレスポンスエラー: {e}")
      return None, True  # HTTPエラーが発生した場合は None, True を返す

    # データ取得
    variable_combs = res.json().get("results", [])

    # 環境変数についての辞書を作成
    for variable_comb in variable_combs:
      try:
        block_var_num = variable_comb["properties"]["Block number"]["number"]
        column_name_data = variable_comb["properties"]["Column name"]["title"]
        
        if column_name_data:
          column_name = column_name_data[0]["text"]["content"]
        else:
          column_name = None
        
        multi_select = variable_comb["properties"]["Type"]["multi_select"]

        result_dict[block_var_num] = {
          "column": column_name,
          "bold": False,
          "italic": False,
          "underline": False,
          "strikethrough": False
        }

        for select in multi_select:
          if select["name"] == "bold":
            result_dict[block_var_num]["bold"] = True
          if select["name"] == "italic":
            result_dict[block_var_num]["italic"] = True
          if select["name"] == "underline":
            result_dict[block_var_num]["underline"] = True
          if select["name"] == "strikethrough":
            result_dict[block_var_num]["strikethrough"] = True

      except KeyError as e:
        print(f"データ処理中に KeyError が発生: {e}")
        error_flag = True  # エラー発生を記録

  except requests.RequestException as e:
    print(f"Notion API へのリクエスト中にエラー発生: {e}")
    return None, True  # APIエラー時

  except Exception as e:
    print(f"create_block_var_and_column_name 関数内で予期せぬエラーが発生: {e}")
    return None, True  # その他のエラー時

  return result_dict, error_flag

# cover & icon から環境変数を作成 ( preperty_name, property_type, property_content(対応する列の内容が入っている) を key にした dict の list)
# 型の一致チェックまで行う（数値・テキスト・日時（日付・日時・時間）の三種類だけをとりあえず分類する）
def create_property_and_column(template_database_id, headers, PROPERTY_NAME_TYPE_BOX, COLUMN_NAME_TYPE_BOX):
  error_flag = False  # エラー発生フラグ
  property_and_column_list = []
  is_order_flag = False

  try:
    # まずは database から内容を取得
    url = f"https://api.notion.com/v1/databases/{template_database_id}/query"
    payload = {}
    res = requests.post(url=url, headers=headers, json=payload)

    try:
      res.raise_for_status()  # HTTPエラーをキャッチ
    except requests.exceptions.HTTPError as e:
      print(f"Notion API からのレスポンスエラー: {e}")
      return None, True  # HTTPエラーが発生した場合は None, True を返す

    # データ取得
    variable_pairs = res.json().get("results", [])

    # 環境変数についてのリストを作成
    for variable_pair in variable_pairs:
      try:
        property_name_data = variable_pair["properties"]["Property name"]["rich_text"]
        column_name_data = variable_pair["properties"]["Column name"]["title"]

        if not property_name_data or not column_name_data:
          print("プロパティ名またはカラム名が存在しません。")
          error_flag = True
          continue

        property_name = property_name_data[0]["text"]["content"]
        column_name = column_name_data[0]["text"]["content"]

        # 型が一致しているかチェック
        if PROPERTY_NAME_TYPE_BOX.get(property_name) == "number":
          if COLUMN_NAME_TYPE_BOX.get(column_name) != "number":
            print(f"警告: property '{property_name}' と column '{column_name}' の型が不一致です。"
                  f" (property type: number, column type: {COLUMN_NAME_TYPE_BOX.get(column_name, '不明')})")
            error_flag = True  # 型不一致のエラー

        # order が直接 filter 対象になっている場合
        if column_name == "order":
          is_order_flag = True

        # property の type を取得する
        property_type = PROPERTY_NAME_TYPE_BOX.get(property_name)
        property_and_column_list.append({
          "column_name": column_name,
          "property_name": property_name,
          "property_type": property_type
        })

      except KeyError as e:
        print(f"データ処理中に KeyError が発生: {e}")
        error_flag = True  # エラー発生を記録

  except requests.RequestException as e:
    print(f"Notion API へのリクエスト中にエラー発生: {e}")
    return None, True  # APIエラー時

  except Exception as e:
    print(f"create_property_and_column 関数内で予期せぬエラーが発生: {e}")
    return None, True  # その他のエラー時

  # order を暗黙的に追加
  if not is_order_flag:
    property_and_column_list.append({
      "column_name": "order",
      "property_name": "order",
      "property_type": "number"
    })

  return property_and_column_list, error_flag

# Filters を作成 ( key は common, notion,spreadsheet, value は filtered order list)
def create_property_or_column_filter(template_database_id, output_database_id, headers, df, PROPERTY_NAME_TYPE_BOX, COLUMN_NAME_TYPE_BOX):
  error_flag = False  # エラー発生フラグ
  filters_box = []
  filter_column_name_list = []

  try:
    # まずは template database から内容を取得
    url = f"https://api.notion.com/v1/databases/{template_database_id}/query"
    payload = {}
    res = requests.post(url=url, headers=headers, json=payload)

    try:
      res.raise_for_status()  # HTTPエラーをキャッチ
    except requests.exceptions.HTTPError as e:
      print(f"Notion API からのレスポンスエラー (template database): {e}")
      return None, None, True  # HTTPエラーが発生した場合は None, True を返す

    # データ取得
    filter_combs = res.json().get("results", [])

    # output database のフィルターを作成
    for filter_comb in filter_combs:
      try:
        is_active = filter_comb["properties"]["Is Active"]["select"]["name"]
        if is_active != "Active":
          continue  # Active でない場合スキップ

        filter_name = filter_comb["properties"]["Name"]["title"][0]["text"]["content"]
        filter_target = filter_comb["properties"]["Column | Property"]["select"]["name"]
        filter_expression = filter_comb["properties"]["Filter"]["rich_text"][0]["text"]["content"]

        if filter_target == "Column":
          filter_column_name_list.append(filter_name)
          filters_box.append({
            "target": filter_target,
            "name": filter_name,
            "type": COLUMN_NAME_TYPE_BOX.get(filter_name),
            "expression": filter_expression
          })
        else:
          filters_box.append({
            "target": filter_target,
            "name": filter_name,
            "type": PROPERTY_NAME_TYPE_BOX.get(filter_name),
            "expression": filter_expression
          })

      except KeyError as e:
        print(f"フィルターデータ処理中に KeyError が発生: {e}")
        error_flag = True  # エラー発生を記録

    # output database のデータ数と spreadsheet のデータ数を取得する
    url = f"https://api.notion.com/v1/databases/{output_database_id}/query"
    res = requests.post(url=url, headers=headers, json={})

    try:
      res.raise_for_status()
    except requests.exceptions.HTTPError as e:
      print(f"Notion API からのレスポンスエラー (output database): {e}")
      return None, None, True

    output_db_data_length = len(res.json().get("results", []))
    spreadsheet_data_length = len(df)

    # Notion 用のフィルターを作成
    try:
      output_notion_filter, error_flag = create_notion_filter(filters_box=filters_box)
    except Exception as e:
      print(f"Notion 用フィルターの作成に失敗: {e}")
      return None, None, True

    output_notion_sorts = [{"property": "order", "direction": "ascending"}]
    payload = {"filter": output_notion_filter, "sorts": output_notion_sorts}

    # output db で filter をかけてデータを取得する
    output_db_filtered_order_list = []
    output_db_filtered_order_dict = {}
    res = requests.post(url=url, headers=headers, json=payload)

    try:
      res.raise_for_status()
    except requests.exceptions.HTTPError as e:
      print(f"Notion API からのフィルターデータ取得エラー: {e}")
      return None, None, True
    
    filtered_items = res.json().get("results", [])
    for item in filtered_items:
      try:
        item_order = item["properties"]["order"]["number"]
        item_id = item["id"]
        output_db_filtered_order_list.append(item_order)
        output_db_filtered_order_dict[item_order] = item_id
      except KeyError as e:
        print(f"order プロパティ取得中に KeyError が発生: {e}")
        error_flag = True

    # Spreadsheet の filtered order list を作る
    try:
      filtered_df = create_spreadsheet_filter(df_original=df, filters_box=filters_box)
    except Exception as e:
      print(f"スプレッドシート用フィルターの作成に失敗: {e}")
      return None, None, True

    spreadsheet_filtered_order_list = filtered_df["order"].tolist()

    # 共通の filtered order list を作成
    if output_db_data_length >= spreadsheet_data_length:
      pruned_output_db_filtered_order_list = [x for x in output_db_filtered_order_list if x <= spreadsheet_data_length]
      common_filtered_order_list = list(set(pruned_output_db_filtered_order_list) & set(spreadsheet_filtered_order_list))
    else:
      extention_set = set(range(output_db_data_length+1, spreadsheet_data_length+1))
      extend_output_db_filtered_order_set = set(output_db_filtered_order_list) | extention_set
      common_filtered_order_list = list(extend_output_db_filtered_order_set & set(spreadsheet_filtered_order_list))

    # 並び替え
    common_filtered_order_list.sort()
    spreadsheet_filtered_order_list.sort()

    return [{"common": common_filtered_order_list, "notion": output_db_filtered_order_list, "spreadsheet": spreadsheet_filtered_order_list}, filter_column_name_list], output_db_filtered_order_dict, error_flag

  except requests.RequestException as e:
    print(f"Notion API へのリクエスト中にエラー発生: {e}")
    return None, None, True

  except Exception as e:
    print(f"create_property_or_column_filter 関数内で予期せぬエラーが発生: {e}")
    return None, None, True