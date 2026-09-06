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
    transport_items / season.cities.note / spot_points.body /
    practical.money_intro / practical.flight_lead / practical.hotel_intro）
  - budget.items[].detail_html の行数（2行）・各行文字数（15〜60）
  - spot_sections[].spots[] の badge 必須・画像フォルダ・map_url形式
  - food_items[] の badge 必須・画像フォルダ・wiki_url 有無
  - spot_sections[] の city_desc / city_info 必須
  - spot_points[] の件数（3〜4個）
  - transport_items[] のフィールド名（name であって title ではない）
  - must フラグの比率（spot 20〜45% / food 20〜35%）
  - 死んだフィールドの残存（manner_cards 等）
  - courses.stable_title の汎用文言チェック
  - courses.stable_plans[].title の抽象語チェック（満喫・堪能等）
  - courses 全テキストの体験談調語尾チェック（南アフリカ adventure_plan は除外）
  - index_card.catch の文字数（44〜54文字）
  - season.cities[].note の文字数（100〜160文字）
  - practical.prac_cards の10枚構成チェック
  - practical.tour_platforms のキー名バリデーション
  - practical.apps[] と tour_platforms の対応チェック
  - practical.country_items の空欄チェック
  - overview.currency_name の括弧が半角かチェック
  - overview.danger_label の文言チェック（レベルに応じた統一表現）
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
    ('overview.description_html',    140, 190, True),
    ('overview.top_spot_desc',        35,  60, False),
    ('overview.top_food_desc',        50,  70, False),
    ('overview.japan_popularity_html', 85, 140, True),
    ('budget.intro',                 100, 180, False),
    ('budget.savings_tips_html',      50,  90, True),
    ('season_mini.description',       35,  60, False),
    ('practical.money_intro',        100, 180, False),
    ('practical.flight_lead',        100, 180, False),
    ('practical.hotel_intro',        100, 180, False),
]

GENERIC_STABLE_TITLES = {'定番の2大プラン', 'モデルコース'}

VALID_PLATFORMS = {'klook', 'getyourguide', 'viator', 'kkday'}

EXPECTED_PRAC_TITLES = [
    'ビザ', '通貨', 'コンセント', 'Wi-Fi', '時差',
    '気温', 'チップ', '水道水', '治安', 'カード払い',
]

_ABSTRACT_PLAN_RE = re.compile(r'(満喫|堪能|充実の旅|を楽しむ)')

# courses 内の体験談調語尾パターン（句点で区切った文末に現れる表現）
_COURSES_BAD_RE = re.compile(
    r'(な旅(に)?なった'
    r'|旅だった'
    r'|\d+[泊日]間だった'
    r'|感じた'
    r'|正解だった'
    r'|一般的だった'
    r'|味わい尽くした'
    r'|な旅だった)'
    r'\s*$'
)
# 歴史的事実の過去形は許容（かつて〜だった 等）
_COURSES_SAFE_RE = re.compile(r'かつて(は)?')


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


def _scan_courses_tone(obj, path, is_sa, skip):
    """courses オブジェクトを再帰走査して体験談調語尾を検出する。
    南アフリカ（is_sa=True）の adventure_plan 配下はスキップ。
    戻り値: [(path, excerpt), ...]"""
    findings = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            child_skip = skip or (is_sa and k == 'adventure_plan')
            findings += _scan_courses_tone(v, f'{path}.{k}', is_sa, child_skip)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            findings += _scan_courses_tone(v, f'{path}[{i}]', is_sa, skip)
    elif isinstance(obj, str) and not skip:
        text = _strip_tags(obj)
        for sent in re.split(r'[。\n]', text):
            sent = sent.strip()
            if not sent:
                continue
            if _COURSES_BAD_RE.search(sent) and not _COURSES_SAFE_RE.search(sent):
                excerpt = sent[-30:] if len(sent) > 30 else sent
                findings.append((path, excerpt))
    return findings


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

    # ── overview / budget / season_mini / practical 系の文字数 ──
    for field, lo, hi, strip in RANGES:
        val = _get(data, field)
        if not val:
            continue
        n = len(_strip_tags(val)) if strip else len(val)
        if n < lo or n > hi:
            issues.append(f'[文字数 {n}字, 目安{lo}-{hi}] {field}')

    # ── index_card.catch 文字数（44〜54文字） ──
    catch = _get(data, 'index_card.catch')
    if catch:
        n = len(catch)
        if n < 44 or n > 54:
            issues.append(f'[catch 文字数 {n}字, 目安44-54] index_card.catch')

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
            elif len(sp.get('badge', '')) > 10:
                issues.append(f'[spot badge {len(sp["badge"])}字, 10字以内] {sp.get("num")} {sp.get("badge")}')
            img = sp.get('image', '')
            if img and not img.startswith('素材/観光スポット/'):
                issues.append(f'[spot image フォルダ名誤り] {sp.get("num")} {img}')
            mu = sp.get('map_url', '')
            if mu and not (mu.startswith('https://maps.google.com/?q=') or mu.startswith('https://maps.app.goo.gl/')):
                issues.append(f'[spot map_url形式NG] {sp.get("num")} {mu}')

    # ── spot_points 件数（3〜4個） ──
    sp_pts = data.get('spot_points', [])
    if sp_pts and (len(sp_pts) < 3 or len(sp_pts) > 4):
        issues.append(f'[spot_points 件数={len(sp_pts)}, 目安3-4個]')

    # ── food_items ──
    foods = data.get('food_items', [])
    for it in foods:
        n = len(it.get('desc', ''))
        if n < 60 or n > 90:
            issues.append(f'[food desc {n}字, 目安60-90] {it.get("num")} {it.get("name")}')
        if not it.get('badge'):
            issues.append(f'[food badge空] {it.get("num")} {it.get("name")}')
        elif len(it.get('badge', '')) > 10:
            issues.append(f'[food badge {len(it["badge"])}字, 10字以内] {it.get("num")} {it.get("badge")}')
        img = it.get('image', '')
        if img and not img.startswith('素材/グルメ/'):
            issues.append(f'[food image フォルダ名誤り] {it.get("num")} {img}')
        if not it.get('wiki_url'):
            issues.append(f'[food wiki_url欠落] {it.get("num")} {it.get("name")}')

    # ── must比率 ──
    if spots:
        must_pct = sum(1 for sp in spots if sp.get('must')) / len(spots) * 100
        if must_pct < 20 or must_pct > 45:
            issues.append(f'[spot must比率 {must_pct:.1f}%, 目安20-45%] {sum(1 for sp in spots if sp.get("must"))}/{len(spots)}')
    if foods:
        must_pct = sum(1 for it in foods if it.get('must')) / len(foods) * 100
        if must_pct < 20 or must_pct > 35:
            issues.append(f'[food must比率 {must_pct:.1f}%, 目安20-35%] {sum(1 for it in foods if it.get("must"))}/{len(foods)}')

    # ── season.cities[].note 文字数（100〜160文字） ──
    for c in data.get('season', {}).get('cities', []):
        note = c.get('note', '')
        if note:
            n = len(note)
            if n < 100 or n > 160:
                issues.append(f'[season city note {n}字, 目安100-160] {c.get("name")}')

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

    # ── stable_plans[].title 抽象語チェック ──
    for plan in (_get(data, 'courses.stable_plans') or []):
        title = plan.get('title', '')
        if title and _ABSTRACT_PLAN_RE.search(title):
            issues.append(f'[plan title 抽象語] "{title}"（都市名を列挙する形に変更を検討）')

    # ── courses 体験談語尾チェック ──
    courses = data.get('courses', {})
    if courses:
        is_sa = (country_id == 'south_africa')
        for path, excerpt in _scan_courses_tone(courses, 'courses', is_sa, False):
            issues.append(f'[courses 体験談語尾] {path}: 「…{excerpt}」')

    # ── practical.prac_cards 10枚構成チェック ──
    prac = data.get('practical', {})
    prac_cards = prac.get('prac_cards', [])
    if prac_cards:
        actual_titles = [c.get('title', '') for c in prac_cards]
        missing = [t for t in EXPECTED_PRAC_TITLES if t not in actual_titles]
        if missing:
            issues.append(f'[prac_cards 項目不足] 未登録: {", ".join(missing)}')
        if len(prac_cards) != 10:
            issues.append(f'[prac_cards 枚数={len(prac_cards)}, 目安10枚]')

    # ── tour_platforms キー名チェック ──
    platforms = prac.get('tour_platforms', [])
    for p in platforms:
        if p not in VALID_PLATFORMS:
            issues.append(f'[tour_platforms 不正なキー] "{p}"（klook / getyourguide / viator のいずれか）')

    # ── apps[] と tour_platforms の対応チェック ──
    app_icons = {a.get('icon') for a in prac.get('apps', [])}
    for p in platforms:
        if p not in app_icons:
            issues.append(f'[apps 未登録] tour_platforms に "{p}" があるが apps[] に対応エントリがない')

    # ── country_items 空欄チェック ──
    if not prac.get('country_items'):
        issues.append('[country_items 空欄] practical.country_items が未設定')

    # ── overview.currency_name の括弧チェック（全角→NG） ──
    cn = _get(data, 'overview.currency_name')
    if cn and ('（' in cn or '）' in cn):
        issues.append(f'[currency_name 全角括弧] "{cn}"（半角 () に修正）')

    # ── overview.danger_label 文言チェック ──
    dlevel = _get(data, 'overview.danger_level')
    dlabel = _get(data, 'overview.danger_label')
    if dlevel is not None and dlabel and country_id != 'north_korea':
        if dlevel == 0 and dlabel != '特に危険情報なし':
            issues.append(f'[danger_label 文言不一致] レベル0は"特に危険情報なし"（現在: "{dlabel}"）')
        elif dlevel == 1 and dlabel != 'レベル1：十分注意':
            issues.append(f'[danger_label 文言不一致] レベル1は"レベル1：十分注意"（現在: "{dlabel}"）')

    # ── cash_daily_low/high の妥当性（食費・交通費の中央値×現金依存度係数との照合） ──
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
