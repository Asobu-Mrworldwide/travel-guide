"""
sitemap.xml をサイト全体の実ページ構成から機械的に生成する。
使い方: python assets/tools/gen_sitemap.py
"""
import datetime
import os

SITE_BASE_URL = 'https://worldmappy.com'
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

NON_COUNTRY_DIRS = {'assets', 'common', 'compare', 'diagnosis', '.git', '__pycache__'}

# 準備中の国（ページ・JSONはあるが未公開＝サイトマップに載せない）。公開時にここから外す。
DRAFT_COUNTRIES = {'indonesia'}

def _discover_countries():
    """<dir>/<dir>.json が存在するトップレベルディレクトリを国ページとして自動検出する"""
    countries = []
    for name in sorted(os.listdir(ROOT)):
        if name in NON_COUNTRY_DIRS or name in DRAFT_COUNTRIES or name.startswith('.'):
            continue
        country_dir = os.path.join(ROOT, name)
        if os.path.isdir(country_dir) and os.path.isfile(os.path.join(country_dir, f'{name}.json')):
            countries.append(name)
    return countries

COUNTRY_PAGES = [
    ('index.html', '', 0.9, 'weekly'),
    ('budget.html', 'budget.html', 0.7, 'monthly'),
    ('course.html', 'course.html', 0.7, 'monthly'),
    ('food.html', 'food.html', 0.7, 'monthly'),
    ('phrases.html', 'phrases.html', 0.7, 'monthly'),
    ('practical.html', 'practical.html', 0.7, 'monthly'),
    ('spots.html', 'spots.html', 0.7, 'monthly'),
]

OTHER_PAGES = [
    ('common/checklist.html', 0.6, 'monthly'),
    ('common/contact.html', 0.3, 'yearly'),
    ('common/privacy.html', 0.3, 'yearly'),
    ('compare/flights.html', 0.5, 'monthly'),
    ('compare/hotels.html', 0.5, 'monthly'),
    ('compare/sim.html', 0.5, 'monthly'),
    # 診断ページは未公開のためサイトマップから除外（公開時に復帰）
    # ('diagnosis/index.html', 0.6, 'monthly'),
    # ('diagnosis/types.html', 0.6, 'monthly'),
]

def build():
    today = datetime.date.today().isoformat()
    urls = [(f'{SITE_BASE_URL}/', 1.0, 'weekly')]

    for country in _discover_countries():
        for _, suffix, priority, freq in COUNTRY_PAGES:
            loc = f'{SITE_BASE_URL}/{country}/{suffix}'
            urls.append((loc, priority, freq))

    for path, priority, freq in OTHER_PAGES:
        urls.append((f'{SITE_BASE_URL}/{path}', priority, freq))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, priority, freq in urls:
        lines.append('  <url>')
        lines.append(f'    <loc>{loc}</loc>')
        lines.append(f'    <lastmod>{today}</lastmod>')
        lines.append(f'    <changefreq>{freq}</changefreq>')
        lines.append(f'    <priority>{priority}</priority>')
        lines.append('  </url>')
    lines.append('</urlset>')
    lines.append('')

    out_path = os.path.join(ROOT, 'sitemap.xml')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'sitemap.xml generated: {len(urls)} URLs')

if __name__ == '__main__':
    build()
