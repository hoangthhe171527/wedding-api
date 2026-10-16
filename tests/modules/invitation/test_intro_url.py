"""Video mở thiệp: thiệp chọn mặc định, link đối tượng đổi riêng, web thiệp nhận URL đã ký."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from app.modules.invitation.domain.services import effective_intro
from tests.conftest import API, Session, buy_plan
from tests.modules.guest.test_links import LINKS, _create
from tests.modules.template.test_intros import MP4, _upload
from tests.modules.test_production_guards import _content

A = "0193a8f0-0000-7000-8000-00000000000a"
#: Slug riêng: seed của fixture `admin` đã giữ slug thiệp mẫu.
PUBLIC = f"{API}/public/invitations/thiep-video"


async def _publish(client: AsyncClient, session: Session) -> None:
    setup = await client.post(
        f"{API}/wedding/setup", json={"mode": "sample"}, headers=session.headers
    )
    assert setup.status_code == 201, setup.text
    await buy_plan(client, session, "premium")
    published = await client.put(
        f"{API}/wedding/publication",
        json={"slug": "thiep-video", "published": True},
        headers=session.headers,
    )
    assert published.status_code == 200, published.text


async def _wedding(client: AsyncClient, session: Session) -> dict[str, Any]:
    data: dict[str, Any] = (await client.get(f"{API}/wedding", headers=session.headers)).json()[
        "data"
    ]
    return data


async def _set_intro(client: AsyncClient, session: Session, intro: str) -> dict[str, Any]:
    content = _content(await _wedding(client, session))
    content["intro"] = intro
    saved = await client.put(f"{API}/wedding", json=content, headers=session.headers)
    assert saved.status_code == 200, saved.text
    data: dict[str, Any] = saved.json()["data"]
    return data


def test_thu_tu_chon_video() -> None:
    assert effective_intro("w") == "w"
    assert effective_intro("none") == ""
    assert effective_intro("") == ""


async def test_luu_va_doc_video_cua_thiep(client: AsyncClient, customer: Session) -> None:
    await client.post(f"{API}/wedding/setup", json={"mode": "blank"}, headers=customer.headers)
    assert (await _wedding(client, customer))["intro"] == ""
    saved = await _set_intro(client, customer, A)
    assert saved["intro"] == A
    assert (await _wedding(client, customer))["intro"] == A
    # Không bắt video phải còn trong thư viện — chỉ kiểm đúng dạng id.
    content = _content(await _wedding(client, customer))
    content["intro"] = "khong-phai-id"
    bad = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert bad.status_code == 400
    assert "intro" in bad.json()["errors"]
    assert (await _set_intro(client, customer, ""))["intro"] == ""


async def test_link_chon_video_rieng(client: AsyncClient, customer: Session) -> None:
    plain = await _create(client, customer, name="Bạn đại học")
    assert plain["intro"] == ""
    off = await _create(client, customer, name="Đồng nghiệp", intro="none")
    assert off["intro"] == "none"
    own = await _create(client, customer, name="Họ hàng", intro=A)
    assert own["intro"] == A

    changed = await client.put(
        f"{LINKS}/{plain['id']}",
        json={"name": "Bạn đại học", "intro": "NONE"},
        headers=customer.headers,
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["data"]["intro"] == "none"
    bad = await client.post(LINKS, json={"name": "Lạ", "intro": "abc"}, headers=customer.headers)
    assert bad.status_code == 400
    assert "intro" in bad.json()["errors"]
    listed = (await client.get(LINKS, headers=customer.headers)).json()["data"]
    assert {item["name"]: item["intro"] for item in listed} == {
        "Bạn đại học": "none",
        "Đồng nghiệp": "none",
        "Họ hàng": A,
    }


async def test_web_thiep_nhan_url_video_theo_link(
    client: AsyncClient, admin: Session, customer: Session
) -> None:
    library = await _upload(client, admin, MP4, "a.mp4")
    library = await _upload(client, admin, MP4, "b.mp4")
    first, second = library[0]["id"], library[1]["id"]
    await _publish(client, customer)

    # Chưa chọn video: web thiệp dùng hiệu ứng cửa.
    page = (await client.get(PUBLIC)).json()["data"]
    assert page["wedding"]["intro_url"] == ""

    await _set_intro(client, customer, first)
    follow = await _create(client, customer, name="Theo thiệp")
    own = await _create(client, customer, name="Video riêng", intro=second)

    page = (await client.get(PUBLIC)).json()["data"]
    assert f"/media/intros/{first}?" in page["wedding"]["intro_url"]
    assert page["wedding"]["intro_url"].startswith("http")
    assert "intro" not in page["wedding"], "id video là dữ liệu nội bộ, chỉ URL lên trang"
    # Video theo design của mẫu: intro riêng của link không còn đè video của thiệp.
    for link in (follow, own):
        seen = (await client.get(f"{PUBLIC}?link={link['slug']}")).json()["data"]
        assert f"/media/intros/{first}?" in seen["wedding"]["intro_url"]

    # URL trên web thiệp phát được.
    url = page["wedding"]["intro_url"]
    played = await client.get(url[url.index("/api/v1") :], headers={"Range": "bytes=0-3"})
    assert played.status_code == 206

    # Video bị xoá khỏi thư viện: thiệp lùi về hiệu ứng cửa.
    await client.delete(f"{API}/intros/{first}", headers=admin.headers)
    page = (await client.get(PUBLIC)).json()["data"]
    assert page["wedding"]["intro_url"] == ""
    seen = (await client.get(f"{PUBLIC}?link={own['slug']}")).json()["data"]
    assert seen["wedding"]["intro_url"] == ""
