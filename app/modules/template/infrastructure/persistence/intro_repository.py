"""Hiện thực của `IntroRepository`: siêu dữ liệu ở Mongo, byte video ở kho object."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from app.core.base_model import new_id, utc_now
from app.core.logging import get_logger
from app.core.storage import ObjectStore, get_object_store
from app.modules.template.domain.entities import Intro
from app.modules.template.domain.intros import EXTENSIONS
from app.modules.template.infrastructure.persistence.models import IntroDocument

log = get_logger(__name__)


def intro_key(intro_id: UUID, content_type: str) -> str:
    """Khoá object: `intros/<id>.<đuôi>` — đuôi giúp kho / CDN đoán đúng kiểu."""
    return f"intros/{intro_id}.{EXTENSIONS.get(content_type, 'bin')}"


def _intro(doc: IntroDocument) -> Intro:
    return Intro(
        id=doc.id,
        name=doc.name,
        key=doc.key,
        content_type=doc.content_type,
        size=doc.size,
        order=doc.order,
        is_active=doc.is_active,
        created_at=doc.created_at,
    )


class BeanieIntroRepository:
    """`IntroRepository` trên Mongo + kho object S3."""

    def __init__(self, store: ObjectStore | None = None) -> None:
        self._store = store or get_object_store()

    async def list_all(self, *, include_inactive: bool) -> list[Intro]:
        criteria: dict[str, Any] = {} if include_inactive else {"is_active": True}
        docs = await IntroDocument.find(criteria).sort("+order", "+created_at").to_list()
        return [_intro(doc) for doc in docs]

    async def get(self, intro_id: UUID) -> Intro | None:
        doc = await IntroDocument.find_one({"_id": intro_id})
        return _intro(doc) if doc else None

    async def next_order(self) -> int:
        last = await IntroDocument.find({}).sort("-order").limit(1).to_list()
        return last[0].order + 1 if last else 0

    async def create(
        self, *, name: str, data: bytes, content_type: str, order: int, actor_id: UUID
    ) -> Intro:
        intro_id = new_id()
        doc = IntroDocument(
            id=intro_id,
            name=name,
            key=intro_key(intro_id, content_type),
            content_type=content_type,
            size=len(data),
            order=order,
            created_by=actor_id,
        )
        # Byte trước, siêu dữ liệu sau: thư viện không bao giờ trỏ vào video chưa có.
        await self._store.put(doc.key, data, content_type)
        try:
            await doc.insert()
        except Exception:
            await self._store.delete(doc.key)
            raise
        return _intro(doc)

    async def update(
        self,
        intro_id: UUID,
        *,
        name: str | None = None,
        is_active: bool | None = None,
        order: int | None = None,
    ) -> Intro | None:
        changes: dict[str, Any] = {
            field: value
            for field, value in (("name", name), ("is_active", is_active), ("order", order))
            if value is not None
        }
        if changes:
            changes["updated_at"] = utc_now()
            await IntroDocument.get_motor_collection().update_one(
                {"_id": intro_id}, {"$set": changes}
            )
        return await self.get(intro_id)

    async def delete(self, intro_id: UUID) -> bool:
        doc = await IntroDocument.find_one({"_id": intro_id})
        if doc is None:
            return False
        await IntroDocument.get_motor_collection().delete_one({"_id": intro_id})
        # Siêu dữ liệu đã xoá thì video không còn phát ở đâu; object còn sót (kho
        # lỗi tạm thời) chỉ tốn chỗ — ghi log để dọn sau.
        try:
            await self._store.delete(doc.key)
        except Exception:
            log.warning("intro_object_orphaned", intro_id=str(intro_id), key=doc.key)
        return True

    async def read_range(self, intro: Intro, start: int, end: int) -> bytes | None:
        return await self._store.get_range(intro.key, start, end - start + 1)

    def direct_url(self, intro: Intro, expires: timedelta) -> str | None:
        return self._store.direct_url(intro.key, expires)


__all__ = ["BeanieIntroRepository", "intro_key"]
