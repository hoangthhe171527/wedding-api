"""Kiểm tra xác thực giao dịch Apple IAP (chặn Sandbox ở prod & chống race condition)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import jwt
import pytest

from app.core.config import Environment, get_settings
from app.core.context import ActorContext
from app.core.errors import ConflictError, ValidationError
from app.modules.billing.application.ports import VerifiedAppleTransaction
from app.modules.billing.application.use_cases.verify_apple_purchase import VerifyApplePurchase
from app.modules.billing.domain.entities import ApplePurchase, Order
from app.modules.billing.domain.enums import PaymentMethod, Plan
from app.modules.billing.infrastructure.external import apple_iap


def _fake_jws(environment: str) -> str:
    return jwt.encode({"environment": environment}, "unused", algorithm="HS256")


def test_chan_giao_dich_sandbox_o_moi_truong_production(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = get_settings()
    monkeypatch.setattr(cfg, "ENV", Environment.PRODUCTION)
    monkeypatch.setattr(cfg, "APPLE_IAP_ALLOW_SANDBOX", False)

    verifier = apple_iap.AppleIapVerifier()
    with pytest.raises(ValidationError) as exc:
        verifier.verify(_fake_jws("Sandbox"))
    assert exc.value.code == "apple_iap_sandbox_disallowed"


def test_cho_phep_sandbox_khi_bat_co_cho_phep(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = get_settings()
    monkeypatch.setattr(cfg, "ENV", Environment.PRODUCTION)
    monkeypatch.setattr(cfg, "APPLE_IAP_ALLOW_SANDBOX", True)

    class _FakeSignedVerifier:
        def __init__(self, *_args: object) -> None:
            pass

        def verify_and_decode_signed_transaction(self, _signed: str) -> SimpleNamespace:
            return SimpleNamespace(
                productId=cfg.APPLE_IAP_PREMIUM_PRODUCT_ID,
                transactionId="tx-1",
                originalTransactionId="orig-1",
                purchaseDate=1_760_000_000_000,
                revocationDate=None,
            )

    monkeypatch.setattr(apple_iap, "SignedDataVerifier", _FakeSignedVerifier)
    result = apple_iap.AppleIapVerifier().verify(_fake_jws("Sandbox"))
    assert result.plan is Plan.PREMIUM
    assert result.environment == "Sandbox"


class _FakeOrders:
    def __init__(self) -> None:
        self.created = False

    async def paid_plans(self, tenant_id: UUID) -> list[Plan]:
        return []

    async def create(
        self,
        *,
        tenant_id: UUID,
        code: str,
        plan: Plan,
        amount: int,
        method: PaymentMethod,
        expires_at: datetime,
        actor_id: UUID | None,
    ) -> Order:
        self.created = True
        raise AssertionError("Không được tạo đơn khi transaction đã thuộc xưởng khác")

    async def mark_paid(self, order_id: UUID, *, reference: str, note: str = "") -> Order | None:
        return None


class _RacePurchases:
    def __init__(self, winner_tenant: UUID) -> None:
        self._winner_tenant = winner_tenant

    async def get_by_transaction_id(self, transaction_id: str) -> ApplePurchase | None:
        return None

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
        # Giả lập DuplicateKeyError trả về bản ghi của tenant đã thắng race trước đó.
        return ApplePurchase(
            transaction_id=transaction_id,
            original_transaction_id=original_transaction_id,
            product_id=product_id,
            plan=plan,
            environment=environment,
            tenant_id=self._winner_tenant,
            purchase_date=purchase_date,
        )


class _StubVerifier:
    def verify(self, signed_transaction: str) -> VerifiedAppleTransaction:
        return VerifiedAppleTransaction(
            transaction_id="tx-race",
            original_transaction_id="orig-race",
            product_id="vn.sunriseieco.thiephy.plan.premium",
            plan=Plan.PREMIUM,
            environment="Production",
            purchase_date=datetime.now(UTC),
        )


async def test_chong_race_cross_tenant_apple_iap() -> None:
    orders = _FakeOrders()
    winner_tenant = uuid4()
    loser_actor = ActorContext(user_id=uuid4(), tenant_id=uuid4(), permissions=frozenset())
    use_case = VerifyApplePurchase(orders, _RacePurchases(winner_tenant), _StubVerifier())  # type: ignore[arg-type]

    with pytest.raises(ConflictError) as exc:
        await use_case.execute(
            loser_actor,
            product_id="vn.sunriseieco.thiephy.plan.premium",
            transaction_id="tx-race",
            signed_transaction="signed",
        )
    assert exc.value.code == "apple_iap_already_linked"
    assert orders.created is False
