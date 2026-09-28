"""Luật thuần của `billing`: mã đơn, giá nâng cấp, xét gói, chữ ký MoMo."""

from __future__ import annotations

from app.modules.billing.domain.entities import Usage
from app.modules.billing.domain.enums import Plan
from app.modules.billing.domain.services import (
    MOMO_IPN_FIELDS,
    find_order_code,
    generate_order_code,
    momo_signature,
    momo_signature_valid,
    required_plan,
    upgrade_price,
    violations,
)


def _usage(**changes: object) -> Usage:
    base: dict[str, object] = {
        "templates": frozenset({"songhy"}),
        "open_style": "",
        "guest_count": 10,
        "music": False,
        "gift": False,
        "theme": False,
    }
    base.update(changes)
    return Usage(**base)  # type: ignore[arg-type]


def test_ma_don_tim_duoc_trong_noi_dung_ban() -> None:
    code = generate_order_code()
    assert len(code) == 12
    assert find_order_code(f"IBFT {code.lower()} chuyen tien") == code
    assert find_order_code(f"{code[:4]}-{code[4:8]} {code[8:]}") == code
    assert find_order_code("khong co ma") is None


def test_gia_nang_cap() -> None:
    assert upgrade_price(Plan.FREE, Plan.PREMIUM) == 499_000
    assert upgrade_price(Plan.STANDARD, Plan.PREMIUM) == 300_000
    assert upgrade_price(Plan.PREMIUM, Plan.STANDARD) is None
    assert upgrade_price(Plan.STANDARD, Plan.STANDARD) is None


def test_xet_goi() -> None:
    tiers = {"songhy": "free", "hongphuc": "free", "uyenuong": "premium", "tapchi": "standard"}
    names = {"uyenuong": "Uyên Ương 3D"}
    assert violations(Plan.FREE, _usage(), tiers, names) == []

    found = violations(
        Plan.FREE,
        _usage(templates=frozenset({"uyenuong", "tapchi"}), guest_count=120, theme=True),
        tiers,
        names,
    )
    by_code = {item.code: item for item in found}
    assert by_code["guests"].plan is Plan.STANDARD
    assert by_code["theme"].plan is Plan.STANDARD
    assert "Uyên Ương 3D" in found[1].message
    assert required_plan(found, Plan.FREE) is Plan.PREMIUM

    gate = violations(Plan.STANDARD, _usage(open_style="gate"), tiers, names)
    assert [item.plan for item in gate] == [Plan.PREMIUM]
    assert violations(Plan.PREMIUM, _usage(open_style="gate", music=True), tiers, names) == []


def test_chu_ky_momo_kiem_duoc_va_bat_duoc_sua_so_tien() -> None:
    payload = {
        "partnerCode": "MOMO",
        "orderId": "TH7KQ2M9XR4P",
        "requestId": "r1",
        "amount": 199000,
        "orderInfo": "Gói Hỷ",
        "orderType": "momo_wallet",
        "transId": 123,
        "resultCode": 0,
        "message": "Thành công.",
        "payType": "qr",
        "responseTime": 1,
        "extraData": "",
    }
    signature = momo_signature("secret", MOMO_IPN_FIELDS, {**payload, "accessKey": "ak"})
    assert momo_signature_valid("secret", "ak", payload, signature)
    assert not momo_signature_valid("secret", "ak", {**payload, "amount": 1}, signature)
