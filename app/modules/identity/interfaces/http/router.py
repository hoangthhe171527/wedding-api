"""Router HTTP của `identity` — nhóm `/api/v1/auth`.

| Method | Path                          | Quyền yêu cầu                   |
|--------|-------------------------------|---------------------------------|
| POST   | /api/v1/auth/login            | công khai (giới hạn tần suất)   |
| POST   | /api/v1/auth/register         | công khai (giới hạn tần suất)   |
| POST   | /api/v1/auth/refresh          | công khai (cần refresh token)   |
| POST   | /api/v1/auth/logout           | chỉ cần đăng nhập               |
| GET    | /api/v1/auth/me               | chỉ cần đăng nhập               |
| POST   | /api/v1/auth/change-password  | chỉ cần đăng nhập               |

Không endpoint nào ở đây gắn quyền theo slug: đây là các thao tác về CHÍNH tài
khoản đang gọi. Router không bắt lỗi — use case ném `AppError`.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response, status

from app.core import rate_limit
from app.core.config import get_settings
from app.core.dependencies import ActorDep, client_ip
from app.core.errors import UnauthorizedError
from app.core.responses import MessageOut, ResponseEnvelope, ok, ok_message
from app.modules.identity.application.dtos import LoginCommand, RefreshCommand, RegisterCommand
from app.modules.identity.domain.errors import InvalidIdentifierError
from app.modules.identity.domain.services import normalize_identifier
from app.modules.identity.infrastructure.providers import (
    ChangeOwnPasswordDep,
    GetCurrentActorDep,
    LoginUserDep,
    LogoutUserDep,
    RefreshTokenDep,
    RegisterCustomerDep,
)
from app.modules.identity.interfaces.http.schemas import (
    ActorOut,
    ChangePasswordIn,
    LoginIn,
    LogoutIn,
    RefreshIn,
    RegisterIn,
    TokenOut,
)

router = APIRouter(prefix="/auth", tags=["Xác thực"])

LOGIN_IP_BUCKET = "login_ip"
LOGIN_IDENTIFIER_BUCKET = "login_identifier"
REGISTER_IP_BUCKET = "register_ip"
_REGISTER_WINDOW_SECONDS = 3600


async def _guard_login_rate(*, ip: str, identifier: str) -> None:
    """Chặn dò mật khẩu TRƯỚC khi chạm tới Argon2 (~50ms mỗi lần băm).

    Hai chiều: theo IP (quét hàng loạt tài khoản từ một máy) và theo định danh
    (botnet đổi IP liên tục dò một tài khoản cụ thể).
    """
    cfg = get_settings()
    window = cfg.LOGIN_RATE_LIMIT_WINDOW_SECONDS
    message = "Bạn đã thử đăng nhập quá nhiều lần. Vui lòng đợi ít phút rồi thử lại."
    await rate_limit.guard(
        LOGIN_IP_BUCKET,
        ip,
        limit=cfg.LOGIN_RATE_LIMIT_IP,
        window_seconds=window,
        message=message,
        code="login_rate_limited",
    )
    await rate_limit.guard(
        LOGIN_IDENTIFIER_BUCKET,
        identifier,
        limit=cfg.LOGIN_RATE_LIMIT_IDENTIFIER,
        window_seconds=window,
        message=message,
        code="login_rate_limited",
    )


#: Refresh token sống trong cookie HttpOnly — JavaScript của trang không đọc được,
#: nên một lỗ XSS không lấy được phiên 30 ngày. Chỉ gửi kèm các đường `/auth`.
REFRESH_COOKIE = "wedding_refresh"


def _set_refresh_cookie(response: Response, token: str) -> None:
    cfg = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=cfg.REFRESH_TTL_DAYS * 86400,
        httponly=True,
        # Máy dev chạy http; mọi môi trường khác bắt buộc https.
        secure=not cfg.is_local,
        samesite="strict",
        path=f"{cfg.API_PREFIX}/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    cfg = get_settings()
    response.delete_cookie(REFRESH_COOKIE, path=f"{cfg.API_PREFIX}/auth")


def _rate_key(raw: str) -> str:
    """Khoá bộ đếm theo định danh ĐÃ chuẩn hoá: `0912 345 678`, `+84912345678`,
    `(0912)345.678`... là một số — đếm chung, không mỗi cách viết một hạn mức.
    Không nhận diện được thì dồn vào một khoá chung (vẫn bị chặn theo IP)."""
    try:
        return normalize_identifier(raw)[1]
    except InvalidIdentifierError:
        return "invalid"


@router.post("/login", response_model=ResponseEnvelope[TokenOut], summary="Đăng nhập")
async def login(
    payload: LoginIn, request: Request, response: Response, use_case: LoginUserDep
) -> dict[str, Any]:
    """Xác thực và mở phiên mới. Sai bất kỳ điều gì cũng trả 401 với đúng một câu."""
    ip = client_ip(request) or "unknown"
    identifier = _rate_key(payload.identifier)
    await _guard_login_rate(ip=ip, identifier=identifier)

    result = await use_case.execute(
        LoginCommand(
            identifier=payload.identifier,
            password=payload.password,
            user_agent=request.headers.get("user-agent"),
            ip=client_ip(request),
        )
    )
    # Đăng nhập đúng chỉ xoá bộ đếm của CHÍNH tài khoản đó (gõ nhầm vài lần rồi
    # vào được không nên bị chặn tiếp). KHÔNG xoá bộ đếm IP: nếu không, kẻ dò chỉ
    # cần xen vào một lần đăng nhập tài khoản của mình là bộ đếm IP về 0.
    window = get_settings().LOGIN_RATE_LIMIT_WINDOW_SECONDS
    await rate_limit.reset(LOGIN_IDENTIFIER_BUCKET, identifier, window_seconds=window)
    _set_refresh_cookie(response, result.refresh_token)
    return ok(TokenOut.of(result))


@router.post(
    "/register",
    response_model=ResponseEnvelope[TokenOut],
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản dùng mẫu",
)
async def register(
    payload: RegisterIn, request: Request, response: Response, use_case: RegisterCustomerDep
) -> dict[str, Any]:
    """Tạo xưởng thiệp riêng + tài khoản `customer`, đăng nhập luôn."""
    ip = client_ip(request) or "unknown"
    await rate_limit.guard(
        REGISTER_IP_BUCKET,
        ip,
        limit=get_settings().REGISTER_RATE_LIMIT_IP,
        window_seconds=_REGISTER_WINDOW_SECONDS,
        message="Có quá nhiều tài khoản được tạo từ mạng của bạn. Vui lòng thử lại sau.",
        code="register_rate_limited",
    )
    result = await use_case.execute(
        RegisterCommand(
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            password=payload.password,
            user_agent=request.headers.get("user-agent"),
            ip=client_ip(request),
        )
    )
    _set_refresh_cookie(response, result.refresh_token)
    return ok(TokenOut.of(result))


@router.post(
    "/refresh", response_model=ResponseEnvelope[TokenOut], summary="Xoay vòng refresh token"
)
async def refresh(
    payload: RefreshIn, request: Request, response: Response, use_case: RefreshTokenDep
) -> dict[str, Any]:
    """Đổi refresh token cũ lấy cặp mới; dùng lại token đã thu hồi sẽ khoá mọi phiên.

    Token lấy từ thân yêu cầu (ứng dụng khác) hoặc cookie HttpOnly (web).
    """
    token = payload.refresh_token or request.cookies.get(REFRESH_COOKIE, "")
    if not token:
        raise UnauthorizedError("Phiên đăng nhập đã hết hạn.", code="missing_refresh_token")
    result = await use_case.execute(
        RefreshCommand(
            refresh_token=token,
            user_agent=request.headers.get("user-agent"),
            ip=client_ip(request),
        )
    )
    _set_refresh_cookie(response, result.refresh_token)
    return ok(TokenOut.of(result))


@router.post("/logout", response_model=ResponseEnvelope[MessageOut], summary="Đăng xuất")
async def logout(
    payload: LogoutIn,
    request: Request,
    response: Response,
    actor: ActorDep,
    use_case: LogoutUserDep,
) -> dict[str, Any]:
    """Thu hồi phiên hiện tại (hoặc mọi phiên nếu `all_devices`) và xoá cookie."""
    token = payload.refresh_token or request.cookies.get(REFRESH_COOKIE) or None
    await use_case.execute(actor, refresh_token=token, all_devices=payload.all_devices)
    _clear_refresh_cookie(response)
    return ok_message("Đã đăng xuất.")


@router.get("/me", response_model=ResponseEnvelope[ActorOut], summary="Người dùng hiện tại")
async def me(actor: ActorDep, use_case: GetCurrentActorDep) -> dict[str, Any]:
    """Người dùng, xưởng và tập quyền — đọc mới từ `access`, không lấy trong token."""
    return ok(ActorOut.of(await use_case.execute(actor)))


@router.post(
    "/change-password",
    response_model=ResponseEnvelope[MessageOut],
    summary="Đổi mật khẩu của chính mình",
)
async def change_password(
    payload: ChangePasswordIn, actor: ActorDep, use_case: ChangeOwnPasswordDep
) -> dict[str, Any]:
    """Đổi mật khẩu; mọi phiên trên thiết bị khác bị thu hồi."""
    await use_case.execute(actor, payload.current_password, payload.new_password)
    return ok_message("Đã đổi mật khẩu. Các thiết bị khác cần đăng nhập lại.")


__all__ = ["router"]
