"""URL ảnh đã ký — dùng chung cho màn soạn thiệp và web thiệp công khai."""

from __future__ import annotations

import time
from typing import Final
from uuid import UUID

from app.core.config import get_settings
from app.core.security import signing

SIGN_KIND: Final[str] = "photo"

#: Làm tròn mốc hết hạn theo giờ: cùng một ảnh trong cùng một giờ cho ra CÙNG
#: một URL, nên trình duyệt dùng lại bộ nhớ đệm thay vì tải lại mỗi lần mở trang.
_BUCKET_SECONDS: Final[int] = 3600


def photo_url(photo_id: UUID, *, small: bool = False) -> str:
    """URL tuyệt đối, tự hết hạn sau `MEDIA_URL_TTL_SECONDS` (cộng tối đa 1 giờ).

    `small`: bản nhỏ cho điện thoại (`&w=sm`). Chữ ký chỉ gắn với ảnh, không với cỡ —
    hai bản là cùng một bức ảnh công khai như nhau.
    """
    cfg = get_settings()
    bucket_start = int(time.time()) // _BUCKET_SECONDS * _BUCKET_SECONDS
    expires_at, signature = signing.sign(
        SIGN_KIND,
        str(photo_id),
        ttl_seconds=cfg.MEDIA_URL_TTL_SECONDS + _BUCKET_SECONDS,
        now=bucket_start,
    )
    return (
        f"{cfg.PUBLIC_API_URL}{cfg.API_PREFIX}/media/photos/{photo_id}"
        f"?exp={expires_at}&sig={signature}{'&w=sm' if small else ''}"
    )


__all__ = ["SIGN_KIND", "photo_url"]
