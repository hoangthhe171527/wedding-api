"""Beanie Document của `guest` — collection `guests`."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from pydantic import Field

from app.core.base_model import ASCENDING, Document, IndexModel, TenantScopedDocument


class GuestDocument(TenantScopedDocument):
    """Một thiệp mời. `code` là mã cuối link riêng của khách."""

    code: str
    name: str
    title: str = ""
    plus: str = ""
    group: str = "Bạn bè"
    side: str = "trai"
    events: list[str] = Field(default_factory=list)
    #: Số người của thiệp. KHÔNG đặt tên `count`: đè lên `Document.count()` của Beanie.
    party_size: int = 1
    template: str = ""
    status: str = "none"
    sent: bool = False
    note: str = ""
    #: Phản hồi khách tự gửi từ web thiệp; `replied_at` rỗng = chưa gửi.
    reply_count: int = 0
    reply_message: str = ""
    replied_at: datetime | None = None
    #: Lượt mở link riêng. Không đụng `updated_at`: mở thiệp không phải sửa khách.
    open_count: int = 0
    first_opened_at: datetime | None = None
    last_opened_at: datetime | None = None

    class Settings(TenantScopedDocument.Settings):
        name = "guests"
        indexes: ClassVar[list[IndexModel]] = [
            *TenantScopedDocument.Settings.indexes,
            # Duy nhất trong xưởng, KỂ CẢ khách đã xoá: mã cũ không được cấp lại
            # cho người khác — link đã gửi cho khách cũ sẽ mở ra tên người mới.
            IndexModel(
                [("tenant_id", ASCENDING), ("code", ASCENDING)],
                name="uq_guests_tenant_code",
                unique=True,
            ),
            IndexModel(
                [("tenant_id", ASCENDING), ("deleted_at", ASCENDING), ("created_at", ASCENDING)],
                name="ix_guests_tenant_order",
            ),
        ]


class WishDocument(TenantScopedDocument):
    """Một lời chúc / phản hồi gửi từ web thiệp."""

    name: str
    message: str = ""
    status: str = "none"
    party_size: int = 1
    guest_code: str = ""

    class Settings(TenantScopedDocument.Settings):
        name = "guest_wishes"
        indexes: ClassVar[list[IndexModel]] = [
            *TenantScopedDocument.Settings.indexes,
            IndexModel(
                [("tenant_id", ASCENDING), ("deleted_at", ASCENDING), ("created_at", ASCENDING)],
                name="ix_guest_wishes_tenant_order",
            ),
        ]


DOCUMENTS: list[type[Document]] = [GuestDocument, WishDocument]

__all__ = ["DOCUMENTS", "GuestDocument", "WishDocument"]
