"""Xưởng mới ở gói Miễn phí: lưu mẫu hay bắt đầu trống đều xuất bản được ngay.

Trước đây bản mẫu gán sẵn 7 mẫu trả phí + bật hộp mừng cưới: người dùng làm theo nút
gợi ý "Lưu dữ liệu mẫu" rồi bị chặn 8 lỗi ở đúng bước cuối.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import API, Session


async def _publish(client: AsyncClient, session: Session, slug: str) -> int:
    response = await client.put(
        f"{API}/wedding/publication",
        json={"slug": slug, "published": True},
        headers=session.headers,
    )
    return response.status_code


@pytest.mark.parametrize("mode", ["sample", "blank"])
async def test_setup_mien_phi_xuat_ban_duoc(
    client: AsyncClient, customer: Session, mode: str
) -> None:
    created = await client.post(
        f"{API}/wedding/setup", json={"mode": mode}, headers=customer.headers
    )
    assert created.status_code == 201, created.text

    check = (await client.get(f"{API}/wedding/plan-check", headers=customer.headers)).json()
    assert check["data"]["violations"] == [], check
    assert await _publish(client, customer, f"mien-phi-{mode}") == 200


async def test_mac_dinh_he_thong_vuot_goi_khong_ap_cho_xuong_mien_phi(
    client: AsyncClient, admin: Session, customer: Session
) -> None:
    saved = await client.put(
        f"{API}/templates/defaults",
        json={
            "group_templates": {"Họ hàng": "hongphuc", "Bạn bè": "hongnhung"},
            "default_template": "uyenuong",
        },
        headers=admin.headers,
    )
    assert saved.status_code == 200, saved.text

    created = await client.post(
        f"{API}/wedding/setup", json={"mode": "sample"}, headers=customer.headers
    )
    wedding = created.json()["data"]
    assert wedding["group_templates"]["Họ hàng"] == "hongphuc", "mẫu trong gói: vẫn nhận"
    assert wedding["group_templates"]["Bạn bè"] == "maudon", "mẫu vượt gói: giữ mẫu miễn phí"
    assert wedding["default_template"] == "ngoctrai"
    assert await _publish(client, customer, "mien-phi-mac-dinh") == 200
