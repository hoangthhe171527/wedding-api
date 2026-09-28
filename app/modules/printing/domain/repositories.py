"""Hợp đồng lưu trữ của `printing`."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.core.pages import Page, PageParams
from app.modules.printing.domain.entities import PrintRequest, PrintSpec
from app.modules.printing.domain.enums import PrintStatus


class PrintRequestRepository(Protocol):
    """Truy cập collection `print_requests`."""

    async def create(self, tenant_id: UUID, spec: PrintSpec, *, actor_id: UUID) -> PrintRequest: ...

    async def list_for_tenant(self, tenant_id: UUID) -> list[PrintRequest]: ...

    async def get(self, tenant_id: UUID, request_id: UUID) -> PrintRequest | None: ...

    async def get_any(self, request_id: UUID) -> PrintRequest | None:
        """Màn vận hành: tra theo id, không lọc xưởng (quyền đã kiểm ở router)."""
        ...

    async def list_page(self, params: PageParams, status: PrintStatus | None) -> Page[PrintRequest]:
        """Màn vận hành: mọi xưởng, mới nhất trước."""
        ...

    async def set_status(
        self,
        request_id: UUID,
        status: PrintStatus,
        admin_note: str | None,
        *,
        actor_id: UUID,
        tenant_id: UUID | None = None,
        only_from: frozenset[PrintStatus] | None = None,
    ) -> PrintRequest | None:
        """Nguyên tử; `only_from` = chỉ đổi khi trạng thái hiện tại thuộc tập này."""
        ...

    async def count_open(self, tenant_id: UUID) -> int:
        """Yêu cầu còn đang xử lý của một xưởng — chặn gửi dồn."""
        ...
