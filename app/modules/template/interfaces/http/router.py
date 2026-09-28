"""Router HTTP của `template`.

| Method | Path                       | Quyền             |
|--------|----------------------------|-------------------|
| GET    | /api/v1/templates          | `template.view`   |
| PATCH  | /api/v1/templates/{id}     | `template.manage` |
| GET    | /api/v1/templates/defaults | công khai         |
| PUT    | /api/v1/templates/defaults | `template.manage` |
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path

from app.core.context import ActorContext
from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.core.responses import ResponseEnvelope, ok, ok_list
from app.modules.template.application.use_cases import TemplatePatch
from app.modules.template.infrastructure.providers import (
    GetCatalogDefaultsDep,
    ListTemplatesDep,
    SaveCatalogDefaultsDep,
    UpdateTemplateDep,
)
from app.modules.template.interfaces.http.schemas import (
    CatalogDefaultsIO,
    TemplateOut,
    TemplatePatchIn,
)

router = APIRouter(prefix="/templates", tags=["Mẫu thiệp"])


@router.get("", response_model=ResponseEnvelope[list[TemplateOut]], summary="Bộ mẫu thiệp")
async def list_templates(
    actor: Annotated[ActorContext, require_permissions(Permission.TEMPLATE_VIEW)],
    use_case: ListTemplatesDep,
) -> dict[str, Any]:
    """Mẫu đang mở; người quản lý bộ mẫu thấy cả mẫu đã tắt."""
    return ok_list([TemplateOut.of(item) for item in await use_case.execute(actor)])


@router.get(
    "/defaults",
    response_model=ResponseEnvelope[CatalogDefaultsIO],
    summary="Mặc định hệ thống (mẫu theo nhóm khách, câu chữ theo giọng văn)",
)
async def get_defaults(use_case: GetCatalogDefaultsDep) -> dict[str, Any]:
    """Công khai: web thiệp và xưởng đều cần câu chữ mặc định để hiện thiệp."""
    return ok(CatalogDefaultsIO.of(await use_case.execute()))


@router.put(
    "/defaults",
    response_model=ResponseEnvelope[CatalogDefaultsIO],
    summary="Lưu mặc định hệ thống",
)
async def save_defaults(
    payload: CatalogDefaultsIO,
    actor: Annotated[ActorContext, require_permissions(Permission.TEMPLATE_MANAGE)],
    use_case: SaveCatalogDefaultsDep,
) -> dict[str, Any]:
    return ok(CatalogDefaultsIO.of(await use_case.execute(actor, payload.to_domain())))


@router.patch("/{key}", response_model=ResponseEnvelope[TemplateOut], summary="Chỉnh một mẫu")
async def update_template(
    key: Annotated[str, Path(min_length=2, max_length=40, pattern=r"^[a-z0-9]+$")],
    payload: TemplatePatchIn,
    actor: Annotated[ActorContext, require_permissions(Permission.TEMPLATE_MANAGE)],
    use_case: UpdateTemplateDep,
) -> dict[str, Any]:
    """Bật/tắt, gắn nhãn Mới, đổi thứ tự hiển thị."""
    item = await use_case.execute(
        actor,
        key,
        TemplatePatch(
            is_active=payload.is_active,
            is_new=payload.is_new,
            sort_order=payload.sort_order,
            tier=payload.tier,
        ),
    )
    return ok(TemplateOut.of(item))


__all__ = ["router"]
