"""Hiện thực Beanie của `PrintRequestRepository`."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pymongo import ReturnDocument

from app.core.base_model import utc_now
from app.core.pages import Page, PageParams
from app.modules.printing.domain.entities import PrintRequest, PrintSpec
from app.modules.printing.domain.enums import PrintStatus
from app.modules.printing.infrastructure.persistence.models import PrintRequestDocument

_OPEN = [PrintStatus.NEW.value, PrintStatus.CONTACTED.value, PrintStatus.PRINTING.value]


def _request(doc: PrintRequestDocument) -> PrintRequest:
    return PrintRequest(
        id=doc.id,
        tenant_id=doc.tenant_id,
        spec=PrintSpec(
            quantity=doc.quantity,
            paper=doc.paper,
            size=doc.size,
            foil=doc.foil,
            envelope=doc.envelope,
            contact_name=doc.contact_name,
            contact_phone=doc.contact_phone,
            address=doc.address,
            note=doc.note,
        ),
        status=PrintStatus(doc.status),
        admin_note=doc.admin_note,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


class BeaniePrintRequestRepository:
    """`PrintRequestRepository` trên Mongo."""

    async def create(self, tenant_id: UUID, spec: PrintSpec, *, actor_id: UUID) -> PrintRequest:
        doc = PrintRequestDocument(
            tenant_id=tenant_id,
            quantity=spec.quantity,
            paper=spec.paper,
            size=spec.size,
            foil=spec.foil,
            envelope=spec.envelope,
            contact_name=spec.contact_name,
            contact_phone=spec.contact_phone,
            address=spec.address,
            note=spec.note,
        )
        doc.stamp_created(actor_id)
        await doc.insert()
        return _request(doc)

    async def list_for_tenant(self, tenant_id: UUID) -> list[PrintRequest]:
        docs = await PrintRequestDocument.scoped(tenant_id).sort("-created_at").limit(20).to_list()
        return [_request(doc) for doc in docs]

    async def get(self, tenant_id: UUID, request_id: UUID) -> PrintRequest | None:
        doc = await PrintRequestDocument.get_scoped(tenant_id, request_id)
        return _request(doc) if doc else None

    async def get_any(self, request_id: UUID) -> PrintRequest | None:
        doc = await PrintRequestDocument.find_one({"_id": request_id, "deleted_at": None})
        return _request(doc) if doc else None

    async def list_page(self, params: PageParams, status: PrintStatus | None) -> Page[PrintRequest]:
        # Ngoại lệ có chủ ý với §0.4: màn vận hành, quyền `studio.oversee` kiểm ở router.
        criteria: dict[str, Any] = {"deleted_at": None}
        if status is not None:
            criteria["status"] = status.value
        total = await PrintRequestDocument.find(criteria).count()
        docs = (
            await PrintRequestDocument.find(criteria)
            .sort("-created_at")
            .skip(params.offset)
            .limit(params.limit)
            .to_list()
        )
        return Page(items=[_request(doc) for doc in docs], total=total, params=params)

    async def set_status(
        self,
        request_id: UUID,
        status: PrintStatus,
        admin_note: str | None,
        *,
        actor_id: UUID,
        tenant_id: UUID | None = None,
        only_from: frozenset[PrintStatus] | None = None,
    ) -> PrintRequest | None:
        """Đổi trạng thái NGUYÊN TỬ; chỉ cập nhật trường được đổi (không ghi đè cả bản ghi).

        `only_from`: chỉ đổi khi trạng thái hiện tại nằm trong tập này — khách huỷ cùng
        lúc đội vận hành chuyển sang "Đang in" thì một bên thắng, không bên nào ghi đè.
        """
        criteria: dict[str, Any] = {"_id": request_id, "deleted_at": None}
        if tenant_id is not None:
            criteria["tenant_id"] = tenant_id
        if only_from is not None:
            criteria["status"] = {"$in": [item.value for item in only_from]}
        changes: dict[str, Any] = {
            "status": status.value,
            "updated_at": utc_now(),
            "updated_by": actor_id,
        }
        if admin_note is not None:
            changes["admin_note"] = admin_note
        raw = await PrintRequestDocument.get_motor_collection().find_one_and_update(
            criteria, {"$set": changes}, return_document=ReturnDocument.AFTER
        )
        return _request(PrintRequestDocument.model_validate(raw)) if raw else None

    async def count_open(self, tenant_id: UUID) -> int:
        return int(
            await PrintRequestDocument.find(
                {"tenant_id": tenant_id, "deleted_at": None, "status": {"$in": _OPEN}}
            ).count()
        )
