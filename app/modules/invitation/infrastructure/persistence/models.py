"""`invitation` CHỈ ĐỌC — không sở hữu collection nào (cùng vai `reporting` ở ad-tracker)."""

from __future__ import annotations

from app.core.base_model import Document

DOCUMENTS: list[type[Document]] = []

__all__ = ["DOCUMENTS"]
