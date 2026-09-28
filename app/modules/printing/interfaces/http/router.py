"""Router HTTP của `printing`.

| Method | Path                                         | Quyền            |
|--------|----------------------------------------------|------------------|
| GET    | /api/v1/printing/options                     | công khai        |
| GET    | /api/v1/printing/requests                    | `studio.manage`  |
| POST   | /api/v1/printing/requests                    | `studio.manage`  |
| POST   | /api/v1/printing/requests/{id}/cancel        | `studio.manage`  |
| GET    | /api/v1/admin/print-requests                 | `studio.oversee` |
| PATCH  | /api/v1/admin/print-requests/{id}            | `studio.oversee` |
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.context import ActorContext
from app.core.dependencies import require_permissions
from app.core.pagination import PageParams, page_params
from app.core.permissions import Permission
from app.core.responses import PaginatedEnvelope, ResponseEnvelope, ok, ok_list, ok_page
from app.modules.printing.domain.enums import PrintStatus
from app.modules.printing.infrastructure.providers import (
    CancelPrintRequestDep,
    ListAllPrintRequestsDep,
    ListPrintRequestsDep,
    SubmitPrintRequestDep,
    UpdatePrintRequestDep,
)
from app.modules.printing.interfaces.http.schemas import (
    PrintOptionsOut,
    PrintRequestIn,
    PrintRequestOut,
    PrintUpdateIn,
)

router = APIRouter(tags=["In thiệp"])

StudioEditor = Annotated[ActorContext, require_permissions(Permission.STUDIO_MANAGE)]
Operator = Annotated[ActorContext, require_permissions(Permission.STUDIO_OVERSEE)]


@router.get(
    "/printing/options",
    response_model=ResponseEnvelope[PrintOptionsOut],
    summary="Chất giấy, khổ thiệp, trạng thái",
)
async def print_options() -> dict[str, Any]:
    return ok(PrintOptionsOut.current())


@router.get(
    "/printing/requests",
    response_model=ResponseEnvelope[list[PrintRequestOut]],
    summary="Yêu cầu in của xưởng",
)
async def list_requests(actor: StudioEditor, use_case: ListPrintRequestsDep) -> dict[str, Any]:
    items = await use_case.execute(actor.tenant_id)
    return ok_list([PrintRequestOut.of(item) for item in items])


@router.post(
    "/printing/requests",
    response_model=ResponseEnvelope[PrintRequestOut],
    status_code=status.HTTP_201_CREATED,
    summary="Gửi yêu cầu in thiệp",
)
async def submit_request(
    payload: PrintRequestIn, actor: StudioEditor, use_case: SubmitPrintRequestDep
) -> dict[str, Any]:
    """Không báo giá ở đây: đội vận hành liên hệ qua Zalo để báo giá và chốt mẫu."""
    created = await use_case.execute(actor.tenant_id, payload.to_domain(), actor_id=actor.user_id)
    return ok(PrintRequestOut.of(created))


@router.post(
    "/printing/requests/{request_id}/cancel",
    response_model=ResponseEnvelope[PrintRequestOut],
    summary="Huỷ yêu cầu in (khi chưa vào in)",
)
async def cancel_request(
    request_id: UUID, actor: StudioEditor, use_case: CancelPrintRequestDep
) -> dict[str, Any]:
    cancelled = await use_case.execute(actor.tenant_id, request_id, actor_id=actor.user_id)
    return ok(PrintRequestOut.of(cancelled))


@router.get(
    "/admin/print-requests",
    response_model=PaginatedEnvelope[PrintRequestOut],
    tags=["Quản trị hệ thống"],
    summary="Mọi yêu cầu in",
)
async def admin_list(
    actor: Operator,
    use_case: ListAllPrintRequestsDep,
    params: Annotated[PageParams, Depends(page_params)],
    request_status: Annotated[PrintStatus | None, Query(alias="status")] = None,
) -> dict[str, Any]:
    del actor
    page = await use_case.execute(params, request_status)
    return ok_page(page.map(lambda item: PrintRequestOut.of(item, admin=True)))


@router.patch(
    "/admin/print-requests/{request_id}",
    response_model=ResponseEnvelope[PrintRequestOut],
    tags=["Quản trị hệ thống"],
    summary="Cập nhật tiến độ yêu cầu in",
)
async def admin_update(
    request_id: UUID, payload: PrintUpdateIn, actor: Operator, use_case: UpdatePrintRequestDep
) -> dict[str, Any]:
    updated = await use_case.execute(
        request_id, payload.status, payload.admin_note, actor_id=actor.user_id
    )
    return ok(PrintRequestOut.of(updated, admin=True))


__all__ = ["router"]
