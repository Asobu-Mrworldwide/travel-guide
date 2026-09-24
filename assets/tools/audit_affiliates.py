"""
audit_affiliates.py — 広告・アフィリエイトリンクの使用状況を集計する

assets/affiliates-data.js に定義された全キー(AFFILIATES / BOOKING_BOXES /
AFFILIATE_CARDS)について、サイト内の各ページで何回・どこで使われているかを
走査し、assets/affiliate-usage-data.js に集計結果を書き出す。

このJSファイルは assets/affiliates-preview.html が <script src> で読み込み、
「広告管理」画面の使用状況セクションに反映する。

使い方:
    python assets/tools/audit_affiliates.py

affiliates-data.js にキーを追加・削除した後や、各国ページに広告を差し込んだ後は
このスクリプトを再実行してから affiliates-preview.html を開くこと。
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
DATA_JS = ROOT / "assets" / "affiliates-data.js"
OUTPUT_JS = ROOT / "assets" / "affiliate-usage-data.js"

# スキャン対象から除外するディレクトリ
EXCLUDE_DIRS = {"_preview", "素材", "assets", ".git", ".claude", "node_modules"}
# ファイル名で除外するもの（テンプレート・デバッグ用の一時ファイル）
EXCLUDE_NAME_PATTERNS = ["_debug_test", "_country_template"]

USAGE_ATTR_RE = re.compile(
    r'data-(affiliate-card-inner|affiliate-card|affiliate-box|affiliate|sticky-banner)="([a-zA-Z0-9_]+)"'
)

ATTR_LABELS = {
    "affiliate": "テキストリンク",
    "affiliate-card": "説明カード",
    "affiliate-card-inner": "統合カード(inner)",
    "affiliate-box": "予約ボタンボックス",
    "sticky-banner": "固定バナー",
}


def extract_top_level_entries(js_text, const_name):
    """affiliates-data.js の `const NAME = { key: {...}, ... };` からトップレベルの
    key → その中身(文字列) の対応を取り出す"""
    m = re.search(r"const\s+" + re.escape(const_name) + r"\s*=\s*\{", js_text)
    if not m:
        return {}
    start = m.end()
    depth = 1
    i = start
    while depth > 0 and i < len(js_text):
        if js_text[i] == "{":
            depth += 1
        elif js_text[i] == "}":
            depth -= 1
        i += 1
    body = js_text[start:i - 1]
    # depth 1（トップレベル）の `key: { ... }` だけを拾う
    entries = {}
    depth = 0
    j = 0
    key_re = re.compile(r"([a-zA-Z0-9_]+)\s*:\s*\{")
    while j < len(body):
        if depth == 0:
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


def collect_html_files():
    files = []
    for p in ROOT.rglob("*.html"):
        rel_parts = p.relative_to(ROOT).parts
        if any(part in EXCLUDE_DIRS for part in rel_parts):
            continue
        if any(pat in p.name for pat in EXCLUDE_NAME_PATTERNS):
            continue
        files.append(p)
    return sorted(files)


def main():
    js_text = DATA_JS.read_text(encoding="utf-8")
    affiliates_entries = extract_top_level_entries(js_text, "AFFILIATES")
    booking_entries = extract_top_level_entries(js_text, "BOOKING_BOXES")
    card_entries = extract_top_level_entries(js_text, "AFFILIATE_CARDS")

    all_keys = {
        "affiliate": list(affiliates_entries.keys()),
        "affiliate-box": list(booking_entries.keys()),
        "affiliate-card": list(card_entries.keys()),
    }
    # affiliate-card-inner / sticky-banner は AFFILIATE_CARDS のキーを流用する仕組みなので同じ一覧を使う
    all_keys["affiliate-card-inner"] = all_keys["affiliate-card"]
    all_keys["sticky-banner"] = all_keys["affiliate-card"]

    # AFFILIATES[key] に banner:{...} がある場合、そのテキストリンク(data-affiliate="key")が
    # 使われている箇所では affiliates.js が自動的に AFFILIATE_CARDS[key] の同名カードも
    # 差し込む（HTML上には data-affiliate-card="key" が現れないため静的走査では検出できない）
    auto_linked_keys = {
        key for key, body in affiliates_entries.items()
        if re.search(r"banner\s*:\s*\{", body) and key in card_entries
    }

    html_files = collect_html_files()

    # usage[type][key] = { total: n, pages: [{file, count}] }
    usage = {t: {k: {"total": 0, "pages": []} for k in keys} for t, keys in all_keys.items()}
    unknown_refs = []  # 定義されていないキーを参照している箇所

    for f in html_files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        rel = f.relative_to(ROOT).as_posix()
        per_file_counts = {}
        for m in USAGE_ATTR_RE.finditer(text):
            attr_type, key = m.group(1), m.group(2)
            per_file_counts.setdefault((attr_type, key), 0)
            per_file_counts[(attr_type, key)] += 1

        for (attr_type, key), count in per_file_counts.items():
            if key not in all_keys.get(attr_type, {}) and key not in usage.get(attr_type, {}):
                unknown_refs.append({"file": rel, "type": attr_type, "key": key, "count": count})
                continue
            usage[attr_type][key]["total"] += count
            usage[attr_type][key]["pages"].append({"file": rel, "count": count})

    # テキストリンク経由での自動カード表示を反映（HTMLには現れない間接使用）
    for key in auto_linked_keys:
        card_u = usage["affiliate-card"][key]
        text_u = usage["affiliate"][key]
        card_u["auto_via_text_link"] = True
        card_u["auto_pages"] = text_u["pages"]

    # 未使用キーの抽出（テキストリンク経由の自動表示があれば未使用扱いしない）
    unused = []
    for attr_type in ("affiliate", "affiliate-box", "affiliate-card"):
        for key, u in usage[attr_type].items():
            is_auto_covered = attr_type == "affiliate-card" and u.get("auto_via_text_link") and len(u.get("auto_pages", [])) > 0
            if u["total"] == 0 and not is_auto_covered:
                unused.append({"type": attr_type, "key": key})

    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scanned_files": len(html_files),
        "usage": usage,
        "unused": unused,
        "unknown_refs": unknown_refs,
        "attr_labels": ATTR_LABELS,
    }

    OUTPUT_JS.write_text(
        "// 自動生成ファイル。手で編集しない。\n"
        "// 生成: assets/tools/audit_affiliates.py\n"
        "const AFFILIATE_USAGE = " + json.dumps(result, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )

    print(f"走査ファイル数: {len(html_files)}")
    print(f"出力: {OUTPUT_JS.relative_to(ROOT)}")
    if unused:
        print(f"\n⚠️ 未使用のキー（{len(unused)}件）:")
        for u in unused:
            print(f"  - [{u['type']}] {u['key']}")
    else:
        print("\n未使用キーなし")
    if unknown_refs:
        print(f"\n⚠️ affiliates-data.js に存在しないキーへの参照（{len(unknown_refs)}件）:")
        for r in unknown_refs:
            print(f"  - {r['file']}: data-{r['type']}=\"{r['key']}\"")
    else:
        print("未定義キー参照なし（NGなし）")


if __name__ == "__main__":
    main()
