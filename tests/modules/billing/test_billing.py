"""Gói dịch vụ: bảng giá, mua / nâng gói, webhook ngân hàng, đối soát, xét gói khi xuất bản."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from tests.conftest import API, Session, buy_plan, guest_code

WEBHOOK_KEY = "local-dev-webhook-key"


@pytest.fixture
def online_payment() -> Iterator[None]:
    """Bật thanh toán trực tuyến (mặc định tắt: nâng gói qua tư vấn Zalo)."""
    settings = get_settings()
    before = settings.ONLINE_PAYMENT_ENABLED
    settings.ONLINE_PAYMENT_ENABLED = True
    yield
    settings.ONLINE_PAYMENT_ENABLED = before


async def _setup_sample(client: AsyncClient, session: Session) -> dict[str, Any]:
    response = await client.post(
        f"{API}/wedding/setup", json={"mode": "sample"}, headers=session.headers
    )
    assert response.status_code == 201, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


def _content(wedding: dict[str, Any]) -> dict[str, Any]:
    meta = {"id", "slug", "published", "site_url", "checklist", "updated_at"}
    return {key: value for key, value in wedding.items() if key not in meta}


async def _order(client: AsyncClient, session: Session, plan: str) -> dict[str, Any]:
    response = await client.post(
        f"{API}/billing/orders",
        json={"plan": plan, "method": "bank_transfer"},
        headers=session.headers,
    )
    assert response.status_code == 201, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


async def _bank(client: AsyncClient, payload: dict[str, Any], key: str = WEBHOOK_KEY) -> Any:
    return await client.post(
        f"{API}/billing/webhooks/bank", json=payload, headers={"Authorization": f"Apikey {key}"}
    )


async def test_cac_goi_cong_khai_khong_lo_gia(client: AsyncClient) -> None:
    response = await client.get(f"{API}/billing/plans")
    assert response.status_code == 200
    plans = {item["slug"]: item for item in response.json()["data"]}
    assert set(plans) == {"free", "standard", "premium"}
    assert all("price" not in item for item in plans.values()), "giá do tư vấn báo qua Zalo"
    assert "gate" in plans["premium"]["open_styles"]
    assert "gate" not in plans["standard"]["open_styles"]
    contact = (await client.get(f"{API}/billing/contact")).json()["data"]
    assert contact["zalo_url"].startswith("https://zalo.me/")


async def test_khach_moi_nang_goi_qua_zalo(client: AsyncClient, customer: Session) -> None:
    data = (await client.get(f"{API}/billing", headers=customer.headers)).json()["data"]
    assert data["plan"]["slug"] == "free"
    assert data["online_payment"] is False
    assert data["contact"]["zalo_phone"]
    blocked = await client.post(
        f"{API}/billing/orders",
        json={"plan": "premium", "method": "bank_transfer"},
        headers=customer.headers,
    )
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "contact_zalo"


async def test_quan_tri_cap_goi(client: AsyncClient, customer: Session, admin: Session) -> None:
    studio_id = customer.actor["studio"]["id"]
    forbidden = await client.post(
        f"{API}/admin/studios/{studio_id}/plan",
        json={"plan": "premium", "note": "tự cấp"},
        headers=customer.headers,
    )
    assert forbidden.status_code == 403
    no_note = await client.post(
        f"{API}/admin/studios/{studio_id}/plan",
        json={"plan": "premium", "note": "  "},
        headers=admin.headers,
    )
    assert no_note.status_code in {400, 422}
    granted = await client.post(
        f"{API}/admin/studios/{studio_id}/plan",
        json={"plan": "standard", "amount": 150_000, "note": "CK VCB, Zalo chị Lan"},
        headers=admin.headers,
    )
    assert granted.status_code == 201, granted.text
    assert granted.json()["data"]["amount"] == 150_000
    again = await client.post(
        f"{API}/admin/studios/{studio_id}/plan",
        json={"plan": "standard", "note": "lần hai"},
        headers=admin.headers,
    )
    assert again.status_code == 409
    plans = (
        await client.get(f"{API}/admin/studio-plans?ids={studio_id}", headers=admin.headers)
    ).json()["data"]
    assert plans == [{"studio_id": studio_id, "plan": {"slug": "standard", "label": "Gói Hỷ"}}]
    billing = (await client.get(f"{API}/billing", headers=customer.headers)).json()["data"]
    assert billing["plan"]["slug"] == "standard"


@pytest.mark.usefixtures("online_payment")
async def test_nang_goi_chi_tra_phan_chenh_lech(client: AsyncClient, customer: Session) -> None:
    await buy_plan(client, customer, "standard")
    billing = (await client.get(f"{API}/billing", headers=customer.headers)).json()["data"]
    assert billing["plan"]["slug"] == "standard"

    order = await _order(client, customer, "premium")
    assert order["amount"] == 300_000
    again = await _order(client, customer, "premium")
    assert again["code"] == order["code"], "bấm hai lần không được sinh hai mã chuyển khoản"

    owned = await client.post(
        f"{API}/billing/orders",
        json={"plan": "standard", "method": "bank_transfer"},
        headers=customer.headers,
    )
    assert owned.status_code == 409
    assert owned.json()["code"] == "plan_owned"


@pytest.mark.usefixtures("online_payment")
async def test_webhook_ngan_hang_kich_hoat_goi(client: AsyncClient, customer: Session) -> None:
    order = await _order(client, customer, "standard")
    code = order["code"]

    wrong = await _bank(client, {"id": 1, "content": code, "transferAmount": 199_000}, "sai")
    assert wrong.status_code == 401

    # Ngân hàng chèn tiền tố, khoảng trắng, chữ thường vào nội dung.
    messy = f"MBVCB.3312.{code[:5].lower()} {code[5:]}.CT tu 0123"
    underpaid = await _bank(client, {"id": 2, "content": messy, "transferAmount": 100_000})
    assert underpaid.json()["status"] == "underpaid"
    pending = await client.get(f"{API}/billing/orders/{order['id']}", headers=customer.headers)
    assert pending.json()["data"]["status"]["slug"] == "pending"

    paid = await _bank(client, {"id": 3, "content": messy, "transferAmount": 199_000})
    assert paid.status_code == 200
    assert paid.json()["status"] == "matched"
    done = await client.get(f"{API}/billing/orders/{order['id']}", headers=customer.headers)
    assert done.json()["data"]["status"]["slug"] == "paid"

    resent = await _bank(client, {"id": 3, "content": messy, "transferAmount": 199_000})
    assert resent.status_code == 200
    assert resent.json()["status"] == "duplicate"

    unmatched = await _bank(client, {"id": 4, "content": "chuyen tien", "transferAmount": 5})
    assert unmatched.json()["status"] == "unmatched"
    outgoing = await _bank(
        client, {"id": 5, "content": code, "transferAmount": 1, "transferType": "out"}
    )
    assert outgoing.json()["status"] == "ignored"

    billing = (await client.get(f"{API}/billing", headers=customer.headers)).json()["data"]
    assert billing["plan"]["slug"] == "standard"


@pytest.mark.usefixtures("online_payment")
async def test_doi_soat_cua_doi_van_hanh(
    client: AsyncClient, customer: Session, admin: Session
) -> None:
    order = await _order(client, customer, "premium")
    await _bank(client, {"id": 77, "content": "khong co ma", "transferAmount": 499_000})

    forbidden = await client.get(f"{API}/admin/orders", headers=customer.headers)
    assert forbidden.status_code == 403

    orders = (await client.get(f"{API}/admin/orders", headers=admin.headers)).json()["data"]
    assert any(item["code"] == order["code"] for item in orders)
    events = (await client.get(f"{API}/admin/payment-events", headers=admin.headers)).json()
    assert any(item["status"] == "unmatched" for item in events["data"])

    confirmed = await client.post(
        f"{API}/admin/orders/{order['id']}/confirm",
        json={"note": "Khách ghi sai nội dung, đã đối chiếu sao kê"},
        headers=admin.headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["data"]["status"]["slug"] == "paid"
    twice = await client.post(
        f"{API}/admin/orders/{order['id']}/confirm", json={"note": "lần hai"}, headers=admin.headers
    )
    assert twice.status_code == 409
    billing = (await client.get(f"{API}/billing", headers=customer.headers)).json()["data"]
    assert billing["plan"]["slug"] == "premium"


@pytest.mark.usefixtures("online_payment")
async def test_huy_don_cho_thanh_toan(client: AsyncClient, customer: Session) -> None:
    order = await _order(client, customer, "standard")
    cancelled = await client.post(
        f"{API}/billing/orders/{order['id']}/cancel", headers=customer.headers
    )
    assert cancelled.json()["data"]["status"]["slug"] == "cancelled"
    late = await _bank(client, {"id": 9, "content": order["code"], "transferAmount": 199_000})
    assert late.json()["status"] == "unmatched", "tiền về cho đơn đã huỷ phải đối soát tay"


@pytest.mark.usefixtures("online_payment")
async def test_don_cua_xuong_khac_tra_404(
    client: AsyncClient, customer: Session, other_customer: Session
) -> None:
    order = await _order(client, customer, "standard")
    response = await client.get(
        f"{API}/billing/orders/{order['id']}", headers=other_customer.headers
    )
    assert response.status_code == 404


async def test_webhook_tat_khi_khong_thanh_toan_online(client: AsyncClient) -> None:
    bank = await _bank(client, {"id": 1, "content": "TH0000000000", "transferAmount": 1})
    assert bank.status_code == 404
    momo = await client.post(f"{API}/billing/webhooks/momo", json={"orderId": "TH0000000000"})
    assert momo.status_code == 404


@pytest.mark.usefixtures("online_payment")
async def test_momo_ipn_sai_chu_ky_bi_tu_choi(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/billing/webhooks/momo",
        json={"orderId": "TH0000000000", "resultCode": 0, "amount": 1, "signature": "x"},
    )
    assert response.status_code == 401


async def test_xuat_ban_bi_chan_khi_vuot_goi(client: AsyncClient, customer: Session) -> None:
    await _setup_sample(client, customer)
    check = (await client.get(f"{API}/wedding/plan-check", headers=customer.headers)).json()
    data = check["data"]
    assert data["plan"] == "free"
    assert data["required"] == "premium"
    codes = {item["code"] for item in data["violations"]}
    assert {"template", "gift"} <= codes

    blocked = await client.put(
        f"{API}/wedding/publication",
        json={"slug": "h-hoang-ha", "published": True},
        headers=customer.headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "plan_required"
    assert blocked.json()["errors"]["plan"]

    await buy_plan(client, customer, "premium")
    after = (await client.get(f"{API}/wedding/plan-check", headers=customer.headers)).json()
    assert after["data"]["violations"] == []
    ok = await client.put(
        f"{API}/wedding/publication",
        json={"slug": "h-hoang-ha", "published": True},
        headers=customer.headers,
    )
    assert ok.status_code == 200


async def test_goi_mien_phi_xuat_ban_duoc_mau_co_dien(
    client: AsyncClient, customer: Session
) -> None:
    response = await client.post(
        f"{API}/wedding/setup", json={"mode": "blank"}, headers=customer.headers
    )
    content = _content(response.json()["data"])
    content["default_template"] = "songhy"
    content["group_templates"] = {}
    content["gift"]["show"] = False
    saved = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert saved.status_code == 200, saved.text
    await client.post(
        f"{API}/guests", json={"name": "Hùng", "title": "Bác"}, headers=customer.headers
    )
    published = await client.put(
        f"{API}/wedding/publication",
        json={"slug": "thiep-mien-phi", "published": True},
        headers=customer.headers,
    )
    assert published.status_code == 200, published.text

    guests = (await client.get(f"{API}/guests", headers=customer.headers)).json()["data"]
    code = guests[0]["code"]
    page = (await client.get(f"{API}/public/invitations/thiep-mien-phi?g={code}")).json()["data"]
    assert page["branding"]["badge"] is True
    assert page["guest"] is None, "gói Miễn phí: link nào cũng mở như link chung"


async def test_tuy_chinh_giao_dien(client: AsyncClient, customer: Session) -> None:
    wedding = await _setup_sample(client, customer)
    content = _content(wedding)
    content["theme"] = {"accent": "đỏ", "font_script": "Comic Sans", "ambient": "khói"}
    bad = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert bad.status_code == 400
    assert {"theme.accent", "theme.font_script", "theme.ambient"} <= set(bad.json()["errors"])

    content["theme"] = {"accent": "#B8323F", "font_script": "Great Vibes", "ambient": "petals"}
    good = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert good.status_code == 200, good.text
    assert good.json()["data"]["theme"]["accent"] == "#B8323F"
    check = (await client.get(f"{API}/wedding/plan-check", headers=customer.headers)).json()
    assert "theme" in {item["code"] for item in check["data"]["violations"]}

    content["theme"] = {"sections": ["gift", "gift"], "hidden": ["menu"], "intro": "red"}
    bad = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert {"theme.sections", "theme.hidden", "theme.intro"} <= set(bad.json()["errors"])
    content["theme"] = {
        "sections": ["events", "couple", "rsvp"],
        "hidden": ["gift"],
        "intro": "#1B3A5C",
        "intro2": "#E8C77A",
    }
    good = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert good.status_code == 200, good.text
    theme = good.json()["data"]["theme"]
    assert theme["sections"] == ["events", "couple", "rsvp"]
    assert theme["hidden"] == ["gift"]
    assert theme["intro"] == "#1B3A5C"


async def test_xac_nhan_tham_du_tren_thiep(client: AsyncClient, customer: Session) -> None:
    await _setup_sample(client, customer)
    await buy_plan(client, customer, "premium")
    await client.put(
        f"{API}/wedding/publication",
        json={"slug": "h-hoang-ha", "published": True},
        headers=customer.headers,
    )
    base = f"{API}/public/invitations/h-hoang-ha"
    code = await guest_code(client, customer)

    uncle = await client.post(
        f"{base}/rsvp",
        json={"g": code, "status": "yes", "count": 5, "message": "Chúc hai cháu trăm năm"},
    )
    assert uncle.status_code == 201, uncle.text
    assert uncle.json()["data"]["name"] == "Bác Hùng & gia đình"

    nameless = await client.post(f"{base}/rsvp", json={"status": "yes"})
    assert nameless.status_code == 400
    assert nameless.json()["code"] == "reply_name"
    stranger = await client.post(
        f"{base}/rsvp", json={"name": "Minh Anh", "status": "maybe", "message": ""}
    )
    assert stranger.status_code == 201

    guests = (await client.get(f"{API}/guests?per_page=500", headers=customer.headers)).json()
    hung = next(item for item in guests["data"] if item["code"] == code)
    assert hung["status"]["slug"] == "yes"
    assert hung["reply"]["count"] == 5
    assert hung["reply"]["message"] == "Chúc hai cháu trăm năm"

    wishes = (await client.get(f"{API}/guests/wishes", headers=customer.headers)).json()["data"]
    assert {item["name"] for item in wishes} == {"Bác Hùng & gia đình", "Minh Anh"}
    public = (await client.get(f"{base}/wishes")).json()["data"]
    assert [item["name"] for item in public] == ["Bác Hùng & gia đình"], "chỉ hiện dòng có lời chúc"

    removed = await client.delete(
        f"{API}/guests/wishes/{wishes[-1]['id']}", headers=customer.headers
    )
    assert removed.status_code == 200
    assert (await client.get(f"{base}/wishes")).json()["data"] == []


async def test_thiep_tu_thiet_ke(client: AsyncClient, customer: Session) -> None:
    wedding = await _setup_sample(client, customer)
    content = _content(wedding)
    content["card_design"] = {
        "enabled": True,
        "base": "khong-co",
        "layers": [
            {"id": "a", "kind": "field", "field": "sai", "color": "đỏ"},
            {"id": "a", "kind": "decor", "decor": "rong", "size": 99},
        ],
    }
    bad = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert bad.status_code == 400
    assert {
        "card_design.base",
        "card_design.layers.0.field",
        "card_design.layers.0.color",
        "card_design.layers.1.id",
        "card_design.layers.1.decor",
        "card_design.layers.1.size",
    } <= set(bad.json()["errors"])

    content["card_design"] = {
        "enabled": True,
        "base": "songhy",
        "layers": [
            {
                "id": "names",
                "kind": "field",
                "field": "couple",
                "font": "script",
                "size": 9,
                "color": "accent",
                "foil": True,
                "x": 8,
                "y": 30,
                "w": 84,
                "h": 16,
            },
            {"id": "hy", "kind": "decor", "decor": "hy-seal", "x": 40, "y": 8, "w": 20, "h": 14},
            {
                "id": "note",
                "kind": "text",
                "text": "Trân trọng kính mời {khach}",
                "color": "#B8323F",
            },
        ],
    }
    good = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert good.status_code == 200, good.text
    saved = good.json()["data"]["card_design"]
    assert [layer["id"] for layer in saved["layers"]] == ["names", "hy", "note"]
    assert saved["layers"][0]["foil"] is True

    await buy_plan(client, customer, "standard")
    check = (await client.get(f"{API}/wedding/plan-check", headers=customer.headers)).json()
    assert "design" in {item["code"] for item in check["data"]["violations"]}


async def test_ghi_nhan_khach_da_mo_thiep(client: AsyncClient, customer: Session) -> None:
    await _setup_sample(client, customer)
    await buy_plan(client, customer, "premium")
    await client.put(
        f"{API}/wedding/publication",
        json={"slug": "h-hoang-ha", "published": True},
        headers=customer.headers,
    )
    base = f"{API}/public/invitations/h-hoang-ha"
    code = await guest_code(client, customer)
    for _ in range(2):
        opened = await client.post(f"{base}/open", json={"g": code})
        assert opened.status_code == 204, opened.text
    # Mã không có thật cũng 204 — không để dò mã.
    assert (await client.post(f"{base}/open", json={"g": "zzzzzz"})).status_code == 204

    guests = (await client.get(f"{API}/guests?page_size=100", headers=customer.headers)).json()
    uncle = next(item for item in guests["data"] if item["code"] == code)
    assert uncle["opens"]["count"] == 2
    assert uncle["opens"]["first_at"] <= uncle["opens"]["last_at"]
    other = next(item for item in guests["data"] if item["code"] != code)
    assert other["opens"] is None


async def test_cap_goi_cho_xuong_khong_ton_tai_bi_tu_choi(
    client: AsyncClient, admin: Session
) -> None:
    response = await client.post(
        f"{API}/admin/studios/01930000-0000-7000-8000-0000deadbeef/plan",
        json={"plan": "premium", "amount": 0, "note": "gõ nhầm id"},
        headers=admin.headers,
    )
    assert response.status_code == 404
    assert response.json()["code"] == "studio_not_found"


async def test_nhat_ky_ghi_thao_tac_quan_tri(
    client: AsyncClient, customer: Session, admin: Session
) -> None:
    studio = customer.actor["studio"]["id"]
    await client.post(
        f"{API}/admin/studios/{studio}/plan",
        json={"plan": "standard", "amount": 199000, "note": "CK Vietcombank 12/10"},
        headers=admin.headers,
    )
    denied = await client.get(f"{API}/admin/audit-events", headers=customer.headers)
    assert denied.status_code == 403
    events = (
        await client.get(f"{API}/admin/audit-events?studio_id={studio}", headers=admin.headers)
    ).json()["data"]
    granted = next(item for item in events if item["action"] == "plan.granted")
    assert granted["details"]["note"] == "CK Vietcombank 12/10"
    assert granted["actor_id"] == admin.actor["user"]["id"]
    assert granted["request_id"]
