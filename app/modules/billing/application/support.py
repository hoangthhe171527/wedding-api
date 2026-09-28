"""Mảnh dùng chung giữa các use case của `billing`."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.base_model import utc_now
from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.modules.billing.application.ports import PlanWaiver
from app.modules.billing.domain.enums import Plan
from app.modules.billing.domain.repositories import OrderRepository
from app.modules.billing.domain.services import highest_plan


@dataclass(frozen=True, slots=True)
class BankAccountInfo:
    """Tài khoản nhận tiền hiện trên màn chuyển khoản VietQR."""

    bin: str
    bank: str
    number: str
    holder: str


def bank_account() -> BankAccountInfo | None:
    """Tài khoản nhận chuyển khoản; None nếu chưa cấu hình."""
    cfg = get_settings()
    if not (cfg.BANK_BIN and cfg.BANK_ACCOUNT_NO and cfg.BANK_ACCOUNT_NAME):
        return None
    return BankAccountInfo(
        bin=cfg.BANK_BIN,
        bank=cfg.BANK_NAME,
        number=cfg.BANK_ACCOUNT_NO,
        holder=cfg.BANK_ACCOUNT_NAME,
    )


def sandbox() -> bool:
    """Chế độ giả lập thanh toán — chỉ bật được ở local/test (Settings chặn)."""
    return get_settings().PAYMENT_SANDBOX


@dataclass(frozen=True, slots=True)
class SupportContact:
    """Kênh tư vấn nâng gói."""

    zalo_phone: str
    zalo_name: str

    @property
    def zalo_url(self) -> str:
        digits = "".join(char for char in self.zalo_phone if char.isdigit())
        return f"https://zalo.me/{digits}" if digits else ""


def support_contact() -> SupportContact:
    cfg = get_settings()
    return SupportContact(zalo_phone=cfg.SUPPORT_ZALO_PHONE, zalo_name=cfg.SUPPORT_ZALO_NAME)


def online_payment() -> bool:
    """Khách tự thanh toán trực tuyến; tắt = nâng gói qua tư vấn Zalo."""
    return get_settings().ONLINE_PAYMENT_ENABLED


def order_not_found() -> NotFoundError:
    return NotFoundError("Không tìm thấy đơn hàng.", code="order_not_found")


async def current_plan(
    orders: OrderRepository, tenant_id: UUID, waiver: PlanWaiver | None = None
) -> Plan:
    """Gói hiện tại = gói cao nhất trong các đơn ĐÃ trả của xưởng.

    Xưởng được miễn (tài khoản quản trị) luôn ở gói cao nhất, không cần đơn nào.
    """
    if waiver is not None and await waiver.waived(tenant_id):
        return Plan.PREMIUM
    return highest_plan(await orders.paid_plans(tenant_id))


async def expire_stale(orders: OrderRepository, tenant_id: UUID | None = None) -> None:
    """Chuyển đơn quá hạn sang "Hết hạn" ở đầu các lượt đọc.

    Trang của khách chỉ quét đơn của CHÍNH xưởng đó; chỉ màn đối soát (`tenant_id`
    None) mới quét toàn hệ thống — nếu không, mỗi lượt mở trang gói của bất kỳ
    xưởng nào là một lệnh ghi quét đơn của mọi xưởng.
    """
    await orders.expire_due(utc_now(), tenant_id)


__all__ = [
    "BankAccountInfo",
    "SupportContact",
    "bank_account",
    "current_plan",
    "expire_stale",
    "online_payment",
    "order_not_found",
    "sandbox",
    "support_contact",
]
