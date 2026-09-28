"""Nhật ký thao tác quản trị — CHỈ GHI THÊM, không sửa, không xoá.

Trả lời được "ai nâng gói cho xưởng này, lúc nào, với ghi chú gì" khi có tranh
chấp. Admin có toàn quyền, nên mọi thao tác quản trị lên dữ liệu của khách (cấp gói,
xác nhận đơn, đổi tiến độ in, khoá tài khoản, sửa mẫu / mặc định hệ thống) đều ghi.

Ghi hỏng thì chỉ ghi log cảnh báo, KHÔNG làm hỏng thao tác chính — giống log.
"""

from __future__ import annotations

from typing import Any, ClassVar
from uuid import UUID

import structlog
from pydantic import Field

from app.core.base_model import ASCENDING, DESCENDING, BaseDocument, IndexModel
from app.core.logging import get_logger

log = get_logger(__name__)


class AuditEventDocument(BaseDocument):
    r"""Một thao tác quản trị.

    Ngoại lệ có chủ ý với §0.4 (không bắt buộc \`tenant_id\`): nhật ký toàn hệ thống
    của đội vận hành; \`tenant_id\` là xưởng BỊ tác động (nếu có).
    """

    action: str
    actor_id: UUID | None = None
    target_type: str
    target_id: str
    tenant_id: UUID | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str = ""

    class Settings(BaseDocument.Settings):
        name = "audit_events"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel([("created_at", DESCENDING)], name="ix_audit_recent"),
            IndexModel(
                [("tenant_id", ASCENDING), ("created_at", DESCENDING)], name="ix_audit_tenant"
            ),
        ]


async def record(
    action: str,
    *,
    actor_id: UUID | None,
    target_type: str,
    target_id: object,
    tenant_id: UUID | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Ghi một dòng nhật ký (request_id lấy từ ngữ cảnh request hiện tại)."""
    context = structlog.contextvars.get_contextvars()
    event = AuditEventDocument(
        action=action,
        actor_id=actor_id,
        target_type=target_type,
        target_id=str(target_id),
        tenant_id=tenant_id,
        details=details or {},
        request_id=str(context.get("request_id", "")),
    )
    try:
        await event.insert()
    except Exception as exc:
        log.warning("audit_write_failed", action=action, error=str(exc))


async def recent(
    *, limit: int = 200, tenant_id: UUID | None = None, action: str | None = None
) -> list[AuditEventDocument]:
    criteria: dict[str, Any] = {}
    if tenant_id is not None:
        criteria["tenant_id"] = tenant_id
    if action:
        criteria["action"] = action
    return await AuditEventDocument.find(criteria).sort("-created_at").limit(limit).to_list()


CORE_DOCUMENTS: list[type[BaseDocument]] = [AuditEventDocument]

__all__ = ["CORE_DOCUMENTS", "AuditEventDocument", "recent", "record"]
