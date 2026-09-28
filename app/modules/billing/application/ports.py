"""Cổng của `billing` sang module khác và ra ngoài hệ thống."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.billing.domain.entities import Order


class PlanWaiver(Protocol):
    """Xưởng được dùng mọi tính năng như gói cao nhất mà không mua (tài khoản quản trị)."""

    async def waived(self, tenant_id: UUID) -> bool: ...


class TemplateCatalog(Protocol):
    """Hạng và tên mẫu thiệp (module `template`)."""

    async def tiers(self) -> dict[str, str]:
        """Khoá mẫu -> slug hạng (`free` / `standard` / `premium`)."""
        ...

    async def names(self) -> dict[str, str]: ...


class MomoGateway(Protocol):
    """Tạo phiên thanh toán ví MoMo cho một đơn."""

    @property
    def enabled(self) -> bool: ...

    async def create_payment(self, order: Order, *, redirect_url: str, ipn_url: str) -> str:
        """Trả `payUrl` để chuyển khách sang MoMo.

        Raises: ServiceUnavailableError khi cổng lỗi hoặc từ chối.
        """
        ...


__all__ = ["MomoGateway", "TemplateCatalog"]
