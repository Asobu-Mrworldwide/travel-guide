"""
Recraft 画像生成管理アプリ
起動: python -m streamlit run assets/tools/app.py
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import streamlit as st

import recraft_api

# ──────────────────────────────────────────────────────────
# パス定義
# ──────────────────────────────────────────────────────────
TOOLS_DIR   = Path(__file__).parent          # assets/tools/
ASSETS_DIR  = TOOLS_DIR.parent              # assets/
ROOT_DIR    = ASSETS_DIR.parent             # World guide/
GENERATE_PY = TOOLS_DIR / "generate.py"
LAST_STATE  = TOOLS_DIR / ".last_state.json"


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
    st.metric("Recraftクレジット", f"{credits:,}" if credits >= 0 else "取得失敗")

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
    col_l, col_r = st.columns(2)

    with col_l:
        # 既存画像を左に表示
        existing_path = ROOT_DIR / country_id / sel_item.get("image", "")
        if existing_path.exists() and sel_item.get("image"):
            st.caption("現在の画像")
            st.image(str(existing_path), use_container_width=True)
        else:
            st.info("画像未生成")

    with col_r:
        st.markdown(f"**{sel_item.get('name', '')}**")
        item_key   = sel_item.get("num", "0").replace(".", "_")
        key_prompt = f"gen_prompt_{item_key}"
        # セッションキャッシュが空でJSONに値があれば強制セット
        if not st.session_state.get(key_prompt) and sel_item.get("prompt_en"):
            st.session_state[key_prompt] = sel_item["prompt_en"]

        prompt_val = st.text_area(
            "プロンプト（英語）",
            height=140,
            key=key_prompt,
        )

        # 皿の形状・色をセレクトボックスで選択
        SHAPES = {
            "プレート":       "ceramic plate",
            "ボウル":         "ceramic bowl",
            "深めのボウル":   "deep ceramic bowl",
            "グラス":         "tall glass",
            "カップ":         "ceramic cup",
            "鉄鍋":           "cast iron pan",
            "木の皿":         "wooden plate",
        }
        COLORS = {
            "白":           "white",
            "オフホワイト": "off-white",
            "ベージュ":     "beige",
            "クリーム":     "cream",
            "水色":         "light blue",
            "ブルー":       "blue",
            "ネイビー":     "navy",
            "グリーン":     "green",
            "セージグリーン": "sage green",
            "イエロー":     "yellow",
            "オレンジ":     "orange",
            "テラコッタ":   "terracotta",
            "レッド":       "red",
            "ピンク":       "pink",
            "パープル":     "purple",
            "ブラウン":     "brown",
            "ダーク":       "dark",
            "ブラック":     "black",
            "グレー":       "gray",
            "なし":         "",
        }

        # 既存の plate_color から形状・色を逆引き（初期値設定）
        saved_plate = sel_item.get("plate_color", "white ceramic plate")
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

        sc1, sc2 = st.columns(2)
        with sc1:
            shape_sel = st.selectbox(
                "皿の形状",
                list(SHAPES.keys()),
                index=list(SHAPES.keys()).index(default_shape),
                key=f"gen_shape_{item_key}",
            )
        with sc2:
            color_sel = st.selectbox(
                "皿の色",
                list(COLORS.keys()),
                index=list(COLORS.keys()).index(default_color),
                key=f"gen_color_{item_key}",  # item_keyはすでに._置換済み
            )

        en_shape = SHAPES[shape_sel]
        en_color = COLORS[color_sel]
        plate_color_val = f"{en_color} {en_shape}".strip() if en_color else en_shape
        st.caption(f"→ `{plate_color_val}`")
        model_val = st.radio(
            "モデル",
            ["recraft20b (~22cr)", "recraftv3 (~40cr)"],
            horizontal=True,
        )
        model_key = "recraft20b" if "recraft20b" in model_val else "recraftv3"
        gen_btn = st.button("🎨 生成実行", type="primary", disabled=not prompt_val.strip())

    # 生成結果エリア（全幅）
    if "gen_result" not in st.session_state:
        st.session_state["gen_result"]      = None
        st.session_state["gen_result_name"] = None
        st.session_state["gen_ext"]         = "webp"

    if gen_btn:
        if not prompt_val.strip():
            st.warning("プロンプトを入力してください。")
        else:
            with st.spinner("生成中..."):
                try:
                    img_bytes, cr1 = recraft_api.generate_image(
                        prompt=prompt_val,
                        plate_color=plate_color_val,
                        model=model_key,
                    )
                    st.session_state["gen_result"]      = img_bytes
                    st.session_state["gen_result_name"] = sel_item.get("name", "output")
                    st.session_state["gen_ext"]         = "webp"
                    st.success(f"生成完了！　消費クレジット: {cr1}")
                except RuntimeError as e:
                    st.error(str(e))

    if st.session_state["gen_result"] is not None:
        st.divider()
        ext_label = "PNG（背景透過）" if st.session_state["gen_ext"] == "png" else "WebP"
        st.caption(f"新しく生成した画像（{ext_label}）")
        st.image(st.session_state["gen_result"], use_container_width=True)

        btn1, btn2, btn3 = st.columns(3)

        with btn1:
            if st.button("💾 この画像を保存", type="primary"):
                name    = st.session_state["gen_result_name"]
                ext     = st.session_state["gen_ext"]
                out_dir = food_dir(country_id)
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{name}.{ext}"
                out_path.write_bytes(st.session_state["gen_result"])
                rel_path = f"素材/グルメ/{name}.{ext}"
                for fi in food_items:
                    if fi.get("name") == name:
                        fi["image"]       = rel_path
                        fi["prompt_en"]   = prompt_val
                        fi["plate_color"] = plate_color_val
                        break
                data["food_items"] = food_items
                save_json(country_id, data)
                st.success(f"✅ 保存: {out_path.name}")
                st.session_state["gen_result"] = None
                st.rerun()

        with btn2:
            if st.button("✂️ 背景除去（+10cr）"):
                with st.spinner("背景除去中..."):
                    try:
                        bg_bytes, cr2 = recraft_api.remove_background(
                            st.session_state["gen_result"]
                        )
                        st.session_state["gen_result"] = bg_bytes
                        st.session_state["gen_ext"]    = "png"
                        st.success(f"背景除去完了！　消費クレジット: {cr2}")
                        st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))

        with btn3:
            if st.button("🔄 破棄して再生成"):
                st.session_state["gen_result"] = None
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

        if not files:
            st.info("画像ファイルがありません。")
        else:
            st.caption(f"{len(files)} 枚")
            cols = st.columns(4)
            for i, fpath in enumerate(files):
                with cols[i % 4]:
                    st.image(str(fpath), caption=fpath.name, use_container_width=True)
                    if st.button("🗑️ 削除", key=f"del_{fpath.name}"):
                        fpath.unlink()
                        st.success(f"削除: {fpath.name}")
                        st.rerun()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# タブ4: サイト更新
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab4:
    st.subheader("サイト更新（generate.py 実行）")
    st.info(f"対象: **{country_id}** の index.html を再生成します。")

    if st.button("🚀 generate.py を実行", type="primary"):
        with st.spinner("実行中..."):
            result = subprocess.run(
                [sys.executable, str(GENERATE_PY), country_id],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=str(TOOLS_DIR),
            )
        if result.returncode == 0:
            st.success("✅ 生成完了！")
        else:
            st.error("❌ エラーが発生しました。")

        if result.stdout:
            st.text_area("stdout", result.stdout, height=100)
        if result.stderr:
            st.text_area("stderr", result.stderr, height=100)
