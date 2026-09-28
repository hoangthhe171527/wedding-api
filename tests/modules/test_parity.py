"""Khoá các bản CHÉP có chủ ý giữa module (§1.2) — chép thì phải trùng.

Chép enum sang module dùng để khỏi import chéo; cái giá là hai bản có thể trôi
khỏi nhau. Bài này đỏ ngay khi điều đó xảy ra.
"""

from __future__ import annotations

from app.modules.guest.domain import enums as guest_enums
from app.modules.template.domain import enums as template_enums
from app.modules.wedding.domain import enums as wedding_enums


def test_nhom_khach_trung_nhau() -> None:
    assert wedding_enums.GUEST_GROUPS == guest_enums.GUEST_GROUPS
    assert template_enums.GUEST_GROUPS == guest_enums.GUEST_GROUPS


def test_o_cau_chu_trung_nhau() -> None:
    assert template_enums.WORDING_KEYS == wedding_enums.WORDING_KEYS


def test_giong_van_trung_nhau() -> None:
    assert {t.value for t in wedding_enums.Tone} == {t.value for t in template_enums.Tone}


def test_goi_trung_hang_mau() -> None:
    from app.modules.billing.domain.enums import Plan

    assert {item.value for item in Plan} == {item.value for item in template_enums.Tier}


def test_man_mo_cua_goi_phu_du_man_mo() -> None:
    """Thêm màn mở mới mà quên bảng gói thì CẢ gói cao nhất cũng không xuất bản được."""
    from app.modules.billing.domain import enums as billing_enums

    all_open = billing_enums._ALL_OPEN
    assert all_open == {item.value for item in wedding_enums.OpenStyle}
    assert all_open >= billing_enums._BASIC_OPEN


def test_huong_dan_ai_du_moi_o_cau_chu_va_giong_van() -> None:
    """Thiếu khoá trong bảng hướng dẫn AI là lỗi 500 ở nút "Gợi ý"."""
    from app.modules.wedding.infrastructure.external.wording_ai import FIELD_GUIDE, TONE_GUIDE

    assert set(FIELD_GUIDE) == set(wedding_enums.WORDING_KEYS)
    assert set(TONE_GUIDE) == {item.value for item in wedding_enums.Tone}
