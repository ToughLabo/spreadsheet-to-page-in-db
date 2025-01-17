

# block 数式, inline 数式の場合には分ける必要がある。
# 出力は {'type': 'text' or 'inline_math' or 'block_math', 'content': '...'}
def separate_equation(text, is_debag=False):
  """
  Parse a given text into a list of dictionaries representing:
  text, inline_math, block_math, bold.
  Furthermore, put half-width spaces before and after inline math.
  """
  # まとめてキャプチャする正規表現
  # \begin ~ \end, インライン数式（$...$）, ボールド（**...**）, イタリック (*...*), 下線(<ins>...</ins>)の順でまとめて
  pattern = re.compile(
    r'(\\begin\{align\*\}.*?\\end\{align\*\}|\$.*?\$|\*\*.*?\*\*|\*.*?\*|<ins>.*?</ins>)',
    flags=re.DOTALL
  )

  # split すると、パターンにマッチしなかった区切り文字列と
  # マッチした文字列が交互にリストに現れる
  # 例: ["ここはマッチ外", "($...$ にマッチした文字列)", "次もマッチ外", ...]
  split_texts = pattern.split(text)
  
  # パターンに実際マッチした部分を取り出す（split_texts と交互に対応する）
  matches = pattern.findall(text)
  if(is_debag):
    print(f"split_texts:{split_texts}")
    print(f"matches: {matches}")
  results = []
  # split_texts と matches は交互に出てくるイメージ
  # たとえば split_texts = [  マッチしない文字列, マッチ文字列, マッチしない文字列, マッチ文字列, ... ]
  #            matches =     [              マッチ文字列,             マッチ文字列, ... ]
  # インデックスをうまく歩きながら順番通り組み立てる
  match_index = 0
  next_continue_flag = False
  
  for index, chunk in enumerate(split_texts):
    # chunk: パターンにマッチしなかった部分
    if chunk not in matches:
      if next_continue_flag:
        next_continue_flag = False
        continue
      # 改行オンリーの場合や改行が複数に渡る場合を処理
      # 1) 連続する改行 (\n+) を一つの改行にまとめる
      collapsed_chunk = re.sub(r'\n+', '\n', chunk)

      # 2) 結果が改行のみ ("\n") か空("") の場合はスキップ
      #    strip() で空になる場合（スペース含む）も同様にスキップ
      # if collapsed_chunk.strip() in ["",r'\n']:
      #   continue
      # スペースを入れる処理
      if len(results)>0 and (results[len(results)-1]["type"] == "inline_math") and (not (collapsed_chunk.startswith(",") and collapsed_chunk.startswith("，") and collapsed_chunk.startswith("、"))):
        spaced_chunk = f" {collapsed_chunk}"
        results.append({"type": "text", "content": spaced_chunk})
      else:
        results.append({"type": "text", "content": collapsed_chunk})
    else:
      # マッチ文字列（= inline/block/boldなど）があれば対応させる
      if match_index < len(matches):
        
        matched_str = matches[match_index]

        # \begin{...} ~ \end{...} 形式のブロック数式
        if matched_str.startswith("\\begin") and matched_str.endswith("\\end{align*}"):
          # 前後の改行を削除する処理（必要に応じてコメントアウト可）
          # -- 前の改行を削除 --
          if len(results) > 0 and results[-1]["type"] in ["text", "bold"]:
            # 末尾が改行で終わっていたら削る (複数の場合にも対応)
            trimmed = re.sub(r'(\n+)$', '', results[-1]["content"])
            if not trimmed:
              results[-1]["content"] = trimmed
            else:
              results.pop()
          # -- 後の改行を削除 --
          #   split_texts[index+1] に次のテキストがあれば改行を削る
          #   ただし次がマッチ文字列でないか等、存在確認を慎重に行う
          if (index + 1) < len(split_texts):
            next_chunk = split_texts[index + 1]
            if next_chunk not in matches:
              # 複数改行を削り一つにまとめる・あるいはなくす
              next_chunk_collapsed = re.sub(r'^(\n+)', '', next_chunk)
              if not next_chunk:
                split_texts[index + 1] = next_chunk_collapsed
              else:
                next_continue_flag = True
          # 数式ブロックの追加
          results.append({"type": "block_math", "content": matched_str})

        # $...$ で囲まれたインライン数式
        elif matched_str.startswith("$") and matched_str.endswith("$"):
          # 中身を抜き出す
          content = matched_str[1:-1].strip()
          # 空白の挿入
          if len(results)>0 and (results[len(results)-1]["type"] == "text" or results[len(results)-1]["type"] == "bold"):
            last_result = results.pop()
            last_content = last_result["content"]
            last_content_spaced = f"{last_content} "
            results.append({"type": "text", "content": last_content_spaced})
          results.append({"type": "inline_math", "content": content})

        # **...** で囲まれたボールド
        elif matched_str.startswith("**") and matched_str.endswith("**"):
          content = matched_str[2:-2].strip()
          results.append({"type": "bold", "content": content})
        # *...* で囲まれたイタリック
        elif matched_str.startswith("*") and matched_str.endswith("*"):
          content = matched_str[1:-1].strip()
          results.append({"type":"italic", "content":content})
        # <ins>...</ins> で囲まれた下線
        elif matched_str.startswith("<ins>") and matched_str.endswith("</ins>"):
          content = matched_str[5:-6].strip()
          results.append({"type":"underline", "content":content})

        match_index += 1

  return results

# 太字や数式などが処理されたブロックの集まりを作る関数
def create_parsed_blocks(text, is_rich_text = False, is_bold = False, is_debag = False):
  block_templates = {}
  text_templates_json = {}
  rich_text = []
  blocks = []
  with open("const/json/math/paragraph.json", 'r', encoding='utf-8') as file:
    data = json.load(file)
    block_templates["paragraph"] = deepcopy(data)
  with open("const/json/math/block_eq.json", 'r', encoding='utf-8') as file:
    data = json.load(file)
    block_templates["block_eq"] = deepcopy(data)
  with open("const/json/math/normal_text.json", 'r', encoding='utf-8') as file:
    data = json.load(file)
    text_templates_json["normal_text"] = deepcopy(data)
  with open("const/json/math/bold_text.json", 'r', encoding='utf-8') as file:
    data = json.load(file)
    text_templates_json["bold_text"] = deepcopy(data)
  with open("const/json/math/inline_eq_text.json", 'r', encoding='utf-8') as file:
    data = json.load(file)
    text_templates_json["inline_eq_text"] = deepcopy(data)
  # text の　parse
  separated_text = separate_equation(text, is_debag=is_debag)
  if(is_bold):
    for index, part in enumerate(separated_text):
      if part["type"] == 'text':
        separated_text[index]["type"] = 'bold'
  # メインの処理。例題のタイトルだけ例外的に処理
  if(is_rich_text):
    for part in separated_text:
      if part["type"] == 'text':
        normal_text_json = deepcopy(text_templates_json["normal_text"])
        normal_text_json["text"]["content"] = part["content"]
        normal_text_json["plain_text"] = part["content"]
        rich_text.append(normal_text_json)
      elif part["type"] == 'bold':
        bold_text_json = deepcopy(text_templates_json["bold_text"])
        bold_text_json["text"]["content"] = part["content"]
        bold_text_json["plain_text"] = part["content"]
        rich_text.append(bold_text_json)
      else:
        inline_eq_text_json = deepcopy(text_templates_json["inline_eq_text"])
        inline_eq_text_json["equation"]["expression"] = part["content"]
        inline_eq_text_json["plain_text"] = part["content"]
        rich_text.append(inline_eq_text_json)
    return rich_text
  else:
    for part in separated_text:
      if part["type"] == 'text':
        normal_text_json = deepcopy(text_templates_json["normal_text"])
        normal_text_json["text"]["content"] = part["content"]
        normal_text_json["plain_text"] = part["content"]
        rich_text.append(normal_text_json)
      elif part["type"] == 'bold':
        bold_text_json = deepcopy(text_templates_json["bold_text"])
        bold_text_json["text"]["content"] = part["content"]
        bold_text_json["plain_text"] = part["content"]
        rich_text.append(bold_text_json)
      elif part["type"] == 'inline_math':
        inline_eq_text_json = deepcopy(text_templates_json["inline_eq_text"])
        inline_eq_text_json["equation"]["expression"] = part["content"]
        inline_eq_text_json["plain_text"] = part["content"]
        rich_text.append(inline_eq_text_json)
      else:
        if rich_text != []:
          paragraph_block_json = deepcopy(block_templates["paragraph"])
          paragraph_block_json["paragraph"]["rich_text"] = rich_text
          blocks.append(paragraph_block_json)
          rich_text = []
        block_eq_json = deepcopy(block_templates["block_eq"])
        block_eq_json["equation"]["expression"] = part["content"]
        blocks.append(block_eq_json)
    if rich_text != []:
      paragraph_block_json = deepcopy(block_templates["paragraph"])
      paragraph_block_json["paragraph"]["rich_text"] = rich_text
      blocks.append(paragraph_block_json)
  return blocks
