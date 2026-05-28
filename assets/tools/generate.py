#!/usr/bin/env python3
"""
国ページ自動生成スクリプト
使い方:  python generate.py <country_id>
例:      python generate.py thailand

読み込み: <country_id>/<country_id>.json
         assets/country_template.html
出力:     <country_id>/index.html
"""
import json, re, os, sys


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

    if json_updated:
        import shutil
        shutil.copy2(json_path, json_path + '.bak')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'  💾 JSON更新: {os.path.basename(json_path)}')
    # ────────────────────────────────────────────────────────────

    html = _render(tpl, data)

    country_dir = os.path.join(root_dir, country_id)
    os.makedirs(os.path.join(country_dir, '素材', 'グルメ'),       exist_ok=True)
    os.makedirs(os.path.join(country_dir, '素材', '観光スポット'), exist_ok=True)
    os.makedirs(os.path.join(country_dir, 'audio'),                exist_ok=True)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'✅ 生成完了: {out_path}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('使い方: python generate.py <country_id>')
        print('例:     python generate.py thailand')
        sys.exit(1)
    generate(sys.argv[1])
