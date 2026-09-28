"""Use case: bộ mẫu thiệp.

Khách dùng mẫu chỉ thấy mẫu đang mở. Người giữ `template.manage` thấy cả mẫu đã
tắt — để bật lại được. Phân nhánh theo QUYỀN, không theo tên vai trò (§0.1).
"""

from __future__ import annotations

from app.core.context import ActorContext
from app.core.permissions import Permission
from app.modules.template.domain.entities import Template
from app.modules.template.domain.repositories import TemplateRepository


class ListTemplates:
    """Danh sách mẫu theo thứ tự hiển thị."""

    def __init__(self, templates: TemplateRepository) -> None:
        self._templates = templates

    async def execute(self, actor: ActorContext) -> list[Template]:
        include_inactive = actor.has(Permission.TEMPLATE_MANAGE.value)
        return await self._templates.list_all(include_inactive=include_inactive)


__all__ = ["ListTemplates"]
