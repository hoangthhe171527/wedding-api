"""Tài khoản quản trị không tính phí: dùng mọi mẫu, mọi tính năng và xuất bản như gói
cao nhất — nhờ quyền `plan.unlimited`, không phải nhờ một đơn hàng."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from tests.conftest import API, Session
from tests.modules.test_production_guards import _content

PAID_TEMPLATE = "stsonghyxanh"  # mẫu Story, hạng Gói Hỷ


async def _setup(client: AsyncClient, session: Session) -> dict[str, Any]:
    await client.post(f"{API}/wedding/setup", json={"mode": "blank"}, headers=session.headers)
    response = await client.get(f"{API}/wedding", headers=session.headers)
    return _content(response.json()["data"])


async def test_xuong_quan_tri_o_goi_cao_nhat_ma_khong_can_don(
    client: AsyncClient, admin: Session
) -> None:
    billing = (await client.get(f"{API}/billing", headers=admin.headers)).json()["data"]
    assert billing["plan"]["slug"] == "premium"
    assert not [order for order in billing["orders"] if order["status"] == "paid"]


async def test_quan_tri_xuat_ban_va_doi_sang_mau_tra_phi(
    client: AsyncClient, admin: Session
) -> None:
    content = await _setup(client, admin)
    published = await client.put(
        f"{API}/wedding/publication",
        json={"slug": "thiep-quan-tri", "published": True},
        headers=admin.headers,
    )
    assert published.status_code == 200, published.text

    content["default_template"] = PAID_TEMPLATE
    content["gift"]["show"] = True
    content["theme"] = {"accent": "#B8323F"}
    saved = await client.put(f"{API}/wedding", json=content, headers=admin.headers)
    assert saved.status_code == 200, saved.text

    check = (await client.get(f"{API}/wedding/plan-check", headers=admin.headers)).json()["data"]
    assert check["violations"] == []

    public = await client.get(f"{API}/public/invitations/thiep-quan-tri")
    assert public.json()["data"]["template"] == PAID_TEMPLATE


async def test_khach_thuong_van_bi_chan_mau_tra_phi(client: AsyncClient, customer: Session) -> None:
    content = await _setup(client, customer)
    await client.put(
        f"{API}/wedding/publication",
        json={"slug": "thiep-khach", "published": True},
        headers=customer.headers,
    )
    content["default_template"] = PAID_TEMPLATE
    blocked = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "plan_required"
