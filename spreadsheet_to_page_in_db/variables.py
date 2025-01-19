import requests
from notion_filter import create_notion_filter
from spreadsheet_filter import create_spreadsheet_filter

# cover & icon から環境変数を作成 ( cover or icon が key, column name が value)
def create_cover_and_icons(database_id, headers):
  # まずは database から内容を取得
  url = f"https://api.notion.com/v1/databases/{database_id}/query"
  payload = {}
  res = requests.post(url=url, headers=headers, json=payload)
  if res.status_code != 200:
    print("cover & icon データベースから環境変数を取得する際にエラーが発生しました。")
    res.raise_for_status()
  variable_pairs = res.json()["results"]
  # 環境変数についての辞書を作成
  cover_and_icon_dict = {}
  cover_and_icon_dict[variable_pairs[0]["properties"]["Select"]["select"]["name"]] = variable_pairs[0]["properties"]["Column name"]["title"][0]["text"]["content"]
  cover_and_icon_dict[variable_pairs[1]["properties"]["Select"]["select"]["name"]] = variable_pairs[1]["properties"]["Column name"]["title"][0]["text"]["content"]
  return cover_and_icon_dict

# Block Var & Column Name から環境変数を作成 ( 変数の数を key, value は 辞書、その辞書の中には column, bold, italic, underline strikethrough が入っている)
def create_block_var_and_column_name(database_id, headers):
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
  if res.status_code != 200:
    print("cover & icon データベースから環境変数を取得する際にエラーが発生しました。")
    res.raise_for_status()
  variable_combs = res.json()["results"]
  # 環境変数についての辞書を作成
  result_dict = {}
  for variable_comb in variable_combs:
    block_var_num = variable_comb["properties"]["Block number"]["number"]
    column_name = variable_comb["properties"]["Column name"]["title"][0]["text"]["content"]
    multi_select = variable_comb["properties"]["Type"]["multi_select"]
    result_dict[block_var_num] = {"column":column_name, "bold": False, "italic": False, "underline": False, "strikethrough": False}
    for select in multi_select:
      if select["name"] == "bold":
        result_dict[block_var_num]["bold"] = True
      if select["name"] == "italic":
        result_dict[block_var_num]["italic"] = True
      if select["name"] == "underline":
        result_dict[block_var_num]["underline"] = True
      if select["name"] == "strikethrough":
        result_dict[block_var_num]["strikethrough"] = True
  return result_dict 

# cover & icon から環境変数を作成 ( preperty_name, property_type, property_content(対応する列の内容が入っている) を key にした dict の list)
def create_property_and_column(template_database_id, output_database_id, headers, df_row):
  # まずは database から内容を取得
  url = f"https://api.notion.com/v1/databases/{template_database_id}/query"
  payload = {}
  res = requests.post(url=url, headers=headers, json=payload)
  if res.status_code != 200:
    print("cover & icon データベースから環境変数を取得する際にエラーが発生しました。")
    res.raise_for_status()
  variable_pairs = res.json()["results"]
  
  # 環境変数についての辞書を作成
  property_and_column_list = []
  url = f"https://api.notion.com/v1/databases/{output_database_id}"
  res = requests.get(url=url, headers=headers)
  if res.status_code != 200:
    print("output database の property の type を取得する際にエラーが発生しました。")
    res.raise_for_status()
  output_db_properties = res.json()["results"]["properties"]
  for variable_pair in variable_pairs:
    property_name = variable_pair["properties"]["Property name"]["rich_text"][0]["text"]["content"]
    column_name = variable_pair["properties"]["Column name"]["title"][0]["text"]["content"]
    # property の type を取得する
    property_type = output_db_properties[property_name]["type"]
    property_content = df_row[column_name]
    property_and_column_list.append({"column_name": column_name, "property_name": property_name, "property_type": property_type, "property_content": property_content})
  return property_and_column_list

# Filters を作成 ( key は common, notion,spreadsheet, value は filtered order list)
def create_property_or_column_filter(template_database_id, output_database_id, headers, df):
  # まずは database から内容を取得
  url = f"https://api.notion.com/v1/databases/{template_database_id}/query"
  payload = {}
  res = requests.post(url=url, headers=headers, json=payload)
  if res.status_code != 200:
    print("cover & icon データベースから環境変数を取得する際にエラーが発生しました。")
    res.raise_for_status()
  filter_combs = res.json()["results"]
  # output database の filter を作成。後で使うように column name を取得しておく。
  filters_box = []
  filter_column_name_list = []
  for filter_comb in filter_combs:
    if filter_comb["properties"]["Is Active"]["select"]["name"] == "Active":
      filter_name = filter_comb["properties"]["Name"]["title"][0]["text"]["content"]
      filter_type = filter_comb["properties"]["Column | Property"]["select"]["name"]
      filter_expression = filter_comb["properties"]["Filter"]["rich_text"][0]["text"]["content"]
      filters_box.append({
        "type": filter_type,
        "name": filter_name,
        "expression": filter_expression
      })
      if filter_type == "Column":
        filter_column_name_list.append(filter_name)
  
  # order list を作成
  # まずは output database の データ数と spreadsheet のデータ数を取得する。
  url = f"https://api.notion.com/v1/databases/{output_database_id}/query"
  res = requests.post(url=url, headers=headers, json={})
  if res.status_code != 200:
    print("output データベースから全てのデータを取得する際にエラーが発生しました。")
    res.raise_for_status()
  output_db_data_length = len(res.json()["results"])
  spreadsheet_data_length = len(df)

  # output db の filtered order list を作る
  # notion 手書きの expression から API 用の filter に変更
  output_notion_filter = create_notion_filter(output_database_id=output_database_id, headers=headers, filters_box=filters_box)
  output_notion_filter["sorts"] = [{"property": "order","direction": "ascending"}]
  # filter をかけてデータを取得する
  output_db_filtered_order_list = []
  res = requests.post(url=url, headers=headers, json=output_notion_filter)
  if res.status_code != 200:
    print("output データベースから filter をかけてデータを取得する際にエラーが発生しました。")
    res.raise_for_status()
  filtered_items = res.json()["results"]
  for item in filtered_items:
    item_order = item["properties"]["order"]["number"]
    output_db_filtered_order_list.append(item_order)
  
  # spreadsheet の filtered order list を作る
  # notion 手書きの expression から dataframe に filter をかける
  filtered_df = create_spreadsheet_filter(df_original=df, filters_box=filters_box)
  spreadsheet_filtered_order_list = filtered_df["order"].tolist()
  
  # 全体を考慮した filtered order list を作成する。
  if output_db_data_length >= spreadsheet_data_length:
    pruned_output_db_filtered_order_list = [x for x in output_db_filtered_order_list if x <= spreadsheet_data_length]
    common_filtered_order_list = list(set(pruned_output_db_filtered_order_list) & set(spreadsheet_filtered_order_list))
  else:
    extention = range(output_db_data_length+1,spreadsheet_data_length+1)
    extend_output_db_filtered_order_list = output_db_filtered_order_list + extention
    common_filtered_order_list = list(set(extend_output_db_filtered_order_list) & set(spreadsheet_filtered_order_list))
  
  return [{"common": common_filtered_order_list, "notion": output_db_filtered_order_list, "spreadsheet": spreadsheet_filtered_order_list}, filter_column_name_list]