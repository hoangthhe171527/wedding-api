"""Ngữ cảnh người thực hiện — đi kèm mọi use case.

`ActorContext` là thứ duy nhất use case cần biết về "ai đang gọi". Router lấy nó
qua `Depends(get_actor)` rồi truyền xuống; use case tự lo phạm vi dữ liệu
(ARCHITECTURE §1.5: vi phạm phạm vi -> 404, không phải 403).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.core.permissions import Permission


@dataclass(frozen=True, slots=True)
class ActorContext:
    """Người dùng đã xác thực cùng phạm vi dữ liệu của họ.

    Attributes:
        user_id: Khoá chính của người dùng.
        tenant_id: Xưởng thiệp lấy từ token; MỌI truy vấn phải lọc theo trường này.
        permissions: Tập slug quyền đã giải quyết (xem `app.core.permissions`).
        session_id: `jti` của access token, dùng để thu hồi phiên.
    """

    user_id: UUID
    tenant_id: UUID
    permissions: frozenset[str] = field(default_factory=frozenset)
    session_id: UUID | None = None

    def has(self, slug: str) -> bool:
        """Actor có đúng quyền `slug` hay không."""
        return slug in self.permissions

    def has_any(self, *slugs: str) -> bool:
        """Actor có ít nhất một trong các quyền truyền vào."""
        return any(slug in self.permissions for slug in slugs)

    @property
    def is_operator(self) -> bool:
        """Actor giữ quyền quản trị hệ thống — dùng để ghi log, KHÔNG để phân quyền.

        Phân quyền luôn đi qua `require_permissions`; thuộc tính này chỉ để log
        phân biệt thao tác của đội vận hành với thao tác của khách.
        """
        return self.has_any(Permission.USER_MANAGE.value, Permission.STUDIO_OVERSEE.value)


__all__ = ["ActorContext"]
