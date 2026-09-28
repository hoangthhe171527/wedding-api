"""Mảnh dùng chung giữa các use case của `wedding`."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.modules.wedding.application.ports import GuestUsage, PlanGate
from app.modules.wedding.domain.entities import Wedding, WeddingContent
from app.modules.wedding.domain.repositories import WeddingRepository
from app.modules.wedding.domain.services import plan_usage, validate_content


def site_url(slug: str) -> str:
    """Link web thiệp chung; link riêng từng khách là `<site_url>#<mã khách>`."""
    return f"{get_settings().PUBLIC_WEB_URL}/invite/{slug}"


def not_setup() -> NotFoundError:
    """Xưởng chưa khởi tạo đám cưới — web hiện dữ liệu mẫu kèm nút "Lưu dữ liệu mẫu"."""
    return NotFoundError(
        "Xưởng chưa có thông tin cưới. Hãy lưu dữ liệu mẫu hoặc bắt đầu từ trang trắng.",
        code="wedding_not_setup",
    )


async def require_wedding(weddings: WeddingRepository, tenant_id: UUID) -> Wedding:
    wedding = await weddings.find_by_tenant(tenant_id)
    if wedding is None:
        raise not_setup()
    return wedding


def ensure_valid(content: WeddingContent, known_templates: frozenset[str]) -> None:
    """Raises: ValidationError kèm lỗi theo từng trường."""
    errors = validate_content(content, known_templates=known_templates)
    if errors:
        raise ValidationError(
            "Thông tin cưới chưa hợp lệ. Vui lòng kiểm tra các trường được đánh dấu.",
            errors=errors,
        )


async def check_plan(wedding: Wedding, guests: GuestUsage, gate: PlanGate) -> dict[str, Any]:
    """Kết quả xét gói của đám cưới (xem `PlanGate`)."""
    used = await guests.usage(wedding.tenant_id)
    usage = plan_usage(
        wedding.content,
        guest_count=int(used.get("count", 0)),
        guest_templates=set(used.get("templates", [])),
        groups=set(used.get("groups", [])),
    )
    return await gate.check(wedding.tenant_id, usage)


async def ensure_plan(wedding: Wedding, guests: GuestUsage, gate: PlanGate) -> None:
    """Raises: ConflictError(`plan_required`) nếu đám cưới dùng tính năng ngoài gói."""
    result = await check_plan(wedding, guests, gate)
    found = result.get("violations") or []
    if found:
        raise ConflictError(
            f"Thiệp đang dùng tính năng của {result.get('required_label')}. "
            "Nâng gói hoặc đổi sang lựa chọn trong gói.",
            code="plan_required",
            errors={"plan": [str(item.get("message")) for item in found]},
        )


__all__ = [
    "check_plan",
    "ensure_plan",
    "ensure_valid",
    "not_setup",
    "require_wedding",
    "site_url",
]
