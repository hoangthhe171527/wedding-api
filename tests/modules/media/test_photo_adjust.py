"""Chỉnh ảnh không phá huỷ: lưu, kiểm miền giá trị, mang tới web thiệp qua fragment."""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote, urlsplit
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import API, Session
from tests.modules.media.test_photos import _jpeg_with_gps, _upload
from tests.modules.test_production_guards import _publish_free


async def _adjust(
    client: AsyncClient, session: Session, photo_id: object, **body: Any
) -> dict[str, Any]:
    response = await client.patch(
        f"{API}/photos/{photo_id}/adjust", json=body, headers=session.headers
    )
    assert response.status_code == 200, response.text
    photo: dict[str, Any] = response.json()["data"][0]
    return photo


async def test_anh_moi_chua_chinh_gi(client: AsyncClient, customer: Session) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(400, 300)))[0]
    assert photo["zoom"] == 1
    assert photo["rotate"] == 0
    assert photo["flip"] is False
    assert [photo[key] for key in ("brightness", "contrast", "saturation", "warmth")] == [0] * 4
    assert photo["filter"] == "goc"
    assert photo["filter_strength"] == 100
    assert photo["caption"] == ""


async def test_luu_moi_truong_chinh_anh(client: AsyncClient, customer: Session) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(400, 300)))[0]
    saved = await _adjust(
        client,
        customer,
        photo["id"],
        focus_x=30,
        focus_y=70,
        zoom=1.6,
        rotate=90,
        flip=True,
        brightness=10,
        contrast=-5,
        saturation=20,
        warmth=-50,
        filter="phim",
        filter_strength=60,
        caption="  Đà Lạt,\n tháng 3  ",
    )
    assert (saved["focus_x"], saved["focus_y"]) == (30, 70)
    assert saved["zoom"] == 1.6
    assert saved["rotate"] == 90
    assert saved["flip"] is True
    assert (saved["brightness"], saved["contrast"], saved["saturation"], saved["warmth"]) == (
        10,
        -5,
        20,
        -50,
    )
    assert (saved["filter"], saved["filter_strength"]) == ("phim", 60)
    assert saved["caption"] == "Đà Lạt, tháng 3"

    listed = (await client.get(f"{API}/photos", headers=customer.headers)).json()["data"][0]
    assert listed["filter"] == "phim"
    assert listed["caption"] == "Đà Lạt, tháng 3"


async def test_chi_ghi_truong_duoc_gui(client: AsyncClient, customer: Session) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(400, 300)))[0]
    await _adjust(client, customer, photo["id"], brightness=12, caption="Ngày ăn hỏi")
    saved = await _adjust(client, customer, photo["id"], filter="den")
    assert saved["brightness"] == 12
    assert saved["caption"] == "Ngày ăn hỏi"
    assert saved["filter"] == "den"


@pytest.mark.parametrize(
    "body",
    [
        {"zoom": 0.5},
        {"zoom": 3.5},
        {"rotate": 45},
        {"brightness": 51},
        {"warmth": -51},
        {"filter": "sepia"},
        {"filter_strength": 101},
        {"focus_x": 120},
        {"caption": "a" * 200},
    ],
)
async def test_tu_choi_gia_tri_ngoai_mien(
    client: AsyncClient, customer: Session, body: dict[str, Any]
) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(400, 300)))[0]
    response = await client.patch(
        f"{API}/photos/{photo['id']}/adjust", json=body, headers=customer.headers
    )
    assert response.status_code in (400, 422), response.text
    listed = (await client.get(f"{API}/photos", headers=customer.headers)).json()["data"][0]
    assert listed["zoom"] == 1
    assert listed["filter"] == "goc"


async def test_chu_thich_qua_dai_sau_khi_gon_bi_tu_choi(
    client: AsyncClient, customer: Session
) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(400, 300)))[0]
    response = await client.patch(
        f"{API}/photos/{photo['id']}/adjust",
        json={"caption": "chữ " * 30},
        headers=customer.headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "photo_adjust_invalid"


async def test_anh_xuong_khac_hoac_khong_co_la_404(
    client: AsyncClient, customer: Session, other_customer: Session
) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(400, 300)))[0]
    other = await client.patch(
        f"{API}/photos/{photo['id']}/adjust", json={"zoom": 2}, headers=other_customer.headers
    )
    assert other.status_code == 404
    missing = await client.patch(
        f"{API}/photos/{uuid4()}/adjust", json={"zoom": 2}, headers=customer.headers
    )
    assert missing.status_code == 404


async def test_thay_anh_giu_mau_bo_loc_chu_thich_bo_cat_khung(
    client: AsyncClient, customer: Session
) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(400, 300)))[0]
    await _adjust(
        client,
        customer,
        photo["id"],
        zoom=2,
        rotate=180,
        flip=True,
        warmth=20,
        filter="nga",
        filter_strength=40,
        caption="Hồ Tây",
    )
    response = await client.post(
        f"{API}/photos/{photo['id']}/replace",
        files={"file": ("moi.jpg", _jpeg_with_gps(500, 400), "image/jpeg")},
        headers=customer.headers,
    )
    assert response.status_code == 200, response.text
    replaced = response.json()["data"][0]
    assert replaced["id"] != photo["id"]
    assert (replaced["zoom"], replaced["rotate"], replaced["flip"]) == (1, 0, False)
    assert replaced["warmth"] == 20
    assert (replaced["filter"], replaced["filter_strength"]) == ("nga", 40)
    assert replaced["caption"] == "Hồ Tây"


async def test_web_thiep_nhan_chinh_anh_trong_fragment(
    client: AsyncClient, customer: Session
) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(400, 300)))[0]
    await _adjust(
        client,
        customer,
        photo["id"],
        focus_x=25,
        focus_y=80,
        zoom=1.5,
        rotate=270,
        brightness=-10,
        filter="hoang",
        caption="Mùa hoa 'anh đào' & \"nắng\"",
    )
    await _publish_free(client, customer)
    data = (await client.get(f"{API}/public/invitations/thiep-mien-phi")).json()["data"]
    fragment = urlsplit(data["photos"][0]).fragment
    assert fragment.startswith("focus=25,80&")
    assert urlsplit(data["photos_small"][0]).fragment == fragment
    params = dict(part.split("=", 1) for part in fragment.split("&"))
    assert params["zoom"] == "1.5"
    assert params["rot"] == "270"
    assert params["b"] == "-10"
    assert params["f"] == "hoang"
    assert "fs" not in params, "cường độ mặc định không ghi vào fragment"
    assert "flip" not in params
    assert not set("'\"& ") & set(params["cap"]), "chú thích phải mã hoá hết ký tự đặc biệt"
    assert unquote(params["cap"]) == "Mùa hoa 'anh đào' & \"nắng\""


async def test_web_thiep_nhan_khung_anh_cua_mau(client: AsyncClient, customer: Session) -> None:
    content = await _publish_free(client, customer)
    wedding = (await client.get(f"{API}/wedding", headers=customer.headers)).json()["data"]
    main = wedding["default_template"]
    content["default_template"] = main
    content["designs"] = {
        key: {**look, "photo_frame": "polaroid" if key == main else look["photo_frame"]}
        for key, look in wedding["designs"].items()
    }
    saved = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert saved.status_code == 200, saved.text
    data = (await client.get(f"{API}/public/invitations/thiep-mien-phi")).json()["data"]
    assert data["wedding"]["photo_frame"] == "polaroid"
    assert "designs" not in data["wedding"]
