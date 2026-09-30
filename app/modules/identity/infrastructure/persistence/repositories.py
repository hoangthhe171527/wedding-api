"""Hiện thực Beanie của repository `identity`."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from beanie.operators import In
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.base_model import new_id, utc_now
from app.core.pages import Page, PageParams
from app.modules.identity.domain.entities import AuthSession, Studio, User
from app.modules.identity.domain.errors import DuplicateIdentifierError
from app.modules.identity.infrastructure.persistence.models import (
    AuthSessionDocument,
    StudioDocument,
    UserDocument,
)


def _studio(doc: StudioDocument) -> Studio:
    return Studio(id=doc.id, name=doc.name, is_active=doc.is_active)


def _user(doc: UserDocument) -> User:
    return User(
        id=doc.id,
        tenant_id=doc.tenant_id,
        full_name=doc.full_name,
        password_hash=doc.password_hash,
        email=doc.email,
        phone=doc.phone,
        is_active=doc.is_active,
        created_at=doc.created_at,
        last_login_at=doc.last_login_at,
    )


def _session(doc: AuthSessionDocument) -> AuthSession:
    return AuthSession(
        id=doc.id,
        tenant_id=doc.tenant_id,
        user_id=doc.user_id,
        expires_at=doc.expires_at,
        created_at=doc.created_at,
        revoked_at=doc.revoked_at,
        replaced_by=doc.replaced_by,
        user_agent=doc.user_agent,
        ip=doc.ip,
    )


class BeanieStudioRepository:
    """`StudioRepository` trên Mongo."""

    async def create(self, *, name: str, studio_id: UUID | None = None) -> Studio:
        doc = StudioDocument.new(name=name, studio_id=studio_id)
        await doc.insert()
        return _studio(doc)

    async def find_by_id(self, studio_id: UUID) -> Studio | None:
        doc = await StudioDocument.get_scoped(studio_id, studio_id)
        return _studio(doc) if doc else None

    async def find_many(self, studio_ids: Sequence[UUID]) -> list[Studio]:
        if not studio_ids:
            return []
        docs = await StudioDocument.find(In(StudioDocument.id, list(studio_ids))).to_list()
        return [_studio(doc) for doc in docs]

    async def delete(self, studio_id: UUID) -> None:
        await StudioDocument.find_one({"_id": studio_id}).delete()


class BeanieUserRepository:
    """`UserRepository` trên Mongo."""

    async def find_by_identifier(
        self, *, email: str | None = None, phone: str | None = None
    ) -> User | None:
        if email is None and phone is None:
            return None
        query: dict[str, Any] = {"deleted_at": None}
        query["email" if email is not None else "phone"] = email if email is not None else phone
        doc = await UserDocument.find_one(query)
        return _user(doc) if doc else None

    async def find_by_id(self, tenant_id: UUID, user_id: UUID) -> User | None:
        doc = await UserDocument.get_scoped(tenant_id, user_id)
        return _user(doc) if doc else None

    async def find_any_by_id(self, user_id: UUID) -> User | None:
        doc = await UserDocument.find_one({"_id": user_id, "deleted_at": None})
        return _user(doc) if doc else None

    async def create(
        self,
        *,
        tenant_id: UUID,
        full_name: str,
        password_hash: str,
        email: str | None,
        phone: str | None,
        user_id: UUID | None = None,
    ) -> User:
        doc = UserDocument(
            id=user_id or new_id(),
            tenant_id=tenant_id,
            full_name=full_name,
            password_hash=password_hash,
            email=email,
            phone=phone,
        )
        try:
            await doc.insert()
        except DuplicateKeyError as exc:
            raise DuplicateIdentifierError from exc
        return _user(doc)

    async def delete(self, user_id: UUID) -> None:
        await UserDocument.find_one({"_id": user_id}).delete()

    async def delete_for_tenant(self, tenant_id: UUID) -> int:
        result = await UserDocument.get_motor_collection().delete_many({"tenant_id": tenant_id})
        return int(result.deleted_count)

    async def set_password_hash(self, tenant_id: UUID, user_id: UUID, password_hash: str) -> bool:
        result = await UserDocument.get_motor_collection().update_one(
            {"_id": user_id, "tenant_id": tenant_id, "deleted_at": None},
            {"$set": {"password_hash": password_hash, "updated_at": utc_now()}},
        )
        return bool(result.matched_count)

    async def set_active(self, user_id: UUID, *, is_active: bool, actor_id: UUID) -> bool:
        result = await UserDocument.get_motor_collection().update_one(
            {"_id": user_id, "deleted_at": None},
            {"$set": {"is_active": is_active, "updated_at": utc_now(), "updated_by": actor_id}},
        )
        return bool(result.matched_count)

    async def touch_login(self, user_id: UUID, at: datetime) -> None:
        await UserDocument.get_motor_collection().update_one(
            {"_id": user_id}, {"$set": {"last_login_at": at}}
        )

    async def search_all(self, *, query: str | None, params: PageParams) -> Page[User]:
        # Ngoại lệ có chủ ý với §0.4: màn quản trị tài khoản của đội vận hành.
        # Quyền `user.manage` đã được kiểm ở router trước khi tới đây.
        criteria: dict[str, Any] = {"deleted_at": None}
        if query:
            pattern = {"$regex": re.escape(query), "$options": "i"}
            criteria["$or"] = [{"full_name": pattern}, {"email": pattern}, {"phone": pattern}]
        finder = UserDocument.find(criteria)
        total = await finder.count()
        docs = await finder.sort("-created_at").skip(params.offset).limit(params.limit).to_list()
        return Page(items=[_user(doc) for doc in docs], total=total, params=params)


class BeanieAuthSessionRepository:
    """`AuthSessionRepository` trên Mongo."""

    async def create(
        self,
        *,
        session_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> AuthSession:
        doc = AuthSessionDocument(
            id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=(user_agent or "")[:300] or None,
            ip=ip,
        )
        await doc.insert()
        return _session(doc)

    async def find_by_refresh_hash(self, refresh_token_hash: str) -> AuthSession | None:
        doc = await AuthSessionDocument.find_one(
            AuthSessionDocument.refresh_token_hash == refresh_token_hash
        )
        return _session(doc) if doc else None

    async def consume_refresh_hash(
        self, refresh_token_hash: str, now: datetime
    ) -> AuthSession | None:
        # `find_one_and_update` là MỘT thao tác nguyên tử phía Mongo: hai request
        # song song cùng token thì đúng một bên thấy phiên còn sống.
        raw = await AuthSessionDocument.get_motor_collection().find_one_and_update(
            {
                "refresh_token_hash": refresh_token_hash,
                "revoked_at": None,
                "expires_at": {"$gt": now},
                "deleted_at": None,
            },
            {"$set": {"revoked_at": now, "updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if raw is None:
            return None
        return _session(AuthSessionDocument.model_validate(raw))

    async def revoke(
        self, tenant_id: UUID, session_id: UUID, *, replaced_by: UUID | None = None
    ) -> bool:
        now = utc_now()
        update: dict[str, Any] = {"updated_at": now}
        if replaced_by is not None:
            update["replaced_by"] = replaced_by
        # Phiên đã bị tiêu thụ (revoked_at có sẵn) vẫn được ghi `replaced_by`.
        result = await AuthSessionDocument.get_motor_collection().update_one(
            {"_id": session_id, "tenant_id": tenant_id},
            [
                {
                    "$set": {
                        **update,
                        "revoked_at": {"$ifNull": ["$revoked_at", now]},
                    }
                }
            ],
        )
        return bool(result.matched_count)

    async def revoke_all_for_user(
        self, user_id: UUID, *, except_session_id: UUID | None = None
    ) -> int:
        criteria: dict[str, Any] = {"user_id": user_id, "revoked_at": None}
        if except_session_id is not None:
            criteria["_id"] = {"$ne": except_session_id}
        now = utc_now()
        result = await AuthSessionDocument.get_motor_collection().update_many(
            criteria, {"$set": {"revoked_at": now, "updated_at": now}}
        )
        return int(result.modified_count)

    async def delete_for_tenant(self, tenant_id: UUID) -> int:
        result = await AuthSessionDocument.get_motor_collection().delete_many(
            {"tenant_id": tenant_id}
        )
        return int(result.deleted_count)


__all__ = ["BeanieAuthSessionRepository", "BeanieStudioRepository", "BeanieUserRepository"]
