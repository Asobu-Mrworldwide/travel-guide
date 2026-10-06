"""
Recraft 画像生成管理アプリ
起動: python -m streamlit run assets/tools/app.py
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import requests
import streamlit as st
from PIL import Image

import recraft_api
from rembg import remove as rembg_remove, new_session as rembg_new_session

@st.cache_resource
def _get_rembg_session():
    """起動時に1回だけモデルをロードしてキャッシュ"""
    return rembg_new_session("birefnet-general")  # 高精度モデル（BiRefNet）

# ──────────────────────────────────────────────────────────
# パス定義
# ──────────────────────────────────────────────────────────
TOOLS_DIR   = Path(__file__).parent          # assets/tools/
ASSETS_DIR  = TOOLS_DIR.parent              # assets/
ROOT_DIR    = ASSETS_DIR.parent             # World guide/
GENERATE_PY = TOOLS_DIR / "generate.py"
LAST_STATE  = TOOLS_DIR / ".last_state.json"
TEMP_DIR    = TOOLS_DIR / ".gen_temp"
TEMP_DIR.mkdir(exist_ok=True)
GEN_ARCHIVE = TOOLS_DIR / "generated_images"
GEN_ARCHIVE.mkdir(exist_ok=True)


import uuid as _uuid

def _temp_save(item: dict) -> dict:
    """gen_results の1件をディスクに一時保存してtmp_idを付与して返す"""
    tid = item.get("tmp_id") or _uuid.uuid4().hex[:10]
    (TEMP_DIR / f"{tid}.webp").write_bytes(item["bytes"])
    # generated_images フォルダにカテゴリ別で自動アーカイブ
    import datetime as _dt
    _ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    _cat = st.session_state.get("gen_category_global", "")
    if "ヒーロー" in _cat:
        _sub = "ヒーロー"
    elif "観光スポット" in _cat:
        _sub = "観光スポット"
    elif "グルメ" in _cat:
        _sub = "グルメ"
    else:
        _sub = "その他"
    _archive_dir = GEN_ARCHIVE / _sub
    _archive_dir.mkdir(exist_ok=True)
    (_archive_dir / f"{_ts}_{tid}.webp").write_bytes(item["bytes"])
    # original_bytes がある場合は別ファイルに保存
    if "original_bytes" in item:
        (TEMP_DIR / f"{tid}_orig.webp").write_bytes(item["original_bytes"])
    meta = {k: v for k, v in item.items() if k not in ("bytes", "original_bytes")}
    meta["tmp_id"] = tid
    if "original_bytes" in item:
        meta["has_original"] = True
    (TEMP_DIR / f"{tid}.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return {**item, "tmp_id": tid}


def _temp_delete(tmp_id: str):
    """一時ファイルを削除"""
    for ext in (".webp", ".json", "_orig.webp"):
        p = TEMP_DIR / f"{tmp_id}{ext}"
        if p.exists():
            p.unlink()


def _temp_load_all() -> list[dict]:
    """起動時に一時ファイルを全件読み込む"""
    results = []
    for meta_path in sorted(TEMP_DIR.glob("*.json")):
        img_path = meta_path.with_suffix(".webp")
        if not img_path.exists():
            continue
        try:
            meta  = json.loads(meta_path.read_text(encoding="utf-8"))
            bdata = img_path.read_bytes()
            # original_bytes の復元
            orig_path = TEMP_DIR / f"{meta.get('tmp_id', '')}_orig.webp"
            if orig_path.exists():
                meta["original_bytes"] = orig_path.read_bytes()
            results.append({**meta, "bytes": bdata})
        except Exception:
            pass
    return results


def to_webp(image_bytes: bytes, quality: int = 85) -> bytes:
    """PNG / JPG バイナリを WebP バイナリに変換する（透過チャンネル保持）"""
    img = Image.open(io.BytesIO(image_bytes))
    buf = io.BytesIO()
    img.save(buf, format="webp", lossless=False, quality=quality)
    return buf.getvalue()


def load_last_state() -> dict:
    try:
        return json.loads(LAST_STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_last_state(state: dict):
    """既存ステートにマージして保存（指定したキーのみ上書き）"""
    try:
        existing = load_last_state()
        existing.update(state)
        LAST_STATE.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


# ──────────────────────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────────────────────
def _run_generate(cid: str) -> tuple[int, str, str]:
    """generate.py を実行して (returncode, stdout, stderr) を返す"""
    try:
        r = subprocess.run(
            [sys.executable, "-X", "utf8", str(GENERATE_PY), cid],
            capture_output=True,
            cwd=str(TOOLS_DIR),
        )
        return r.returncode, r.stdout.decode("utf-8", errors="replace"), r.stderr.decode("utf-8", errors="replace")
    except Exception as e:
        return -1, "", str(e)


def detect_countries() -> list[str]:
    """ROOT_DIR 直下で <name>.json が存在するフォルダを列挙"""
    result = []
    for d in sorted(ROOT_DIR.iterdir()):
        if d.is_dir() and (d / f"{d.name}.json").exists():
            result.append(d.name)
    return result


def load_json(country_id: str) -> dict:
    path = ROOT_DIR / country_id / f"{country_id}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(country_id: str, data: dict):
    path = ROOT_DIR / country_id / f"{country_id}.json"
    shutil.copy2(path, path.with_suffix(".json.bak"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def image_exists(country_id: str, item: dict) -> bool:
    img = item.get("image", "")
    if not img:
        return False
    return (ROOT_DIR / country_id / img).exists()


def food_dir(country_id: str) -> Path:
    return ROOT_DIR / country_id / "素材" / "グルメ"


# ──────────────────────────────────────────────────────────
# 広告管理タブ用のヘルパー
# ──────────────────────────────────────────────────────────
import affiliates_data_io as aff_io
from audit_affiliates import compute_usage as aff_compute_usage, write_usage_report as aff_write_usage_report

AFF_ATTR_BY_CONST = {
    "AFFILIATES": ("data-affiliate", "affiliate"),
    "AFFILIATE_CARDS": ("data-affiliate-card", "affiliate-card"),
    "BOOKING_BOXES": ("data-affiliate-box", "affiliate-box"),
    "SIDE_BANNERS": ("data-affiliate-side", "affiliate-side"),
}


# ──────────────────────────────────────────────────────────
# 広告プレビューの描画（iframeを使わず、affiliates.jsのロジックをPythonに移植して
# st.markdown に直接描画する。iframeだと固定高さ・スクロールバーで見た目が崩れるため）
# ──────────────────────────────────────────────────────────
AFF_PREVIEW_SCOPE = "wm-adprev"
AFF_SITE_BASE = "https://worldmappy.com/"  # ../assets/... 等の相対パス解決用


def _aff_scope_css(css: str, scope_selector: str) -> str:
    """CSSの各セレクタに scope_selector を前置して、ページ全体への影響を防ぐ
    （style.css の `.container` のような汎用的なクラス名が管理画面側と衝突しないようにする）。
    @media/@supports は中身を再帰的にスコープし、@keyframes等はそのまま通す。"""
    out = []
    i, n = 0, len(css)
    while i < n:
        if css[i:i + 2] == "/*":
            end = css.find("*/", i + 2)
            end = n if end == -1 else end + 2
            i = end
            continue
        brace = css.find("{", i)
        semi = css.find(";", i)
        if brace == -1:
            i = n
            break
        if semi != -1 and semi < brace:
            i = semi + 1
            continue
        selector = css[i:brace]
        depth, j = 1, brace + 1
        while depth > 0 and j < n:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
            j += 1
        body = css[brace + 1:j - 1]
        sel = selector.strip()
        if sel.startswith("@media") or sel.startswith("@supports"):
            out.append(f"{selector}{{{_aff_scope_css(body, scope_selector)}}}")
        elif sel.startswith("@"):
            pass  # @keyframes / @font-face 等は影響が限定的なのでそのまま捨てる（重複防止）
        else:
            parts = []
            for p in selector.split(","):
                p = p.strip()
                if not p:
                    continue
                parts.append(scope_selector if p in (":root", "html", "body", "*") else f"{scope_selector} {p}")
            if parts:
                out.append(",".join(parts) + "{" + body + "}")
        i = j
    return "".join(out)


@st.cache_data(show_spinner=False)
def _aff_preview_css() -> str:
    """style.css と affiliates.js内のAFFILIATES_CSSを合体してスコープ付きCSSを作る（キャッシュ）"""
    site_css = (ASSETS_DIR / "style.css").read_text(encoding="utf-8")
    js_text = (ASSETS_DIR / "affiliates.js").read_text(encoding="utf-8")
    m = re.search(r"const AFFILIATES_CSS = `(.*?)`;", js_text, re.S)
    aff_css = m.group(1) if m else ""
    return _aff_scope_css(site_css + "\n" + aff_css, f".{AFF_PREVIEW_SCOPE}")


def _aff_fix_relative_paths(html: str) -> str:
    """'../assets/...' のような相対パスを実サイトの絶対URLに書き換える"""
    return re.sub(r'(src|href)="\.\./([^"]*)"', rf'\1="{AFF_SITE_BASE}\2"', html)


def aff_get_entry(const_name: str, key: str) -> dict | None:
    """affiliates-data.js から既存エントリ1件をPythonのdictとして取得する（JS object literal → dict）"""
    import json5
    js_text = aff_io.read_data_js_text()
    entries = aff_io.extract_top_level_entries(js_text, const_name)
    body = entries.get(key)
    if body is None:
        return None
    try:
        return json5.loads("{" + body + "}")
    except Exception:
        return None


def _aff_render_link(v: dict) -> str:
    return f'<a href="{v.get("url", "")}" target="_blank" rel="noopener" class="budget-link" style="text-align:left;width:auto">{v.get("label", "")}</a>'


def _aff_render_card(c: dict) -> str:
    icon, name, tagline = c.get("icon", ""), c.get("name", ""), c.get("tagline", "")
    logo, name_large = c.get("logo", ""), c.get("name_large")
    desc, note, btn, url, color = c.get("desc", ""), c.get("note", ""), c.get("btn", ""), c.get("url", ""), c.get("color", "#006847")
    points_html = "".join(f"<li>{p}</li>" for p in c.get("points", []))
    # affiliates.js の buildAffCard() と同じ分岐: logo優先 → name_large → icon+name+tagline
    if logo:
        header_inner = f'<div style="line-height:1">{logo}</div>'
    elif name_large:
        header_inner = (
            f'<div><div style="display:flex;align-items:center;gap:10px">'
            f'<span class="aff-card-icon">{icon}</span>'
            f'<div class="aff-card-name" style="font-size:1.5em;line-height:1">{name}</div>'
            f'</div><div class="aff-card-tagline" style="margin-top:4px">{tagline}</div></div>'
        )
    else:
        header_inner = (
            f'<div style="display:flex;align-items:center;gap:10px">'
            f'<span class="aff-card-icon">{icon}</span>'
            f'<div><div class="aff-card-name">{name}</div><div class="aff-card-tagline">{tagline}</div></div>'
            f'</div>'
        )
    return f'''<div class="aff-card">
  <div class="aff-card-header" style="display:flex;align-items:center;justify-content:space-between">
    {header_inner}
  </div>
  <div class="aff-card-body">
    {f'<p style="font-size:0.82em;color:var(--sub);line-height:1.7;margin:0 0 12px">{desc}</p>' if desc else ''}
    <ul class="aff-card-points">{points_html}</ul>
    {f'<div class="aff-card-note">{note}</div>' if note else ''}
    <a href="{url}" target="_blank" rel="noopener" class="aff-card-btn" style="background:{color}">{btn}</a>
  </div>
</div>'''


def _aff_render_booking_box(box: dict) -> str:
    buttons_html = ""
    for b in box.get("buttons", []):
        desc = f'<p class="booking-btn-desc">{b["desc"]}</p>' if b.get("desc") else ""
        buttons_html += f'<div class="booking-btn-group">{desc}<a href="{b.get("url", "")}" target="_blank" rel="noopener" class="btn-booking {b.get("className", "")}">{b.get("label", "")}</a></div>'
    return f'<div class="booking-box"><h3 class="booking-title">{box.get("title", "")}</h3><div class="booking-buttons">{buttons_html}</div></div>'


def _aff_render_side_banner(v: dict) -> str:
    w, h = v.get("width", 300), v.get("height", 250)
    html = (
        f'<a href="{v.get("url", "")}" target="_blank" rel="noopener nofollow">'
        f'<img src="{v.get("img", "")}" width="{w}" height="{h}" alt="{v.get("alt", "")}" '
        f'style="width:100%;height:auto;border-radius:6px;display:block"></a>'
    )
    if v.get("pixel"):
        html += f'<img src="{v["pixel"]}" width="1" height="1" alt="" style="border:none;position:absolute;width:1px;height:1px">'
    return html


def aff_render_preview(const_name: str, value: dict):
    """広告1件のプレビューをiframeなしでそのままページに描画する（st.markdown直書き）"""
    renderers = {
        "AFFILIATES": _aff_render_link,
        "AFFILIATE_CARDS": _aff_render_card,
        "BOOKING_BOXES": _aff_render_booking_box,
        "SIDE_BANNERS": _aff_render_side_banner,
    }
    renderer = renderers.get(const_name)
    if not renderer:
        return
    inner = _aff_fix_relative_paths(renderer(value))
    # st.markdownはMarkdownパーサーを通すため、改行+インデント入りのHTMLを渡すと
    # 4スペース以上のインデント行がコードブロック扱いされてタグが素通しされず文字化けする。
    # 改行を潰して1行にまとめ、Markdown側に解釈させず素のHTMLとして扱わせる。
    inner = re.sub(r"\n\s*", "", inner)
    # 実サイトの幅に合わせる：サイドレール 300px − 左右パディング18px×2 = 264px、本文 740px − 左右28px×2 = 684px
    max_w = "264px" if const_name == "SIDE_BANNERS" else "684px"
    st.markdown(f"<style>{_aff_preview_css()}</style>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="{AFF_PREVIEW_SCOPE}" style="max-width:{max_w};margin:4px 0 4px;'
        f"font-family:'Hiragino Kaku Gothic ProN','Noto Sans JP',sans-serif\">{inner}</div>",
        unsafe_allow_html=True,
    )


def aff_validate_required(const_name: str, value: dict) -> bool:
    if not value.get("brand"):
        return False
    if const_name == "AFFILIATES":
        return all(value.get(f) for f in ("name", "label", "url"))
    if const_name == "AFFILIATE_CARDS":
        return all(value.get(f) for f in ("icon", "name", "tagline", "btn", "url", "color")) and bool(value.get("points"))
    if const_name == "BOOKING_BOXES":
        return bool(value.get("title")) and bool(value.get("buttons"))
    if const_name == "SIDE_BANNERS":
        return all(value.get(f) for f in ("name", "img", "url", "width", "height"))
    return False


def aff_read_brand_map() -> dict:
    """affiliates-data.js を走査し、ブランド名 -> [(const_name, key), ...] を返す"""
    js_text = (ASSETS_DIR / "affiliates-data.js").read_text(encoding="utf-8")
    brand_map: dict[str, list[tuple[str, str]]] = {}
    for const_name in ("AFFILIATES", "BOOKING_BOXES", "AFFILIATE_CARDS", "SIDE_BANNERS"):
        entries = aff_io.extract_top_level_entries(js_text, const_name)
        for key, body in entries.items():
            m = re.search(r"brand:\s*'((?:[^'\\]|\\.)*)'", body)
            brand = m.group(1).replace("\\'", "'") if m else "その他"
            brand_map.setdefault(brand, []).append((const_name, key))
    return brand_map


def _aff_parse_raw_tag(raw_tag: str) -> dict | None:
    """貼り付けられた広告タグ（<a><img>やテキストリンク）から種類・項目を自動判別する"""
    raw_tag = raw_tag.strip()
    if not raw_tag:
        return None

    def _attr(tag_str, name):
        m = re.search(name + r'="([^"]*)"', tag_str, re.I)
        return m.group(1) if m else ""

    _imgs = re.findall(r'<img\s+([^>]*)>', raw_tag, re.I)
    _hrefs = re.findall(r'<a\s+[^>]*href="([^"]+)"', raw_tag, re.I)

    # 画像タグがあれば、1x1の計測ピクセル以外の「実体のある画像」を探す
    _banner_img, _bw, _bh = "", "", ""
    for _t in _imgs:
        _w, _h, _src = _attr(_t, "width"), _attr(_t, "height"), _attr(_t, "src")
        if not _src:
            continue
        if _w in ("1", "0") or _h in ("1", "0"):
            continue  # 計測ピクセルはバナー画像扱いしない
        if not _banner_img:
            _banner_img, _bw, _bh = _src, _w, _h

    if _banner_img and _hrefs:
        # 実体のあるバナー画像が見つかった → 画像バナーとして解析
        _pixel_img = next(
            (_attr(_t, "src") for _t in _imgs
             if _attr(_t, "width") in ("1", "0") or _attr(_t, "height") in ("1", "0")),
            "",
        )
        return {
            "kind": "banner", "img": _banner_img, "url": _hrefs[0], "pixel": _pixel_img,
            "width": int(_bw) if _bw.isdigit() else 0, "height": int(_bh) if _bh.isdigit() else 0,
        }

    # 実体のあるバナー画像がない（計測ピクセルのみ、または画像なし）→ テキストリンクとして扱う
    _url = _hrefs[0] if _hrefs else (raw_tag if re.match(r'^https?://\S+$', raw_tag) else "")
    if _url:
        # <a>タグの中身（表示テキスト）があれば、ASP側が用意した実際の文言をそのまま使う
        _anchor_m = re.search(r'<a\s+[^>]*href="[^"]+"[^>]*>(.*?)</a>', raw_tag, re.I | re.S)
        _anchor_text = re.sub(r'<[^>]+>', '', _anchor_m.group(1)).strip() if _anchor_m else ""
        return {"kind": "link", "url": _url, "text": _anchor_text}
    return None


def _aff_auto_key(brand: str, kind: str, url: str, taken: set) -> str:
    """キーを `{brand}_{banner|text}_{n}` 形式で自動採番する（ブランドが英数字でなければURLのドメインで代用）"""
    from urllib.parse import urlparse
    base = re.sub(r"[^a-z0-9]+", "_", (brand or "").lower()).strip("_")
    if not base:
        host = urlparse(url).netloc.lower()
        base = re.sub(r"[^a-z0-9]+", "_", host).strip("_") or "ad"
    if not base[0].isalpha():
        base = "ad_" + base
    kind_s = "banner" if kind == "banner" else "text"
    n = 1
    while f"{base}_{kind_s}_{n}" in taken:
        n += 1
    return f"{base}_{kind_s}_{n}"


def aff_registration_form(default_brand: str | None, key_prefix: str):
    """広告エントリ登録フォーム。default_brand を渡すとブランド名を固定して追加できる。
    保存できたら True を返す（呼び出し側で rerun・キャッシュ破棄などを行う）"""
    if default_brand is not None:
        brand = default_brand
        st.caption(f"ブランド「{brand}」に追加します")
    else:
        brand = st.text_input("ブランド名（新規）", key=f"{key_prefix}_brand").strip()

    st.caption(
        "ASPサイトでコピーした広告タグ（`<a>...<img>...</a>`）や、アフィリエイトのURLを貼り付けてください。"
        "複数まとめて登録する場合は、1件ごとに空行（改行2回）で区切ってください。"
    )
    raw_tag = st.text_area(
        "広告タグ／URLを貼り付け（複数は空行区切り）", key=f"{key_prefix}_raw_tag", height=140,
        placeholder='<a href="...">...<img ... src="..."></a>\n\nhttps://...\n\nhttps://...',
    )

    # ASPの埋め込みコードはhref/src等の属性値の途中に改行が混入していることがある
    # （a8.net等でよく発生）ため、引用符内の改行は先に除去してから分割する
    _normalized = re.sub(r'"[^"]*"', lambda m: m.group(0).replace("\n", "").replace("\r", ""),
                          raw_tag.strip(), flags=re.S)
    _chunks = [c.strip() for c in re.split(r"\n\s*\n", _normalized)] if _normalized else []
    _chunks = [c for c in _chunks if c]
    _items = []
    _taken_by_const: dict[str, set] = {}
    for _chunk in _chunks:
        _p = _aff_parse_raw_tag(_chunk)
        if not _p:
            _items.append({"ok": False, "raw": _chunk})
            continue
        if _p["kind"] == "banner":
            _cn = "SIDE_BANNERS"
            _v = {
                "brand": brand, "name": brand, "alt": brand,
                "img": _p["img"], "url": _p["url"],
                "width": _p["width"], "height": _p["height"],
            }
            if _p["pixel"]:
                _v["pixel"] = _p["pixel"]
        else:
            _cn = "AFFILIATES"
            _label = _p.get("text") or f"{brand}を見る →"
            _v = {"brand": brand, "name": brand, "label": _label, "btn": "見る →", "url": _p["url"]}
        _taken = _taken_by_const.setdefault(_cn, set(aff_io.list_all_keys()[_cn]))
        _k = _aff_auto_key(brand, _p["kind"], _v["url"], _taken)
        _taken.add(_k)
        _items.append({"ok": True, "const_name": _cn, "value": _v, "key": _k, "kind": _p["kind"]})

    if _chunks and not brand:
        st.info("ブランド名を入力すると読み取り結果が表示されます")
    elif _items:
        _ok_count = sum(1 for it in _items if it["ok"])
        st.markdown(f"##### 読み取り結果（{_ok_count} / {len(_items)} 件）")
        for it in _items:
            if not it["ok"]:
                st.warning(f"⚠️ 読み取れませんでした: {it['raw'][:60]}")
                continue
            with st.container(border=True):
                st.markdown(
                    f'<code>{it["key"]}</code>',
                    unsafe_allow_html=True,
                )
                aff_render_preview(it["const_name"], it["value"])

    _ok_items = [it for it in _items if it["ok"]] if brand else []

    with st.expander("詳しい形式を手動で入力（説明カード・予約ボタンなど、自動判別できない形式）"):
        CATEGORY_MAP = {
            "テキストリンク（シンプルなリンク）": "AFFILIATES",
            "説明カード（詳しい説明つきのカード）": "AFFILIATE_CARDS",
            "予約ボタンの並び": "BOOKING_BOXES",
            "画像バナー（手動入力）": "SIDE_BANNERS",
        }
        _use_manual = st.checkbox("手動入力を使う（貼り付けた内容より優先）", key=f"{key_prefix}_use_manual")
        category_label = st.radio("種類", list(CATEGORY_MAP.keys()), key=f"{key_prefix}_category")
        manual_const_name = CATEGORY_MAP[category_label]

        manual_value = {}
        if manual_const_name == "AFFILIATES":
            c1, c2 = st.columns(2)
            with c1:
                f_name = st.text_input("名前（内部管理用）", key=f"{key_prefix}_name")
                f_label = st.text_input("リンクの文言", placeholder="〇〇を見る →", key=f"{key_prefix}_label")
                f_btn = st.text_input("ボタンの文言", placeholder="見る →", key=f"{key_prefix}_btn")
            with c2:
                f_url = st.text_input("リンク先URL", key=f"{key_prefix}_url")
                f_desc = st.text_area("説明文", key=f"{key_prefix}_desc", height=80)
            has_banner = st.checkbox("バナー画像も設定する", key=f"{key_prefix}_has_banner")
            manual_value = {"brand": brand, "name": f_name, "label": f_label, "desc": f_desc, "btn": f_btn, "url": f_url}
            if has_banner:
                b_img = st.text_input("バナー画像URL", key=f"{key_prefix}_banner_img")
                b_url = st.text_input("バナーのリンク先URL", key=f"{key_prefix}_banner_url")
                b_pixel = st.text_input("計測用ピクセルURL（なければ空欄）", key=f"{key_prefix}_banner_pixel")
                banner = {"img": b_img, "url": b_url}
                if b_pixel:
                    banner["pixel"] = b_pixel
                manual_value["banner"] = banner

        elif manual_const_name == "AFFILIATE_CARDS":
            c1, c2 = st.columns(2)
            with c1:
                f_icon = st.text_input("アイコン（絵文字1文字、例: 🚗）", key=f"{key_prefix}_icon")
                f_name = st.text_input("名前", key=f"{key_prefix}_name")
                f_tagline = st.text_input("一言キャッチ", key=f"{key_prefix}_tagline")
                f_color = st.color_picker("テーマカラー", value="#006847", key=f"{key_prefix}_color")
            with c2:
                f_btn = st.text_input("ボタンの文言", placeholder="見る →", key=f"{key_prefix}_btn")
                f_url = st.text_input("リンク先URL", key=f"{key_prefix}_url")
                f_note = st.text_input("補足（注釈。なければ空欄でOK）", key=f"{key_prefix}_note")
            f_points = st.text_area(
                "特徴（1行に1つずつ）", key=f"{key_prefix}_points", height=100,
                placeholder="現地ATMで現地通貨をその場で引き出せる\nアプリで残高・履歴をリアルタイム管理",
            )
            points_list = [p.strip() for p in f_points.split("\n") if p.strip()]
            f_desc = ""
            has_banner = False
            banner = None
            banner_side = False
            with st.expander("詳細設定（説明文・バナー画像。必要な場合だけ開く）"):
                f_desc = st.text_area("詳しい説明文（任意）", key=f"{key_prefix}_desc2", height=80)
                has_banner = st.checkbox("バナー画像を追加する", key=f"{key_prefix}_card_has_banner")
                if has_banner:
                    b_img = st.text_input("バナー画像URL", key=f"{key_prefix}_card_banner_img")
                    b_url = st.text_input("バナーのリンク先URL", key=f"{key_prefix}_card_banner_url")
                    b_pixel = st.text_input("計測用ピクセルURL（なければ空欄）", key=f"{key_prefix}_card_banner_pixel")
                    banner_side = st.checkbox(
                        "バナーをカードの横に並べる（未チェックなら単独表示）", key=f"{key_prefix}_card_banner_side",
                    )
                    banner = {"img": b_img, "url": b_url}
                    if b_pixel:
                        banner["pixel"] = b_pixel
            manual_value = {
                "brand": brand, "icon": f_icon, "name": f_name, "tagline": f_tagline,
                "points": points_list, "note": f_note, "btn": f_btn, "url": f_url, "color": f_color,
            }
            if f_desc:
                manual_value["desc"] = f_desc
            if has_banner:
                manual_value["banner"] = banner
                if banner_side:
                    manual_value["bannerSide"] = True

        elif manual_const_name == "SIDE_BANNERS":
            c1, c2 = st.columns(2)
            with c1:
                f_name = st.text_input("名前（内部管理用）", key=f"{key_prefix}_side_name")
                f_alt = st.text_input("alt（画像の説明）", key=f"{key_prefix}_side_alt")
            with c2:
                f_img = st.text_input("バナー画像URL", key=f"{key_prefix}_side_img")
                f_url = st.text_input("リンク先URL", key=f"{key_prefix}_side_url")
            c3, c4, c5 = st.columns(3)
            with c3:
                f_w = st.number_input("画像の幅(px)", min_value=1, value=300, key=f"{key_prefix}_side_w")
            with c4:
                f_h = st.number_input("画像の高さ(px)", min_value=1, value=250, key=f"{key_prefix}_side_h")
            with c5:
                f_pixel = st.text_input("計測用ピクセルURL（任意）", key=f"{key_prefix}_side_pixel")
            manual_value = {
                "brand": brand, "name": f_name, "alt": f_alt,
                "img": f_img, "url": f_url, "width": int(f_w), "height": int(f_h),
            }
            if f_pixel:
                manual_value["pixel"] = f_pixel

        else:  # BOOKING_BOXES
            f_title = st.text_input("タイトル", key=f"{key_prefix}_box_title")
            st.caption("ボタンの色は仮の青色（Skyscannerと同じ）で表示されます。特定の色にしたい場合は保存後にaffiliates.jsのCSSを調整してください。")
            box_rows = st.data_editor(
                [{"ラベル": "", "URL": "", "説明（任意）": ""}],
                num_rows="dynamic", use_container_width=True, key=f"{key_prefix}_box_rows",
            )
            buttons = []
            for _row in box_rows:
                _label = (_row.get("ラベル") or "").strip()
                _url = (_row.get("URL") or "").strip()
                if not _label or not _url:
                    continue
                _btn = {"className": "btn-skyscanner", "label": _label, "url": _url}
                _desc = (_row.get("説明（任意）") or "").strip()
                if _desc:
                    _btn["desc"] = _desc
                buttons.append(_btn)
            manual_value = {"brand": brand, "title": f_title, "buttons": buttons}

        if _use_manual:
            if "brand" not in manual_value:
                manual_value["brand"] = brand
            if not aff_validate_required(manual_const_name, manual_value):
                st.info("必須項目が足りません")
            else:
                st.markdown("##### プレビュー")
                aff_render_preview(manual_const_name, manual_value)
                _manual_existing = aff_io.list_all_keys()[manual_const_name]
                _manual_key = st.text_input(
                    "キー（半角小文字英数字とアンダースコアのみ。例: my_new_link）", key=f"{key_prefix}_manual_key",
                ).strip()
                _manual_key_error = None
                if _manual_key:
                    if not aff_io.is_valid_key(_manual_key):
                        _manual_key_error = "半角小文字英数字とアンダースコアのみ、先頭は英字にしてください"
                    elif _manual_key in _manual_existing:
                        _manual_key_error = "このキーはすでに使われています"
                    if _manual_key_error:
                        st.error(_manual_key_error)
                if _manual_key and not _manual_key_error and st.button("💾 登録する", type="primary", key=f"{key_prefix}_manual_save"):
                    try:
                        aff_io.save_new_entry(manual_const_name, _manual_key, manual_value)
                    except Exception as e:
                        st.error(f"保存に失敗しました: {e}")
                    else:
                        st.success(f"✅ キー「{_manual_key}」として登録しました（バックアップ: affiliates-data.js.bak）")
                        return True

    if not _ok_items:
        return False

    if st.button(f"💾 {len(_ok_items)}件をまとめて登録する", type="primary", key=f"{key_prefix}_save"):
        _errors = []
        for it in _ok_items:
            try:
                aff_io.save_new_entry(it["const_name"], it["key"], it["value"])
            except Exception as e:
                _errors.append(f"{it['key']}: {e}")
        if _errors:
            st.error("一部の登録に失敗しました:\n" + "\n".join(_errors))
            return False
        else:
            st.success(f"✅ {len(_ok_items)}件登録しました（バックアップ: affiliates-data.js.bak）")
            return True
    return False


# ──────────────────────────────────────────────────────────
# ページ設定
# ──────────────────────────────────────────────────────────
st.set_page_config(page_title="Recraft 画像生成ツール", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@400;500;700;900&family=IBM+Plex+Mono:wght@400;500&display=swap');
.stApp { background-color: #F1F5EA; font-family: 'Zen Kaku Gothic New', sans-serif; color: #22302A; }
textarea { font-size: 1.25rem !important; line-height: 1.75 !important; }

/* ── 管理画面の共通デザイントークン（Content Studio の配色に合わせる） ── */
:root {
  --wm-admin-primary: #14503C;
  --wm-admin-primary-dark: #0E3A2B;
  --wm-admin-gold: #F5B921;
  --wm-admin-radius: 10px;
}

/* ── サイドバー（緑地・ナビ・クレジット） ── */
[data-testid="stSidebar"] { background-color: #14503C; }
[data-testid="stSidebar"] * { color: #E6EFE2; }
[data-testid="stSidebarUserContent"] {
  display: flex; flex-direction: column; min-height: calc(100vh - 40px);
}
.wm-brand { display: flex; align-items: center; gap: 10px; padding: 4px 8px 22px; }
.wm-brand-mark {
  width: 34px; height: 34px; border-radius: 10px; background: var(--wm-admin-gold);
  color: #14503C; font-weight: 900; font-size: 17px; display: grid; place-items: center;
}
.wm-brand-name { font-weight: 900; font-size: 15px; color: #fff; line-height: 1.2; }
.wm-brand-sub { font-size: 11px; color: #A9C4B5; letter-spacing: .08em; line-height: 1.2; }
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] {
  flex-direction: column !important; gap: 4px !important; flex-wrap: nowrap !important;
}
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] label {
  position: relative; width: 100%; border: 0 !important; background: transparent !important;
  border-radius: 10px !important; padding: 11px 12px 11px 22px !important;
}
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] label p {
  color: #BFD3C6 !important; font-size: 14px !important; font-weight: 700 !important;
}
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
  background: rgba(255,255,255,.12) !important; border: 0 !important;
}
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) p { color: #fff !important; }
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked)::before {
  content: ""; position: absolute; left: 8px; top: 50%; transform: translateY(-50%);
  width: 6px; height: 6px; border-radius: 3px; background: var(--wm-admin-gold);
}
.wm-credit {
  margin-top: auto; background: rgba(255,255,255,.07); border-radius: 12px; padding: 16px 16px 14px;
}
.wm-credit-label { font-size: 11px; color: #A9C4B5; letter-spacing: .06em; line-height: 1.4; }
.wm-credit-value {
  display: flex; align-items: baseline; gap: 6px; margin-top: 8px;
  font-size: 26px; font-weight: 900; color: #fff; line-height: 1.1; font-variant-numeric: tabular-nums;
}
.wm-credit-value span { font-size: 12px; color: #A9C4B5; font-weight: 500; }
.wm-credit-value .wm-credit-jpy { font-size: 16px; color: #CFE0D5; font-weight: 700; margin-left: 6px; }

/* ── トップバー（白・下線・固定） ── */
.st-key-wm_topbar {
  background: #fff; border-bottom: 1px solid #DDE5D3; padding: 12px 20px;
  position: sticky; top: 0; z-index: 5; margin-bottom: 16px;
}
/* ── 生成画面：金のCTA・費用行 ── */
.st-key-hero_gen button, .st-key-spot_gen button, .st-key-food_gen button {
  background: var(--wm-admin-primary) !important; color: #fff !important;
  border: 0 !important; font-weight: 900 !important;
}
.st-key-hero_gen button *, .st-key-spot_gen button *, .st-key-food_gen button * {
  color: #fff !important;
}
.st-key-hero_gen button:hover, .st-key-spot_gen button:hover, .st-key-food_gen button:hover {
  background: var(--wm-admin-primary-dark) !important;
}
.wm-blank-tile { aspect-ratio: 1 / 1; background: #F4F7F0; border: 1px solid #E4EBDD; border-radius: 12px; }
.wm-cost-row {
  display: flex; justify-content: space-between; align-items: baseline;
  border-top: 1px solid #E4EBDD; padding-top: 12px; font-size: 13px; color: #5E6E64;
}
.wm-cost-row b { font-size: 20px; font-weight: 900; color: #22302A; }
.wm-cost-row small { font-size: 12px; font-weight: 500; color: #8A968E; margin-left: 4px; }
[data-testid="stVerticalBlockBorderWrapper"] { background: #fff; }
.wm-stats { display: flex; gap: 16px; font-size: 13px; color: #5E6E64; flex-wrap: wrap; white-space: nowrap; }
.wm-stats b { color: #22302A; font-size: 15px; }
.wm-stats b.ok { color: #2F8A5F; font-size: 13px; }
.wm-stats b.ng { color: #E0892B; font-size: 13px; }
.st-key-wm_topbar div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  background: #F7FAF3 !important; border-color: #C9D6C1 !important; border-radius: 9px !important;
  font-weight: 700; color: #14503C !important;
}
div.stButton > button, div.stDownloadButton > button {
  border-radius: var(--wm-admin-radius) !important;
  border: 1px solid rgba(0,0,0,0.08) !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 2px rgba(20,40,30,0.08) !important;
  transition: filter 0.15s ease !important;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
  filter: brightness(0.97);
}
div.stButton > button[kind="primary"] {
  background: var(--wm-admin-primary) !important;
  border-color: var(--wm-admin-primary) !important;
}
div.stButton > button[kind="primary"]:hover {
  background: var(--wm-admin-primary-dark) !important;
  border-color: var(--wm-admin-primary-dark) !important;
}
[data-testid="stExpander"] {
  border-radius: var(--wm-admin-radius) !important;
  border: 1px solid rgba(0,0,0,0.08) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: var(--wm-admin-radius) !important;
}

/* ── ラジオボタンをピル型チップに（Claude Designの参考デザインに合わせる） ── */
div[data-testid="stRadio"] [role="radiogroup"] {
  gap: 8px !important;
  flex-wrap: wrap;
}
div[data-testid="stRadio"] [role="radiogroup"] label {
  border: 1px solid #D7E6DC;
  background: #fff;
  border-radius: 16px !important;
  padding: 6px 14px !important;
  margin: 0 !important;
  transition: background 0.15s ease, border-color 0.15s ease;
}
div[data-testid="stRadio"] [role="radiogroup"] label > div:first-child {
  display: none;
}
div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
  background: var(--wm-admin-primary);
  border-color: var(--wm-admin-primary);
}
div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) p {
  color: #fff !important;
  font-weight: 700 !important;
}

/* ── 広告の種類バッジ ── */
.wm-use-pill { display: inline-block; font-size: 12px; font-weight: 700; border-radius: 99px; padding: 3px 10px; }
.wm-use-pill.used { background: #E3F1E8; color: #2F6B4C; }
.wm-use-pill.unused { background: #FFF1DA; color: #A35F0E; }
.wm-type-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: #fff;
  border-radius: 6px;
  padding: 3px 8px;
  vertical-align: middle;
}
.wm-type-badge.aff   { background: var(--wm-admin-primary); }
.wm-type-badge.card  { background: #2563EB; }
.wm-type-badge.side  { background: #7C3AED; }
.wm-type-badge.box   { background: #D97706; }
</style>
""", unsafe_allow_html=True)
st.title("🎨 Recraft 画像生成ツール")

# ── ナビ（サイドバー）─ 5画面。生成系3画面はカテゴリをナビから決める ──
_NAV_ITEMS = [
    ("hero", "ヒーロー画像生成"),
    ("spot", "観光スポット画像"),
    ("food", "グルメ画像"),
    ("new",  "国を追加"),
    ("ads",  "広告管理"),
]
_NAV_LABELS = [lbl for _, lbl in _NAV_ITEMS]
_CAT_BY_NAV = {"hero": "🏔️ ヒーロー画像", "spot": "🗺️ 観光スポット", "food": "🍜 グルメ"}
_qp_tab = st.query_params.get("tab", _NAV_LABELS[0])
if _qp_tab not in _NAV_LABELS:
    _qp_tab = _NAV_LABELS[0]


def _on_main_nav_change():
    st.query_params["tab"] = st.session_state["main_nav"]


with st.sidebar:
    st.markdown(
        '<div class="wm-brand"><div class="wm-brand-mark">W</div>'
        '<div><div class="wm-brand-name">World Mappy</div>'
        '<div class="wm-brand-sub">CONTENT STUDIO</div></div></div>',
        unsafe_allow_html=True,
    )
    _nav = st.radio(
        "ページ", _NAV_LABELS, index=_NAV_LABELS.index(_qp_tab),
        key="main_nav", on_change=_on_main_nav_change, label_visibility="collapsed",
    )
st.query_params["tab"] = _nav
_nav_key = {lbl: key for key, lbl in _NAV_ITEMS}[_nav]
tab2 = _nav_key in _CAT_BY_NAV   # 生成系3画面
tab4 = _nav_key == "new"
tab5 = _nav_key == "ads"
gen_category = _CAT_BY_NAV.get(_nav_key, "🍜 グルメ")
st.session_state["gen_category_global"] = gen_category
save_last_state({"category": gen_category})

# 国選択
countries  = detect_countries()
last_state = load_last_state()
if not countries:
    st.error("国フォルダが見つかりません。World guide/ 直下に <country>/<country>.json を用意してください。")
    st.stop()

# ── トップバー：国選択 ・ 状態 ・ サイト更新 ──
with st.container(key="wm_topbar"):
    col_sel, col_info, col_update = st.columns([3, 4, 4], vertical_alignment="center")
    with col_sel:
        last_country = last_state.get("country", countries[0])
        country_idx  = countries.index(last_country) if last_country in countries else 0
        country_id   = st.selectbox("対象の国", countries, index=country_idx)

data       = load_json(country_id)
food_items = data.get("food_items", [])

with col_info:
    _all_spots = [sp for sec in data.get("spot_sections", []) for sp in sec.get("spots", [])]
    _spot_done = sum(1 for sp in _all_spots if image_exists(country_id, sp))
    _hero_img  = data.get("hero_image", "")
    _hero_ok   = bool(_hero_img and (ROOT_DIR / country_id / _hero_img).exists())
    _food_done = sum(1 for item in food_items if image_exists(country_id, item))
    st.markdown(
        f'<div class="wm-stats">'
        f'<span>ヒーロー <b class="{"ok" if _hero_ok else "ng"}">{"設定済" if _hero_ok else "未設定"}</b></span>'
        f'<span>観光 <b>{_spot_done}</b>/{len(_all_spots)}</span>'
        f'<span>グルメ <b>{_food_done}</b>/{len(food_items)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

with col_update:
    _all_c = detect_countries()
    _col_upd_one, _col_upd_all = st.columns(2)
    with _col_upd_one:
        if st.button(f"{country_id} のみ更新", key="top_update_one", use_container_width=True):
            with st.spinner(f"{country_id} を再生成中..."):
                _rc, _out, _err = _run_generate(country_id)
            if _rc == 0:
                st.success(f"✅ {country_id} 完了")
            else:
                st.error(f"❌ {country_id} 失敗\n{_err}")
    with _col_upd_all:
        if st.button(f"全{len(_all_c)}か国を更新", key="top_update_all", type="primary", use_container_width=True):
            _log = []
            _prog = st.progress(0, text="準備中...")
            for _i, _cid in enumerate(_all_c):
                _prog.progress(_i / len(_all_c), text=f"{_cid} ({_i+1}/{len(_all_c)})")
                _rc, _out, _err = _run_generate(_cid)
                _log.append(("✅" if _rc == 0 else "❌") + f" {_cid}")
            _prog.progress(1.0, text="完了！")
            _ok = sum(1 for l in _log if l.startswith("✅"))
            if _ok == len(_log):
                st.success(f"✅ 全 {_ok} か国 完了")
            else:
                st.warning("\n".join(_log))

# ── サイドバー下部：Recraft クレジット ──
try:
    credits = recraft_api.get_credits()
except Exception:
    credits = -1
with st.sidebar:
    if credits >= 0:
        st.markdown(
            f'<div class="wm-credit"><div class="wm-credit-label">RECRAFT クレジット</div>'
            f'<div class="wm-credit-value">{credits:,}<span>cr</span>'
            f'<span class="wm-credit-jpy">≈ ¥{credits * 0.16:,.0f}</span></div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="wm-credit"><div class="wm-credit-label">RECRAFT クレジット</div>'
                    '<div class="wm-credit-value">取得失敗</div></div>', unsafe_allow_html=True)


# gen_results 管理（初回ロード復元 / カテゴリ切り替えリセット）
if "gen_results" not in st.session_state:
    st.session_state["gen_results"] = []
    st.session_state["_gen_cat"]    = gen_category
elif st.session_state.get("_gen_cat") != gen_category:
    st.session_state["_gen_cat"]    = gen_category
    st.session_state["gen_results"] = []

st.divider()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# タブ1: 一覧 / プロンプト編集（カテゴリ対応）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if tab2:
    st.subheader("画像生成")

    with st.expander(f"🚀 画像を一括生成（{country_id} / {gen_category} の未生成分のみ）", expanded=False):
        st.caption("各アイテムの保存済みプロンプト・皿設定をそのまま使い、未生成の画像だけを自動生成・自動保存します（プレビュー選択なし）。生成後にJSONも更新されます。")
        if st.button("🚀 一括生成を実行", key="bulk_gen_btn", type="primary"):
            _bulk_data = load_json(country_id)

            if gen_category == "🍜 グルメ":
                _targets = [it for it in _bulk_data.get("food_items", [])
                            if not image_exists(country_id, it) and it.get("prompt_en")]
                _out_dir = food_dir(country_id)
                _out_dir.mkdir(parents=True, exist_ok=True)
                _rel_prefix = "素材/グルメ/"
                _model, _w, _h, _use_style = "recraft20b", 1024, 1024, True
            elif gen_category == "🏔️ ヒーロー画像":
                _targets = [] if _bulk_data.get("hero_image") or not _bulk_data.get("hero_prompt") else [
                    {"name": "ヒーロー", "prompt_en": _bulk_data.get("hero_prompt", ""), "plate_color": ""}
                ]
                _out_dir = ROOT_DIR / country_id / "素材"
                _out_dir.mkdir(parents=True, exist_ok=True)
                _rel_prefix = "素材/"
                _model, _w, _h, _use_style = "style_spot", 1820, 1024, True
            else:  # 🗺️ 観光スポット
                _targets = []
                for _sec in _bulk_data.get("spot_sections", []):
                    for _sp in _sec.get("spots", []):
                        if not image_exists(country_id, _sp) and _sp.get("prompt_en"):
                            _targets.append(_sp)
                _out_dir = ROOT_DIR / country_id / "素材" / "観光スポット"
                _out_dir.mkdir(parents=True, exist_ok=True)
                _rel_prefix = "素材/観光スポット/"
                _model, _w, _h, _use_style = "style_spot", 1820, 1024, True

            if not _targets:
                st.info("未生成の画像はありません。")
            else:
                _prog = st.progress(0, text="準備中...")
                _log  = []
                for _i, _t in enumerate(_targets):
                    _name = _t.get("name", f"item{_i}")
                    _prog.progress(_i / len(_targets), text=f"{_name} ({_i+1}/{len(_targets)})")
                    try:
                        _img_bytes, _cr = recraft_api.generate_image(
                            prompt=_t.get("prompt_en", ""),
                            plate_color=_t.get("plate_color", ""),
                            model=_model,
                            use_style=_use_style,
                            width=_w,
                            height=_h,
                        )
                        _out_path = _out_dir / f"{_name}.webp"
                        with open(_out_path, "wb") as _f:
                            _f.write(_img_bytes)
                        if gen_category == "🏔️ ヒーロー画像":
                            _bulk_data["hero_image"] = f"{_rel_prefix}{_name}.webp"
                        else:
                            _t["image"] = f"{_rel_prefix}{_name}.webp"
                        save_json(country_id, _bulk_data)  # 1枚ごとに保存（中断時の消失を防ぐ）
                        _log.append(f"✅ {_name}（残{_cr}cr）")
                    except Exception as e:
                        _log.append(f"❌ {_name}: {e}")
                _prog.progress(1.0, text="完了！")
                st.success("\n".join(_log))

    st.divider()

    # ────────────────── 🍜 グルメ ──────────────────
    if gen_category == "🍜 グルメ":

        def sort_key(item):
            return (1 if image_exists(country_id, item) else 0, item.get("num", ""))

        sorted_items  = sorted(food_items, key=sort_key)
        # 料理の選択：プルダウンをやめ、画像タイルから「選択」ボタンで選ぶ（未生成はブランク表示）
        _sel_key  = f"food_pick_{country_id}"
        _nums     = [i.get("num", "") for i in sorted_items]
        _last_dish = last_state.get("dish") if last_state.get("country") == country_id else None
        _default_num = next((i.get("num", "") for i in sorted_items if _last_dish and i.get("name") == _last_dish),
                            _nums[0] if _nums else "")
        if st.session_state.get(_sel_key) not in _nums:
            st.session_state[_sel_key] = _default_num
        sel_item = next(i for i in sorted_items if i.get("num", "") == st.session_state[_sel_key])
        def _render_food_grid():
            _per_row = 4
            for _r0 in range(0, len(sorted_items), _per_row):
                _row_cols = st.columns(_per_row)
                for _col, _it in zip(_row_cols, sorted_items[_r0:_r0 + _per_row]):
                    _num = _it.get("num", "")
                    with _col:
                        if image_exists(country_id, _it):
                            st.image(str(ROOT_DIR / country_id / _it["image"]), use_container_width=True)
                        else:
                            st.markdown('<div class="wm-blank-tile"></div>', unsafe_allow_html=True)
                        _is_sel = st.session_state[_sel_key] == _num
                        st.caption(("✓ " if _is_sel else "") + f"{_num} {_it.get('name', '')}")
                        if st.button("選択", key=f"pick_{_num}", type="primary" if _is_sel else "secondary",
                                     use_container_width=True):
                            st.session_state[_sel_key] = _num
                            st.rerun()


        save_last_state({"country": country_id, "dish": sel_item.get("name", ""), "tab": 1})

        st.divider()

        item_key   = sel_item.get("num", "0").replace(".", "_")
        key_prompt = f"gen_prompt_{item_key}"
        if not st.session_state.get(key_prompt):
            # 優先順: last_state（前回編集値）→ JSON（保存済み）
            _saved_prompt = last_state.get("prompts", {}).get(f"{country_id}_{item_key}", "")
            st.session_state[key_prompt] = _saved_prompt or sel_item.get("prompt_en", "")

        SHAPES = {
            "指定なし":             "",
            "皿なし":               "no plate",
            "プレート":             "ceramic plate",
            "ボウル":               "ceramic bowl",
            "深めのボウル":         "deep ceramic bowl",
            "グラス":               "tall glass",
            "カップ":               "ceramic cup",
            "鉄鍋":                 "cast iron pan",
            "木の皿":               "wooden plate",
            "紙皿":                 "paper plate",
            "紙カップ":             "paper cup",
            "バナナの葉":           "banana leaf",
            "竹かご":               "bamboo basket",
            "新聞紙":               "newspaper",
            "クラフト紙（敷き紙）": "kraft paper laid flat",
        }
        COLORS = {
            "白":             "white",
            "オフホワイト":   "off-white",
            "ベージュ":       "beige",
            "クリーム":       "cream",
            "水色":           "light blue",
            "ブルー":         "blue",
            "ネイビー":       "navy",
            "グリーン":       "green",
            "セージグリーン": "sage green",
            "イエロー":       "yellow",
            "オレンジ":       "orange",
            "テラコッタ":     "terracotta",
            "レッド":         "red",
            "ピンク":         "pink",
            "パープル":       "purple",
            "ブラウン":       "brown",
            "ダーク":         "dark",
            "ブラック":       "black",
            "グレー":         "gray",
            "なし":           "",
        }

        saved_plate   = sel_item.get("plate_color", "")
        default_shape = "指定なし"
        default_color = "なし"
        for jp_s, en_s in SHAPES.items():
            if en_s in saved_plate:
                default_shape = jp_s
                break
        for jp_c, en_c in COLORS.items():
            if en_c and en_c in saved_plate:
                default_color = jp_c
                break

        shape_key   = f"gen_shape_{item_key}"
        color_key   = f"gen_color_{item_key}"
        pattern_key = f"gen_pattern_{item_key}"
        _shape_now  = st.session_state.get(shape_key, default_shape)
        _color_now  = st.session_state.get(color_key, default_color)
        if _shape_now not in SHAPES: _shape_now = default_shape
        if _color_now not in COLORS: _color_now = default_color

        en_shape        = SHAPES[_shape_now]
        en_color        = COLORS[_color_now]
        _use_pattern    = st.session_state.get(pattern_key, False)
        _pattern_str    = " with decorative pattern" if _use_pattern and en_shape else ""
        plate_color_val = (f"{en_color} {en_shape}{_pattern_str}".strip()
                           if en_color else f"{en_shape}{_pattern_str}".strip())
        prompt_val      = st.session_state.get(key_prompt, sel_item.get("prompt_en", ""))
        # ページ更新後も復元できるよう last_state に保存
        _p_dict = {**last_state.get("prompts", {}), f"{country_id}_{item_key}": prompt_val}
        save_last_state({"prompts": _p_dict})

        # ── 背景除去の事前処理（col_l 描画より前に実行してから表示） ──
        if "pending_bg_idx" in st.session_state:
            _bg_i    = st.session_state.pop("pending_bg_idx")
            _results = st.session_state.get("gen_results", [])
            if 0 <= _bg_i < len(_results):
                with st.spinner("背景除去中（ローカル処理）..."):
                    try:
                        _res      = _results[_bg_i]
                        bg_bytes  = rembg_remove(_res["bytes"], session=_get_rembg_session())
                        new_bytes = to_webp(bg_bytes)
                        new_list  = list(_results)
                        # 元画像をoriginal_bytesとして保持
                        orig = _res.get("original_bytes") or _res["bytes"]
                        new_list[_bg_i] = _temp_save({**_res, "bytes": new_bytes, "original_bytes": orig})
                        st.session_state["gen_results"] = new_list
                        st.rerun()
                    except Exception as e:
                        st.error(f"背景除去失敗: {e}")

        col_l, col_r = st.columns(2)

        with col_l:
            results = st.session_state.get("gen_results", [])
            if results:
                hdr_l, hdr_r = st.columns([4, 1])
                with hdr_l:
                    st.caption(f"生成した画像 ({len(results)}枚) — 保存したい1枚を選んでください")
                with hdr_r:
                    if st.button("🗑️ 全削除", help="生成画像をすべて破棄"):
                        for r in results:
                            _temp_delete(r.get("tmp_id", ""))
                        st.session_state["gen_results"] = []
                        st.rerun()
                ncols = min(len(results), 2)
                img_cols = st.columns(ncols)
                for i, res in enumerate(results):
                    with img_cols[i % ncols]:
                        cr_str = f"消費: {res['credits']}cr" if res.get("credits") else ""
                        st.caption(f"#{i+1}　{cr_str}")
                        st.image(res["bytes"], use_container_width=True)
                        b1, b2, b3, b4 = st.columns(4)
                        with b1:
                            if st.button("💾 保存", key=f"save_{i}", type="primary"):
                                name    = res.get("name", sel_item.get("name", "output"))
                                out_dir = food_dir(country_id)
                                out_dir.mkdir(parents=True, exist_ok=True)
                                out_path = out_dir / f"{name}.webp"
                                out_path.write_bytes(to_webp(res["bytes"]))
                                rel_path = f"素材/グルメ/{name}.webp"
                                for fi in food_items:
                                    if fi.get("name") == name:
                                        fi["image"]       = rel_path
                                        fi["prompt_en"]   = prompt_val
                                        fi["plate_color"] = plate_color_val
                                        break
                                data["food_items"] = food_items
                                save_json(country_id, data)
                                for r in results:
                                    _temp_delete(r.get("tmp_id", ""))
                                st.success(f"✅ 保存: {out_path.name}")
                                st.session_state["gen_results"] = []
                                st.rerun()
                        with b2:
                            if st.button("✂️", key=f"bg_{i}", help="背景除去"):
                                st.session_state["pending_bg_idx"] = i
                                st.rerun()
                        with b3:
                            if st.button("🗑️", key=f"del_{i}", help="この画像を削除"):
                                _temp_delete(res.get("tmp_id", ""))
                                st.session_state["gen_results"] = [r for j, r in enumerate(results) if j != i]
                                st.rerun()
                        with b4:
                            if res.get("original_bytes"):
                                if st.button("↩️", key=f"undo_{i}", help="背景除去を元に戻す"):
                                    _restored = {k: v for k, v in res.items() if k not in ("original_bytes", "has_original")}
                                    _restored["bytes"] = res["original_bytes"]
                                    _new_list = list(results)
                                    _new_list[i] = _temp_save(_restored)
                                    st.session_state["gen_results"] = _new_list
                                    st.rerun()
            else:
                existing_path = ROOT_DIR / country_id / sel_item.get("image", "")
                if existing_path.exists() and sel_item.get("image"):
                    st.caption("現在の画像")
                    st.image(str(existing_path), use_container_width=True)
                    if st.session_state.get("food_del_pending"):
                        _c1, _c2 = st.columns(2)
                        with _c1:
                            if st.button("本当に削除", key="food_img_del_confirm", type="primary", use_container_width=True):
                                existing_path.unlink()
                                sel_item["image"] = ""
                                data["food_items"] = food_items
                                save_json(country_id, data)
                                st.session_state.pop("food_del_pending", None)
                                st.success("画像を削除しました")
                                st.rerun()
                        with _c2:
                            if st.button("✕", key="food_img_del_cancel", use_container_width=True):
                                st.session_state.pop("food_del_pending", None)
                                st.rerun()
                    else:
                        if st.button("🗑️ この画像を削除", key="food_img_del"):
                            st.session_state["food_del_pending"] = True
                            st.rerun()
                else:
                    st.info("画像未生成")

        ANGLES = {
            "🍽️ 手前斜め前（45°）": (
                "three-quarter front-diagonal view, camera positioned at 45-degree angle"
                " from the front-right, NOT overhead, NOT top-down, dish visible from"
                " the side and slightly above, lateral perspective,"
            ),
            "⬆️ 真上（フラットレイ）": "directly overhead, flat lay, top-down view, bird's eye view,",
            "📐 斜め上（60°）":        "high angle shot from above at 60 degrees, slightly diagonal, angled downward,",
            "👁️ 目線（テーブル高）":   "eye-level front view, camera at table height, horizontal perspective,",
            "✏️ 指定なし":             "",
        }

        with col_r:
            st.markdown(f"**{sel_item.get('name', '')}**")
            st.text_area("プロンプト（英語）", height=200, key=key_prompt)
            angle_key = f"gen_angle_{item_key}"
            angle_sel = st.selectbox(
                "📷 カメラアングル",
                list(ANGLES.keys()),
                index=0,
                key=angle_key,
            )
            angle_prefix = ANGLES[angle_sel]
            use_style_key = f"gen_style_{item_key}"
            use_style_val = st.toggle(
                "スタイルID を使用（オフ＝背景色・アングル指示が通りやすい）",
                value=True,
                key=use_style_key,
            )
            sc1, sc2, sc3 = st.columns([2, 2, 1])
            with sc1:
                shape_sel = st.selectbox(
                    "皿の形状",
                    list(SHAPES.keys()),
                    index=list(SHAPES.keys()).index(_shape_now),
                    key=shape_key,
                )
            with sc2:
                color_sel = st.selectbox(
                    "皿の色",
                    list(COLORS.keys()),
                    index=list(COLORS.keys()).index(_color_now),
                    key=color_key,
                )
            with sc3:
                pattern_sel = st.toggle("柄あり", key=pattern_key)
            # セレクトボックスの戻り値から plate_color_val を再計算（確実に最新値を使う）
            en_shape_r      = SHAPES[shape_sel]
            en_color_r      = COLORS[color_sel]
            _pstr_r         = " with decorative pattern" if pattern_sel and en_shape_r else ""
            plate_color_val = (f"{en_color_r} {en_shape_r}{_pstr_r}".strip()
                               if en_color_r else f"{en_shape_r}{_pstr_r}".strip())
            st.markdown(
                f"<p style='font-size:1.1em;font-weight:600;color:#444;margin:2px 0 8px;'>"
                f"→ {plate_color_val}</p>",
                unsafe_allow_html=True,
            )
            model_val = st.radio(
                "モデル",
                [
                    "recraft20b       22cr ≈ ¥3.5/枚  （水彩）",
                    "recraftv3        40cr ≈ ¥6.4/枚  （水彩）",
                    "watercolor20b    22cr ≈ ¥3.5/枚  (スタイルIDなし・色指示が通りやすい)",
                    "style_food_0710  未計測cr  （グルメ用新スタイル・2026-07-10追加）",
                ],
                horizontal=False,
                key=f"gen_model_{item_key}",
            )
            if "watercolor20b" in model_val:
                model_key_r = "watercolor20b"
            elif "style_food_0710" in model_val:
                model_key_r = "style_food_0710"
            elif "recraftv3" in model_val:
                model_key_r = "recraftv3"
            else:
                model_key_r = "recraft20b"
            ASPECT_RATIOS = {
                "1:1  (1024×1024)": (1024, 1024),
                "4:3  (1365×1024)": (1365, 1024),
                "3:4  (1024×1365)": (1024, 1365),
                "16:9 (1820×1024)": (1820, 1024),
                "9:16 (1024×1820)": (1024, 1820),
            }
            ratio_sel  = st.selectbox("縦横比", list(ASPECT_RATIOS.keys()), index=0, key=f"gen_ratio_{item_key}")
            gen_width, gen_height = ASPECT_RATIOS[ratio_sel]
            _base        = (angle_prefix + " " + prompt_val).strip() if angle_prefix else prompt_val
            # 自然素材・皿なし はsolid背景と矛盾するので _bg_suffix を付けない
            _NO_BG_SHAPES = {"banana leaf", "no plate", "bamboo basket",
                             "newspaper", "kraft paper laid flat", "wooden plate"}
            _blue_plates  = {"light blue", "blue", "navy"}
            if en_shape_r in _NO_BG_SHAPES:
                _bg_suffix = ""
            else:
                _bg_suffix = (", pure solid white background, isolated on white"
                              if en_color_r in _blue_plates
                              else ", pure solid light blue background, isolated on light blue")
            final_prompt = _base + _bg_suffix
            # 送信プロンプト確認（plate_color を含む完全な文字列を表示）
            _preview_plate = f", served on a {plate_color_val}." if plate_color_val else ""
            _preview_full  = final_prompt + _preview_plate
            with st.expander("📤 送信プロンプト確認（クリックで展開）", expanded=False):
                st.code(_preview_full, language=None)
                st.caption(f"皿: {plate_color_val or '（指定なし）'}　サイズ: {gen_width}×{gen_height}")
            _food_cr = {"recraft20b": 22, "recraftv3": 40, "watercolor20b": 22}.get(model_key_r)
            _food_cost_txt = f"{_food_cr}cr" if _food_cr else "未計測"
            _food_yen_txt  = f' <small>≈ ¥{_food_cr * 0.16:,.1f}</small>' if _food_cr else ""
            st.markdown(
                f'<div class="wm-cost-row"><span>1枚 × {_food_cost_txt}</span>'
                f'<b>{_food_cost_txt}{_food_yen_txt}</b></div>',
                unsafe_allow_html=True,
            )
            gen_btn = st.button("生成実行", type="primary", key="food_gen", disabled=not prompt_val.strip())

        if gen_btn:
            if not prompt_val.strip():
                st.warning("プロンプトを入力してください。")
            else:
                with st.spinner("生成中..."):
                    try:
                        img_bytes, cr1 = recraft_api.generate_image(
                            prompt=final_prompt,
                            plate_color=plate_color_val,
                            model=model_key_r,
                            use_style=use_style_val,
                            width=gen_width,
                            height=gen_height,
                        )
                        new_item = _temp_save({
                            "bytes":   img_bytes,
                            "ext":     "webp",
                            "credits": cr1,
                            "name":    sel_item.get("name", "output"),
                        })
                        st.session_state["gen_results"] = (
                            st.session_state.get("gen_results", []) + [new_item]
                        )
                        st.rerun()
                    except (RuntimeError, requests.exceptions.RequestException) as e:
                        st.error(str(e))


    # ────────────────── 🏔️ ヒーロー画像 ──────────────────
        st.divider()
        st.markdown("##### 料理を選ぶ")
        _render_food_grid()

    elif gen_category == "🏔️ ヒーロー画像":

        hero_prompt_key = f"hero_prompt_{country_id}"
        if not st.session_state.get(hero_prompt_key):
            st.session_state[hero_prompt_key] = data.get("hero_prompt", "")

        # 背景除去の事前処理
        if "pending_bg_idx" in st.session_state:
            _bg_i    = st.session_state.pop("pending_bg_idx")
            _results = st.session_state.get("gen_results", [])
            if 0 <= _bg_i < len(_results):
                with st.spinner("背景除去中（ローカル処理）..."):
                    try:
                        _res      = _results[_bg_i]
                        bg_bytes  = rembg_remove(_res["bytes"], session=_get_rembg_session())
                        new_bytes = to_webp(bg_bytes)
                        new_list  = list(_results)
                        # 元画像をoriginal_bytesとして保持
                        orig = _res.get("original_bytes") or _res["bytes"]
                        new_list[_bg_i] = _temp_save({**_res, "bytes": new_bytes, "original_bytes": orig})
                        st.session_state["gen_results"] = new_list
                        st.rerun()
                    except Exception as e:
                        st.error(f"背景除去失敗: {e}")

        col_l, col_r = st.columns(2)

        with col_l:
            results = st.session_state.get("gen_results", [])
            if results:
                hdr_l, hdr_r = st.columns([4, 1])
                with hdr_l:
                    st.caption(f"生成した画像 ({len(results)}枚)")
                with hdr_r:
                    if st.button("🗑️ 全削除", key="hero_delall"):
                        for r in results:
                            _temp_delete(r.get("tmp_id", ""))
                        st.session_state["gen_results"] = []
                        st.rerun()
                ncols = min(len(results), 2)
                img_cols = st.columns(ncols)
                for i, res in enumerate(results):
                    with img_cols[i % ncols]:
                        st.caption(f"#{i+1}　消費: {res.get('credits', 0)}cr")
                        st.image(res["bytes"], use_container_width=True)
                        b1, b2, b3, b4 = st.columns(4)
                        with b1:
                            if st.button("💾 保存", key=f"hero_save_{i}", type="primary"):
                                hero_dir = ROOT_DIR / country_id / "素材"
                                hero_dir.mkdir(parents=True, exist_ok=True)
                                out_path = hero_dir / "ヒーロー.webp"
                                out_path.write_bytes(to_webp(res["bytes"]))
                                data["hero_image"]  = "素材/ヒーロー.webp"
                                data["hero_prompt"] = st.session_state.get(hero_prompt_key, "")
                                save_json(country_id, data)
                                for r in results:
                                    _temp_delete(r.get("tmp_id", ""))
                                st.success("✅ 保存: ヒーロー.webp")
                                st.session_state["gen_results"] = []
                                st.rerun()
                        with b2:
                            if st.button("✂️", key=f"hero_bg_{i}", help="背景除去"):
                                st.session_state["pending_bg_idx"] = i
                                st.rerun()
                        with b3:
                            if st.button("🗑️", key=f"hero_del_{i}", help="削除"):
                                _temp_delete(res.get("tmp_id", ""))
                                st.session_state["gen_results"] = [r for j, r in enumerate(results) if j != i]
                                st.rerun()
                        with b4:
                            if res.get("original_bytes"):
                                if st.button("↩️", key=f"hero_undo_{i}", help="背景除去を元に戻す"):
                                    _restored = {k: v for k, v in res.items() if k not in ("original_bytes", "has_original")}
                                    _restored["bytes"] = res["original_bytes"]
                                    _new_list = list(results)
                                    _new_list[i] = _temp_save(_restored)
                                    st.session_state["gen_results"] = _new_list
                                    st.rerun()
            else:
                _hero_img = data.get("hero_image", "")
                hero_path = ROOT_DIR / country_id / _hero_img if _hero_img else None
                if hero_path and hero_path.exists() and hero_path.is_file():
                    st.caption("現在のヒーロー画像")
                    st.image(str(hero_path), use_container_width=True)
                    if st.session_state.get("hero_del_pending"):
                        _c1, _c2 = st.columns(2)
                        with _c1:
                            if st.button("本当に削除", key="hero_img_del_confirm", type="primary", use_container_width=True):
                                hero_path.unlink()
                                data["hero_image"] = ""
                                save_json(country_id, data)
                                st.session_state.pop("hero_del_pending", None)
                                st.success("画像を削除しました")
                                st.rerun()
                        with _c2:
                            if st.button("✕", key="hero_img_del_cancel", use_container_width=True):
                                st.session_state.pop("hero_del_pending", None)
                                st.rerun()
                    else:
                        if st.button("🗑️ この画像を削除", key="hero_img_del"):
                            st.session_state["hero_del_pending"] = True
                            st.rerun()
                else:
                    st.info("ヒーロー画像未設定")

        hero_prompt_val = ""
        with col_r:
            st.markdown(f"**{data.get('name', '')} ヒーロー画像**")
            st.text_area(
                "プロンプト（英語）",
                height=200,
                key=hero_prompt_key,
                placeholder="e.g. Aerial panoramic view of Samarkand with blue-domed Registan Square at golden sunset, ultra-wide travel banner",
            )
            hero_model_val = st.radio(
                "モデル",
                [
                    "recraft20b   22cr ≈ ¥3.5/枚  （水彩）",
                    "recraftv3    40cr ≈ ¥6.4/枚  （水彩）",
                    "vector_art   40cr ≈ ¥6.4/枚  （フラットベクターイラスト）",
                    "style_spot   22cr ≈ ¥3.5/枚  （フラットベクター）",
                    "style_spot3  40cr ≈ ¥6.4/枚  （フラットベクター v3）",
                    "style_spot4  40cr ≈ ¥6.4/枚  （フラットベクター v4）",
                    "style_spot5  40cr ≈ ¥6.4/枚  （フラットベクター v5）",
                ],
                index=3,
                horizontal=False,
                key="hero_model",
            )
            if "style_spot5" in hero_model_val:
                hero_model_key = "style_spot5"
            elif "style_spot4" in hero_model_val:
                hero_model_key = "style_spot4"
            elif "style_spot3" in hero_model_val:
                hero_model_key = "style_spot3"
            elif "style_spot" in hero_model_val:
                hero_model_key = "style_spot"
            elif "recraft20b" in hero_model_val:
                hero_model_key = "recraft20b"
            elif "vector_art" in hero_model_val:
                hero_model_key = "vector_art"
            else:
                hero_model_key = "recraftv3"
            _hero_ratios = {
                "16:9 (1820×1024)": (1820, 1024),
                "1:1  (1024×1024)": (1024, 1024),
                "4:3  (1365×1024)": (1365, 1024),
                "9:16 (1024×1820)": (1024, 1820),
            }
            hero_ratio_sel = st.selectbox("縦横比", list(_hero_ratios.keys()), index=0, key="hero_ratio")
            hero_w, hero_h = _hero_ratios[hero_ratio_sel]
            hero_prompt_val = st.session_state.get(hero_prompt_key, "")
            _hero_cr = {"recraft20b": 22, "recraftv3": 40, "vector_art": 40, "style_spot": 22,
                        "style_spot3": 40, "style_spot4": 40, "style_spot5": 40}.get(hero_model_key, 40)
            st.markdown(
                f'<div class="wm-cost-row"><span>1枚 × {_hero_cr}cr</span>'
                f'<b>{_hero_cr}cr <small>≈ ¥{_hero_cr * 0.16:,.1f}</small></b></div>',
                unsafe_allow_html=True,
            )
            hero_gen_btn    = st.button(
                "生成実行", type="primary", key="hero_gen",
                disabled=not hero_prompt_val.strip(),
            )

        if hero_gen_btn:
            with st.spinner("生成中..."):
                try:
                    img_bytes, cr1 = recraft_api.generate_image(
                        prompt=hero_prompt_val,
                        plate_color="",
                        model=hero_model_key,
                        width=hero_w,
                        height=hero_h,
                    )
                    new_item = _temp_save({
                        "bytes":   img_bytes,
                        "ext":     "webp",
                        "credits": cr1,
                        "name":    "ヒーロー",
                    })
                    st.session_state["gen_results"] = (
                        st.session_state.get("gen_results", []) + [new_item]
                    )
                    st.rerun()
                except (RuntimeError, requests.exceptions.RequestException) as e:
                    st.error(str(e))


    # ────────────────── 🏙️ 都市カード ──────────────────
    elif gen_category == "🗺️ 観光スポット":

        spot_secs = data.get("spot_sections", [])
        # 全スポットをフラット化（未生成を優先ソート）
        _all_spots_flat = []
        for _si, _s in enumerate(spot_secs):
            for _pi, _sp in enumerate(_s.get("spots", [])):
                _all_spots_flat.append({
                    "sec_idx":   _si,
                    "spot_idx":  _pi,
                    "city_name": _s.get("city_name", ""),
                    "city_id":   _s.get("city_id", ""),
                    "spot":      _sp,
                })

        if not _all_spots_flat:
            st.warning("スポットが登録されていません。JSONの spot_sections > spots を確認してください。")
        else:
            def _spot_has_img(entry):
                img = entry["spot"].get("image", "")
                return bool(img) and (ROOT_DIR / country_id / img).exists()

            _sorted_spots  = sorted(_all_spots_flat, key=lambda e: (1 if _spot_has_img(e) else 0, e["city_name"]))
            def _spot_id(e):
                return f"{e['city_id']}|{e['spot'].get('name', '')}"
            _spot_key = f"spot_pick_{country_id}"
            _spot_ids = [_spot_id(e) for e in _sorted_spots]
            _last_spot = last_state.get("spot") if last_state.get("country") == country_id else None
            _default_id = next((_spot_id(e) for e in _sorted_spots if _last_spot and e["spot"].get("name") == _last_spot),
                               _spot_ids[0])
            if st.session_state.get(_spot_key) not in _spot_ids:
                st.session_state[_spot_key] = _default_id
            sel_spot_entry = next(e for e in _sorted_spots if _spot_id(e) == st.session_state[_spot_key])
            sel_spot       = sel_spot_entry["spot"]
            spot_name      = sel_spot.get("name", "")
            spot_city_name = sel_spot_entry["city_name"]
            save_last_state({"country": country_id, "spot": spot_name, "tab": 1})
            _safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in spot_name)
            spot_prompt_key = f"spot_prompt_{country_id}_{sel_spot_entry['city_id']}_{_safe_name}"
            json_prompt = sel_spot.get("prompt_en", "")
            if spot_prompt_key not in st.session_state or (not st.session_state[spot_prompt_key] and json_prompt):
                st.session_state[spot_prompt_key] = json_prompt

            st.divider()

            # 背景除去の事前処理
            if "pending_bg_idx" in st.session_state:
                _bg_i    = st.session_state.pop("pending_bg_idx")
                _results = st.session_state.get("gen_results", [])
                if 0 <= _bg_i < len(_results):
                    with st.spinner("背景除去中（ローカル処理）..."):
                        try:
                            _res      = _results[_bg_i]
                            bg_bytes  = rembg_remove(_res["bytes"], session=_get_rembg_session())
                            new_bytes = to_webp(bg_bytes)
                            new_list  = list(_results)
                            orig = _res.get("original_bytes") or _res["bytes"]
                            new_list[_bg_i] = _temp_save({**_res, "bytes": new_bytes, "original_bytes": orig})
                            st.session_state["gen_results"] = new_list
                            st.rerun()
                        except Exception as e:
                            st.error(f"背景除去失敗: {e}")

            col_l, col_r = st.columns(2)

            with col_l:
                results = st.session_state.get("gen_results", [])
                if results:
                    hdr_l, hdr_r = st.columns([4, 1])
                    with hdr_l:
                        st.caption(f"生成した画像 ({len(results)}枚)")
                    with hdr_r:
                        if st.button("🗑️ 全削除", key="spot_delall"):
                            for r in results:
                                _temp_delete(r.get("tmp_id", ""))
                            st.session_state["gen_results"] = []
                            st.rerun()
                    ncols = min(len(results), 2)
                    img_cols = st.columns(ncols)
                    for i, res in enumerate(results):
                        with img_cols[i % ncols]:
                            st.caption(f"#{i+1}　消費: {res.get('credits', 0)}cr")
                            st.image(res["bytes"], use_container_width=True)
                            b1, b2, b3, b4 = st.columns(4)
                            with b1:
                                if st.button("💾 保存", key=f"spot_save_{i}", type="primary"):
                                    spot_img_dir = ROOT_DIR / country_id / "素材" / "観光スポット"
                                    spot_img_dir.mkdir(parents=True, exist_ok=True)
                                    fname    = f"{spot_name}.webp"
                                    out_path = spot_img_dir / fname
                                    out_path.write_bytes(to_webp(res["bytes"]))
                                    rel = f"素材/観光スポット/{fname}"
                                    # JSONのspot.imageとprompt_enを更新
                                    _sec_idx  = sel_spot_entry["sec_idx"]
                                    _sp_idx   = sel_spot_entry["spot_idx"]
                                    data["spot_sections"][_sec_idx]["spots"][_sp_idx]["image"]     = rel
                                    data["spot_sections"][_sec_idx]["spots"][_sp_idx]["prompt_en"] = st.session_state.get(spot_prompt_key, "")
                                    save_json(country_id, data)
                                    for r in results:
                                        _temp_delete(r.get("tmp_id", ""))
                                    st.success(f"✅ 保存: {fname}")
                                    st.session_state["gen_results"] = []
                                    st.rerun()
                            with b2:
                                if st.button("✂️", key=f"spot_bg_{i}", help="背景除去"):
                                    st.session_state["pending_bg_idx"] = i
                                    st.rerun()
                            with b3:
                                if st.button("🗑️", key=f"spot_del_{i}", help="削除"):
                                    _temp_delete(res.get("tmp_id", ""))
                                    st.session_state["gen_results"] = [r for j, r in enumerate(results) if j != i]
                                    st.rerun()
                            with b4:
                                if res.get("original_bytes"):
                                    if st.button("↩️", key=f"spot_undo_{i}", help="背景除去を元に戻す"):
                                        _restored = {k: v for k, v in res.items() if k not in ("original_bytes", "has_original")}
                                        _restored["bytes"] = res["original_bytes"]
                                        _new_list = list(results)
                                        _new_list[i] = _temp_save(_restored)
                                        st.session_state["gen_results"] = _new_list
                                        st.rerun()
                else:
                    spot_img      = sel_spot.get("image", "")
                    spot_img_path = (ROOT_DIR / country_id / spot_img) if spot_img else None
                    if spot_img_path and spot_img_path.exists():
                        st.caption("現在のスポット画像")
                        st.image(str(spot_img_path), use_container_width=True)
                        if st.session_state.get("spot_del_pending"):
                            _c1, _c2 = st.columns(2)
                            with _c1:
                                if st.button("本当に削除", key="spot_img_del_confirm", type="primary", use_container_width=True):
                                    spot_img_path.unlink()
                                    sel_spot["image"] = ""
                                    save_json(country_id, data)
                                    st.session_state.pop("spot_del_pending", None)
                                    st.success("画像を削除しました")
                                    st.rerun()
                            with _c2:
                                if st.button("✕", key="spot_img_del_cancel", use_container_width=True):
                                    st.session_state.pop("spot_del_pending", None)
                                    st.rerun()
                        else:
                            if st.button("🗑️ この画像を削除", key="spot_img_del"):
                                st.session_state["spot_del_pending"] = True
                                st.rerun()
                    else:
                        st.info(f"{spot_name} の画像未設定")

            spot_prompt_val_now = ""
            with col_r:
                st.markdown(f"**{spot_name}**　*{spot_city_name}*")
                st.text_area(
                    "プロンプト（英語）",
                    height=200,
                    key=spot_prompt_key,
                    placeholder=f"e.g. {spot_name}, scenic landscape, detailed illustration",
                )
                spot_model_val = st.radio(
                    "モデル",
                    [
                        "recraft20b       22cr ≈ ¥3.5/枚  （水彩）",
                        "recraftv3        40cr ≈ ¥6.4/枚  （水彩）",
                        "watercolor20b    22cr ≈ ¥3.5/枚  (スタイルIDなし・色指示が通りやすい)",
                        "style_spot       22cr ≈ ¥3.5/枚  （フラットベクター）",
                        "style_spot3      40cr ≈ ¥6.4/枚  （フラットベクター v3）",
                        "style_spot4      40cr ≈ ¥6.4/枚  （フラットベクター v4）",
                        "style_spot5      40cr ≈ ¥6.4/枚  （フラットベクター v5）",
                    ],
                    horizontal=False,
                    index=3,
                    key="spot_model",
                )
                if "watercolor20b" in spot_model_val:
                    spot_model_key = "watercolor20b"
                elif "style_spot5" in spot_model_val:
                    spot_model_key = "style_spot5"
                elif "style_spot4" in spot_model_val:
                    spot_model_key = "style_spot4"
                elif "style_spot3" in spot_model_val:
                    spot_model_key = "style_spot3"
                elif "recraftv3" in spot_model_val:
                    spot_model_key = "recraftv3"
                elif "style_spot" in spot_model_val:
                    spot_model_key = "style_spot"
                else:
                    spot_model_key = "recraft20b"
                spot_use_style = st.toggle(
                    "スタイルID を使用",
                    value=True,
                    key="spot_use_style",
                )
                _spot_ratios = {
                    "1:1  (1024×1024)": (1024, 1024),
                    "4:3  (1365×1024)": (1365, 1024),
                    "16:9 (1820×1024)": (1820, 1024),
                    "3:4  (1024×1365)": (1024, 1365),
                }
                spot_ratio_sel      = st.selectbox("縦横比", list(_spot_ratios.keys()), index=2, key="spot_ratio")
                spot_w, spot_h      = _spot_ratios[spot_ratio_sel]
                spot_prompt_val_now = st.session_state.get(spot_prompt_key, "")
                _spot_cr = {"recraft20b": 22, "recraftv3": 40, "watercolor20b": 22, "style_spot": 22,
                            "style_spot3": 40, "style_spot4": 40, "style_spot5": 40}.get(spot_model_key, 40)
                st.markdown(
                    f'<div class="wm-cost-row"><span>1枚 × {_spot_cr}cr</span>'
                    f'<b>{_spot_cr}cr <small>≈ ¥{_spot_cr * 0.16:,.1f}</small></b></div>',
                    unsafe_allow_html=True,
                )
                spot_gen_btn        = st.button(
                    "生成実行", type="primary", key="spot_gen",
                    disabled=not spot_prompt_val_now.strip(),
                )

            if spot_gen_btn:
                with st.spinner("生成中..."):
                    try:
                        img_bytes, cr1 = recraft_api.generate_image(
                            prompt=spot_prompt_val_now,
                            plate_color="",
                            model=spot_model_key,
                            use_style=spot_use_style,
                            width=spot_w,
                            height=spot_h,
                        )
                        new_item = _temp_save({
                            "bytes":   img_bytes,
                            "ext":     "webp",
                            "credits": cr1,
                            "name":    spot_name,
                        })
                        st.session_state["gen_results"] = (
                            st.session_state.get("gen_results", []) + [new_item]
                        )
                        st.rerun()
                    except (RuntimeError, requests.exceptions.RequestException) as e:
                        st.error(str(e))



            st.divider()
            st.markdown("##### スポットを選ぶ")
            _per_row = 4
            for _r0 in range(0, len(_sorted_spots), _per_row):
                _row_cols = st.columns(_per_row)
                for _k, (_col, _e) in enumerate(zip(_row_cols, _sorted_spots[_r0:_r0 + _per_row])):
                    _idx = _r0 + _k
                    _sp = _e["spot"]
                    _sid = _spot_id(_e)
                    with _col:
                        if _spot_has_img(_e):
                            st.image(str(ROOT_DIR / country_id / _sp["image"]), use_container_width=True)
                        else:
                            st.markdown('<div class="wm-blank-tile"></div>', unsafe_allow_html=True)
                        _is_sel = st.session_state[_spot_key] == _sid
                        st.caption(("✓ " if _is_sel else "") + f"{_e['city_name']} / {_sp.get('name', '')}")
                        if st.button("選択", key=f"spick_{_idx}", type="primary" if _is_sel else "secondary",
                                     use_container_width=True):
                            st.session_state[_spot_key] = _sid
                            st.rerun()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# タブ4: 新規国を作成
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import copy as _copy

# テンプレートファイルの保存先
COUNTRY_TEMPLATE_PATH = TOOLS_DIR / "_country_template.json"

# ── コンテンツフィールドをクリアして1件の food_item スキーマを返す ──
def _blank_food_item(i: int, src: dict) -> dict:
    d = _copy.deepcopy(src)
    d.update({
        "num": f"No.{i+1}", "name": "", "badge": "", "desc": "",
        "image": "", "prompt_en": "", "plate_color": "white ceramic plate",
        "city": "national",
    })
    return d

def _blank_spot_section(i: int, src: dict) -> dict:
    d = _copy.deepcopy(src)
    d.update({
        "city_id": f"city{i+1}", "city_name": "", "city_image": "",
        "city_prompt": "", "city_desc": "", "spots": [],
    })
    return d

def _build_template_from(base_id: str) -> dict:
    """ベース国の JSON から全フィールドを引き継ぎ、内容だけ空にしたテンプレートを生成。"""
    base = load_json(base_id)
    tmpl = _copy.deepcopy(base)

    # ── トップレベル識別子をクリア ──
    tmpl.update({
        "id": "__template__", "name": "", "name_en": "", "page_title": "",
        "hero_image": "", "hero_alt": "", "hero_prompt": "",
    })

    # ── overview: テキスト値を空に（スタイル系は保持） ──
    _KEEP_OV = {"difficulty_label_bg", "difficulty_label_color",
                "difficulty_pct", "difficulty_bar"}
    for k in tmpl.get("overview", {}):
        if k not in _KEEP_OV:
            tmpl["overview"][k] = ""

    # ── map ──
    tmpl["map"] = {
        "element_id": "", "center_lat": "0", "center_lng": "0",
        "zoom": "5", "map_id": "ebb608e55ed157f8630c407e", "country_label": "",
    }

    # ── cities / food_items / spot_sections は 0件スタート ──
    tmpl["cities"]        = []
    tmpl["food_items"]    = []
    tmpl["spot_sections"] = []

    # ── season_mini ──
    sm = tmpl.get("season_mini", {})
    sm["description"] = ""
    sm["city_name"]   = ""
    # months は構造（icon/temp/type）だけ保持して値を空に
    for m in sm.get("months", []):
        m["icon"] = ""; m["temp"] = "--°"

    # ── basic_data: 値のみ空に ──
    for item in tmpl.get("basic_data", []):
        item["value"] = ""; item["note"] = ""; item["compare_html"] = ""

    # ── season（詳細）: テキストのみ空に ──
    s = tmpl.get("season", {})
    s["description_html"] = ""; s["tip_html"] = ""
    for city in s.get("cities", []):
        city["name"] = ""; city["city_id"] = ""; city["best_note"] = ""

    # ── budget ──
    b = tmpl.get("budget", {})
    for k in ("plan1_label","plan1_range","plan1_note",
              "plan2_label","plan2_range","plan2_note","savings_tips_html"):
        if k in b: b[k] = ""
    for item in b.get("items", []):
        item["detail_html"] = ""; item["price"] = ""

    # ── practical ──
    p = tmpl.get("practical", {})
    for card in p.get("prac_cards", []):
        card["value"] = ""
    for step in p.get("prep_steps", []):
        step["desc_html"] = ""
    for k in ("special_note_title","special_note_html","special_note_url",
              "special_note_url_label","flight_intro","flight_tip_html",
              "hotel_intro","hotel_tip","cash_small_tip_html","cash_note",
              "cta_title","cta_desc"):
        if k in p: p[k] = ""
    for airline in p.get("airlines", []):
        airline.update({"name": "", "desc": "", "price": ""})
    for area in p.get("hotel_areas", []):
        area.update({"name": "", "tag": "", "desc": "", "price": "", "maps_url": ""})
    p["country_items_html"] = ""
    for app_ in p.get("apps", []):
        app_.update({"name": "", "type_label": "", "desc": ""})
    for k in ("currency_code","exchange_rate","eco_daily","std_daily","lux_daily"):
        if k in p: p[k] = "0"

    # ── manner_cards: type/icon は保持、テキストのみ空に ──
    for card in tmpl.get("manner_cards", []):
        card["title"] = ""; card["desc"] = ""
    tmpl["manner_cta_title"] = ""; tmpl["manner_cta_desc"] = ""

    # ── phrases ──
    ph = tmpl.get("phrases", {})
    ph["language_name"] = ""; ph["card_title"] = ""
    for cat in ph.get("categories", []):
        cat["label"] = ""
        for item in cat.get("items", []):
            item.update({"jp": "", "foreign": "", "reading": "", "audio": ""})

    # ── transport_items ──
    for item in tmpl.get("transport_items", []):
        item["name"] = ""; item["desc"] = ""

    # ── courses ──
    c = tmpl.get("courses", {})
    for k in ("intro","stable_title","adventure_title",
              "adventure_note_html","cta_title","cta_desc"):
        if k in c: c[k] = ""
    for plan in c.get("stable_plans", []):
        plan.update({"label": "", "title": "", "tip": ""})
        for day in plan.get("days", []):
            day["content_html"] = ""
            if "duration" in day: day["duration"] = ""
    ap = c.get("adventure_plan", {})
    if ap:
        ap["tip"] = ""
        for day in ap.get("days", []):
            day["content_html"] = ""
            if "duration" in day: day["duration"] = ""

    # ── food / spots セクション設定 ──
    tmpl["food_section_title"]  = ""
    tmpl["food_filter_cities"]  = []
    tmpl["spots_section_title"] = ""
    tmpl["spots_filter_cities"] = []

    # ── food modal ──
    tmpl["food_modal_phrase_main"] = ""
    tmpl["food_modal_phrase_sub"]  = ""

    # ── index_card ──
    if "index_card" in tmpl:
        ic = tmpl["index_card"]
        for k in list(ic.keys()):
            if isinstance(ic[k], str):  ic[k] = ""
            elif isinstance(ic[k], list): ic[k] = []

    COUNTRY_TEMPLATE_PATH.write_text(
        json.dumps(tmpl, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return tmpl


def _new_country_from_template(cid: str, name_ja: str, name_en: str) -> dict:
    """テンプレートをコピーして id / name だけ差し替えた新規国JSONを返す。"""
    tmpl = json.loads(COUNTRY_TEMPLATE_PATH.read_text(encoding="utf-8"))
    tmpl["id"]            = cid
    tmpl["name"]          = name_ja
    tmpl["name_en"]       = name_en
    tmpl["page_title"]    = f"{name_ja}旅行ガイド"
    tmpl["hero_alt"]      = f"{name_ja}の風景"
    tmpl["map"]["element_id"]    = f"{cid}-map"
    tmpl["map"]["country_label"] = name_ja
    tmpl["overview"]["country_question"] = f"{name_ja}ってどんな国？"
    return tmpl


if tab4:
    st.subheader("新しい国のページを作成")

    # ════════════════════════════════
    # セクション1: テンプレート管理
    # ════════════════════════════════
    st.markdown("#### 📄 テンプレート管理")
    if COUNTRY_TEMPLATE_PATH.exists():
        _tmpl_mtime = COUNTRY_TEMPLATE_PATH.stat().st_mtime
        import datetime as _dt
        _tmpl_date  = _dt.datetime.fromtimestamp(_tmpl_mtime).strftime("%Y-%m-%d %H:%M")
        st.success(f"✅ テンプレートあり　（更新: {_tmpl_date}）")
    else:
        st.warning("⚠️ テンプレートがまだありません。下のボタンで作成してください。")

    tc1, tc2 = st.columns([3, 2])
    with tc1:
        _tmpl_base = st.selectbox(
            "ベースにする国", countries,
            index=countries.index("malaysia") if "malaysia" in countries else 0,
            key="tmpl_base_sel",
            help="このJSONのフィールド構成・件数をテンプレートとして保存します",
        )
    with tc2:
        st.write("")
        st.write("")
        if st.button("🔄 テンプレートを作成／更新", key="tmpl_create_btn"):
            _build_template_from(_tmpl_base)
            st.success(f"✅ {_tmpl_base} をベースにテンプレートを保存しました")
            st.rerun()

    st.divider()

    # ════════════════════════════════
    # セクション2: 新規国を作成
    # ════════════════════════════════
    st.markdown("#### 🌍 新規国を作成")

    _tmpl_ok = COUNTRY_TEMPLATE_PATH.exists()
    if not _tmpl_ok:
        st.info("先にテンプレートを作成してください。")

    import re as _re

    # 日本語国名 → 英語名 変換辞書
    _JA_TO_EN = {
        "日本": "Japan", "アメリカ": "United States", "アメリカ合衆国": "United States",
        "イギリス": "United Kingdom", "フランス": "France", "ドイツ": "Germany",
        "イタリア": "Italy", "スペイン": "Spain", "ポルトガル": "Portugal",
        "オランダ": "Netherlands", "ベルギー": "Belgium", "スイス": "Switzerland",
        "オーストリア": "Austria", "ギリシャ": "Greece", "トルコ": "Turkey",
        "ロシア": "Russia", "ウクライナ": "Ukraine", "ポーランド": "Poland",
        "チェコ": "Czech Republic", "ハンガリー": "Hungary", "ルーマニア": "Romania",
        "ブルガリア": "Bulgaria", "クロアチア": "Croatia", "セルビア": "Serbia",
        "スウェーデン": "Sweden", "ノルウェー": "Norway", "デンマーク": "Denmark",
        "フィンランド": "Finland", "アイスランド": "Iceland",
        "中国": "China", "韓国": "South Korea", "台湾": "Taiwan",
        "タイ": "Thailand", "ベトナム": "Vietnam", "カンボジア": "Cambodia",
        "ラオス": "Laos", "ミャンマー": "Myanmar", "マレーシア": "Malaysia",
        "シンガポール": "Singapore", "インドネシア": "Indonesia",
        "フィリピン": "Philippines", "インド": "India", "スリランカ": "Sri Lanka",
        "ネパール": "Nepal", "バングラデシュ": "Bangladesh", "パキスタン": "Pakistan",
        "アフガニスタン": "Afghanistan", "イラン": "Iran", "イラク": "Iraq",
        "サウジアラビア": "Saudi Arabia", "アラブ首長国連邦": "United Arab Emirates",
        "UAE": "United Arab Emirates", "イスラエル": "Israel",
        "ヨルダン": "Jordan", "レバノン": "Lebanon", "シリア": "Syria",
        "エジプト": "Egypt", "モロッコ": "Morocco", "チュニジア": "Tunisia",
        "アルジェリア": "Algeria", "リビア": "Libya", "エチオピア": "Ethiopia",
        "ケニア": "Kenya", "タンザニア": "Tanzania", "ウガンダ": "Uganda",
        "ルワンダ": "Rwanda", "南アフリカ": "South Africa",
        "南アフリカ共和国": "South Africa", "ナイジェリア": "Nigeria",
        "ガーナ": "Ghana", "セネガル": "Senegal", "マダガスカル": "Madagascar",
        "オーストラリア": "Australia", "ニュージーランド": "New Zealand",
        "カナダ": "Canada", "メキシコ": "Mexico", "ブラジル": "Brazil",
        "アルゼンチン": "Argentina", "チリ": "Chile", "ペルー": "Peru",
        "コロンビア": "Colombia", "ベネズエラ": "Venezuela", "エクアドル": "Ecuador",
        "ボリビア": "Bolivia", "パラグアイ": "Paraguay", "ウルグアイ": "Uruguay",
        "キューバ": "Cuba", "ジャマイカ": "Jamaica", "ハイチ": "Haiti",
        "ウズベキスタン": "Uzbekistan", "カザフスタン": "Kazakhstan",
        "キルギス": "Kyrgyzstan", "タジキスタン": "Tajikistan",
        "トルクメニスタン": "Turkmenistan", "ジョージア": "Georgia",
        "アゼルバイジャン": "Azerbaijan", "アルメニア": "Armenia",
        "モルディブ": "Maldives", "スリランカ": "Sri Lanka",
        "パプアニューギニア": "Papua New Guinea", "フィジー": "Fiji",
    }

    def _to_id(en: str) -> str:
        return _re.sub(r"[^a-z0-9]+", "_", en.lower()).strip("_")

    def _sync_from_ja():
        ja = st.session_state.get("nc_name_ja", "").strip()
        en = _JA_TO_EN.get(ja, "")
        if en:
            st.session_state["nc_name_en"] = en
            st.session_state["nc_id"]      = _to_id(en)

    def _sync_from_en():
        en = st.session_state.get("nc_name_en", "")
        st.session_state["nc_id"] = _to_id(en)

    nc1, nc2 = st.columns(2)
    with nc1:
        st.text_input("国名（日本語）", placeholder="南アフリカ共和国",
                      key="nc_name_ja", disabled=not _tmpl_ok, on_change=_sync_from_ja)
        st.text_input("国名（英語）",   placeholder="South Africa",
                      key="nc_name_en", disabled=not _tmpl_ok, on_change=_sync_from_en)
        st.text_input("国ID（自動入力・変更可）", placeholder="south_africa",
                      key="nc_id", disabled=not _tmpl_ok)
    with nc2:
        if _tmpl_ok:
            st.info("フォルダとJSONの骨格を作成します。\n\nグルメ・都市の内容はこのチャットでClaudeに依頼してください。")

    new_id      = st.session_state.get("nc_id", "")
    new_name_ja = st.session_state.get("nc_name_ja", "")
    new_name_en = st.session_state.get("nc_name_en", "")
    _can_create = _tmpl_ok and bool(new_id.strip() and new_name_ja.strip())
    if st.button("🌍 フォルダ＆JSONを作成", type="primary", disabled=not _can_create):
        _cid   = new_id.strip().lower().replace(" ", "_")
        _jpath = ROOT_DIR / _cid / f"{_cid}.json"

        if _jpath.exists():
            st.error(f"すでに存在します: {_jpath}")
        else:
            (ROOT_DIR / _cid / "素材" / "グルメ").mkdir(parents=True, exist_ok=True)
            (ROOT_DIR / _cid / "素材" / "都市").mkdir(parents=True, exist_ok=True)
            _new_data = _new_country_from_template(_cid, new_name_ja.strip(), new_name_en.strip())
            with open(_jpath, "w", encoding="utf-8") as _f:
                json.dump(_new_data, _f, ensure_ascii=False, indent=2)
            st.success("✅ 作成完了！")
            st.code(str(_jpath), language=None)
            st.info("F5 でドロップダウンに反映されます。グルメ・都市の追加はチャットでClaudeに依頼してください。")
            load_json.clear()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# タブ5: 広告管理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if tab5:
    _AFF_SECTIONS = ["🏷️ ブランド別", "📄 ページ別"]
    _qp_aff = st.query_params.get("aff", _AFF_SECTIONS[0])
    if _qp_aff not in _AFF_SECTIONS:
        _qp_aff = _AFF_SECTIONS[0]

    def _on_aff_section_change():
        st.query_params["aff"] = st.session_state["aff_section"]

    aff_section = st.radio(
        "表示", _AFF_SECTIONS, horizontal=True, index=_AFF_SECTIONS.index(_qp_aff),
        key="aff_section", on_change=_on_aff_section_change,
    )
    st.query_params["aff"] = aff_section

    # ── a. 一覧・使用状況 ──
    if aff_section == _AFF_SECTIONS[0]:
        st.caption(
            "assets/affiliates-data.js の内容と、各ページでの使用状況です（開くたびに最新集計）。"
            "ブランドを選んで「このブランドに追加」から新しい広告を登録できます。"
        )
        if st.button("🔄 使用状況を再集計", key="aff_recalc") or "aff_usage_cache" not in st.session_state:
            with st.spinner("全ページを集計中…"):
                _r = aff_compute_usage()
                aff_write_usage_report(_r)
                st.session_state["aff_usage_cache"] = _r
        _aff_result = st.session_state["aff_usage_cache"]
        _usage = _aff_result["usage"]
        _STYLES = [("AFFILIATES", "テキストリンク", "affiliate", "aff"),
                   ("BOOKING_BOXES", "予約ボタン", "affiliate-box", "box"),
                   ("AFFILIATE_CARDS", "説明カード", "affiliate-card", "card"),
                   ("SIDE_BANNERS", "画像バナー", "affiliate-side", "side")]

        _NEW_BRAND = "＋ 新しいブランド"

        def _is_unused(const_name, k):
            t = _STYLES_BY_CONST[const_name][1]
            u = (_usage.get(t) or {}).get(k) or {}
            if const_name == "SIDE_BANNERS":
                return False
            return u.get("total", 0) == 0 and not u.get("auto_via_text_link")

        _STYLES_BY_CONST = {c: (lbl, t, cls) for c, lbl, t, cls in _STYLES}

        def _aff_brand_page():
            brand_map = aff_read_brand_map()
            _brand_names = sorted(brand_map.keys())
            _unused_brands = {b for b, items in brand_map.items() if any(_is_unused(c, k) for c, k in items)}

            col_list, col_main = st.columns([1, 3], gap="large")

            with col_list:
                _q = st.text_input("ブランド検索", key="aff_brand_search", placeholder="検索")
                _filtered = [b for b in _brand_names if _q.strip().lower() in b.lower()] if _q.strip() else _brand_names
                _opts = _filtered + [_NEW_BRAND]

                def _fmt(name):
                    if name == _NEW_BRAND:
                        return name
                    return name

                _default = st.session_state.get("aff_brand_sel", _opts[0] if _opts else _NEW_BRAND)
                if _default not in _opts:
                    _default = _opts[0] if _opts else _NEW_BRAND
                _sel = st.radio("ブランド", _opts, format_func=_fmt, key="aff_brand_sel",
                                index=_opts.index(_default), label_visibility="collapsed")

            with col_main:
                if _sel == _NEW_BRAND:
                    st.markdown("#### 新しいブランドを追加")
                    if aff_registration_form(default_brand=None, key_prefix="newbrand"):
                        st.session_state.pop("aff_usage_cache", None)
                        st.rerun()
                    return

                st.markdown(f"#### {_sel}")
                _rows = brand_map.get(_sel, [])
                for const_name, k in _rows:
                    lbl, t, cls = _STYLES_BY_CONST[const_name]
                    u = (_usage.get(t) or {}).get(k) or {}
                    n = u.get("total", 0)
                    if const_name == "SIDE_BANNERS":
                        pill = '<span class="wm-use-pill used">全ページ共通</span>'
                    elif n:
                        pill = f'<span class="wm-use-pill used">使用中 {n}箇所</span>'
                    elif u.get("auto_via_text_link"):
                        pill = '<span class="wm-use-pill used">自動表示</span>'
                    else:
                        pill = '<span class="wm-use-pill unused">未使用</span>'

                    _entry_value = aff_get_entry(const_name, k)
                    with st.container(border=True):
                        _pv, _meta = st.columns([4, 1.3], gap="medium")
                        with _pv:
                            if _entry_value is None:
                                st.caption("⚠️ プレビューの読み込みに失敗しました")
                            else:
                                aff_render_preview(const_name, _entry_value)
                        with _meta:
                            st.markdown(
                                f'<div>{pill}</div>',
                                unsafe_allow_html=True,
                            )
                            st.caption(f"ASP: {(_entry_value or {}).get('asp', '不明')}")
                            st.code(k, language=None)
                            _del_key = f"aff_del_pending_{const_name}_{k}"
                            if st.session_state.get(_del_key):
                                if st.button("本当に削除", key=f"aff_del_confirm_{const_name}_{k}", type="primary",
                                             use_container_width=True):
                                    try:
                                        aff_io.delete_entry(const_name, k)
                                    except Exception as e:
                                        st.error(f"削除に失敗しました: {e}")
                                    else:
                                        st.session_state.pop(_del_key, None)
                                        st.session_state.pop("aff_usage_cache", None)
                                        st.rerun()
                                if st.button("✕", key=f"aff_del_cancel_{const_name}_{k}", use_container_width=True):
                                    st.session_state.pop(_del_key, None)
                                    st.rerun()
                            else:
                                if st.button("🗑️ 削除", key=f"aff_del_{const_name}_{k}", use_container_width=True):
                                    st.session_state[_del_key] = True
                                    st.rerun()

                with st.container(border=True):
                    st.markdown(f"##### ＋ 「{_sel}」に広告を追加")
                    if aff_registration_form(default_brand=_sel, key_prefix=f"add_{_sel}"):
                        st.session_state.pop("aff_usage_cache", None)
                        st.rerun()

        _aff_brand_page()

    # ── b. ページ別使用状況 ──
    else:

        st.caption("国を選ぶと、その国の各ページに実際に表示されている広告の一覧を確認できます。")
        _aff_result = aff_compute_usage()
        _usage = _aff_result["usage"]
        _attr_labels = _aff_result["attr_labels"]

        from collections import defaultdict as _defaultdict
        _pages_index = _defaultdict(list)
        for _attr_type, _keys in _usage.items():
            for _key, _u in _keys.items():
                for _p in _u.get("pages", []):
                    _pages_index[_p["file"]].append({"type": _attr_type, "key": _key, "count": _p["count"]})

        _countries = detect_countries()
        sel_country = st.selectbox("国", ["すべて"] + _countries, key="aff_page_country")

        target_files = sorted(_pages_index.keys())
        if sel_country != "すべて":
            target_files = [f for f in target_files if f.startswith(sel_country + "/")]

        if not target_files:
            st.info("対象のページで広告の使用が見つかりませんでした。")
        for f in target_files:
            items = _pages_index[f]
            st.markdown(f"**{f}**")
            st.table([
                {"種類": _attr_labels.get(it["type"], it["type"]), "キー": it["key"], "回数": it["count"]}
                for it in items
            ])

        if _aff_result["unused"]:
            with st.expander(f"⚠️ どのページにも配置されていないキー（{len(_aff_result['unused'])}件）"):
                for u in _aff_result["unused"]:
                    st.write(f"- [{_attr_labels.get(u['type'], u['type'])}] {u['key']}")
