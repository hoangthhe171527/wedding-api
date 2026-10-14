"""Thư viện video mở thiệp: tải lên, phân quyền, ẩn/hiện, sắp xếp, xoá, phát qua URL đã ký."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from app.modules.template.domain.intros import intro_name, sniff_video
from tests.conftest import API, Session

INTROS = f"{API}/intros"
#: MP4 tí hon: hộp `ftyp` ở byte 4..8 là đủ để nhận dạng.
MP4 = b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 4
WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 100


async def _upload(
    client: AsyncClient,
    session: Session,
    data: bytes = MP4,
    filename: str = "Cửa son.mp4",
    name: str | None = None,
) -> list[dict[str, Any]]:
    response = await client.post(
        INTROS,
        files={"file": (filename, data, "video/mp4")},
        data={"name": name} if name is not None else {},
        headers=session.headers,
    )
    assert response.status_code == 201, response.text
    items: list[dict[str, Any]] = response.json()["data"]
    return items


def _path(url: str) -> str:
    return url[url.index("/api/v1") :]


def test_nhan_dang_video_theo_byte_dau() -> None:
    assert sniff_video(MP4) == "video/mp4"
    assert sniff_video(WEBM) == "video/webm"
    assert sniff_video(b"\xff\xd8\xff\xe0 jpeg") is None
    assert sniff_video(b"") is None
    assert intro_name(None, "Cửa son đỏ.mp4") == "Cửa son đỏ"
    assert intro_name("  ", "") == "Video mở thiệp"
    assert len(intro_name("x" * 200, None)) == 80


async def test_quan_tri_tai_video_len(client: AsyncClient, admin: Session) -> None:
    first = await _upload(client, admin)
    assert len(first) == 1
    item = first[0]
    assert set(item) == {
        "id",
        "name",
        "url",
        "content_type",
        "size",
        "order",
        "is_active",
        "created_at",
    }
    assert item["name"] == "Cửa son"
    assert item["content_type"] == "video/mp4"
    assert item["size"] == len(MP4)
    assert item["order"] == 0
    assert item["is_active"] is True
    assert "/api/v1/media/intros/" in item["url"]
    assert "sig=" in item["url"]

    both = await _upload(client, admin, WEBM, "b.webm", name="  Hoa rơi  ")
    assert [entry["name"] for entry in both] == ["Cửa son", "Hoa rơi"]
    assert both[1]["order"] == 1
    assert both[1]["content_type"] == "video/webm"


async def test_tu_choi_tep_khong_phai_video(client: AsyncClient, admin: Session) -> None:
    bad = await client.post(
        INTROS,
        files={"file": ("gia.mp4", b"\xff\xd8\xff\xe0 khong phai video", "video/mp4")},
        headers=admin.headers,
    )
    assert bad.status_code == 400
    assert bad.json()["code"] == "intro_unsupported"
    empty = await client.post(
        INTROS, files={"file": ("rong.mp4", b"", "video/mp4")}, headers=admin.headers
    )
    assert empty.status_code == 400
    assert empty.json()["code"] == "intro_empty"


async def test_video_qua_lon(client: AsyncClient, admin: Session) -> None:
    from app.core.config import get_settings

    cfg = get_settings()
    original = cfg.INTRO_MAX_BYTES
    cfg.INTRO_MAX_BYTES = 200_000
    try:
        big = await client.post(
            INTROS,
            files={"file": ("lon.mp4", MP4 + b"\x00" * 200_000, "video/mp4")},
            headers=admin.headers,
        )
    finally:
        cfg.INTRO_MAX_BYTES = original
    assert big.status_code == 400
    assert big.json()["code"] == "intro_too_large"


async def test_khach_khong_duoc_quan_ly_thu_vien(
    client: AsyncClient, admin: Session, customer: Session
) -> None:
    items = await _upload(client, admin)
    upload = await client.post(
        INTROS, files={"file": ("a.mp4", MP4, "video/mp4")}, headers=customer.headers
    )
    assert upload.status_code == 403
    patch = await client.patch(
        f"{INTROS}/{items[0]['id']}", json={"name": "x"}, headers=customer.headers
    )
    assert patch.status_code == 403
    delete = await client.delete(f"{INTROS}/{items[0]['id']}", headers=customer.headers)
    assert delete.status_code == 403
    assert (await client.get(INTROS)).status_code == 401


async def test_video_da_tat_an_voi_khach_van_hien_voi_quan_tri(
    client: AsyncClient, admin: Session, customer: Session
) -> None:
    await _upload(client, admin, name="Một")
    items = await _upload(client, admin, name="Hai")
    off = await client.patch(
        f"{INTROS}/{items[0]['id']}", json={"is_active": False}, headers=admin.headers
    )
    assert off.status_code == 200, off.text
    assert [(i["name"], i["is_active"]) for i in off.json()["data"]] == [
        ("Một", False),
        ("Hai", True),
    ]
    seen = (await client.get(INTROS, headers=customer.headers)).json()["data"]
    assert [item["name"] for item in seen] == ["Hai"]
    managed = (await client.get(INTROS, headers=admin.headers)).json()["data"]
    assert [item["name"] for item in managed] == ["Một", "Hai"]


async def test_doi_ten_va_sap_xep(client: AsyncClient, admin: Session) -> None:
    await _upload(client, admin, name="Một")
    items = await _upload(client, admin, name="Hai")
    second = items[1]["id"]
    renamed = await client.patch(
        f"{INTROS}/{second}", json={"name": "  Hai mới ", "order": 0}, headers=admin.headers
    )
    assert renamed.status_code == 200, renamed.text
    moved = await client.patch(
        f"{INTROS}/{items[0]['id']}", json={"order": 5}, headers=admin.headers
    )
    assert [item["name"] for item in moved.json()["data"]] == ["Hai mới", "Một"]

    blank = await client.patch(f"{INTROS}/{second}", json={"name": ""}, headers=admin.headers)
    assert blank.status_code == 422
    missing = await client.patch(
        f"{INTROS}/0193a8f0-0000-7000-8000-000000000000", json={"name": "x"}, headers=admin.headers
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "intro_not_found"


async def test_xoa_video(client: AsyncClient, admin: Session) -> None:
    items = await _upload(client, admin)
    url = items[0]["url"]
    deleted = await client.delete(f"{INTROS}/{items[0]['id']}", headers=admin.headers)
    assert deleted.status_code == 200
    assert deleted.json()["data"] == []
    assert (await client.get(_path(url))).status_code == 404
    again = await client.delete(f"{INTROS}/{items[0]['id']}", headers=admin.headers)
    assert again.status_code == 404


async def test_phat_video_qua_url_da_ky_co_range(client: AsyncClient, admin: Session) -> None:
    items = await _upload(client, admin)
    path = _path(items[0]["url"])

    full = await client.get(path)
    assert full.status_code == 200
    assert full.content == MP4
    assert full.headers["content-type"] == "video/mp4"
    assert full.headers["accept-ranges"] == "bytes"
    assert full.headers["cache-control"] == "private, max-age=86400, immutable"
    assert full.headers["x-content-type-options"] == "nosniff"

    part = await client.get(path, headers={"Range": "bytes=0-1"})
    assert part.status_code == 206
    assert part.content == MP4[:2]
    assert part.headers["content-range"] == f"bytes 0-1/{len(MP4)}"
    assert part.headers["content-length"] == "2"

    tail = await client.get(path, headers={"Range": "bytes=-10"})
    assert tail.status_code == 206
    assert tail.content == MP4[-10:]

    rest = await client.get(path, headers={"Range": "bytes=100-"})
    assert rest.status_code == 206
    assert rest.content == MP4[100:]
    assert rest.headers["content-range"] == f"bytes 100-{len(MP4) - 1}/{len(MP4)}"

    clamp = await client.get(path, headers={"Range": f"bytes=10-{len(MP4) + 50}"})
    assert clamp.status_code == 206
    assert clamp.content == MP4[10:]

    for bad in (f"bytes={len(MP4)}-", "bytes=5-2", "items=0-1", "bytes=0-1,4-5", "bytes=-0"):
        refused = await client.get(path, headers={"Range": bad})
        assert refused.status_code == 416, bad
        assert refused.headers["content-range"] == f"bytes */{len(MP4)}"

    head = await client.head(path, headers={"Range": "bytes=0-9"})
    assert head.status_code == 206
    assert head.headers["content-length"] == "10"


async def test_video_da_tat_van_phat_sai_chu_ky_la_404(client: AsyncClient, admin: Session) -> None:
    items = await _upload(client, admin)
    path = _path(items[0]["url"])
    await client.patch(
        f"{INTROS}/{items[0]['id']}", json={"is_active": False}, headers=admin.headers
    )
    assert (await client.get(path)).status_code == 200

    tampered = path[:-4] + ("0000" if not path.endswith("0000") else "1111")
    assert (await client.get(tampered)).status_code == 404
    # Chữ ký của ảnh không mở được video (loại chữ ký khác nhau).
    from app.core.security import signing

    exp, sig = signing.sign("photo", items[0]["id"], ttl_seconds=600)
    photo_signed = f"{API}/media/intros/{items[0]['id']}?exp={exp}&sig={sig}"
    assert (await client.get(photo_signed)).status_code == 404
