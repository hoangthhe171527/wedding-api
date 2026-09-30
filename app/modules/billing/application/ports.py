"""Cổng của `billing` sang module khác và ra ngoài hệ thống."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.billing.domain.entities import Order
from app.modules.billing.domain.enums import Plan


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


@dataclass(frozen=True, slots=True)
class VerifiedAppleTransaction:
    """Dữ liệu giao dịch sau khi infrastructure đã xác thực chữ ký Apple."""

    transaction_id: str
    original_transaction_id: str
    product_id: str
    plan: Plan
    environment: str
    purchase_date: datetime


class AppleTransactionVerifier(Protocol):
    """Cổng xác thực JWS StoreKit, do tầng infrastructure hiện thực."""

    def verify(self, signed_transaction: str) -> VerifiedAppleTransaction: ...


__all__ = [
    "AppleTransactionVerifier",
    "MomoGateway",
    "TemplateCatalog",
    "VerifiedAppleTransaction",
]
