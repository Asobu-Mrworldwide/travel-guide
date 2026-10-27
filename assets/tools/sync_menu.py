"""ハンバーガーメニュー（右スライドのドロワー）の「共通部分」を、全ページへ同じ形で書き込む。

メニューは各HTMLに静的に書かれているため、手作業だと並び・名前がページごとにずれる。
ここで共通の骨組みを1か所に定義し、各ファイルのドロワー本体を書き換える（何度実行しても同じ結果になる）。

共通の骨組み（どのページでも同じ順番・同じ名前）:
  [ページ固有ブロック]  国ガイド: ○○を旅する + 近くの国 / 共通ページ: このページ(ページ内リンクがある場合のみ)
  エリアで探す / シーズンで探す / 旅行タイプ診断(未公開の間は診断ページのみ) / ツール(持ち物チェックリスト) / World Mappyについて

対象: assets/country_template.html（国ガイドの元。反映後に generate.py で全国を再生成する）、
      index.html、diagnosis/*.html、common/*.html

使い方:  python assets/tools/sync_menu.py
"""
import glob
import os
import re
import sys
from urllib.parse import quote

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# index.html の COUNTRIES/データのエリア順（destinations-data.js の area と同じ）
AREAS = ['東南アジア', '中央アジア', 'アフリカ', '東アジア', '南アジア', 'ヨーロッパ', 'オセアニア', '北アメリカ', '南米']
HOLIDAYS = ['正月', 'GW', 'お盆', 'シルバーウィーク']

# 旅行タイプ診断は未公開。False の間は、診断ページ自身のメニュー以外には診断へのリンクを出さない。
# 公開するときは True にして、このスクリプトと generate.py を実行する。
SHOW_DIAG_IN_PUBLIC_MENU = False

CHEV = '<span class="hb-item__chev" aria-hidden="true">&rsaquo;</span>'


def item(href, label):
    return ('<a class="hb-item" href="%s"><span class="hb-item__dot"></span>'
            '<span class="hb-item__label">%s</span>%s</a>') % (href, label, CHEV)


def accordion(sec, ident, label, panel_inner, expanded=False, primary=False, last=False):
    btn_cls = 'hb-sec--primary' if primary else 'hb-sec'
    if last:
        btn_cls += ' hb-sec--last'
    panel_cls = 'hb-panel' + (' hb-panel--primary' if primary else '')
    caret = '&#9650;' if expanded else '&#9660;'
    hidden = '' if expanded else ' hidden'
    if panel_inner:   # 読みやすいよう、項目ごとに改行して書き出す
        panel_inner = '\n      ' + panel_inner.replace('</a><a', '</a>\n      <a') + '\n    '
    return (
        '    <button class="%s" type="button" data-sec="%s" aria-expanded="%s" aria-controls="%s">\n'
        '      <span class="hb-sec__label">%s</span>\n'
        '      <span class="hb-sec__caret" aria-hidden="true">%s</span>\n'
        '    </button>\n'
        '    <div class="%s" id="%s"%s>%s</div>\n\n'
    ) % (btn_cls, sec, 'true' if expanded else 'false', ident, label, caret, panel_cls, ident, hidden, panel_inner)


def common_sections(kind, base, country=False):
    """kind: top / diag / common / country。base: 'common/' などを付ける前の相対パス('' か '../')"""
    out = ''
    if country:
        out += accordion('nearby', 'hbSecNearby', '近くの国', '<div id="hb-nearby"></div>')

    # エリア・シーズン：トップはページ内フィルタ(index.htmlのJSが中身を作る)、他ページは index.html へのリンク
    if kind == 'top':
        area_inner, season_inner = '', ''
    else:
        area_inner = ''.join(item('%sindex.html?region=%s#wm-index' % (base, quote(a)), a) for a in AREAS)
        season_inner = ''.join(item('%sindex.html?season=%s#wm-index' % (base, quote(h)), h) for h in HOLIDAYS)
    out += accordion('area', 'hbSecArea', 'エリアで探す', area_inner, expanded=(kind == 'top'), primary=(kind == 'top'))
    out += accordion('season', 'hbSecSeason', 'シーズンで探す', season_inner)

    if kind == 'diag' or SHOW_DIAG_IN_PUBLIC_MENU:
        diag_inner = item(base + 'diagnosis/index.html', '診断を受ける') + item(base + 'diagnosis/types.html', '旅行タイプ一覧')
        out += accordion('diag', 'hbSecDiag', '旅行タイプ診断', diag_inner, expanded=(kind == 'diag'))

    # 直接リンクだと誤タップしやすいので、「ツール」の中に入れる（今後ツールが増えたらここに足す）
    checklist_href = base + 'common/checklist.html' + ('?from={{id}}' if country else '')
    out += accordion('tools', 'hbSecTools', 'ツール', item(checklist_href, '持ち物チェックリスト'))

    about = ''.join('<a href="%scommon/%s.html">%s →</a>' % (base, f, l) for f, l in [
        ('about', '運営者情報'), ('faq', 'よくある質問'), ('contact', 'お問い合わせ'),
        ('disclaimer', '免責事項'), ('privacy', 'プライバシーポリシー')])
    out += accordion('about', 'hbSecAbout', 'World Mappyについて', '<div class="hb-about">\n        %s\n      </div>' % about.replace('</a><a', '</a>\n        <a'), last=True)
    return out


def split_body(s):
    """ドロワー本体 <div class="hb-drawer__body"> の中身の範囲(start,end)を返す。
    終端は .hb-cta-wrap の直前、なければ本体を閉じる </div>（</aside> の直前）の手前。"""
    a = s.find('<div class="hb-drawer__body">')
    if a < 0:
        return None
    start = a + len('<div class="hb-drawer__body">')
    cta = s.find('<div class="hb-cta-wrap">', start)
    aside = s.find('</aside>', start)
    if 0 <= cta < aside:
        end = cta
    else:
        end = s.rfind('</div>', start, aside)
    return start, end


def page_specific(path, body):
    """ページ固有ブロック（最初の1つ）をそのまま取り出す。なければ空文字。"""
    name = os.path.basename(path)
    if name == 'country_template.html':
        # 最初のアコーディオン(○○を旅する)だけがページ固有。2つ目のボタンの手前までを取る（再実行しても増えない）
        starts = [m.start() for m in re.finditer(r'<button class="hb-sec(?:--primary)?"', body)]
        return body[:starts[1]] if len(starts) > 1 else body
    m = re.search(r'<button class="hb-sec--primary"[^>]*data-sec="page"[^>]*>\s*<span class="hb-sec__label">([^<]*)', body)
    if not m:
        return ''
    # 「このページ」「持ち物チェックリスト」はページ内リンク(#...)を持つ固有ブロック。それ以外(旅行タイプ診断/旅のガイド)は共通側へ移す。
    if m.group(1) in ('このページ', '持ち物チェックリスト') and '<a class="hb-item" href="#' in body:
        j = body.find('<button class="hb-sec"', m.start())
        return body[:j] if j >= 0 else body
    return ''


def sync(path):
    s = open(path, encoding='utf-8').read()
    rng = split_body(s)
    if not rng:
        return None
    start, end = rng
    body = s[start:end]
    rel = os.path.relpath(path, ROOT).replace('\\', '/')
    folder = rel.split('/')[0] if '/' in rel else ''
    if rel == 'assets/country_template.html':
        kind, base, country = 'country', '../', True
    elif rel == 'index.html':
        kind, base, country = 'top', '', False
    elif folder == 'diagnosis':
        kind, base, country = 'diag', '../', False
    else:
        kind, base, country = 'common', '../', False
    specific = page_specific(rel, body)
    new_body = '\n\n    ' + specific.strip() + '\n\n' if specific.strip() else '\n\n'
    new_body += common_sections(kind, base, country)
    new_body = new_body.rstrip('\n') + '\n\n    '
    new_s = s[:start] + new_body + s[end:]
    if new_s != s:
        open(path, 'w', encoding='utf-8', newline='').write(new_s)
        return True
    return False


def main():
    targets = ['assets/country_template.html', 'index.html'] + sorted(glob.glob(os.path.join(ROOT, 'diagnosis', '*.html'))) \
        + sorted(glob.glob(os.path.join(ROOT, 'common', '*.html')))
    for t in targets:
        p = t if os.path.isabs(t) else os.path.join(ROOT, t)
        r = sync(p)
        print('%-40s %s' % (os.path.relpath(p, ROOT), {None: '（ドロワーなし）', True: '更新', False: '変更なし'}[r]))


if __name__ == '__main__':
    sys.exit(main())
