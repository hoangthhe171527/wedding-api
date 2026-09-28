"""Kết nối MongoDB và khởi tạo Beanie.

Một client cho cả tiến trình. Motor tự quản pool nên KHÔNG tạo client mới cho mỗi
request — làm vậy sẽ nổ số kết nối.

Giao dịch (`transaction()`) cần Mongo chạy dạng replica set. `docker-compose.yml`
dựng replica set một nút (`rs0`); ở Mongo standalone thì tự lùi về ghi tuần tự.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_client: AsyncIOMotorClient[dict[str, Any]] | None = None
_database: AsyncIOMotorDatabase[dict[str, Any]] | None = None


def build_client(
    settings: Settings | None = None, *, url: str | None = None
) -> AsyncIOMotorClient[dict[str, Any]]:
    """Tạo client Motor mới."""
    cfg = settings or get_settings()
    return AsyncIOMotorClient(
        url or cfg.MONGODB_URL,
        uuidRepresentation="standard",
        maxPoolSize=cfg.MONGODB_MAX_POOL_SIZE,
        minPoolSize=cfg.MONGODB_MIN_POOL_SIZE,
        serverSelectionTimeoutMS=cfg.MONGODB_TIMEOUT_MS,
        tz_aware=True,
    )


def get_client() -> AsyncIOMotorClient[dict[str, Any]]:
    """Client dùng chung của tiến trình."""
    global _client
    if _client is None:
        _client = build_client()
    return _client


def get_database() -> AsyncIOMotorDatabase[dict[str, Any]]:
    """Database dùng chung của tiến trình."""
    global _database
    if _database is None:
        _database = get_client()[get_settings().MONGODB_DB]
    return _database


async def init_database(
    *,
    database: AsyncIOMotorDatabase[dict[str, Any]] | None = None,
    documents: list[type] | None = None,
) -> AsyncIOMotorDatabase[dict[str, Any]]:
    """Nối Beanie với danh sách document và đồng bộ index.

    Beanie tự tạo index khai báo trong `Settings.indexes` — thứ thay thế Alembic
    ở phía Mongo.
    """
    from app.models_registry import all_documents

    # PyMongo cấm `bool(Database)` nên phải so sánh None tường minh.
    db = database if database is not None else get_database()
    models = documents or all_documents()
    await init_beanie(database=db, document_models=models)
    await _drop_abstract_base_collections(db, models)
    log.info("database_ready", database=db.name)
    return db


async def _drop_abstract_base_collections(
    db: AsyncIOMotorDatabase[dict[str, Any]], models: list[type]
) -> None:
    """Xoá collection rác Beanie sinh ra cho lớp cha trừu tượng (chỉ khi RỖNG).

    Beanie tạo index cho cả lớp cha `TenantScopedDocument`, nên Mongo dựng hẳn
    một collection mang tên nó — không ai ghi vào nhưng nằm chình ình trong DB.
    """
    registered = set(models)
    abstract: set[str] = set()
    for model in models:
        for ancestor in model.__mro__[1:]:
            if ancestor is Document or not (
                isinstance(ancestor, type) and issubclass(ancestor, Document)
            ):
                continue
            if ancestor in registered:
                continue
            settings = getattr(ancestor, "Settings", None)
            abstract.add(str(getattr(settings, "name", None) or ancestor.__name__))

    existing = set(await db.list_collection_names())
    for name in sorted(abstract & existing):
        if await db[name].estimated_document_count() > 0:
            log.warning("abstract_base_collection_not_empty", collection=name)
            continue
        await db.drop_collection(name)


async def ping() -> bool:
    """Mongo có phản hồi hay không — dùng cho `/health`."""
    try:
        await get_client().admin.command("ping")
        return True
    except PyMongoError:
        return False


@asynccontextmanager
async def transaction() -> AsyncIterator[Any]:
    """Giao dịch nhiều thao tác. Cần replica set.

    Dùng khi một thao tác nghiệp vụ ghi vào nhiều collection::

        async with transaction() as session:
            await wedding.insert(session=session)
            await Guest.insert_many(guests, session=session)

    Mongo standalone không hỗ trợ giao dịch: ghi cảnh báo rồi chạy không giao
    dịch. Xác định topology TRƯỚC khi yield để mỗi lượt chỉ yield đúng một lần.
    """
    client = get_client()
    topology = await client.admin.command("hello")
    supports_transactions = bool(topology.get("setName")) or (topology.get("msg") == "isdbgrid")
    if not supports_transactions:
        log.warning("transaction_unsupported", reason="mongodb_standalone")
        yield None
        return

    async with await client.start_session() as session, session.start_transaction():
        yield session


async def close_database() -> None:
    """Đóng client khi tắt ứng dụng."""
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None


__all__ = [
    "build_client",
    "close_database",
    "get_client",
    "get_database",
    "init_database",
    "ping",
    "transaction",
]
