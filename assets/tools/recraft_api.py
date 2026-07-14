"""
Recraft API ラッパー
"""
import socket
import time

import requests
import urllib3.util.connection as _urllib3_conn

# このマシンはデフォルトでIPv6(NAT64)経由の接続を優先するが、その経路が不安定で
# ConnectionResetError(10054)やタイムアウトが頻発する（実測で約6割が失敗）。
# IPv4接続は安定しているため、プロセス全体でIPv4を強制する。
_urllib3_conn.allowed_gai_family = lambda: socket.AF_INET

API_KEY  = "Wo1jeJZqRrD88QF8tRLGuYCCM8oBzYEYA8wptkXgaKP4hKLEWuM37k80C72MJpd3"
BASE_URL = "https://external.api.recraft.ai/v1"

# NAT64等の不安定な経路で ConnectionResetError(10054) が起きることがあるため、
# ネットワーク層のエラーのみ待機を挟んでリトライする（API側のエラーはリトライしない）。
# 待機時間は 2s→4s→8s→16s と指数的に伸ばし、単発の瞬断より長い障害にも粘る。
_RETRY_COUNT = 5
_RETRY_BASE_WAIT_SEC = 2
_REQUEST_TIMEOUT = 60


def _request_with_retry(method: str, url: str, **kwargs) -> requests.Response:
    kwargs.setdefault("timeout", _REQUEST_TIMEOUT)
    last_err = None
    for attempt in range(1, _RETRY_COUNT + 1):
        try:
            return requests.request(method, url, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_err = e
            if attempt < _RETRY_COUNT:
                time.sleep(_RETRY_BASE_WAIT_SEC * (2 ** (attempt - 1)))
    raise last_err

STYLE_IDS = {
    "recraftv3":   "b516fe3c-488e-4156-8d6f-cf4001afabaf",  # ~40cr/枚
    "recraft20b":  "22e8c6e6-6115-4a87-9947-97f30035270d",  # ~22cr/枚
    "watercolor":  "8e7eb6b9-3323-460c-b48c-6f5a9dfe5796",  # 水彩 ~40cr/枚
    "vector_art":  "641438a8-5f63-4710-b7e9-52bd3eab4c46",  # フラットベクターイラスト ~40cr/枚
    "style_new":   "87bd8c4b-3fde-41cf-a6e1-a8fad8b3ef89",  # 新スタイル (recraft20bベース)
    "style_spot":  "b2b0bc9d-430e-4bbe-a021-598140916fff",  # 観光スポット用スタイル
    "style_spot2": "8b00a308-fe96-46dc-83d9-0c0751cce0e2",  # 観光スポット用スタイル v2
    "style_spot3": "0aff9d28-5e11-41c0-bd52-61ccd8449963",  # 観光スポット用スタイル v3
    "style_spot4": "3765cf6e-0cf9-49ed-8b44-9200c2f68289",  # 観光スポット用スタイル v4
    "style_spot5": "0fa21982-70a8-4857-b62f-093dac9c7771",  # 観光スポット用スタイル v5
    "style_food_0710": "568daa6a-9631-44e7-a615-ce547146ae52",  # グルメイラスト用スタイル (2026-07-10追加)
    # watercolor20b は style_id なし（プロンプト強化で代替）
}

# style キーに対応する実際の model パラメータ
BASE_MODELS = {
    "recraftv3":    "recraftv3",
    "recraft20b":   "recraft20b",
    "watercolor":   "recraftv3",
    "watercolor20b":"recraft20b",
    "vector_art":   "recraft20b",   # フラットベクター: recraft20b ベース
    "style_new":    "recraft20b",   # 新スタイル: recraft20b ベース
    "style_spot":   "recraftv3",    # 観光スポット用スタイル: recraftv3 ベース
    "style_spot2":  "recraftv3",    # 観光スポット用スタイル v2: recraftv3 ベース
    "style_spot3":  "recraftv3",    # 観光スポット用スタイル v3: recraftv3 ベース
    "style_spot4":  "recraftv3",    # 観光スポット用スタイル v4: recraftv3 ベース
    "style_spot5":  "recraftv3",    # 観光スポット用スタイル v5: recraftv3 ベース
    "style_food_0710": "recraftv2",  # グルメイラスト用スタイル (2026-07-10追加): recraftv2 ベース
}

# モデルキーごとにプロンプト先頭に自動付与するプレフィックス
PROMPT_PREFIXES = {
    "watercolor20b": (
        "watercolor illustration, soft watercolor brush strokes, "
        "painterly texture, hand-painted style, delicate color washes,"
    ),
    "style_food_0710": (
        "plain solid white background, no colored background, no background scenery, "
        "no background pattern, isolated food illustration on white,"
    ),
}


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {API_KEY}"}


def get_credits() -> int:
    """現在のクレジット残高を返す。失敗時は -1"""
    resp = _request_with_retry("GET", f"{BASE_URL}/users/me", headers=_auth_headers())
    if resp.status_code == 200:
        return resp.json().get("credits", -1)
    return -1


def generate_image(prompt: str, plate_color: str, model: str = "recraft20b",
                   width: int = 1024, height: int = 1024,
                   use_style: bool = True) -> tuple[bytes, int]:
    """
    画像を生成してバイナリと消費クレジット数を返す。
    use_style=False にするとスタイルIDを送らず、アングル指示が通りやすくなる。
    失敗時は RuntimeError を raise。
    """
    # watercolor20b 等はプレフィックスでスタイルを補強
    prefix = PROMPT_PREFIXES.get(model, "")
    if plate_color == "no plate":
        content = (f"{prompt}, no plate, no dish, no bowl, no tableware, "
                   "food only, isolated on plain background.")
    elif plate_color:
        content = f"{prompt}, served on a {plate_color}."
    else:
        content = prompt
    full_prompt = f"{prefix} {content}".strip() if prefix else content
    actual_model = BASE_MODELS.get(model, model)   # "watercolor" → "recraftv3" に変換
    headers = {**_auth_headers(), "Content-Type": "application/json"}
    payload = {
        "prompt": full_prompt,
        "model":  actual_model,
        "size":   f"{width}x{height}",
    }
    if use_style and model in STYLE_IDS:
        payload["style_id"] = STYLE_IDS[model]
    resp = _request_with_retry("POST", f"{BASE_URL}/images/generations", headers=headers, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f"生成失敗 ({resp.status_code}): {resp.text}")

    data    = resp.json()
    credits = data.get("credits", 0)
    url     = data["data"][0]["url"]

    dl = _request_with_retry("GET", url)
    if dl.status_code != 200:
        raise RuntimeError(f"ダウンロード失敗 ({dl.status_code})")
    return dl.content, credits


def remove_background(image_bytes: bytes) -> tuple[bytes, int]:
    """
    背景除去した PNG バイナリと消費クレジット数を返す。
    失敗時は RuntimeError を raise。
    """
    resp = _request_with_retry(
        "POST",
        f"{BASE_URL}/images/removeBackground",
        headers=_auth_headers(),
        files={"file": ("image.webp", image_bytes, "image/webp")},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"背景除去失敗 ({resp.status_code}): {resp.text}")

    data    = resp.json()
    credits = data.get("credits", 0)
    url     = data["image"]["url"]

    dl = _request_with_retry("GET", url)
    if dl.status_code != 200:
        raise RuntimeError(f"ダウンロード失敗 ({dl.status_code})")
    return dl.content, credits
