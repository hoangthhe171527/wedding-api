"""Router HTTP của `access`.

| Method | Path                 | Quyền yêu cầu     |
|--------|----------------------|-------------------|
| GET    | /api/v1/permissions  | chỉ cần đăng nhập |
| GET    | /api/v1/roles        | `user.manage`     |
| GET    | /api/v1/admin/audit-events | `studio.oversee` |
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query

from app.core import audit
from app.core.context import ActorContext
from app.core.dependencies import ActorDep, require_permissions
from app.core.permissions import PERMISSION_CATALOG, Permission
from app.core.responses import ResponseEnvelope, ok_list
from app.modules.access.infrastructure.providers import ListRolesDep
from app.modules.access.interfaces.http.schemas import AuditEventOut, PermissionOut, RoleOut

router = APIRouter(tags=["Phân quyền"])


@router.get(
    "/permissions",
    response_model=ResponseEnvelope[list[PermissionOut]],
    summary="Danh mục quyền",
)
async def list_permissions(actor: ActorDep) -> dict[str, Any]:
    """Danh mục quyền kèm nhãn tiếng Việt — client không hardcode nhãn."""
    del actor  # chỉ cần đăng nhập
    return ok_list([PermissionOut.of(item) for item in PERMISSION_CATALOG])


@router.get("/roles", response_model=ResponseEnvelope[list[RoleOut]], summary="Danh sách vai trò")
async def list_roles(
    actor: Annotated[ActorContext, require_permissions(Permission.USER_MANAGE)],
    use_case: ListRolesDep,
) -> dict[str, Any]:
    """Mọi vai trò của hệ thống và tập quyền của từng vai trò."""
    del actor
    return ok_list([RoleOut.of(role) for role in await use_case.execute()])


@router.get(
    "/admin/audit-events",
    response_model=ResponseEnvelope[list[AuditEventOut]],
    tags=["Quản trị hệ thống"],
    summary="Nhật ký thao tác quản trị",
)
async def audit_events(
    actor: Annotated[ActorContext, require_permissions(Permission.STUDIO_OVERSEE)],
    studio_id: Annotated[UUID | None, Query(description="Chỉ thao tác lên một xưởng")] = None,
    action: Annotated[str | None, Query(max_length=60)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> dict[str, Any]:
    """Mới nhất trước. Chỉ đọc — nhật ký không sửa, không xoá được qua API."""
    del actor
    items = await audit.recent(limit=limit, tenant_id=studio_id, action=action)
    return ok_list([AuditEventOut.of(item) for item in items])


__all__ = ["router"]
