"""Dependency dùng chung cho tầng HTTP: actor đã xác thực, cổng kiểm quyền, IP client.

Quy tắc bất di bất dịch (ARCHITECTURE §0.2): file này KHÔNG import bất kỳ thứ gì
trong `app.modules`. Tập quyền nằm sẵn trong access token nên `get_actor` không
chạm DB — bước kiểm thu hồi đọc Redis, không đọc `auth_sessions`.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.context import ActorContext
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.permissions import Permission, label_of
from app.core.security.revocation import is_revoked
from app.core.security.tokens import decode_access_token

#: `auto_error=False` để tự ném `UnauthorizedError` với envelope tiếng Việt,
#: thay vì để Starlette trả 403 kiểu Anh ngữ khi thiếu header.
bearer_scheme = HTTPBearer(auto_error=False, scheme_name="Bearer")

BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


async def get_actor(request: Request, credentials: BearerCredentials) -> ActorContext:
    """Giải mã access token thành `ActorContext`.

    Raises:
        UnauthorizedError: thiếu header, sai định dạng, token hỏng, hết hạn, bị thu hồi.
    """
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError(
            "Bạn cần đăng nhập để thực hiện thao tác này.", code="missing_token"
        )
    if credentials.scheme.lower() != "bearer":
        raise UnauthorizedError(
            "Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.", code="token_invalid"
        )

    claims = decode_access_token(credentials.credentials)
    # Chữ ký hợp lệ mới chứng minh token do ta phát, chưa chứng minh phiên còn
    # sống. Thiếu bước này thì đăng xuất/đổi mật khẩu để cửa mở thêm 15 phút.
    if await is_revoked(
        user_id=claims.user_id, session_id=claims.session_id, issued_at=claims.issued_at
    ):
        raise UnauthorizedError(
            "Phiên đăng nhập đã kết thúc. Vui lòng đăng nhập lại.", code="token_revoked"
        )
    actor = ActorContext(
        user_id=claims.user_id,
        tenant_id=claims.tenant_id,
        permissions=claims.permissions,
        session_id=claims.session_id,
    )
    request.state.actor = actor
    return actor


ActorDep = Annotated[ActorContext, Depends(get_actor)]


def require_permissions(*slugs: Permission | str) -> Any:
    """Dependency factory chặn 403 khi actor thiếu BẤT KỲ quyền nào trong `slugs`.

    Dùng ở router::

        actor: Annotated[ActorContext, require_permissions(Permission.GUEST_MANAGE)]
    """
    required = tuple(str(slug) for slug in slugs)

    async def _guard(actor: ActorDep) -> ActorContext:
        missing = [slug for slug in required if slug not in actor.permissions]
        if missing:
            raise ForbiddenError(
                "Bạn không có quyền thực hiện thao tác này.",
                code="forbidden",
                context={"missing": missing, "required": list(required)},
            )
        return actor

    _guard.__doc__ = "Yêu cầu quyền: " + ", ".join(label_of(slug) for slug in required)
    return Depends(_guard)


def client_ip(request: Request) -> str | None:
    """IP thật của client, đọc `X-Forwarded-For` từ phía ĐÁNG TIN.

    `X-Forwarded-For` do client bắt đầu viết; mỗi proxy chỉ nối thêm địa chỉ nó
    thấy vào cuối. Phần tử đầu là thứ client tự khai — đọc nó là để hạn mức đăng
    nhập theo IP bị vượt chỉ bằng cách đổi một header. Phần tử do proxy của ta
    ghi nằm cách cuối `TRUSTED_PROXY_HOPS - 1` bước.
    """
    peer = request.client.host if request.client else None
    hops = get_settings().TRUSTED_PROXY_HOPS
    if hops <= 0:
        return peer
    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return peer
    parts = [part.strip() for part in forwarded.split(",") if part.strip()]
    if len(parts) < hops:
        return peer
    return parts[-hops]


__all__ = [
    "ActorDep",
    "BearerCredentials",
    "bearer_scheme",
    "client_ip",
    "get_actor",
    "require_permissions",
]
