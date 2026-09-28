"""Fixture dùng chung cho toàn bộ test.

Chạy trong container (`make test`) trên MongoDB và Redis thật — database
`wedding_test`, tách hẳn khỏi DB chạy thật. Mỗi test dọn sạch mọi collection và
mọi khoá Redis của hệ trước khi chạy, nên không test nào thấy dữ liệu của test
khác. Giả lập Mongo trong bộ nhớ luôn lệch hành vi ở index và aggregate — chọn
cách dọn dữ liệu, chậm hơn chút nhưng đúng với thực tế chạy.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.database import close_database, get_client, init_database
from app.core.redis import get_redis
from app.core.storage import get_object_store
from app.main import create_app
from app.models_registry import all_documents
from app.modules.access import build_ensure_default_roles
from app.modules.template import build_ensure_catalog
from app.modules.template.infrastructure.persistence.defaults_repository import (
    clear_defaults_cache,
)

API = "/api/v1"


@pytest.fixture(scope="session")
async def mongo_client() -> AsyncIterator[AsyncIOMotorClient[dict[str, Any]]]:
    """Client dùng chung của tiến trình — `transaction()` mở session trên nó."""
    client = get_client()
    yield client
    await close_database()


@pytest.fixture(scope="session")
async def database(
    mongo_client: AsyncIOMotorClient[dict[str, Any]],
) -> AsyncIterator[AsyncIOMotorDatabase[dict[str, Any]]]:
    """Database test, đã nối Beanie và tạo đủ index."""
    cfg = get_settings()
    db = mongo_client[cfg.effective_test_database]
    await init_database(database=db, documents=all_documents())
    # Ảnh của test ghi vào bucket riêng, không lẫn ảnh thật ở local.
    cfg.S3_BUCKET = cfg.effective_test_bucket
    await get_object_store().ensure_bucket()
    yield db
    await mongo_client.drop_database(cfg.effective_test_database)


@pytest.fixture(autouse=True)
async def clean_state(database: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
    """Dọn dữ liệu Mongo (giữ index) và khoá Redis của hệ trước mỗi test.

    Không có teardown: dữ liệu của test vừa chạy còn nguyên để soi khi test đỏ.
    Dọn Redis là bắt buộc: bộ đếm tần suất và danh sách thu hồi của test trước
    sẽ chặn nhầm test sau.
    """
    clear_defaults_cache()
    for name in await database.list_collection_names():
        if not name.startswith("system."):
            await database[name].delete_many({})
    redis = get_redis()
    keys = [key async for key in redis.scan_iter(match=f"{get_settings().REDIS_KEY_PREFIX}:*")]
    if keys:
        await redis.delete(*keys)


@pytest.fixture
async def catalog() -> None:
    """Vai trò mặc định + bộ mẫu — điều kiện để đăng ký và lưu thông tin cưới."""
    await build_ensure_default_roles().execute()
    await build_ensure_catalog().execute()


@pytest.fixture
async def client(catalog: None) -> AsyncIterator[AsyncClient]:
    """Client HTTP gọi thẳng ứng dụng ASGI (không qua mạng)."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@dataclass
class Session:
    """Một người dùng đã đăng nhập trong test."""

    access_token: str
    refresh_token: str
    actor: dict[str, Any]

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


async def register(client: AsyncClient, *, email: str, name: str = "Khách Thử") -> Session:
    """Đăng ký một khách dùng mẫu và trả phiên đăng nhập."""
    response = await client.post(
        f"{API}/auth/register",
        json={"full_name": name, "email": email, "password": "matkhau123"},
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    return Session(data["access_token"], data["refresh_token"], data["actor"])


async def login(client: AsyncClient, identifier: str, password: str) -> Session:
    response = await client.post(
        f"{API}/auth/login", json={"identifier": identifier, "password": password}
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    return Session(data["access_token"], data["refresh_token"], data["actor"])


async def buy_plan(client: AsyncClient, session: Session, plan: str = "premium") -> None:
    """Nâng gói qua đúng luồng thật: khách nhắn Zalo, quản trị cấp gói ở màn quản trị."""
    from app.seeds.seed import ADMIN_PASSWORD, ensure_admin

    await build_ensure_default_roles().execute()
    await ensure_admin()
    operator = await login(client, "admin@thiephy.vn", ADMIN_PASSWORD)
    granted = await client.post(
        f"{API}/admin/studios/{session.actor['studio']['id']}/plan",
        json={"plan": plan, "amount": 0, "note": "Khách nhắn Zalo, test"},
        headers=operator.headers,
    )
    assert granted.status_code == 201, granted.text


@pytest.fixture
async def customer(client: AsyncClient) -> Session:
    return await register(client, email="coupleA@example.com", name="Trần Huy Hoàng")


@pytest.fixture
async def other_customer(client: AsyncClient) -> Session:
    return await register(client, email="coupleB@example.com", name="Lê Minh Khang")


@pytest.fixture
async def admin(client: AsyncClient) -> Session:
    """Tài khoản quản trị tạo đúng như seed tạo."""
    from app.seeds.seed import ADMIN_PASSWORD, run_seed

    await run_seed()
    return await login(client, "admin@thiephy.vn", ADMIN_PASSWORD)


async def guest_code(client: AsyncClient, session: Session, name: str = "Hùng") -> str:
    """Mã link riêng của một khách mẫu (mã ngẫu nhiên — tra theo tên)."""
    response = await client.get(f"{API}/guests?per_page=500", headers=session.headers)
    guest = next(item for item in response.json()["data"] if item["name"] == name)
    return str(guest["code"])
