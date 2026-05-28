"""
WebP変換スクリプト
使い方: py convert_to_webp.py
素材フォルダ内のPNG/JPGを自動でWebPに変換します
"""

from PIL import Image
import os

# 変換対象フォルダ（サブフォルダも含む）
BASE_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

def convert_to_webp(folder):
    converted = 0
    for file in os.listdir(folder):
        name, ext = os.path.splitext(file)
        if ext.lower() not in ('.png', '.jpg', '.jpeg'):
            continue

        src = os.path.join(folder, file)
        dst = os.path.join(folder, name + '.webp')

        # すでにWebPが存在する場合はスキップ
        if os.path.exists(dst):
            print(f"  スキップ（既存）: {file}")
            continue

        img = Image.open(src)
        img.save(dst, 'webp', lossless=False, quality=85)
        size_before = os.path.getsize(src) // 1024
        size_after = os.path.getsize(dst) // 1024
        print(f"  変換完了: {file} ({size_before}KB → {size_after}KB)")
        converted += 1

    return converted

print("===== WebP変換スクリプト =====\n")

# 各国の素材フォルダを自動検索
total = 0
for country_folder in os.listdir(BASE_DIR):
    material_dir = os.path.join(BASE_DIR, country_folder, '素材')
    if os.path.isdir(material_dir):
        print(f"[{country_folder}/素材/]")
        count = convert_to_webp(material_dir)
        total += count

if total == 0:
    print("変換対象のファイルはありませんでした。")
else:
    print(f"\n完了: 合計 {total} ファイルを変換しました！")

input("\nEnterキーで終了...")
