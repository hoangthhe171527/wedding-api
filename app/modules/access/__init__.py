"""Module `access` — vai trò, gán vai trò, giải tập quyền.

Sở hữu `roles` và `role_assignments`. Vai trò là DỮ LIỆU (ARCHITECTURE §0.1): mã
nghiệp vụ chỉ kiểm slug quyền, không bao giờ kiểm tên vai trò.

Barrel công bố hàm dựng cho module khác cắm vào cổng của họ — không module nào
được import Document của `access`.
"""

from app.modules.access.domain.role_blueprints import ADMIN_ROLE_SLUG, CUSTOMER_ROLE_SLUG
from app.modules.access.infrastructure.external.tenant_permissions import (
    build_tenant_permission_reader,
)
from app.modules.access.infrastructure.external.user_roles import build_user_role_reader
from app.modules.access.infrastructure.providers import (
    build_ensure_default_roles,
    build_grant_role,
    build_resolve_permissions,
)
from app.modules.access.interfaces.http.router import router

__all__ = [
    "ADMIN_ROLE_SLUG",
    "CUSTOMER_ROLE_SLUG",
    "build_ensure_default_roles",
    "build_grant_role",
    "build_resolve_permissions",
    "build_tenant_permission_reader",
    "build_user_role_reader",
    "router",
]
