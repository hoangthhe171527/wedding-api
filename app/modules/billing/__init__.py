"""Module `billing` — gói dịch vụ, đơn hàng, thanh toán (VietQR, MoMo), đối soát.

Sở hữu `orders`, `payment_events`.
"""

from app.modules.billing.infrastructure.external.account_deletion import build_account_data_deleter
from app.modules.billing.infrastructure.external.bridges import (
    build_entitlement_reader,
    build_plan_gate,
    build_plan_granter,
)
from app.modules.billing.interfaces.http.router import router

__all__ = [
    "build_account_data_deleter",
    "build_entitlement_reader",
    "build_plan_gate",
    "build_plan_granter",
    "router",
]
