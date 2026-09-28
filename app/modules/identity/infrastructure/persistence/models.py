"""Beanie Document của `identity` — studios, users, auth_sessions.

Các index không bắt đầu bằng `tenant_id` (ngoại lệ §0.4) đều vì cùng một lý do:
**chúng được tra ở thời điểm chưa biết tenant**, tức trước khi có access token.

1. `uq_users_email` / `uq_users_phone` — đăng nhập chỉ có `identifier`. Duy nhất
   TOÀN CỤC: một con người là một tài khoản.
2. `uq_auth_sessions_refresh_hash` — `POST /auth/refresh` chỉ gửi chuỗi token.
3. `ix_auth_sessions_user` — "cắt mọi phiên của người này" là câu hỏi về con
   người (đổi mật khẩu, bị khoá, phát hiện trộm token).
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from app.core.base_model import (
    ASCENDING,
    DESCENDING,
    Document,
    IndexModel,
    TenantScopedDocument,
    new_id,
)


class StudioDocument(TenantScopedDocument):
    """Xưởng thiệp — gốc của mọi phạm vi dữ liệu.

    `tenant_id` của chính document này bằng `id` của nó, để `studios` vẫn là một
    collection tenant-scoped bình thường thay vì một trường hợp đặc biệt.
    """

    name: str
    is_active: bool = True

    class Settings(TenantScopedDocument.Settings):
        name = "studios"

    @classmethod
    def new(cls, *, name: str, studio_id: UUID | None = None) -> StudioDocument:
        """Dựng xưởng mới, giữ bất biến `tenant_id == id`."""
        identifier = studio_id or new_id()
        return cls(id=identifier, tenant_id=identifier, name=name)


class UserDocument(TenantScopedDocument):
    """Người dùng đăng nhập được. Phải có ít nhất email hoặc số điện thoại.

    Ràng buộc "một trong hai" nằm ở use case: Mongo không diễn đạt được bằng index.
    """

    full_name: str
    password_hash: str
    email: str | None = None
    phone: str | None = None
    is_active: bool = True
    last_login_at: datetime | None = None

    class Settings(TenantScopedDocument.Settings):
        name = "users"
        indexes: ClassVar[list[IndexModel]] = [
            *TenantScopedDocument.Settings.indexes,
            IndexModel(
                [("email", ASCENDING)],
                name="uq_users_email",
                unique=True,
                partialFilterExpression={"email": {"$type": "string"}},
            ),
            IndexModel(
                [("phone", ASCENDING)],
                name="uq_users_phone",
                unique=True,
                partialFilterExpression={"phone": {"$type": "string"}},
            ),
            # Màn quản trị tài khoản: mọi xưởng, mới nhất trước.
            IndexModel(
                [("deleted_at", ASCENDING), ("created_at", DESCENDING)], name="ix_users_recent"
            ),
        ]


class AuthSessionDocument(TenantScopedDocument):
    """Một phiên đăng nhập = một refresh token đang sống.

    DB chỉ lưu **bản băm** refresh token; lộ database không đồng nghĩa lộ token.
    Phiên đã thu hồi KHÔNG bị xoá: giữ lại để phát hiện việc dùng lại token cũ.
    """

    user_id: UUID
    refresh_token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None
    replaced_by: UUID | None = None
    user_agent: str | None = None
    ip: str | None = None

    class Settings(TenantScopedDocument.Settings):
        name = "auth_sessions"
        indexes: ClassVar[list[IndexModel]] = [
            *TenantScopedDocument.Settings.indexes,
            IndexModel(
                [("refresh_token_hash", ASCENDING)],
                name="uq_auth_sessions_refresh_hash",
                unique=True,
            ),
            IndexModel(
                [("user_id", ASCENDING), ("created_at", DESCENDING)],
                name="ix_auth_sessions_user",
            ),
            # Dọn rác: xoá phiên 7 ngày SAU khi hết hạn — giữ thêm một tuần để
            # vẫn phát hiện được hành vi dùng lại token vừa hết hạn.
            IndexModel(
                [("expires_at", ASCENDING)],
                name="ttl_auth_sessions_expired",
                expireAfterSeconds=604_800,
            ),
        ]


#: Bắt buộc — thiếu biến này thì Beanie không ánh xạ collection (xem models_registry).
DOCUMENTS: list[type[Document]] = [StudioDocument, UserDocument, AuthSessionDocument]

__all__ = ["DOCUMENTS", "AuthSessionDocument", "StudioDocument", "UserDocument"]
