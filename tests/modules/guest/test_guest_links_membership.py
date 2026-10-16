"""Khách thuộc một link (spec §5.3): gán, chuyển hàng loạt, thống kê, xoá link."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from httpx import AsyncClient

from app.modules.guest import build_guest_usage_reader
from app.modules.guest.infrastructure.persistence.models import GuestDocument, InviteLinkDocument
from tests.conftest import API, Session

GUESTS = f"{API}/guests"
LINKS = f"{API}/guests/links"


async def _link(client: AsyncClient, session: Session, name: str) -> dict[str, Any]:
    response = await client.post(LINKS, json={"name": name}, headers=session.headers)
    assert response.status_code == 201, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


async def _guest(client: AsyncClient, session: Session, **body: Any) -> dict[str, Any]:
    response = await client.post(GUESTS, json={"name": "Bác Bình", **body}, headers=session.headers)
    assert response.status_code == 201, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


async def test_tao_khach_trong_link_va_thong_ke(client: AsyncClient, customer: Session) -> None:
    link = await _link(client, customer, "Họ hàng nhà trai")
    guest = await _guest(client, customer, link=link["id"])
    assert guest["link"] == link["id"]
    listed = (await client.get(LINKS, headers=customer.headers)).json()["data"]
    assert listed[0]["guest_count"] == 1
    assert listed[0]["reply_count"] == 0


async def test_link_khong_ton_tai_bi_tu_choi(client: AsyncClient, customer: Session) -> None:
    response = await client.post(
        GUESTS,
        json={"name": "A", "link": "0190a000-0000-7000-8000-000000000000"},
        headers=customer.headers,
    )
    assert response.status_code == 400
    assert "link" in response.json()["errors"]


async def test_chuyen_hang_loat(client: AsyncClient, customer: Session) -> None:
    first = await _link(client, customer, "Bạn bè")
    second = await _link(client, customer, "Đồng nghiệp")
    a = await _guest(client, customer, link=first["id"])
    b = await _guest(client, customer, name="Chị Lan")
    moved = await client.post(
        f"{GUESTS}/move-link",
        json={"guest_ids": [a["id"], b["id"]], "link": second["id"]},
        headers=customer.headers,
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["data"]["moved"] == 2
    rows = (await client.get(GUESTS, headers=customer.headers)).json()["data"]
    assert {row["link"] for row in rows} == {second["id"]}


async def test_xoa_link_tra_khach_ve_chua_xep(client: AsyncClient, customer: Session) -> None:
    link = await _link(client, customer, "Bạn bè")
    await _guest(client, customer, link=link["id"])
    deleted = await client.delete(f"{LINKS}/{link['id']}", headers=customer.headers)
    assert deleted.status_code == 200
    rows = (await client.get(GUESTS, headers=customer.headers)).json()["data"]
    assert rows[0]["link"] == ""


async def test_nhap_nhanh_cot_link_tao_link_moi(client: AsyncClient, customer: Session) -> None:
    existing = await _link(client, customer, "Bạn bè")
    text = "Anh | Minh Khoa |  | bạn bè | trai | 2\nChị | Thu Trang |  | Đồng nghiệp | gai | 1"
    response = await client.post(f"{GUESTS}/import", json={"text": text}, headers=customer.headers)
    assert response.status_code == 201, response.text
    created = response.json()["data"]["created"]
    links = {
        item["name"]: item["id"]
        for item in (await client.get(LINKS, headers=customer.headers)).json()["data"]
    }
    assert created[0]["link"] == existing["id"]  # khớp tên không phân biệt hoa thường
    assert created[1]["link"] == links["Đồng nghiệp"]  # tên mới -> link mới


async def test_link_cu_khong_con_khong_chan_sua_truong_khac(
    client: AsyncClient, customer: Session
) -> None:
    guest = await _guest(client, customer)
    dangling = "0190a000-0000-7000-8000-000000000000"
    await GuestDocument.get_motor_collection().update_one(
        {"_id": UUID(guest["id"])}, {"$set": {"link": dangling}}
    )
    response = await client.patch(
        f"{GUESTS}/{guest['id']}", json={"sent": True}, headers=customer.headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["sent"] is True
    moved = await client.patch(
        f"{GUESTS}/{guest['id']}", json={"link": dangling}, headers=customer.headers
    )
    assert moved.status_code == 400, "gán link không tồn tại vẫn bị chặn"


async def test_mau_dang_dung_chi_gom_mau_cua_link(client: AsyncClient, customer: Session) -> None:
    link = await _link(client, customer, "Bạn bè")
    await _guest(client, customer, link=link["id"])
    tenant = (await GuestDocument.find_one({})).tenant_id  # type: ignore[union-attr]
    await GuestDocument.get_motor_collection().update_many({}, {"$set": {"template": "noir"}})
    await InviteLinkDocument.get_motor_collection().update_many(
        {}, {"$set": {"template": "lienket"}}
    )
    usage = await build_guest_usage_reader().usage(tenant)
    assert usage["count"] == 1
    assert usage["templates"] == ["lienket"], "guest.template đã bỏ — không tính gói"
