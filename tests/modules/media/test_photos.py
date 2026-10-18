"""Ảnh cưới: tải lên, bỏ EXIF, làm bìa, URL đã ký, giới hạn."""

from __future__ import annotations

import io

from httpx import AsyncClient
from PIL import Image

from tests.conftest import API, Session


def _jpeg_with_gps(width: int = 2400, height: int = 1800) -> bytes:
    image = Image.new("RGB", (width, height), (200, 120, 90))
    exif = Image.Exif()
    exif[0x010F] = "Điện thoại của cô dâu"  # Make
    exif[0x8825] = {1: "N", 2: (21.0, 1.0, 30.0)}  # GPSInfo
    out = io.BytesIO()
    image.save(out, format="JPEG", exif=exif)
    return out.getvalue()


async def _upload(
    client: AsyncClient, session: Session, data: bytes, name: str = "a.jpg"
) -> list[dict[str, object]]:
    response = await client.post(
        f"{API}/photos", files={"file": (name, data, "image/jpeg")}, headers=session.headers
    )
    assert response.status_code == 201, response.text
    photos: list[dict[str, object]] = response.json()["data"]
    return photos


async def test_tai_anh_thu_nho_va_bo_exif(client: AsyncClient, customer: Session) -> None:
    photos = await _upload(client, customer, _jpeg_with_gps())
    assert len(photos) == 1
    assert photos[0]["is_cover"] is True
    assert max(int(str(photos[0]["width"])), int(str(photos[0]["height"]))) == 1600

    url = str(photos[0]["url"])
    path = url[url.index("/api/v1") :]
    served = await client.get(path)
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/jpeg"
    with Image.open(io.BytesIO(served.content)) as stored:
        assert not stored.getexif(), "EXIF (GPS) phải bị bỏ trước khi lên web công khai"


async def test_url_anh_sai_chu_ky_la_404(client: AsyncClient, customer: Session) -> None:
    photos = await _upload(client, customer, _jpeg_with_gps(400, 300))
    url = str(photos[0]["url"])
    path = url[url.index("/api/v1") :]
    tampered = path[:-4] + ("0000" if not path.endswith("0000") else "1111")
    assert (await client.get(tampered)).status_code == 404


async def test_lam_bia_dua_anh_len_dau(client: AsyncClient, customer: Session) -> None:
    await _upload(client, customer, _jpeg_with_gps(400, 300), "1.jpg")
    photos = await _upload(client, customer, _jpeg_with_gps(300, 400), "2.jpg")
    second = photos[1]["id"]
    covered = await client.post(f"{API}/photos/{second}/cover", headers=customer.headers)
    data = covered.json()["data"]
    assert data[0]["id"] == second
    assert data[0]["is_cover"] is True


async def test_doi_thu_tu_anh_va_anh_dau_thanh_bia(client: AsyncClient, customer: Session) -> None:
    await _upload(client, customer, _jpeg_with_gps(400, 300), "1.jpg")
    await _upload(client, customer, _jpeg_with_gps(300, 400), "2.jpg")
    photos = await _upload(client, customer, _jpeg_with_gps(500, 400), "3.jpg")
    ids = [str(item["id"]) for item in photos]

    response = await client.put(
        f"{API}/photos/order", json={"ids": [ids[2], ids[0], ids[1]]}, headers=customer.headers
    )

    assert response.status_code == 200, response.text
    ordered = response.json()["data"]
    assert [str(item["id"]) for item in ordered] == [ids[2], ids[0], ids[1]]
    assert ordered[0]["is_cover"] is True


async def test_can_trong_tam_anh(client: AsyncClient, customer: Session) -> None:
    photos = await _upload(client, customer, _jpeg_with_gps(400, 300))
    response = await client.patch(
        f"{API}/photos/{photos[0]['id']}/focus",
        json={"focus_x": 42, "focus_y": 88},
        headers=customer.headers,
    )
    assert response.status_code == 200, response.text
    focused = response.json()["data"][0]
    assert focused["focus_x"] == 42
    assert focused["focus_y"] == 88


async def test_khong_tai_trung_cung_mot_anh(client: AsyncClient, customer: Session) -> None:
    data = _jpeg_with_gps(400, 300)
    await _upload(client, customer, data, "1.jpg")
    response = await client.post(
        f"{API}/photos",
        files={"file": ("trung.jpg", data, "image/jpeg")},
        headers=customer.headers,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "photo_duplicate"


async def test_thay_anh_giu_nguyen_vi_tri_trong_album(
    client: AsyncClient, customer: Session
) -> None:
    first_album = await _upload(client, customer, _jpeg_with_gps(400, 300), "1.jpg")
    old_first = first_album[0]["id"]
    album = await _upload(client, customer, _jpeg_with_gps(300, 400), "2.jpg")
    old_second = album[1]["id"]

    response = await client.post(
        f"{API}/photos/{old_first}/replace",
        files={"file": ("moi.jpg", _jpeg_with_gps(500, 200), "image/jpeg")},
        headers=customer.headers,
    )

    assert response.status_code == 200, response.text
    replaced = response.json()["data"]
    assert len(replaced) == 2
    assert replaced[0]["id"] != old_first
    assert replaced[0]["is_cover"] is True
    assert replaced[1]["id"] == old_second


async def test_khong_the_thay_anh_cua_xuong_khac(
    client: AsyncClient, customer: Session, other_customer: Session
) -> None:
    photos = await _upload(client, customer, _jpeg_with_gps(400, 300))
    response = await client.post(
        f"{API}/photos/{photos[0]['id']}/replace",
        files={"file": ("moi.jpg", _jpeg_with_gps(300, 400), "image/jpeg")},
        headers=other_customer.headers,
    )
    assert response.status_code == 404


async def test_tep_khong_phai_anh_bi_tu_choi(client: AsyncClient, customer: Session) -> None:
    response = await client.post(
        f"{API}/photos",
        files={"file": ("x.jpg", b"day khong phai anh", "image/jpeg")},
        headers=customer.headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "photo_unreadable"


async def test_anh_xuong_khac_khong_xoa_duoc(
    client: AsyncClient, customer: Session, other_customer: Session
) -> None:
    photos = await _upload(client, customer, _jpeg_with_gps(400, 300))
    response = await client.delete(
        f"{API}/photos/{photos[0]['id']}", headers=other_customer.headers
    )
    assert response.status_code == 404
