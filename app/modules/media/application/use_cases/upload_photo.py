"""Use case: tải một ảnh cưới lên album."""

from __future__ import annotations

import asyncio
import weakref
from uuid import UUID

from app.core.config import get_settings
from app.core.context import ActorContext
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.modules.media.application.ports import ImageProcessor, UnreadableImageError
from app.modules.media.application.support import photo_url
from app.modules.media.application.use_cases.list_photos import PhotoView
from app.modules.media.domain.repositories import PhotoRepository

log = get_logger(__name__)


#: Ảnh xử lý cùng lúc trong MỘT tiến trình — mỗi ảnh giữ vài chục MB RAM lúc giải mã.
_PROCESS_SLOTS = 2
_slots: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = (
    weakref.WeakKeyDictionary()
)


def _process_slot() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    slots = _slots.get(loop)
    if slots is None:
        slots = _slots[loop] = asyncio.Semaphore(_PROCESS_SLOTS)
    return slots


class UploadPhoto:
    """Chuẩn hoá ảnh rồi thêm mới hoặc thay đúng một vị trí trong album."""

    def __init__(self, photos: PhotoRepository, processor: ImageProcessor) -> None:
        self._photos = photos
        self._processor = processor

    async def execute(
        self,
        actor: ActorContext,
        data: bytes,
        *,
        filename: str,
        replacing: UUID | None = None,
    ) -> PhotoView:
        """Thêm ảnh, hoặc thay ``replacing`` mà giữ nguyên thứ tự của ảnh cũ.

        Raises: ValidationError (tệp lớn/không phải ảnh), ConflictError (album đầy),
        NotFoundError (ảnh cần thay không thuộc xưởng).
        """
        cfg = get_settings()
        if len(data) > cfg.PHOTO_MAX_BYTES:
            limit_mb = cfg.PHOTO_MAX_BYTES / 1_000_000
            raise ValidationError(
                f"Ảnh “{filename}” quá lớn (tối đa {limit_mb:.1f} MB).", code="photo_too_large"
            )
        existing = await self._photos.list(actor.tenant_id)
        replaced = next((item for item in existing if item.id == replacing), None)
        if replacing is not None and replaced is None:
            raise NotFoundError("Không tìm thấy ảnh.", code="photo_not_found")
        if replaced is None and len(existing) >= cfg.PHOTO_MAX_COUNT:
            raise ConflictError(
                f"Album đã đủ {cfg.PHOTO_MAX_COUNT} ảnh. Xoá bớt ảnh rồi thử lại.",
                code="photo_limit",
            )
        try:
            # Giải mã + thu nhỏ + mã hoá lại tốn 100-500ms CPU: chạy trong thread (tối đa
            # _PROCESS_SLOTS ảnh cùng lúc) để không làm đứng mọi request khác.
            async with _process_slot():
                image = await asyncio.to_thread(self._processor.process, data)
        except UnreadableImageError:
            raise ValidationError(
                f"Không đọc được ảnh “{filename}”. Hãy dùng ảnh JPG hoặc PNG.",
                code="photo_unreadable",
            ) from None

        order = replaced.order if replaced is not None else existing[-1].order + 1 if existing else 0
        photo = await self._photos.create(
            actor.tenant_id, image, order=order, actor_id=actor.user_id
        )
        if replaced is not None:
            # Tạo ảnh mới trước để lỗi xử lý/kho ảnh không làm mất ảnh cũ. ID mới
            # cũng tránh URL ký/cached của ảnh cũ tiếp tục hiện sau khi thay.
            if not await self._photos.delete(actor.tenant_id, replaced.id):
                await self._photos.delete(actor.tenant_id, photo.id)
                raise NotFoundError("Không tìm thấy ảnh.", code="photo_not_found")
            log.info(
                "photo_replaced",
                tenant_id=str(actor.tenant_id),
                old_photo_id=str(replaced.id),
                photo_id=str(photo.id),
                size=photo.size,
            )
            return PhotoView(photo=photo, url=photo_url(photo.id))
        # Kiểm LẠI sau khi ghi: hai lượt tải song song có thể cùng qua bước kiểm ở trên.
        if await self._photos.count(actor.tenant_id) > cfg.PHOTO_MAX_COUNT:
            await self._photos.delete(actor.tenant_id, photo.id)
            raise ConflictError(
                f"Album đã đủ {cfg.PHOTO_MAX_COUNT} ảnh. Xoá bớt ảnh rồi thử lại.",
                code="photo_limit",
            )
        log.info("photo_uploaded", tenant_id=str(actor.tenant_id), size=photo.size)
        return PhotoView(photo=photo, url=photo_url(photo.id))


__all__ = ["UploadPhoto"]
