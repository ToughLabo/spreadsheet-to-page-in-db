import re

def extract_uuid_from_notion_url(url):
  pattern = r"([0-9a-f]{32})|([0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12})"
  match = re.search(pattern, url)
  if match:
    return match.group(1)
  else:
    print("Not found id from url!")
    return None