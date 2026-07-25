"""Public image links used when sharing life-number results."""

from __future__ import annotations

from typing import Any


LIFE_NUMBER_IMAGE_BASE_URL = (
    "https://raw.githubusercontent.com/jackho1314/rich_ai_project/main"
)


def life_number_image_url(life_path: Any) -> str:
    """Return the matching public image URL for a life number from 1 to 9."""
    try:
        number = int(str(life_path).strip())
    except (TypeError, ValueError):
        return ""
    if number not in range(1, 10):
        return ""
    return f"{LIFE_NUMBER_IMAGE_BASE_URL}/life-number-{number}.jpg"


def life_number_image_share_block(life_path: Any) -> str:
    """Build the two-line image block appended to LINE share text."""
    image_url = life_number_image_url(life_path)
    if not image_url:
        return ""
    number = int(str(life_path).strip())
    return f"🖼️ 我的 {number} 號人專屬圖卡：\n{image_url}"
