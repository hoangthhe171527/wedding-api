"""Yêu cầu in thiệp: khách gửi, xem, huỷ; đội vận hành cập nhật tiến độ."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from tests.conftest import API, Session, build_ensure_default_roles, login

REQUEST: dict[str, Any] = {
    "quantity": 150,
    "paper": "my-thuat",
    "size": "5x7",
    "foil": True,
    "envelope": True,
    "contact_name": "Trần Huy Hoàng",
    "contact_phone": "0912 345 678",
    "address": "Số 88 Lạc Long Quân, Tây Hồ, Hà Nội",
    "note": "Ép nhũ vàng tên cô dâu chú rể",
}


async def _operator(client: AsyncClient) -> Session:
    from app.seeds.seed import ADMIN_PASSWORD, ensure_admin

    await build_ensure_default_roles().execute()
    await ensure_admin()
    return await login(client, "admin@thiephy.vn", ADMIN_PASSWORD)


async def test_khach_gui_va_huy_yeu_cau_in(
    client: AsyncClient, customer: Session, other_customer: Session
) -> None:
    options = (await client.get(f"{API}/printing/options")).json()["data"]
    assert {"my-thuat", "kraft"} <= {item["slug"] for item in options["papers"]}

    bad = await client.post(
        f"{API}/printing/requests",
        json={**REQUEST, "quantity": 2, "contact_phone": "123", "paper": "vang"},
        headers=customer.headers,
    )
    assert bad.status_code == 400
    assert {"quantity", "contact_phone", "paper"} <= set(bad.json()["errors"])

    created = await client.post(f"{API}/printing/requests", json=REQUEST, headers=customer.headers)
    assert created.status_code == 201, created.text
    body = created.json()["data"]
    assert body["status"]["slug"] == "new"
    assert body["contact_phone"] == "0912345678"
    assert body["studio_id"] is None

    mine = (await client.get(f"{API}/printing/requests", headers=customer.headers)).json()
    assert [item["id"] for item in mine["data"]] == [body["id"]]
    theirs = (await client.get(f"{API}/printing/requests", headers=other_customer.headers)).json()
    assert theirs["data"] == []
    stolen = await client.post(
        f"{API}/printing/requests/{body['id']}/cancel", headers=other_customer.headers
    )
    assert stolen.status_code == 404

    cancelled = await client.post(
        f"{API}/printing/requests/{body['id']}/cancel", headers=customer.headers
    )
    assert cancelled.json()["data"]["status"]["slug"] == "cancelled"


async def test_van_hanh_cap_nhat_tien_do(client: AsyncClient, customer: Session) -> None:
    created = (
        await client.post(f"{API}/printing/requests", json=REQUEST, headers=customer.headers)
    ).json()["data"]
    assert (
        await client.get(f"{API}/admin/print-requests", headers=customer.headers)
    ).status_code == 403

    operator = await _operator(client)
    listed = (await client.get(f"{API}/admin/print-requests", headers=operator.headers)).json()
    assert listed["data"][0]["studio_id"] == customer.actor["studio"]["id"]

    updated = await client.patch(
        f"{API}/admin/print-requests/{created['id']}",
        json={"status": "printing", "admin_note": "Đã báo giá qua Zalo, giao 5/11"},
        headers=operator.headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["status"]["label"] == "Đang in"

    locked = await client.post(
        f"{API}/printing/requests/{created['id']}/cancel", headers=customer.headers
    )
    assert locked.status_code == 409
    assert locked.json()["code"] == "print_locked"
    mine = (await client.get(f"{API}/printing/requests", headers=customer.headers)).json()
    assert mine["data"][0]["admin_note"] == "Đã báo giá qua Zalo, giao 5/11"
