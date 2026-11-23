"""Cầu nối: URL ảnh đã ký của một xưởng — cho web thiệp công khai (`invitation`)."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from app.core import cache
from app.core.config import get_settings
from app.core.storage import ObjectStore, get_object_store
from app.modules.media.application.support import photo_url
from app.modules.media.domain.fragment import photo_fragment
from app.modules.media.infrastructure.persistence.repositories import (
    PUBLIC_ALBUM_CACHE,
    BeaniePhotoRepository,
)

PUBLIC_ALBUM_TTL_SECONDS = 300


class PublicPhotoLister:
    """Danh sách URL theo thứ tự album — phần tử đầu là ảnh bìa."""

    def __init__(
        self,
        photos: BeaniePhotoRepository | None = None,
        store: ObjectStore | None = None,
    ) -> None:
        self._photos = photos or BeaniePhotoRepository()
        self._store = store or get_object_store()

    async def album(self, tenant_id: UUID) -> dict[str, list[str]]:
        """`full` và `small` cùng thứ tự — web thiệp ghép thành `srcset`.

        Điểm căn và chỉnh ảnh đi trong fragment (`domain/fragment.py`).
        Khi có `S3_PUBLIC_URL`, trả thẳng presigned CDN URL đã neo theo giờ để
        trình duyệt tải trực tiếp không qua bước 302 từ API; khi không có (local/test),
        trả URL API có `&w=sm`.
        """
        cached = await cache.get_json(PUBLIC_ALBUM_CACHE, str(tenant_id))
        entries: list[dict[str, str]]
        if isinstance(cached, list) and all(isinstance(row, dict) for row in cached):
            entries = [
                {
                    "id": str(row.get("id", "")),
                    "storage_key": str(row.get("storage_key", "")),
                    "small_key": str(row.get("small_key", "")),
                    "fragment": str(row.get("fragment", "")),
                }
                for row in cached
            ]
        else:
            items = await self._photos.list(tenant_id)
            entries = [
                {
                    "id": str(item.id),
                    "storage_key": item.storage_key,
                    "small_key": item.small_key,
                    "fragment": photo_fragment(item),
                }
                for item in items
            ]
            await cache.set_json(
                entries, PUBLIC_ALBUM_TTL_SECONDS, PUBLIC_ALBUM_CACHE, str(tenant_id)
            )

        full_urls: list[str] = []
        small_urls: list[str] = []
        ttl = timedelta(seconds=get_settings().MEDIA_URL_TTL_SECONDS)
        direct_enabled = self._store.has_public_url
        for entry in entries:
            fragment = entry["fragment"]
            storage_key = entry["storage_key"]
            if direct_enabled and storage_key:
                small_key = entry["small_key"] or storage_key
                full_base = self._store.direct_url(storage_key, ttl)
                small_base = self._store.direct_url(small_key, ttl)
                if full_base and small_base:
                    full_urls.append(f"{full_base}#{fragment}")
                    small_urls.append(f"{small_base}#{fragment}")
                    continue
            photo_id = UUID(entry["id"])
            full_urls.append(f"{photo_url(photo_id)}#{fragment}")
            small_urls.append(f"{photo_url(photo_id, small=True)}#{fragment}")
        return {"full": full_urls, "small": small_urls}


def build_public_photo_lister() -> PublicPhotoLister:
    """Hàm dựng công bố trên barrel `app.modules.media`."""
    return PublicPhotoLister()


__all__ = ["PUBLIC_ALBUM_TTL_SECONDS", "PublicPhotoLister", "build_public_photo_lister"]
