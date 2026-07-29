#!/usr/bin/env python3
"""
check_rules.py — 国ページの執筆ルール一括検証スクリプト

CLAUDE.md・メモリーで確定した文字数・スキーマルールをまとめてチェックする。
generate.py の末尾から自動的に呼び出される（generate() の最後）ほか、
単体でも実行できる:
    python check_rules.py <country_id>
    python check_rules.py --all   （全国チェック）

チェック内容:
  - 文字数ルール（spot desc / food desc / overview系 / budget系 / season_mini /
    transport_items / season.cities.note / spot_points.body）
  - budget.items[].detail_html の行数（2行）・各行文字数（15〜60）
  - spot_sections[].spots[] の badge 必須・画像フォルダ・map_url形式
  - food_items[] の badge 必須・画像フォルダ
  - spot_sections[] の city_desc / city_info 必須
  - transport_items[] のフィールド名（name であって title ではない）
  - must フラグの比率（spot 20〜45% / food 20〜35%）
  - 死んだフィールドの残存（manner_cards 等）
  - courses.stable_title の汎用文言チェック
  - phrases カテゴリの項目数（_country_template.json との一致）
  - practical.cash_daily_low/high が budget.items（食費・交通費の中央値×現金依存度係数）の
    計算式から大きく外れていないか（実測値による個別上書きは±40%程度まで許容）
"""
import json, re, os, glob, sys

def _strip_tags(s):
    return re.sub(r'<[^>]+>', '', s or '')

def _get(d, path):
    cur = d
    for p in path.split('.'):
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
    return cur

RANGES = [
    ('overview.description_html', 140, 190, True),
    ('overview.top_spot_desc', 35, 60, False),
    ('overview.top_food_desc', 50, 70, False),
    ('overview.japan_popularity_html', 85, 140, True),
    ('budget.intro', 100, 180, False),
    ('budget.savings_tips_html', 50, 90, True),
    ('season_mini.description', 35, 60, False),
]

GENERIC_STABLE_TITLES = {'定番の2大プラン', 'モデルコース'}

def _parse_price_range(s):
    """'1,000〜4,000円/日' のような文字列から[下限, 上限]（円）を取り出す。'1.5万'表記にも対応。"""
    if not s:
        return None
    s2 = s.replace(',', '')
    def conv(tok):
        m = re.match(r'([\d.]+)万', tok)
        if m:
            return float(m.group(1)) * 10000
        m2 = re.match(r'([\d.]+)', tok)
        return float(m2.group(1)) if m2 else None
    nums = [conv(n) for n in re.findall(r'[\d.]+万?', s2)]
    nums = [n for n in nums if n is not None]
    return nums[:2] if len(nums) >= 2 else None

_INTERCITY_TRANSPORT_MARKERS = ('国内線', 'レンタカー', 'フライト', '飛行機', '隣島', '島間')

def _cash_dependency_mult(label):
    if not label:
        return None
    if '高' in label:
        return 1.0
    if '低' in label:
        return 0.2
    if '中' in label:
        return 0.7
    return None


def check_country(country_id, data=None, root_dir=None, verbose=True):
    """1か国分をチェックし、issue文字列のリストを返す。"""
    if data is None:
        root_dir = root_dir or os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
        path = os.path.join(root_dir, country_id, f'{country_id}.json')
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    else:
        root_dir = root_dir or os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

    issues = []

    # ── overview / budget / season_mini 系の文字数 ──
    for field, lo, hi, strip in RANGES:
        val = _get(data, field)
        if not val:
            continue
        n = len(_strip_tags(val)) if strip else len(val)
        if n < lo or n > hi:
            issues.append(f'[文字数 {n}字, 目安{lo}-{hi}] {field}')

    # ── transport_items ──
    for t in data.get('transport_items', []):
        if 'title' in t and 'name' not in t:
            issues.append(f'[transport_items フィールド名バグ] "title"を使用（正しくは"name"） → {t.get("title")}')
        n = len(_strip_tags(t.get('desc', '')))
        if t.get('desc') and (n < 50 or n > 80):
            issues.append(f'[transport desc {n}字, 目安50-80] {t.get("name", t.get("title"))}')

    # ── budget.items[].detail_html ──
    for it in data.get('budget', {}).get('items', []):
        dh = it.get('detail_html', '')
        if not dh:
            continue
        lines = dh.split('<br>')
        if len(lines) != 2:
            issues.append(f'[budget item 行数={len(lines)}, 目安2行] {it.get("name")}')
        for ln in lines:
            n = len(_strip_tags(ln).strip())
            if n and (n < 15 or n > 60):
                issues.append(f'[budget item 行 {n}字, 目安15-60] {it.get("name")}')

    # ── spot_sections ──
    spots = []
    for sec in data.get('spot_sections', []):
        if not sec.get('city_desc'):
            issues.append(f'[city_desc欠落] {sec.get("city_id")}')
        if not sec.get('city_info'):
            issues.append(f'[city_info欠落] {sec.get("city_id")}')
        for sp in sec.get('spots', []):
            spots.append(sp)
            n = len(sp.get('desc', ''))
            if n < 50 or n > 80:
                issues.append(f'[spot desc {n}字, 目安50-80] {sp.get("num")} {sp.get("name")}')
            if not sp.get('badge'):
                issues.append(f'[spot badge空] {sp.get("num")} {sp.get("name")}')
            img = sp.get('image', '')
            if img and not img.startswith('素材/観光スポット/'):
                issues.append(f'[spot image フォルダ名誤り] {sp.get("num")} {img}')
            mu = sp.get('map_url', '')
            if mu and not (mu.startswith('https://maps.google.com/?q=') or mu.startswith('https://maps.app.goo.gl/')):
                issues.append(f'[spot map_url形式NG] {sp.get("num")} {mu}')

    # ── food_items ──
    foods = data.get('food_items', [])
    for it in foods:
        n = len(it.get('desc', ''))
        if n < 60 or n > 90:
            issues.append(f'[food desc {n}字, 目安60-90] {it.get("num")} {it.get("name")}')
        if not it.get('badge'):
            issues.append(f'[food badge空] {it.get("num")} {it.get("name")}')
        img = it.get('image', '')
        if img and not img.startswith('素材/グルメ/'):
            issues.append(f'[food image フォルダ名誤り] {it.get("num")} {img}')

    # ── must比率 ──
    if spots:
        must_pct = sum(1 for sp in spots if sp.get('must')) / len(spots) * 100
        if must_pct < 20 or must_pct > 45:
            issues.append(f'[spot must比率 {must_pct:.1f}%, 目安20-45%] {sum(1 for sp in spots if sp.get("must"))}/{len(spots)}')
    if foods:
        must_pct = sum(1 for it in foods if it.get('must')) / len(foods) * 100
        if must_pct < 20 or must_pct > 35:
            issues.append(f'[food must比率 {must_pct:.1f}%, 目安20-35%] {sum(1 for it in foods if it.get("must"))}/{len(foods)}')

    # ── 死んだフィールド ──
    for key in ('manner_cards', 'manner_cta_title', 'manner_cta_desc'):
        if key in data:
            issues.append(f'[死んだフィールド残存] {key}')
    if 'cta_title' in data.get('practical', {}) or 'cta_desc' in data.get('practical', {}):
        issues.append('[死んだフィールド残存] practical.cta_title/cta_desc')

    # ── stable_title 汎用文言 ──
    st = _get(data, 'courses.stable_title')
    if st in GENERIC_STABLE_TITLES:
        issues.append(f'[stable_title 汎用文言] "{st}"（国固有の見出しに変更を検討）')

    # ── cash_daily_low/high の妥当性（食費・交通費の中央値×現金依存度係数との照合） ──
    prac = data.get('practical', {})
    cdl, cdh = prac.get('cash_daily_low'), prac.get('cash_daily_high')
    rate = prac.get('exchange_rate')
    mult = _cash_dependency_mult(prac.get('cash_dependency'))
    if cdl and cdh and rate and mult:
        food = transport = None
        transport_is_intercity = False
        for it in data.get('budget', {}).get('items', []):
            if '食費' in it.get('name', ''):
                food = _parse_price_range(it.get('price'))
            if '交通費' in it.get('name', ''):
                transport = _parse_price_range(it.get('price'))
                if any(m in it.get('detail_html', '') for m in _INTERCITY_TRANSPORT_MARKERS):
                    transport_is_intercity = True
        if food and transport:
            try:
                transport_component = transport[0] if transport_is_intercity else (transport[0] + transport[1]) / 2
                median_jpy = (food[0] + food[1]) / 2 + transport_component
                rate_f = float(rate)
                expected_low = median_jpy * mult / rate_f
                expected_high = expected_low * 1.3
                actual_low, actual_high = float(cdl), float(cdh)
                if expected_low > 0 and not (0.5 <= actual_low / expected_low <= 1.6):
                    issues.append(f'[cash_daily_low 目安からの乖離] 実測/上書きでなければ再計算を推奨: 現在{cdl} 計算目安≈{expected_low:.0f}')
                if expected_high > 0 and not (0.5 <= actual_high / expected_high <= 1.6):
                    issues.append(f'[cash_daily_high 目安からの乖離] 実測/上書きでなければ再計算を推奨: 現在{cdh} 計算目安≈{expected_high:.0f}')
            except (ValueError, ZeroDivisionError):
                pass

    # ── phrases カテゴリ項目数（テンプレートと比較） ──
    tpl_path = os.path.join(root_dir, 'assets', 'tools', '_country_template.json')
    if os.path.exists(tpl_path):
        with open(tpl_path, encoding='utf-8') as f:
            tpl = json.load(f)
        expected = {c['label']: len(c['items']) for c in tpl['phrases']['decks'][0]['categories']}
        for deck in data.get('phrases', {}).get('decks', []):
            for cat in deck.get('categories', []):
                exp_n = expected.get(cat['label'])
                got_n = len(cat.get('items', []))
                if exp_n is not None and got_n < exp_n:
                    issues.append(f'[phrases 項目不足] {deck.get("id")} / {cat["label"]}: {got_n}/{exp_n}')

    if verbose:
        if issues:
            print(f'=== {country_id}: {len(issues)}件のNG ===')
            for i in issues:
                print(' ', i)
        else:
            print(f'=== {country_id}: NGなし ===')

    return issues


def check_all(root_dir=None, verbose=True):
    root_dir = root_dir or os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
    results = {}
    for path in sorted(glob.glob(os.path.join(root_dir, '*', '*.json'))):
        country_id = os.path.basename(path)[:-5]
        if country_id != os.path.basename(os.path.dirname(path)):
            continue
        try:
            issues = check_country(country_id, root_dir=root_dir, verbose=verbose)
            results[country_id] = issues
        except Exception as e:
            if verbose:
                print(f'=== {country_id}: 読み込みエラー {e} ===')
    return results


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('使い方: python check_rules.py <country_id> | --all')
        sys.exit(1)
    if sys.argv[1] == '--all':
        check_all()
    else:
        check_country(sys.argv[1])
