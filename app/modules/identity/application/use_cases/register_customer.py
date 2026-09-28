"""Use case: khách tự đăng ký tài khoản dùng mẫu.

Một lượt đăng ký tạo ba thứ ở hai module: xưởng + tài khoản (`identity`) và vai
trò `customer` (`access`, qua cổng `RoleGranter`). Không gói được vào một giao
dịch Mongo xuyên module mà không rò session qua cổng, nên dùng **bù trừ**: bước
sau hỏng thì xoá cứng những gì bước trước vừa tạo — không để lại tài khoản
đăng nhập được mà không có quyền gì, cũng không để lại email bị "chiếm" vĩnh viễn.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.errors import ConflictError, ForbiddenError, ValidationError
from app.core.logging import get_logger
from app.core.security.password import hash_password_async
from app.modules.identity.application.dtos import AuthResult, RegisterCommand
from app.modules.identity.application.ports import RoleGranter
from app.modules.identity.application.session_issuer import SessionIssuer
from app.modules.identity.domain.errors import DuplicateIdentifierError, IdentityDomainError
from app.modules.identity.domain.repositories import StudioRepository, UserRepository
from app.modules.identity.domain.services import (
    check_password_policy,
    normalize_email,
    normalize_phone,
    studio_name_for,
)

log = get_logger(__name__)

#: Slug vai trò cấp cho khách tự đăng ký. Đây là đường CẤP vai trò — nơi duy nhất
#: được gọi tên một vai trò cụ thể (xem `access.domain.role_blueprints`).
CUSTOMER_ROLE_SLUG = "customer"


class RegisterCustomer:
    """Tạo xưởng + tài khoản + vai trò `customer`, rồi mở phiên luôn."""

    def __init__(
        self,
        users: UserRepository,
        studios: StudioRepository,
        roles: RoleGranter,
        issuer: SessionIssuer,
    ) -> None:
        self._users = users
        self._studios = studios
        self._roles = roles
        self._issuer = issuer

    async def execute(self, command: RegisterCommand) -> AuthResult:
        """Đăng ký.

        Raises:
            ForbiddenError: hệ thống đang tắt tự đăng ký.
            ValidationError: thiếu định danh, sai định dạng, mật khẩu yếu.
            ConflictError: email/số điện thoại đã có tài khoản.
        """
        if not get_settings().ALLOW_SELF_REGISTRATION:
            raise ForbiddenError(
                "Hệ thống đang tạm dừng đăng ký mới. Vui lòng liên hệ quản trị viên.",
                code="registration_closed",
            )

        full_name = " ".join(command.full_name.split())
        email, phone = self._normalized_identifiers(command)
        try:
            check_password_policy(command.password)
        except IdentityDomainError as exc:
            raise ValidationError(
                exc.message, errors={exc.field or "password": [exc.message]}
            ) from exc

        # Tra trước để trả câu rõ ràng; index duy nhất vẫn là chốt chặn thật
        # (hai lượt đăng ký song song cùng email).
        taken = (email and await self._users.find_by_identifier(email=email)) or (
            phone and await self._users.find_by_identifier(phone=phone)
        )
        if taken:
            raise self._duplicate()

        studio = await self._studios.create(name=studio_name_for(full_name))
        try:
            user = await self._users.create(
                tenant_id=studio.id,
                full_name=full_name,
                password_hash=await hash_password_async(command.password),
                email=email,
                phone=phone,
            )
        except DuplicateIdentifierError:
            await self._studios.delete(studio.id)
            raise self._duplicate() from None

        try:
            await self._roles.execute(
                tenant_id=studio.id, user_id=user.id, role_slug=CUSTOMER_ROLE_SLUG
            )
        except Exception:
            await self._users.delete(user.id)
            await self._studios.delete(studio.id)
            raise

        log.info("customer_registered", user_id=str(user.id), studio_id=str(studio.id))
        return await self._issuer.issue(user, studio, user_agent=command.user_agent, ip=command.ip)

    @staticmethod
    def _duplicate() -> ConflictError:
        return ConflictError(DuplicateIdentifierError.message, code="identifier_taken")

    @staticmethod
    def _normalized_identifiers(command: RegisterCommand) -> tuple[str | None, str | None]:
        email_raw = (command.email or "").strip()
        phone_raw = (command.phone or "").strip()
        if not email_raw and not phone_raw:
            message = "Nhập email hoặc số điện thoại để đăng nhập về sau."
            raise ValidationError(message, errors={"email": [message]})
        try:
            email = normalize_email(email_raw) if email_raw else None
            phone = normalize_phone(phone_raw) if phone_raw else None
        except IdentityDomainError as exc:
            raise ValidationError(
                exc.message, errors={exc.field or "email": [exc.message]}
            ) from exc
        return email, phone


__all__ = ["CUSTOMER_ROLE_SLUG", "RegisterCustomer"]
