"""Cầu nối cho `guest`: thiệp đang xuất bản thì gói cho tối đa bao nhiêu khách.

Gói chỉ xét lúc XUẤT BẢN (§1.10): soạn nháp thêm khách thoải mái. Nhưng khi web
thiệp đang mở, khách mới nhận link ngay — nên thêm vượt hạn mức phải bị chặn.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.billing import build_entitlement_reader
from app.modules.wedding.infrastructure.persistence.repositories import BeanieWeddingRepository


class PublishedGuestLimit:
    def __init__(self) -> None:
        self._weddings = BeanieWeddingRepository()
        self._entitlements = build_entitlement_reader()

    async def limit_for(self, tenant_id: UUID) -> dict[str, Any] | None:
        """`{"limit", "label"}` nếu thiệp đang xuất bản; None nếu chưa (không giới hạn theo gói)."""
        wedding = await self._weddings.find_by_tenant(tenant_id)
        if wedding is None or not wedding.published:
            return None
        plan = await self._entitlements.plan_for(tenant_id)
        return {"limit": int(plan["guest_limit"]), "label": str(plan.get("label", ""))}


def build_published_guest_limit() -> PublishedGuestLimit:
    return PublishedGuestLimit()


__all__ = ["PublishedGuestLimit", "build_published_guest_limit"]
