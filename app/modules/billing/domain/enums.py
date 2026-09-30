"""Enum và bảng gói của `billing`.

Cặp đôi trả **một lần cho một đám cưới** (xưởng), không thuê bao: đám cưới là
việc một lần. Mua gói cao hơn khi đã có gói thấp thì chỉ trả phần chênh lệch.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class Plan(StrEnum):
    """Gói dịch vụ. Slug trùng `template.domain.enums.Tier` (bản gốc của hạng mẫu)."""

    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"


#: Thứ bậc để so sánh gói: gói cao hơn gồm mọi quyền của gói thấp hơn.
PLAN_RANK: Final[dict[Plan, int]] = {Plan.FREE: 0, Plan.STANDARD: 1, Plan.PREMIUM: 2}


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


ORDER_STATUS_LABELS: Final[dict[OrderStatus, str]] = {
    OrderStatus.PENDING: "Chờ thanh toán",
    OrderStatus.PAID: "Đã thanh toán",
    OrderStatus.EXPIRED: "Hết hạn",
    OrderStatus.CANCELLED: "Đã huỷ",
}


class PaymentMethod(StrEnum):
    """Cách trả tiền.

    * `bank_transfer` — chuyển khoản VietQR; ngân hàng báo về qua webhook và
      hệ thống tự khớp theo mã đơn trong nội dung chuyển khoản.
    * `momo` — ví MoMo, cổng báo kết quả qua IPN có chữ ký.
    * `apple_iap` — giao dịch StoreKit 2, đã xác thực JWS bởi máy chủ.
    """

    BANK_TRANSFER = "bank_transfer"
    MOMO = "momo"
    APPLE_IAP = "apple_iap"


class PaymentEventStatus(StrEnum):
    """Kết quả xử lý một báo có tiền về — để đội vận hành đối soát."""

    MATCHED = "matched"
    DUPLICATE = "duplicate"
    UNMATCHED = "unmatched"
    UNDERPAID = "underpaid"
    IGNORED = "ignored"


@dataclass(frozen=True, slots=True)
class PlanSpec:
    """Quyền của một gói.

    Attributes:
        price: Giá niêm yết (đồng).
        guest_limit: Số thiệp mời tối đa được xuất bản.
        open_styles: Màn mở thiệp được chọn cố định cho mọi mẫu. `""` (theo mẫu)
            luôn được: màn mở theo mẫu đã bị giới hạn qua hạng của mẫu.
        per_guest_links: Link riêng từng khách (`#mã`). Tắt thì link nào cũng mở
            như link chung.
        remove_badge: Bỏ dấu "Tạo bởi Xưởng Thiệp Hỷ" ở cuối web thiệp.
        theme: Tự chỉnh màu, font, hiệu ứng nền.
        music: Nhạc nền.
        gift: Hộp mừng cưới (số tài khoản).
    """

    plan: Plan
    label: str
    price: int
    guest_limit: int
    open_styles: frozenset[str]
    per_guest_links: bool
    remove_badge: bool
    theme: bool
    music: bool
    gift: bool
    design: bool
    highlights: tuple[str, ...]


_BASIC_OPEN: Final[frozenset[str]] = frozenset({"", "env", "fold"})
_ALL_OPEN: Final[frozenset[str]] = frozenset(
    {"", "env", "fold", "mix", "3d", "particles", "gate", "lotus", "scroll", "box"}
)

PLAN_SPECS: Final[dict[Plan, PlanSpec]] = {
    Plan.FREE: PlanSpec(
        plan=Plan.FREE,
        label="Miễn phí",
        price=0,
        guest_limit=50,
        open_styles=_BASIC_OPEN,
        per_guest_links=False,
        remove_badge=False,
        theme=False,
        music=False,
        gift=False,
        design=False,
        highlights=(
            "5 mẫu cổ điển",
            "Tối đa 50 khách",
            "Link chung cho mọi khách",
            "Xác nhận tham dự trên thiệp",
        ),
    ),
    Plan.STANDARD: PlanSpec(
        plan=Plan.STANDARD,
        label="Gói Hỷ",
        price=199_000,
        guest_limit=300,
        open_styles=_BASIC_OPEN | {"mix"},
        per_guest_links=True,
        remove_badge=True,
        theme=True,
        music=False,
        gift=True,
        design=False,
        highlights=(
            "Mẫu tiêu chuẩn",
            "Tối đa 300 khách",
            "Link riêng in tên từng khách",
            "Tự chỉnh màu, font, hiệu ứng",
            "Hộp mừng cưới",
            "Bỏ dấu “Tạo bởi”",
        ),
    ),
    Plan.PREMIUM: PlanSpec(
        plan=Plan.PREMIUM,
        label="Gói Lộng Lẫy",
        price=499_000,
        guest_limit=2000,
        open_styles=_ALL_OPEN,
        per_guest_links=True,
        remove_badge=True,
        theme=True,
        music=True,
        gift=True,
        design=True,
        highlights=(
            "Mọi mẫu, kể cả Cung đình và Hoạt hình 3D",
            "Mọi màn mở: cổng son, sen nở, cuộn thư, hộp quà",
            "Tự thiết kế thiệp: kéo thả chữ, ảnh, hoạ tiết",
            "Không giới hạn khách (tối đa 2.000)",
            "Nhạc nền",
            "Mọi quyền của Gói Hỷ",
        ),
    ),
}

#: Đơn chưa trả sau chừng này giờ thì hết hạn (chuyển khoản có thể về chậm).
ORDER_TTL_HOURS: Final[int] = 24

__all__ = [
    "ORDER_STATUS_LABELS",
    "ORDER_TTL_HOURS",
    "PLAN_RANK",
    "PLAN_SPECS",
    "OrderStatus",
    "PaymentEventStatus",
    "PaymentMethod",
    "Plan",
    "PlanSpec",
]
