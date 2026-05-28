"""
Recraft API ラッパー
"""
import requests

API_KEY  = "Wo1jeJZqRrD88QF8tRLGuYCCM8oBzYEYA8wptkXgaKP4hKLEWuM37k80C72MJpd3"
BASE_URL = "https://external.api.recraft.ai/v1"

STYLE_IDS = {
    "recraftv3":  "b516fe3c-488e-4156-8d6f-cf4001afabaf",  # ~40cr/枚
    "recraft20b": "22e8c6e6-6115-4a87-9947-97f30035270d",  # ~22cr/枚
}


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {API_KEY}"}


def get_credits() -> int:
    """現在のクレジット残高を返す。失敗時は -1"""
    resp = requests.get(f"{BASE_URL}/users/me", headers=_auth_headers())
    if resp.status_code == 200:
        return resp.json().get("credits", -1)
    return -1


def generate_image(prompt: str, plate_color: str, model: str = "recraft20b",
                   width: int = 1024, height: int = 1024) -> tuple[bytes, int]:
    """
    画像を生成してバイナリと消費クレジット数を返す。
    失敗時は RuntimeError を raise。
    """
    full_prompt = f"{prompt}, served on a {plate_color}."
    headers = {**_auth_headers(), "Content-Type": "application/json"}
    payload = {
        "prompt": full_prompt,
        "model":  model,
        "style_id": STYLE_IDS[model],
        "width":  width,
        "height": height,
    }
    resp = requests.post(f"{BASE_URL}/images/generations", headers=headers, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f"生成失敗 ({resp.status_code}): {resp.text}")

    data    = resp.json()
    credits = data.get("credits", 0)
    url     = data["data"][0]["url"]

    dl = requests.get(url)
    if dl.status_code != 200:
        raise RuntimeError(f"ダウンロード失敗 ({dl.status_code})")
    return dl.content, credits


def remove_background(image_bytes: bytes) -> tuple[bytes, int]:
    """
    背景除去した PNG バイナリと消費クレジット数を返す。
    失敗時は RuntimeError を raise。
    """
    resp = requests.post(
        f"{BASE_URL}/images/removeBackground",
        headers=_auth_headers(),
        files={"file": ("image.webp", image_bytes, "image/webp")},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"背景除去失敗 ({resp.status_code}): {resp.text}")

    data    = resp.json()
    credits = data.get("credits", 0)
    url     = data["image"]["url"]

    dl = requests.get(url)
    if dl.status_code != 200:
        raise RuntimeError(f"ダウンロード失敗 ({dl.status_code})")
    return dl.content, credits
