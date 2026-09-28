"""Cổng ví MoMo (API v2, kiểu `captureWallet`).

Tắt khi chưa có khoá đối tác. Đối chiếu lại tài liệu MoMo và chạy thử trên môi
trường test của MoMo khi ký hợp đồng — tên trường và thứ tự ký nằm ở
`billing.domain.services`.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import ServiceUnavailableError
from app.core.logging import get_logger
from app.modules.billing.domain.entities import Order
from app.modules.billing.domain.enums import PLAN_SPECS
from app.modules.billing.domain.services import MOMO_CREATE_FIELDS, momo_signature

log = get_logger(__name__)

_TIMEOUT_SECONDS = 15.0


class HttpMomoGateway:
    """`MomoGateway` gọi thẳng HTTP tới MoMo."""

    @property
    def enabled(self) -> bool:
        cfg = get_settings()
        return bool(cfg.MOMO_PARTNER_CODE and cfg.MOMO_ACCESS_KEY and cfg.MOMO_SECRET_KEY)

    async def create_payment(self, order: Order, *, redirect_url: str, ipn_url: str) -> str:
        cfg = get_settings()
        body: dict[str, Any] = {
            "partnerCode": cfg.MOMO_PARTNER_CODE,
            "accessKey": cfg.MOMO_ACCESS_KEY,
            "requestId": f"{order.code}-{order.id.hex[:8]}",
            "amount": order.amount,
            "orderId": order.code,
            "orderInfo": f"{PLAN_SPECS[order.plan].label} {order.code}",
            "redirectUrl": redirect_url,
            "ipnUrl": ipn_url,
            "requestType": "captureWallet",
            "extraData": "",
            "lang": "vi",
        }
        body["signature"] = momo_signature(cfg.MOMO_SECRET_KEY, MOMO_CREATE_FIELDS, body)
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.post(cfg.MOMO_ENDPOINT, json=body)
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("momo_create_failed", code=order.code, error=type(exc).__name__)
            raise _unavailable() from exc
        if str(data.get("resultCode")) != "0" or not data.get("payUrl"):
            log.warning(
                "momo_create_rejected",
                code=order.code,
                result=data.get("resultCode"),
                message=data.get("message"),
            )
            raise _unavailable()
        return str(data["payUrl"])


def _unavailable() -> ServiceUnavailableError:
    return ServiceUnavailableError(
        "MoMo chưa nhận thanh toán lúc này. Vui lòng thử lại hoặc chuyển khoản ngân hàng.",
        code="momo_failed",
    )


__all__ = ["HttpMomoGateway"]
