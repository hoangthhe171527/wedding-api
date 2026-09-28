"""Hiện thực Beanie của `GuestRepository`."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from pymongo import ReturnDocument
from pymongo.errors import BulkWriteError, DuplicateKeyError

from app.core.base_model import utc_now
from app.core.pages import Page, PageParams
from app.modules.guest.domain.entities import Guest, GuestDraft, GuestOpens, GuestReply, Wish
from app.modules.guest.domain.enums import RsvpStatus, Side
from app.modules.guest.domain.repositories import GuestCodeTakenError
from app.modules.guest.infrastructure.persistence.models import GuestDocument, WishDocument

#: Mã lỗi khoá trùng của MongoDB (index duy nhất `(tenant, code)`).
_DUPLICATE_KEY = 11000


def _draft_fields(draft: GuestDraft) -> dict[str, Any]:
    return {
        "name": draft.name.strip(),
        "title": draft.title.strip(),
        "plus": draft.plus.strip(),
        "group": draft.group,
        "side": draft.side.value,
        "events": list(draft.events),
        "party_size": draft.count,
        "template": draft.template,
        "status": draft.status.value,
        "sent": draft.sent,
        "note": draft.note.strip(),
    }


def _guest(doc: GuestDocument) -> Guest:
    return Guest(
        id=doc.id,
        tenant_id=doc.tenant_id,
        code=doc.code,
        draft=GuestDraft(
            name=doc.name,
            title=doc.title,
            plus=doc.plus,
            group=doc.group,
            side=Side(doc.side),
            events=tuple(doc.events),
            count=doc.party_size,
            template=doc.template,
            status=RsvpStatus(doc.status),
            sent=doc.sent,
            note=doc.note,
        ),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        reply=(
            GuestReply(count=doc.reply_count, message=doc.reply_message, replied_at=doc.replied_at)
            if doc.replied_at
            else None
        ),
        opens=(
            GuestOpens(
                count=doc.open_count,
                first_at=doc.first_opened_at,
                last_at=doc.last_opened_at or doc.first_opened_at,
            )
            if doc.first_opened_at
            else None
        ),
    )


def _wish(doc: WishDocument) -> Wish:
    return Wish(
        id=doc.id,
        tenant_id=doc.tenant_id,
        name=doc.name,
        message=doc.message,
        status=RsvpStatus(doc.status),
        count=doc.party_size,
        guest_code=doc.guest_code,
        created_at=doc.created_at,
    )


class BeanieGuestRepository:
    """`GuestRepository` trên Mongo."""

    async def list_page(self, tenant_id: UUID, params: PageParams) -> Page[Guest]:
        finder = GuestDocument.scoped(tenant_id)
        total = await finder.count()
        docs = await (
            GuestDocument.scoped(tenant_id)
            .sort("+created_at")
            .skip(params.offset)
            .limit(params.limit)
            .to_list()
        )
        return Page(items=[_guest(doc) for doc in docs], total=total, params=params)

    async def get(self, tenant_id: UUID, guest_id: UUID) -> Guest | None:
        doc = await GuestDocument.get_scoped(tenant_id, guest_id)
        return _guest(doc) if doc else None

    async def find_by_code(self, tenant_id: UUID, code: str) -> Guest | None:
        doc = await GuestDocument.scoped(tenant_id, GuestDocument.code == code).first_or_none()
        return _guest(doc) if doc else None

    async def count(self, tenant_id: UUID) -> int:
        return int(await GuestDocument.scoped(tenant_id).count())

    async def count_by_tenant(self, tenant_ids: Sequence[UUID]) -> dict[UUID, int]:
        if not tenant_ids:
            return {}
        pipeline: list[dict[str, Any]] = [
            {"$match": {"tenant_id": {"$in": list(tenant_ids)}, "deleted_at": None}},
            {"$group": {"_id": "$tenant_id", "n": {"$sum": 1}}},
        ]
        rows = await GuestDocument.get_motor_collection().aggregate(pipeline).to_list(None)
        return {row["_id"]: int(row["n"]) for row in rows}

    async def usage(self, tenant_id: UUID) -> tuple[int, frozenset[str], frozenset[str]]:
        collection = GuestDocument.get_motor_collection()
        live = {"tenant_id": tenant_id, "deleted_at": None}
        count = int(await collection.count_documents(live))
        templates = await collection.distinct("template", {**live, "template": {"$ne": ""}})
        groups = await collection.distinct("group", live)
        return count, frozenset(map(str, templates)), frozenset(map(str, groups))

    async def create(
        self, tenant_id: UUID, code: str, draft: GuestDraft, *, actor_id: UUID | None
    ) -> Guest:
        doc = GuestDocument(tenant_id=tenant_id, code=code, **_draft_fields(draft))
        doc.stamp_created(actor_id)
        try:
            await doc.insert()
        except DuplicateKeyError as exc:
            raise GuestCodeTakenError from exc
        return _guest(doc)

    async def create_many(
        self,
        tenant_id: UUID,
        items: Sequence[tuple[str, GuestDraft]],
        *,
        actor_id: UUID | None,
    ) -> tuple[list[Guest], list[int]]:
        docs = []
        for code, draft in items:
            doc = GuestDocument(tenant_id=tenant_id, code=code, **_draft_fields(draft))
            doc.stamp_created(actor_id)
            docs.append(doc)
        if not docs:
            return [], []
        failed: set[int] = set()
        try:
            await GuestDocument.get_motor_collection().insert_many(
                [doc.model_dump(by_alias=True) for doc in docs], ordered=False
            )
        except BulkWriteError as exc:
            for error in exc.details.get("writeErrors", []):
                if error.get("code") != _DUPLICATE_KEY:
                    raise
                failed.add(int(error["index"]))
        created = [_guest(doc) for index, doc in enumerate(docs) if index not in failed]
        return created, sorted(failed)

    async def discard(self, tenant_id: UUID, guest_ids: Sequence[UUID]) -> None:
        # Xoá HẲN: chỉ dùng để gỡ khách vừa tạo khi phát hiện vượt hạn mức (hoàn tác).
        await GuestDocument.get_motor_collection().delete_many(
            {"tenant_id": tenant_id, "_id": {"$in": list(guest_ids)}}
        )

    async def replace(
        self, tenant_id: UUID, guest_id: UUID, draft: GuestDraft, *, actor_id: UUID
    ) -> Guest | None:
        raw = await GuestDocument.get_motor_collection().find_one_and_update(
            {"_id": guest_id, "tenant_id": tenant_id, "deleted_at": None},
            {"$set": {**_draft_fields(draft), "updated_at": utc_now(), "updated_by": actor_id}},
            return_document=ReturnDocument.AFTER,
        )
        return _guest(GuestDocument.model_validate(raw)) if raw else None

    async def soft_delete(self, tenant_id: UUID, guest_id: UUID, *, actor_id: UUID) -> bool:
        now = utc_now()
        result = await GuestDocument.get_motor_collection().update_one(
            {"_id": guest_id, "tenant_id": tenant_id, "deleted_at": None},
            {"$set": {"deleted_at": now, "deleted_by": actor_id, "updated_at": now}},
        )
        return bool(result.modified_count)

    async def record_reply(
        self, tenant_id: UUID, code: str, *, status: RsvpStatus, count: int, message: str
    ) -> Guest | None:
        now = utc_now()
        raw = await GuestDocument.get_motor_collection().find_one_and_update(
            {"tenant_id": tenant_id, "code": code, "deleted_at": None},
            {
                "$set": {
                    "status": status.value,
                    "reply_count": count,
                    "reply_message": message,
                    "replied_at": now,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return _guest(GuestDocument.model_validate(raw)) if raw else None

    async def record_open(self, tenant_id: UUID, code: str) -> bool:
        now = utc_now()
        # Pipeline update: một lệnh nguyên tử, giữ `first_opened_at` đã có.
        result = await GuestDocument.get_motor_collection().update_one(
            {"tenant_id": tenant_id, "code": code, "deleted_at": None},
            [
                {
                    "$set": {
                        "open_count": {"$add": [{"$ifNull": ["$open_count", 0]}, 1]},
                        "first_opened_at": {"$ifNull": ["$first_opened_at", now]},
                        "last_opened_at": now,
                    }
                }
            ],
        )
        return bool(result.modified_count)


class BeanieWishRepository:
    """`WishRepository` trên Mongo."""

    async def add(
        self,
        tenant_id: UUID,
        *,
        name: str,
        message: str,
        status: RsvpStatus,
        count: int,
        guest_code: str,
    ) -> Wish:
        doc = WishDocument(
            tenant_id=tenant_id,
            name=name,
            message=message,
            status=status.value,
            party_size=count,
            guest_code=guest_code,
        )
        await doc.insert()
        return _wish(doc)

    async def list_recent(self, tenant_id: UUID, *, limit: int, with_message: bool) -> list[Wish]:
        criteria: dict[str, Any] = {"message": {"$ne": ""}} if with_message else {}
        docs = (
            await WishDocument.scoped(tenant_id, criteria)
            .sort("-created_at")
            .limit(limit)
            .to_list()
        )
        return [_wish(doc) for doc in docs]

    async def soft_delete(self, tenant_id: UUID, wish_id: UUID, *, actor_id: UUID) -> bool:
        now = utc_now()
        result = await WishDocument.get_motor_collection().update_one(
            {"_id": wish_id, "tenant_id": tenant_id, "deleted_at": None},
            {"$set": {"deleted_at": now, "deleted_by": actor_id, "updated_at": now}},
        )
        return bool(result.modified_count)


__all__ = ["BeanieGuestRepository", "BeanieWishRepository"]
