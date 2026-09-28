"""Envelope thành công — ARCHITECTURE §1.6.

`{"data": <payload>, "meta": {...}?}` — khớp `ApiResponse<T>` mà
`wedding-web/src/core/api/api-client.ts` mong đợi. Router LUÔN trả qua `ok(...)`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.pages import Page
from app.core.pagination import PageMeta

Meta = dict[str, Any] | BaseModel | None


def _normalize_meta(meta: Meta) -> dict[str, Any] | None:
    if meta is None:
        return None
    if isinstance(meta, BaseModel):
        return meta.model_dump()
    return meta or None


def ok(data: Any, meta: Meta = None) -> dict[str, Any]:
    """Bọc payload vào envelope thành công."""
    envelope: dict[str, Any] = {"data": data}
    normalized = _normalize_meta(meta)
    if normalized is not None:
        envelope["meta"] = normalized
    return envelope


def ok_page(page: Page[Any], extra_meta: Meta = None) -> dict[str, Any]:
    """Bọc một `Page` thành envelope kèm meta phân trang chuẩn."""
    meta: dict[str, Any] = page.meta_dict()
    extra = _normalize_meta(extra_meta)
    if extra:
        meta.update(extra)
    return {"data": list(page.items), "meta": meta}


def ok_list(items: Sequence[Any], meta: Meta = None) -> dict[str, Any]:
    """Bọc danh sách không phân trang."""
    return ok(list(items), meta)


class ResponseEnvelope[T](BaseModel):
    """Envelope generic để OpenAPI sinh đúng schema."""

    model_config = ConfigDict(from_attributes=True)

    data: T
    meta: dict[str, Any] | None = None


class PaginatedEnvelope[T](BaseModel):
    """Envelope cho danh sách phân trang, `meta` có kiểu chặt."""

    model_config = ConfigDict(from_attributes=True)

    data: list[T]
    meta: PageMeta


class MessageOut(BaseModel):
    """Payload cho thao tác chỉ cần báo kết quả (xoá, đăng xuất...)."""

    message: str


def ok_message(message: str) -> dict[str, Any]:
    """Envelope cho thao tác không có dữ liệu trả về."""
    return ok({"message": message})


__all__ = [
    "MessageOut",
    "Meta",
    "PaginatedEnvelope",
    "ResponseEnvelope",
    "ok",
    "ok_list",
    "ok_message",
    "ok_page",
]
