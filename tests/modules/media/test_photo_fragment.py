"""Hàm thuần: fragment URL của ảnh và miền giá trị chỉnh ảnh."""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest

from app.modules.media.domain.entities import Photo, PhotoAdjust, adjust_problem, clean_caption
from app.modules.media.domain.fragment import photo_fragment


def _photo(**adjust: object) -> Photo:
    return Photo(
        id=uuid4(),
        tenant_id=uuid4(),
        order=0,
        content_type="image/jpeg",
        size=1,
        width=10,
        height=10,
        focus_x=12.5,
        focus_y=80,
        adjust=PhotoAdjust(**adjust),  # type: ignore[arg-type]
    )


def test_anh_chua_chinh_chi_co_diem_can() -> None:
    assert photo_fragment(_photo()) == "focus=12.5,80"


def test_ghi_moi_khoa_khac_mac_dinh_theo_thu_tu_co_dinh() -> None:
    photo = _photo(
        zoom=2.25,
        rotate=90,
        flip=True,
        brightness=5,
        contrast=-3,
        saturation=10,
        warmth=-20,
        filter="nga",
        filter_strength=55,
        caption="Đà Lạt",
    )
    assert photo_fragment(photo) == (
        "focus=12.5,80&zoom=2.25&rot=90&flip=1&b=5&c=-3&s=10&w=-20&f=nga&fs=55"
        "&cap=%C4%90%C3%A0%20L%E1%BA%A1t"
    )


def test_cuong_do_bo_qua_khi_khong_co_bo_loc() -> None:
    assert photo_fragment(_photo(filter_strength=30)) == "focus=12.5,80"


@pytest.mark.parametrize(
    "changes",
    [
        {"zoom": 0.9},
        {"zoom": 3.01},
        {"rotate": 360},
        {"contrast": 70},
        {"saturation": -51},
        {"filter": "vintage"},
        {"filter_strength": -1},
        {"caption": "x" * 81},
    ],
)
def test_ngoai_mien_co_cau_bao_loi(changes: dict[str, object]) -> None:
    assert adjust_problem(replace(PhotoAdjust(), **changes)) is not None  # type: ignore[arg-type]


def test_bien_hop_le() -> None:
    assert adjust_problem(PhotoAdjust(zoom=3, rotate=270, brightness=-50, warmth=50)) is None
    assert adjust_problem(PhotoAdjust(filter="den", filter_strength=0, caption="x" * 80)) is None


def test_chu_thich_mot_dong() -> None:
    assert clean_caption("  Hồ \n Tây\tbuổi sớm ") == "Hồ Tây buổi sớm"
