"""Beanie Document của `template` — collection `templates`."""

from __future__ import annotations

from typing import ClassVar
from uuid import UUID

from pydantic import Field

from app.core.base_model import ASCENDING, BaseDocument, Document, IndexModel


class TemplateDocument(BaseDocument):
    """Một mẫu thiệp của bộ sưu tập.

    Ngoại lệ có chủ ý với §0.4 (không `tenant_id`): bộ mẫu là danh mục TOÀN HỆ
    THỐNG, mọi xưởng dùng chung — giống `roles`.
    """

    key: str
    name: str
    family: str
    tone: str
    layout: str
    is_new: bool = False
    is_active: bool = True
    sort_order: int = 0
    tier: str = "standard"

    class Settings(BaseDocument.Settings):
        name = "templates"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel([("key", ASCENDING)], name="uq_templates_key", unique=True),
            IndexModel([("sort_order", ASCENDING)], name="ix_templates_sort"),
        ]


class CatalogDefaultsDocument(BaseDocument):
    """Mặc định hệ thống — đúng MỘT bản ghi (`key = "system"`), toàn hệ thống như `templates`."""

    key: str = "system"
    group_templates: dict[str, str] = Field(default_factory=dict)
    default_template: str = ""
    wording: dict[str, dict[str, str]] = Field(default_factory=dict)
    messages: dict[str, str] = Field(default_factory=dict)

    class Settings(BaseDocument.Settings):
        name = "catalog_defaults"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel([("key", ASCENDING)], name="uq_catalog_defaults_key", unique=True),
        ]


class IntroDocument(BaseDocument):
    """Một video mở thiệp của thư viện chung — toàn hệ thống như `templates`.

    Byte video nằm ở kho object S3, khoá `key`; Mongo chỉ giữ siêu dữ liệu.
    """

    name: str
    key: str
    content_type: str
    size: int
    order: int = 0
    is_active: bool = True
    created_by: UUID | None = None

    class Settings(BaseDocument.Settings):
        name = "intros"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel([("order", ASCENDING), ("created_at", ASCENDING)], name="ix_intros_order"),
        ]


DOCUMENTS: list[type[Document]] = [TemplateDocument, CatalogDefaultsDocument, IntroDocument]

__all__ = ["DOCUMENTS", "CatalogDefaultsDocument", "IntroDocument", "TemplateDocument"]
