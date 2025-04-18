import requests
import json
import time

# DB に新しいページを作成する。
def create_new_page_in_db(headers, database_id, icon, cover, properties, children, order, delete_order_index):
  url = "https://api.notion.com/v1/pages"
  parent = {"database_id": database_id}
  payload = {
    "parent": parent,
    "icon": icon,
    "cover": cover,
    "properties": properties,
    "children": children
  }
  print("payload:",payload)
  res = requests.post(url=url, headers=headers, json=payload)
  print("res:", res)
  if res.status_code != 200:
    if order:
      print(f"ページを作成する際にエラーが発生しました。order = {order}")
    else:
      print(f"ページを作成する際にエラーが発生しました。")
    # 元のページを復活させてエラーを吐く
    if order in delete_order_index:
      page_id = delete_order_index[order]
      url = f"https://api.notion.com/v1/pages/{page_id}"
      payload = {
        "archived": False,
        "properties":
          {
            "Status": {
              "status": {
                "name": "エラー"
              }
            }
          }
      }
      res = requests.patch(url=url, headers=headers, json=payload)
      if res.status_code != 200:
        print(order)
        print("元のページを復活させてエラーを吐かせる時にエラーが発生しました。")
        res.raise_for_status()
    res.raise_for_status()
  return order

# 既存のページに追加する。
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

# pagination を使って database の全てのページを取得する。
def fetch_all_pages(headers, url, payload):
  all_pages = []
  payload["page_size"] = 100
  
  while True:
    res = res.post(url, headers=headers, data=json.dumps(payload))
    if res.status_code != 200:
      print("database の page を fetch する時にエラーが発生しました。")
      res.raise_for_status()
    response_data = res.json()
    all_pages.extend(response_data.get("results", []))
    
    if not response_data.get("has_more"):
      break
    
    # Update payload with next_cursor
    payload["start_cursor"] = response_data["next_cursor"]
  
  return all_pages

def update_notion_status_to_error(template_id: str, error_message: str, headers: dict, is_stopped = False):
  """
  NotionのページのStatusプロパティを「エラー」に更新する関数

  Args:
    template_id (str): NotionのページID
    error_message (str): エラーメッセージ (例: "csv file (3番目) を取得する際にエラーが発生しました。")
    headers (dict): Notion APIの認証ヘッダー
  """
  url = f"https://api.notion.com/v1/pages/{template_id}"
  data = {
    "properties": {
      "Status": {
        "status": {
          "name": "エラー"
        }
      }
    }
  }
  
  res = requests.patch(url=url, headers=headers, json=data)
  
  if res.status_code != 200:
    print(f"実行中からエラーに変更する際にエラーが発生しました。({error_message})")
    res.raise_for_status()
  else:
    print({error_message})
    if is_stopped:
      res.raise_for_status()

def update_notion_status_to_ready(template_id: str, headers: dict, is_stopped=False):
  url = f"https://api.notion.com/v1/pages/{template_id}"
  data = {
    "properties":
      {
        "Status": {
          "status": {
            "name": "実行待機中"
          }
        }
      }
  }
  res = requests.patch(url=url, headers=headers, json=data)
  if res.status_code != 200:
    error_message = "Template Box から テンプレートのデータを取得する際にエラーが発生しました。"
    update_notion_status_to_error(template_id=template_id, error_message=error_message, headers=headers, is_stopped=is_stopped)

def update_notion_status_to_inprogress(template_id: str, headers: dict, is_stopped=False):
  url = f"https://api.notion.com/v1/pages/{template_id}"
  data = {
    "properties":
      {
        "Status": {
          "status": {
            "name": "実行中"
          }
        }
      }
  }
  res = requests.patch(url=url, headers=headers, json=data)
  if res.status_code != 200:
    error_message = "Template Box から テンプレートのデータを取得する際にエラーが発生しました。"
    update_notion_status_to_error(template_id=template_id, error_message=error_message, headers=headers, is_stopped=is_stopped)