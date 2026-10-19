"""Web thiệp: mẫu theo link của khách, giao diện theo design của mẫu (spec §6)."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from app.modules.invitation.domain.services import apply_design, effective_template
from tests.conftest import API, Session, buy_plan, guest_code

PUBLIC = f"{API}/public/invitations/h-hoang-ha"


def test_thu_tu_chon_mau() -> None:
    pick = effective_template
    assert (
        pick(guest_link={"template": "a"}, url_link={"template": "b"}, default_template="d") == "a"
    )
    assert pick(guest_link=None, url_link={"template": "b"}, default_template="d") == "b"
    assert pick(guest_link={"template": ""}, url_link=None, default_template="d") == "d"
    assert pick(guest_link=None, url_link=None, default_template="") == "daile"


def test_mau_chua_design_khong_lay_theme_mau_chinh() -> None:
    snapshot = {
        "default_template": "daile",
        "theme": {"accent": "#AA0000"},
        "designs": {
            "daile": {
                "theme": {"accent": "#AA0000"},
                "card_design": {},
                "intro": "",
                "open_style": "",
                "music_url": "",
            }
        },
    }
    shown = apply_design(snapshot, "other")
    assert shown["theme"] == {}
    assert apply_design(snapshot, "daile")["theme"] == {"accent": "#AA0000"}


def test_mau_chinh_khoa_da_nghi_giu_giao_dien_cu() -> None:
    from app.modules.template.domain.catalog import canonical_template_key

    snapshot = {"default_template": "anhdao", "theme": {"accent": "#AA0000"}, "intro": "v"}
    assert canonical_template_key("anhdao") == "daile"
    shown = apply_design(snapshot, "daile", canonical_template_key)
    assert shown["theme"] == {"accent": "#AA0000"}
    stored = {**snapshot, "designs": {"anhdao": {"theme": {"accent": "#00AA00"}}}}
    assert apply_design(stored, "daile", canonical_template_key)["theme"] == {"accent": "#00AA00"}


async def _publish_with_link(client: AsyncClient, session: Session) -> dict[str, Any]:
    setup = await client.post(
        f"{API}/wedding/setup", json={"mode": "sample"}, headers=session.headers
    )
    assert setup.status_code == 201, setup.text
    await buy_plan(client, session, "premium")
    published = await client.put(
        f"{API}/wedding/publication",
        json={"slug": "h-hoang-ha", "published": True},
        headers=session.headers,
    )
    assert published.status_code == 200, published.text
    link = await client.post(
        f"{API}/guests/links", json={"name": "Họ hàng", "slug": "ho-hang"}, headers=session.headers
    )
    assert link.status_code == 201, link.text
    data: dict[str, Any] = link.json()["data"]
    return data


async def test_khach_trong_link_thay_loi_moi_va_le_tiec_cua_link(
    client: AsyncClient, customer: Session
) -> None:
    link = await _publish_with_link(client, customer)
    wedding = (await client.get(f"{API}/wedding", headers=customer.headers)).json()["data"]
    first_event = wedding["events"][0]["id"]
    await client.put(
        f"{API}/guests/links/{link['id']}",
        json={
            "name": "Họ hàng",
            "slug": "ho-hang",
            "greeting": "Quý họ hàng",
            "events": [first_event],
        },
        headers=customer.headers,
    )
    guest = await client.post(
        f"{API}/guests", json={"name": "Bác Bình", "link": link["id"]}, headers=customer.headers
    )
    code = guest.json()["data"]["code"]
    opened = (await client.get(f"{PUBLIC}?g={code}")).json()["data"]
    assert opened["link"] == "ho-hang"
    assert [event["id"] for event in opened["wedding"]["events"]] == [first_event]


async def test_khach_chua_xep_link_thay_mau_chinh(client: AsyncClient, customer: Session) -> None:
    await _publish_with_link(client, customer)
    code = await guest_code(client, customer)
    opened = await client.get(f"{PUBLIC}?g={code}")
    assert opened.status_code == 200, opened.text
    assert opened.json()["data"]["template"] == "daile"


def test_khung_anh_theo_design_cua_mau_dang_hien() -> None:
    from app.modules.invitation.domain.services import public_wedding

    look = {"theme": {}, "card_design": {}, "intro": "", "open_style": "", "music_url": ""}
    snapshot = {
        "default_template": "daile",
        "theme": {},
        "designs": {
            "daile": {**look, "photo_frame": "gold"},
            "other": {**look},
        },
    }
    assert public_wedding(apply_design(snapshot, "daile"))["photo_frame"] == "gold"
    assert apply_design(snapshot, "other")["photo_frame"] == "none"
    assert apply_design(snapshot, "chua-design")["photo_frame"] == "none"
