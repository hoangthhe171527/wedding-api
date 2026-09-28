"""Luồng soạn thiệp: khởi tạo, lưu tự động, lộ trình, xuất bản, web thiệp công khai."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from tests.conftest import API, Session, buy_plan, guest_code


async def _setup(client: AsyncClient, session: Session, mode: str = "sample") -> dict[str, Any]:
    response = await client.post(
        f"{API}/wedding/setup", json={"mode": mode}, headers=session.headers
    )
    assert response.status_code == 201, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


async def test_xuong_moi_chua_co_thong_tin_cuoi(client: AsyncClient, customer: Session) -> None:
    response = await client.get(f"{API}/wedding", headers=customer.headers)
    assert response.status_code == 404
    assert response.json()["code"] == "wedding_not_setup"


async def test_luu_du_lieu_mau_kem_khach_mau(client: AsyncClient, customer: Session) -> None:
    wedding = await _setup(client, customer)
    assert wedding["groom"]["short"] == "Huy Hoàng"
    assert wedding["slug"] == "h-hoang-ha"
    assert wedding["published"] is False
    assert len(wedding["events"]) == 4

    guests = await client.get(f"{API}/guests?per_page=500", headers=customer.headers)
    codes = {item["code"] for item in guests.json()["data"]}
    assert len(codes) == 10
    assert "bh7k2m" not in codes, "mã mẫu cố định chỉ dành cho xưởng demo"

    again = await client.post(
        f"{API}/wedding/setup", json={"mode": "blank"}, headers=customer.headers
    )
    assert again.status_code == 409


async def test_slug_goi_y_trung_thi_them_hau_to(
    client: AsyncClient, customer: Session, other_customer: Session
) -> None:
    first = await _setup(client, customer)
    second = await _setup(client, other_customer)
    assert first["slug"] == "h-hoang-ha"
    assert second["slug"] == "h-hoang-ha-2"


async def test_bat_dau_trong(client: AsyncClient, customer: Session) -> None:
    wedding = await _setup(client, customer, "blank")
    assert wedding["events"] == []
    guests = await client.get(f"{API}/guests", headers=customer.headers)
    assert guests.json()["data"] == []


async def test_luu_noi_dung_khong_dong_toi_xuat_ban(client: AsyncClient, customer: Session) -> None:
    wedding = await _setup(client, customer)
    await client.put(
        f"{API}/wedding/checklist",
        json={"done": {"c1": True, "c99": True}},
        headers=customer.headers,
    )
    content = {
        k: v
        for k, v in wedding.items()
        if k not in {"id", "slug", "published", "site_url", "checklist", "updated_at"}
    }
    content["story"] = "Chuyện mới"
    saved = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert saved.status_code == 200
    data = saved.json()["data"]
    assert data["story"] == "Chuyện mới"
    assert data["checklist"] == {"c1": True}
    assert data["slug"] == "h-hoang-ha"


async def test_luu_noi_dung_sai_bao_loi_tung_truong(client: AsyncClient, customer: Session) -> None:
    await _setup(client, customer)
    response = await client.put(
        f"{API}/wedding",
        json={
            "default_template": "khong-co-mau-nay",
            "events": [{"id": "e1", "date": "2026-13-45", "time": "25:00"}],
            "rsvp": {"url": "javascript:alert(1)"},
        },
        headers=customer.headers,
    )
    assert response.status_code == 400
    errors = response.json()["errors"]
    assert {"default_template", "events.0.date", "events.0.time", "rsvp.url"} <= set(errors)


async def test_xuat_ban_va_mo_web_thiep(client: AsyncClient, customer: Session) -> None:
    await _setup(client, customer)
    code = await guest_code(client, customer)
    hidden = await client.get(f"{API}/public/invitations/h-hoang-ha?g={code}")
    assert hidden.status_code == 404
    await buy_plan(client, customer)

    published = await client.put(
        f"{API}/wedding/publication",
        json={"slug": "h-hoang-ha", "published": True},
        headers=customer.headers,
    )
    assert published.status_code == 200
    assert published.json()["data"]["site_url"].endswith("/invite/h-hoang-ha")

    # Khách có mẫu theo nhóm "Họ hàng" -> Song Hỷ Đỏ Son.
    uncle = (await client.get(f"{API}/public/invitations/h-hoang-ha?g={code}")).json()["data"]
    assert uncle["guest"]["name"] == "Hùng"
    assert uncle["template"] == "songhy"
    assert "note" not in uncle["guest"]
    assert "group" not in uncle["guest"]
    assert "messages" not in uncle["wedding"]
    assert "checklist" not in uncle["wedding"]

    # Khách có mẫu riêng.
    trang = await guest_code(client, customer, "Thu Trang")
    friend = (await client.get(f"{API}/public/invitations/h-hoang-ha?g={trang}")).json()["data"]
    assert friend["template"] == "xothom"

    # Mã sai: vẫn mở như link chung, không báo mã có thật hay không.
    general = await client.get(f"{API}/public/invitations/h-hoang-ha?g=zzzzzz")
    assert general.status_code == 200
    assert general.json()["data"]["guest"] is None
    assert general.json()["data"]["template"] == "ngoctrai"


async def test_tat_hop_mung_cuoi_thi_so_tai_khoan_khong_len_mang(
    client: AsyncClient, customer: Session
) -> None:
    wedding = await _setup(client, customer)
    content = {
        k: v
        for k, v in wedding.items()
        if k not in {"id", "slug", "published", "site_url", "checklist", "updated_at"}
    }
    content["gift"]["show"] = False
    await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    await buy_plan(client, customer)
    await client.put(
        f"{API}/wedding/publication",
        json={"slug": "h-hoang-ha", "published": True},
        headers=customer.headers,
    )
    data = (await client.get(f"{API}/public/invitations/h-hoang-ha")).json()["data"]
    assert data["wedding"]["gift"]["groom"]["number"] == ""
    assert "0123" not in str(data)


async def test_slug_da_co_chu_tra_409(
    client: AsyncClient, customer: Session, other_customer: Session
) -> None:
    await _setup(client, customer)
    await _setup(client, other_customer)
    await buy_plan(client, other_customer)
    taken = await client.put(
        f"{API}/wedding/publication",
        json={"slug": "h-hoang-ha", "published": True},
        headers=other_customer.headers,
    )
    assert taken.status_code == 409
    assert taken.json()["code"] == "slug_taken"
    reserved = await client.put(
        f"{API}/wedding/publication",
        json={"slug": "admin", "published": True},
        headers=other_customer.headers,
    )
    assert reserved.status_code == 400
