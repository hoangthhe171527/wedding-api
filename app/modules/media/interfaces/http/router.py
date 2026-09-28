"""Router HTTP của `media`.

| Method | Path                               | Quyền                 |
|--------|------------------------------------|-----------------------|
| GET    | /api/v1/photos                     | `studio.manage`       |
| POST   | /api/v1/photos                     | `studio.manage`       |
| POST   | /api/v1/photos/{id}/cover          | `studio.manage`       |
| DELETE | /api/v1/photos/{id}                | `studio.manage`       |
| GET    | /api/v1/media/photos/{id}?exp&sig[&w=sm] | công khai, URL đã ký |
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, File, Query, Response, UploadFile, status
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.context import ActorContext
from app.core.dependencies import require_permissions
from app.core.errors import ValidationError
from app.core.permissions import Permission
from app.core.responses import ResponseEnvelope, ok_list
from app.modules.media.infrastructure.providers import (
    DeletePhotoDep,
    ListPhotosDep,
    MakeCoverDep,
    ReadPhotoDep,
    UploadPhotoDep,
)
from app.modules.media.interfaces.http.schemas import PhotoOut, photos_out

router = APIRouter(tags=["Ảnh cưới"])

StudioEditor = Annotated[ActorContext, require_permissions(Permission.STUDIO_MANAGE)]


@router.get("/photos", response_model=ResponseEnvelope[list[PhotoOut]], summary="Album ảnh cưới")
async def list_photos(actor: StudioEditor, use_case: ListPhotosDep) -> dict[str, Any]:
    """Ảnh theo thứ tự album; ảnh đầu (`is_cover`) là ảnh bìa."""
    return ok_list(photos_out(await use_case.execute(actor)))


@router.post(
    "/photos",
    response_model=ResponseEnvelope[list[PhotoOut]],
    status_code=status.HTTP_201_CREATED,
    summary="Tải ảnh lên",
)
async def upload_photo(
    actor: StudioEditor,
    upload: UploadPhotoDep,
    listing: ListPhotosDep,
    file: Annotated[UploadFile, File(description="Ảnh JPG/PNG/WebP")],
) -> dict[str, Any]:
    """Trả lại TRỌN album sau khi thêm — web thay danh sách một lần, không ghép tay."""
    # Đọc dư một byte: biết tệp vượt hạn mức mà không phải nạp cả tệp khổng lồ.
    limit = get_settings().PHOTO_MAX_BYTES
    data = await file.read(limit + 1)
    if not data:
        raise ValidationError("Tệp ảnh rỗng.", code="photo_empty")
    await upload.execute(actor, data, filename=file.filename or "ảnh")
    return ok_list(photos_out(await listing.execute(actor)))


@router.post(
    "/photos/{photo_id}/cover",
    response_model=ResponseEnvelope[list[PhotoOut]],
    summary="Làm ảnh bìa",
)
async def make_cover(
    photo_id: UUID, actor: StudioEditor, use_case: MakeCoverDep, listing: ListPhotosDep
) -> dict[str, Any]:
    await use_case.execute(actor, photo_id)
    return ok_list(photos_out(await listing.execute(actor)))


@router.delete(
    "/photos/{photo_id}", response_model=ResponseEnvelope[list[PhotoOut]], summary="Xoá ảnh"
)
async def delete_photo(
    photo_id: UUID, actor: StudioEditor, use_case: DeletePhotoDep, listing: ListPhotosDep
) -> dict[str, Any]:
    await use_case.execute(actor, photo_id)
    return ok_list(photos_out(await listing.execute(actor)))


@router.get(
    "/media/photos/{photo_id}",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}, "image/png": {}}}},
    summary="Tải byte ảnh qua URL đã ký",
)
async def read_photo(
    photo_id: UUID,
    use_case: ReadPhotoDep,
    exp: Annotated[int, Query(ge=0)],
    sig: Annotated[str, Query(min_length=64, max_length=64)],
    w: Annotated[Literal["sm"] | None, Query(description="`sm`: bản nhỏ cho điện thoại")] = None,
) -> Response:
    """Không cần đăng nhập — chữ ký là giấy phép. Sai/hết hạn -> 404."""
    photo = await use_case.execute(photo_id, expires_at=exp, signature=sig, small=w == "sm")
    if photo.redirect:
        # 302 chứ không 301: URL ký của kho đổi theo giờ, không được lưu vĩnh viễn.
        return RedirectResponse(
            photo.redirect, status_code=302, headers={"Cache-Control": "private, max-age=300"}
        )
    return Response(
        content=photo.data,
        media_type=photo.content_type,
        headers={
            # URL mang chữ ký theo giờ nên nội dung ứng với một URL không bao giờ
            # đổi: cho trình duyệt giữ lâu, không cho proxy chung lưu.
            "Cache-Control": "private, max-age=86400, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )


__all__ = ["router"]
