# test_parser.py
import pytest
from spreadsheet_to_page_in_db.parse import (
  inline_text_to_rich_text,
  parse_blocks,
  parse_any_one_block,
)


class TestInlineTextToRichText:
  def test_empty_string(self):
    """空文字列を渡した場合は空リストが返ることをテスト"""
    result = inline_text_to_rich_text("")
    assert result == []

  def test_plain_text(self):
    """単純なテキストのみのケース"""
    text = "Hello world"
    result = inline_text_to_rich_text(text)
    assert len(result) == 1
    assert result[0]["type"] == "text"
    assert result[0]["text"]["content"] == "Hello world"
    assert result[0]["annotations"]["bold"] == False
    assert result[0]["annotations"]["italic"] == False
    assert result[0]["annotations"]["underline"] == False
    assert result[0]["annotations"]["strikethrough"] == False

  def test_bold_text(self):
    """太字を含むマークダウン風テキストを渡した場合"""
    text = "**Hello** world"
    result = inline_text_to_rich_text(text)
    # 結果例：
    # [
    #   {
    #       "type": "text",
    #       "text": {"content": "Hello", "link": None},
    #       "annotations": {"bold": True, "italic": False, ...},
    #       ...
    #   },
    #   {
    #       "type": "text",
    #       "text": {"content": " world", "link": None},
    #       "annotations": {"bold": False, "italic": False, ...},
    #       ...
    #   }
    # ]
    assert len(result) == 2
    assert result[0]["annotations"]["bold"] == True
    assert result[1]["annotations"]["bold"] == False

  def test_code_inline(self):
    """インラインコードを含むテキスト"""
    text = "Here is `code` snippet."
    result = inline_text_to_rich_text(text)
    # code_inline 部分は "type":"text", annotations.code=True になる
    assert len(result) == 3
    assert result[1]["annotations"]["code"] == True
    assert result[1]["text"]["content"] == "code"


class TestParseBlocks:
  def test_single_heading(self):
    """見出しのみの Markdown"""
    md_text = "# Heading 1"
    blocks = parse_blocks(md_text)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "heading_1"
    heading_content = blocks[0]["heading_1"]["rich_text"]
    assert len(heading_content) == 1
    assert heading_content[0]["type"] == "text"
    assert heading_content[0]["text"]["content"] == "Heading 1"

  def test_paragraph_and_hr(self):
    """段落と区切り線が混在するケース"""
    md_text = """Hello world

---
"""
    blocks = parse_blocks(md_text)
    # 段落と divider (hr) が一つずつ
    assert len(blocks) == 2
    assert blocks[0]["type"] == "paragraph"
    assert blocks[1]["type"] == "divider"

  def test_bullet_list(self):
    """箇条書きを含むケース"""
    md_text = """- item1
- item2
- item3
"""
    blocks = parse_blocks(md_text)
    # bullet_list_open → list_item_open → ...
    # parse_bulleted_list では複数のブロックが返る可能性がある
    # Notion API では bulleted_list_item が並ぶイメージになる
    assert len(blocks) == 3
    for b in blocks:
      assert b["type"] == "bulleted_list_item"
      assert "rich_text" in b["bulleted_list_item"]

  def test_blockquote_and_callout(self):
    """引用ブロック / callout を含むケース"""
    # [!🔔] 形式を含む
    md_text = """> [!🔔] This is callout
> 
> Quote line
"""
    blocks = parse_blocks(md_text)
    # blockquote_open → parse_blockquote
    # → callout or quote に分岐
    # md_text は1つの blockquote に2行入れているイメージ
    assert len(blocks) == 1
    assert blocks[0]["type"] in ("callout", "quote"), "呼び出し結果がcallout or quoteになっているか"
    if blocks[0]["type"] == "callout":
      # icon や rich_text をチェック
      assert blocks[0]["icon"] == {"emoji": "🔔"}
      callout_text = blocks[0]["callout"]["rich_text"]
      # "This is callout\n\nQuote line\n" としてパースされる可能性あり
      # あるいは children に quote が入る実装の場合もあるので
      # 実装に合わせてチェックを書き換えてください
      assert len(callout_text) > 0
    else:
      quote_text = blocks[0]["quote"]["rich_text"]
      assert len(quote_text) > 0

  def test_ordered_list(self):
    """番号付きリストを含むケース"""
    md_text = """1. itemA
2. itemB
3. itemC
"""
    blocks = parse_blocks(md_text)
    # ordered_list_item が3つ
    assert len(blocks) == 3
    for i, block in enumerate(blocks, start=1):
      assert block["type"] == "ordered_list_item"
      text_list = block["ordered_list_item"]["rich_text"]
      assert len(text_list) == 1
      expected = f"item{chr(ord('A') + i - 1)}"  # itemA, itemB, itemC
      assert text_list[0]["text"]["content"] == expected

  def test_table(self):
    """テーブルを含むケース(簡易)"""
    md_text = """
| Col1 | Col2 |
|------|------|
| R1C1 | R1C2 |
| R2C1 | R2C2 |
"""
    blocks = parse_blocks(md_text)
    assert len(blocks) == 1
    table_block = blocks[0]
    assert table_block["type"] == "table"
    table_data = table_block["table"]
    # カラムヘッダーが有効か
    assert table_data["has_column_header"] == True
    # 行データが入っているか
    assert len(table_data["children"]) == 1 + 2  # ヘッダー行 + 2 行
    # 先頭がヘッダー行、次がR1,次がR2 などのテスト

  def test_math_block(self):
    """数式ブロックのみのテスト"""
    md_text = """$$
E = mc^2
$$
"""
    blocks = parse_blocks(md_text)
    # math_block → parse_equation
    assert len(blocks) == 1
    assert blocks[0]["type"] == "equation"
    # 何を返すかは parse_equation の実装次第
    # とりあえず expression を保持しているかどうかをチェック
    assert "equation" in blocks[0]
    # 実装では expression に tokens[index] をそのまま入れているが
    # 必要に応じて修正（blocks[0]["equation"]["expression"] が "E = mc^2" かどうか etc.）


# parse_any_one_block のテスト例 (細かく検証する場合)
class TestParseAnyOneBlock:
  def test_return_none_for_unknown(self):
    """未知のトークンタイプの場合に None, index+1 が返るか"""
    tokens = [
        # tokenのダミー
        type("DummyToken", (), {"type": "unknown_token"})
    ]
    block, new_index = parse_any_one_block(tokens, 0)
    assert block is None
    assert new_index == 1

