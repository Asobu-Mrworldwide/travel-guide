"""
未生成スポット画像の一括生成スクリプト
使い方: python bulk_generate.py
"""
import json, sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from recraft_api import generate_image

BASE = os.path.join(os.path.dirname(__file__), '..', '..')

def run(country_id, city_id=None):
    json_path = os.path.join(BASE, country_id, f'{country_id}.json')
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    targets = []
    for sec in data.get('spot_sections', []):
        if city_id and sec['city_id'] != city_id:
            continue
        for s in sec['spots']:
            if not s.get('image') and s.get('prompt_en'):
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
                width=1024,
                height=1024,
                use_style=True
            )
            with open(out_path, 'wb') as f:
                f.write(img_bytes)
            # JSONのimageフィールドを更新
            s['image'] = f'素材/観光スポット/{name}.webp'
            print(f'完了（残{credits}cr）')
            time.sleep(1)
        except Exception as e:
            print(f'失敗: {e}')

    # JSON保存
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('JSONを更新しました')

if __name__ == '__main__':
    # 例: ペナンのみ生成
    run('malaysia', city_id='penang')
    # 全都市生成する場合: run('malaysia')
