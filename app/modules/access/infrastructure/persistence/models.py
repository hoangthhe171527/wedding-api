"""Beanie Document của `access` — hai collection: `roles`, `role_assignments`."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from pydantic import Field

from app.core.base_model import (
    ASCENDING,
    BaseDocument,
    Document,
    IndexModel,
    TenantScopedDocument,
)


class RoleDocument(BaseDocument):
    """Một vai trò của hệ thống.

    Ngoại lệ có chủ ý với §0.4 (không có `tenant_id`): vai trò ở sản phẩm này là
    danh mục toàn hệ thống — mọi xưởng dùng chung `admin`/`customer`. Chia vai
    trò theo xưởng chỉ sinh ra hàng nghìn bản sao y hệt nhau.

    `permissions` lưu slug trần: catalog quyền là hằng số của mã nguồn
    (`app.core.permissions`), đưa vào DB chỉ thêm một nguồn sự thật có thể lệch.
    """

    slug: str
    label: str
    permissions: list[str] = Field(default_factory=list)

    class Settings(BaseDocument.Settings):
        name = "roles"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel([("slug", ASCENDING)], name="uq_roles_slug", unique=True),
        ]


class RoleAssignmentDocument(TenantScopedDocument):
    """Gán một vai trò cho một người dùng trong một xưởng.

    Bảng nối riêng thay vì mảng nhúng trong `users`: gán/gỡ vai trò là thao tác
    của `access`, mà `access` không được ghi vào collection của `identity`.
    """

    user_id: UUID
    role_id: UUID

    class Settings(TenantScopedDocument.Settings):
        name = "role_assignments"
        indexes: ClassVar[list[IndexModel]] = [
            *TenantScopedDocument.Settings.indexes,
            IndexModel(
                [("tenant_id", ASCENDING), ("user_id", ASCENDING), ("role_id", ASCENDING)],
                name="uq_role_assignments_tenant_user_role",
                unique=True,
                partialFilterExpression={"deleted_at": None},
            ),
            # Ngoại lệ có chủ ý: màn quản trị tài khoản tra vai trò theo người,
            # xuyên xưởng — xem `RoleAssignmentRepository.list_for_users`.
            IndexModel([("user_id", ASCENDING)], name="ix_role_assignments_user"),
        ]


#: Bắt buộc — xem `app.models_registry`.
DOCUMENTS: list[type[Document]] = [RoleDocument, RoleAssignmentDocument]

__all__ = ["DOCUMENTS", "RoleAssignmentDocument", "RoleDocument"]
