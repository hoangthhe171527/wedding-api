"""Cầu nối: cấp tài khoản theo khoá tự nhiên cố định — dùng cho seed.

Idempotent: chạy lần hai không tạo thêm xưởng/tài khoản nào. Seed là tầng ghép
module, nên nó gọi hàm dựng trên barrel thay vì chạm Document của `identity`.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.security.password import hash_password
from app.modules.access import build_grant_role
from app.modules.identity.infrastructure.persistence.repositories import (
    BeanieStudioRepository,
    BeanieUserRepository,
)


@dataclass(frozen=True, slots=True)
class ProvisionedAccount:
    """Kết quả cấp tài khoản."""

    studio_id: UUID
    user_id: UUID
    created: bool


class AccountProvisioner:
    """Bảo đảm tồn tại: một xưởng, một tài khoản trong xưởng, một vai trò."""

    def __init__(self) -> None:
        self._studios = BeanieStudioRepository()
        self._users = BeanieUserRepository()
        self._grant = build_grant_role()

    async def ensure(
        self,
        *,
        studio_id: UUID,
        studio_name: str,
        user_id: UUID,
        full_name: str,
        email: str | None,
        phone: str | None,
        password: str,
        role_slug: str,
    ) -> ProvisionedAccount:
        created = False
        if await self._studios.find_by_id(studio_id) is None:
            await self._studios.create(name=studio_name, studio_id=studio_id)
            created = True
        if await self._users.find_any_by_id(user_id) is None:
            await self._users.create(
                tenant_id=studio_id,
                full_name=full_name,
                password_hash=hash_password(password),
                email=email,
                phone=phone,
                user_id=user_id,
            )
            created = True
        await self._grant.execute(tenant_id=studio_id, user_id=user_id, role_slug=role_slug)
        return ProvisionedAccount(studio_id=studio_id, user_id=user_id, created=created)


def build_account_provisioner() -> AccountProvisioner:
    """Hàm dựng công bố trên barrel `app.modules.identity`."""
    return AccountProvisioner()


__all__ = ["AccountProvisioner", "ProvisionedAccount", "build_account_provisioner"]
