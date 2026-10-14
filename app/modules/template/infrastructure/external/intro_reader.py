"""Cầu nối: id video mở thiệp -> URL đã ký — cho web thiệp công khai (`invitation`).

Khớp cấu trúc cổng `IntroVideos` mà `invitation` khai. Trả chuỗi thuần.
"""

from __future__ import annotations

from uuid import UUID

from app.modules.template.application.intro_urls import intro_url
from app.modules.template.infrastructure.persistence.intro_repository import (
    BeanieIntroRepository,
)


class IntroUrlReader:
    """Video còn trong thư viện (kể cả đã tắt) -> URL; id rỗng / lạ / đã xoá -> ""."""

    def __init__(self) -> None:
        self._intros = BeanieIntroRepository()

    async def url_of(self, intro_id: str) -> str:
        try:
            parsed = UUID(intro_id)
        except ValueError:
            return ""
        intro = await self._intros.get(parsed)
        return intro_url(intro.id) if intro else ""


def build_intro_url_reader() -> IntroUrlReader:
    """Hàm dựng công bố trên barrel `app.modules.template`."""
    return IntroUrlReader()


__all__ = ["IntroUrlReader", "build_intro_url_reader"]
