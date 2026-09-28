"""Use case: đăng nhập bằng email hoặc số điện thoại.

Thông tin đăng nhập sai trả **401 với đúng một câu**: "Thông tin đăng nhập không
đúng." Không bao giờ nói "email không tồn tại" hay "sai mật khẩu" — như vậy là
biếu không cho kẻ tấn công danh sách tài khoản có thật.
"""

from __future__ import annotations

import secrets
from functools import lru_cache

from app.core.base_model import utc_now
from app.core.errors import UnauthorizedError
from app.core.logging import get_logger
from app.core.security.password import (
    hash_password,
    hash_password_async,
    needs_rehash,
    verify_password_async,
)
from app.modules.identity.application.dtos import AuthResult, LoginCommand
from app.modules.identity.application.session_issuer import SessionIssuer
from app.modules.identity.domain.enums import IdentifierKind
from app.modules.identity.domain.errors import InvalidIdentifierError
from app.modules.identity.domain.repositories import StudioRepository, UserRepository
from app.modules.identity.domain.services import normalize_identifier

log = get_logger(__name__)

#: Một câu duy nhất cho mọi kiểu sai — xem docstring module.
INVALID_CREDENTIALS_MESSAGE = "Thông tin đăng nhập không đúng."


@lru_cache(maxsize=1)
def _decoy_hash() -> str:
    """Chuỗi băm giả để so khớp khi không tìm thấy người dùng.

    Không có bước này, đăng nhập bằng email không tồn tại trả lời nhanh hơn hẳn
    email có thật (vì bỏ qua Argon2) — đủ để dò tài khoản bằng đồng hồ bấm giờ.
    """
    return hash_password(secrets.token_urlsafe(32))


class LoginUser:
    """Xác thực người dùng rồi mở phiên mới. Không nhận `ActorContext`: actor sinh ra ở đây."""

    def __init__(
        self, users: UserRepository, studios: StudioRepository, issuer: SessionIssuer
    ) -> None:
        self._users = users
        self._studios = studios
        self._issuer = issuer

    async def execute(self, command: LoginCommand) -> AuthResult:
        """Đăng nhập.

        Raises:
            UnauthorizedError: định danh sai, không tìm thấy, sai mật khẩu, tài
                khoản hoặc xưởng bị khoá.
        """
        try:
            kind, value = normalize_identifier(command.identifier)
        except InvalidIdentifierError:
            await verify_password_async(command.password, _decoy_hash())
            raise self._invalid() from None

        user = await self._users.find_by_identifier(
            email=value if kind is IdentifierKind.EMAIL else None,
            phone=value if kind is IdentifierKind.PHONE else None,
        )
        if user is None:
            await verify_password_async(command.password, _decoy_hash())
            raise self._invalid()
        if not await verify_password_async(command.password, user.password_hash):
            raise self._invalid()

        # Từ đây người gọi ĐÃ chứng minh sở hữu tài khoản, nên nói rõ lý do bị
        # chặn không còn là rò rỉ — và giúp họ biết phải làm gì.
        if not user.is_active:
            raise UnauthorizedError(
                "Tài khoản đã bị khoá. Vui lòng liên hệ quản trị viên.", code="account_disabled"
            )
        studio = await self._studios.find_by_id(user.tenant_id)
        if studio is None or not studio.is_active:
            raise UnauthorizedError(
                "Xưởng thiệp của bạn đã ngừng hoạt động. Vui lòng liên hệ quản trị viên.",
                code="studio_disabled",
            )

        if needs_rehash(user.password_hash):
            await self._users.set_password_hash(
                user.tenant_id, user.id, await hash_password_async(command.password)
            )

        result = await self._issuer.issue(
            user, studio, user_agent=command.user_agent, ip=command.ip
        )
        await self._users.touch_login(user.id, utc_now())
        log.info("login_succeeded", user_id=str(user.id), identifier_kind=str(kind))
        return result

    def _invalid(self) -> UnauthorizedError:
        return UnauthorizedError(INVALID_CREDENTIALS_MESSAGE, code="invalid_credentials")


__all__ = ["INVALID_CREDENTIALS_MESSAGE", "LoginUser"]
