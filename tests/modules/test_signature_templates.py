"""Dòng mẫu "Độc bản": nay chỉ còn để tương thích — mẫu duy nhất là `daile`."""

from __future__ import annotations

from app.modules.template.domain.catalog import (
    DOC_BAN_2026_KEYS,
    ORIGINAL_TEMPLATE_KEYS,
    RETIRED_KEYS,
    TEMPLATE_BLUEPRINTS,
)
from app.modules.template.domain.entities import Template
from app.modules.template.domain.enums import FAMILY_LABELS, Family, Tier


def _signature() -> list[Template]:
    return [item for item in TEMPLATE_BLUEPRINTS if item.family is Family.STORY_SIGNATURE]


def test_dai_le_la_mau_cung_dinh_mien_phi_duy_nhat() -> None:
    daile = next(item for item in TEMPLATE_BLUEPRINTS if item.key == "daile")
    assert "daile" in ORIGINAL_TEMPLATE_KEYS
    assert daile.family is Family.ROYAL
    assert daile.tier is Tier.FREE
    assert FAMILY_LABELS[Family.ROYAL] == "Cung đình lộng lẫy"


def test_doc_ban_2026_nghi_nhung_van_mien_phi() -> None:
    """Thiệp đã xuất bản bằng `db*` lưu lại vẫn không bị chặn vì hạng."""
    originals = [item for item in _signature() if item.key in DOC_BAN_2026_KEYS]
    assert [item.key for item in originals] == list(DOC_BAN_2026_KEYS)
    assert len(originals) == 6
    assert all(item.tier is Tier.FREE for item in originals)
    assert all(item.key in RETIRED_KEYS for item in originals)
    assert FAMILY_LABELS[Family.STORY_SIGNATURE] == "Độc bản"


def test_mau_doc_ban_cu_chi_con_de_tuong_thich() -> None:
    legacy = [item for item in _signature() if item.key not in DOC_BAN_2026_KEYS]
    assert len(legacy) == 12
    assert all(item.tier is Tier.PREMIUM for item in legacy)
    assert all(item.key.startswith("sg") for item in legacy)
    assert all(item.key in RETIRED_KEYS for item in legacy)


def test_doc_ban_khong_trung_khoa_hay_ten_voi_mau_khac() -> None:
    keys = [item.key for item in TEMPLATE_BLUEPRINTS]
    names = [item.name for item in TEMPLATE_BLUEPRINTS]
    assert len(keys) == len(set(keys))
    assert len(names) == len(set(names))
