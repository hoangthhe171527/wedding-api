"""Router HTTP của `invitation` — web thiệp công khai, KHÔNG cần đăng nhập.

| Method | Path                                          | Quyền                         |
|--------|-----------------------------------------------|-------------------------------|
| GET    | /api/v1/public/invitations/{slug}?g=          | công khai (giới hạn tần suất) |
| POST   | /api/v1/public/invitations/{slug}/rsvp        | công khai (giới hạn tần suất) |
| GET    | /api/v1/public/invitations/{slug}/wishes      | công khai                     |
| POST   | /api/v1/public/invitations/{slug}/open        | công khai (giới hạn tần suất) |
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, Request, Response, status

from app.core import rate_limit
from app.core.dependencies import client_ip
from app.core.responses import ResponseEnvelope, ok, ok_list
from app.modules.invitation.infrastructure.providers import (
    GetInvitationDep,
    ListPublicWishesDep,
    RecordOpenDep,
    SubmitReplyDep,
)
from app.modules.invitation.interfaces.http.schemas import (
    InvitationOut,
    OpenIn,
    PublicWishOut,
    ReplyIn,
    ReplyOut,
)

router = APIRouter(prefix="/public/invitations", tags=["Web thiệp công khai"])

#: Hạn mức tính theo (IP, thiệp): khách dự tiệc dùng chung WiFi, nhà mạng di động
#: dùng chung IP (CGNAT) — tính theo IP trần là chặn nhầm cả bàn tiệc. Mục đích là
#: chặn dò mã khách hàng loạt trên MỘT thiệp, không điều tiết người xem thật.
_VIEW_LIMIT_PER_MINUTE = 300
#: Ghi nhận "đã mở" là một lệnh ghi DB — tách bộ đếm riêng, chặt hơn lượt xem.
_OPEN_LIMIT_PER_MINUTE = 120
#: Một người gửi phản hồi vài lần là cùng; nhiều hơn là rác.
_REPLY_LIMIT_PER_10_MIN = 30

Slug = Annotated[str, Path(min_length=3, max_length=60, pattern=r"^[a-z0-9-]+$")]


@router.get("/{slug}", response_model=ResponseEnvelope[InvitationOut], summary="Mở web thiệp")
async def get_invitation(
    slug: Slug,
    request: Request,
    response: Response,
    use_case: GetInvitationDep,
    g: Annotated[str | None, Query(max_length=12, description="Mã khách (phần sau dấu #).")] = None,
) -> dict[str, Any]:
    """Đám cưới đã xuất bản + ảnh + đúng vị khách ứng với mã (nếu có)."""
    await rate_limit.guard(
        "invitation_view",
        f"{client_ip(request) or 'unknown'}:{slug}",
        limit=_VIEW_LIMIT_PER_MINUTE,
        window_seconds=60,
        message="Bạn mở thiệp quá nhanh. Vui lòng thử lại sau ít phút.",
        code="invitation_rate_limited",
    )
    # Trang mang tên khách: không cho proxy/CDN dùng chung bản lưu giữa hai người.
    response.headers["Cache-Control"] = "private, no-store"
    return ok(InvitationOut.of(await use_case.execute(slug, g)))


@router.post(
    "/{slug}/rsvp",
    response_model=ResponseEnvelope[ReplyOut],
    status_code=status.HTTP_201_CREATED,
    summary="Gửi xác nhận tham dự và lời chúc",
)
async def submit_reply(
    slug: Slug, payload: ReplyIn, request: Request, use_case: SubmitReplyDep
) -> dict[str, Any]:
    """Link riêng: cập nhật đúng khách đó. Link chung: ghi theo tên khách tự điền."""
    await rate_limit.guard(
        "invitation_reply",
        f"{client_ip(request) or 'unknown'}:{slug}",
        limit=_REPLY_LIMIT_PER_10_MIN,
        window_seconds=600,
        message="Bạn đã gửi nhiều phản hồi. Vui lòng thử lại sau ít phút.",
        code="reply_rate_limited",
    )
    result = await use_case.execute(
        slug,
        code=payload.g,
        name=payload.name,
        status=payload.status,
        count=payload.count,
        message=payload.message,
    )
    return ok(ReplyOut.model_validate(result))


@router.get(
    "/{slug}/wishes",
    response_model=ResponseEnvelope[list[PublicWishOut]],
    summary="Lời chúc hiện trên web thiệp",
)
async def list_wishes(slug: Slug, use_case: ListPublicWishesDep) -> dict[str, Any]:
    return ok_list([PublicWishOut.model_validate(item) for item in await use_case.execute(slug)])


@router.post(
    "/{slug}/open",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Ghi nhận khách đã mở link riêng",
)
async def record_open(
    slug: Slug, payload: OpenIn, request: Request, use_case: RecordOpenDep
) -> Response:
    """Luôn trả 204 kể cả mã sai — không để lộ mã nào có thật."""
    await rate_limit.guard(
        "invitation_mark_open",
        f"{client_ip(request) or 'unknown'}:{slug}",
        limit=_OPEN_LIMIT_PER_MINUTE,
        window_seconds=60,
        message="Bạn mở thiệp quá nhanh. Vui lòng thử lại sau ít phút.",
        code="invitation_rate_limited",
    )
    await use_case.execute(slug, payload.g)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
