"""Schema HTTP của `printing`."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.printing.domain.entities import PrintRequest, PrintSpec
from app.modules.printing.domain.enums import (
    PAPERS,
    PRINT_STATUS_LABELS,
    SIZES,
    PrintStatus,
)


class LabelOut(BaseModel):
    slug: str
    label: str


class PrintOptionsOut(BaseModel):
    papers: list[LabelOut]
    sizes: list[LabelOut]
    statuses: list[LabelOut]

    @classmethod
    def current(cls) -> PrintOptionsOut:
        return cls(
            papers=[LabelOut(slug=key, label=value) for key, value in PAPERS.items()],
            sizes=[LabelOut(slug=key, label=value) for key, value in SIZES.items()],
            statuses=[
                LabelOut(slug=key.value, label=value) for key, value in PRINT_STATUS_LABELS.items()
            ],
        )


class PrintRequestIn(BaseModel):
    quantity: Annotated[int, Field(ge=1, le=100_000)]
    paper: Annotated[str, Field(max_length=40)]
    size: Annotated[str, Field(max_length=40)]
    foil: bool = False
    envelope: bool = False
    contact_name: Annotated[str, Field(max_length=120)]
    contact_phone: Annotated[str, Field(max_length=24)]
    address: Annotated[str, Field(max_length=300)]
    note: Annotated[str, Field(max_length=1000)] = ""

    def to_domain(self) -> PrintSpec:
        return PrintSpec(**self.model_dump())


class PrintUpdateIn(BaseModel):
    status: PrintStatus
    admin_note: Annotated[str | None, Field(max_length=1000)] = None


class PrintRequestOut(BaseModel):
    id: UUID
    quantity: int
    paper: LabelOut
    size: LabelOut
    foil: bool
    envelope: bool
    contact_name: str
    contact_phone: str
    address: str
    note: str
    status: LabelOut
    admin_note: str
    created_at: datetime
    updated_at: datetime | None = None
    #: Chỉ màn vận hành: xưởng gửi yêu cầu.
    studio_id: UUID | None = None

    @classmethod
    def of(cls, item: PrintRequest, *, admin: bool = False) -> PrintRequestOut:
        spec = item.spec
        return cls(
            id=item.id,
            quantity=spec.quantity,
            paper=LabelOut(slug=spec.paper, label=PAPERS.get(spec.paper, spec.paper)),
            size=LabelOut(slug=spec.size, label=SIZES.get(spec.size, spec.size)),
            foil=spec.foil,
            envelope=spec.envelope,
            contact_name=spec.contact_name,
            contact_phone=spec.contact_phone,
            address=spec.address,
            note=spec.note,
            status=LabelOut(slug=item.status.value, label=PRINT_STATUS_LABELS[item.status]),
            admin_note=item.admin_note,
            created_at=item.created_at,
            updated_at=item.updated_at,
            studio_id=item.tenant_id if admin else None,
        )


__all__ = ["LabelOut", "PrintOptionsOut", "PrintRequestIn", "PrintRequestOut", "PrintUpdateIn"]
