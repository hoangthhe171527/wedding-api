"""Cầu nối: URL ảnh đã ký của một xưởng — cho web thiệp công khai (`invitation`)."""

from __future__ import annotations

from uuid import UUID

from app.modules.media.application.support import photo_url
from app.modules.media.domain.fragment import photo_fragment
from app.modules.media.infrastructure.persistence.repositories import BeaniePhotoRepository


class PublicPhotoLister:
    """Danh sách URL theo thứ tự album — phần tử đầu là ảnh bìa."""

    def __init__(self) -> None:
        self._photos = BeaniePhotoRepository()

    async def album(self, tenant_id: UUID) -> dict[str, list[str]]:
        """`full` và `small` cùng thứ tự — web thiệp ghép thành `srcset`.

        Điểm căn và chỉnh ảnh đi trong fragment (`domain/fragment.py`).
        """
        items = await self._photos.list(tenant_id)
        return {
            "full": [f"{photo_url(item.id)}#{photo_fragment(item)}" for item in items],
            "small": [f"{photo_url(item.id, small=True)}#{photo_fragment(item)}" for item in items],
        }


def build_public_photo_lister() -> PublicPhotoLister:
    """Hàm dựng công bố trên barrel `app.modules.media`."""
    return PublicPhotoLister()


__all__ = ["PublicPhotoLister", "build_public_photo_lister"]
