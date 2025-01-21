# test_pre_process.py
import pytest
import requests_mock
import pandas as pd
from unittest.mock import patch, MagicMock
from spreadsheet_to_page_in_db.pre_process import (
  extract_uuid_from_notion_url,
  pre_process_callout,
  pre_process_quote,
  pre_process_numbered_list,
  pre_process_bulleted_list,
  pre_process_generative_ai_detail,
  pre_process_generative_ai_batched,
  batch_process_dataframe,
  pre_process_csv
)


def test_extract_uuid_from_notion_url():
  # 正常系: ハイフン付きバージョン
  url1 = "https://www.notion.so/SomeTitle-12345678-1234-1234-1234-1234567890ab"
  assert extract_uuid_from_notion_url(url1) == "123456781234123412341234567890ab"

  # 正常系: ハイフンなしバージョン
  url2 = "https://www.notion.so/123456781234123412341234567890ab?v=xxxxx"
  assert extract_uuid_from_notion_url(url2) == "123456781234123412341234567890ab"

  # UUID が見つからない場合
  url3 = "https://www.notion.so/"
  assert extract_uuid_from_notion_url(url3) is None


def test_pre_process_callout():
  text = "This is a callout"
  expected = "> [!⭐] This is a callout"
  assert pre_process_callout(text) == expected


def test_pre_process_quote():
  text = "This is a quote"
  expected = "> This is a quote"
  assert pre_process_quote(text) == expected


def test_pre_process_numbered_list():
  # 入力にインデント/箇条書き記号あり
  input_text = """・Hello
  - World
      - Nested
  Final
"""
  # 期待値
  # 1. Hello
  # 2. World
  #     1. Nested
  # 3. Final
  # （ただし行頭のスペース量によってインデントが決まる）
  expected = """1. Hello
2. World
  1. Nested
3. Final"""
  assert pre_process_numbered_list(input_text) == expected


def test_pre_process_bulleted_list():
  input_text = """・Apple
  - Banana
    - Cherry
  Durian
"""
    # 行頭のスペース量(2スペース単位) でインデントが決まる
  expected = """- Apple
  - Banana
    - Cherry
  - Durian"""
  assert pre_process_bulleted_list(input_text) == expected


@pytest.mark.parametrize("input_text, mock_response_text", [
  ("Sample text", "Processed text"),
  ("Another text", "Another processed text")
])
def test_pre_process_generative_ai_detail(input_text, mock_response_text):
  # `generate_content` をモック化
  with patch("spreadsheet_to_page_in_db.pre_process.genai.GenerativeModel") as mock_model_class:
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = mock_response_text
    mock_model_class.return_value = mock_model

    output = pre_process_generative_ai_detail(input_text)
    assert output == mock_response_text

    # ちゃんと generate_content が呼ばれたかを確認
    mock_model.generate_content.assert_called_once()


def test_pre_process_generative_ai_batched():
  fake_input = "<ROW 0>Hello</ROW 0>\n<ROW 1>World</ROW 1>"
  fake_output = (
    "<ROW 0>\n変換済み: Hello\n</ROW 0>\n"
    "<ROW 1>\n変換済み: World\n</ROW 1>"
  )
  with patch("spreadsheet_to_page_in_db.pre_process.genai.GenerativeModel") as mock_model_class:
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = fake_output
    mock_model_class.return_value = mock_model

    result = pre_process_generative_ai_batched(fake_input)
    print(result)
    assert "<ROW 0>\n変換済み: Hello\n</ROW 0>" in result
    assert "<ROW 1>\n変換済み: World\n</ROW 1>" in result
    # モック呼び出し確認
    mock_model.generate_content.assert_called_once()

def test_batch_process_dataframe():
    # DataFrame を用意
    df = pd.DataFrame({
        "content": [
            "First row content",
            "Second row content",
            "Third row content",
            "Forth row content"
        ]
    })

    # バッチ処理用のモック戻り値
    fake_output_first_call = "<ROW 1>変換済み: Second row content</ROW 1>\n<ROW 2>変換済み: Third row content</ROW 2>"
    fake_output_second_call = ""

    # AI detail の戻り値（1回目と2回目で異なる値を返す）
    detail_side_effects = ["Detail Processed First row", "Detail Processed Fourth row"]

    # バッチ処理の戻り値（1回目と2回目で異なる値を返す）
    batch_side_effects = [fake_output_first_call, fake_output_second_call]

    with patch("spreadsheet_to_page_in_db.pre_process.pre_process_generative_ai_detail") as mock_detail, \
         patch("spreadsheet_to_page_in_db.pre_process.pre_process_generative_ai_batched") as mock_batched:

        # `side_effect` を使って呼び出しごとに異なる戻り値を設定
        mock_detail.side_effect = detail_side_effects
        mock_batched.side_effect = batch_side_effects

        # 実行
        processed_df = batch_process_dataframe(df, "content", batch_size=2)

        # 先頭行は pre_process_generative_ai_detail で処理される
        mock_detail.assert_has_calls([("First row content",), ("Forth row content",)])

        # 2,3行目はバッチ処理で処理される
        mock_batched.assert_called()

    # 結果検証
    assert processed_df.at[0, "content"] == "Detail Processed First row"
    assert processed_df.at[1, "content"] == "変換済み: Second row content"
    assert processed_df.at[2, "content"] == "変換済み: Third row content"
    assert processed_df.at[3, "content"] == "Detail Processed Fourth row"


def test_pre_process_csv(requests_mock):
  """
  requests_mock は pytest-requests-mock プラグイン等を使う例です。
  もし標準 unittest.mock.patch で requests.post をモックにする場合は下記のように書き換えて下さい。
  """

  # ダミーのレスポンスを用意
  mock_json = {
    "results": [
      {
        "properties": {
          "Column": {"title": [{"text": {"content": "Score"}}]},
          "Type": {"select": {"name": "int"}},
          "AI": {"checkbox": False}
        }
      },
      {
        "properties": {
          "Column": {"title": [{"text": {"content": "Note"}}]},
          "Type": {"select": {"name": "callout"}},
          "AI": {"checkbox": False}
        }
      }
    ]
  }

  # requests_mock でエンドポイントをモック
  requests_mock.post("https://api.notion.com/v1/databases/TEST_DB_ID/query", json=mock_json, status_code=200)

  headers = {"Authorization": "Bearer TEST"}
  df = pd.DataFrame({
    "Score": ["10", "20", "invalid"],
    "Note": ["some text", "more text", "final text"],
    "UnrelatedColumn": ["x", "y", "z"]
  })

  processed = pre_process_csv(
    database_id="TEST_DB_ID",
    headers=headers,
    df=df,
    pre_process_message="none"  # "全体" にすると AI 変換が他列にも波及する例
  )

  # Score は int に変換される (invalid -> 0)
  assert list(processed["Score"]) == [10, 20, 0]
  # Note は callout -> "> [!⭐] some text" 等に変換されたあと、AI が有効なので "MOCK AI OUTPUT"
  print(list(processed["Note"]))
  assert list(processed["Note"]) == ["> [!⭐] some text", "> [!⭐] more text", "> [!⭐] final text"] #"MOCK AI OUTPUT", "MOCK AI OUTPUT", "MOCK AI OUTPUT"]
  # UnrelatedColumn は何も指定されていないのでそのまま
  assert list(processed["UnrelatedColumn"]) == ["x", "y", "z"]
