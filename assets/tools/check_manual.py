"""旅人取扱説明書（diagnosis/manual-data.js）の文字数チェック。

表面（使用方法）と裏面（上手な使い方・禁止事項・充電方法・よくある質問・保証と免責）の
各項目に文字数の目安を設け、タイプ間で用紙の高さがそろうようにする。
使い方: python assets/tools/check_manual.py
"""
import re, os, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

# 項目 -> (下限, 上限)。実データ16タイプの中央値付近を基準にしている（2026-11制定）
RANGES = {
    'usage':             (75, 100),   # 使用方法（表面）
    'good1':             (30, 40),    # 上手な使い方 1つ目
    'good2':             (25, 35),    # 上手な使い方 2つ目
    'ban':               (38, 50),    # 禁止事項
    'charge:充電スポット':  (4, 10),
    'charge:所要時間':     (2, 6),
    'charge:満充電のサイン': (12, 18),
    'qa1Q':              (14, 20),    # よくある質問 1問目の質問
    'qa1A':              (32, 42),    # 　　　　　　　　 回答
    'qa2Q':              (12, 19),    # 2問目の質問
    'qa2A':              (22, 35),    # 　　　　 回答
    'waiver':            (27, 40),    # 保証と免責
}

def load():
    s = open(os.path.join(ROOT, 'diagnosis', 'manual-data.js'), encoding='utf-8').read()
    blocks = re.split(r"\n  ([A-Z]{4}): \{", s)
    for i in range(1, len(blocks), 2):
        code, b = blocks[i], blocks[i + 1]
        items = {'usage': re.search(r"usage: '(.*?)',\n", b, re.S).group(1)}
        g = re.findall(r"\n      '(.*?)',", '\n' + re.search(r"good: \[(.*?)\n    \],", b, re.S).group(1))
        items['good1'], items['good2'] = g[0], g[1]
        items['ban'] = re.findall(r"'(.*?)',", re.search(r"ban: \[(.*?)\n    \],", b, re.S).group(1))[0]
        for k, v in re.findall(r"\['(.*?)',\s*'(.*?)'\]", re.search(r"charge: \[(.*?)\n    \],", b, re.S).group(1)):
            items['charge:' + k] = v
        qa = re.findall(r"\['(.*?)',\s*'(.*?)'\]", re.search(r"qa: \[(.*?)\n    \],", b, re.S).group(1))[:2]   # 表示は2問まで
        items['qa1Q'], items['qa1A'] = qa[0]
        items['qa2Q'], items['qa2A'] = qa[1]
        items['waiver'] = re.search(r"waiver: '(.*?)',", b).group(1)
        yield code, items

def main():
    issues = []
    for code, items in load():
        if not re.fullmatch(r'[^。（）]+は、保証対象外です。（[^（）]+）', items['waiver']):
            issues.append(f'[{code} waiver 型違い（「〜は、保証対象外です。（本人の様子）」）] {items["waiver"]}')
        for k, (lo, hi) in RANGES.items():
            n = len(items.get(k, ''))
            if not lo <= n <= hi:
                issues.append(f'[{code} {k} {n}字, 目安{lo}-{hi}] {items.get(k, "")}')
    if issues:
        print(f'=== manual-data: NG {len(issues)}件 ===')
        print('\n'.join(issues))
        sys.exit(1)
    print('=== manual-data: NGなし ===')

if __name__ == '__main__':
    main()
