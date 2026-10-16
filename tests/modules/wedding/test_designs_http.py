"""`PUT /wedding` mang `designs`; client cũ không gửi thì không mất design."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from tests.conftest import API, Session


async def _setup(client: AsyncClient, session: Session) -> dict[str, Any]:
    response = await client.post(
        f"{API}/wedding/setup", json={"mode": "blank"}, headers=session.headers
    )
    assert response.status_code == 201, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


def _content(data: dict[str, Any]) -> dict[str, Any]:
    drop = {"id", "slug", "published", "site_url", "checklist", "updated_at"}
    return {key: value for key, value in data.items() if key not in drop}


def _look(accent: str) -> dict[str, Any]:
    return {
        "theme": {"accent": accent},
        "card_design": {},
        "intro": "",
        "open_style": "",
        "music_url": "",
    }


async def test_luu_designs_va_truong_cu_theo_mau_chinh(
    client: AsyncClient, customer: Session
) -> None:
    content = _content(await _setup(client, customer))
    content["default_template"] = "daile"
    content["designs"] = {"daile": _look("#AA0000")}
    saved = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert saved.status_code == 200, saved.text
    data = saved.json()["data"]
    assert data["designs"]["daile"]["theme"]["accent"] == "#AA0000"
    assert data["theme"]["accent"] == "#AA0000"


async def test_luu_khong_gui_designs_giu_design_cu(client: AsyncClient, customer: Session) -> None:
    content = _content(await _setup(client, customer))
    content["default_template"] = "daile"
    content["designs"] = {"daile": _look("#AA0000")}
    first = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert first.status_code == 200, first.text
    # App cũ: không có khoá `designs`, đổi màu qua trường cũ.
    legacy = {key: value for key, value in content.items() if key != "designs"}
    legacy["theme"] = {"accent": "#00AA00"}
    second = await client.put(f"{API}/wedding", json=legacy, headers=customer.headers)
    assert second.status_code == 200, second.text
    data = second.json()["data"]
    assert data["designs"]["daile"]["theme"]["accent"] == "#00AA00"
    assert data["theme"]["accent"] == "#00AA00"


async def test_design_mau_khong_ton_tai_bi_tu_choi(client: AsyncClient, customer: Session) -> None:
    content = _content(await _setup(client, customer))
    content["designs"] = {"khong-co-mau-nay": _look("#AA0000")}
    response = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert response.status_code == 400
    assert "designs.khong-co-mau-nay" in response.json()["errors"]
