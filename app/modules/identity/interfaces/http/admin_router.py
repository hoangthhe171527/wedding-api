"""Router quản trị tài khoản — nhóm `/api/v1/admin/users` (quyền `user.manage`).

| Method | Path                              | Quyền        |
|--------|-----------------------------------|--------------|
| GET    | /api/v1/admin/users               | user.manage  |
| PATCH  | /api/v1/admin/users/{id}/status   | user.manage  |
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.context import ActorContext
from app.core.dependencies import require_permissions
from app.core.pagination import PageParams, page_params
from app.core.permissions import Permission
from app.core.responses import PaginatedEnvelope, ResponseEnvelope, ok, ok_page
from app.modules.identity.application.dtos import UserSummary
from app.modules.identity.infrastructure.providers import ListUsersDep, SetUserActiveDep
from app.modules.identity.interfaces.http.schemas import AdminUserOut, SetActiveIn

router = APIRouter(prefix="/admin/users", tags=["Quản trị tài khoản"])

UserManager = Annotated[ActorContext, require_permissions(Permission.USER_MANAGE)]


@router.get("", response_model=PaginatedEnvelope[AdminUserOut], summary="Danh sách tài khoản")
async def list_users(
    actor: UserManager,
    use_case: ListUsersDep,
    params: Annotated[PageParams, Depends(page_params)],
    q: Annotated[str | None, Query(max_length=120, description="Tìm theo tên, email, SĐT.")] = None,
) -> dict[str, Any]:
    """Mọi tài khoản của hệ thống, mới nhất trước."""
    del actor
    page = await use_case.execute(query=q, params=params)
    return ok_page(page.map(AdminUserOut.of))


@router.patch(
    "/{user_id}/status",
    response_model=ResponseEnvelope[AdminUserOut],
    summary="Khoá / mở khoá tài khoản",
)
async def set_status(
    user_id: UUID, payload: SetActiveIn, actor: UserManager, use_case: SetUserActiveDep
) -> dict[str, Any]:
    """Khoá tài khoản cắt mọi phiên đang đăng nhập của người đó ngay lập tức."""
    user = await use_case.execute(actor, user_id, is_active=payload.is_active)
    return ok(AdminUserOut.of(UserSummary(user=user, studio_name=None)))


__all__ = ["router"]
