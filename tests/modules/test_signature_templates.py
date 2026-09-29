"""Dòng mẫu "Độc bản": 12 mẫu cao cấp xưởng tự thiết kế."""

from __future__ import annotations

from app.modules.template.domain.catalog import TEMPLATE_BLUEPRINTS
from app.modules.template.domain.enums import FAMILY_LABELS, Family, Tier


def _signature() -> list:
    return [item for item in TEMPLATE_BLUEPRINTS if item.family is Family.STORY_SIGNATURE]


def test_doc_ban_du_12_mau_can_goi_long_lay() -> None:
    items = _signature()
    assert len(items) == 12
    assert all(item.tier is Tier.PREMIUM for item in items)
    assert all(item.key.startswith("sg") for item in items)
    assert FAMILY_LABELS[Family.STORY_SIGNATURE] == "Độc bản"


def test_doc_ban_khong_trung_khoa_hay_ten_voi_mau_khac() -> None:
    keys = [item.key for item in TEMPLATE_BLUEPRINTS]
    names = [item.name for item in TEMPLATE_BLUEPRINTS]
    assert len(keys) == len(set(keys))
    assert len(names) == len(set(names))
