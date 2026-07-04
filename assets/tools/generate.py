#!/usr/bin/env python3
"""
国ページ自動生成スクリプト
使い方:  python generate.py <country_id>
例:      python generate.py thailand

読み込み: <country_id>/<country_id>.json
         assets/country_template.html
出力:     <country_id>/index.html
"""
import json, re, os, sys, urllib.parse


# ──────────────────────────────────────────
# テンプレートエンジン
# ──────────────────────────────────────────

def _get(path, ctx):
    """ドット記法でコンテキストから値を取得  例: "overview.difficulty_pct" """
    val = ctx
    for p in path.split('.'):
        if isinstance(val, dict):
            val = val.get(p)
        elif isinstance(val, list):
            try:
                val = val[int(p)]
            except (ValueError, IndexError):
                val = None
        else:
            val = None
        if val is None:
            return ''
    return '' if val is None else val


def _load_icon(key, ctx):
    """
    アイコンをキー名で解決する。優先順位:
    1. 素材/絵文字/<key>.svg が存在すればSVGを返す
    2. assets/icons.json にキーがあれば絵文字を返す
    3. どちらもなければキー名をそのまま返す
    """
    root_dir   = ctx.get('__root_dir__', '')
    assets_dir = os.path.join(root_dir, 'assets')

    svg_path = os.path.join(root_dir, '素材', '絵文字', f'{key}.svg')
    if os.path.exists(svg_path):
        with open(svg_path, encoding='utf-8') as f:
            return f.read().strip()

    icons_path = os.path.join(assets_dir, 'icons.json')
    if os.path.exists(icons_path):
        with open(icons_path, encoding='utf-8') as f:
            icons = json.load(f)
        if key in icons:
            return icons[key]

    return key


def _render(text, ctx):
    """テンプレートテキストをコンテキストでレンダリング"""
    result = []
    i = 0
    n = len(text)
    while i < n:
        if text[i:i+2] == '{{':
            j = text.find('}}', i + 2)
            if j == -1:
                result.append(text[i]); i += 1; continue
            expr = text[i+2:j].strip()
            if expr.startswith('icon:'):
                icon_key = expr[5:].strip()
                resolved = _get(icon_key, ctx)
                if resolved and isinstance(resolved, str):
                    icon_key = resolved
                result.append(_load_icon(icon_key, ctx))
            else:
                result.append(str(_get(expr, ctx)))
            i = j + 2

        elif text[i:i+2] == '{%':
            j = text.find('%}', i + 2)
            if j == -1:
                result.append(text[i]); i += 1; continue
            tag = text[i+2:j].strip()

            if tag.startswith('for '):
                m = re.match(r'for\s+(\w+)\s+in\s+([\w.]+)', tag)
                if not m:
                    i = j + 2; continue
                var_name  = m.group(1)
                list_path = m.group(2)
                items     = _get(list_path, ctx)
                inner, end_pos = _find_end(text, j + 2, 'for', 'endfor')
                if isinstance(items, list):
                    for item in items:
                        new_ctx = dict(ctx)
                        new_ctx[var_name] = item
                        result.append(_render(inner, new_ctx))
                i = end_pos

            elif tag.startswith('if '):
                condition = tag[3:].strip()
                then_block, else_block, end_pos = _find_if(text, j + 2)
                val = _get(condition, ctx)
                if val:
                    result.append(_render(then_block, ctx))
                elif else_block is not None:
                    result.append(_render(else_block, ctx))
                i = end_pos

            elif tag in ('endif', 'endfor', 'else'):
                i = j + 2  # 親ブロックで処理済み

            else:
                i = j + 2

        else:
            result.append(text[i])
            i += 1

    return ''.join(result)


def _find_end(text, start, open_kw, close_kw):
    """ネストを考慮して閉じタグを探す。戻り値: (内部テキスト, 終了位置)"""
    depth = 1
    i = start
    while i < len(text):
        fo = text.find('{%', i)
        if fo == -1:
            break
        fc = text.find('%}', fo + 2)
        if fc == -1:
            break
        tag = text[fo+2:fc].strip()
        if tag == open_kw or tag.startswith(open_kw + ' '):
            depth += 1
            i = fc + 2
        elif tag == close_kw or tag.startswith(close_kw + ' '):
            depth -= 1
            if depth == 0:
                return text[start:fo], fc + 2
            i = fc + 2
        else:
            i = fc + 2
    return text[start:], len(text)


def _find_if(text, start):
    """if/else/endif を探す。戻り値: (then_text, else_text|None, end_pos)"""
    depth = 1
    i = start
    else_split = None
    while i < len(text):
        fo = text.find('{%', i)
        if fo == -1:
            break
        fc = text.find('%}', fo + 2)
        if fc == -1:
            break
        tag = text[fo+2:fc].strip()
        if tag.startswith('if '):
            depth += 1
            i = fc + 2
        elif tag == 'else' and depth == 1:
            else_split = (fo, fc + 2)
            i = fc + 2
        elif tag == 'endif':
            depth -= 1
            if depth == 0:
                if else_split:
                    return text[start:else_split[0]], text[else_split[1]:fo], fc + 2
                else:
                    return text[start:fo], None, fc + 2
            i = fc + 2
        else:
            i = fc + 2
    return text[start:], None, len(text)


# ──────────────────────────────────────────
# スポットデータ（分割ページ用：どのページでもポップアップを開けるよう埋め込む）
# ──────────────────────────────────────────

def build_spot_data_js(data):
    """spot_sections から num→{name,desc,img,mapUrl} の JS オブジェクトリテラルを作る"""
    country_label = data.get('map', {}).get('country_label', '')
    obj = {}
    for sec in data.get('spot_sections', []):
        city = sec.get('city_name', '')
        for sp in sec.get('spots', []):
            num = sp.get('num', '')
            if not num:
                continue
            name = sp.get('name', '')
            desc = sp.get('desc', '')
            img  = sp.get('image', '') or ''
            if sp.get('map_url'):
                map_url = sp['map_url']
            elif sp.get('no_map'):
                map_url = ''
            else:
                q = ' '.join(x for x in [name, city, country_label] if x)
                map_url = 'https://maps.google.com/?q=' + urllib.parse.quote(q, safe='')
            obj[num] = {'num': num, 'name': name, 'desc': desc, 'img': img, 'mapUrl': map_url}
    # <script> 内に安全に埋め込めるよう '<' をエスケープ
    return json.dumps(obj, ensure_ascii=False).replace('<', '\\u003c')


# ──────────────────────────────────────────
# 国一覧 (index.html) 自動更新
# ──────────────────────────────────────────

def _esc(s):
    """JS文字列内のシングルクォートをエスケープ"""
    return str(s).replace("'", "\\'")

def update_index(country_id, data, root_dir):
    """
    index.html の COUNTRIES 配列に国カードを追加する（未登録の場合のみ）。
    JSON に index_card フィールドがない場合はスキップ。
    """
    card = data.get('index_card')
    if not card:
        return

    index_path = os.path.normpath(os.path.join(root_dir, 'index.html'))
    if not os.path.exists(index_path):
        print(f'  ⚠️  index.html が見つかりません: {index_path}')
        return

    with open(index_path, encoding='utf-8') as f:
        html = f.read()

    url = f"{country_id}/index.html"
    if f"url:'{url}'" in html:
        print(f'  ℹ️  国一覧: 登録済みのためスキップ')
        return

    # カード情報を組み立て
    name       = _esc(data.get('name', ''))
    name_en    = _esc(data.get('name_en', ''))
    flag       = _esc(card.get('flag', ''))
    catch_     = _esc(card.get('catch', ''))
    region     = _esc(card.get('region', ''))
    flight     = _esc(data.get('overview', {}).get('flight_hours', ''))
    best_label = _esc(card.get('best_label', ''))
    gradient   = _esc(card.get('gradient', ''))
    card_img   = _esc(f"{country_id}/{data.get('hero_image', '')}")
    budget_str = ','.join(f"'{b}'" for b in card.get('budget', []))
    months_str = ','.join(str(m) for m in card.get('best_months', []))
    tags_str   = ','.join(f"'{_esc(t)}'" for t in card.get('tags', []))

    new_entry = (
        f"  {{\n"
        f"    name:'{name}', nameEn:'{name_en}', flag:'{flag}',\n"
        f"    catch:'{catch_}',\n"
        f"    region:'{region}', flight:'{flight}', budget:[{budget_str}],\n"
        f"    bestMonths:[{months_str}], bestLabel:'{best_label}',\n"
        f"    tags:[{tags_str}],\n"
        f"    gradient:'{gradient}',\n"
        f"    cardImg:'{card_img}',\n"
        f"    url:'{url}', available:true\n"
        f"  }},\n"
    )

    # 最初の available:false ブロックの直前に挿入
    pos = html.find('available:false')
    if pos != -1:
        block_start = html.rfind('  {', 0, pos)
        if block_start == -1:
            print('  ⚠️  挿入位置が特定できませんでした')
            return
        html = html[:block_start] + new_entry + html[block_start:]
    else:
        # unavailable エントリがない場合は COUNTRIES 配列末尾へ
        arr_start = html.find('const COUNTRIES')
        end_pos   = html.find('];', arr_start)
        if end_pos == -1:
            print('  ⚠️  COUNTRIES配列が見つかりません')
            return
        html = html[:end_pos] + new_entry + html[end_pos:]

    import shutil
    shutil.copy2(index_path, index_path + '.bak')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  📋 国一覧に追加: {name}')


# ──────────────────────────────────────────
# メイン処理
# ──────────────────────────────────────────

def generate(country_id):
    tools_dir  = os.path.dirname(os.path.abspath(__file__))  # assets/tools/
    assets_dir = os.path.join(tools_dir, '..')               # assets/
    root_dir   = os.path.join(tools_dir, '..', '..')         # World guide/

    json_path = os.path.join(root_dir, country_id, f'{country_id}.json')
    tpl_path  = os.path.join(assets_dir, 'country_template.html')
    out_path  = os.path.join(root_dir, country_id, 'index.html')

    if not os.path.exists(json_path):
        print(f'❌ JSONファイルが見つかりません: {json_path}')
        sys.exit(1)
    if not os.path.exists(tpl_path):
        print(f'❌ テンプレートが見つかりません: {tpl_path}')
        sys.exit(1)

    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    with open(tpl_path, encoding='utf-8') as f:
        tpl = f.read()

    # ── グルメ・観光スポット画像の自動検出 ──────────────────────
    # 素材/グルメ/<料理名>.webp または 素材/観光スポット/<スポット名>.webp が
    # 存在すれば image フィールドを自動補完し JSON を更新する
    json_updated = False

    food_dir = os.path.join(root_dir, country_id, '素材', 'グルメ')
    for item in data.get('food_items', []):
        name     = item.get('name', '')
        img_path = os.path.join(food_dir, f'{name}.webp')
        rel_path = f'素材/グルメ/{name}.webp'
        if os.path.exists(img_path) and item.get('image') != rel_path:
            item['image'] = rel_path
            json_updated  = True
            print(f'  🖼️  グルメ画像を自動検出: {name}.webp')

    spot_dir = os.path.join(root_dir, country_id, '素材', '観光スポット')
    for section in data.get('spot_sections', []):
        for spot in section.get('spots', []):
            name     = spot.get('name', '')
            img_path = os.path.join(spot_dir, f'{name}.webp')
            rel_path = f'素材/観光スポット/{name}.webp'
            if os.path.exists(img_path) and spot.get('image') != rel_path:
                spot['image'] = rel_path
                json_updated  = True
                print(f'  🖼️  スポット画像を自動検出: {name}.webp')

    city_img_dir = os.path.join(root_dir, country_id, '素材', '都市')
    for section in data.get('spot_sections', []):
        city_id_key = section.get('city_id', '')
        if not city_id_key:
            continue
        img_path = os.path.join(city_img_dir, f'{city_id_key}.webp')
        rel_path = f'素材/都市/{city_id_key}.webp'
        if os.path.exists(img_path) and section.get('city_image') != rel_path:
            section['city_image'] = rel_path
            json_updated = True
            print(f'  🖼️  都市画像を自動検出: {city_id_key}.webp')

    if json_updated:
        import shutil
        shutil.copy2(json_path, json_path + '.bak')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'  💾 JSON更新: {os.path.basename(json_path)}')
    # ────────────────────────────────────────────────────────────

    data['__root_dir__'] = os.path.normpath(root_dir)

    country_dir = os.path.join(root_dir, country_id)
    os.makedirs(os.path.join(country_dir, '素材', 'グルメ'),       exist_ok=True)
    os.makedirs(os.path.join(country_dir, '素材', '観光スポット'), exist_ok=True)
    os.makedirs(os.path.join(country_dir, '素材', '都市'),         exist_ok=True)
    os.makedirs(os.path.join(country_dir, 'audio'),                exist_ok=True)

    SECTIONS = ['basic', 'spots', 'food', 'course', 'budget', 'practical', 'phrases']

    if data.get('multipage'):
        # ── 分割ページモード（タブごとに個別HTML） ──
        pages = [
            ('basic',     'index.html',     '基本情報'),
            ('spots',     'spots.html',     '観光スポット'),
            ('food',      'food.html',      'グルメ'),
            ('course',    'course.html',    'モデルコース'),
            ('budget',    'budget.html',    '予算・費用'),
            ('practical', 'practical.html', '旅の準備'),
            ('phrases',   'phrases.html',   'フレーズ'),
        ]
        base_title   = data.get('page_title', '')
        name         = data.get('name', '')
        spot_data_js = build_spot_data_js(data)
        for slug, outfile, label in pages:
            ctx = dict(data)
            ctx['multipage']       = True
            ctx['singlepage']      = False
            ctx['spot_data_js']    = spot_data_js
            ctx['show']            = {s: (s == slug) for s in SECTIONS}
            ctx['nav_active']      = {s: ('active' if s == slug else '') for s in SECTIONS}
            ctx['sec_active']      = {s: ('active' if s == slug else '') for s in SECTIONS}
            ctx['container_style'] = 'max-width:1000px' if slug in ('spots', 'food') else ''
            ctx['page_title']      = base_title if slug == 'basic' else f'{name}の{label}｜{base_title}'
            html = _render(tpl, ctx)
            with open(os.path.join(country_dir, outfile), 'w', encoding='utf-8') as f:
                f.write(html)
            print(f'  📄 {outfile}')
        print(f'✅ 生成完了（分割{len(pages)}ページ）: {country_dir}')
    else:
        # ── 従来モード（1枚のindex.htmlに全タブ） ──
        ctx = dict(data)
        ctx['multipage']       = False
        ctx['singlepage']      = True
        ctx['show']            = {s: True for s in SECTIONS}
        ctx['nav_active']      = {s: ('active' if s == 'basic' else '') for s in SECTIONS}
        ctx['sec_active']      = {s: ('active' if s == 'basic' else '') for s in SECTIONS}
        ctx['container_style'] = ''
        html = _render(tpl, ctx)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'✅ 生成完了: {out_path}')

    update_index(country_id, data, root_dir)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('使い方: python generate.py <country_id>')
        print('例:     python generate.py thailand')
        sys.exit(1)
    generate(sys.argv[1])
