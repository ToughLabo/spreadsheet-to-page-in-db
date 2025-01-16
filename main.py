import requests
from dotenv import load_dotenv
import os
import json
import pandas as pd
import re
from copy import deepcopy
from rich.progress import track

def append_sibling_paragraph_to_page(headers, page_id, block_id, type, new_content):
  url = f"https://api.notion.com/v1/blocks/{page_id}/children"
  payload = {
    "children": [
      {
        type: {
          "rich_text": [
            {
              "text": {
                "content": new_content
              }
            }
          ]
        }
      }
    ],
    "after": block_id
  }
  res = requests.patch(url, headers=headers, data=json.dumps(payload))
  if res.status_code != 200:
    print(f"Error: {res.status_code}")
    print(res.text)
  return res.json()

def append_paragraph_to_toggle(headers, toggle_block_id, text_content):
  """
  既存のトグルブロックに子ブロック（段落）を追加する
  """
  print(f"text_content:{text_content}")
  url = f"https://api.notion.com/v1/blocks/{toggle_block_id}/children"
  # TODO: いい感じに修正が必要　ひとまず上書きではなく、追加するように調整
  payload = {
    "children": [
      {
        "paragraph": {
          "rich_text": [
            {
              "text": {
                "content": text_content
              }
            }
          ]
        }
      }
    ]
  }

  res = requests.patch(url, headers=headers, data=json.dumps(payload))
  if res.status_code == 200:
    print("成功:", res.json())
  else:
    print("失敗:", res.status_code, res.text)

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

# 問題文処理用
# [{title: "", problem: ""}, ,,,] の形式で返す。
# 先頭と末尾の空行を削除してからresultsに追加する処理
def flush_chunk(current_chunk):
  # 先頭の空行を削除
  while current_chunk and not current_chunk[0].strip():
    current_chunk.pop(0)
  # 末尾の空行を削除
  while current_chunk and not current_chunk[-1].strip():
    current_chunk.pop()
  return current_chunk

def separate_problems(problems: str):
  lines = problems.splitlines(keepends=False)
  results = []
  current_chunk = []
  template = {"title":"", "problem":""}
  problem_comb = deepcopy(template)

  for line in lines:
    # 「例題」という文字列が含まれる行があれば
    if '例題' in line:
      # いままでの本文を確定して、先頭＆末尾の空行を除去
      if problem_comb["title"]:
        problem_content = flush_chunk(current_chunk)
        problem_comb["problem"] = '\n'.join(problem_content)
        results.append(problem_comb)
        problem_comb = deepcopy(template)
      problem_comb["title"] = line
      current_chunk = []
    else:
      current_chunk.append(line)

  # ループ終了後、まだ本文が残っていれば処理して追加
  problem_content = flush_chunk(current_chunk)
  problem_comb["problem"] = '\n'.join(problem_content)
  results.append(problem_comb)

  return results

# チェックの解答用、numbered_list を処理するため
def transform_into_n_list(input_text):
  # 正規表現パターン: 数字で始まり、その後に内容が続くセクションをキャプチャ
  # または、空行が存在する箇所で区切る
  pattern = r"(^\d+\.\s.*?)(?=^\d+\.\s|\Z)|(^.*?(?:\n\s*\n|\Z))"
  # セクションを抽出
  matches = re.findall(pattern, input_text, flags=re.MULTILINE | re.DOTALL)
  # matches はタプルのリストになるため、各要素をフラット化してフィルタリング
  flattened_matches = [item.strip() for sublist in matches for item in sublist if item.strip()]
  # 余分な空白を除去して返す
  return flattened_matches

# ここで絶対に学んでほしいこと用、bulleted_list を処理するため ネストされた箇条書きまで処理できる
# 出力形式
def transform_into_b_list(input_text):
  """
  空白行で区切られた通常テキストも含め、
  Markdown 風の箇条書きを階層構造として解析して返す。
  出力形式は [{"text": ..., "indent_level": ..., "children": [...]}, ...] のようにする。
  """

  lines = input_text.splitlines()

  # 箇条書きの正規表現
  #  - 行頭の空白 (\s*)
  #  - 箇条書き記号 ([\*-])
  #  - 少なくとも1つの空白 (\s+)
  #  - 残りのテキスト (.*)
  bullet_pattern = re.compile(r'^(\s*)([\*-])\s+(.*)')

  # 結果リスト(トップレベル要素を格納)
  result = []
  # スタック (階層管理用)
  stack = []
  # 箇条書きでない行を一時的に貯めるバッファ
  non_bullet_buffer = []

  def flush_non_bullet():
    """
    non_bullet_buffer に溜まった行を1つのノードとして
    indent_level=0 で result に追加し、バッファをクリアする。
    その際、箇条書きの階層を管理する stack もリセットしておく。
    """
    if non_bullet_buffer:
      # 連続する非箇条書き行は空白行で区切られたひとまとまりとして扱う
      text = "\n".join(non_bullet_buffer).strip()
      if text:  # 空行だけになる可能性があるのでチェック
        node = {
          "text": text,
          "indent_level": 0,
          "children": []
        }
        result.append(node)
      non_bullet_buffer.clear()
      # 箇条書きの階層をリセット (通常テキストが割り込んだら階層は途切れる、という扱い)
      stack.clear()

  for line in lines:
    # 箇条書き（bullet）であるか確認
    match = bullet_pattern.match(line)
    if match:
      # bullet 行なので、まずは non_bullet_buffer をフラッシュ
      flush_non_bullet()

      # インデント部分、箇条書き記号、テキスト部分を取得
      indent_str, bullet_mark, text = match.groups()
      indent_level = len(indent_str)  # スペースの長さをインデントレベルとする

      node = {
        "text": text.strip(),
        "indent_level": indent_level,
        "children": []
      }

      if not stack:
        # スタックが空ならトップレベル要素
        result.append(node)
        stack.append(node)
      else:
        # 現在のスタック末尾のインデントよりも浅い、または同じなら戻る
        while stack and indent_level <= stack[-1]["indent_level"]:
          stack.pop()

        if stack:
          # スタック末尾に子要素として追加
          stack[-1]["children"].append(node)
        else:
          # すべて pop されたらトップレベルに追加
          result.append(node)

        stack.append(node)

    else:
      # bullet 行ではない
      if not line.strip():
        # 空白行 → non_bullet_buffer をフラッシュして区切り扱いに
        flush_non_bullet()
      else:
        # 非箇条書き行 → 一時バッファに追加
        non_bullet_buffer.append(line)

  # 最後にバッファが残っていればフラッシュ
  flush_non_bullet()

  return result

# 再帰的に bulleted list を処理
def recursive_important_points(important_point):
  # bulleted list json テンプレートの読み込み
  with open("const/json/math/important_point_text_bulleted_list_item.json", "r", encoding="utf-8") as file:
    json_template = json.load(file)
  current_template = deepcopy(json_template)
  # 再帰的に children を解決
  children = []
  if important_point["children"] != []:
    for child_important_point in important_point["children"]:
      child_json = recursive_important_points(child_important_point)
      children.append(child_json)
  current_template["bulleted_list_item"]["rich_text"] = create_parsed_blocks(important_point["text"], is_rich_text=True)
  current_template["bulleted_list_item"]["children"] = children
  return current_template

# block 数式, inline 数式の場合には分ける必要がある。
# 出力は {'type': 'text' or 'inline_math' or 'block_math', 'content': '...'}
def separate_equation(text, is_debag=False):
  """
  Parse a given text into a list of dictionaries representing:
  text, inline_math, block_math, bold.
  Furthermore, put half-width spaces before and after inline math.
  """
  # まとめてキャプチャする正規表現
  # ブロック数式（\n$...$\n）や \begin ~ \end, インライン数式（$...$）, ボールド（**...**）の順でまとめて
  pattern = re.compile(
    r'(\\begin\{.*?\}.*?\\end\{.*?\}|\$.*?\$|\*\*.*?\*\*)',
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

        match_index += 1

  return results

# 例題の処理だけ別個でする（数学用に作ってある。）
def make_page_template(problems, check_answer, important_points, reference, practice_problem, practice_answer):
  # 辞書で block を蓄積
  blocks = {}
  result = []
  # 例題がある場合のフラグ
  is_problem = False
  # template の読み込み
  with open("const/json/math/problem_h3.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["problem"] = deepcopy(data)
  with open("const/json/math/problem_text_toggle.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["problem_text"] = deepcopy(data)
  with open("const/json/math/check_answer_h3.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["check_answer"] = deepcopy(data)
  with open("const/json/math/check_answer_contents_numbered_list_item.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["check_answer_contents"] = deepcopy(data)
  with open("const/json/math/important_point_h3.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["important_point"] = deepcopy(data)
  with open("const/json/math/important_point_text_bulleted_list_item.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["important_point_text"] = deepcopy(data)
  with open("const/json/math/complement_h3.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["complement"] = deepcopy(data)
  with open("const/json/math/complement_contents_toggle_h3.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["complement_contents"] = deepcopy(data)
  with open("const/json/math/reference_h3.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["reference"] = deepcopy(data)
  with open("const/json/math/main_reference_toggle_underline.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["main_reference"] = deepcopy(data)
  with open("const/json/math/sub_reference_toggle_underline.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["sub_reference"] = deepcopy(data)
  with open("const/json/math/practice_h3.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["practice"] = deepcopy(data)
  with open("const/json/math/practice_toggle.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["practice_problem"] = deepcopy(data)
  with open("const/json/math/practice_answer_toggle.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["practice_answer"] = deepcopy(data)
  with open("const/json/math/paragraph.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    blocks["paragraph"] = deepcopy(data)
  
  # 問題文（例題がある場合のみ）
  if(problems):
    is_problem = True
    # タイトル
    result.append(blocks["problem"])
    # 中身
    separated_problems = separate_problems(problems)
    for p in separated_problems:
      title = create_parsed_blocks(p["title"], is_rich_text=True, is_bold=True)
      problem = create_parsed_blocks(p["problem"])
      problem_text_json = deepcopy(blocks["problem_text"])
      problem_text_json["toggle"]["rich_text"] = title
      problem_text_json["toggle"]["children"] = problem
      result.append(problem_text_json)
  # チェックの解答
  # タイトル
  result.append(blocks["check_answer"])
  # 中身
  check_answers = transform_into_n_list(check_answer)
  for check_answer in check_answers:
    check_answer_json = deepcopy(blocks["check_answer_contents"])
    check_answer_json["numbered_list_item"]["rich_text"] = create_parsed_blocks(check_answer, is_rich_text=True)
    result.append(check_answer_json)
  # ここで絶対に学んでほしいこと
  # タイトル
  result.append(blocks["important_point"])
  # 中身
  important_points = transform_into_b_list(important_points)
  for important_point in important_points:
    important_point_json = recursive_important_points(important_point)
    result.append(important_point_json)
  # これを理解すれば完璧！
  result.append(blocks["complement"])
  result.append(blocks["complement_contents"])
  # 参照
  result.append(blocks["reference"])
  reference_text = create_parsed_blocks(reference, is_rich_text=True)
  main_reference_json = blocks["main_reference"]
  main_reference_json["toggle"]["children"][0]["paragraph"]["rich_text"] = reference_text
  result.append(main_reference_json)
  result.append(blocks["paragraph"])
  result.append(blocks["sub_reference"])
  result.append(blocks["paragraph"])
  # 練習問題
  result.append(blocks["practice"])
  practice_problem_blocks = create_parsed_blocks(practice_problem)
  practice_problem_json = blocks["practice_problem"]
  practice_problem_json["toggle"]["children"] = practice_problem_blocks
  result.append(blocks["practice_problem"])
  result.append(blocks["paragraph"])
  practice_answer_blocks = create_parsed_blocks(practice_answer)
  practice_answer_json = blocks["practice_answer"]
  practice_answer_json["toggle"]["children"] = practice_answer_blocks
  result.append(blocks["practice_answer"])
  
  return result

# Notion データベース内の 全てのページを取得する。
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


def main():
  load_dotenv("config/.env")

  NOTION_API_KEY = os.getenv("NOTION_API_KEY")
  NOTION_VERSION = os.getenv("NOTION_VERSION")
  database_id = os.getenv("NOTION_DATABASE_ID")
  BLOCK_1_COLUMN = os.getenv("BLOCK_1_COLUMN")
  BLOCK_2_COLUMN = os.getenv("BLOCK_2_COLUMN")
  BLOCK_3_COLUMN = os.getenv("BLOCK_3_COLUMN")
  BLOCK_4_COLUMN = os.getenv("BLOCK_4_COLUMN")
  BLOCK_5_COLUMN = os.getenv("BLOCK_5_COLUMN")
  BLOCK_6_COLUMN = os.getenv("BLOCK_6_COLUMN")
  BLOCK_7_COLUMN = os.getenv("BLOCK_7_COLUMN")
  BLOCK_8_COLUMN = os.getenv("BLOCK_8_COLUMN")
  CSV_FILE_NAME = os.getenv("CSV_FILE_NAME")
  
  df = pd.read_csv(f"const/csv/math/{CSV_FILE_NAME}", header=0, usecols=[BLOCK_1_COLUMN, BLOCK_2_COLUMN, BLOCK_3_COLUMN, BLOCK_4_COLUMN, BLOCK_5_COLUMN, BLOCK_6_COLUMN, BLOCK_7_COLUMN, BLOCK_8_COLUMN])
  df = df.fillna('')
  url_for_page_ids = f"https://api.notion.com/v1/databases/{database_id}/query"

  headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json"
  }

  # order property でソート順を指定
  payload = {
    "sorts": [
      {
        "property": "order",
        "direction": "ascending"
      }
    ]
  }

  pages = fetch_all_pages(url=url_for_page_ids, headers=headers, payload=payload)

  # csv の順番 と page_id の順番が一致していることを仮定する。
  for index, page in track(enumerate(pages),description="creating pages"):
    page_id = page["id"]
    url_for_block_ids = f"https://api.notion.com/v1/blocks/{page_id}/children"
    res = requests.get(url_for_block_ids, headers=headers)
    if res.status_code != 200:
      print(f"Error: {res.status_code}")
      print(res.text)
      exit()
    data = res.json()
    blocks =data["results"]
    # 既存のページを綺麗にお掃除
    for block in blocks:
      block_id_for_delete = block["id"]
      url_for_delete_blocks = f"https://api.notion.com/v1/blocks/{block_id_for_delete}"
      res = requests.delete(url_for_delete_blocks, headers=headers)
      if res.status_code != 200:
        print(f"Error: {res.status_code}")
        print(res.text)
        exit()
    # ページの中身の作成
    problems=df.at[index, BLOCK_1_COLUMN]; check_answer=df.at[index, BLOCK_2_COLUMN]; important_points=df.at[index, BLOCK_3_COLUMN];
    reference=df.at[index, BLOCK_4_COLUMN]; practice_problem=df.at[index, BLOCK_5_COLUMN]; practice_answer=df.at[index, BLOCK_6_COLUMN];
    area=df.at[index, BLOCK_8_COLUMN]; 
    if(problems):
      problem_numbers=df.at[index, BLOCK_7_COLUMN]
      reference += f" チャート式基礎からの数学{area}　例題{problem_numbers}"
    blocks = make_page_template(problems=problems, check_answer=check_answer, important_points=important_points, reference=reference, practice_problem=practice_problem, practice_answer=practice_answer)
    # ページの追加
    append_contents(headers=headers, page_id=page_id, blocks=blocks)

if __name__ == "__main__":
  main()