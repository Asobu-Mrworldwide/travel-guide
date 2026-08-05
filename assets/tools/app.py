"""
Recraft 画像生成管理アプリ
起動: python -m streamlit run assets/tools/app.py
"""
import io
import json
import os
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
# ページ設定
# ──────────────────────────────────────────────────────────
st.set_page_config(page_title="Recraft 画像生成ツール", layout="wide")
st.markdown("""
<style>
.stApp { background-color: #ddeaf5; }
[data-testid="stSidebar"] { background-color: #ccdff0; }
textarea { font-size: 1.25rem !important; line-height: 1.75 !important; }
</style>
""", unsafe_allow_html=True)
st.title("🎨 Recraft 画像生成ツール")

# 国選択
countries  = detect_countries()
last_state = load_last_state()
if not countries:
    st.error("国フォルダが見つかりません。World guide/ 直下に <country>/<country>.json を用意してください。")
    st.stop()

col_sel, col_info, col_cr, col_update = st.columns([2, 3, 2, 2])
with col_sel:
    last_country = last_state.get("country", countries[0])
    country_idx  = countries.index(last_country) if last_country in countries else 0
    country_id   = st.selectbox("国を選択", countries, index=country_idx)

data       = load_json(country_id)
food_items = data.get("food_items", [])

_cat_options_early = ["🍜 グルメ", "🏔️ ヒーロー画像", "🗺️ 観光スポット"]
_current_cat = st.session_state.get(
    "gen_category_global",
    last_state.get("category", _cat_options_early[0]),
)
if _current_cat not in _cat_options_early:
    _current_cat = _cat_options_early[0]

with col_info:
    if _current_cat == "🍜 グルメ":
        total   = len(food_items)
        has_img = sum(1 for item in food_items if image_exists(country_id, item))
        st.metric("料理数", total)
        st.caption(f"画像あり: {has_img} / {total}")
    elif _current_cat == "🏔️ ヒーロー画像":
        _hero_img = data.get("hero_image", "")
        has_img   = 1 if (_hero_img and (ROOT_DIR / country_id / _hero_img).exists()) else 0
        st.metric("ヒーロー画像", 1)
        st.caption(f"画像あり: {has_img} / 1")
    else:
        _all_spots = [sp for sec in data.get("spot_sections", []) for sp in sec.get("spots", [])]
        total      = len(_all_spots)
        has_img    = sum(1 for sp in _all_spots if image_exists(country_id, sp))
        st.metric("スポット数", total)
        st.caption(f"画像あり: {has_img} / {total}")

with col_cr:
    try:
        credits = recraft_api.get_credits()
    except Exception:
        credits = -1
    if credits >= 0:
        yen = credits * 0.16
        st.metric("Recraftクレジット", f"{credits:,} cr")
        st.markdown(f"<p style='font-size:1.4em;font-weight:700;margin-top:-12px;color:#1a6fa8;'>≈ ¥{yen:,.0f}</p>", unsafe_allow_html=True)
    else:
        st.metric("Recraftクレジット", "取得失敗")

with col_update:
    st.markdown("**サイト更新**")
    _all_c = detect_countries()
    st.caption(f"全 {len(_all_c)} か国を再生成")
    _col_upd_one, _col_upd_all = st.columns(2)
    with _col_upd_one:
        if st.button(f"🔄 {country_id} のみ更新", key="top_update_one"):
            with st.spinner(f"{country_id} を再生成中..."):
                _rc, _out, _err = _run_generate(country_id)
            if _rc == 0:
                st.success(f"✅ {country_id} 完了")
            else:
                st.error(f"❌ {country_id} 失敗\n{_err}")
    with _col_upd_all:
        if st.button(f"🌏 全国更新", key="top_update_all", type="primary"):
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

# カテゴリ選択（全タブ共通）— 起動時に前回値を復元
_cat_options = ["🍜 グルメ", "🏔️ ヒーロー画像", "🗺️ 観光スポット"]
_last_cat    = last_state.get("category", _cat_options[0])
if "gen_category_global" not in st.session_state:
    st.session_state["gen_category_global"] = _last_cat if _last_cat in _cat_options else _cat_options[0]
gen_category = st.radio(
    "カテゴリ",
    _cat_options,
    horizontal=True,
    label_visibility="collapsed",
    key="gen_category_global",
)
save_last_state({"category": gen_category})

# gen_results 管理（初回ロード復元 / カテゴリ切り替えリセット）
if "gen_results" not in st.session_state:
    st.session_state["gen_results"] = []
    st.session_state["_gen_cat"]    = gen_category
elif st.session_state.get("_gen_cat") != gen_category:
    st.session_state["_gen_cat"]    = gen_category
    st.session_state["gen_results"] = []

st.divider()

# ──────────────────────────────────────────────────────────
# タブ復元（毎描画で発火、ただし既に正しいタブなら何もしない）
# ──────────────────────────────────────────────────────────
last_tab   = last_state.get("tab", 1)
active_tab = st.session_state.get("active_tab", last_tab)

import streamlit.components.v1 as components
components.html(f"""
<script>
(function() {{
    var target = {active_tab};
    var tries  = 0;
    var timer  = setInterval(function() {{
        var tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
        if (tabs && tabs.length > target) {{
            var current = Array.from(tabs).findIndex(function(t) {{
                return t.getAttribute('aria-selected') === 'true';
            }});
            if (current !== target) tabs[target].click();
            clearInterval(timer);
        }}
        if (++tries > 20) clearInterval(timer);
    }}, 120);
}})();
</script>
""", height=0, scrolling=False)

# ──────────────────────────────────────────────────────────
# タブ
# ──────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📋 一覧", "✨ 画像生成", "🖼️ 画像管理", "🌍 新規作成"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# タブ1: 一覧 / プロンプト編集（カテゴリ対応）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab1:
    # ── グルメ ──
    if gen_category == "🍜 グルメ":
        st.subheader("料理一覧・プロンプト編集")
        # 既存アイテムを名前でインデックス（フィールド保全用）
        _orig_by_name = {item.get("name"): item for item in food_items if item.get("name")}
        rows = []
        for item in food_items:
            rows.append({
                "name":        item.get("name", ""),
                "画像":        "✅" if image_exists(country_id, item) else "❌",
                "plate_color": item.get("plate_color", ""),
                "prompt_en":   item.get("prompt_en", ""),
            })
        edited = st.data_editor(
            rows,
            column_config={
                "name":        st.column_config.TextColumn("料理名", width="medium"),
                "画像":        st.column_config.TextColumn("画像", disabled=True, width="small"),
                "plate_color": st.column_config.TextColumn("皿の色（英語）", width="medium"),
                "prompt_en":   st.column_config.TextColumn("プロンプト（英語）", width="large"),
            },
            use_container_width=True,
            num_rows="dynamic",
            key="food_editor",
        )
        if st.button("💾 JSONを保存", type="primary", key="t1_food_save"):
            new_food_items = []
            for row in edited:
                name = (row.get("name") or "").strip()
                if not name:          # 空行はスキップ
                    continue
                orig = _orig_by_name.get(name, {})
                new_food_items.append({
                    "num":         f"No.{len(new_food_items)+1}",
                    "name":        name,
                    "badge":       orig.get("badge", ""),
                    "type":        orig.get("type", "main"),
                    "city":        orig.get("city", "national"),
                    "desc":        orig.get("desc", ""),
                    "image":       orig.get("image", ""),
                    "plate_color": (row.get("plate_color") or orig.get("plate_color", "")).strip(),
                    "prompt_en":   (row.get("prompt_en")   or orig.get("prompt_en",   "")).strip(),
                })
            data["food_items"] = new_food_items
            save_json(country_id, data)
            save_last_state({"tab": 0})
            for k in list(st.session_state.keys()):
                if k.startswith("gen_prompt_"):
                    del st.session_state[k]
            st.success("✅ 保存しました（バックアップ: .json.bak）")
            st.rerun()

    # ── ヒーロー画像 ──
    elif gen_category == "🏔️ ヒーロー画像":
        st.subheader("ヒーロー画像・プロンプト編集")
        _hpk = f"t1_hero_prompt_{country_id}"
        if not st.session_state.get(_hpk):
            st.session_state[_hpk] = data.get("hero_prompt", "")
        st.text_area("プロンプト（英語）", height=200, key=_hpk,
                     placeholder="e.g. Aerial panoramic view of...")
        if st.button("💾 JSONを保存", type="primary", key="t1_hero_save"):
            data["hero_prompt"] = st.session_state.get(_hpk, "")
            save_json(country_id, data)
            st.success("✅ 保存しました")

    # ── 観光スポット ──
    elif gen_category == "🗺️ 観光スポット":
        st.subheader("観光スポット・プロンプト編集")
        spot_secs = data.get("spot_sections", [])
        # 全セクションのスポットをフラット化
        spot_rows = []
        for s in spot_secs:
            cid   = s.get("city_id", "")
            cname = s.get("city_name", "")
            for spot in s.get("spots", []):
                sname = spot.get("name", "")
                spot_rows.append({
                    "city_id":   cid,
                    "都市":      cname,
                    "スポット名": sname,
                    "画像":      "✅" if (ROOT_DIR / country_id / spot.get("image", "X")).exists() else "❌",
                    "prompt_en": spot.get("prompt_en", ""),
                })
        if not spot_rows:
            st.warning("スポットが登録されていません。JSONの spot_sections > spots を確認してください。")
        else:
            edited_spots = st.data_editor(
                spot_rows,
                column_config={
                    "city_id":   None,
                    "都市":      st.column_config.TextColumn("都市", disabled=True, width="small"),
                    "スポット名": st.column_config.TextColumn("スポット名", disabled=True, width="medium"),
                    "画像":      st.column_config.TextColumn("画像", disabled=True, width="small"),
                    "prompt_en": st.column_config.TextColumn("プロンプト（英語）", width="large"),
                },
                use_container_width=True,
                key="spot_editor",
            )
            if st.button("💾 JSONを保存", type="primary", key="t1_spot_save"):
                # (city_id, spot_name) → prompt_en のルックアップを構築
                prompt_lookup = {
                    (r.get("city_id", ""), r.get("スポット名", "")): r.get("prompt_en", "")
                    for r in edited_spots
                }
                for s in data.get("spot_sections", []):
                    cid = s.get("city_id", "")
                    for spot in s.get("spots", []):
                        key = (cid, spot.get("name", ""))
                        if key in prompt_lookup:
                            spot["prompt_en"] = prompt_lookup[key]
                save_json(country_id, data)
                st.success("✅ 保存しました")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# タブ2: 画像生成
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab2:
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
        item_labels   = [
            f"{'✅' if image_exists(country_id, i) else '❌'} {i.get('num','')} {i.get('name','')}"
            for i in sorted_items
        ]
        last_dish    = last_state.get("dish") if last_state.get("country") == country_id else None
        default_dish = next((i for i, lbl in enumerate(item_labels) if last_dish and last_dish in lbl), 0)
        selected_label = st.selectbox("料理を選択", item_labels, index=default_dish, key="gen_select")
        sel_idx        = item_labels.index(selected_label)
        sel_item       = sorted_items[sel_idx]

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
            gen_btn = st.button("🎨 生成実行", type="primary", disabled=not prompt_val.strip())

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
            hero_gen_btn    = st.button(
                "🎨 生成実行", type="primary", key="hero_gen",
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
            _spot_labels   = [
                f"{'✅' if _spot_has_img(e) else '❌'} {e['city_name']} / {e['spot'].get('name','')}"
                for e in _sorted_spots
            ]
            _last_spot    = last_state.get("spot") if last_state.get("country") == country_id else None
            _default_spot = next((i for i, lbl in enumerate(_spot_labels) if _last_spot and _last_spot in lbl), 0)
            sel_spot_label = st.selectbox("スポットを選択", _spot_labels, index=_default_spot, key="spot_sel")
            sel_spot_entry = _sorted_spots[_spot_labels.index(sel_spot_label)]
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
                spot_gen_btn        = st.button(
                    "🎨 生成実行", type="primary", key="spot_gen",
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



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# タブ3: 画像管理（カテゴリ対応）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab3:
    st.subheader("画像管理")
    exts = {".webp", ".png", ".jpg", ".jpeg"}

    def _img_grid(files, del_key_prefix, json_rel_prefix=None):
        """画像グリッド表示（削除・背景除去・元に戻すボタン付き）"""
        if not files:
            st.info("画像ファイルがありません。")
            return
        st.caption(f"{len(files)} 枚")
        cols = st.columns(4)
        for i, fpath in enumerate(files):
            with cols[i % 4]:
                st.image(str(fpath), caption=fpath.name, use_container_width=True)
                orig_backup = fpath.parent / f"{fpath.stem}_orig.webp"
                has_orig = orig_backup.exists()
                _del_pending_key = f"{del_key_prefix}del_pending_{fpath.name}"
                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.session_state.get(_del_pending_key):
                        # 2段階目: 確認ボタン
                        if st.button("本当に削除", key=f"{del_key_prefix}del_confirm_{fpath.name}",
                                     type="primary", help="クリックで完全削除"):
                            fpath.unlink()
                            if orig_backup.exists():
                                orig_backup.unlink()
                            st.session_state.pop(_del_pending_key, None)
                            st.rerun()
                        if st.button("✕", key=f"{del_key_prefix}del_cancel_{fpath.name}", help="キャンセル"):
                            st.session_state.pop(_del_pending_key, None)
                            st.rerun()
                    else:
                        # 1段階目: 削除ボタン
                        if st.button("🗑️", key=f"{del_key_prefix}del_{fpath.name}", help="削除（確認あり）"):
                            st.session_state[_del_pending_key] = True
                            st.rerun()
                with b2:
                    if st.button("✂️", key=f"{del_key_prefix}bg_{fpath.name}", help="背景除去"):
                        with st.spinner("処理中（ローカル処理）..."):
                            try:
                                orig_bytes = fpath.read_bytes()
                                bg_bytes   = rembg_remove(orig_bytes, session=_get_rembg_session())
                                webp_bytes = to_webp(bg_bytes)
                                new_path   = fpath.with_suffix(".webp")
                                # 元画像をバックアップ（まだバックアップがない場合のみ）
                                bak_path = new_path.parent / f"{new_path.stem}_orig.webp"
                                if not bak_path.exists():
                                    bak_path.write_bytes(orig_bytes)
                                new_path.write_bytes(webp_bytes)
                                if json_rel_prefix:
                                    rel_old = f"{json_rel_prefix}{fpath.name}"
                                    rel_new = f"{json_rel_prefix}{new_path.name}"
                                    for fi in food_items:
                                        if fi.get("image") == rel_old:
                                            fi["image"] = rel_new
                                            break
                                    data["food_items"] = food_items
                                    save_json(country_id, data)
                                if fpath != new_path:
                                    fpath.unlink()
                                st.success(f"完了 → {new_path.name}")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                with b3:
                    if has_orig:
                        if st.button("↩️", key=f"{del_key_prefix}undo_{fpath.name}", help="元に戻す"):
                            fpath.write_bytes(orig_backup.read_bytes())
                            orig_backup.unlink()
                            st.success(f"元に戻しました: {fpath.name}")
                            st.rerun()

    # ── グルメ ──
    if gen_category == "🍜 グルメ":
        img_dir = food_dir(country_id)
        if not img_dir.exists():
            st.info("素材/グルメ/ フォルダがまだ存在しません。")
        else:
            files   = sorted([f for f in img_dir.iterdir() if f.suffix.lower() in exts])
            non_webp = [f for f in files if f.suffix.lower() in {".png", ".jpg", ".jpeg"}]
            if non_webp:
                if st.button(f"🔄 WebP一括変換（{len(non_webp)}枚）", type="primary"):
                    converted = 0
                    for fpath in non_webp:
                        try:
                            new_path = fpath.with_suffix(".webp")
                            new_path.write_bytes(to_webp(fpath.read_bytes()))
                            rel_old = f"素材/グルメ/{fpath.name}"
                            rel_new = f"素材/グルメ/{new_path.name}"
                            for fi in food_items:
                                if fi.get("image") == rel_old:
                                    fi["image"] = rel_new; break
                            if fpath != new_path: fpath.unlink()
                            converted += 1
                        except Exception as e:
                            st.error(f"{fpath.name}: {e}")
                    if converted:
                        data["food_items"] = food_items
                        save_json(country_id, data)
                        st.success(f"✅ {converted}枚をWebPに変換しました")
                        st.rerun()
            _img_grid(files, "g3_", "素材/グルメ/")

    # ── ヒーロー画像 ──
    elif gen_category == "🏔️ ヒーロー画像":
        hero_path = ROOT_DIR / country_id / "素材" / "ヒーロー.webp"
        if hero_path.exists():
            st.image(str(hero_path), caption="ヒーロー.webp", use_container_width=True)
            if st.button("🗑️ 削除", key="t3_hero_del"):
                hero_path.unlink()
                st.success("削除しました")
                st.rerun()
        else:
            st.info("ヒーロー画像がまだありません。")

    # ── 観光スポット ──
    elif gen_category == "🗺️ 観光スポット":
        spot_img_dir = ROOT_DIR / country_id / "素材" / "観光スポット"
        if not spot_img_dir.exists():
            st.info("素材/観光スポット/ フォルダがまだ存在しません。")
        else:
            files = sorted([f for f in spot_img_dir.iterdir() if f.suffix.lower() in exts])
            _img_grid(files, "g3s_")


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
    p["country_items_label"] = ""; p["country_items"] = []
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


with tab4:
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
