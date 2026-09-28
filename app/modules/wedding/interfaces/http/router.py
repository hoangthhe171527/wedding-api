"""Router HTTP của `wedding`.

| Method | Path                          | Quyền            |
|--------|-------------------------------|------------------|
| GET    | /api/v1/wedding               | `studio.manage`  |
| POST   | /api/v1/wedding/setup         | `studio.manage`  |
| PUT    | /api/v1/wedding               | `studio.manage`  |
| PUT    | /api/v1/wedding/checklist     | `studio.manage`  |
| PUT    | /api/v1/wedding/publication   | `studio.manage`  |
| GET    | /api/v1/wedding/plan-check    | `studio.manage`  |
| GET    | /api/v1/wedding/wording/ai    | `studio.manage`  |
| POST   | /api/v1/wedding/wording/suggest | `studio.manage` |
| GET    | /api/v1/admin/studios         | `studio.oversee` |

Phạm vi dữ liệu (chỉ đám cưới của xưởng mình) nằm ở use case qua `actor.tenant_id`.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, status

from app.core import rate_limit
from app.core.context import ActorContext
from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.core.responses import ResponseEnvelope, ok, ok_list
from app.modules.wedding.application.use_cases import SetupMode
from app.modules.wedding.infrastructure.providers import (
    CheckWeddingPlanDep,
    GetWeddingDep,
    ListStudiosDep,
    SaveChecklistDep,
    SaveWeddingDep,
    SetPublicationDep,
    SetupWeddingDep,
    SuggestWordingDep,
)
from app.modules.wedding.interfaces.http.schemas import (
    AiStatusOut,
    ChecklistIn,
    PlanCheckOut,
    PublicationIn,
    SetupIn,
    StudioOverviewOut,
    WeddingContentIO,
    WeddingOut,
    WordingSuggestIn,
    WordingSuggestOut,
)

router = APIRouter(tags=["Thông tin cưới"])

StudioEditor = Annotated[ActorContext, require_permissions(Permission.STUDIO_MANAGE)]


@router.get("/wedding", response_model=ResponseEnvelope[WeddingOut], summary="Thông tin cưới")
async def get_wedding(actor: StudioEditor, use_case: GetWeddingDep) -> dict[str, Any]:
    """404 `wedding_not_setup` khi xưởng chưa khởi tạo — web hiện dữ liệu mẫu."""
    return ok(WeddingOut.of_wedding(await use_case.execute(actor)))


@router.post(
    "/wedding/setup",
    response_model=ResponseEnvelope[WeddingOut],
    status_code=status.HTTP_201_CREATED,
    summary="Lưu dữ liệu mẫu hoặc bắt đầu trống",
)
async def setup_wedding(
    payload: SetupIn, actor: StudioEditor, use_case: SetupWeddingDep
) -> dict[str, Any]:
    wedding = await use_case.execute(actor, SetupMode(payload.mode))
    return ok(WeddingOut.of_wedding(wedding))


@router.put("/wedding", response_model=ResponseEnvelope[WeddingOut], summary="Lưu thông tin cưới")
async def save_wedding(
    payload: WeddingContentIO, actor: StudioEditor, use_case: SaveWeddingDep
) -> dict[str, Any]:
    """Thay trọn nội dung (lưu tự động từ form). Không chạm slug/xuất bản/tiến độ."""
    return ok(WeddingOut.of_wedding(await use_case.execute(actor, payload.to_domain())))


@router.put(
    "/wedding/checklist",
    response_model=ResponseEnvelope[WeddingOut],
    summary="Tiến độ lộ trình chuẩn bị",
)
async def save_checklist(
    payload: ChecklistIn, actor: StudioEditor, use_case: SaveChecklistDep
) -> dict[str, Any]:
    return ok(WeddingOut.of_wedding(await use_case.execute(actor, payload.done)))


@router.put(
    "/wedding/publication",
    response_model=ResponseEnvelope[WeddingOut],
    summary="Đường dẫn công khai và bật/tắt web thiệp",
)
async def set_publication(
    payload: PublicationIn, actor: StudioEditor, use_case: SetPublicationDep
) -> dict[str, Any]:
    wedding = await use_case.execute(actor, slug=payload.slug, published=payload.published)
    return ok(WeddingOut.of_wedding(wedding))


@router.get(
    "/wedding/plan-check",
    response_model=ResponseEnvelope[PlanCheckOut],
    summary="Thiệp đang dùng gì vượt gói",
)
async def check_plan(actor: StudioEditor, use_case: CheckWeddingPlanDep) -> dict[str, Any]:
    """Rỗng `violations` = xuất bản được với gói hiện tại."""
    return ok(PlanCheckOut.model_validate(await use_case.execute(actor)))


#: Mỗi lượt gợi ý là một lượt gọi mô hình trả phí — đủ rộng cho người soạn thật.
_SUGGEST_LIMIT_PER_HOUR = 40


@router.get(
    "/wedding/wording/ai",
    response_model=ResponseEnvelope[AiStatusOut],
    summary="Gợi ý câu chữ bằng AI có bật không",
)
async def wording_ai_status(actor: StudioEditor, use_case: SuggestWordingDep) -> dict[str, Any]:
    del actor
    return ok(AiStatusOut(enabled=use_case.enabled))


@router.post(
    "/wedding/wording/suggest",
    response_model=ResponseEnvelope[WordingSuggestOut],
    summary="Gợi ý câu chữ cho một ô của thiệp",
)
async def suggest_wording(
    payload: WordingSuggestIn, actor: StudioEditor, use_case: SuggestWordingDep
) -> dict[str, Any]:
    """Ba phương án theo giọng văn; người soạn chọn rồi sửa tiếp. Không tự lưu."""
    await rate_limit.guard(
        "wording_suggest",
        str(actor.tenant_id),
        limit=_SUGGEST_LIMIT_PER_HOUR,
        window_seconds=3600,
        message="Bạn đã dùng nhiều lượt gợi ý. Thử lại sau ít phút.",
        code="ai_rate_limited",
    )
    suggestions = await use_case.execute(actor, field=payload.field, tone=payload.tone)
    return ok(WordingSuggestOut(suggestions=suggestions))


@router.get(
    "/admin/studios",
    response_model=ResponseEnvelope[list[StudioOverviewOut]],
    tags=["Quản trị hệ thống"],
    summary="Giám sát xưởng thiệp",
)
async def list_studios(
    actor: Annotated[ActorContext, require_permissions(Permission.STUDIO_OVERSEE)],
    use_case: ListStudiosDep,
) -> dict[str, Any]:
    """Mọi xưởng đã khởi tạo đám cưới, kèm số khách — không lộ nội dung khách mời."""
    del actor
    return ok_list([StudioOverviewOut.of(item) for item in await use_case.execute()])


__all__ = ["router"]
