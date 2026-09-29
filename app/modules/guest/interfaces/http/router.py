"""Router HTTP của `guest` — quyền `guest.manage`, phạm vi xưởng của actor.

| Method | Path                      | Ghi chú                              |
|--------|---------------------------|--------------------------------------|
| GET    | /api/v1/guests            | phân trang, `per_page` tối đa 500    |
| POST   | /api/v1/guests            | thêm khách                           |
| POST   | /api/v1/guests/import     | nhập nhanh nhiều dòng                |
| PATCH  | /api/v1/guests/{id}       | sửa một phần (đã gửi, phản hồi...)   |
| DELETE | /api/v1/guests/{id}       | xoá mềm                              |
| GET    | /api/v1/guests/wishes     | sổ phản hồi, lời chúc từ web thiệp   |
| DELETE | /api/v1/guests/wishes/{id}| gỡ một lời chúc                      |
| GET    | /api/v1/guests/links       | link theo đối tượng                  |
| POST   | /api/v1/guests/links       | tạo link, đuôi rỗng = tự sinh        |
| PUT    | /api/v1/guests/links/{id}  | sửa tên, đuôi, mẫu                   |
| DELETE | /api/v1/guests/links/{id}  | xoá mềm, link đã gửi mở như chung    |
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.context import ActorContext
from app.core.dependencies import require_permissions
from app.core.pagination import PageParams, page_params
from app.core.permissions import Permission
from app.core.responses import (
    MessageOut,
    PaginatedEnvelope,
    ResponseEnvelope,
    ok,
    ok_list,
    ok_message,
    ok_page,
)
from app.modules.guest.infrastructure.providers import (
    CreateGuestDep,
    CreateLinkDep,
    DeleteGuestDep,
    DeleteLinkDep,
    DeleteWishDep,
    ImportGuestsDep,
    ListGuestsDep,
    ListLinksDep,
    ListWishesDep,
    UpdateGuestDep,
    UpdateLinkDep,
)
from app.modules.guest.interfaces.http.schemas import (
    GuestIn,
    GuestOut,
    GuestPatchIn,
    ImportIn,
    ImportOut,
    LinkIn,
    LinkOut,
    WishOut,
)

router = APIRouter(prefix="/guests", tags=["Khách mời"])

GuestManager = Annotated[ActorContext, require_permissions(Permission.GUEST_MANAGE)]


@router.get("", response_model=PaginatedEnvelope[GuestOut], summary="Danh sách khách mời")
async def list_guests(
    actor: GuestManager,
    use_case: ListGuestsDep,
    params: Annotated[PageParams, Depends(page_params)],
) -> dict[str, Any]:
    page = await use_case.execute(actor, params)
    return ok_page(page.map(GuestOut.of))


@router.get(
    "/wishes", response_model=ResponseEnvelope[list[WishOut]], summary="Phản hồi và lời chúc"
)
async def list_wishes(actor: GuestManager, use_case: ListWishesDep) -> dict[str, Any]:
    """Mọi phản hồi gửi từ web thiệp, mới nhất trước — kể cả khách mở link chung."""
    return ok_list([WishOut.of(item) for item in await use_case.execute(actor)])


@router.delete(
    "/wishes/{wish_id}", response_model=ResponseEnvelope[MessageOut], summary="Gỡ lời chúc"
)
async def delete_wish(
    wish_id: UUID, actor: GuestManager, use_case: DeleteWishDep
) -> dict[str, Any]:
    await use_case.execute(actor, wish_id)
    return ok_message("Đã gỡ lời chúc.")


@router.get("/links", response_model=ResponseEnvelope[list[LinkOut]], summary="Link theo đối tượng")
async def list_links(actor: GuestManager, use_case: ListLinksDep) -> dict[str, Any]:
    """Mỗi link một nhóm người, một mẫu thiệp — gửi vào nhóm Zalo mà không cần nhập khách."""
    return ok_list([LinkOut.of(item) for item in await use_case.execute(actor)])


@router.post(
    "/links",
    response_model=ResponseEnvelope[LinkOut],
    status_code=status.HTTP_201_CREATED,
    summary="Tạo link theo đối tượng",
)
async def create_link(
    payload: LinkIn, actor: GuestManager, use_case: CreateLinkDep
) -> dict[str, Any]:
    return ok(LinkOut.of(await use_case.execute(actor, payload.to_domain())))


@router.put("/links/{link_id}", response_model=ResponseEnvelope[LinkOut], summary="Sửa link")
async def update_link(
    link_id: UUID, payload: LinkIn, actor: GuestManager, use_case: UpdateLinkDep
) -> dict[str, Any]:
    return ok(LinkOut.of(await use_case.execute(actor, link_id, payload.to_domain())))


@router.delete("/links/{link_id}", response_model=ResponseEnvelope[MessageOut], summary="Xoá link")
async def delete_link(
    link_id: UUID, actor: GuestManager, use_case: DeleteLinkDep
) -> dict[str, Any]:
    await use_case.execute(actor, link_id)
    return ok_message("Đã xoá link.")


@router.post(
    "",
    response_model=ResponseEnvelope[GuestOut],
    status_code=status.HTTP_201_CREATED,
    summary="Thêm khách",
)
async def create_guest(
    payload: GuestIn, actor: GuestManager, use_case: CreateGuestDep
) -> dict[str, Any]:
    return ok(GuestOut.of(await use_case.execute(actor, payload.to_domain())))


@router.post(
    "/import",
    response_model=ResponseEnvelope[ImportOut],
    status_code=status.HTTP_201_CREATED,
    summary="Nhập nhanh nhiều khách",
)
async def import_guests(
    payload: ImportIn, actor: GuestManager, use_case: ImportGuestsDep
) -> dict[str, Any]:
    """`Danh xưng | Tên | Kèm theo | Nhóm | Nhà (trai/gái) | Số người` — mỗi dòng một thiệp."""
    return ok(ImportOut.of(await use_case.execute(actor, payload.text)))


@router.patch("/{guest_id}", response_model=ResponseEnvelope[GuestOut], summary="Sửa khách")
async def update_guest(
    guest_id: UUID, payload: GuestPatchIn, actor: GuestManager, use_case: UpdateGuestDep
) -> dict[str, Any]:
    return ok(GuestOut.of(await use_case.execute(actor, guest_id, payload.to_domain())))


@router.delete("/{guest_id}", response_model=ResponseEnvelope[MessageOut], summary="Xoá khách")
async def delete_guest(
    guest_id: UUID, actor: GuestManager, use_case: DeleteGuestDep
) -> dict[str, Any]:
    await use_case.execute(actor, guest_id)
    return ok_message("Đã xoá khách.")


__all__ = ["router"]
