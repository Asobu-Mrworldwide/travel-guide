#!/usr/bin/env python3
"""
為替レート変動チェッカー
使い方:
    python check_exchange_rates.py                  # 全国のレートを確認するだけ
    python check_exchange_rates.py --threshold 5     # 閾値を変更（デフォルト±10%）
    python check_exchange_rates.py --apply           # 閾値を超えた国だけ実際にJSONを更新する

各国JSONの practical.exchange_rate（保存済み・1単位=何円）を、無料為替API
（open.er-api.com, JPY基準・APIキー不要）から取得した現在レートと比較する。
--apply を付けると、閾値を超えた国だけ overview.currency_rate と
practical.exchange_rate を上書きする。budget内の物価プロス文（「屋台なら1食
300〜500円」等）は自動更新の対象外なので、更新された国は手動で見直すこと。
更新後は generate.py <country_id> を忘れずに実行する。
"""
import json, os, argparse, urllib.request

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

COUNTRIES = [
    {"id": "malaysia",     "path": "malaysia/malaysia.json",        "code": "MYR", "unit_amount": 1,     "unit_label": "RM"},
    {"id": "thailand",     "path": "thailand/thailand.json",        "code": "THB", "unit_amount": 1,     "unit_label": "THB"},
    {"id": "uzbekistan",   "path": "uzbekistan/uzbekistan.json",    "code": "UZS", "unit_amount": 10000, "unit_label": "万UZS"},
    {"id": "south_africa", "path": "south_africa/south_africa.json","code": "ZAR", "unit_amount": 1,     "unit_label": "ZAR"},
    {"id": "taiwan",       "path": "taiwan/taiwan.json",            "code": "TWD", "unit_amount": 1,     "unit_label": "TWD"},
    {"id": "singapore",    "path": "singapore/singapore.json",      "code": "SGD", "unit_amount": 1,     "unit_label": "SGD"},
    {"id": "srilanka",     "path": "srilanka/srilanka.json",        "code": "LKR", "unit_amount": 1,     "unit_label": "LKR"},
]


def fetch_jpy_rates():
    url = "https://open.er-api.com/v6/latest/JPY"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.load(resp)
    if data.get("result") != "success":
        raise RuntimeError(f"為替API取得失敗: {data}")
    return data["rates"]  # rates[CODE] = 1JPYあたりのCODE通貨量


def fmt_num(x):
    r = round(x, 4)
    if r == int(r):
        return str(int(r))
    s = f"{r:.4f}".rstrip('0').rstrip('.')
    return s


def main():
    ap = argparse.ArgumentParser(description="各国の為替レートをチェックし、変動が大きい国を知らせる")
    ap.add_argument('--threshold', type=float, default=10.0, help='通知する変動率(%%)の閾値。デフォルト10')
    ap.add_argument('--apply', action='store_true', help='閾値を超えた国だけ、レート表記を実際にJSONへ反映する')
    args = ap.parse_args()

    print('為替レートを取得中... (open.er-api.com)')
    jpy_rates = fetch_jpy_rates()
    print()

    changed = []
    print(f"{'国':<14}{'通貨':<6}{'保存レート':>10}{'現在レート':>12}{'変動率':>9}")
    print('-' * 55)
    for c in COUNTRIES:
        path = os.path.join(ROOT, c['path'])
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        stored = float(data['practical']['exchange_rate'])
        if c['code'] not in jpy_rates:
            print(f"  ⚠️  {c['id']}: 通貨コード {c['code']} がAPIレスポンスに見つかりません")
            continue
        live = 1 / jpy_rates[c['code']]  # 現地通貨1単位のJPY換算
        change_pct = (live - stored) / stored * 100
        flag = '⚠️ ' if abs(change_pct) >= args.threshold else '   '
        print(f"{flag}{c['id']:<11}{c['code']:<6}{stored:>10.4f}{live:>12.4f}{change_pct:>8.1f}%")
        if abs(change_pct) >= args.threshold:
            changed.append((c, stored, live, change_pct))

    print()
    if not changed:
        print(f'閾値(±{args.threshold}%)を超えた国はありませんでした。')
        return

    print(f'⚠️  閾値(±{args.threshold}%)を超えた国が{len(changed)}件あります:')
    for c, stored, live, pct in changed:
        print(f"  - {c['id']}: {stored} → {live:.4f}円 ({pct:+.1f}%)")

    if args.apply:
        print()
        for c, stored, live, pct in changed:
            path = os.path.join(ROOT, c['path'])
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            data['practical']['exchange_rate'] = fmt_num(live)
            display_val = fmt_num(live * c['unit_amount'])
            data['overview']['currency_rate'] = f"1{c['unit_label']} ≈ {display_val}円"
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.write('\n')
            print(f"  ✅ {c['id']} のレート表記を更新しました → generate.py {c['id']} を実行してください")
        print("\n⚠️  budget内の物価プロス文（1食◯◯円など）は自動更新していません。上記の国は手動で見直してください。")
    else:
        print("\n--apply を付けて再実行すると、上記の国だけレート表記を自動更新します。")


if __name__ == '__main__':
    main()
