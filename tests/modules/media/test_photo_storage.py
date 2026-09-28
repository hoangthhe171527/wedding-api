"""Byte ảnh nằm ở kho object (MinIO / S3), Mongo chỉ giữ siêu dữ liệu."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.storage import get_object_store
from app.seeds.migrate_photos import migrate_photos
from tests.conftest import API, Session
from tests.modules.media.test_photos import _jpeg_with_gps, _upload


def _path(url: object) -> str:
    text = str(url)
    return text[text.index("/api/v1") :]


@pytest.fixture
def public_store() -> Iterator[None]:
    """Kho có địa chỉ công khai: URL ảnh chuyển hướng thẳng tới kho."""
    settings = get_settings()
    before = settings.S3_PUBLIC_URL
    settings.S3_PUBLIC_URL = "https://media.thiephy.test"
    get_object_store.cache_clear()
    yield
    settings.S3_PUBLIC_URL = before
    get_object_store.cache_clear()


async def test_anh_nam_o_kho_object_khong_o_mongo(
    client: AsyncClient, customer: Session, database: AsyncIOMotorDatabase[dict[str, Any]]
) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(400, 300)))[0]
    meta = await database["photos"].find_one({"_id": UUID(str(photo["id"]))})
    assert meta is not None
    assert meta["storage_key"] == f"photos/{customer.actor['studio']['id']}/{photo['id']}"
    assert await database["photo_blobs"].count_documents({}) == 0
    stored = await get_object_store().get(meta["storage_key"])
    assert stored is not None
    assert stored[:2] == b"\xff\xd8"

    deleted = await client.delete(f"{API}/photos/{photo['id']}", headers=customer.headers)
    assert deleted.status_code in (200, 204), deleted.text
    assert await get_object_store().get(meta["storage_key"]) is None


async def test_kho_cong_khai_thi_chuyen_huong(
    client: AsyncClient, customer: Session, public_store: None
) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(400, 300)))[0]
    served = await client.get(_path(photo["url"]))
    assert served.status_code == 302
    location = served.headers["location"]
    assert location.startswith("https://media.thiephy.test/")
    assert "X-Amz-Signature=" in location


async def test_chuyen_anh_cu_tu_mongo_sang_kho(
    client: AsyncClient, customer: Session, database: AsyncIOMotorDatabase[dict[str, Any]]
) -> None:
    photo = (await _upload(client, customer, _jpeg_with_gps(400, 300)))[0]
    photo_id = UUID(str(photo["id"]))
    meta = await database["photos"].find_one({"_id": photo_id})
    assert meta is not None
    data = await get_object_store().get(meta["storage_key"])
    # Dựng lại trạng thái trước khi có kho: byte trong `photo_blobs`, chưa có khoá.
    await get_object_store().delete(meta["storage_key"])
    await database["photos"].update_one({"_id": photo_id}, {"$set": {"storage_key": ""}})
    await database["photo_blobs"].insert_one(
        {
            "_id": photo_id,
            "tenant_id": meta["tenant_id"],
            "photo_id": photo_id,
            "content_type": "image/jpeg",
            "data": data,
            "deleted_at": None,
        }
    )
    assert (await client.get(_path(photo["url"]))).status_code == 200, "ảnh cũ vẫn đọc được"

    summary = await migrate_photos()
    assert summary["moved"] == 1
    assert await database["photo_blobs"].count_documents({}) == 0
    served = await client.get(_path(photo["url"]))
    assert served.status_code == 200
    assert served.content == data
