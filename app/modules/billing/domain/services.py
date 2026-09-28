"""Hàm thuần của `billing`: mã đơn, giá nâng cấp, xét gói, chữ ký MoMo."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from collections.abc import Iterable, Mapping
from typing import Final

from app.modules.billing.domain.entities import Usage, Violation
from app.modules.billing.domain.enums import PLAN_RANK, PLAN_SPECS, Plan

#: Bỏ chữ dễ nhầm khi khách gõ tay nội dung chuyển khoản (0/O, 1/I/L).
_CODE_ALPHABET: Final[str] = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_PREFIX: Final[str] = "TH"
CODE_BODY_LENGTH: Final[int] = 10
_CODE_RE: Final = re.compile(rf"{CODE_PREFIX}[{_CODE_ALPHABET}]{{{CODE_BODY_LENGTH}}}")
_NON_ALNUM: Final = re.compile(r"[^A-Z0-9]")

_OPEN_STYLE_LABELS: Final[dict[str, str]] = {
    "mix": "bìa tạp chí / rèm nhung",
    "3d": "hoạt hình cô dâu chú rể",
    "particles": "hạt nhũ kết thành tên",
    "gate": "cổng son",
    "lotus": "sen nở",
    "scroll": "cuộn thư lụa",
    "box": "hộp quà nhung",
}


def generate_order_code() -> str:
    """`TH` + 10 ký tự: đủ ngắn để gõ tay, đủ dài để không đoán hay trùng."""
    return CODE_PREFIX + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(CODE_BODY_LENGTH))


def find_order_code(content: str) -> str | None:
    """Tìm mã đơn trong nội dung chuyển khoản.

    Ngân hàng hay chèn khoảng trắng, gạch nối hoặc tiền tố ("MBVCB.123.TH7K…")
    và đổi chữ hoa/thường — nên bỏ hết ký tự không phải chữ số trước khi tìm.
    """
    match = _CODE_RE.search(_NON_ALNUM.sub("", content.upper()))
    return match.group(0) if match else None


def highest_plan(plans: Iterable[Plan]) -> Plan:
    """Gói cao nhất trong các gói đã trả; không có gì thì là Miễn phí."""
    return max(plans, key=lambda plan: PLAN_RANK[plan], default=Plan.FREE)


def upgrade_price(current: Plan, target: Plan) -> int | None:
    """Số tiền cần trả để lên `target` khi đang có `current`; None = không nâng được."""
    if PLAN_RANK[target] <= PLAN_RANK[current]:
        return None
    return PLAN_SPECS[target].price - PLAN_SPECS[current].price


def _plan_for_tier(tier: str) -> Plan:
    try:
        return Plan(tier)
    except ValueError:
        return Plan.STANDARD


def violations(
    plan: Plan, usage: Usage, template_tiers: Mapping[str, str], template_names: Mapping[str, str]
) -> list[Violation]:
    """Những thứ đám cưới đang dùng mà gói `plan` chưa cho phép.

    Chỉ xét khi XUẤT BẢN: soạn và xem trước thì dùng thoải mái mọi thứ.
    """
    found: list[Violation] = []
    rank = PLAN_RANK[plan]
    spec = PLAN_SPECS[plan]

    for key in sorted(usage.templates):
        needed = _plan_for_tier(template_tiers.get(key, Plan.STANDARD.value))
        if PLAN_RANK[needed] > rank:
            name = template_names.get(key, key)
            found.append(
                Violation(
                    code="template",
                    message=f"Mẫu “{name}” thuộc {PLAN_SPECS[needed].label}.",
                    plan=needed,
                )
            )

    if usage.open_style not in spec.open_styles:
        needed = min(
            (item for item in Plan if usage.open_style in PLAN_SPECS[item].open_styles),
            key=lambda item: PLAN_RANK[item],
            default=Plan.PREMIUM,
        )
        label = _OPEN_STYLE_LABELS.get(usage.open_style, usage.open_style)
        found.append(
            Violation(
                code="open_style",
                message=f"Màn mở “{label}” thuộc {PLAN_SPECS[needed].label}.",
                plan=needed,
            )
        )

    if usage.guest_count > spec.guest_limit:
        needed = min(
            (item for item in Plan if PLAN_SPECS[item].guest_limit >= usage.guest_count),
            key=lambda item: PLAN_RANK[item],
            default=Plan.PREMIUM,
        )
        found.append(
            Violation(
                code="guests",
                message=(
                    f"{spec.label} xuất bản tối đa {spec.guest_limit} thiệp mời; "
                    f"bạn đang có {usage.guest_count}."
                ),
                plan=needed,
            )
        )

    feature_checks = (
        (usage.theme and not spec.theme, "theme", "Màu, font, hiệu ứng tự chỉnh"),
        (usage.gift and not spec.gift, "gift", "Hộp mừng cưới"),
        (usage.music and not spec.music, "music", "Nhạc nền"),
        (usage.design and not spec.design, "design", "Thiệp tự thiết kế"),
    )
    for used, code, label in feature_checks:
        if not used:
            continue
        needed = min(
            (item for item in Plan if getattr(PLAN_SPECS[item], code)),
            key=lambda item: PLAN_RANK[item],
        )
        found.append(
            Violation(code=code, message=f"{label} thuộc {PLAN_SPECS[needed].label}.", plan=needed)
        )
    return found


def required_plan(found: Iterable[Violation], current: Plan) -> Plan:
    """Gói thấp nhất đủ cho mọi thứ đang dùng."""
    return highest_plan([current, *(item.plan for item in found)])


# --- MoMo (API v2, "captureWallet") ------------------------------------------
#: Thứ tự trường ký cố định theo tài liệu MoMo — sai thứ tự là sai chữ ký.
MOMO_CREATE_FIELDS: Final[tuple[str, ...]] = (
    "accessKey",
    "amount",
    "extraData",
    "ipnUrl",
    "orderId",
    "orderInfo",
    "partnerCode",
    "redirectUrl",
    "requestId",
    "requestType",
)
MOMO_IPN_FIELDS: Final[tuple[str, ...]] = (
    "accessKey",
    "amount",
    "extraData",
    "message",
    "orderId",
    "orderInfo",
    "orderType",
    "partnerCode",
    "payType",
    "requestId",
    "responseTime",
    "resultCode",
    "transId",
)


def momo_signature(secret_key: str, fields: tuple[str, ...], values: Mapping[str, object]) -> str:
    """HMAC-SHA256 hex trên chuỗi `k1=v1&k2=v2...` theo đúng thứ tự `fields`."""
    raw = "&".join(f"{name}={values.get(name, '')}" for name in fields)
    return hmac.new(secret_key.encode(), raw.encode(), hashlib.sha256).hexdigest()


def momo_signature_valid(
    secret_key: str, access_key: str, payload: Mapping[str, object], signature: str
) -> bool:
    expected = momo_signature(secret_key, MOMO_IPN_FIELDS, {**payload, "accessKey": access_key})
    return hmac.compare_digest(expected, signature)


__all__ = [
    "CODE_PREFIX",
    "MOMO_CREATE_FIELDS",
    "MOMO_IPN_FIELDS",
    "find_order_code",
    "generate_order_code",
    "highest_plan",
    "momo_signature",
    "momo_signature_valid",
    "required_plan",
    "upgrade_price",
    "violations",
]
