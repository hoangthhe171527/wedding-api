"""Hiện thực Beanie của repository `access`."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from beanie.operators import In
from pymongo.errors import DuplicateKeyError

from app.modules.access.domain.entities import Role, RoleAssignment
from app.modules.access.domain.role_blueprints import RoleBlueprint
from app.modules.access.infrastructure.persistence.models import (
    RoleAssignmentDocument,
    RoleDocument,
)


def _role(doc: RoleDocument) -> Role:
    return Role(id=doc.id, slug=doc.slug, label=doc.label, permissions=tuple(doc.permissions))


def _assignment(doc: RoleAssignmentDocument) -> RoleAssignment:
    return RoleAssignment(
        id=doc.id, tenant_id=doc.tenant_id, user_id=doc.user_id, role_id=doc.role_id
    )


class BeanieRoleRepository:
    """`RoleRepository` trên Mongo."""

    async def list_all(self) -> list[Role]:
        docs = await RoleDocument.find_all().sort("+created_at").to_list()
        return [_role(doc) for doc in docs]

    async def find_by_slug(self, slug: str) -> Role | None:
        doc = await RoleDocument.find_one(RoleDocument.slug == slug)
        return _role(doc) if doc else None

    async def find_many(self, role_ids: Sequence[UUID]) -> list[Role]:
        if not role_ids:
            return []
        docs = await RoleDocument.find(In(RoleDocument.id, list(role_ids))).to_list()
        return [_role(doc) for doc in docs]

    async def upsert_blueprint(self, blueprint: RoleBlueprint) -> Role:
        existing = await RoleDocument.find_one(RoleDocument.slug == blueprint.slug)
        if existing is not None:
            missing = [slug for slug in blueprint.permissions if slug not in existing.permissions]
            if missing:
                # Chỉ thêm, không gỡ: quyền cấp tay cho vai trò vẫn giữ nguyên.
                existing.permissions = [*existing.permissions, *missing]
                await existing.save()
            return _role(existing)
        doc = RoleDocument(
            slug=blueprint.slug, label=blueprint.label, permissions=list(blueprint.permissions)
        )
        try:
            await doc.insert()
        except DuplicateKeyError:
            # Hai tiến trình khởi động cùng lúc cùng seed: bên thua đọc lại.
            again = await RoleDocument.find_one(RoleDocument.slug == blueprint.slug)
            if again is None:
                raise
            return _role(again)
        return _role(doc)


class BeanieRoleAssignmentRepository:
    """`RoleAssignmentRepository` trên Mongo."""

    async def list_for_user(self, tenant_id: UUID, user_id: UUID) -> list[RoleAssignment]:
        docs = await RoleAssignmentDocument.scoped(
            tenant_id, RoleAssignmentDocument.user_id == user_id
        ).to_list()
        return [_assignment(doc) for doc in docs]

    async def list_for_users(self, user_ids: Sequence[UUID]) -> list[RoleAssignment]:
        if not user_ids:
            return []
        docs = await RoleAssignmentDocument.find(
            In(RoleAssignmentDocument.user_id, list(user_ids)),
            RoleAssignmentDocument.deleted_at == None,  # noqa: E711 — cú pháp truy vấn Beanie
        ).to_list()
        return [_assignment(doc) for doc in docs]

    async def assign(self, tenant_id: UUID, user_id: UUID, role_id: UUID) -> RoleAssignment:
        existing = await RoleAssignmentDocument.scoped(
            tenant_id,
            RoleAssignmentDocument.user_id == user_id,
            RoleAssignmentDocument.role_id == role_id,
        ).first_or_none()
        if existing is not None:
            return _assignment(existing)
        doc = RoleAssignmentDocument(tenant_id=tenant_id, user_id=user_id, role_id=role_id)
        await doc.insert()
        return _assignment(doc)


__all__ = ["BeanieRoleAssignmentRepository", "BeanieRoleRepository"]
