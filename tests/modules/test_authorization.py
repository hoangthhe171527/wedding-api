"""Phân quyền theo slug (403) và cô lập dữ liệu giữa hai xưởng (404, không phải 403)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import API, Session

ADMIN_ONLY = [
    ("GET", "/admin/users"),
    ("GET", "/admin/studios"),
    ("GET", "/roles"),
    ("PATCH", "/templates/uyenuong"),
]
#: Màn soạn thiệp — khách dùng mẫu và quản trị viên (toàn quyền, trên xưởng của mình).
STUDIO = [
    ("GET", "/wedding"),
    ("PUT", "/wedding/checklist"),
    ("GET", "/guests"),
    ("GET", "/photos"),
]


@pytest.mark.parametrize(("method", "path"), ADMIN_ONLY)
async def test_khach_dung_mau_bi_chan_khoi_man_quan_tri(
    client: AsyncClient, customer: Session, method: str, path: str
) -> None:
    response = await client.request(method, f"{API}{path}", headers=customer.headers, json={})
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


async def test_quan_tri_vien_chi_thay_xuong_cua_minh(
    client: AsyncClient, admin: Session, customer: Session
) -> None:
    """Admin toàn quyền nhưng dữ liệu vẫn theo xưởng: không bao giờ thấy thiệp của khách."""
    await client.post(f"{API}/wedding/setup", json={"mode": "sample"}, headers=customer.headers)
    mine = await client.get(f"{API}/guests", headers=customer.headers)
    assert mine.json()["data"], "khách có danh sách khách mẫu"

    wedding = await client.get(f"{API}/wedding", headers=admin.headers)
    assert wedding.status_code == 404
    assert wedding.json()["code"] == "wedding_not_setup"
    guests = await client.get(f"{API}/guests", headers=admin.headers)
    assert guests.status_code == 200
    assert guests.json()["data"] == []


@pytest.mark.parametrize(("method", "path"), ADMIN_ONLY + STUDIO)
async def test_chua_dang_nhap_tra_401(client: AsyncClient, method: str, path: str) -> None:
    response = await client.request(method, f"{API}{path}", json={})
    assert response.status_code == 401


async def test_ca_hai_vai_tro_xem_duoc_bo_mau(
    client: AsyncClient, admin: Session, customer: Session
) -> None:
    # 122 mẫu + 12 mẫu Độc bản; khách không thấy 26 mẫu đã cho nghỉ.
    for session, expected in ((admin, 134), (customer, 108)):
        response = await client.get(f"{API}/templates", headers=session.headers)
        assert response.status_code == 200
        assert len(response.json()["data"]) == expected


async def test_mau_da_tat_an_voi_khach_van_hien_voi_quan_tri(
    client: AsyncClient, admin: Session, customer: Session
) -> None:
    off = await client.patch(
        f"{API}/templates/noir", json={"is_active": False}, headers=admin.headers
    )
    assert off.status_code == 200
    seen_by_customer = await client.get(f"{API}/templates", headers=customer.headers)
    seen_by_admin = await client.get(f"{API}/templates", headers=admin.headers)
    assert "noir" not in {item["id"] for item in seen_by_customer.json()["data"]}
    assert "noir" in {item["id"] for item in seen_by_admin.json()["data"]}


async def test_khach_cua_xuong_khac_la_404(
    client: AsyncClient, customer: Session, other_customer: Session
) -> None:
    created = await client.post(
        f"{API}/guests", json={"name": "Bác Hùng", "group": "Họ hàng"}, headers=customer.headers
    )
    assert created.status_code == 201
    guest_id = created.json()["data"]["id"]

    # Xưởng B không thấy, không sửa, không xoá được — và nhận 404 chứ không 403.
    listed = await client.get(f"{API}/guests", headers=other_customer.headers)
    assert listed.json()["data"] == []
    patched = await client.patch(
        f"{API}/guests/{guest_id}", json={"sent": True}, headers=other_customer.headers
    )
    assert patched.status_code == 404
    deleted = await client.delete(f"{API}/guests/{guest_id}", headers=other_customer.headers)
    assert deleted.status_code == 404

    still = await client.get(f"{API}/guests", headers=customer.headers)
    assert still.json()["data"][0]["sent"] is False


async def test_man_giam_sat_khong_lo_noi_dung_khach(
    client: AsyncClient, admin: Session, customer: Session
) -> None:
    await client.post(f"{API}/wedding/setup", json={"mode": "sample"}, headers=customer.headers)
    response = await client.get(f"{API}/admin/studios", headers=admin.headers)
    assert response.status_code == 200
    rows = response.json()["data"]
    mine = next(row for row in rows if row["studio_id"] == customer.actor["studio"]["id"])
    assert mine["guests"] == 10
    assert set(mine) == {
        "studio_id",
        "couple",
        "slug",
        "published",
        "site_url",
        "main_date",
        "events",
        "guests",
        "updated_at",
    }
