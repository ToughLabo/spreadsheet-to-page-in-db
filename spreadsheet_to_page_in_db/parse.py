from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
import re
from typing import Any
from mdit_py_plugins.amsmath import amsmath_plugin

# TODO: 下線判定を後から実装する。（デフォルトで下線にすることは可能）
# TODO: color 判定はできない。
# 数式ブロックは inline には想定していない
# inline text から rich text へ
def inline_text_to_rich_text(inline_text: str, is_bold=False, is_italic=False, is_underline=False, is_strikethrough=False) -> list[dict[str,Any]]:
  # 空の場合を先に処理
  if not inline_text :
    return []
  # parser の初期化
  md = MarkdownIt("gfm-like").use(dollarmath_plugin, allow_space=True, double_inline=True)
  tokens = md.parse(inline_text)
  # 空文字を取り除く
  tokens = [token for token in tokens[1].children if not (token.type == "text" and token.content == "")]
  # rich_text を格納する
  rich_text_array = []
  # annotation
  bold = is_bold
  italic = is_italic
  strikethrough = is_strikethrough
  underline = is_underline
  link_url = None
  # parser の仕様上必ず 1 paragraph として処理されることに注意。
  for token in tokens:
    if token.type == "s_open":
      strikethrough = True
      continue
    if token.type == "s_close":
      strikethrough = False
      continue
    if token.type == "strong_open":
      bold = True
      continue
    if token.type == "strong_close":
      bold = False
      continue
    if token.type == "em_open":
      italic = True
      continue
    if token.type == "em_close":
      italic = False
      continue
    if token.type == "link_open":
      link_url = token.attrs["href"]
    if token.type == "link_close":
      link_url = None
    if token.type == "code_inline":
      # code_inline は一発で text を作る
      content = token.content
      rich_text_array.append({
        "type": "text",
        "text": { "content": content, "link": None },
        "annotations": {
          "bold": False,
          "italic": False,
          "underline": False,
          "strikethrough": False,
          "code": True,
          "color": "default"
        }
      })
      continue
    if token.type == "math_inline" or token.type == "math_inline_double":
      # math_inline は一発で text を作る
      content = token.content
      rich_text_array.append({
        "type": "equation",
        "equation": { "expression": content },
        "annotations": {
          "bold": bold,
          "italic": italic,
          "underline": underline,
          "strikethrough": strikethrough,
          "code": False,
          "color": "default"
        }
      })
      continue
    if token.type == "text":
      content = token.content
      if link_url:
        link = {"url":link_url}
      else:
        link = None
      # 現在の bold, italic を反映して text を作る
      rich_text_array.append({
        "type": "text",
        "text": { "content": content, "link": link },
        "annotations": {
          "bold": bold,
          "italic": italic,
          "underline": underline,
          "strikethrough": strikethrough,
          "code": False,
          "color": "default"
        }
      })

  return rich_text_array

# ----------------------
# Block の parse. 入力 index は必ずそのブロックの先頭。出力 index は必ずそのブロックの最後尾 + 1 (次のブロックの先頭)
# ----------------------
# heading block を parse
def parse_heading(tokens, index, is_bold=False, is_italic=False, is_underline=False, is_strikethrough=False) -> dict[str,Any]:
  level = int(tokens[index].tag[-1])
  heading_text = ""
  index += 1
  while index < len(tokens):
    if tokens[index].type == "inline":
      heading_text = tokens[index].content
    else:
      break
    index += 1
  block = {
        "type": f"heading_{level}",
        f"heading_{level}": {
          "rich_text": inline_text_to_rich_text(heading_text, is_bold, is_italic, is_underline, is_strikethrough),
          "color": "default",
          "is_toggleable": False
        }
      }
  index += 1
  return block, index

# divider block を parse
def parse_divider(tokens, index) -> dict[str,Any]:
  block = {
    "type": "divider",
    "divider": {}
  }
  index += 1
  return block, index

# TODO: emojiに関する処理を改善する。
# quote or callout block を parse
def parse_blockquote(tokens, index, is_bold=False, is_italic=False, is_underline=False, is_strikethrough=False) -> dict[str,Any]:
  p_text = ""
  children = []
  index += 1
  # 先に この quote block の rich_text を取得
  if tokens[index].type == "paragraph_open":
    index += 1
    while index < len(tokens) and tokens[index].type != "paragraph_close":
      if tokens[index].type == "inline":
        p_text += tokens[index].content + "\n"
      index += 1
    index += 1
  while index < len(tokens) and tokens[index].type != "blockquote_close":
    block, index = parse_any_one_block(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
    if block:
      children.append(block)

  # TODO:emojiに関する処理を改善する。
  # 今は[!★]のような形式を前提としている。
  # Callout かどうかを簡易判定：[!X] で始まれば callout とみなす
  callout_pattern = r"^\[\!(.*?)\]\s*(.*)"
  if p_text.startswith("[!"):
    # Callout
    match = re.search(callout_pattern, p_text)
    block = {
      "type": "callout",
      "callout":{
        "rich_text": inline_text_to_rich_text(match.group(2), is_bold, is_italic, is_underline, is_strikethrough),
        "icon": {
        "emoji": match.group(1)
        },
        "color": "default",
        "children": children
      },
    }
  else:
    # Quote
    block = {
      "type": "quote",
      "quote": {
        "rich_text": inline_text_to_rich_text(p_text, is_bold, is_italic, is_underline, is_strikethrough),
        "color": "default",
        "children": children
      }
    }
  index += 1
  return block, index

# list_item を parse 
def parse_list_item(tokens, index, type, is_bold=False, is_italic=False, is_underline=False, is_strikethrough=False) -> dict[str,Any]:
  list_text = ""
  children = []
  index += 1
  # 先に このリストの rich text を取得
  if tokens[index].type == "paragraph_open":
    index += 1
    while index < len(tokens) and tokens[index].type != "paragraph_close":
      if tokens[index].type == "inline":
        list_text += tokens[index].content + "\n"
      index += 1
    index += 1
  # 再帰的に children を取得
  while index < len(tokens) and tokens[index].type != "list_item_close":
    block, index = parse_any_one_block(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
    if block:
      children.append(block)

  # block を作成 
  block = {
    "type": type,
    type :{
      "rich_text": inline_text_to_rich_text(list_text, is_bold, is_italic, is_underline, is_strikethrough),
      "children": children
    }
  }
  index += 1
  return block, index

  
def parse_bulleted_list(tokens, index, is_bold=False, is_italic=False, is_underline=False, is_strikethrough=False) -> list[dict[str,Any]]:
  index += 1
  blocks = []
  while index < len(tokens) and tokens[index].type != "bullet_list_close":
    if tokens[index].type == "list_item_open":
      item_block, index = parse_list_item(tokens, index, "bulleted_list_item", is_bold, is_italic, is_underline, is_strikethrough)
      blocks.append(item_block)
    else:
      index += 1
  index += 1
  return blocks, index

# numbered_list block を parse
def parse_numbered_list(tokens, index, is_bold=False, is_italic=False, is_underline=False, is_strikethrough=False) -> list[dict[str,Any]]:
  index += 1
  block = []
  while index < len(tokens) and tokens[index].type != "ordered_list_close":
    if tokens[index].type == "list_item_open":
      item_block, index = parse_list_item(tokens, index, "ordered_list_item", is_bold, is_italic, is_underline, is_strikethrough)
      block.append(item_block)
    else:
      index += 1
  index += 1
  return block, index

# table block を parse
def parse_table(tokens, index, is_bold=False, is_italic=False, is_underline=False, is_strikethrough=False) -> dict[str,Any]:
  # table_close までを一つのテーブルとみなす
  header = []
  rows = []
  index += 1
  row_data = []
  has_column_header = False
  table_width = 0
  table_rows = []
  cells = []
  while index < len(tokens) and tokens[index].type != "table_close":
    # 行の開始
    if tokens[index].type == "tr_open":
      row_data = []
      index += 1
    # 各セルの処理
    elif tokens[index].type == "td_open":
      cell_text = ""
      index += 1
      while index < len(tokens) and tokens[index].type != "td_close":
        if tokens[index].type == "inline":
          cell_text += tokens[index].content
        index += 1
      row_data.append(inline_text_to_rich_text(cell_text.strip(), is_bold, is_italic, is_underline, is_strikethrough))
      index += 1
    # 行としてまとめる
    elif tokens[index].type == "tr_close":
      rows.append(row_data)
      index += 1
    # ヘッダー行の処理
    elif tokens[index].type == "thead_open":
      while tokens[index].type != "thead_close":
        if tokens[index].type == "th_open":
          cell_text = ""
          index += 1
          while index < len(tokens) and tokens[index].type != "th_close":
            if tokens[index].type == "inline":
              cell_text += tokens[index].content
            index += 1
          header.append(inline_text_to_rich_text(cell_text.strip(), is_bold, is_italic, is_underline, is_strikethrough))
        index += 1
    # tbody_open/close
    else:
      index += 1
  # ヘッダーの設定
  if header:
    has_column_header = True
    table_width = len(header)
  else:
    table_width = len(rows[0])
  # 各行の処理
  if has_column_header:
    for cell in header:
      cells.append(cell)
    table_rows.append({
    "type": "table_row",
    "table_row": {
      "cells": cells
    }
  })
  cells = []
  for row in rows:
    for cell in row:
      cells.append(cell)
    table_rows.append({
      "type": "table_row",
      "table_row": {
        "cells": cells
      }
    })
    cells = []
  block = {
    "type": "table",
    "table": {
      "table_width": table_width,
      "has_column_header": has_column_header,
      "has_row_header": False,
      "children": table_rows
    }
  }
  index += 1
  return block, index

# TODO: image block を parse
def parse_image(tokens, index) -> dict[str,Any]:
  pass

# equation block を parse
def parse_equation(tokens, index) -> dict[str,Any]:
  expression = tokens[index] 
  block = {
    "type": "equation",
    "equation": {
      "expression": expression.content
    }
  }
  index += 1
  return block, index

# paragraph block を parse
def parse_paragraph(tokens, index, is_bold=False, is_italic=False, is_underline=False, is_strikethrough=False) -> dict[str,Any]:
  paragraph_text = ""
  index += 1
  # 先にこのパラグラフのテキストを処理
  while index < len(tokens) and tokens[index].type != "paragraph_close":
    if tokens[index].type == "inline":
      paragraph_text += tokens[index].content + "\n"
    index += 1
  block = {
    "type": "paragraph",
    "paragraph": {
      "rich_text": inline_text_to_rich_text(paragraph_text, is_bold, is_italic, is_underline, is_strikethrough),
      "color": "default"
    }
  }
  index += 1
  return block, index

# あらゆる 1 ブロックに対応する parse
def parse_any_one_block(tokens, index, is_bold=False, is_italic=False, is_underline=False, is_strikethrough=False) -> dict[str,Any]:
  t = tokens[index]
  if t.type == "heading_open":
    return parse_heading(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
  if t.type == "hr":
    return parse_divider(tokens, index)
  if t.type == "bullet_list_open":
    return parse_bulleted_list(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
  if t.type == "ordered_list_open":
    return parse_numbered_list(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
  if t.type == "blockquote_open":
    return parse_blockquote(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
  if t.type == "table_open":
    return parse_table(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
  if t.type in ("math_block", "amsmath"):
    return parse_equation(tokens, index)
  if t.type == "paragraph_open":
    return parse_paragraph(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
  return None, index + 1

# Markdown 風 text から blocks を作成
def parse_blocks(text, index=0, is_bold=False, is_italic=False, is_underline=False, is_strikethrough=False) -> list[dict[str,Any]]:
  blocks = []
  md = MarkdownIt("gfm-like").use(dollarmath_plugin, allow_space=True, double_inline=True).use(amsmath_plugin)
  tokens = md.parse(text)
  while index < len(tokens):
    t = tokens[index]
    if t.type == "heading_open":
      block, index = parse_heading(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
      blocks.append(block)
    elif t.type == "hr":
      block, index = parse_divider(tokens, index)
      blocks.append(block)
    elif t.type == "bullet_list_open":
      list_blocks, index = parse_bulleted_list(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
      blocks.extend(list_blocks)
    elif t.type == "ordered_list_open":
      list_blocks, index = parse_numbered_list(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
      blocks.extend(list_blocks)
    elif t.type == "blockquote_open":
      block, index = parse_blockquote(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
      blocks.append(block)
    elif t.type == "table_open":
      block, index = parse_table(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
      blocks.append(block)
    elif t.type in ("math_block", "amsmath"):
      block, index = parse_equation(tokens, index)
      blocks.append(block)
    elif t.type == "paragraph_open":
      block, index = parse_paragraph(tokens, index, is_bold, is_italic, is_underline, is_strikethrough)
      blocks.append(block)
    else:
      index += 1
  return blocks