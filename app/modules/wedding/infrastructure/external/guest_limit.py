"""Cầu nối cho `guest`: hạn mức khách và kiểm tra gói của mẫu link khi thiệp đang xuất bản.

Gói chỉ xét lúc XUẤT BẢN (§1.10): soạn nháp thêm khách hoặc tạo link thoải mái.
Nhưng khi web thiệp đang mở, khách mới hoặc link mới có hiệu lực ngay — nên
thêm vượt hạn mức hoặc gán mẫu vượt gói phải bị chặn.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.errors import ConflictError
from app.modules.billing import build_entitlement_reader, build_plan_gate
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


class PublishedLinkGate:
    def __init__(self) -> None:
        self._weddings = BeanieWeddingRepository()
        self._gate = build_plan_gate()

    async def ensure_template(self, tenant_id: UUID, template_key: str) -> None:
        """Raises: ConflictError(`plan_required`) nếu thiệp đang xuất bản mà mẫu link vượt gói."""
        if not template_key:
            return
        wedding = await self._weddings.find_by_tenant(tenant_id)
        if wedding is None or not wedding.published:
            return
        result = await self._gate.check(tenant_id, {"templates": (template_key,)})
        found = result.get("violations") or []
        if found:
            raise ConflictError(
                f"Thiệp đang dùng tính năng của {result.get('required_label')}. "
                "Nâng gói hoặc đổi sang lựa chọn trong gói.",
                code="plan_required",
                errors={"plan": [str(item.get("message")) for item in found]},
            )


def build_published_guest_limit() -> PublishedGuestLimit:
    return PublishedGuestLimit()


def build_published_link_gate() -> PublishedLinkGate:
    return PublishedLinkGate()


__all__ = [
    "PublishedGuestLimit",
    "PublishedLinkGate",
    "build_published_guest_limit",
    "build_published_link_gate",
]
