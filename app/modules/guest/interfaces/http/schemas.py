"""Schema HTTP của `guest`."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.guest.application.use_cases import GuestPatch, ImportResult, LinkInput
from app.modules.guest.domain.entities import Guest, GuestDraft, InviteLink, Wish
from app.modules.guest.domain.enums import (
    DEFAULT_GROUP,
    MAX_PARTY_SIZE,
    RSVP_LABELS,
    RsvpStatus,
    Side,
)

Short = Annotated[str, Field(max_length=120)]
EventId = Annotated[str, Field(min_length=1, max_length=40)]
TemplateKey = Annotated[str, Field(max_length=40)]


class GuestIn(BaseModel):
    """Thân `POST /guests` — đủ mọi trường của form khách."""

    name: Annotated[str, Field(min_length=1, max_length=160)]
    title: Short = ""
    plus: Short = ""
    group: Short = DEFAULT_GROUP
    side: Side = Side.TRAI
    events: Annotated[list[EventId], Field(max_length=20)] = Field(default_factory=list)
    count: Annotated[int, Field(ge=1, le=MAX_PARTY_SIZE)] = 1
    template: TemplateKey = ""
    status: RsvpStatus = RsvpStatus.NONE
    sent: bool = False
    note: Annotated[str, Field(max_length=300)] = ""

    def to_domain(self) -> GuestDraft:
        return GuestDraft(
            name=self.name,
            title=self.title,
            plus=self.plus,
            group=self.group,
            side=self.side,
            events=tuple(self.events),
            count=self.count,
            template=self.template,
            status=self.status,
            sent=self.sent,
            note=self.note,
        )


class GuestPatchIn(BaseModel):
    """Thân `PATCH /guests/{id}` — chỉ gửi trường cần đổi."""

    name: Annotated[str, Field(min_length=1, max_length=160)] | None = None
    title: Short | None = None
    plus: Short | None = None
    group: Short | None = None
    side: Side | None = None
    events: Annotated[list[EventId], Field(max_length=20)] | None = None
    count: Annotated[int, Field(ge=1, le=MAX_PARTY_SIZE)] | None = None
    template: TemplateKey | None = None
    status: RsvpStatus | None = None
    sent: bool | None = None
    note: Annotated[str, Field(max_length=300)] | None = None

    def to_domain(self) -> GuestPatch:
        return GuestPatch(
            name=self.name,
            title=self.title,
            plus=self.plus,
            group=self.group,
            side=self.side,
            events=tuple(self.events) if self.events is not None else None,
            count=self.count,
            template=self.template,
            status=self.status,
            sent=self.sent,
            note=self.note,
        )


class ImportIn(BaseModel):
    """Văn bản dán từ ô "Nhập nhanh"."""

    text: Annotated[str, Field(min_length=1, max_length=100_000)]


class StatusOut(BaseModel):
    slug: str
    label: str


class ReplyOut(BaseModel):
    """Phản hồi khách tự gửi từ web thiệp."""

    count: int
    message: str
    replied_at: datetime


class OpensOut(BaseModel):
    """Khách đã mở link riêng."""

    count: int
    first_at: datetime
    last_at: datetime


class GuestOut(BaseModel):
    """Một thiệp mời. `code` là mã cuối link riêng."""

    id: UUID
    code: str
    name: str
    title: str
    plus: str
    group: str
    side: Side
    events: list[str]
    count: int
    template: str
    status: StatusOut
    sent: bool
    note: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    reply: ReplyOut | None = None
    opens: OpensOut | None = None

    @classmethod
    def of(cls, guest: Guest) -> GuestOut:
        draft = guest.draft
        return cls(
            id=guest.id,
            code=guest.code,
            name=draft.name,
            title=draft.title,
            plus=draft.plus,
            group=draft.group,
            side=draft.side,
            events=list(draft.events),
            count=draft.count,
            template=draft.template,
            status=StatusOut(slug=draft.status.value, label=RSVP_LABELS[draft.status]),
            sent=draft.sent,
            note=draft.note,
            created_at=guest.created_at,
            updated_at=guest.updated_at,
            reply=(
                ReplyOut(
                    count=guest.reply.count,
                    message=guest.reply.message,
                    replied_at=guest.reply.replied_at,
                )
                if guest.reply
                else None
            ),
            opens=(
                OpensOut(
                    count=guest.opens.count,
                    first_at=guest.opens.first_at,
                    last_at=guest.opens.last_at,
                )
                if guest.opens
                else None
            ),
        )


class WishOut(BaseModel):
    """Một phản hồi / lời chúc. `guest_code` rỗng = gửi từ link chung."""

    id: UUID
    name: str
    message: str
    status: StatusOut
    count: int
    guest_code: str
    #: Đuôi link đối tượng gửi phản hồi; rỗng = link chung hoặc link riêng.
    link: str = ""
    created_at: datetime

    @classmethod
    def of(cls, wish: Wish) -> WishOut:
        return cls(
            id=wish.id,
            name=wish.name,
            message=wish.message,
            status=StatusOut(slug=wish.status.value, label=RSVP_LABELS[wish.status]),
            count=wish.count,
            guest_code=wish.guest_code,
            link=wish.link,
            created_at=wish.created_at,
        )


class ImportOut(BaseModel):
    created: list[GuestOut]
    skipped: int

    @classmethod
    def of(cls, result: ImportResult) -> ImportOut:
        return cls(created=[GuestOut.of(item) for item in result.created], skipped=result.skipped)


class LinkIn(BaseModel):
    """Thân `POST /guests/links` và `PUT /guests/links/{id}`. `slug` rỗng = tự sinh từ tên."""

    name: Annotated[str, Field(min_length=1, max_length=80)]
    slug: Annotated[str, Field(max_length=40)] = ""
    template: TemplateKey = ""
    #: Người được mời trên thiệp ("Quý đồng nghiệp"); rỗng = "Quý khách".
    greeting: Annotated[str, Field(max_length=120)] = ""
    #: Id lễ tiệc nhóm này được mời; rỗng = mọi lễ tiệc.
    events: Annotated[list[EventId], Field(max_length=20)] = Field(default_factory=list)

    def to_domain(self) -> LinkInput:
        return LinkInput(
            name=self.name,
            slug=self.slug,
            template=self.template,
            greeting=self.greeting,
            events=tuple(self.events),
        )


class LinkOut(BaseModel):
    """Một link theo đối tượng. Link đầy đủ = `site_url` + `/` + `slug`."""

    id: UUID
    slug: str
    name: str
    template: str
    greeting: str = ""
    events: list[str] = []
    opens: int
    last_opened_at: datetime | None = None
    created_at: datetime | None = None

    @classmethod
    def of(cls, link: InviteLink) -> LinkOut:
        return cls(
            id=link.id,
            slug=link.slug,
            name=link.name,
            template=link.template,
            greeting=link.greeting,
            events=list(link.events),
            opens=link.opens,
            last_opened_at=link.last_opened_at,
            created_at=link.created_at,
        )


__all__ = [
    "GuestIn",
    "GuestOut",
    "GuestPatchIn",
    "ImportIn",
    "ImportOut",
    "LinkIn",
    "LinkOut",
    "WishOut",
]
