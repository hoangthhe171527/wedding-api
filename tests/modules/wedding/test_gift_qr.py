"""Ảnh QR mừng cưới do cặp đôi tải lên: chỉ nhận ảnh raster, ẩn khi tắt hộp mừng cưới."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from app.modules.invitation.domain.services import public_wedding
from tests.conftest import API, Session
from tests.modules.test_production_guards import _content

PNG = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


async def _blank(client: AsyncClient, session: Session) -> dict[str, Any]:
    await client.post(f"{API}/wedding/setup", json={"mode": "blank"}, headers=session.headers)
    response = await client.get(f"{API}/wedding", headers=session.headers)
    return _content(response.json()["data"])


async def test_luu_anh_qr_png(client: AsyncClient, customer: Session) -> None:
    content = await _blank(client, customer)
    content["gift"] = {
        "show": True,
        "groom": {"bank": "Vietcombank", "number": "0123456789", "holder": "TRAN HUY", "qr": PNG},
        "bride": {"bank": "", "number": "", "holder": "", "qr": ""},
    }
    saved = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert saved.status_code == 200, saved.text
    assert saved.json()["data"]["gift"]["groom"]["qr"] == PNG


async def test_tu_choi_svg_va_link_ngoai(client: AsyncClient, customer: Session) -> None:
    content = await _blank(client, customer)
    for bad in ("data:image/svg+xml;base64,PHN2Zz4=", "https://example.com/qr.png"):
        content["gift"] = {
            "show": True,
            "groom": {"bank": "", "number": "", "holder": "", "qr": bad},
            "bride": {"bank": "", "number": "", "holder": "", "qr": ""},
        }
        saved = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
        assert saved.status_code == 400, bad
        assert "gift.groom.qr" in saved.json()["errors"]


def test_tat_hop_mung_cuoi_thi_bo_ca_anh_qr() -> None:
    account = {"bank": "VCB", "number": "1", "holder": "A", "qr": PNG}
    hidden = public_wedding({"gift": {"show": False, "groom": account, "bride": account}})
    assert hidden["gift"]["groom"]["qr"] == ""
    shown = public_wedding({"gift": {"show": True, "groom": account, "bride": account}})
    assert shown["gift"]["groom"]["qr"] == PNG
