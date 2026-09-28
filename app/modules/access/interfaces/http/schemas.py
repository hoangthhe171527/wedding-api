"""Schema HTTP của `access`."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.core.audit import AuditEventDocument
from app.core.permissions import PERMISSION_GROUP_LABELS, PermissionDefinition
from app.modules.access.domain.entities import Role


class PermissionOut(BaseModel):
    """Một quyền trong catalog, kèm nhãn tiếng Việt."""

    slug: str
    label: str
    group: str
    group_label: str
    description: str

    @classmethod
    def of(cls, item: PermissionDefinition) -> PermissionOut:
        return cls(
            slug=item.slug.value,
            label=item.label,
            group=item.group.value,
            group_label=PERMISSION_GROUP_LABELS[item.group],
            description=item.description,
        )


class RoleOut(BaseModel):
    """Một vai trò."""

    id: UUID
    slug: str
    label: str
    permissions: list[str]

    @classmethod
    def of(cls, role: Role) -> RoleOut:
        return cls(id=role.id, slug=role.slug, label=role.label, permissions=list(role.permissions))


__all__ = ["PermissionOut", "RoleOut"]


class AuditEventOut(BaseModel):
    """Một dòng nhật ký thao tác quản trị."""

    id: UUID
    action: str
    actor_id: UUID | None
    target_type: str
    target_id: str
    studio_id: UUID | None
    details: dict[str, Any]
    request_id: str
    created_at: datetime | None

    @classmethod
    def of(cls, item: AuditEventDocument) -> AuditEventOut:
        return cls(
            id=item.id,
            action=item.action,
            actor_id=item.actor_id,
            target_type=item.target_type,
            target_id=item.target_id,
            studio_id=item.tenant_id,
            details=item.details,
            request_id=item.request_id,
            created_at=item.created_at,
        )
