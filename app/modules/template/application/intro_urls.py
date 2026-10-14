"""URL video mở thiệp đã ký — dùng chung cho thư viện (màn soạn) và web thiệp công khai.

Ký y hệt URL ảnh cưới (`media`), chỉ khác loại chữ ký (`intro`): chữ ký của ảnh
không mở được video và ngược lại.
"""

from __future__ import annotations

import time
from typing import Final
from uuid import UUID

from app.core.config import get_settings
from app.core.security import signing

SIGN_KIND: Final[str] = "intro"

#: Làm tròn mốc hết hạn theo giờ: cùng một video trong cùng một giờ cho ra CÙNG
#: một URL, nên trình duyệt dùng lại bộ nhớ đệm thay vì tải lại video.
_BUCKET_SECONDS: Final[int] = 3600


def intro_url(intro_id: UUID) -> str:
    """URL tuyệt đối, tự hết hạn sau `MEDIA_URL_TTL_SECONDS` (cộng tối đa 1 giờ)."""
    cfg = get_settings()
    bucket_start = int(time.time()) // _BUCKET_SECONDS * _BUCKET_SECONDS
    expires_at, signature = signing.sign(
        SIGN_KIND,
        str(intro_id),
        ttl_seconds=cfg.MEDIA_URL_TTL_SECONDS + _BUCKET_SECONDS,
        now=bucket_start,
    )
    return (
        f"{cfg.PUBLIC_API_URL}{cfg.API_PREFIX}/media/intros/{intro_id}"
        f"?exp={expires_at}&sig={signature}"
    )


__all__ = ["SIGN_KIND", "intro_url"]
