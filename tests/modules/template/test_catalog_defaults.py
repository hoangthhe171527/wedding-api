"""Mặc định hệ thống: admin đặt mẫu theo nhóm khách + câu chữ theo giọng văn."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from tests.conftest import API, Session, buy_plan

DEFAULTS: dict[str, Any] = {
    "group_templates": {"Họ hàng": "songhy", "Bạn bè": "hongnhung"},
    "default_template": "ngoctrai",
    "wording": {"family": {"invite": "Trân trọng kính mời ", "announce": ""}},
    "messages": {"friends": "Tụi mình cưới rồi nè {khach}! {link}"},
}


async def test_admin_toan_quyen(client: AsyncClient, admin: Session) -> None:
    perms = set(admin.actor["permissions"])
    assert {"studio.manage", "guest.manage", "template.manage", "studio.oversee"} <= perms
    setup = await client.post(f"{API}/wedding/setup", json={"mode": "blank"}, headers=admin.headers)
    assert setup.status_code == 201, setup.text


async def test_luu_va_ap_mac_dinh(client: AsyncClient, admin: Session, customer: Session) -> None:
    denied = await client.put(f"{API}/templates/defaults", json=DEFAULTS, headers=customer.headers)
    assert denied.status_code == 403

    bad = await client.put(
        f"{API}/templates/defaults",
        json={
            "group_templates": {"Người lạ": "songhy", "Bạn bè": "khongco"},
            "wording": {"family": {"bank": "x"}},
        },
        headers=admin.headers,
    )
    assert bad.status_code == 400
    assert {"group_templates", "group_templates.Bạn bè", "wording.family"} <= set(
        bad.json()["errors"]
    )

    saved = await client.put(f"{API}/templates/defaults", json=DEFAULTS, headers=admin.headers)
    assert saved.status_code == 200, saved.text
    body = saved.json()["data"]
    assert body["wording"] == {"family": {"invite": "Trân trọng kính mời"}}, "ô trống bị bỏ"

    public = (await client.get(f"{API}/templates/defaults")).json()["data"]
    assert public["group_templates"]["Họ hàng"] == "songhy"

    # Xưởng mới nhận mẫu theo nhóm khách của hệ thống.
    created = await client.post(
        f"{API}/wedding/setup", json={"mode": "sample"}, headers=customer.headers
    )
    assert created.status_code == 201, created.text
    wedding = created.json()["data"]
    assert wedding["group_templates"]["Họ hàng"] == "songhy"
    assert wedding["group_templates"]["Bạn bè"] == "hongnhung"
    assert wedding["default_template"] == "ngoctrai"

    # Web thiệp nhận kèm câu chữ mặc định.
    await buy_plan(client, customer, "premium")
    await client.put(
        f"{API}/wedding/publication",
        json={"slug": "h-hoang-ha", "published": True},
        headers=customer.headers,
    )
    page = (await client.get(f"{API}/public/invitations/h-hoang-ha")).json()["data"]
    assert page["defaults"]["wording"]["family"]["invite"] == "Trân trọng kính mời"
    assert page["defaults"]["messages"]["friends"].startswith("Tụi mình")
