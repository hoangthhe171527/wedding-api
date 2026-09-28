"""Gom mọi Beanie Document để `init_beanie` biết đủ collection.

Beanie chỉ ánh xạ những document được truyền vào lúc khởi tạo. Document nào không
có mặt ở đây sẽ **im lặng không dùng được** (và index không bao giờ được tạo) — nên
mọi module mới bắt buộc thêm tên vào `MODULE_NAMES`.

Nạp mềm có chủ ý: module chưa dựng xong không làm chết cả ứng dụng. Đặt
`STRICT_MODEL_IMPORT=1` để bắt lỗi ngay (CI và production).
"""

from __future__ import annotations

import importlib
import os
from typing import Any, Final

from app.core.logging import get_logger

log = get_logger(__name__)

#: Thứ tự chỉ để dễ đọc: định danh -> phân quyền -> danh mục -> nghiệp vụ -> đọc.
MODULE_NAMES: Final[tuple[str, ...]] = (
    "identity",
    "access",
    "template",
    "wedding",
    "guest",
    "media",
    "billing",
    "printing",
    "invitation",
)

_MODEL_PATH_TEMPLATE: Final[str] = "app.modules.{name}.infrastructure.persistence.models"

STRICT: Final[bool] = os.environ.get("STRICT_MODEL_IMPORT", "").lower() in {"1", "true", "yes"}


def _documents_of(module: Any) -> list[type]:
    """Danh sách document mà một module khai báo qua biến `DOCUMENTS` bắt buộc."""
    documents = getattr(module, "DOCUMENTS", None)
    if documents is None:
        if STRICT:
            message = f"{module.__name__} không export `DOCUMENTS`."
            raise RuntimeError(message)
        log.warning("module_without_documents", module=module.__name__)
        return []
    return list(documents)


def all_documents() -> list[type]:
    """Toàn bộ Beanie Document của mọi module đã dựng xong."""
    # Document của tầng core (nhật ký quản trị) — không thuộc module nào.
    from app.core.audit import CORE_DOCUMENTS

    collected: list[type] = list(CORE_DOCUMENTS)
    for name in MODULE_NAMES:
        path = _MODEL_PATH_TEMPLATE.format(name=name)
        try:
            module = importlib.import_module(path)
        except ModuleNotFoundError as exc:
            if STRICT:
                raise
            log.warning("model_module_missing", module=path, reason=str(exc))
            continue
        collected.extend(_documents_of(module))
    return collected


def collection_names() -> tuple[str, ...]:
    """Tên mọi collection đã đăng ký — tiện để kiểm tra không sót."""
    names: list[str] = []
    for document in all_documents():
        settings = getattr(document, "Settings", None)
        names.append(str(getattr(settings, "name", None) or document.__name__.lower()))
    return tuple(sorted(names))


__all__ = ["MODULE_NAMES", "all_documents", "collection_names"]
