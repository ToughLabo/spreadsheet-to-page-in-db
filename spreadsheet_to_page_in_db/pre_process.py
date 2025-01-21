import re
import requests
import pandas as pd
import google.generativeai as genai
import math
import time

def extract_uuid_from_notion_url(url):
  pattern = r"([0-9a-f]{32})|([0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12})"
  match = re.search(pattern, url)
  if match:
    result = match.group(1) if match.group(1) else match.group(2)  # どちらかのグループがマッチしているはず

    if len(result) == 36:  # ハイフン付きUUIDの場合
      return result.replace("-", "")
    elif len(result) == 32:  # すでにハイフンなしUUIDの場合
      return result
    else:
      raise ValueError("不正な UUID です。")
  else:
    print("Not found id from url!")
    return None

def pre_process_callout(text):
  return f"> [!⭐] {text}"

def pre_process_quote(text):
  return f"> {text}"

def pre_process_numbered_list(text):
  lines = text.split("\n")
  markdown_lines = []
  counters = [0] * 10  # 最大10階層まで対応

  for line in lines:
    stripped = line.lstrip()
    indent_level = (len(line) - len(stripped)) // 4  # 4スペース = 1レベルのインデント
    stripped = stripped.lstrip("・-").strip()  # `・`や`-`を削除

    if stripped:  # 空行は無視
      counters[indent_level] += 1
      for i in range(indent_level + 1, len(counters)):
        counters[i] = 0  # 下位のカウンターをリセット

      bullet = f"{counters[indent_level]}. "
      markdown_lines.append("  " * indent_level + bullet + stripped)
  
  return "\n".join(markdown_lines)

def pre_process_bulleted_list(text):
  lines = text.split("\n")
  markdown_lines = []

  for line in lines:
    stripped = line.lstrip()
    indent_level = (len(line) - len(stripped)) // 2  # 2スペース = 1レベルのインデント
    stripped = stripped.lstrip("・-").strip()  # `・` や `-` を削除

    if stripped:  # 空行を無視
      bullet = "- "
      markdown_lines.append("  " * indent_level + bullet + stripped)

  return "\n".join(markdown_lines)

def pre_process_generative_ai_detail(text):
  genai.configure(api_key="AIzaSyDNyIuolCcdB_etfq3i_YO_TxtDYsqMCf4")
  model = genai.GenerativeModel("gemini-2.0-flash-exp")
  prompt1 = r"""
  あなたは優れた Markdown 変換ツールです。これからお渡しする文章を改行も含めて全て、以下のルールを厳守して「Notion の API で扱いやすい Markdown 形式」に変換してください。

  変換後の出力では、次の **ブロックレベル** および **インラインレベル** の規則をすべて満たす必要があります。

  ---

  ### 1. ブロックレベルのルール

  1. **段落 (Paragraph)**
      - 先頭に何もつけずテキストを記述します。
  2. **見出し (Heading)**
      
      # 見出し１, ## 見出し２, ### 見出し３ のみ使用可能です。
      
      - 以降のレベル（heading_4, heading_5）は使用しないでください。
  3. **箇条書き (Bulleted list)**
      - 行頭に - をつけて記述します。
      - 途中改行が必要な場合、その改行は同じリストアイテム内での改行なのか、次の新しいリストアイテムの開始なのかを明確にしてください（変換時に意図に合わせて適切に処理してください）。
  4. **番号付きリスト (Numbered list)**
      - 行頭に 1. のように数字とピリオドをつけて記述します。
      - 同様に途中の改行処理に注意してください。
  5. **引用 (Quote)**
      - 行頭に > をつけて引用文を記述します。
  6. **Callout**
      - 行頭に > [!⭐] をつけ、その後に内容を続けます。
  7. **コードブロック (Code block)**
      - 「```言語名 ... ```」形式で記述します。
      - 例:
      ```python 
        print(”Hello”)
      ```
  8. **ブロック数式 (Block equation)**
      - かならず「$$」を行頭と行末の **別々の行** に置き、次のような形で記述してください。
          
          
          $$
          E=mc^2
          $$
          
      - 上下に必ず空行を入れてください。
      - \itemize や \enumerate は決して使わないでください（LaTeX 構文の箇条書きは不可）。
      - 数式の構文ルールは KaTeX に依拠すると想定します。
  9. **区切り線 (Divider)**
      - 水平線として「---」(もしくは長めのダッシュ) を使います。
      - 例:  ---------------------
  10. **表 (Table)**
    - Markdown 標準のテーブル構文を使ってください。  
    - 例:
      ```
      | 見出し1 | 見出し2 |
      | ------ | ------ |
      | セルA1  | セルA2  |
      | セルB1  | セルB2  |
      ```
    - 必要に応じて `:---:`, `---:`, `:---` などで列の整列を示すことができます。
  11. **既に Markdown 形式になっている箇所は、内容を変更せずにそのまま維持すること。**

  ---

  ### 2. インラインレベルのルール

  1. **太字 (Bold)**
      - **...** で囲みます。
  2. *斜体 (Italic)*
      - *...* で囲みます。
  3. ~~取り消し線~~
      - ~~...~~ で囲みます。
  4. **インラインコード (Inline code)**
      - ``...``で囲みます（バッククォート2つ）。
  5. **インライン数式**
      - $…$ で囲みます。
      - ブロック数式との混在を防ぐため、インライン数式はかならず $...$ を使ってください。
  6. **ブロック数式内でのインライン Markdown 禁止**
      - 「$$...$$」の中に **太字や斜体などの Markdown 構文を入れてはいけません**。

  ---

  ### 3. 重要な前提

  - **ブロック数式 ($$...$$ や \begin{equation}...\end{equation}) の内側にはインライン Markdown を入れないでください。**
  - **パラグラフに入れ子にした箇条書きは認識不可能なので、変換は平坦化するか段落・引用など他の手段に切り替えてください。**
  - **既に Markdown 形式になっている部分は可能な限りそのまま残します。修正が不要なら触れないでください。**
  - **インライン数式は $...$ を使用し、ブロック数式は必ず「$$」を行頭・行末の行で使用してください。**

  ---

  以上のルールを踏まえ、以下のテキストを Notion 向け Markdown 形式に変換してください。

  テキストを引用しながら、可能な限り正確な変換を行ってください。

  ### 入力テキスト
  """
  
  prompt2 = f"\n{text}\n"
  
  prompt3 = r"""
  #### 出力フォーマット
  上記の **ブロックレベルのルール** と **インラインレベルのルール** に遵守した Markdown テキストを **本文のみ** 出力してください（説明や理由等は不要です）。

  - 不要な要素やタグは含めないでください（エスケープ文字や余計な制御文字を挿入しない）。
  - 必要に応じて箇条書きや見出し、ブロック数式、表の構文などを正しく置き換えてください。
  """
  prompt = prompt1 + prompt2 + prompt3
  response = model.generate_content(prompt)
  return response.text

def pre_process_generative_ai_batched(prompt_text: str) -> str:
  res = pre_process_generative_ai_detail(prompt_text)
  # ダミーの例: 各 <ROW i> の中で "変換済み: {元テキスト}" と返すだけ
  pattern = r"<ROW (\d+)>\s*(.*?)\s*</ROW \1>"
  matches = re.findall(pattern, res, re.DOTALL)
  result = [f"<ROW {row_idx}>\n{transformed_text}\n</ROW {row_idx}>" for row_idx, transformed_text in matches]
  
  # まとめて結合して返す
  return "\n".join(result)

# -------------------------------
# DataFrame の複数行をまとめて LLM に投げる関数
# -------------------------------
def batch_process_dataframe(
  df: pd.DataFrame,
  text_column: str,
  batch_size: int = 20
) -> pd.DataFrame:
  """
  - df: 入力データフレーム
  - text_column: 変換対象となる列名
  - batch_size: 1回の LLM 呼び出しあたりに処理する行数

  戻り値: 変換結果が格納されたデータフレーム
  """

  # 行数から何バッチ必要か計算
  total_rows = len(df)
  num_batches = math.ceil((total_rows-1) / batch_size)
  # 列番号を取得
  column_num = df.columns.get_loc(text_column)

  for batch_idx in range(num_batches):
    start_i = batch_idx * batch_size 
    end_i = min((batch_idx + 1) * batch_size , total_rows)

    # バッチに含まれる行を切り出す
    subset = df.iloc[start_i:end_i]
    # LLMに渡す用のプロンプト作成
    # 形式: <ROW i>(テキスト)</ROW i> を連続させる
    prompt_lines = []
    row_index = start_i
    for row in subset[text_column]:
      original_text = str(row)  # 文字列変換（NaN対策など）
      # ここでは1行でまとめているが、複数行なら分割対応も可
      prompt_lines.append(f"<ROW {row_index}>\n{original_text}\n</ROW {row_index}>")
      row_index += 1

    prompt_text = "\n".join(prompt_lines)

    # 前後に追加の指示を入れるなど自由に調整可
    full_prompt = (
      "複数の文章を上記のルールに基づいて変換して下さい。これは Batch 処理です。\n文章は\n<ROW i>\n（文章内容）\n</ROW i>\n の形式で入力されます。 "
      "出力は必ず以下の構造で文章ごとに区切って返してください:\n"
      "<ROW i>\n(変換結果)\n</ROW i>\n\n"
      "以下が入力です:\n"
      f"{prompt_text}"
    )

    # LLM呼び出し（実際には API 呼び出し）
    # time.sleep(10)
    response_text = pre_process_generative_ai_batched(full_prompt)

    # レスポンスをパースして対応する行に書き込み
    # 想定形式: <ROW 10>\n変換結果...\n</ROW 10>
    pattern = r"<ROW\s+(\d+)>\s*(.*?)\s*</ROW\s+\1>"
    matches = re.findall(pattern, response_text, flags=re.DOTALL)

    # matches は [("10", "変換結果..."), ("11", "...")] のように (row_id, content) の配列
    row_index = start_i
    for row_id_str, content_str in matches:
      # row_id_str を int に変換
      row_id = int(row_id_str)
      # ずれた時のための帳尻合わせ
      while row_index != row_id:
        if row_index < row_id:
          time.sleep(15)
          df.iat[row_index, column_num] = pre_process_generative_ai_detail(df.iat[row_index, column_num]).strip()
          row_index += 1
        else:
          row_id += 1
      # DataFrame に書き込み
      df.iat[row_id, column_num] = content_str.strip()
      row_index += 1
    # 返答がまったくルールを守って返ってこなかった場合
    while row_index < end_i:
      time.sleep(15)
      df.iat[row_index, column_num] = pre_process_generative_ai_detail(df.iat[row_index, column_num]).strip()
      row_index += 1
  
  return df

# csv file の前処理
def pre_process_csv(database_id, headers, df, pre_process_message):
  # まずは database から内容を取得
  url = f"https://api.notion.com/v1/databases/{database_id}/query"
  payload = {}
  res = requests.post(url=url, headers=headers, json=payload)
  if res.status_code != 200:
    print("cover & icon データベースから環境変数を取得する際にエラーが発生しました。")
    res.raise_for_status()
  variable_pairs = res.json()["results"]
  column_list = []
  for variable_pair in variable_pairs:
    column_name = variable_pair["properties"]["Column"]["title"][0]["text"]["content"]
    method = variable_pair["properties"]["Type"]["select"]["name"]
    ai_flag = variable_pair["properties"]["AI"]["checkbox"]
    column_list.append(column_name)
    
    # int 型
    if method == "int":
      df[column_name] = pd.to_numeric(df[column_name], errors='coerce').fillna(0).astype(int)
      continue
    
    # float 型
    if method == "float":
      df[column_name] = pd.to_numeric(df[column_name], errors='coerce').fillna(0).astype(float)
      continue
    
    # callout 型
    if method == "callout":
      df[column_name] = df[column_name].apply(pre_process_callout)
      if ai_flag:
        df[column_name] = pre_process_generative_ai_batched(df[column_name])
      continue
    
    if method == "quote":
      df[column_name] = df[column_name].apply(pre_process_quote)
      if ai_flag:
        df[column_name] = pre_process_generative_ai_batched(df[column_name])
      continue
    
    if method == "numbered_list":
      df[column_name] = df[column_name].apply(pre_process_numbered_list)
      if ai_flag:
        df[column_name] = pre_process_generative_ai_batched(df[column_name])
      continue
    
    if method == "bulleted_list":
      df[column_name] = df[column_name].apply(pre_process_bulleted_list)
      if ai_flag:
        df[column_name] = pre_process_generative_ai_batched(df[column_name])
      continue
    
    if ai_flag:
      df[column_name] = pre_process_generative_ai_batched(df[column_name])
      continue
  
  if pre_process_message == "全体":
    for column_name in df.columns.to_list():
      if not column_name in column_list:
        df[column_name] = pre_process_generative_ai_batched(df[column_name])
  
  return df

if __name__ == "__main__":
  data = {
    "Title": ["数学の基礎", "プログラミング入門", "生物学の概要", "経済学の基本"],
    "Content": [
        "数学の基礎\n数学は論理的思考を鍛える学問である。\n\n1. 数式の例\n E = mc^2 \n\n2. 命題と証明\n- 命題: 自然数 n が偶数である。\n- 証明: n = 2k ($k$ は整数) で表せるため、偶数である。",
        
        "プログラミング入門\nプログラミングの基本は **変数**、**制御構造**、関数 である。\n\n例: Python の変数\n```python\nx = 10\ny = 20\nprint(x + y)\n```\n\n箇条書き\n- 変数\n- ループ\n- 条件分岐",
        
        "生物学の概要\n 1. 生命の基本単位\n生物は細胞から成り立っている。\n\n| 種類 | 特徴 |\n|---|---|\n| 原核細胞 | 核を持たない |\n| 真核細胞 | 核を持つ |\n\n### 2. DNA と遺伝情報\nDNAは生物の遺伝情報を保持している。\n$$ \\text{DNA} = \\text{ATGCの配列} $$",
        
        "経済学の基本\n 1. 需要と供給\n市場では **需要** と **供給** によって価格が決定される。\n\n 2. グラフの例\n```python\nimport matplotlib.pyplot as plt\n\ndemand = [100, 80, 60, 40, 20]\nsupply = [20, 40, 60, 80, 100]\nplt.plot(demand, label='Demand')\nplt.plot(supply, label='Supply')\nplt.legend()\nplt.show()\n```"
    ]
  }
  df = pd.DataFrame(data)
  df_result = batch_process_dataframe(df=df, text_column="Content", batch_size=2)
  print(df_result.head())
  print(df_result["Content"])

