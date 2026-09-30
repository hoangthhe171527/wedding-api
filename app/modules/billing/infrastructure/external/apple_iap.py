"""Xác thực giao dịch StoreKit 2 do Apple ký."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jwt
from appstoreserverlibrary.models.Environment import Environment as AppleEnvironment
from appstoreserverlibrary.signed_data_verifier import (
    SignedDataVerifier,
    VerificationException,
)
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding

from app.core.config import get_settings
from app.core.errors import ServiceUnavailableError, ValidationError
from app.modules.billing.application.ports import VerifiedAppleTransaction
from app.modules.billing.domain.enums import Plan


def _root_certificates() -> list[bytes]:
    path = Path(__file__).with_name("certs") / "apple_root_ca_g3.pem"
    certificate = x509.load_pem_x509_certificate(path.read_bytes())
    return [certificate.public_bytes(Encoding.DER)]


class AppleIapVerifier:
    """Kiểm tra chữ ký, bundle id, môi trường và product của giao dịch Apple."""

    def verify(self, signed_transaction: str) -> VerifiedAppleTransaction:
        cfg = get_settings()
        if not signed_transaction.strip():
            raise ValidationError("Thiếu dữ liệu giao dịch Apple.", code="apple_iap_missing")

        try:
            unverified: dict[str, Any] = jwt.decode(
                signed_transaction,
                options={"verify_signature": False},
            )
            environment = AppleEnvironment(str(unverified["environment"]))
        except (KeyError, ValueError, TypeError, jwt.InvalidTokenError) as exc:
            raise ValidationError(
                "Giao dịch Apple không đúng định dạng.", code="apple_iap_invalid"
            ) from exc

        if environment is AppleEnvironment.PRODUCTION and cfg.APPLE_IAP_APPLE_ID is None:
            raise ServiceUnavailableError(
                "Thanh toán App Store chưa được cấu hình hoàn chỉnh.",
                code="apple_iap_not_configured",
            )

        try:
            verifier = SignedDataVerifier(
                _root_certificates(),
                cfg.APPLE_IAP_ENABLE_ONLINE_CHECKS,
                environment,
                cfg.APPLE_IAP_BUNDLE_ID,
                cfg.APPLE_IAP_APPLE_ID,
            )
            transaction = verifier.verify_and_decode_signed_transaction(signed_transaction)
        except (VerificationException, ValueError, OSError) as exc:
            raise ValidationError(
                "Không thể xác thực giao dịch Apple.", code="apple_iap_invalid"
            ) from exc

        product_id = transaction.productId
        transaction_id = transaction.transactionId
        original_transaction_id = transaction.originalTransactionId
        purchase_date = transaction.purchaseDate
        if (
            not product_id
            or not transaction_id
            or not original_transaction_id
            or purchase_date is None
        ):
            raise ValidationError("Giao dịch Apple thiếu thông tin.", code="apple_iap_invalid")
        if transaction.revocationDate is not None:
            raise ValidationError(
                "Giao dịch Apple đã bị hoàn tiền hoặc thu hồi.",
                code="apple_iap_revoked",
            )

        product_to_plan = {
            cfg.APPLE_IAP_STANDARD_PRODUCT_ID: Plan.STANDARD,
            cfg.APPLE_IAP_PREMIUM_PRODUCT_ID: Plan.PREMIUM,
        }
        plan = product_to_plan.get(product_id)
        if plan is None:
            raise ValidationError(
                "Sản phẩm Apple không thuộc ứng dụng này.",
                code="apple_iap_product_invalid",
            )

        return VerifiedAppleTransaction(
            transaction_id=transaction_id,
            original_transaction_id=original_transaction_id,
            product_id=product_id,
            plan=plan,
            environment=environment.value,
            purchase_date=datetime.fromtimestamp(purchase_date / 1000, tz=UTC),
        )


__all__ = ["AppleIapVerifier", "VerifiedAppleTransaction"]
