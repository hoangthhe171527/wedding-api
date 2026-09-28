"""Khách mời: nhập nhanh (hàm thuần) và các thao tác qua HTTP."""

from __future__ import annotations

from httpx import AsyncClient

from app.modules.guest.domain.enums import Side
from app.modules.guest.domain.services import generate_code, is_valid_code, parse_import
from tests.conftest import API, Session


def test_nhap_nhanh_doc_dung_dinh_dang_thiet_ke() -> None:
    drafts, skipped = parse_import(
        "Bác | Hùng | & gia đình | Họ hàng | trai | 4\n"
        "Chị\tMai Anh\t\tĐồng nghiệp\tgái\t1\n"
        " | Thu Trang | & người thương | nhóm lạ | GÁI | abc\n"
        "Chỉ có một cột\n"
        "\n"
    )
    assert skipped == 1
    assert [(d.title, d.name, d.group, d.side, d.count) for d in drafts] == [
        ("Bác", "Hùng", "Họ hàng", Side.TRAI, 4),
        ("Chị", "Mai Anh", "Đồng nghiệp", Side.GAI, 1),
        ("", "Thu Trang", "Bạn bè", Side.GAI, 1),
    ]


def test_ma_khach_sau_ky_tu() -> None:
    codes = {generate_code() for _ in range(200)}
    assert len(codes) == 200
    assert all(is_valid_code(code) for code in codes)


async def test_them_sua_xoa_khach(client: AsyncClient, customer: Session) -> None:
    created = await client.post(
        f"{API}/guests",
        json={"title": "Bác", "name": "Hùng", "plus": "& gia đình", "group": "Họ hàng", "count": 4},
        headers=customer.headers,
    )
    assert created.status_code == 201
    guest = created.json()["data"]
    assert is_valid_code(guest["code"])
    assert guest["status"] == {"slug": "none", "label": "Chưa phản hồi"}

    patched = await client.patch(
        f"{API}/guests/{guest['id']}",
        json={"sent": True, "status": "yes"},
        headers=customer.headers,
    )
    assert patched.json()["data"]["sent"] is True
    assert patched.json()["data"]["status"]["label"] == "Sẽ đến"
    assert patched.json()["data"]["name"] == "Hùng"

    deleted = await client.delete(f"{API}/guests/{guest['id']}", headers=customer.headers)
    assert deleted.status_code == 200
    listed = await client.get(f"{API}/guests", headers=customer.headers)
    assert listed.json()["meta"]["total"] == 0


async def test_khach_sai_nhom_hoac_sai_mau(client: AsyncClient, customer: Session) -> None:
    response = await client.post(
        f"{API}/guests",
        json={"name": "Ai đó", "group": "Nhóm lạ", "template": "khongco"},
        headers=customer.headers,
    )
    assert response.status_code == 400
    assert {"group", "template"} <= set(response.json()["errors"])


async def test_nhap_nhanh_qua_http(client: AsyncClient, customer: Session) -> None:
    response = await client.post(
        f"{API}/guests/import",
        json={"text": "Bác | Hùng | | Họ hàng | trai | 4\n | Thu Trang | | Bạn bè | gái | 2"},
        headers=customer.headers,
    )
    assert response.status_code == 201
    assert len(response.json()["data"]["created"]) == 2
    empty = await client.post(
        f"{API}/guests/import", json={"text": "khong co cot nao"}, headers=customer.headers
    )
    assert empty.status_code == 400
    assert empty.json()["code"] == "import_empty"
