"""Schema HTTP của `billing`."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.billing.application.support import (
    BankAccountInfo,
    SupportContact,
    bank_account,
    support_contact,
)
from app.modules.billing.application.use_cases import BillingSummary
from app.modules.billing.domain.entities import Order, PaymentEvent
from app.modules.billing.domain.enums import (
    ORDER_STATUS_LABELS,
    PLAN_SPECS,
    OrderStatus,
    PaymentMethod,
    Plan,
    PlanSpec,
)


class LabelOut(BaseModel):
    slug: str
    label: str


class PlanOut(BaseModel):
    """Một gói trên bảng giá."""

    slug: Plan
    label: str
    guest_limit: int
    open_styles: list[str]
    per_guest_links: bool
    remove_badge: bool
    theme: bool
    music: bool
    gift: bool
    design: bool
    highlights: list[str]

    @classmethod
    def of(cls, spec: PlanSpec) -> PlanOut:
        return cls(
            slug=spec.plan,
            label=spec.label,
            guest_limit=spec.guest_limit,
            open_styles=sorted(spec.open_styles),
            per_guest_links=spec.per_guest_links,
            remove_badge=spec.remove_badge,
            theme=spec.theme,
            music=spec.music,
            gift=spec.gift,
            design=spec.design,
            highlights=list(spec.highlights),
        )


def all_plans() -> list[PlanOut]:
    return [PlanOut.of(spec) for spec in PLAN_SPECS.values()]


class TransferOut(BaseModel):
    """Thông tin chuyển khoản: quét mã VietQR hoặc gõ tay đúng nội dung."""

    bank: str
    bin: str
    number: str
    holder: str
    amount: int
    content: str
    qr_url: str

    @classmethod
    def of(cls, account: BankAccountInfo, order: Order) -> TransferOut:
        qr_url = (
            f"https://img.vietqr.io/image/{account.bin}-{account.number}-compact2.png"
            f"?amount={order.amount}&addInfo={order.code}&accountName={quote(account.holder)}"
        )
        return cls(
            bank=account.bank,
            bin=account.bin,
            number=account.number,
            holder=account.holder,
            amount=order.amount,
            content=order.code,
            qr_url=qr_url,
        )


class OrderOut(BaseModel):
    id: UUID
    code: str
    plan: LabelOut
    amount: int
    method: PaymentMethod
    status: LabelOut
    created_at: datetime
    expires_at: datetime
    paid_at: datetime | None = None
    pay_url: str = ""
    transfer: TransferOut | None = None
    tenant_id: UUID | None = None
    reference: str = ""
    note: str = ""

    @classmethod
    def of(cls, order: Order, *, admin: bool = False) -> OrderOut:
        account = bank_account()
        transfer = (
            TransferOut.of(account, order)
            if account and order.method is PaymentMethod.BANK_TRANSFER
            else None
        )
        return cls(
            id=order.id,
            code=order.code,
            plan=LabelOut(slug=order.plan.value, label=PLAN_SPECS[order.plan].label),
            amount=order.amount,
            method=order.method,
            status=LabelOut(slug=order.status.value, label=ORDER_STATUS_LABELS[order.status]),
            created_at=order.created_at,
            expires_at=order.expires_at,
            paid_at=order.paid_at,
            pay_url=order.pay_url,
            transfer=transfer,
            tenant_id=order.tenant_id if admin else None,
            reference=order.reference if admin else "",
            note=order.note if admin else "",
        )


class ContactOut(BaseModel):
    """Kênh tư vấn nâng gói qua Zalo."""

    zalo_phone: str
    zalo_name: str
    zalo_url: str

    @classmethod
    def of(cls, item: SupportContact) -> ContactOut:
        return cls(zalo_phone=item.zalo_phone, zalo_name=item.zalo_name, zalo_url=item.zalo_url)


def current_contact() -> ContactOut:
    return ContactOut.of(support_contact())


class BillingOut(BaseModel):
    """Gói hiện tại của xưởng, các gói, kênh nâng gói và các đơn gần đây.

    Giá không trả ra: giá do đội tư vấn báo qua Zalo.
    """

    plan: PlanOut
    plans: list[PlanOut]
    contact: ContactOut
    #: Khách tự thanh toán trực tuyến được không (tắt = nâng qua Zalo).
    online_payment: bool
    orders: list[OrderOut]
    methods: list[PaymentMethod]
    sandbox: bool

    @classmethod
    def of(cls, summary: BillingSummary) -> BillingOut:
        methods: list[PaymentMethod] = []
        if summary.bank or summary.sandbox:
            methods.append(PaymentMethod.BANK_TRANSFER)
        if summary.momo:
            methods.append(PaymentMethod.MOMO)
        return cls(
            plan=PlanOut.of(PLAN_SPECS[summary.plan]),
            plans=all_plans(),
            contact=ContactOut.of(summary.contact),
            online_payment=summary.online_payment,
            orders=[OrderOut.of(item) for item in summary.orders],
            methods=methods,
            sandbox=summary.sandbox,
        )


class AppleIapVerifyIn(BaseModel):
    """JWS StoreKit 2 gửi từ app lên để máy chủ xác thực."""

    product_id: str = Field(min_length=1, max_length=200)
    transaction_id: str = Field(min_length=1, max_length=200)
    signed_transaction: str = Field(min_length=1, max_length=100_000)


class AppleIapVerifyOut(BaseModel):
    """Kết quả cấp quyền sau khi xác thực transaction Apple."""

    transaction_id: str
    plan: LabelOut
    current_plan: LabelOut
    activated: bool


class OrderIn(BaseModel):
    plan: Plan
    method: PaymentMethod = PaymentMethod.BANK_TRANSFER


class GrantIn(BaseModel):
    """Cấp gói sau khi chốt với khách qua Zalo. `amount` = số tiền đã thu (có thể 0)."""

    plan: Plan
    amount: Annotated[int, Field(ge=0, le=100_000_000)] = 0
    note: Annotated[str, Field(min_length=3, max_length=300)]


class StudioPlanOut(BaseModel):
    studio_id: UUID
    plan: LabelOut


class ConfirmIn(BaseModel):
    note: Annotated[str, Field(min_length=3, max_length=300)]


class BankWebhookIn(BaseModel):
    """Webhook báo có theo định dạng dịch vụ đọc sao kê (kiểu SePay).

    Giữ nguyên trường lạ (`extra="allow"`) để lưu đủ vào sổ đối soát.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: int | str
    content: str = ""
    transfer_type: str = Field(default="in", alias="transferType")
    transfer_amount: int = Field(alias="transferAmount", ge=0)
    account_number: str = Field(default="", alias="accountNumber")
    reference_code: str = Field(default="", alias="referenceCode")


class PaymentEventOut(BaseModel):
    id: UUID
    source: str
    external_id: str
    amount: int
    content: str
    status: str
    order_code: str
    tenant_id: UUID | None
    received_at: datetime

    @classmethod
    def of(cls, event: PaymentEvent) -> PaymentEventOut:
        return cls(
            id=event.id,
            source=event.source,
            external_id=event.external_id,
            amount=event.amount,
            content=event.content,
            status=event.status.value,
            order_code=event.order_code,
            tenant_id=event.tenant_id,
            received_at=event.received_at,
        )


class WebhookAckOut(BaseModel):
    success: bool = True
    status: str


__all__ = [
    "AppleIapVerifyIn",
    "AppleIapVerifyOut",
    "BankWebhookIn",
    "BillingOut",
    "ConfirmIn",
    "ContactOut",
    "GrantIn",
    "OrderIn",
    "OrderOut",
    "OrderStatus",
    "PaymentEventOut",
    "PlanOut",
    "StudioPlanOut",
    "WebhookAckOut",
    "all_plans",
    "current_contact",
]
