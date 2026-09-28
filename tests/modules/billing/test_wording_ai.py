"""Gợi ý câu chữ bằng AI: tắt khi chưa cấu hình, bật thì trả đúng ba phương án."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.modules.wedding.infrastructure import providers
from tests.conftest import API, Session


class FakeWriter:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    @property
    def enabled(self) -> bool:
        return True

    async def suggest(
        self, *, field: str, tone: str, facts: dict[str, str], current: str
    ) -> list[str]:
        self.calls.append({"field": field, "tone": tone, "facts": facts, "current": current})
        return ["Trân trọng kính mời", "Thân mời", "Hân hạnh kính mời"]


async def test_tat_khi_chua_co_khoa(client: AsyncClient, customer: Session) -> None:
    status = await client.get(f"{API}/wedding/wording/ai", headers=customer.headers)
    assert status.json()["data"]["enabled"] is False
    denied = await client.post(
        f"{API}/wedding/wording/suggest",
        json={"field": "invite", "tone": "family"},
        headers=customer.headers,
    )
    assert denied.status_code == 503
    assert denied.json()["code"] == "ai_disabled"


async def test_goi_y_khi_bat(
    client: AsyncClient, customer: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    await client.post(f"{API}/wedding/setup", json={"mode": "sample"}, headers=customer.headers)
    writer = FakeWriter()
    monkeypatch.setattr(providers, "build_wording_writer", lambda: writer)

    bad = await client.post(
        f"{API}/wedding/wording/suggest",
        json={"field": "bank", "tone": "family"},
        headers=customer.headers,
    )
    assert bad.status_code == 400
    good = await client.post(
        f"{API}/wedding/wording/suggest",
        json={"field": "invite", "tone": "friends"},
        headers=customer.headers,
    )
    assert good.status_code == 200, good.text
    assert len(good.json()["data"]["suggestions"]) == 3
    facts = writer.calls[0]["facts"]
    assert facts["chú rể"]
    assert facts["cô dâu"]
    assert not any("0912" in value for value in facts.values()), "không gửi số điện thoại"
