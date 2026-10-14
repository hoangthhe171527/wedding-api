"""Module `template` — bộ mẫu thiệp và thư viện video mở thiệp (danh mục toàn hệ thống).

Sở hữu `templates`, `catalog_defaults`, `intros` (byte video ở kho object S3). Web
giữ phần hình (thư viện render); module này giữ siêu dữ liệu và trạng thái
mở/đóng do đội vận hành quản lý.
"""

from fastapi import APIRouter

from app.modules.template.domain.catalog import DEFAULT_TEMPLATE_KEY
from app.modules.template.infrastructure.external.catalog_reader import (
    build_catalog_defaults_reader,
    build_template_catalog_reader,
)
from app.modules.template.infrastructure.external.intro_reader import build_intro_url_reader
from app.modules.template.infrastructure.providers import build_ensure_catalog
from app.modules.template.interfaces.http.intro_router import router as intro_router
from app.modules.template.interfaces.http.router import router as template_router

#: Module chỉ export MỘT `router`; hai nhóm đường dẫn gộp ở đây.
router = APIRouter()
router.include_router(template_router)
router.include_router(intro_router)

__all__ = [
    "DEFAULT_TEMPLATE_KEY",
    "build_catalog_defaults_reader",
    "build_ensure_catalog",
    "build_intro_url_reader",
    "build_template_catalog_reader",
    "router",
]
