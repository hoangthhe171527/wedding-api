"""Lớp nền Beanie (MongoDB) dùng chung cho mọi document của mọi module.

Quy ước bắt buộc (ARCHITECTURE §0.4): **mọi collection nghiệp vụ có `tenant_id`**
— ở đây tenant là một *Xưởng thiệp* (studio) — và mọi index bắt đầu bằng nó.

Document nghiệp vụ kế thừa `TenantScopedDocument` để có sẵn khoá chính UUIDv7,
`tenant_id`, dấu thời gian, vết kiểm toán và xoá mềm.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar, Self

import uuid6
from beanie import Document, Replace, Save, SaveChanges, Update, before_event
from pydantic import ConfigDict, Field
from pymongo import ASCENDING, DESCENDING, IndexModel


def new_id() -> uuid.UUID:
    """Sinh UUIDv7 (sắp thứ tự theo thời gian) — dạng id chuẩn của toàn hệ thống."""
    return uuid.UUID(str(uuid6.uuid7()))


def utc_now() -> datetime:
    """Thời điểm hiện tại, luôn kèm múi giờ UTC."""
    return datetime.now(UTC)


class BaseDocument(Document):
    """Document gốc: khoá chính UUIDv7 và dấu thời gian.

    Chỉ dùng trực tiếp khi collection thật sự phi-tenant (danh mục toàn hệ
    thống như bộ mẫu thiệp, vai trò) — trường hợp đó phải ghi rõ lý do trong
    docstring của document.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    # Thu hẹp kiểu `id` của Beanie xuống `UUID` là CHỦ Ý (ARCHITECTURE §1.6).
    id: uuid.UUID = Field(default_factory=new_id, alias="_id")  # type: ignore[assignment]
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @before_event(Replace, Save, SaveChanges, Update)
    def _touch_updated_at(self) -> None:
        """Cập nhật `updated_at` ở mọi đường ghi đè."""
        self.updated_at = utc_now()

    class Settings:
        """Cấu hình mặc định; document con ghi đè `name` và `indexes`."""

        use_state_management = True
        validate_on_save = True
        indexes: ClassVar[list[IndexModel]] = []


class TenantScopedDocument(BaseDocument):
    """Lớp cha của MỌI collection nghiệp vụ thuộc một Xưởng thiệp."""

    tenant_id: uuid.UUID
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None
    deleted_at: datetime | None = None
    deleted_by: uuid.UUID | None = None

    class Settings(BaseDocument.Settings):
        """Index nền: mọi truy vấn đều bắt đầu bằng `tenant_id`."""

        indexes: ClassVar[list[IndexModel]] = [
            IndexModel([("tenant_id", ASCENDING), ("deleted_at", ASCENDING)], name="ix_tenant"),
            IndexModel(
                [("tenant_id", ASCENDING), ("created_at", DESCENDING)],
                name="ix_tenant_created",
            ),
        ]

    # --- Xoá mềm ------------------------------------------------------------
    @property
    def is_deleted(self) -> bool:
        """Bản ghi đã bị xoá mềm hay chưa."""
        return self.deleted_at is not None

    def mark_deleted(self, actor_id: uuid.UUID | None = None) -> None:
        """Đánh dấu xoá mềm (không xoá vật lý)."""
        self.deleted_at = utc_now()
        self.deleted_by = actor_id

    # --- Vết kiểm toán ------------------------------------------------------
    def stamp_created(self, actor_id: uuid.UUID | None = None) -> Self:
        """Ghi vết người tạo (và người sửa lần đầu)."""
        if actor_id is not None:
            self.created_by = actor_id
            self.updated_by = actor_id
        return self

    def touch(self, actor_id: uuid.UUID | None = None) -> Self:
        """Ghi vết người sửa."""
        self.updated_at = utc_now()
        if actor_id is not None:
            self.updated_by = actor_id
        return self

    # --- Truy vấn -----------------------------------------------------------
    @classmethod
    def scoped(cls, tenant_id: uuid.UUID, *args: Any, **kwargs: Any) -> Any:
        """Query đã lọc tenant và bỏ bản ghi xoá mềm.

        Repository LUÔN vào bằng cửa này; gọi `find` trần là rò rỉ dữ liệu giữa
        các xưởng::

            await Guest.scoped(actor.tenant_id, Guest.side == "gai").to_list()
        """
        return cls.find({"tenant_id": tenant_id, "deleted_at": None}, *args, **kwargs)

    @classmethod
    async def get_scoped(cls, tenant_id: uuid.UUID, doc_id: uuid.UUID) -> Self | None:
        """Lấy một document theo id trong phạm vi tenant. Ngoài phạm vi -> None."""
        return await cls.find_one({"_id": doc_id, "tenant_id": tenant_id, "deleted_at": None})


__all__ = [
    "ASCENDING",
    "DESCENDING",
    "BaseDocument",
    "Document",
    "IndexModel",
    "TenantScopedDocument",
    "before_event",
    "new_id",
    "utc_now",
]
