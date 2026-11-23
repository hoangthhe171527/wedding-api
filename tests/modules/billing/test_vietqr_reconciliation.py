"""Kiểm tra đối soát webhook VietQR và ẩn/hiện giá gói theo cờ online payment."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.core import audit
from app.core.config import get_settings
from app.modules.billing.application.support import BankAccountInfo, SupportContact
from app.modules.billing.application.use_cases.get_billing import BillingSummary
from app.modules.billing.application.use_cases.record_payment import (
    BankTransfer,
    RecordBankTransfer,
)
from app.modules.billing.domain.entities import Order, PaymentEvent
from app.modules.billing.domain.enums import (
    PLAN_SPECS,
    OrderStatus,
    PaymentEventStatus,
    PaymentMethod,
    Plan,
)
from app.modules.billing.domain.repositories import DuplicatePaymentEventError
from app.modules.billing.interfaces.http.schemas import BillingOut, all_plans


class _FakeOrders:
    def __init__(self, order: Order) -> None:
        self.order = order

    def current_status(self) -> OrderStatus:
        return self.order.status

    async def find_by_code(self, code: str) -> Order | None:
        return self.order if code == self.order.code else None

    async def mark_paid(self, order_id: UUID, *, reference: str, note: str = "") -> Order | None:
        if order_id != self.order.id or self.order.status is OrderStatus.PAID:
            return None
        self.order = Order(
            id=self.order.id,
            tenant_id=self.order.tenant_id,
            code=self.order.code,
            plan=self.order.plan,
            amount=self.order.amount,
            method=self.order.method,
            status=OrderStatus.PAID,
            expires_at=self.order.expires_at,
            created_at=self.order.created_at,
            paid_at=datetime.now(UTC),
            reference=reference,
            note=note,
        )
        return self.order


class _FakeEvents:
    def __init__(self) -> None:
        self.seen: set[tuple[str, str]] = set()
        self.items: list[PaymentEvent] = []

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
        raw: dict[str, Any],
    ) -> PaymentEvent:
        del raw
        key = (source, external_id)
        if key in self.seen:
            raise DuplicatePaymentEventError
        self.seen.add(key)
        event = PaymentEvent(
            id=uuid4(),
            source=source,
            external_id=external_id,
            amount=amount,
            content=content,
            status=status,
            received_at=datetime.now(UTC),
            order_code=order_code,
            tenant_id=tenant_id,
        )
        self.items.append(event)
        return event


def _pending_order(amount: int = 199_000) -> Order:
    now = datetime.now(UTC)
    return Order(
        id=uuid4(),
        tenant_id=uuid4(),
        code="TH7K2M9P4Q2X",
        plan=Plan.STANDARD,
        amount=amount,
        method=PaymentMethod.BANK_TRANSFER,
        status=OrderStatus.PENDING,
        expires_at=now + timedelta(hours=2),
        created_at=now,
    )


async def test_webhook_loc_sai_tai_khoan_nhan_va_ghi_audit_khi_khop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = get_settings()
    monkeypatch.setattr(cfg, "ONLINE_PAYMENT_ENABLED", True)
    monkeypatch.setattr(cfg, "BANK_WEBHOOK_KEY", "k" * 32)
    monkeypatch.setattr(cfg, "BANK_ACCOUNT_NO", "1023-456-789")

    audits: list[tuple[str, dict[str, Any]]] = []

    async def _fake_audit(
        action: str,
        *,
        actor_id: UUID | None,
        target_type: str,
        target_id: object,
        tenant_id: UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        del target_type, target_id, tenant_id
        assert actor_id is None
        audits.append((action, details or {}))

    monkeypatch.setattr(audit, "record", _fake_audit)

    order = _pending_order(199_000)
    orders = _FakeOrders(order)
    events = _FakeEvents()
    use_case = RecordBankTransfer(orders, events)  # type: ignore[arg-type]

    # Báo có gửi nhầm sang STK khác -> IGNORED, đơn vẫn PENDING.
    wrong_acc = await use_case.execute(
        "k" * 32,
        BankTransfer(
            external_id="tx-wrong-acc",
            amount=199_000,
            content=order.code,
            direction="in",
            raw={},
            account_number="9999999999",
        ),
    )
    assert wrong_acc is PaymentEventStatus.IGNORED
    assert orders.current_status() is OrderStatus.PENDING
    assert events.items == []

    # Chuyển thiếu tiền vào đúng STK -> UNDERPAID, đơn vẫn PENDING.
    under = await use_case.execute(
        "k" * 32,
        BankTransfer(
            external_id="tx-under",
            amount=100_000,
            content=f"MBVCB.{order.code}",
            direction="in",
            raw={},
            account_number="1023456789",
        ),
    )
    assert under is PaymentEventStatus.UNDERPAID
    assert orders.current_status() is OrderStatus.PENDING

    # Chuyển đủ tiền vào đúng STK -> MATCHED, kích hoạt đơn và ghi audit.
    matched = await use_case.execute(
        "k" * 32,
        BankTransfer(
            external_id="tx-ok",
            amount=199_000,
            content=f"CT {order.code}",
            direction="in",
            raw={},
            account_number="1023 456 789",
        ),
    )
    assert matched is PaymentEventStatus.MATCHED
    assert orders.current_status() is OrderStatus.PAID
    assert audits == [
        (
            "order.paid_auto",
            {
                "code": order.code,
                "source": "bank",
                "amount": 199_000,
                "external_id": "tx-ok",
            },
        )
    ]

    # Gửi lại đúng external_id -> DUPLICATE, không kích hoạt hay audit lần 2.
    replay = await use_case.execute(
        "k" * 32,
        BankTransfer(
            external_id="tx-ok",
            amount=199_000,
            content=order.code,
            direction="in",
            raw={},
            account_number="1023456789",
        ),
    )
    assert replay is PaymentEventStatus.DUPLICATE
    assert len(audits) == 1


def test_billing_out_chi_tra_gia_khi_bat_online_payment() -> None:
    contact = SupportContact(zalo_phone="0987000111", zalo_name="CSKH")
    bank = BankAccountInfo(bank="Vietcombank", bin="970436", number="1023456789", holder="CONG TY")
    upgrade_prices: dict[Plan, int | None] = {
        Plan.FREE: None,
        Plan.STANDARD: PLAN_SPECS[Plan.STANDARD].price,
        Plan.PREMIUM: PLAN_SPECS[Plan.PREMIUM].price,
    }

    zalo_mode = BillingOut.of(
        BillingSummary(
            plan=Plan.FREE,
            upgrade_prices=upgrade_prices,
            orders=[],
            contact=contact,
            online_payment=False,
            bank=bank,
            momo=False,
            sandbox=False,
        )
    )
    assert zalo_mode.prices == {}

    online_mode = BillingOut.of(
        BillingSummary(
            plan=Plan.FREE,
            upgrade_prices=upgrade_prices,
            orders=[],
            contact=contact,
            online_payment=True,
            bank=bank,
            momo=False,
            sandbox=True,
        )
    )
    assert online_mode.prices == {
        "standard": PLAN_SPECS[Plan.STANDARD].price,
        "premium": PLAN_SPECS[Plan.PREMIUM].price,
    }
    assert all("price" not in item.model_dump() for item in all_plans())
