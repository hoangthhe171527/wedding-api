"""Hiện thực Beanie của `OrderRepository` và `PaymentEventRepository`."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.base_model import utc_now
from app.core.pages import Page, PageParams
from app.modules.billing.domain.entities import ApplePurchase, Order, PaymentEvent
from app.modules.billing.domain.enums import (
    OrderStatus,
    PaymentEventStatus,
    PaymentMethod,
    Plan,
)
from app.modules.billing.domain.repositories import (
    DuplicatePaymentEventError,
    OrderCodeTakenError,
)
from app.modules.billing.infrastructure.persistence.models import (
    ApplePurchaseDocument,
    OrderDocument,
    PaymentEventDocument,
)


def _order(doc: OrderDocument) -> Order:
    return Order(
        id=doc.id,
        tenant_id=doc.tenant_id,
        code=doc.code,
        plan=Plan(doc.plan),
        amount=doc.amount,
        method=PaymentMethod(doc.method),
        status=OrderStatus(doc.status),
        expires_at=doc.expires_at,
        created_at=doc.created_at,
        paid_at=doc.paid_at,
        pay_url=doc.pay_url,
        reference=doc.reference,
        note=doc.note,
    )


def _order_raw(raw: dict[str, Any] | None) -> Order | None:
    return _order(OrderDocument.model_validate(raw)) if raw else None


def _event(doc: PaymentEventDocument) -> PaymentEvent:
    return PaymentEvent(
        id=doc.id,
        source=doc.source,
        external_id=doc.external_id,
        amount=doc.amount,
        content=doc.content,
        status=PaymentEventStatus(doc.status),
        received_at=doc.created_at,
        order_code=doc.order_code,
        tenant_id=doc.tenant_id,
    )


def _apple_purchase(doc: ApplePurchaseDocument) -> ApplePurchase:
    return ApplePurchase(
        transaction_id=doc.transaction_id,
        original_transaction_id=doc.original_transaction_id,
        product_id=doc.product_id,
        plan=Plan(doc.plan),
        environment=doc.environment,
        tenant_id=doc.tenant_id,
        purchase_date=doc.purchase_date,
    )


class BeanieOrderRepository:
    """`OrderRepository` trên Mongo."""

    async def create(
        self,
        *,
        tenant_id: UUID,
        code: str,
        plan: Plan,
        amount: int,
        method: PaymentMethod,
        expires_at: datetime,
        actor_id: UUID,
    ) -> Order:
        doc = OrderDocument(
            tenant_id=tenant_id,
            code=code,
            plan=plan.value,
            amount=amount,
            method=method.value,
            status=OrderStatus.PENDING.value,
            expires_at=expires_at,
        )
        doc.stamp_created(actor_id)
        try:
            await doc.insert()
        except DuplicateKeyError as exc:
            raise OrderCodeTakenError from exc
        return _order(doc)

    async def get(self, tenant_id: UUID, order_id: UUID) -> Order | None:
        doc = await OrderDocument.get_scoped(tenant_id, order_id)
        return _order(doc) if doc else None

    async def get_any(self, order_id: UUID) -> Order | None:
        doc = await OrderDocument.find_one({"_id": order_id, "deleted_at": None})
        return _order(doc) if doc else None

    async def find_by_code(self, code: str) -> Order | None:
        doc = await OrderDocument.find_one({"code": code, "deleted_at": None})
        return _order(doc) if doc else None

    async def list_for_tenant(self, tenant_id: UUID) -> list[Order]:
        docs = await OrderDocument.scoped(tenant_id).sort("-created_at").limit(50).to_list()
        return [_order(doc) for doc in docs]

    async def list_page(self, params: PageParams, status: OrderStatus | None) -> Page[Order]:
        # Ngoại lệ có chủ ý với §0.4: màn đối soát của đội vận hành, quyền
        # `studio.oversee` đã được kiểm ở router.
        criteria: dict[str, Any] = {"deleted_at": None}
        if status is not None:
            criteria["status"] = status.value
        total = await OrderDocument.find(criteria).count()
        docs = (
            await OrderDocument.find(criteria)
            .sort("-created_at")
            .skip(params.offset)
            .limit(params.limit)
            .to_list()
        )
        return Page(items=[_order(doc) for doc in docs], total=total, params=params)

    async def paid_plans(self, tenant_id: UUID) -> list[Plan]:
        raw = await OrderDocument.get_motor_collection().distinct(
            "plan",
            {"tenant_id": tenant_id, "status": OrderStatus.PAID.value, "deleted_at": None},
        )
        return [Plan(item) for item in raw]

    async def paid_plans_many(self, tenant_ids: list[UUID]) -> dict[UUID, list[Plan]]:
        # Ngoại lệ có chủ ý với §0.4: màn quản trị (`studio.oversee` kiểm ở router).
        cursor = OrderDocument.get_motor_collection().aggregate(
            [
                {
                    "$match": {
                        "tenant_id": {"$in": tenant_ids},
                        "status": OrderStatus.PAID.value,
                        "deleted_at": None,
                    }
                },
                {"$group": {"_id": "$tenant_id", "plans": {"$addToSet": "$plan"}}},
            ]
        )
        found = {row["_id"]: [Plan(item) for item in row["plans"]] async for row in cursor}
        return {tenant_id: found.get(tenant_id, []) for tenant_id in tenant_ids}

    async def open_order(self, tenant_id: UUID, plan: Plan, method: PaymentMethod) -> Order | None:
        doc = (
            await OrderDocument.scoped(
                tenant_id,
                {
                    "plan": plan.value,
                    "method": method.value,
                    "status": OrderStatus.PENDING.value,
                    "expires_at": {"$gt": utc_now()},
                },
            )
            .sort("-created_at")
            .first_or_none()
        )
        return _order(doc) if doc else None

    async def set_pay_url(self, order_id: UUID, pay_url: str) -> None:
        await OrderDocument.get_motor_collection().update_one(
            {"_id": order_id}, {"$set": {"pay_url": pay_url, "updated_at": utc_now()}}
        )

    async def mark_paid(self, order_id: UUID, *, reference: str, note: str = "") -> Order | None:
        now = utc_now()
        raw = await OrderDocument.get_motor_collection().find_one_and_update(
            # Đơn đã hết hạn vẫn nhận tiền: khách chuyển khoản muộn vẫn là đã trả.
            {
                "_id": order_id,
                "status": {"$in": [OrderStatus.PENDING.value, OrderStatus.EXPIRED.value]},
            },
            {
                "$set": {
                    "status": OrderStatus.PAID.value,
                    "paid_at": now,
                    "reference": reference,
                    "note": note,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return _order_raw(raw)

    async def cancel(self, tenant_id: UUID, order_id: UUID) -> Order | None:
        raw = await OrderDocument.get_motor_collection().find_one_and_update(
            {
                "_id": order_id,
                "tenant_id": tenant_id,
                "deleted_at": None,
                "status": OrderStatus.PENDING.value,
            },
            {"$set": {"status": OrderStatus.CANCELLED.value, "updated_at": utc_now()}},
            return_document=ReturnDocument.AFTER,
        )
        return _order_raw(raw)

    async def expire_due(self, now: datetime, tenant_id: UUID | None = None) -> int:
        criteria: dict[str, Any] = {
            "status": OrderStatus.PENDING.value,
            "expires_at": {"$lte": now},
        }
        if tenant_id is not None:
            criteria["tenant_id"] = tenant_id
        result = await OrderDocument.get_motor_collection().update_many(
            criteria,
            {"$set": {"status": OrderStatus.EXPIRED.value, "updated_at": now}},
        )
        return int(result.modified_count)


class BeaniePaymentEventRepository:
    """`PaymentEventRepository` trên Mongo."""

    async def record(
        self,
        *,
        source: str,
        external_id: str,
        amount: int,
        content: str,
        status: PaymentEventStatus,
        order_code: str,
        tenant_id: UUID | None,
        raw: dict[str, object],
    ) -> PaymentEvent:
        doc = PaymentEventDocument(
            source=source,
            external_id=external_id,
            amount=amount,
            content=content,
            status=status.value,
            order_code=order_code,
            tenant_id=tenant_id,
            raw=dict(raw),
        )
        try:
            await doc.insert()
        except DuplicateKeyError as exc:
            raise DuplicatePaymentEventError from exc
        return _event(doc)

    async def list_recent(self, limit: int) -> list[PaymentEvent]:
        docs = await PaymentEventDocument.find({}).sort("-created_at").limit(limit).to_list()
        return [_event(doc) for doc in docs]


class BeanieApplePurchaseRepository:
    """Sổ transaction Apple đã xác thực trên Mongo."""

    async def get_by_transaction_id(self, transaction_id: str) -> ApplePurchase | None:
        doc = await ApplePurchaseDocument.find_one({"transaction_id": transaction_id})
        return _apple_purchase(doc) if doc else None

    async def create(
        self,
        *,
        transaction_id: str,
        original_transaction_id: str,
        product_id: str,
        plan: Plan,
        environment: str,
        tenant_id: UUID,
        purchase_date: datetime,
    ) -> ApplePurchase:
        doc = ApplePurchaseDocument(
            transaction_id=transaction_id,
            original_transaction_id=original_transaction_id,
            product_id=product_id,
            plan=plan.value,
            environment=environment,
            tenant_id=tenant_id,
            purchase_date=purchase_date,
        )
        try:
            await doc.insert()
        except DuplicateKeyError:
            existing = await self.get_by_transaction_id(transaction_id)
            if existing is None:
                raise
            return existing
        return _apple_purchase(doc)


__all__ = [
    "BeanieApplePurchaseRepository",
    "BeanieOrderRepository",
    "BeaniePaymentEventRepository",
]
