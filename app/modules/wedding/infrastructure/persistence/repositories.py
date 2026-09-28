"""Hiện thực Beanie của `WeddingRepository`."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import UUID

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core import cache
from app.core.base_model import utc_now
from app.modules.wedding.domain.design import CardDesign, DesignLayer
from app.modules.wedding.domain.entities import (
    BankAccount,
    DressCode,
    Event,
    Gift,
    Parents,
    Person,
    Rsvp,
    ScheduleItem,
    Theme,
    Wedding,
    WeddingContent,
)
from app.modules.wedding.domain.enums import EventKind, OpenStyle, Side
from app.modules.wedding.domain.repositories import SlugTakenError, WeddingAlreadyExistsError
from app.modules.wedding.infrastructure.persistence.models import WeddingDocument


def _content_of(doc: WeddingDocument) -> WeddingContent:
    return WeddingContent(
        groom=Person(**doc.groom.model_dump()),
        bride=Person(**doc.bride.model_dump()),
        groom_parents=Parents(**doc.groom_parents.model_dump()),
        bride_parents=Parents(**doc.bride_parents.model_dump()),
        events=tuple(
            Event(
                id=item.id,
                name=item.name,
                kind=EventKind(item.kind),
                side=Side(item.side),
                date=item.date,
                time=item.time,
                venue=item.venue,
                address=item.address,
                map_url=item.map_url,
                arrival=item.arrival,
            )
            for item in doc.events
        ),
        story=doc.story,
        quote=doc.quote,
        rsvp=Rsvp(**doc.rsvp.model_dump()),
        gift=Gift(
            show=doc.gift.show,
            groom=BankAccount(**doc.gift.groom.model_dump()),
            bride=BankAccount(**doc.gift.bride.model_dump()),
        ),
        music_url=doc.music_url,
        default_template=doc.default_template,
        group_templates=dict(doc.group_templates),
        wording={tone: dict(fields) for tone, fields in doc.wording.items()},
        messages=dict(doc.messages),
        open_style=OpenStyle(doc.open_style),
        theme=Theme(
            **{
                **doc.theme.model_dump(),
                "sections": tuple(doc.theme.sections),
                "hidden": tuple(doc.theme.hidden),
            }
        ),
        card_design=CardDesign(
            enabled=doc.card_design.enabled,
            base=doc.card_design.base,
            layers=tuple(DesignLayer(**item.model_dump()) for item in doc.card_design.layers),
        ),
        schedule=tuple(ScheduleItem(time=item.time, label=item.label) for item in doc.schedule),
        dress_code=DressCode(note=doc.dress_code.note, colors=tuple(doc.dress_code.colors)),
    )


def _wedding(doc: WeddingDocument) -> Wedding:
    return Wedding(
        id=doc.id,
        tenant_id=doc.tenant_id,
        content=_content_of(doc),
        slug=doc.slug,
        published=doc.published,
        checklist=dict(doc.checklist),
        updated_at=doc.updated_at,
    )


#: Khoá cache bản công khai của đám cưới theo slug (web thiệp), xem published_reader.
PUBLISHED_CACHE = "published_wedding"
#: Màn giám sát xưởng chỉ hiện chừng này xưởng mới cập nhật nhất.
LIST_ALL_LIMIT = 1000


def _content_fields(content: WeddingContent) -> dict[str, Any]:
    """Nội dung -> dict thuần đúng hình document; dùng chung cho insert và `$set`.

    Enum đổi về `.value` tường minh: lưu thẳng thành viên enum thì đọc lại vẫn
    đúng, nhưng so sánh trong truy vấn thô (`{"kind": "tiec"}`) dễ lệch kiểu.
    """
    fields = asdict(content)
    fields["events"] = [
        {**event, "kind": EventKind(event["kind"]).value, "side": Side(event["side"]).value}
        for event in fields["events"]
    ]
    fields["open_style"] = OpenStyle(fields["open_style"]).value
    return fields


def _is_slug_conflict(exc: DuplicateKeyError) -> bool:
    return "uq_weddings_slug" in str(exc)


class BeanieWeddingRepository:
    """`WeddingRepository` trên Mongo."""

    async def find_by_tenant(self, tenant_id: UUID) -> Wedding | None:
        doc = await WeddingDocument.scoped(tenant_id).first_or_none()
        return _wedding(doc) if doc else None

    async def find_published_by_slug(self, slug: str) -> Wedding | None:
        doc = await WeddingDocument.find_one({"slug": slug, "published": True, "deleted_at": None})
        return _wedding(doc) if doc else None

    async def slug_exists(self, slug: str) -> bool:
        return await WeddingDocument.find_one({"slug": slug}) is not None

    async def create(
        self, *, tenant_id: UUID, content: WeddingContent, slug: str, actor_id: UUID | None
    ) -> Wedding:
        doc = WeddingDocument(tenant_id=tenant_id, slug=slug, **_content_fields(content))
        doc.stamp_created(actor_id)
        try:
            await doc.insert()
        except DuplicateKeyError as exc:
            if _is_slug_conflict(exc):
                raise SlugTakenError from exc
            raise WeddingAlreadyExistsError from exc
        return _wedding(doc)

    async def _update(
        self, tenant_id: UUID, changes: dict[str, Any], actor_id: UUID
    ) -> Wedding | None:
        raw = await WeddingDocument.get_motor_collection().find_one_and_update(
            {"tenant_id": tenant_id, "deleted_at": None},
            {"$set": {**changes, "updated_at": utc_now(), "updated_by": actor_id}},
            return_document=ReturnDocument.AFTER,
        )
        if raw is None:
            return None
        doc = WeddingDocument.model_validate(raw)
        # Bản công khai đã cache (web thiệp) phải thấy ngay nội dung / trạng thái mới.
        await cache.delete(PUBLISHED_CACHE, doc.slug)
        return _wedding(doc)

    async def save_content(
        self, tenant_id: UUID, content: WeddingContent, *, actor_id: UUID
    ) -> Wedding | None:
        return await self._update(tenant_id, _content_fields(content), actor_id)

    async def save_checklist(
        self, tenant_id: UUID, checklist: dict[str, bool], *, actor_id: UUID
    ) -> Wedding | None:
        return await self._update(tenant_id, {"checklist": checklist}, actor_id)

    async def save_publication(
        self, tenant_id: UUID, *, slug: str, published: bool, actor_id: UUID
    ) -> Wedding | None:
        try:
            return await self._update(tenant_id, {"slug": slug, "published": published}, actor_id)
        except DuplicateKeyError as exc:
            raise SlugTakenError from exc

    async def list_all(self) -> list[Wedding]:
        # Ngoại lệ có chủ ý với §0.4: màn giám sát của đội vận hành, quyền
        # `studio.oversee` đã được kiểm ở router.
        # Có trần: tải không giới hạn là kéo hàng trăm MB vào RAM khi có chục nghìn xưởng.
        docs = (
            await WeddingDocument.find({"deleted_at": None})
            .sort("-updated_at")
            .limit(LIST_ALL_LIMIT)
            .to_list()
        )
        return [_wedding(doc) for doc in docs]


__all__ = ["BeanieWeddingRepository"]
