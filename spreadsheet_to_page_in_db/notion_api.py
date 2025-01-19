import requests
import json

# DB に新しいページを作成する。
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

