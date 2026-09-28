"""Use case: đọc ảnh qua URL đã ký (công khai, không cần đăng nhập).

Chữ ký sai hay hết hạn đều trả **404**, không phải 403: không xác nhận cho người
dò rằng id ảnh đó có tồn tại.

Kho object có địa chỉ công khai (`S3_PUBLIC_URL`) thì trả URL để chuyển hướng
— trình duyệt tải thẳng từ kho / CDN, API không gánh byte ảnh. Không có thì
API đọc hộ và trả byte.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from app.core.errors import NotFoundError
from app.core.security import signing
from app.modules.media.application.support import SIGN_KIND
from app.modules.media.domain.repositories import PhotoRepository

#: URL ký của kho sống tối thiểu chừng này, kể cả khi URL của API sắp hết hạn —
#: đủ để trình duyệt tải xong ảnh sau khi được chuyển hướng.
_MIN_DIRECT_SECONDS = 300


@dataclass(frozen=True, slots=True)
class PhotoContent:
    data: bytes = b""
    content_type: str = ""
    redirect: str | None = None


def _not_found() -> NotFoundError:
    return NotFoundError("Không tìm thấy ảnh.", code="photo_not_found")


class ReadPhoto:
    def __init__(self, photos: PhotoRepository) -> None:
        self._photos = photos

    async def execute(
        self, photo_id: UUID, *, expires_at: int, signature: str, small: bool = False
    ) -> PhotoContent:
        if not signing.verify(SIGN_KIND, str(photo_id), expires_at=expires_at, signature=signature):
            raise _not_found()
        ttl = max(expires_at - int(time.time()), _MIN_DIRECT_SECONDS)
        # S3 giới hạn URL ký tối đa 7 ngày.
        url = await self._photos.direct_url(
            photo_id, timedelta(seconds=min(ttl, 7 * 86400)), small=small
        )
        if url:
            return PhotoContent(redirect=url)
        content = await self._photos.read_content(photo_id, small=small)
        if content is None:
            raise _not_found()
        return PhotoContent(data=content[0], content_type=content[1])


__all__ = ["PhotoContent", "ReadPhoto"]
