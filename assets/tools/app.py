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

import streamlit as st
from PIL import Image

import recraft_api

# ──────────────────────────────────────────────────────────
# パス定義
# ──────────────────────────────────────────────────────────
TOOLS_DIR   = Path(__file__).parent          # assets/tools/
ASSETS_DIR  = TOOLS_DIR.parent              # assets/
ROOT_DIR    = ASSETS_DIR.parent             # World guide/
GENERATE_PY = TOOLS_DIR / "generate.py"
LAST_STATE  = TOOLS_DIR / ".last_state.json"


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
    try:
        LAST_STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


# ──────────────────────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────────────────────
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
</style>
""", unsafe_allow_html=True)
st.title("🎨 Recraft 画像生成ツール")

# 国選択
countries  = detect_countries()
last_state = load_last_state()
if not countries:
    st.error("国フォルダが見つかりません。World guide/ 直下に <country>/<country>.json を用意してください。")
    st.stop()

col_sel, col_info, col_cr = st.columns([2, 3, 2])
with col_sel:
    last_country = last_state.get("country", countries[0])
    country_idx  = countries.index(last_country) if last_country in countries else 0
    country_id   = st.selectbox("国を選択", countries, index=country_idx)

data       = load_json(country_id)
food_items = data.get("food_items", [])

with col_info:
    total   = len(food_items)
    has_img = sum(1 for item in food_items if image_exists(country_id, item))
    st.metric("料理数", total)
    st.caption(f"画像あり: {has_img} / {total}")

with col_cr:
    credits = recraft_api.get_credits()
    if credits >= 0:
        yen = credits * 0.16
        st.metric("Recraftクレジット", f"{credits:,} cr")
        st.markdown(f"<p style='font-size:1.4em;font-weight:700;margin-top:-12px;color:#1a6fa8;'>≈ ¥{yen:,.0f}</p>", unsafe_allow_html=True)
    else:
        st.metric("Recraftクレジット", "取得失敗")

st.divider()

# ──────────────────────────────────────────────────────────
# タブ
# ──────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📋 料理一覧", "✨ 画像生成", "🖼️ 画像管理", "🚀 サイト更新"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# タブ1: 料理一覧 / プロンプト編集
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab1:
    st.subheader("料理一覧・プロンプト編集")

    rows = []
    for item in food_items:
        rows.append({
            "num":         item.get("num", ""),
            "name":        item.get("name", ""),
            "画像":        "✅" if image_exists(country_id, item) else "❌",
            "plate_color": item.get("plate_color", ""),
            "prompt_en":   item.get("prompt_en", ""),
        })

    edited = st.data_editor(
        rows,
        column_config={
            "num":         st.column_config.TextColumn("No.", disabled=True, width="small"),
            "name":        st.column_config.TextColumn("料理名", disabled=True, width="medium"),
            "画像":        st.column_config.TextColumn("画像", disabled=True, width="small"),
            "plate_color": st.column_config.TextColumn("皿の色（英語）", width="medium"),
            "prompt_en":   st.column_config.TextColumn("プロンプト（英語）", width="large"),
        },
        use_container_width=True,
        num_rows="fixed",
        key="food_editor",
    )

    if st.button("💾 JSONを保存", type="primary"):
        for i, row in enumerate(edited):
            food_items[i]["plate_color"] = row["plate_color"]
            food_items[i]["prompt_en"]   = row["prompt_en"]
        data["food_items"] = food_items
        save_json(country_id, data)
        st.success("✅ 保存しました（バックアップ: .json.bak）")
        st.rerun()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# タブ2: 画像生成
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab2:
    st.subheader("画像生成")

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

    # 選択状態を保存
    save_last_state({"country": country_id, "dish": sel_item.get("name", "")})

    st.divider()

    # ── カラム描画より先に値を確定（col_l の保存ボタンで参照するため）──
    item_key   = sel_item.get("num", "0").replace(".", "_")
    key_prompt = f"gen_prompt_{item_key}"
    if not st.session_state.get(key_prompt) and sel_item.get("prompt_en"):
        st.session_state[key_prompt] = sel_item["prompt_en"]

    SHAPES = {
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

    # 既存 plate_color から形状・色を逆引きしてデフォルト値を決定
    saved_plate   = sel_item.get("plate_color", "white ceramic plate")
    default_shape = "プレート"
    default_color = "白"
    for jp_s, en_s in SHAPES.items():
        if en_s in saved_plate:
            default_shape = jp_s
            break
    for jp_c, en_c in COLORS.items():
        if en_c and en_c in saved_plate:
            default_color = jp_c
            break

    shape_key  = f"gen_shape_{item_key}"
    color_key  = f"gen_color_{item_key}"
    _shape_now = st.session_state.get(shape_key, default_shape)
    _color_now = st.session_state.get(color_key, default_color)
    if _shape_now not in SHAPES: _shape_now = default_shape
    if _color_now not in COLORS: _color_now = default_color

    en_shape        = SHAPES[_shape_now]
    en_color        = COLORS[_color_now]
    plate_color_val = f"{en_color} {en_shape}".strip() if en_color else en_shape
    prompt_val      = st.session_state.get(key_prompt, sel_item.get("prompt_en", ""))

    if "gen_results" not in st.session_state:
        st.session_state["gen_results"] = []   # [{bytes, ext, credits, name}, ...]

    col_l, col_r = st.columns(2)

    with col_l:
        results = st.session_state.get("gen_results", [])
        if results:
            hdr_l, hdr_r = st.columns([4, 1])
            with hdr_l:
                st.caption(f"生成した画像 ({len(results)}枚) — 保存したい1枚を選んでください")
            with hdr_r:
                if st.button("🗑️ 全削除", help="生成画像をすべて破棄"):
                    st.session_state["gen_results"] = []
                    st.rerun()

            ncols = min(len(results), 2)
            img_cols = st.columns(ncols)
            for i, res in enumerate(results):
                with img_cols[i % ncols]:
                    cr_str = f"消費: {res['credits']}cr" if res.get("credits") else ""
                    st.caption(f"#{i+1}　{cr_str}")
                    st.image(res["bytes"], use_container_width=True)
                    b1, b2, b3 = st.columns(3)
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
                            st.success(f"✅ 保存: {out_path.name}")
                            st.session_state["gen_results"] = []
                            st.rerun()
                    with b2:
                        if st.button("✂️", key=f"bg_{i}", help="背景除去"):
                            with st.spinner("処理中..."):
                                try:
                                    bg_bytes, _ = recraft_api.remove_background(res["bytes"])
                                    st.session_state["gen_results"][i]["bytes"] = to_webp(bg_bytes)
                                    st.rerun()
                                except RuntimeError as e:
                                    st.error(str(e))
                    with b3:
                        if st.button("🗑️", key=f"del_{i}", help="この画像を削除"):
                            st.session_state["gen_results"].pop(i)
                            st.rerun()
        else:
            existing_path = ROOT_DIR / country_id / sel_item.get("image", "")
            if existing_path.exists() and sel_item.get("image"):
                st.caption("現在の画像")
                st.image(str(existing_path), use_container_width=True)
            else:
                st.info("画像未生成")

    with col_r:
        st.markdown(f"**{sel_item.get('name', '')}**")
        st.text_area("プロンプト（英語）", height=140, key=key_prompt)

        sc1, sc2 = st.columns(2)
        with sc1:
            st.selectbox(
                "皿の形状",
                list(SHAPES.keys()),
                index=list(SHAPES.keys()).index(_shape_now),
                key=shape_key,
            )
        with sc2:
            st.selectbox(
                "皿の色",
                list(COLORS.keys()),
                index=list(COLORS.keys()).index(_color_now),
                key=color_key,
            )

        st.markdown(
            f"<p style='font-size:1.1em;font-weight:600;color:#444;margin:2px 0 8px;'>"
            f"→ {plate_color_val}</p>",
            unsafe_allow_html=True,
        )
        model_val = st.radio(
            "モデル",
            ["recraft20b  22cr ≈ ¥3.5/枚", "recraftv3  40cr ≈ ¥6.4/枚"],
            horizontal=True,
        )
        model_key_r = "recraft20b" if "recraft20b" in model_val else "recraftv3"
        gen_btn = st.button("🎨 生成実行", type="primary", disabled=not prompt_val.strip())

    if gen_btn:
        if not prompt_val.strip():
            st.warning("プロンプトを入力してください。")
        else:
            with st.spinner("生成中..."):
                try:
                    img_bytes, cr1 = recraft_api.generate_image(
                        prompt=prompt_val,
                        plate_color=plate_color_val,
                        model=model_key_r,
                    )
                    st.session_state["gen_results"].append({
                        "bytes":   img_bytes,
                        "ext":     "webp",
                        "credits": cr1,
                        "name":    sel_item.get("name", "output"),
                    })
                except RuntimeError as e:
                    st.error(str(e))
        if st.session_state.get("gen_results"):
            st.rerun()



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# タブ3: 画像管理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab3:
    st.subheader("画像管理")
    img_dir = food_dir(country_id)

    if not img_dir.exists():
        st.info("素材/グルメ/ フォルダがまだ存在しません。")
    else:
        exts  = {".webp", ".png", ".jpg", ".jpeg"}
        files = sorted([f for f in img_dir.iterdir() if f.suffix.lower() in exts])

        # PNG / JPG が存在する場合は一括変換ボタンを表示
        non_webp = [f for f in files if f.suffix.lower() in {".png", ".jpg", ".jpeg"}]
        if non_webp:
            if st.button(f"🔄 WebP一括変換（{len(non_webp)}枚）", type="primary"):
                converted = 0
                for fpath in non_webp:
                    try:
                        webp_bytes = to_webp(fpath.read_bytes())
                        new_path   = fpath.with_suffix(".webp")
                        new_path.write_bytes(webp_bytes)
                        # JSON の image パスを更新
                        rel_old = f"素材/グルメ/{fpath.name}"
                        rel_new = f"素材/グルメ/{new_path.name}"
                        for fi in food_items:
                            if fi.get("image") == rel_old:
                                fi["image"] = rel_new
                                break
                        if fpath != new_path:
                            fpath.unlink()
                        converted += 1
                    except Exception as e:
                        st.error(f"{fpath.name}: {e}")
                if converted:
                    data["food_items"] = food_items
                    save_json(country_id, data)
                    st.success(f"✅ {converted}枚をWebPに変換しました")
                    st.rerun()

        if not files:
            st.info("画像ファイルがありません。")
        else:
            st.caption(f"{len(files)} 枚")
            cols = st.columns(4)
            for i, fpath in enumerate(files):
                with cols[i % 4]:
                    st.image(str(fpath), caption=fpath.name, use_container_width=True)
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("🗑️", key=f"del_{fpath.name}", help="削除"):
                            fpath.unlink()
                            st.success(f"削除: {fpath.name}")
                            st.rerun()
                    with b2:
                        is_png = fpath.suffix.lower() == ".png"
                        if st.button("✂️", key=f"bg_{fpath.name}", help="背景透過（+10cr）",
                                     disabled=is_png):
                            with st.spinner("処理中..."):
                                try:
                                    bg_bytes, cr2 = recraft_api.remove_background(fpath.read_bytes())
                                    # 背景除去後も WebP で保存（透過チャンネル保持）
                                    webp_bytes = to_webp(bg_bytes)
                                    new_path   = fpath.with_suffix(".webp")
                                    new_path.write_bytes(webp_bytes)
                                    # JSON の image パスを更新
                                    rel_old = f"素材/グルメ/{fpath.name}"
                                    rel_new = f"素材/グルメ/{new_path.name}"
                                    for fi in food_items:
                                        if fi.get("image") == rel_old:
                                            fi["image"] = rel_new
                                            break
                                    data["food_items"] = food_items
                                    save_json(country_id, data)
                                    if fpath != new_path:
                                        fpath.unlink()
                                    st.success(f"完了 -{cr2}cr → {new_path.name}")
                                    st.rerun()
                                except RuntimeError as e:
                                    st.error(str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# タブ4: サイト更新
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab4:
    st.subheader("サイト更新（generate.py 実行）")
    st.info(f"対象: **{country_id}** の index.html を再生成します。")

    if st.button("🚀 generate.py を実行", type="primary"):
        with st.spinner("実行中..."):
            try:
                result = subprocess.run(
                    [sys.executable, "-X", "utf8", str(GENERATE_PY), country_id],
                    capture_output=True,
                    cwd=str(TOOLS_DIR),
                )
                stdout = result.stdout.decode("utf-8", errors="replace")
                stderr = result.stderr.decode("utf-8", errors="replace")
                returncode = result.returncode
            except Exception as e:
                stdout, stderr, returncode = "", str(e), -1

        if returncode == 0:
            st.success("✅ 生成完了！")
        else:
            st.error(f"❌ エラーが発生しました（returncode={returncode}）")

        if stdout:
            st.text_area("stdout", stdout, height=120)
        if stderr:
            st.text_area("stderr（エラー詳細）", stderr, height=200)
