"""Kiểm tra use case quên mật khẩu, đặt lại mật khẩu và link hỗ trợ của admin."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import pytest

from app.core import audit
from app.core.config import get_settings
from app.core.context import ActorContext
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.security.password import hash_password, verify_password
from app.modules.identity.application.use_cases import password_reset as pr_module
from app.modules.identity.application.use_cases.password_reset import (
    CreateAdminResetLink,
    RequestPasswordReset,
    ResetPassword,
)
from app.modules.identity.domain.entities import PasswordResetToken, User
from app.modules.identity.infrastructure.external.smtp_mailer import SmtpPasswordResetMailer


class _FakeUsers:
    def __init__(self, users: list[User]) -> None:
        self.by_id: dict[UUID, User] = {u.id: u for u in users}

    async def find_by_identifier(
        self, *, email: str | None = None, phone: str | None = None
    ) -> User | None:
        for user in self.by_id.values():
            if email is not None and user.email == email:
                return user
            if phone is not None and user.phone == phone:
                return user
        return None

    async def find_by_id(self, tenant_id: UUID, user_id: UUID) -> User | None:
        user = self.by_id.get(user_id)
        return user if user and user.tenant_id == tenant_id else None

    async def find_any_by_id(self, user_id: UUID) -> User | None:
        return self.by_id.get(user_id)

    async def set_password_hash(self, tenant_id: UUID, user_id: UUID, password_hash: str) -> bool:
        user = await self.find_by_id(tenant_id, user_id)
        if user is None:
            return False
        self.by_id[user_id] = User(
            id=user.id,
            tenant_id=user.tenant_id,
            full_name=user.full_name,
            password_hash=password_hash,
            email=user.email,
            phone=user.phone,
            is_active=user.is_active,
        )
        return True


class _FakeSessions:
    def __init__(self) -> None:
        self.revoked_calls: list[tuple[UUID, UUID | None]] = []

    async def revoke_all_for_user(
        self, user_id: UUID, *, except_session_id: UUID | None = None
    ) -> int:
        self.revoked_calls.append((user_id, except_session_id))
        return 2


class _FakeResetTokens:
    def __init__(self) -> None:
        self.rows: list[tuple[str, PasswordResetToken]] = []

    async def create(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        created_by_admin_id: UUID | None = None,
    ) -> PasswordResetToken:
        item = PasswordResetToken(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            expires_at=expires_at,
            used_at=None,
            created_by_admin_id=created_by_admin_id,
        )
        self.rows.append((token_hash, item))
        return item

    async def invalidate_for_user(self, user_id: UUID, now: datetime) -> int:
        count = 0
        updated: list[tuple[str, PasswordResetToken]] = []
        for token_hash, item in self.rows:
            if item.user_id == user_id and item.used_at is None:
                count += 1
                item = PasswordResetToken(
                    id=item.id,
                    tenant_id=item.tenant_id,
                    user_id=item.user_id,
                    expires_at=item.expires_at,
                    used_at=now,
                    created_by_admin_id=item.created_by_admin_id,
                )
            updated.append((token_hash, item))
        self.rows = updated
        return count

    async def consume(self, token_hash: str, now: datetime) -> PasswordResetToken | None:
        for idx, (stored_hash, item) in enumerate(self.rows):
            if stored_hash == token_hash and item.used_at is None and item.expires_at > now:
                consumed = PasswordResetToken(
                    id=item.id,
                    tenant_id=item.tenant_id,
                    user_id=item.user_id,
                    expires_at=item.expires_at,
                    used_at=now,
                    created_by_admin_id=item.created_by_admin_id,
                )
                self.rows[idx] = (stored_hash, consumed)
                return consumed
        return None


class _FakeMailer:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_reset_link(
        self, *, to_email: str, full_name: str, reset_url: str, ttl_minutes: int
    ) -> bool:
        self.sent.append(
            {
                "to_email": to_email,
                "full_name": full_name,
                "reset_url": reset_url,
                "ttl_minutes": ttl_minutes,
            }
        )
        return True


def _user(
    *,
    email: str | None = "khach@example.com",
    phone: str | None = None,
    is_active: bool = True,
) -> User:
    return User(
        id=uuid4(),
        tenant_id=uuid4(),
        full_name="Minh Linh",
        password_hash=hash_password("matkhau123"),
        email=email,
        phone=phone,
        is_active=is_active,
    )


async def test_request_reset_chong_do_tai_khoan_va_vo_hieu_token_cu() -> None:
    email_user = _user(email="lan@example.com")
    phone_only = _user(email=None, phone="0912345678")
    locked = _user(email="khoa@example.com", is_active=False)
    users = _FakeUsers([email_user, phone_only, locked])
    tokens = _FakeResetTokens()
    mailer = _FakeMailer()
    use_case = RequestPasswordReset(users, tokens, mailer)  # type: ignore[arg-type]

    # SĐT không có email, tài khoản khoá, tài khoản không tồn tại, chuỗi sai: im lặng hết.
    await use_case.execute("0912345678")
    await use_case.execute("khoa@example.com")
    await use_case.execute("khongton@example.com")
    await use_case.execute("not-an-identifier")
    assert mailer.sent == []
    assert tokens.rows == []

    # Tài khoản email hợp lệ: gửi mail và lưu hash; xin lại lần 2 thì token lần 1 bị vô hiệu.
    await use_case.execute("  LAN@Example.com ")
    await use_case.execute("lan@example.com")
    assert len(mailer.sent) == 2
    assert len(tokens.rows) == 2
    assert tokens.rows[0][1].used_at is not None
    assert tokens.rows[1][1].used_at is None


async def test_reset_password_kiem_mat_khau_truoc_va_thu_hoi_tat_ca_phien(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audits: list[tuple[str, dict[str, Any]]] = []
    revoked_users: list[UUID] = []

    async def _fake_audit(
        action: str,
        *,
        actor_id: UUID | None,
        target_type: str,
        target_id: object,
        tenant_id: UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        del actor_id, target_type, target_id, tenant_id
        audits.append((action, details or {}))

    async def _fake_revoke_user(
        user_id: UUID, *, at: datetime, except_session_id: UUID | None = None
    ) -> None:
        del at
        assert except_session_id is None
        revoked_users.append(user_id)

    monkeypatch.setattr(audit, "record", _fake_audit)
    monkeypatch.setattr(pr_module, "revoke_user", _fake_revoke_user)

    user = _user(email="lan@example.com")
    users = _FakeUsers([user])
    sessions = _FakeSessions()
    tokens = _FakeResetTokens()
    mailer = _FakeMailer()

    await RequestPasswordReset(users, tokens, mailer).execute("lan@example.com")  # type: ignore[arg-type]
    raw_token = parse_qs(urlsplit(mailer.sent[0]["reset_url"]).query)["token"][0]
    reset = ResetPassword(users, sessions, tokens)  # type: ignore[arg-type]

    # Mật khẩu yếu không được tiêu thụ token đang còn hạn.
    with pytest.raises(ValidationError):
        await reset.execute(raw_token, "yeu")
    assert tokens.rows[0][1].used_at is None

    # Đặt lại thành công: đổi hash, cắt mọi phiên, ghi audit.
    await reset.execute(raw_token, "MatkhauMoi99")
    updated = users.by_id[user.id]
    assert verify_password("MatkhauMoi99", updated.password_hash) is True
    assert sessions.revoked_calls == [(user.id, None)]
    assert revoked_users == [user.id]
    assert audits == [("password.reset", {"via": "self_service"})]

    # Dùng lại cùng token phải bị từ chối.
    with pytest.raises(ValidationError) as reused:
        await reset.execute(raw_token, "MatkhauMoi88")
    assert reused.value.code == "reset_token_invalid"


async def test_admin_reset_link_va_smtp_khong_cau_hinh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audits: list[str] = []

    async def _fake_audit(action: str, **_kwargs: object) -> None:
        audits.append(action)

    monkeypatch.setattr(audit, "record", _fake_audit)
    active = _user(email=None, phone="0988777666")
    locked = _user(email=None, phone="0911222333", is_active=False)
    users = _FakeUsers([active, locked])
    tokens = _FakeResetTokens()
    actor = ActorContext(user_id=uuid4(), tenant_id=uuid4(), permissions=frozenset({"user.manage"}))
    use_case = CreateAdminResetLink(users, tokens)  # type: ignore[arg-type]

    link = await use_case.execute(actor, active.id)
    assert "/reset-password?token=" in link.reset_url
    assert link.expires_at > datetime.now(UTC)
    assert audits == ["user.reset_link_created"]
    assert tokens.rows[0][1].created_by_admin_id == actor.user_id

    with pytest.raises(NotFoundError):
        await use_case.execute(actor, uuid4())
    with pytest.raises(ConflictError):
        await use_case.execute(actor, locked.id)

    cfg = get_settings()
    monkeypatch.setattr(cfg, "SMTP_HOST", "")
    assert (
        await SmtpPasswordResetMailer().send_reset_link(
            to_email="a@example.com",
            full_name="A",
            reset_url="http://localhost:8091/reset-password?token=abc",
            ttl_minutes=30,
        )
        is False
    )
