"""Dữ liệu cho mẫu web thiệp kiểu kể chuyện: giờ đón khách, lịch trình, dress code, sổ lưu bút."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from tests.conftest import API, Session
from tests.modules.test_production_guards import _content, _publish_free


async def _wedding(client: AsyncClient, session: Session) -> dict[str, Any]:
    response = await client.get(f"{API}/wedding", headers=session.headers)
    data: dict[str, Any] = response.json()["data"]
    return data


async def test_mau_co_san_lich_trinh_va_gio_don_khach(
    client: AsyncClient, customer: Session
) -> None:
    await client.post(f"{API}/wedding/setup", json={"mode": "sample"}, headers=customer.headers)
    wedding = await _wedding(client, customer)
    assert [item["label"] for item in wedding["schedule"]][:2] == ["Đón khách", "Khai tiệc"]
    assert wedding["dress_code"]["note"]
    reception = next(e for e in wedding["events"] if e["id"] == "e4")
    assert reception["arrival"] == "17:30"


async def test_luu_va_kiem_lich_trinh_dress_code(client: AsyncClient, customer: Session) -> None:
    await client.post(f"{API}/wedding/setup", json={"mode": "blank"}, headers=customer.headers)
    content = _content(await _wedding(client, customer))
    content["schedule"] = [{"time": "18:00", "label": "  Khai tiệc  "}]
    content["dress_code"] = {"note": "Áo dài", "colors": ["#aa3344", "#FFFFFF"]}
    saved = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert saved.status_code == 200, saved.text
    data = saved.json()["data"]
    assert data["schedule"] == [{"time": "18:00", "label": "Khai tiệc"}]
    assert data["dress_code"] == {"note": "Áo dài", "colors": ["#AA3344", "#FFFFFF"]}

    content["schedule"] = [{"time": "25:00", "label": "x"}]
    content["dress_code"] = {"note": "", "colors": ["đỏ"]}
    bad = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert bad.status_code == 400
    assert {"schedule.0.time", "dress_code.colors.0"} <= set(bad.json()["errors"])


async def test_web_thiep_thay_lich_trinh_va_nhan_loi_chuc(
    client: AsyncClient, customer: Session
) -> None:
    content = await _publish_free(client, customer)
    content["schedule"] = [{"time": "18:00", "label": "Khai tiệc"}]
    assert (await client.put(f"{API}/wedding", json=content, headers=customer.headers)).is_success
    page = (await client.get(f"{API}/public/invitations/thiep-mien-phi")).json()["data"]
    assert page["wedding"]["schedule"] == [{"time": "18:00", "label": "Khai tiệc"}]

    sent = await client.post(
        f"{API}/public/invitations/thiep-mien-phi/wishes",
        json={"name": "Lan", "message": "Trăm năm hạnh phúc!"},
    )
    assert sent.status_code == 201, sent.text
    wishes = (await client.get(f"{API}/public/invitations/thiep-mien-phi/wishes")).json()["data"]
    assert wishes[0]["name"] == "Lan"
    assert wishes[0]["message"] == "Trăm năm hạnh phúc!"

    empty = await client.post(
        f"{API}/public/invitations/thiep-mien-phi/wishes", json={"name": "Lan", "message": ""}
    )
    assert empty.status_code in (400, 422)
