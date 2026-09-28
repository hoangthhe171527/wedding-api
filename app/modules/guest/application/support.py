"""Mảnh dùng chung giữa các use case của `guest`."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.modules.guest.application.ports import PlanGuestLimit
from app.modules.guest.domain.entities import Guest, GuestDraft
from app.modules.guest.domain.enums import MAX_GUESTS_PER_STUDIO
from app.modules.guest.domain.repositories import GuestCodeTakenError, GuestRepository
from app.modules.guest.domain.services import generate_code, validate_draft

#: Va chạm mã trong một xưởng vài trăm khách gần như không xảy ra; vài lượt thử
#: là thừa đủ, và có trần để không bao giờ lặp vô hạn.
_CODE_ATTEMPTS = 8


def guest_not_found() -> NotFoundError:
    return NotFoundError("Không tìm thấy khách mời.", code="guest_not_found")


def ensure_valid(draft: GuestDraft, known_templates: frozenset[str]) -> None:
    errors = validate_draft(draft, known_templates=known_templates)
    if errors:
        first = next(iter(errors.values()))[0]
        raise ValidationError(first, errors=errors)


async def _capacity_error(
    tenant_id: UUID, total: int, plan_limit: PlanGuestLimit | None
) -> ConflictError | None:
    if total > MAX_GUESTS_PER_STUDIO:
        return ConflictError(
            f"Mỗi xưởng tối đa {MAX_GUESTS_PER_STUDIO} thiệp mời.", code="guest_limit"
        )
    quota = await plan_limit.limit_for(tenant_id) if plan_limit is not None else None
    if quota is not None and total > int(quota["limit"]):
        return ConflictError(
            f"Web thiệp đang mở với {quota.get('label') or 'gói hiện tại'}: tối đa "
            f"{quota['limit']} thiệp mời. Nâng gói để thêm khách.",
            code="plan_required",
            errors={"plan": [f"Gói hiện tại cho tối đa {quota['limit']} thiệp mời."]},
        )
    return None


async def ensure_capacity(
    guests: GuestRepository,
    tenant_id: UUID,
    adding: int,
    plan_limit: PlanGuestLimit | None = None,
) -> None:
    """Kiểm NHANH trước khi ghi. Raises: ConflictError (trần hệ thống / hạn mức gói)."""
    error = await _capacity_error(tenant_id, await guests.count(tenant_id) + adding, plan_limit)
    if error is not None:
        raise error


async def settle_capacity(
    guests: GuestRepository,
    tenant_id: UUID,
    created: Sequence[Guest],
    plan_limit: PlanGuestLimit | None = None,
) -> None:
    """Kiểm LẠI sau khi ghi: hai lượt thêm khách song song có thể cùng qua bước kiểm
    trước. Vượt thì xoá hẳn chính các khách vừa tạo rồi báo lỗi — không cần khoá.

    Raises: ConflictError.
    """
    error = await _capacity_error(tenant_id, await guests.count(tenant_id), plan_limit)
    if error is not None:
        await guests.discard(tenant_id, [guest.id for guest in created])
        raise error


async def create_many_with_codes(
    guests: GuestRepository,
    tenant_id: UUID,
    drafts: Sequence[GuestDraft],
    *,
    actor_id: UUID | None,
) -> list[Guest]:
    """Tạo hàng loạt bằng MỘT lệnh ghi (thay vì mỗi khách một lượt); dòng nào trùng mã
    thì sinh mã khác và chỉ thử lại những dòng đó."""
    created: list[Guest] = []
    pending = list(drafts)
    for _ in range(_CODE_ATTEMPTS):
        if not pending:
            return created
        done, failed = await guests.create_many(
            tenant_id, [(generate_code(), draft) for draft in pending], actor_id=actor_id
        )
        created.extend(done)
        pending = [pending[index] for index in failed]
    if pending:
        await guests.discard(tenant_id, [guest.id for guest in created])
        raise ConflictError(
            "Chưa sinh được mã khách. Vui lòng thử lại.", code="guest_code_exhausted"
        )
    return created


async def create_with_code(
    guests: GuestRepository,
    tenant_id: UUID,
    draft: GuestDraft,
    *,
    actor_id: UUID | None,
    code: str | None = None,
) -> Guest:
    """Tạo khách với mã ngẫu nhiên (hoặc mã cho sẵn — dữ liệu mẫu), thử lại khi va chạm."""
    for attempt in range(_CODE_ATTEMPTS):
        candidate = code if (code and attempt == 0) else generate_code()
        try:
            return await guests.create(tenant_id, candidate, draft, actor_id=actor_id)
        except GuestCodeTakenError:
            continue
    raise ConflictError("Chưa sinh được mã khách. Vui lòng thử lại.", code="guest_code_exhausted")


__all__ = [
    "create_many_with_codes",
    "create_with_code",
    "ensure_capacity",
    "ensure_valid",
    "guest_not_found",
    "settle_capacity",
]
