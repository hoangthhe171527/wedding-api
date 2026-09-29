"""Link theo đối tượng: một link cho cả một nhóm người, mẫu thiệp riêng."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from app.modules.guest.domain.services import is_valid_link_slug, link_slug_from
from tests.conftest import API, Session, buy_plan, guest_code

LINKS = f"{API}/guests/links"
PUBLIC = f"{API}/public/invitations/h-hoang-ha"


async def _publish(client: AsyncClient, session: Session, plan: str | None = "premium") -> None:
    setup = await client.post(
        f"{API}/wedding/setup", json={"mode": "sample"}, headers=session.headers
    )
    assert setup.status_code == 201, setup.text
    if plan:
        await buy_plan(client, session, plan)
    published = await client.put(
        f"{API}/wedding/publication",
        json={"slug": "h-hoang-ha", "published": True},
        headers=session.headers,
    )
    assert published.status_code == 200, published.text


async def _create(client: AsyncClient, session: Session, **body: Any) -> dict[str, Any]:
    response = await client.post(LINKS, json=body, headers=session.headers)
    assert response.status_code == 201, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


def test_duoi_link_sinh_tu_ten_tieng_viet() -> None:
    assert link_slug_from("Đồng nghiệp công ty") == "dong-nghiep-cong-ty"
    assert link_slug_from("  Lớp 12A1 — THPT Chu Văn An ") == "lop-12a1-thpt-chu-van-an"
    assert is_valid_link_slug("ban-dai-hoc")
    assert not is_valid_link_slug("-dau-gach")
    assert not is_valid_link_slug("a")
    assert not is_valid_link_slug("co dau")
    assert not is_valid_link_slug("dong-nghiep~0193")


async def test_tao_sua_xoa_link(client: AsyncClient, customer: Session) -> None:
    first = await _create(client, customer, name="Đồng nghiệp công ty", template="noir")
    assert first["slug"] == "dong-nghiep-cong-ty"
    assert first["template"] == "noir"
    assert first["opens"] == 0
    # Tên trùng: đuôi tự sinh được đánh số tiếp, không báo lỗi.
    second = await _create(client, customer, name="Đồng nghiệp công ty")
    assert second["slug"] == "dong-nghiep-cong-ty-2"
    # Đuôi tự đặt mà trùng thì báo rõ.
    taken = await client.post(
        LINKS, json={"name": "Khác", "slug": "dong-nghiep-cong-ty"}, headers=customer.headers
    )
    assert taken.status_code == 409
    assert taken.json()["code"] == "link_slug_taken"

    updated = await client.put(
        f"{LINKS}/{second['id']}",
        json={"name": "Bạn đại học", "slug": "ban-dai-hoc", "template": "songhy"},
        headers=customer.headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["slug"] == "ban-dai-hoc"

    deleted = await client.delete(f"{LINKS}/{first['id']}", headers=customer.headers)
    assert deleted.status_code == 200
    listed = (await client.get(LINKS, headers=customer.headers)).json()["data"]
    assert [item["slug"] for item in listed] == ["ban-dai-hoc"]
    # Xoá xong thì đuôi được nhả: tạo lại link cùng đuôi được.
    again = await _create(client, customer, name="Đồng nghiệp công ty")
    assert again["slug"] == "dong-nghiep-cong-ty"


async def test_link_sai_du_lieu(client: AsyncClient, customer: Session) -> None:
    bad = await client.post(
        LINKS,
        json={"name": "  ", "slug": "Có Dấu", "template": "khongco"},
        headers=customer.headers,
    )
    assert bad.status_code == 400
    assert {"name", "slug", "template"} <= set(bad.json()["errors"])


async def test_link_cua_xuong_khac_khong_dung_duoc(
    client: AsyncClient, customer: Session, other_customer: Session
) -> None:
    mine = await _create(client, customer, name="Hàng xóm")
    assert (await client.get(LINKS, headers=other_customer.headers)).json()["data"] == []
    edit = await client.put(
        f"{LINKS}/{mine['id']}", json={"name": "Chiếm"}, headers=other_customer.headers
    )
    assert edit.status_code == 404
    gone = await client.delete(f"{LINKS}/{mine['id']}", headers=other_customer.headers)
    assert gone.status_code == 404


async def test_mo_link_doi_tuong_ra_dung_mau(client: AsyncClient, customer: Session) -> None:
    await _publish(client, customer)
    link = await _create(client, customer, name="Đồng nghiệp", template="noir")

    shared = (await client.get(PUBLIC)).json()["data"]
    audience = (await client.get(f"{PUBLIC}?link={link['slug']}")).json()["data"]
    assert audience["template"] == "noir"
    assert audience["link"] == link["slug"]
    assert audience["guest"] is None
    assert shared["template"] != "noir"
    assert shared["link"] == ""
    # Đuôi lạ mở như link chung, không báo lỗi (không cho dò đuôi nào có thật).
    unknown = (await client.get(f"{PUBLIC}?link=khong-co")).json()["data"]
    assert unknown["template"] == shared["template"]
    assert unknown["link"] == ""
    # Link riêng của khách vẫn được ưu tiên hơn link đối tượng.
    code = await guest_code(client, customer)
    both = (await client.get(f"{PUBLIC}?g={code}&link={link['slug']}")).json()["data"]
    assert both["guest"]["code"] == code
    assert both["template"] != "noir"


async def test_luot_mo_va_phan_hoi_ghi_theo_link(client: AsyncClient, customer: Session) -> None:
    await _publish(client, customer)
    link = await _create(client, customer, name="Bạn đại học", template="noir")
    for _ in range(3):
        opened = await client.post(f"{PUBLIC}/open", json={"link": link["slug"]})
        assert opened.status_code == 204, opened.text
    assert (await client.post(f"{PUBLIC}/open", json={"link": "khong-co"})).status_code == 204

    reply = await client.post(
        f"{PUBLIC}/rsvp",
        json={"link": link["slug"], "name": "Minh Anh", "status": "yes", "count": 2},
    )
    assert reply.status_code == 201, reply.text
    stranger = await client.post(
        f"{PUBLIC}/rsvp", json={"link": "bia-dat", "name": "Ai đó", "status": "maybe"}
    )
    assert stranger.status_code == 201

    listed = (await client.get(LINKS, headers=customer.headers)).json()["data"]
    assert listed[0]["opens"] == 3
    assert listed[0]["last_opened_at"]
    wishes = (await client.get(f"{API}/guests/wishes", headers=customer.headers)).json()["data"]
    by_name = {item["name"]: item["link"] for item in wishes}
    assert by_name == {"Minh Anh": link["slug"], "Ai đó": ""}


async def test_goi_mien_phi_link_doi_tuong_mo_nhu_link_chung(
    client: AsyncClient, customer: Session
) -> None:
    await _publish(client, customer, plan=None)
    link = await _create(client, customer, name="Đồng nghiệp", template="noir")
    page = (await client.get(f"{PUBLIC}?link={link['slug']}")).json()["data"]
    assert page["link"] == ""
    assert page["template"] != "noir"


async def test_mau_cua_link_tinh_vao_goi(client: AsyncClient, customer: Session) -> None:
    await client.post(f"{API}/wedding/setup", json={"mode": "sample"}, headers=customer.headers)
    await _create(client, customer, name="Đối tác", template="phaohoa")
    check = (await client.get(f"{API}/wedding/plan-check", headers=customer.headers)).json()
    subjects = {
        item["subject"] for item in check["data"]["violations"] if item["code"] == "template"
    }
    assert "phaohoa" in subjects


async def test_link_moi_rieng_va_chi_hien_tiec_duoc_moi(
    client: AsyncClient, customer: Session
) -> None:
    await _publish(client, customer)
    wedding = (await client.get(f"{API}/wedding", headers=customer.headers)).json()["data"]
    events = wedding["events"]
    assert len(events) > 1
    party = events[-1]["id"]
    link = await _create(
        client,
        customer,
        name="Đồng nghiệp",
        greeting="Quý đồng nghiệp",
        events=[party, party, "khong-co"],
    )
    assert link["greeting"] == "Quý đồng nghiệp"
    assert link["events"] == [party, "khong-co"]

    page = (await client.get(f"{PUBLIC}?link={link['slug']}")).json()["data"]
    assert page["greeting"] == "Quý đồng nghiệp"
    assert [item["id"] for item in page["wedding"]["events"]] == [party]
    shared = (await client.get(PUBLIC)).json()["data"]
    assert shared["greeting"] == ""
    assert len(shared["wedding"]["events"]) == len(events)

    # Lễ tiệc đã chọn bị xoá hết: thiệp vẫn hiện đủ, không bao giờ rỗng.
    gone = await client.put(
        f"{LINKS}/{link['id']}",
        json={"name": "Đồng nghiệp", "events": ["khong-co"]},
        headers=customer.headers,
    )
    assert gone.status_code == 200, gone.text
    page = (await client.get(f"{PUBLIC}?link={link['slug']}")).json()["data"]
    assert len(page["wedding"]["events"]) == len(events)


async def test_nguoi_duoc_moi_qua_dai(client: AsyncClient, customer: Session) -> None:
    long = await client.post(
        LINKS, json={"name": "Nhóm", "greeting": "x" * 121}, headers=customer.headers
    )
    assert long.status_code == 422
