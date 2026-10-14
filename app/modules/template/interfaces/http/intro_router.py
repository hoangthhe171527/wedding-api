"""Router HTTP thư viện video mở thiệp (thuộc `template`).

| Method | Path                                  | Quyền                 |
|--------|---------------------------------------|-----------------------|
| GET    | /api/v1/intros                        | `template.view`       |
| POST   | /api/v1/intros                        | `template.manage`     |
| PATCH  | /api/v1/intros/{id}                   | `template.manage`     |
| DELETE | /api/v1/intros/{id}                   | `template.manage`     |
| GET    | /api/v1/media/intros/{id}?exp&sig     | công khai, URL đã ký  |

Mọi lệnh ghi trả lại TRỌN thư viện (như `GET` của người quản lý) — web thay danh
sách một lần, không ghép tay.
"""

from __future__ import annotations

import re
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile, status
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.context import ActorContext
from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.core.responses import ResponseEnvelope, ok_list
from app.modules.template.application.use_cases import IntroPatch
from app.modules.template.application.use_cases.intros import intro_not_found
from app.modules.template.domain.intros import INTRO_NAME_MAX
from app.modules.template.infrastructure.providers import (
    DeleteIntroDep,
    ListIntrosDep,
    ReadIntroDep,
    UpdateIntroDep,
    UploadIntroDep,
)
from app.modules.template.interfaces.http.schemas import IntroOut, IntroPatchIn

router = APIRouter(tags=["Video mở thiệp"])

Viewer = Annotated[ActorContext, require_permissions(Permission.TEMPLATE_VIEW)]
Manager = Annotated[ActorContext, require_permissions(Permission.TEMPLATE_MANAGE)]

#: URL mang chữ ký theo giờ nên nội dung ứng với một URL không bao giờ đổi: cho
#: trình duyệt giữ lâu, không cho proxy chung lưu.
_MEDIA_HEADERS = {
    "Cache-Control": "private, max-age=86400, immutable",
    "X-Content-Type-Options": "nosniff",
    "Accept-Ranges": "bytes",
}
_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


class _BadRangeError(Exception):
    """Header `Range` sai cú pháp hoặc nằm ngoài video -> 416."""


def _parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    """`Range: bytes=a-b | a- | -n` -> `(đầu, cuối)` gồm hai đầu; không có header -> None.

    Chỉ nhận MỘT đoạn — `<video>` của trình duyệt không bao giờ xin nhiều đoạn.
    Raises: _BadRangeError.
    """
    if header is None:
        return None
    match = _RANGE_RE.match(header.strip())
    if match is None:
        raise _BadRangeError
    first, last = match.groups()
    if not first:
        # `-n`: n byte cuối.
        if not last or int(last) == 0 or size == 0:
            raise _BadRangeError
        return max(size - int(last), 0), size - 1
    start = int(first)
    end = int(last) if last else size - 1
    if start >= size or end < start:
        raise _BadRangeError
    return start, min(end, size - 1)


async def _library(listing: ListIntrosDep, actor: ActorContext) -> dict[str, Any]:
    return ok_list([IntroOut.of(view) for view in await listing.execute(actor)])


@router.get("/intros", response_model=ResponseEnvelope[list[IntroOut]], summary="Video mở thiệp")
async def list_intros(actor: Viewer, listing: ListIntrosDep) -> dict[str, Any]:
    """Video đang mở; người quản lý bộ mẫu thấy cả video đã tắt."""
    return await _library(listing, actor)


@router.post(
    "/intros",
    response_model=ResponseEnvelope[list[IntroOut]],
    status_code=status.HTTP_201_CREATED,
    summary="Tải video mở thiệp lên",
)
async def upload_intro(
    actor: Manager,
    upload: UploadIntroDep,
    listing: ListIntrosDep,
    file: Annotated[UploadFile, File(description="Video MP4/WebM")],
    name: Annotated[str | None, Form(max_length=INTRO_NAME_MAX)] = None,
) -> dict[str, Any]:
    """`name` trống = tên tệp bỏ đuôi. Video mới xếp cuối thư viện."""
    # Đọc dư một byte: biết tệp vượt hạn mức mà không phải nạp cả tệp khổng lồ.
    data = await file.read(get_settings().INTRO_MAX_BYTES + 1)
    await upload.execute(actor, data, filename=file.filename, name=name)
    return await _library(listing, actor)


@router.patch(
    "/intros/{intro_id}",
    response_model=ResponseEnvelope[list[IntroOut]],
    summary="Đổi tên / bật tắt / thứ tự một video",
)
async def update_intro(
    intro_id: UUID,
    payload: IntroPatchIn,
    actor: Manager,
    use_case: UpdateIntroDep,
    listing: ListIntrosDep,
) -> dict[str, Any]:
    await use_case.execute(
        actor,
        intro_id,
        IntroPatch(name=payload.name, is_active=payload.is_active, order=payload.order),
    )
    return await _library(listing, actor)


@router.delete(
    "/intros/{intro_id}",
    response_model=ResponseEnvelope[list[IntroOut]],
    summary="Xoá video mở thiệp",
)
async def delete_intro(
    intro_id: UUID, actor: Manager, use_case: DeleteIntroDep, listing: ListIntrosDep
) -> dict[str, Any]:
    """Thiệp đang chọn video này lùi về hiệu ứng cửa."""
    await use_case.execute(actor, intro_id)
    return await _library(listing, actor)


@router.api_route(
    "/media/intros/{intro_id}",
    methods=["GET", "HEAD"],
    response_class=Response,
    responses={
        200: {"content": {"video/mp4": {}, "video/webm": {}}},
        206: {"description": "Một đoạn video (`Range`)"},
        416: {"description": "`Range` không hợp lệ"},
    },
    summary="Phát video mở thiệp qua URL đã ký",
)
async def read_intro(
    intro_id: UUID,
    request: Request,
    use_case: ReadIntroDep,
    exp: Annotated[int, Query(ge=0)],
    sig: Annotated[str, Query(min_length=64, max_length=64)],
) -> Response:
    """Không cần đăng nhập — chữ ký là giấy phép. Sai/hết hạn/đã xoá -> 404.

    Hỗ trợ HTTP Range (206): Safari trên iOS không phát `<video>` nếu máy chủ
    không trả được từng đoạn.
    """
    media = await use_case.open(intro_id, expires_at=exp, signature=sig)
    if media.redirect:
        # 302 chứ không 301: URL ký của kho đổi theo giờ, không được lưu vĩnh viễn.
        return RedirectResponse(
            media.redirect, status_code=302, headers={"Cache-Control": "private, max-age=300"}
        )
    intro = media.intro
    if intro is None:  # `open` trả hoặc chuyển hướng, hoặc video — không bao giờ cả hai rỗng
        raise intro_not_found()
    size = intro.size
    try:
        span = _parse_range(request.headers.get("range"), size)
    except _BadRangeError:
        return Response(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            headers={**_MEDIA_HEADERS, "Content-Range": f"bytes */{size}"},
        )
    start, end = span if span is not None else (0, size - 1)
    headers = dict(_MEDIA_HEADERS)
    if span is not None:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    code = status.HTTP_206_PARTIAL_CONTENT if span is not None else status.HTTP_200_OK
    if request.method == "HEAD" or size == 0:
        headers["Content-Length"] = str(end - start + 1 if size else 0)
        return Response(status_code=code, media_type=intro.content_type, headers=headers)
    data = await use_case.read(intro, start, end)
    return Response(content=data, status_code=code, media_type=intro.content_type, headers=headers)


__all__ = ["router"]
