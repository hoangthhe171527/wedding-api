"""Beanie Document của `printing` — collection `print_requests`."""

from __future__ import annotations

from typing import ClassVar

from app.core.base_model import (
    ASCENDING,
    DESCENDING,
    Document,
    IndexModel,
    TenantScopedDocument,
)


class PrintRequestDocument(TenantScopedDocument):
    """Một yêu cầu in thiệp giấy của một xưởng."""

    quantity: int
    paper: str
    size: str
    foil: bool = False
    envelope: bool = False
    contact_name: str
    contact_phone: str
    address: str
    note: str = ""
    status: str = "new"
    admin_note: str = ""

    class Settings(TenantScopedDocument.Settings):
        name = "print_requests"
        indexes: ClassVar[list[IndexModel]] = [
            *TenantScopedDocument.Settings.indexes,
            IndexModel(
                [("status", ASCENDING), ("created_at", DESCENDING)],
                name="ix_print_requests_status",
            ),
            IndexModel(
                [("deleted_at", ASCENDING), ("created_at", DESCENDING)],
                name="ix_print_requests_recent",
            ),
        ]


DOCUMENTS: list[type[Document]] = [PrintRequestDocument]

__all__ = ["DOCUMENTS", "PrintRequestDocument"]
