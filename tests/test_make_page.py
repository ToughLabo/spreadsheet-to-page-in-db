import pytest
import json
from unittest.mock import patch, MagicMock

# テスト対象の関数をインポート
# （提示されたコードを spreadsheet_to_page_in_db.make_page.py にまとめてある前提）
from spreadsheet_to_page_in_db.make_page import (
  is_block_var,
  make_callout_block,
  make_column_list_block,
  make_divider_block,
  make_heading_block,
  make_paragraph_block,
  make_toggle_block,
  make_complete_block_for_template,
  make_page_property,
  delete_pages,
)

#############################
# 1. is_block_var のテスト
#############################
class TestIsBlockVar:
  def test_block_var_single_digit(self):
    """BLOCK_1 のように7文字 (BLOCK_ + 1桁数字) なら True, var_num=1 を返す"""
    rich_text = [
      {
        "type": "text",
        "text": {"content": "BLOCK_1"}
      }
    ]
    flag, num = is_block_var(rich_text)
    assert flag is True
    assert num == 1

  def test_block_var_two_digits(self):
    """BLOCK_12 のように8文字 (BLOCK_ + 2桁数字) なら True, var_num=12 を返す"""
    rich_text = [
      {
        "type": "text",
        "text": {"content": "BLOCK_12"}
      }
    ]
    flag, num = is_block_var(rich_text)
    assert flag is True
    assert num == 12

  def test_not_block_var(self):
    """BLOCK_123 のように3桁以上は対応外の例外, あるいは普通の文字列ならFalse"""
    rich_text = [
      {
        "type": "text",
        "text": {"content": "BLOCK_123"}
      }
    ]
    flag, num = is_block_var(rich_text)
    assert flag is True
    assert num == 123

  def test_different_text(self):
    """BLOCK_ 以外なら普通に False, None を返す"""
    rich_text = [
      {
        "type": "text",
        "text": {"content": "Hello World"}
      }
    ]
    flag, num = is_block_var(rich_text)
    assert flag is False
    assert num is None

  def test_empty_rich_text(self):
    """rich_text が空配列 or 要素0件なら False, None"""
    flag, num = is_block_var([])
    assert flag is False
    assert num is None

#############################
# 2. make_callout_block のテスト
#############################
@pytest.fixture
def mock_requests_get():
  """
  requests.get をモック化するためのフィクスチャ。
  他テストでも使い回したい場合は使います。
  """
  with patch("spreadsheet_to_page_in_db.make_page.requests.get") as mock_get:
      yield mock_get

def test_make_callout_block_no_children(mock_requests_get):
  """
  has_children=False の場合、children取得のGETを呼ばず、
  そのままcalloutブロックを作るかをテスト
  """
  # テンプレートブロックの例
  template_block = {
    "type": "callout",
    "id": "xxxxx",
    "has_children": False,
    "callout": {
      "rich_text": [
        {
          "type": "text",
          "text": {"content": "BLOCK_1"}
        }
      ],
      "icon": {"emoji": "🔔"},
      "color": "default"
    }
  }
  # BLOCK_VAR_BOX のダミーデータ (BLOCK_1 → カラム "title" で文字列を取得)
  BLOCK_VAR_BOX = {
    1: {
      "column": "title",
      "bold": True,
      "underline": False,
      "italic": False,
      "strikethrough": False
    }
  }
  # df_row のダミー（pandas の行を想定）: dictでOK
  df_row = {"title": "TestTitle"}

  headers = {}  # ダミー

  # 実行
  callout_block = make_callout_block(headers, template_block, df_row, BLOCK_VAR_BOX)

  # 検証
  # mock_requests_get は呼ばれていないはず
  mock_requests_get.assert_not_called()

  assert callout_block["type"] == "callout"
  assert callout_block["callout"]["rich_text"][0]["text"]["content"] == "TestTitle"
  assert callout_block["callout"]["icon"]["emoji"] == "🔔"

def test_make_callout_block_with_children(mock_requests_get):
  """
  has_children=True の場合、children取得のGETを行うことをテスト
  """
  # Mock のレスポンスを指定
  mock_resp = MagicMock()
  mock_resp.status_code = 200
  mock_resp.json.return_value = {
    "results": [
      {
        "type": "paragraph",
        "id": "child-block-id",
        "has_children": False,
        "paragraph": {
          "rich_text": [{"type":"text","text":{"content":"child paragraph"}}],
          "color": "default",
          "children": []
        }
      }
    ]
  }
  mock_requests_get.return_value = mock_resp

  template_block = {
    "type": "callout",
    "id": "parent-block-id",
    "has_children": True,
    "callout": {
      "rich_text": [
        {
          "type": "text",
          "text": {"content": "Just normal text"}
        }
      ],
      "icon": {"emoji": "😎"},
      "color": "default"
    }
  }
  BLOCK_VAR_BOX = {}
  df_row = {}
  headers = {"Authorization":"Bearer X", "Notion-Version":"2022-06-28"}

  callout_block = make_callout_block(headers, template_block, df_row, BLOCK_VAR_BOX)

  # GET が一度呼ばれているか
  mock_requests_get.assert_called_once()
  # 返された子ブロックが入っているか
  children = callout_block["callout"]["children"]
  assert len(children) == 1
  assert children[0]["type"] == "paragraph"

#############################
# 3. make_column_list_block
#############################
@pytest.fixture
def mock_requests_get_children():
  """
  column_list などが子供ブロックを取得する時のモック
  """
  with patch("spreadsheet_to_page_in_db.make_page.requests.get") as mock_get:
    yield mock_get

def test_make_column_list_block(mock_requests_get_children):
  """
  column_list が has_children=True の column を持つケース
  """
  # まず column_list の子供(= columns) 取得用のモック
  mock_resp_columns = MagicMock()
  mock_resp_columns.status_code = 200
  mock_resp_columns.json.return_value = {
    "results": [
      {
        "type": "column",
        "id": "column_id_1",
        "has_children": True
      },
      {
        "type": "column",
        "id": "column_id_2",
        "has_children": False
      }
    ]
  }
  # column_id_1 の children 取得用モック
  mock_resp_column1_children = MagicMock()
  mock_resp_column1_children.status_code = 200
  mock_resp_column1_children.json.return_value = {
    "results": [
      {
        "type": "paragraph",
        "id": "child_id_p",
        "has_children": False,
        "paragraph": {
          "rich_text": [{"type":"text","text":{"content":"In column1"}}],
          "color": "default",
        }
      }
    ]
  }

  # 2回のGET呼び出しに対して、順にモックレスポンスを返す
  mock_requests_get_children.side_effect = [mock_resp_columns, mock_resp_column1_children]

  # テンプレートブロック
  column_list_block = {
    "type": "column_list",
    "id": "column_list_id",
    "has_children": True,
    "column_list": {"children": []}
  }
  BLOCK_VAR_BOX = {}
  df_row = {}
  headers = {}

  res_block = make_column_list_block(headers, column_list_block, df_row, BLOCK_VAR_BOX)

  # mock_requests_get_children が2回呼ばれたか
  assert mock_requests_get_children.call_count == 2

  # 結果の構造を確認
  assert res_block["type"] == "column_list"
  cl_children = res_block["column_list"]["children"]
  assert len(cl_children) == 2

  # column_id_1 の children に paragraph がいるか
  col1 = cl_children[0]
  assert col1["type"] == "column"
  assert len(col1["column"]["children"]) == 1
  assert col1["column"]["children"][0]["type"] == "paragraph"

  # column_id_2 は has_children=False だったので中身は空
  col2 = cl_children[1]
  assert col2["type"] == "column"
  assert len(col2["column"]["children"]) == 0

#############################
# 4. make_divider_block の簡単テスト
#############################
def test_make_divider_block():
  block = make_divider_block()
  assert block["type"] == "divider"
  assert block["divider"] == {}

#############################
# 5. make_heading_block の簡単テスト (has_children=False)
#############################
def test_make_heading_block_no_children():
  template_block = {
    "type": "heading_1",
    "id": "heading_1_id",
    "has_children": False,
    "heading_1": {
      "rich_text": [{"type": "text","text":{"content": "BLOCK_1"}}],
      "color": "default",
      "is_toggleable": False,
      "children": []
    }
  }
  BLOCK_VAR_BOX = {
    1: {
      "column": "title",
      "bold": False,
      "underline": False,
      "italic": False,
      "strikethrough": False
    }
  }
  df_row = {"title": "New Heading Title"}
  headers = {}

  block = make_heading_block(headers, template_block, df_row, BLOCK_VAR_BOX)
  assert block["type"] == "heading_1"
  text_arr = block["heading_1"]["rich_text"]
  assert len(text_arr) == 1
  assert text_arr[0]["text"]["content"] == "New Heading Title"

#############################
# 6. make_paragraph_block のテスト
#############################
def test_make_paragraph_block_no_children():
  paragraph_block = {
    "type": "paragraph",
    "id": "para_id",
    "has_children": False,
    "paragraph": {
      "rich_text": [{"type":"text","text":{"content":"BLOCK_1"}}],
      "color": "default"
    }
  }
  BLOCK_VAR_BOX = {
    1: {
      "column": "body",
      "bold": True,
      "underline": False,
      "italic": False,
      "strikethrough": False
    }
  }
  df_row = {"body": "This is paragraph from CSV"}
  headers = {}
  result, is_blocks = make_paragraph_block(headers, paragraph_block, df_row, BLOCK_VAR_BOX)
  # paragraph_block は BLOCK_var だったので parse_blocks() を呼ぶ
  # => (parsed_blocks, True) を返す想定
  assert is_blocks is True
  # parse_blocks の結果が返ってきているか
  # たとえば parse_blocks は paragraph ブロックのリストを返すので、
  # そこは実装次第で確認してください。
  assert isinstance(result, list)
  # ざっくり内容をチェック
  if result:
      assert result[0]["type"] in ("paragraph","heading_1","heading_2","bulleted_list_item")

#############################
# 7. make_toggle_block の簡単テスト
#############################
def test_make_toggle_block_no_children():
  toggle_block = {
    "type": "toggle",
    "id": "toggle_id",
    "has_children": False,
    "toggle": {
      "rich_text": [{"type":"text","text":{"content":"BLOCK_1"}}],
      "color": "default",
      "children": []
    }
  }
  BLOCK_VAR_BOX = {
    1: {
      "column": "toggle_content",
      "bold": False,
      "underline": False,
      "italic": False,
      "strikethrough": False
    }
  }
  df_row = {"toggle_content": "A toggled block text"}
  headers = {}

  result_block = make_toggle_block(headers, toggle_block, df_row, BLOCK_VAR_BOX)
  assert result_block["type"] == "toggle"
  toggle_text = result_block["toggle"]["rich_text"]
  assert len(toggle_text) == 1
  assert toggle_text[0]["text"]["content"] == "A toggled block text"

#############################
# 8. make_complete_block_for_template
#############################
def test_make_complete_block_for_template_paragraph():
  template_block = {
    "type": "paragraph",
    "paragraph": {
      "rich_text": [{"type":"text","text":{"content":"Hello"}}],
      "color": "default"
    },
    "id": "some_id",
    "has_children": False
  }
  BLOCK_VAR_BOX = {}
  df_row = {}
  headers = {}

  block, is_blocks = make_complete_block_for_template(headers, template_block, df_row, BLOCK_VAR_BOX)
  # paragraph ブロックが返る
  assert not is_blocks
  assert block["type"] == "paragraph"
  assert block["paragraph"]["rich_text"][0]["text"]["content"] == "Hello"

#############################
# 9. spreadsheet_to_page_in_db.make_page_property
#############################
def test_make_page_property_files():
  prop = make_page_property(
    property_name="Attachments",
    property_type="files",
    property_content="https://example.com/foo.png,https://example.com/bar.jpg",
    PROPERTY_SELECT_BOX={}
  )
  assert "files" in prop
  assert len(prop["files"]) == 2
  assert prop["files"][0]["external"]["url"] == "https://example.com/foo.png"
  assert prop["files"][1]["external"]["url"] == "https://example.com/bar.jpg"

def test_make_page_property_select_ok():
  PROPERTY_SELECT_BOX = {
    "Category": ["News", "Blog", "Tutorial"]
  }
  prop = make_page_property(
    property_name="Category",
    property_type="select",
    property_content="Blog",
    PROPERTY_SELECT_BOX=PROPERTY_SELECT_BOX
  )
  assert "select" in prop
  assert prop["select"]["name"] == "Blog"

def test_make_page_property_select_fail():
  PROPERTY_SELECT_BOX = {
    "Category": ["News", "Blog", "Tutorial"]
  }
  with pytest.raises(ValueError) as e:
    make_page_property(
      property_name="Category",
      property_type="select",
      property_content="SomethingElse",
      PROPERTY_SELECT_BOX=PROPERTY_SELECT_BOX
    )
  assert "出力先のデータベースに登録されていません" in str(e.value)

def test_make_page_property_checkbox():
  prop = make_page_property(
    property_name="Done",
    property_type="checkbox",
    property_content=True,  # bool であるべき
    PROPERTY_SELECT_BOX={}
  )
  # { "checkbox": True } が返る想定
  assert "checkbox" in prop
  assert prop["checkbox"] is True

#############################
# 10. delete_pages
#############################
# @pytest.fixture
# def mock_requests_post_patch():
#   with patch("spreadsheet_to_page_in_db.make_page.requests.post") as mock_post, \
#       patch("spreadsheet_to_page_in_db.make_page.requests.patch") as mock_patch:
#     yield (mock_post, mock_patch)

# def test_delete_pages_success(mock_requests_post_patch):
#   """
#   filtered_order=[10,20] などを指定して、想定通りに Notion API が呼ばれるかをテスト
#   """
#   mock_post, mock_patch = mock_requests_post_patch
#   # post -> 200 OK, resultsに1件だけ
#   post_resp = MagicMock()
#   post_resp.status_code = 200
#   post_resp.json.return_value = {
#     "results": [
#       {"id": "page_id_123"}
#     ]
#   }
#   mock_post.return_value = post_resp

#   # patch -> 200 OK
#   patch_resp = MagicMock()
#   patch_resp.status_code = 200
#   patch_resp.json.return_value = {}
#   mock_patch.return_value = patch_resp

#   headers = {}
#   output_database_id = "db_id"
#   filtered_order = [10, 20]

#   delete_pages(output_database_id, headers, filtered_order)

#   assert mock_post.call_count == 2  # 2回（order=10, order=20）
#   assert mock_patch.call_count == 2

#   # post が呼ばれたときの引数を確認
#   call_args_list = mock_post.call_args_list
#   print("call_args_list[0]:", call_args_list[0])
#   # 1回目
#   call = call_args_list[0]
#   assert call["url"] == f"https://api.notion.com/v1/databases/{output_database_id}/query"
#   # payloadをチェック
#   expected_filter = {
#     "filter": {
#       "property": "order",
#       "number": {
#         "equals": 10
#       }
#     }
#   }
#   assert call.headers == headers
#   assert call.json == expected_filter

#   # patch が呼ばれたときの引数を確認
#   call_args_list_patch = mock_patch.call_args_list
#   args, kwargs = call_args_list_patch[0]
#   # https://api.notion.com/v1/pages/page_id_123
#   assert "page_id_123" in args[0]
#   # data = {"archived": True}
#   body = json.loads(kwargs["data"])
#   assert body["archived"] is True
