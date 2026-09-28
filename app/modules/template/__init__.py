"""Module `template` — bộ mẫu thiệp (danh mục toàn hệ thống).

Sở hữu `templates`. Web giữ phần hình (thư viện render); module này giữ siêu dữ
liệu và trạng thái mở/đóng do đội vận hành quản lý.
"""

from app.modules.template.domain.catalog import DEFAULT_TEMPLATE_KEY
from app.modules.template.infrastructure.external.catalog_reader import (
    build_catalog_defaults_reader,
    build_template_catalog_reader,
)
from app.modules.template.infrastructure.providers import build_ensure_catalog
from app.modules.template.interfaces.http.router import router

__all__ = [
    "DEFAULT_TEMPLATE_KEY",
    "build_catalog_defaults_reader",
    "build_ensure_catalog",
    "build_template_catalog_reader",
    "router",
]
