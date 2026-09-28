"""Thực thể thuần của `printing`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.printing.domain.enums import PrintStatus


@dataclass(frozen=True, slots=True)
class PrintSpec:
    """Khách muốn in gì. Không có giá: đội vận hành báo giá khi liên hệ."""

    quantity: int
    paper: str
    size: str
    foil: bool
    envelope: bool
    contact_name: str
    contact_phone: str
    address: str
    note: str = ""


@dataclass(frozen=True, slots=True)
class PrintRequest:
    id: UUID
    tenant_id: UUID
    spec: PrintSpec
    status: PrintStatus
    admin_note: str
    created_at: datetime
    updated_at: datetime | None = None
