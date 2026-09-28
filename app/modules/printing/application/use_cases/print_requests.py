"""Use case: khách gửi yêu cầu in, đội vận hành cập nhật tiến độ.

Không có giá và không thanh toán online: sau khi nhận yêu cầu, đội vận hành
liên hệ qua Zalo / điện thoại để báo giá và chốt mẫu.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from app.core import audit
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.pages import Page, PageParams
from app.modules.printing.domain.entities import PrintRequest, PrintSpec
from app.modules.printing.domain.enums import CANCELLABLE, PrintStatus
from app.modules.printing.domain.repositories import PrintRequestRepository
from app.modules.printing.domain.services import normalize_phone, spec_errors

#: Một đám cưới cần in vài đợt là cùng; nhiều hơn là gửi nhầm / rác.
MAX_OPEN_REQUESTS = 3


def _not_found() -> NotFoundError:
    return NotFoundError("Không tìm thấy yêu cầu in.", code="print_request_not_found")


class SubmitPrintRequest:
    def __init__(self, requests: PrintRequestRepository) -> None:
        self._requests = requests

    async def execute(self, tenant_id: UUID, spec: PrintSpec, *, actor_id: UUID) -> PrintRequest:
        """Raises: ValidationError (thiếu thông tin), ConflictError (quá nhiều yêu cầu mở)."""
        spec = replace(
            spec,
            contact_name=spec.contact_name.strip(),
            contact_phone=normalize_phone(spec.contact_phone),
            address=spec.address.strip(),
            note=spec.note.strip(),
        )
        errors = spec_errors(spec)
        if errors:
            raise ValidationError(
                "Yêu cầu in còn thiếu thông tin.", code="print_invalid", errors=errors
            )
        if await self._requests.count_open(tenant_id) >= MAX_OPEN_REQUESTS:
            raise ConflictError(
                "Bạn đang có nhiều yêu cầu in chưa xong. Nhắn Zalo để chúng tôi hỗ trợ.",
                code="print_too_many",
            )
        return await self._requests.create(tenant_id, spec, actor_id=actor_id)


class ListPrintRequests:
    def __init__(self, requests: PrintRequestRepository) -> None:
        self._requests = requests

    async def execute(self, tenant_id: UUID) -> list[PrintRequest]:
        return await self._requests.list_for_tenant(tenant_id)


class CancelPrintRequest:
    def __init__(self, requests: PrintRequestRepository) -> None:
        self._requests = requests

    async def execute(self, tenant_id: UUID, request_id: UUID, *, actor_id: UUID) -> PrintRequest:
        """Raises: NotFoundError, ConflictError (đã vào in)."""
        found = await self._requests.get(tenant_id, request_id)
        if found is None:
            raise _not_found()
        if found.status not in CANCELLABLE:
            raise ConflictError(
                "Thiệp đã vào in, không huỷ trên hệ thống được. Nhắn Zalo để được hỗ trợ.",
                code="print_locked",
            )
        # Điều kiện "còn huỷ được" kiểm TRONG lệnh ghi: đội vận hành vừa chuyển sang
        # "Đang in" giữa lúc đọc và lúc ghi thì lệnh huỷ không khớp, không ghi đè.
        updated = await self._requests.set_status(
            request_id,
            PrintStatus.CANCELLED,
            None,
            actor_id=actor_id,
            tenant_id=tenant_id,
            only_from=CANCELLABLE,
        )
        if updated is None:
            raise ConflictError(
                "Thiệp đã vào in, không huỷ trên hệ thống được. Nhắn Zalo để được hỗ trợ.",
                code="print_locked",
            )
        return updated


class ListAllPrintRequests:
    def __init__(self, requests: PrintRequestRepository) -> None:
        self._requests = requests

    async def execute(self, params: PageParams, status: PrintStatus | None) -> Page[PrintRequest]:
        return await self._requests.list_page(params, status)


class UpdatePrintRequest:
    """Đội vận hành chuyển trạng thái và ghi chú (giá đã báo, ngày giao...)."""

    def __init__(self, requests: PrintRequestRepository) -> None:
        self._requests = requests

    async def execute(
        self, request_id: UUID, status: PrintStatus, admin_note: str | None, *, actor_id: UUID
    ) -> PrintRequest:
        updated = await self._requests.set_status(
            request_id,
            status,
            admin_note.strip() if admin_note is not None else None,
            actor_id=actor_id,
        )
        if updated is None:
            raise _not_found()
        await audit.record(
            "print.status_changed",
            actor_id=actor_id,
            target_type="print_request",
            target_id=request_id,
            tenant_id=updated.tenant_id,
            details={"status": status.value, "admin_note": admin_note or ""},
        )
        return updated
