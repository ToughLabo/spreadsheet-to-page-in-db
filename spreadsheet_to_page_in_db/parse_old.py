import re
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.amsmath import amsmath_plugin
from pprint import pprint

# TODO:下線判定を後から実装する。
# 数式ブロックは inline には想定していない
# inline text から rich text へ
def inline_text_to_rich_text(inline_text: str):
  # parser の初期化
  md = MarkdownIt("gfm-like").use(dollarmath_plugin, allow_space=True, double_inline=True)
  tokens = md.parse(inline_text)
  # rich_text を格納する
  rich_text_array = []
  # annotation
  bold = False
  italic = False
  strikethrough = False
  underline = False
  link_url = None
  # parser の仕様上必ず 1 paragraph として処理されることに注意。
  for token in tokens[1].children:
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
        },
        "plain_text": content,
        "href": None
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
        },
        "plain_text": content,
        "href": link_url
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
        },
        "plain_text": content,
        "href": link_url
      })

  return rich_text_array

# TODO:箇条書きに関してもう少し考える
# ブロック単位の分割
def parse_markdown_to_blocks(text: str):
  """
  markdown-it-py + amsmath_plugin + dollarmath_plugin を使用して
  Markdown をブロック単位でパースするサンプルコード。
  
  以下のブロックに対応：
    - Heading (#, ##, ### など)
    - Paragraph
    - Bullet List / Ordered List
    - Blockquote (引用)
    - Callout (簡易的実装：blockquote 内の先頭行が [!xxxx] の場合を想定)
    - Divider (hr)
    - Image
    - Table
    - 数式 (amsmath/dollarmath):
        * ブロック数式（$$ ... $$ や \begin{aligned} ... \end{aligned} など）
        * インライン数式（$ ... $）

  ※ 実際の Markdown 記法やプラグインでのパース結果によっては、
    全てのケースを完璧に網羅しない可能性があります。
  """

  md = (
    MarkdownIt("gfm-like")
    .use(amsmath_plugin)    # \\begin{aligned} ... \\end{aligned} 等
    .use(dollarmath_plugin, allow_space=True, double_inline=True) # $...$, $$...$$ の数式
  )

  tokens = md.parse(text)
  blocks = []
  i = 0

  while i < len(tokens):
    t = tokens[i]

    #---------------------------
    # 1) Heading (#, ##, ### ...)
    #---------------------------
    if t.type == "heading_open":
      level = int(t.tag[-1])  # 'h1' -> 1, 'h2'->2, ...
      heading_text = ""
      j = i + 1
      while j < len(tokens):
        if tokens[j].type == "inline":
          heading_text = tokens[j].content
        if tokens[j].type == "heading_close":
          break
        j += 1
      blocks.append({
        "type": f"heading_{level}",
        f"heading_{level}": {
          "rich_text": inline_text_to_rich_text(heading_text)
        },
        "color": "default",
        "is_toggleable": False
      })
      i = j + 1
      continue

    #---------------------------
    # 2) Horizontal rule (Divider)
    #---------------------------
    if t.type == "hr":
      blocks.append({
        "type": "divider",
        "divider": {}
      })
      i += 1
      continue

    #---------------------------
    # 3) Blockquote (引用, Callout)
    #---------------------------
    if t.type == "blockquote_open":
      # blockquote_close が来るまでを一つの塊とする
      content_lines = []
      j = i + 1
      while j < len(tokens) and tokens[j].type != "blockquote_close":
        if tokens[j].type == "paragraph_open":
          # 段落全体を拾う
          p_text = ""
          k = j + 1
          while k < len(tokens) and tokens[k].type != "paragraph_close":
            if tokens[k].type == "inline":
              p_text += tokens[k].content + "\n"
            k += 1
          content_lines.append(p_text.strip())
          j = k
        j += 1
      blockquote_text = "\n".join(x for x in content_lines if x).strip()

      # TODO:emojiに関する処理を改善する。
      # 今は[!★]のような形式を前提としている。
      # Callout かどうかを簡易判定：[!X] で始まれば callout とみなす
      first_line = blockquote_text.split("\n", 1)[0]
      if first_line.startswith("[!"):
        # Callout
        blocks.append({
          "type": "callout",
          "callout":{
            "rich_text": inline_text_to_rich_text(blockquote_text[4:])
          },
          "icon": {
            "emoji": blockquote_text[2]
          },
          "color": "default"
        })
      else:
        # 通常の blockquote
        blocks.append({
          "type": "quote",
          "quote": {
            "rich_text": inline_text_to_rich_text(blockquote_text)
          },
          "color": "default"
        })

      i = j + 1
      continue

    #---------------------------
    # 4) Bullet / Ordered List
    #---------------------------
    #   list_item_open の直前に "bullet_list_open" or "ordered_list_open" がある
    #   list_item には 1 paragraph のみ入ることを仮定
    #---------------------------
    def recursive_list_child(tokens, index, type=None):
      children = []
      child_type = tokens[index].type
      index += 1
      if child_type == "paragraph_open":
        paragraph_text = inline_text_to_rich_text(tokens[index])
        index += 2
        return {"type": "paragraph", "paragraph": {"rich_text": paragraph_text}}, index
      elif child_type == ("math_block" or "amsmath") :
        expression = tokens[index]
        index += 2
        return {"type": "equation", "equation": {"expression": expression}}, index
      elif child_type == "table_open":
        # table_close までを一つのテーブルとみなす
        header = []
        rows = []
        j = i + 1
        row_data = []
        has_column_header = False
        table_width = 1
        table_rows = []
        cells = []
        while j < len(tokens) and tokens[j].type != "table_close":
          if tokens[j].type == "tr_open":
            row_data = []
            j += 1
          elif tokens[j].type == "td_open":
            # 次の inline を探す
            cell_text = ""
            k = j + 1
            while k < len(tokens) and tokens[k].type != "td_close":
              if tokens[k].type == "inline":
                cell_text += tokens[k].content
              k += 1
            row_data.append(cell_text.strip())
            j = k + 1
          elif tokens[j].type == "tr_close":
            rows.append(row_data)
            j += 1
          elif tokens[j].type == "thead_open":
            # ヘッダー行の処理
            while tokens[j].type != "thead_close":
              if tokens[j].type == "th_open":
                cell_text = ""
                k = j + 1
                while k < len(tokens) and tokens[k].type != "th_close":
                  if tokens[k].type == "inline":
                    cell_text += tokens[k].content
                  k += 1
                header.append(cell_text.strip())
                j = k
              j += 1
          else:
            j += 1
        # ヘッダーの設定
        if header:
          has_column_header = True
          table_width = len(header)
        else:
          table_width = len(row_data[0])
        # 各行の処理
        if has_column_header:
          for cell in header:
            cells.append({
              "type": "text",
              "text": {
                "content": cell,
                "link": None
              },
              "plain_text": cell,
              "href": None
            })
          table_rows.append({
          "type": "table_row",
          "table_row": {
            "cells": cells
          }
        })
        cells = []
        for row in rows:
          for cell in row:
            cells.append({
              "type": "text",
              "text": {
                "content": cell,
                "link": None
              },
              "plain_text": cell,
              "href": None
            })
          table_rows.append({
            "type": "table_row",
            "table_row": {
              "cells": cells
            }
          })
          cells = []
        
        index = j + 1
        result = {
          "type": "table",
          "table": {
            "table_width": table_width,
            "has_column_header": has_column_header,
            "has_row_header": False,
            "children": table_rows
          }
        }
        return result, index
      elif child_type == "blockquote_open":
        # blockquote_close が来るまでを一つの塊とする
        content_lines = []
        j = i + 1
        while j < len(tokens) and tokens[j].type != "blockquote_close":
          if tokens[j].type == "paragraph_open":
            # 段落全体を拾う
            p_text = ""
            k = j + 1
            while k < len(tokens) and tokens[k].type != "paragraph_close":
              if tokens[k].type == "inline":
                p_text += tokens[k].content + "\n"
              k += 1
            content_lines.append(p_text.strip())
            j = k
          j += 1
        blockquote_text = "\n".join(x for x in content_lines if x).strip()
        # TODO:emojiに関する処理を改善する。
        # 今は[!★]のような形式を前提としている。
        # Callout かどうかを簡易判定：[!X] で始まれば callout とみなす
        first_line = blockquote_text.split("\n", 1)[0]
        if first_line.startswith("[!"):
          # Callout
          result = ({
            "type": "callout",
            "callout":{
              "rich_text": inline_text_to_rich_text(blockquote_text[4:])
            },
            "icon": {
              "emoji": blockquote_text[2]
            },
            "color": "default"
          })
          index = j + 1
          return result, index
        else:
          # 通常の blockquote
          result = ({
            "type": "quote",
            "quote": {
              "rich_text": inline_text_to_rich_text(blockquote_text)
            },
            "color": "default"
          })
          index = j + 1
          return result, index
      elif child_type == "list_item_open":
        index += 1
        rich_text = inline_text_to_rich_text(tokens[index])
        index += 2
        if tokens[index].type == ("bullet_list_open"):
          index += 1
          children, index = recursive_list_child(tokens, index, "bulleted_list_item")
        elif tokens[index].type == ("ordered_list_open"):
          index += 1
          children, index = recursive_list_child(tokens, index, "numbered_list_item")
        index += 1
        return {"type": type, type: {"rich_text": rich_text, "color":"default", "children": children}}, index
      else:
        print("error: Your Block Type is not supported in list item")
        raise(ValueError)
      
      
    if t.type in ("bullet_list_open", "ordered_list_open"):
      list_type = "bulleted_list_item" if t.type == "bullet_list_open" else "ordered_list_item"
      j = i + 1
      while tokens[j].type not in ("bullet_list_close", "ordered_list_close"):
        children = []
        if tokens[j+1].type == "list_item_close":
          k = j - 1
          rich_text = []
        else:
          k = j + 2
          rich_text = inline_text_to_rich_text(tokens[k])
        k += 2 
        # index は list_item_close の位置で帰ってくる
        if tokens[k].type == "bullet_list_open":
          children, k = recursive_list_child(tokens, k + 1, "bulleted_list_item")
        elif token[k].type == "ordered_list_open":
          children, k = recursive_list_child(tokens, k + 1, "numbered_list_item")
        blocks.append({"type":list_type, "rich_text": rich_text, "color": "default", "children": children})
        j = k + 1
      continue

    #---------------------------
    # 5) Table 列ヘッダーのみに対応。行ヘッダーがは未実装
    #---------------------------
    if t.type == "table_open":
      # table_close までを一つのテーブルとみなす
      header = []
      rows = []
      j = i + 1
      row_data = []
      has_column_header = False
      table_width = 1
      table_rows = []
      cells = []
      while j < len(tokens) and tokens[j].type != "table_close":
        print(f"tokens[j]:{tokens[j]}")
        if tokens[j].type == "tr_open":
          row_data = []
          j += 1
        elif tokens[j].type == "td_open":
          # 次の inline を探す
          cell_text = ""
          k = j + 1
          while k < len(tokens) and tokens[k].type != "td_close":
            if tokens[k].type == "inline":
              cell_text += tokens[k].content
            k += 1
          row_data.append(cell_text.strip())
          j = k + 1
        elif tokens[j].type == "tr_close":
          rows.append(row_data)
          j += 1
        elif tokens[j].type == "thead_open":
          # ヘッダー行の処理
          while tokens[j].type != "thead_close":
            if tokens[j].type == "th_open":
              cell_text = ""
              k = j + 1
              while k < len(tokens) and tokens[k].type != "th_close":
                if tokens[k].type == "inline":
                  cell_text += tokens[k].content
                k += 1
              header.append(cell_text.strip())
              j = k
            j += 1
        else:
          j += 1
      # ヘッダーの設定
      if header:
        has_column_header = True
        table_width = len(header)
      else:
        table_width = len(row_data[0])
      # 各行の処理
      if has_column_header:
        for cell in header:
          cells.append({
            "type": "text",
            "text": {
              "content": cell,
              "link": None
            },
            "plain_text": cell,
            "href": None
          })
        table_rows.append({
        "type": "table_row",
        "table_row": {
          "cells": cells
        }
      })
      cells = []
      for row in rows:
        for cell in row:
          cells.append({
            "type": "text",
            "text": {
              "content": cell,
              "link": None
            },
            "plain_text": cell,
            "href": None
          })
        table_rows.append({
          "type": "table_row",
          "table_row": {
            "cells": cells
          }
        })
        cells = []
      blocks.append({
        "type": "table",
        "table": {
          "table_width": table_width,
          "has_column_header": has_column_header,
          "has_row_header": False,
          "children": table_rows
        }
      })
      i = j + 1
      continue

    #---------------------------
    # 6) Image TODO: ここはまだ Unavaliable
    #---------------------------
    #   inline の子トークンに "image" が出るケースもあるが、
    #   ブロック的にはパラグラフ扱いになる場合も。
    #   ここでは単独で <img> 相当の token を見つけた場合を想定
    #---------------------------
    # if t.type == "inline":
    #   # inline.children の中に image token があるかどうか
    #   if t.children:
    #     # 複数の child の中に image があるかチェック
    #     for child in t.children:
    #       if child.type == "image":
    #         blocks.append({
    #           "type": "image",
    #           "src": child.attrs.get("src", ""),
    #           "alt": child.content,
    #           "title": child.attrs.get("title", "")
    #         })
    #   # 他の inline は paragraph で処理する可能性があるのでスルー
    #   i += 1
    #   continue

    #---------------------------
    # 7) 数式（amsmath / dollarmath）
    #---------------------------
    #   これらのプラグインでは、
    #   - "math_block" (ブロック数式)
    #   - "math_inline" (インライン数式)
    #   といった token.type が挿入される
    #---------------------------
    if t.type == "math_block" or t.type == "amsmath":
      blocks.append({
        "type": "equation",
        "equation": {
          "expression": t.content.strip()
        }
      })
      i += 1
      continue

    #---------------------------
    # 8) Paragraph (その他テキスト)
    #---------------------------
    if t.type == "paragraph_open":
      paragraph_text = ""
      j = i + 1
      while j < len(tokens) and tokens[j].type != "paragraph_close":
        if tokens[j].type == "inline":
          paragraph_text += tokens[j].content + "\n"
        j += 1
      blocks.append({
        "type": "paragraph",
        "paragraph": {
          "rich_text": inline_text_to_rich_text(paragraph_text.strip())
        },
        "color": "default" 
      })
      i = j + 1
      continue

    # 何でもなければ次へ
    i += 1

  return blocks


if __name__ == "__main__":
  sample = r"""
# 見出し

これは段落です。  
- 箇条書きアイテム1
  - 箇条書きアイテム 1-1
  - 箇条書きアイテム 1-2
- 箇条書きアイテム2

> [!★] これは callout の例


テーブル例：

| A列 | B列 |
|-----|-----|
| 1   | 2   |
| 3   | 4   |



___


画像とインライン数式：
https://example.com/image.png
$E=mc^2$

ブロック数式：

$$
\begin{aligned}
  x^2 + 1 &= 0 \\
  y &= \frac{1}{2}
\end{aligned}
$$
"""

  # blocks_parsed = parse_markdown_to_blocks(sample)
  # for b in blocks_parsed:
  #   print(b)


  md = MarkdownIt("gfm-like").use(dollarmath_plugin, allow_space=True, double_inline=True).use(amsmath_plugin)
  text = r"""
  ## $1$：次の分数関数の定義域と値域を求めなさい。

  $$
  \begin{align*} &(1) \enspace y = \frac{2}{x-1} + 3 \\ &(2) \enspace y = \frac{-1}{x+2} - 1 \\ &(3) \enspace y = \frac{3}{x} + 2 \end{align*} 
  $$

  $2$：次の問いに答えなさい。

  \begin{align*} &(1) \enspace 分数関数 $y = \frac{1}{x}$ のグラフを描きなさい。（漸近線も書き込むこと） \\ &(2) \enspace (1)のグラフをもとに、分数関数 $y = \frac{1}{x-2} + 1$ のグラフを描きなさい。（漸近線も書き込むこと） \\ &(3) \enspace (2)のグラフから、この関数の定義域と値域を求めなさい。 \end{align*}

  $3$：次の分数関数のグラフの漸近線を求めなさい。

  \begin{align*} &(1) \enspace y = \frac{4}{x-3} + 5 \\ &(2) \enspace y = \frac{-2}{x+1} - 2 \\ &(3) \enspace y = \frac{1}{x} - 3 \end{align*} 

  $4$：分数関数 $y = \frac{k}{x-p} + q$ のグラフは、関数 $y = \frac{k}{x}$ のグラフをどのように平行移動したものか答えなさい。

  （注：平行移動とは、グラフの形を変えずに、グラフ全体をある方向にずらすことです。）

  *   **定義域と値域は関数の基本！グラフをイメージして考えよう！**
      *   分数関数 $y = \frac{k}{x-p} + q$  の定義域は、「**分母が $0$ にならない**」という条件から求められる。
          *   **分母**：$x-p$
          *   $x-p$ が $0$ になると、計算できなくなっちゃう（**数学では$0$で割ることはできない**）。
          *   だから、$x-p \neq 0$、つまり、$x \neq p$ が定義域になる。
      *   値域は、与えられた関数を$x$について解くことで求められる。
          *   $x =$ の形に変形する。
          *   その際、分母に$y$の式が出てくるので、その分母が$0$にならない条件から、$y \neq q$ が値域になる。
      *   **定義域**：関数のグラフを書くときに、$x$ に入れて良い値の範囲のこと。
      *  **値域**：関数のグラフを書いたときに、$y$ がとる値の範囲のこと。
      *   分数関数の定義域と値域は、グラフの**漸近線**（だんだん近づいていくけど、決して交わらない線のこと）と関係がある。
          *   **漸近線**は、$x = p$ と $y = q$ の２つ。
          *   定義域と値域を考える上で、**漸近線が重要なヒント**になることを覚えておこう！
          
  1. 分数方程式を解く際に、分母が $0$ になる場合は解として認められないことに注意する。この問題では、$x=2$ が解にならないことを常に確認する必要がある。
      1. 箇条書き１
        箇条書き２
  2. 与えられた方程式 $\frac{x-5}{x-2} = 3x+k$ は、変形すると $(x-5) = (3x+k)(x-2)$ となる。ただし、$x \neq 2$。
  3. 上記の式を展開して整理すると、$3x^2 + (k-7)x - 2k + 5 = 0$ という $x$ の $2$ 次方程式が得られる。この $2$ 次方程式の解が元の分数方程式の解の候補となる。
  4.  ここで、$x=2$ が解にならないための条件を確認する。 $x=2$ を元の $2$ 次方程式に代入すると、$12 + 2(k-7) - 2k + 5 = 12 + 2k - 14 - 2k + 5 = 3 \neq 0$ となり、$x=2$ はこの $2$ 次方程式の解ではないことがわかる。したがって、この $2$ 次方程式の解はすべて元の分数方程式の解の候補となりえる。
  5. $2$ 次方程式の実数解の個数は判別式 $D = (k-7)^2 - 4 \cdot 3 \cdot (-2k+5)$ の符号によって決まる。
      $(1)$ $D > 0$ のとき、異なる $2$ つの実数解をもつ。
      $(2)$ $D = 0$ のとき、重解（$1$つの実数解）をもつ。
      $(3)$ $D < 0$ のとき、実数解をもたない。
  6. 判別式 $D$ を計算すると、$D = k^2 - 14k + 49 + 24k - 60 = k^2 + 10k - 11$ となる。
  7. 判別式 $D = k^2 + 10k - 11$ の符号を調べるために、$D=0$ となる $k$ の値を求めると、$k^2 + 10k - 11 = (k+11)(k-1) = 0$ より、$k=-11, 1$。
  8. したがって、$k$ の値によって実数解の個数は以下のようになる。
      $(1)$ $k < -11$ または $1 < k$ のとき、$D > 0$ となり、$2$ つの実数解をもつ。
      $(2)$ $k = -11$ または $k = 1$ のとき、$D = 0$ となり、$1$ つの実数解をもつ。
      $(3)$ $-11 < k < 1$ のとき、$D < 0$ となり、実数解をもたない。
      
  テーブル例：

  | A列 | B列 |
  |-----|-----|
  | 1   | 2   |
  | 3   | 4   |



  """
  input_text = r"""
  与えられた方程式 $\frac{x-5}{x-2} = 3x+k$ は、変形すると $(x-5) = (3x+k)(x-2)$ となる。ただし、$x \neq 2$。
  https://example.com/image.png [画像2](https://example.com/image2.png)
  テーブル例：

  | A列 | B列 |
  |-----|-----|
  | 1   | 2   |
  | 3   | 4   |
  
  > [!★] quote
  > - bullet
  ------
  
  - 箇条書きアイテム1
    これは段落です。
      - ふぁｄふぁ
  
  
  to- 箇条書きアイテム 1-1
    箇条書きアイテム 1-2
  - 箇条書きアイテム2
    箇条書きアイテム3
  1. 箇条書きアイテム4
  """
  # print("rich_token:", inline_text_to_rich_text(input_text))
  tokens = md.parse(input_text)

  for token in tokens:
    print(f"{token.type} ({token.tag}): {token.content}")
    if token.children:
      for child in token.children:
        print(f"  - child:{child}")
        print(f"  - {child.type} ({child.tag}): {child.content}")
  # print(f"blocks:{parse_markdown_to_blocks(input_text)}")
