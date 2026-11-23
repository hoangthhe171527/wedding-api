"""Cầu nối: id video mở thiệp -> URL đã ký — cho web thiệp công khai (`invitation`).

Khớp cấu trúc cổng `IntroVideos` mà `invitation` khai. Trả chuỗi thuần.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from app.core import cache
from app.core.config import get_settings
from app.core.storage import ObjectStore, get_object_store
from app.modules.template.application.intro_urls import intro_url
from app.modules.template.infrastructure.persistence.intro_repository import (
    INTRO_META_CACHE,
    BeanieIntroRepository,
)

INTRO_META_TTL_SECONDS = 300


class IntroUrlReader:
    """Video còn trong thư viện (kể cả đã tắt) -> URL; id rỗng / lạ / đã xoá -> ""."""

    def __init__(
        self,
        intros: BeanieIntroRepository | None = None,
        store: ObjectStore | None = None,
    ) -> None:
        self._intros = intros or BeanieIntroRepository()
        self._store = store or get_object_store()

    async def url_of(self, intro_id: str) -> str:
        try:
            parsed = UUID(intro_id)
        except ValueError:
            return ""
        cached = await cache.get_json(INTRO_META_CACHE, str(parsed))
        if not isinstance(cached, dict) or "exists" not in cached:
            intro = await self._intros.get(parsed)
            cached = {"exists": True, "key": intro.key} if intro else {"exists": False}
            await cache.set_json(cached, INTRO_META_TTL_SECONDS, INTRO_META_CACHE, str(parsed))
        if not cached.get("exists"):
            return ""
        object_key = str(cached.get("key") or "")
        if self._store.has_public_url and object_key:
            ttl = timedelta(seconds=get_settings().MEDIA_URL_TTL_SECONDS)
            direct = self._store.direct_url(object_key, ttl)
            if direct:
                return direct
        return intro_url(parsed)


def build_intro_url_reader() -> IntroUrlReader:
    """Hàm dựng công bố trên barrel `app.modules.template`."""
    return IntroUrlReader()


__all__ = ["INTRO_META_TTL_SECONDS", "IntroUrlReader", "build_intro_url_reader"]
