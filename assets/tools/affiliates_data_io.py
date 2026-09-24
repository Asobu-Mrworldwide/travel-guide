"""
affiliates_data_io.py — assets/affiliates-data.js の読み書き共通処理

このファイルは手書きのJavaScriptオブジェクトリテラル（JSONではない）なので、
専用の簡易パーサ（中括弧の対応を数えるだけの方式）とシリアライザで扱う。

- audit_affiliates.py はここから extract_top_level_entries() を使って
  既存キーの一覧を読み取る（使用状況の集計用）。
- assets/tools/app.py の「広告管理」タブはここから save_new_entry() を使って
  新しい広告リンク/カードを安全に追記する（.bak バックアップ＋書き込み後の検証つき）。
"""
import re
import shutil
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ASSETS_DIR = TOOLS_DIR.parent
ROOT = ASSETS_DIR.parent
DATA_JS = ASSETS_DIR / "affiliates-data.js"

CONST_NAMES = ("AFFILIATES", "BOOKING_BOXES", "AFFILIATE_CARDS")

_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_IDENT_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


def read_data_js_text() -> str:
    return DATA_JS.read_text(encoding="utf-8")


def _find_const_open_index(js_text: str, const_name: str) -> int:
    """`const NAME = {` の開き `{` の直後の位置を返す"""
    m = re.search(r"const\s+" + re.escape(const_name) + r"\s*=\s*\{", js_text)
    if not m:
        raise ValueError(f"const {const_name} が見つかりません")
    return m.end()


def _find_const_close_index(js_text: str, const_name: str) -> int:
    """`const NAME = { ... }` の、対応する閉じ `}` の位置(index)を返す"""
    start = _find_const_open_index(js_text, const_name)
    depth = 1
    i = start
    while depth > 0 and i < len(js_text):
        if js_text[i] == "{":
            depth += 1
        elif js_text[i] == "}":
            depth -= 1
        i += 1
    return i - 1


def extract_top_level_entries(js_text: str, const_name: str) -> dict:
    """`const NAME = { key: {...}, ... };` からトップレベルの
    key → その中身(文字列) の対応を取り出す"""
    try:
        start = _find_const_open_index(js_text, const_name)
    except ValueError:
        return {}
    close = _find_const_close_index(js_text, const_name)
    body = js_text[start:close]

    entries = {}
    key_re = re.compile(r"([a-zA-Z0-9_]+)\s*:\s*\{")
    j = 0
    while j < len(body):
        mm = key_re.match(body, j)
        if mm:
            key = mm.group(1)
            entry_start = mm.end()
            d = 1
            k = entry_start
            while d > 0 and k < len(body):
                if body[k] == "{":
                    d += 1
                elif body[k] == "}":
                    d -= 1
                k += 1
            entries[key] = body[entry_start:k - 1]
            j = k
            continue
        j += 1
    return entries


def is_valid_key(key: str) -> bool:
    return bool(_KEY_RE.match(key))


def list_all_keys(js_text: str | None = None) -> dict:
    """{ const_name: [key, ...] } を返す（重複チェック・一覧表示用）"""
    js_text = js_text if js_text is not None else read_data_js_text()
    return {cn: list(extract_top_level_entries(js_text, cn).keys()) for cn in CONST_NAMES}


def _js_string(s: str) -> str:
    escaped = (
        s.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
    )
    return f"'{escaped}'"


def to_js_literal(value, indent: int = 1) -> str:
    """Python の dict/list/str/bool/int/None を、affiliates-data.js の既存スタイル
    （シングルクォート文字列・2スペースインデント・末尾カンマ）のJSリテラル文字列に変換する"""
    pad = "  " * indent
    pad_close = "  " * (indent - 1)

    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = ["{"]
        for k, v in value.items():
            key_str = k if _IDENT_RE.match(k) else _js_string(k)
            lines.append(f"{pad}{key_str}: {to_js_literal(v, indent + 1)},")
        lines.append(f"{pad_close}}}")
        return "\n".join(lines)

    if isinstance(value, list):
        if not value:
            return "[]"
        # 短い文字列だけのリストは1行にまとめる（points等）
        if all(isinstance(v, str) for v in value) and sum(len(v) for v in value) < 60:
            return "[" + ", ".join(_js_string(v) for v in value) + "]"
        lines = ["["]
        for v in value:
            lines.append(f"{pad}{to_js_literal(v, indent + 1)},")
        lines.append(f"{pad_close}]")
        return "\n".join(lines)

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (int, float)):
        return str(value)

    if value is None:
        return "null"

    if isinstance(value, str):
        return _js_string(value)

    raise TypeError(f"to_js_literal: サポートされていない型です: {type(value)}")


def insert_entry(js_text: str, const_name: str, key: str, value_dict: dict) -> str:
    """const_name ブロックの閉じ `}` の直前に、新しい `key: { ... },` を挿入する"""
    close_idx = _find_const_close_index(js_text, const_name)
    value_js = to_js_literal(value_dict, indent=2)
    entry_text = f"  {key}: {value_js},\n\n"
    return js_text[:close_idx] + entry_text + js_text[close_idx:]


def save_new_entry(const_name: str, key: str, value_dict: dict) -> None:
    """新しいエントリを affiliates-data.js に安全に追記する。

    - キー形式チェック（半角小文字英数字とアンダースコアのみ、先頭は英字）
    - const内でのキー重複チェック
    - 書き込み前に .bak バックアップを1世代作成
    - 書き込み後に再パースして壊れていないか検証。失敗時はバックアップから復元して例外を送出
    """
    if const_name not in CONST_NAMES:
        raise ValueError(f"不明な const_name です: {const_name}")
    if not _KEY_RE.match(key):
        raise ValueError("キーは半角小文字英数字とアンダースコアのみ、先頭は英字にしてください（例: my_new_link）")

    js_text = read_data_js_text()
    existing = extract_top_level_entries(js_text, const_name)
    if key in existing:
        raise ValueError(f"キー「{key}」はすでに {const_name} に存在します")

    backup_path = DATA_JS.with_suffix(".js.bak")
    shutil.copy2(DATA_JS, backup_path)

    new_text = insert_entry(js_text, const_name, key, value_dict)
    DATA_JS.write_text(new_text, encoding="utf-8")

    # 書き込み後の検証：壊れていたらバックアップから復元する
    try:
        verify_text = DATA_JS.read_text(encoding="utf-8")
        ok = True
        for cn in CONST_NAMES:
            entries = extract_top_level_entries(verify_text, cn)
            if not entries and cn in js_text:
                # 元々中身があった const が空扱いになった＝壊れている
                ok = False
            if cn == const_name and key not in entries:
                ok = False
        if not ok:
            raise RuntimeError("書き込み後の内容が想定と一致しません")
    except Exception as e:
        shutil.copy2(backup_path, DATA_JS)
        raise RuntimeError(f"保存に失敗したため変更を元に戻しました（{e}）") from e
