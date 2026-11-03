#!/usr/bin/env python3
"""
為替レート変動チェッカー
使い方:
    python check_exchange_rates.py                  # 全国のレートを確認するだけ
    python check_exchange_rates.py --threshold 5     # 閾値を変更（デフォルト±10%）
    python check_exchange_rates.py --apply           # 閾値を超えた国だけ実際にJSONを更新する

各国JSONの practical.exchange_rate（保存済み・1単位=何円）を、無料為替API
（open.er-api.com, JPY基準・APIキー不要）から取得した現在レートと比較する。
対象国は <国>/<国>.json の practical.currency_code から自動検出する。

--apply を付けると、閾値を超えた国だけ overview.currency_rate・
practical.exchange_rate・practical.cash_note を上書きし、practical.cash_daily_low/high
も「円換算の額を保ったまま新レートで現地通貨に直す」形で再計算する
（元の値の丸め単位を引き継ぐ。食費・交通費の計算式そのものは変えない）。
budget内の物価プロス文（「屋台なら1食300〜500円」等）は自動更新の対象外なので、
更新された国は手動で見直すこと。更新後は generate.py <country_id> を忘れずに実行する。
"""
import json, os, re, argparse, urllib.request
from math import floor, log10

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

_UNIT_AMOUNTS = {'1万': 10000, '1,000': 1000, '1': 1}


def _discover_countries():
    """<dir>/<dir>.json を持つ全国を自動検出し、通貨コードとレート表記の単位を読み取る。"""
    out = []
    for name in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, name, f'{name}.json')
        if not os.path.isfile(path):
            continue
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        pr = data.get('practical', {})
        m = re.search(r'[A-Z]{3}', str(pr.get('currency_code', '')))
        if not m or 'exchange_rate' not in pr:
            continue
        unit_text, label = '1', m.group(0)
        cm = re.match(r'^(1万|1,000|1)\s*(.+?)\s*≈', str(data.get('overview', {}).get('currency_rate', '')))
        if cm:
            unit_text, label = cm.group(1), cm.group(2)
        out.append({"id": name, "path": f"{name}/{name}.json", "code": m.group(0),
                    "unit_amount": _UNIT_AMOUNTS[unit_text], "unit_text": unit_text,
                    "unit_label": label, "has_unit_display": bool(cm)})
    return out


def fetch_jpy_rates():
    url = "https://open.er-api.com/v6/latest/JPY"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.load(resp)
    if data.get("result") != "success":
        raise RuntimeError(f"為替API取得失敗: {data}")
    return data["rates"]  # rates[CODE] = 1JPYあたりのCODE通貨量


def fmt_num(x):
    """有効数字3桁で文字列化（0.0071のような小さい値でも精度を落とさない）。"""
    if x == 0:
        return '0'
    digits = 2 - int(floor(log10(abs(x))))
    if digits <= 0:
        return str(int(round(x, digits)))
    return f"{round(x, digits):.{digits}f}".rstrip('0').rstrip('.')


def fmt_display(x):
    """『1BRL ≈ 29円』のような表示用。10円以上は整数、10円未満は小数1桁。"""
    return str(int(round(x))) if x >= 10 else f"{x:.1f}".rstrip('0').rstrip('.')


_UNITS = [100000, 50000, 10000, 5000, 1000, 500, 100, 50, 10, 5, 1]


def _rounding_unit(*vals):
    """元の値を割り切れる、最も大きいキリの良い単位（丸め単位）を返す。"""
    for u in _UNITS:
        if all(v % u == 0 for v in vals):
            return u
    return 1


def rescale_cash(low, high, old_rate, new_rate):
    """円換算額を保ったまま新レートの現地通貨額に直し、元の丸め単位で四捨五入する。"""
    u = _rounding_unit(low, high)
    conv = lambda v: max(u, int(round(v * old_rate / new_rate / u)) * u)
    return conv(low), conv(high)


def apply_update(c, stored, live):
    path = os.path.join(ROOT, c['path'])
    with open(path, encoding='utf-8') as f:
        raw = f.read()
    data = json.loads(raw)
    pr, ov = data['practical'], data['overview']
    pr['exchange_rate'] = fmt_num(live)
    disp = fmt_display(live * c['unit_amount'])
    if c['has_unit_display']:
        ov['currency_rate'] = re.sub(r'≈\s*[\d.,]+\s*円', f'≈ {disp}円', str(ov['currency_rate']), count=1)
    try:
        low, high = int(pr['cash_daily_low']), int(pr['cash_daily_high'])
        nl, nh = rescale_cash(low, high, stored, live)
        pr['cash_daily_low'], pr['cash_daily_high'] = str(nl), str(nh)
        cash_msg = f"cash_daily {low}〜{high} → {nl}〜{nh}"
    except (KeyError, ValueError):
        cash_msg = "cash_dailyは対象外"
    note = str(pr.get('cash_note', ''))
    if '円で計算' in note:
        if c['unit_amount'] > 1:
            label, val = f"{c['unit_text']}{c['unit_label']}", disp
        else:
            label, val = f"1 {c['code']}", fmt_num(live)
        pr['cash_note'] = re.sub(r'^[^<]*?円で計算', f'{label} ≈ {val}円で計算', note, count=1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2) + ('\n' if raw.endswith('\n') else ''))
    return cash_msg


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
    for c in _discover_countries():
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
            cash_msg = apply_update(c, stored, live)
            print(f"  ✅ {c['id']}: {stored} → {fmt_num(live)}円 / {cash_msg} → generate.py {c['id']} を実行してください")
        print("\n⚠️  budget内の物価プロス文（1食◯◯円など）は自動更新していません。上記の国は手動で見直してください。")
    else:
        print("\n--apply を付けて再実行すると、上記の国だけレート表記を自動更新します。")


if __name__ == '__main__':
    main()
