"""
未生成画像（スポット・グルメ・ヒーロー）の一括生成スクリプト

使い方:
    python bulk_generate.py <country_id>                 # 見積もりのみ（生成しない）
    python bulk_generate.py <country_id> --yes           # スポット・グルメ・ヒーローを生成
    python bulk_generate.py <country_id> --yes --only spot   # spot / food / hero のどれか一つ
    python bulk_generate.py <country_id> --yes --city bali   # スポットを都市（city_id）で絞る

- 画像が未生成（imageが空、またはファイルが無い）で、prompt_en（ヒーローはhero_prompt）がある分だけが対象。
- Recraftクレジットを消費するため、--yes を付けない限り何も生成しない（見積もりだけ表示）。
- 使うスタイルは app.py の現行標準に合わせる（スポット・ヒーロー: style_spot_1101、グルメ: style_food_1101、各35cr）。
- 1枚ごとにJSONへ保存するので、途中で止めても生成済み分は失われない。
- 生成後は `python generate.py <country_id>` で反映し、生成された画像の見栄え（顔・手の崩れ、構図）を目視確認すること。
"""
import json, sys, os, time, argparse
sys.path.insert(0, os.path.dirname(__file__))

BASE = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

CREDITS_PER_IMAGE = 35
YEN_PER_CREDIT = 0.16


def _exists(country_id, rel):
    return bool(rel) and os.path.exists(os.path.join(BASE, country_id, rel))


def collect_targets(data, country_id, only=None, city_id=None):
    """生成対象を [(カテゴリ, 保存名, 画像を書き込む辞書, 生成設定)] で返す。"""
    targets = []
    if only in (None, 'spot'):
        for sec in data.get('spot_sections', []):
            if city_id and sec.get('city_id') != city_id:
                continue
            for s in sec.get('spots', []):
                if s.get('prompt_en') and not _exists(country_id, s.get('image')):
                    targets.append(('spot', s['name'], s, dict(
                        prompt=s['prompt_en'], plate_color='', model='style_spot_1101',
                        width=1820, height=1024, subdir='観光スポット')))
    if only in (None, 'food'):
        for it in data.get('food_items', []):
            if it.get('prompt_en') and not _exists(country_id, it.get('image')):
                targets.append(('food', it['name'], it, dict(
                    prompt=it['prompt_en'], plate_color=it.get('plate_color', ''),
                    model='style_food_1101', width=1024, height=1024, subdir='グルメ')))
    if only in (None, 'hero'):
        if data.get('hero_prompt') and not _exists(country_id, data.get('hero_image')):
            targets.append(('hero', 'ヒーロー', data, dict(
                prompt=data['hero_prompt'], plate_color='', model='style_spot_1101',
                width=1820, height=1024, subdir=None)))
    return targets


def run(country_id, only=None, city_id=None, execute=False):
    json_path = os.path.join(BASE, country_id, f'{country_id}.json')
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    targets = collect_targets(data, country_id, only, city_id)
    counts = {k: sum(1 for t in targets if t[0] == k) for k in ('spot', 'food', 'hero')}
    cr = len(targets) * CREDITS_PER_IMAGE
    print(f'未生成: スポット{counts["spot"]}枚 / グルメ{counts["food"]}枚 / ヒーロー{counts["hero"]}枚'
          f'（計{len(targets)}枚、約{cr}cr、約¥{cr * YEN_PER_CREDIT:,.0f}）')
    if not targets:
        return
    if not execute:
        print('見積もりのみです。生成するには --yes を付けて再実行してください。')
        return

    from recraft_api import generate_image
    failed = 0
    for i, (cat, name, holder, cfg) in enumerate(targets, 1):
        out_dir = os.path.join(BASE, country_id, '素材', *( [cfg['subdir']] if cfg['subdir'] else [] ))
        os.makedirs(out_dir, exist_ok=True)
        print(f'  [{i}/{len(targets)}] {cat}: {name} ...', end=' ', flush=True)
        try:
            img_bytes, credits = generate_image(
                prompt=cfg['prompt'], plate_color=cfg['plate_color'], model=cfg['model'],
                width=cfg['width'], height=cfg['height'], use_style=True)
            with open(os.path.join(out_dir, f'{name}.webp'), 'wb') as f:
                f.write(img_bytes)
            rel = f'素材/{cfg["subdir"]}/{name}.webp' if cfg['subdir'] else f'素材/{name}.webp'
            holder['hero_image' if cat == 'hero' else 'image'] = rel
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f'完了（残{credits}cr）')
            time.sleep(1)
        except Exception as e:
            failed += 1
            print(f'失敗: {e}')
    print(f'終了: 成功{len(targets) - failed} / 失敗{failed}。続けて generate.py {country_id} を実行してください。')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='未生成画像の一括生成')
    ap.add_argument('country_id')
    ap.add_argument('--yes', action='store_true', help='実際に生成する（クレジットを消費）')
    ap.add_argument('--only', choices=['spot', 'food', 'hero'])
    ap.add_argument('--city', help='スポットを絞る city_id')
    a = ap.parse_args()
    run(a.country_id, only=a.only, city_id=a.city, execute=a.yes)
