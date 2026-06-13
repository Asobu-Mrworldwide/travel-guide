"""
指定スポットを除く全観光スポット画像を再生成（上書き）
"""
import json, sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from recraft_api import generate_image

BASE = r'C:\Users\Asobu\Documents\海外情報サイト\World guide'

EXCLUDE_NAMES = {'アイコンサイアム', 'エレファントサンクチュアリ', 'パトンビーチ', 'ノンノク・ガーデン', 'シミラン諸島'}

# 既に今回の実行で生成済み（スキップ）
ALREADY_DONE = {
    'ワット・プラケオ（エメラルド寺院）', '王宮（グランドパレス）',
    'ワット・ポー（涅槃仏寺院）', 'ワット・アルン（暁の寺）',
    'カオサン通り', 'チャトゥチャック週末市場', 'ルーフトップバー',
    'ナイトマーケット', 'ワット・ドイステープ', '旧市街・お堀',
    'サンデー＆サタデーナイトバザール', 'チェンマイ花祭り（2月）', 'タイ古式マッサージ',
}

def run(country_id):
    json_path = os.path.join(BASE, country_id, f'{country_id}.json')
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    targets = []
    for sec in data.get('spot_sections', []):
        for s in sec['spots']:
            name = s['name']
            if not s.get('prompt_en'):
                continue
            # 除外チェック（部分一致）
            if any(ex in name for ex in EXCLUDE_NAMES):
                continue
            if name in ALREADY_DONE:
                continue
            targets.append(s)

    print(f'{len(targets)}件を生成します')
    for s in targets:
        name = s['name']
        prompt = s['prompt_en']
        out_path = os.path.join(BASE, country_id, '素材', '観光スポット', f'{name}.webp')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        print(f'  生成中: {name} ...', end=' ', flush=True)
        try:
            img_bytes, credits = generate_image(
                prompt=prompt,
                plate_color='',
                model='style_spot',
                width=1820,
                height=1024,
                use_style=True
            )
            with open(out_path, 'wb') as f:
                f.write(img_bytes)
            s['image'] = f'素材/観光スポット/{name}.webp'
            print(f'完了（残{credits}cr）')
            time.sleep(1)
        except Exception as e:
            print(f'失敗: {e}')

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('JSONを更新しました')

if __name__ == '__main__':
    run('thailand')
