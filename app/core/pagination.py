"""Phân trang ở tầng HTTP — ARCHITECTURE §1.6.

Query: `?page=1&per_page=20`. Meta trả về: `{page, per_page, total, total_pages}`.
Kiểu thuần `Page`/`PageParams` nằm ở `app.core.pages` để domain dùng được.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field

from app.core.pages import DEFAULT_PER_PAGE, MAX_PER_PAGE, Page, PageParams


def page_params(
    page: Annotated[int, Query(ge=1, description="Trang hiện tại, bắt đầu từ 1.")] = 1,
    per_page: Annotated[
        int, Query(ge=1, le=MAX_PER_PAGE, description="Số bản ghi mỗi trang.")
    ] = DEFAULT_PER_PAGE,
) -> PageParams:
    """Dependency FastAPI: `params: Annotated[PageParams, Depends(page_params)]`."""
    return PageParams(page=page, per_page=per_page)


class PageMeta(BaseModel):
    """Khối `meta` của một response phân trang (cho OpenAPI)."""

    page: int = Field(ge=1)
    per_page: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


__all__ = ["DEFAULT_PER_PAGE", "MAX_PER_PAGE", "Page", "PageMeta", "PageParams", "page_params"]
