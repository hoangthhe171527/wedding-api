"""Bản nhỏ cho điện thoại: tạo lúc tải lên, đọc qua `&w=sm`, ảnh cũ chạy bù."""

from __future__ import annotations

import io
from typing import Any
from uuid import UUID

from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from PIL import Image

from app.core.storage import get_object_store
from app.modules.media.infrastructure.external.pillow_processor import SMALL_WIDTH
from app.seeds.backfill_photo_variants import backfill_photo_variants
from tests.conftest import API, Session
from tests.modules.media.test_photos import _jpeg_with_gps, _upload
from tests.modules.test_production_guards import _publish_free


def _path(url: object) -> str:
    text = str(url)
    return text[text.index("/api/v1") :]


def _width(data: bytes) -> int:
    with Image.open(io.BytesIO(data)) as image:
        assert not image.getexif(), "bản nhỏ cũng không được mang EXIF"
        return image.width


async def test_anh_lon_co_ban_nho(client: AsyncClient, customer: Session) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(2400, 1800)))[0]
    full = await client.get(_path(photo["url"]))
    small = await client.get(_path(photo["url"]) + "&w=sm")
    assert full.status_code == small.status_code == 200
    assert _width(full.content) == 1600
    assert _width(small.content) == SMALL_WIDTH
    assert len(small.content) < len(full.content)


async def test_web_thiep_tra_ca_ban_nho(client: AsyncClient, customer: Session) -> None:
    await _upload(client, customer, _jpeg_with_gps(2400, 1800))
    await _publish_free(client, customer)
    data = (await client.get(f"{API}/public/invitations/thiep-mien-phi")).json()["data"]
    assert len(data["photos_small"]) == len(data["photos"]) == 1
    assert data["photos_small"][0].endswith("&w=sm")


async def test_anh_cu_chua_co_ban_nho_van_doc_duoc_va_chay_bu(
    client: AsyncClient, customer: Session, database: AsyncIOMotorDatabase[dict[str, Any]]
) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(2400, 1800)))[0]
    photo_id = UUID(str(photo["id"]))
    meta = await database["photos"].find_one({"_id": photo_id})
    assert meta is not None
    assert meta["small_key"]
    # Dựng lại ảnh "đời cũ": chưa có bản nhỏ.
    await get_object_store().delete(meta["small_key"])
    await database["photos"].update_one({"_id": photo_id}, {"$set": {"small_key": ""}})

    fallback = await client.get(_path(photo["url"]) + "&w=sm")
    assert fallback.status_code == 200
    assert _width(fallback.content) == 1600, "chưa có bản nhỏ thì trả bản đầy đủ"

    summary = await backfill_photo_variants()
    assert summary["created"] == 1
    small = await client.get(_path(photo["url"]) + "&w=sm")
    assert _width(small.content) == SMALL_WIDTH
    assert (await backfill_photo_variants())["created"] == 0, "chạy lại không làm gì thêm"


async def test_anh_nho_san_khong_tao_ban_nho(
    client: AsyncClient, customer: Session, database: AsyncIOMotorDatabase[dict[str, Any]]
) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(600, 400)))[0]
    meta = await database["photos"].find_one({"_id": UUID(str(photo["id"]))})
    assert meta is not None
    assert meta["small_key"] == ""
    deleted = await client.delete(f"{API}/photos/{photo['id']}", headers=customer.headers)
    assert deleted.status_code in (200, 204)
