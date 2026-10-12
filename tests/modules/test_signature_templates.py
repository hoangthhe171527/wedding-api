"""Dòng mẫu "Độc bản": 12 mẫu cao cấp xưởng tự thiết kế."""

from __future__ import annotations

from app.modules.template.domain.catalog import ORIGINAL_TEMPLATE_KEYS, TEMPLATE_BLUEPRINTS
from app.modules.template.domain.entities import Template
from app.modules.template.domain.enums import FAMILY_LABELS, Family, Tier


def _signature() -> list[Template]:
    return [item for item in TEMPLATE_BLUEPRINTS if item.family is Family.STORY_SIGNATURE]


def test_doc_ban_moi_du_sau_mau_mien_phi() -> None:
    items = _signature()
    originals = [item for item in items if item.key in ORIGINAL_TEMPLATE_KEYS]
    assert [item.key for item in originals] == list(ORIGINAL_TEMPLATE_KEYS)
    assert len(originals) == 6
    assert all(item.tier is Tier.FREE for item in originals)
    assert FAMILY_LABELS[Family.STORY_SIGNATURE] == "Độc bản"


def test_mau_doc_ban_cu_chi_con_de_tuong_thich() -> None:
    legacy = [item for item in _signature() if item.key not in ORIGINAL_TEMPLATE_KEYS]
    assert len(legacy) == 12
    assert all(item.tier is Tier.PREMIUM for item in legacy)
    assert all(item.key.startswith("sg") for item in legacy)


def test_doc_ban_khong_trung_khoa_hay_ten_voi_mau_khac() -> None:
    keys = [item.key for item in TEMPLATE_BLUEPRINTS]
    names = [item.name for item in TEMPLATE_BLUEPRINTS]
    assert len(keys) == len(set(keys))
    assert len(names) == len(set(names))
