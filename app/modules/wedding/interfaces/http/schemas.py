"""Schema HTTP của `wedding`.

Tên trường snake_case theo hợp đồng chung (§1.6). Web ánh xạ sang hình `W`
camelCase của thư viện render ở tầng infrastructure của nó.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.wedding.application.support import site_url
from app.modules.wedding.application.use_cases import StudioOverview
from app.modules.wedding.domain.design import MAX_LAYERS, CardDesign, DesignLayer
from app.modules.wedding.domain.entities import (
    BankAccount,
    DressCode,
    Event,
    Gift,
    Parents,
    Person,
    Rsvp,
    ScheduleItem,
    Theme,
    Wedding,
    WeddingContent,
)
from app.modules.wedding.domain.enums import EventKind, OpenStyle, Side

Short = Annotated[str, Field(max_length=120)]
Line = Annotated[str, Field(max_length=300)]
Url = Annotated[str, Field(max_length=1000)]
Text = Annotated[str, Field(max_length=2000)]


class PersonIO(BaseModel):
    full: Short = ""
    short: Short = ""
    rank: Short = ""
    phone: Annotated[str, Field(max_length=30)] = ""

    def to_domain(self) -> Person:
        return Person(full=self.full, short=self.short, rank=self.rank, phone=self.phone)

    @classmethod
    def of(cls, item: Person) -> PersonIO:
        return cls(full=item.full, short=item.short, rank=item.rank, phone=item.phone)


class ParentsIO(BaseModel):
    father: Short = ""
    mother: Short = ""
    address: Line = ""

    def to_domain(self) -> Parents:
        return Parents(father=self.father, mother=self.mother, address=self.address)

    @classmethod
    def of(cls, item: Parents) -> ParentsIO:
        return cls(father=item.father, mother=item.mother, address=item.address)


class EventIO(BaseModel):
    id: Annotated[str, Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")]
    name: Short = ""
    kind: EventKind = EventKind.TIEC
    side: Side = Side.TRAI
    date: Annotated[str, Field(max_length=10)] = ""
    time: Annotated[str, Field(max_length=5)] = ""
    venue: Line = ""
    address: Line = ""
    map_url: Url = ""
    arrival: Annotated[str, Field(max_length=5)] = ""

    def to_domain(self) -> Event:
        return Event(
            id=self.id,
            name=self.name,
            kind=self.kind,
            side=self.side,
            date=self.date,
            time=self.time,
            venue=self.venue,
            address=self.address,
            map_url=self.map_url,
            arrival=self.arrival,
        )

    @classmethod
    def of(cls, item: Event) -> EventIO:
        return cls(
            id=item.id,
            name=item.name,
            kind=item.kind,
            side=item.side,
            date=item.date,
            time=item.time,
            venue=item.venue,
            address=item.address,
            map_url=item.map_url,
            arrival=item.arrival,
        )


class ScheduleItemIO(BaseModel):
    time: Annotated[str, Field(max_length=5)] = ""
    label: Annotated[str, Field(max_length=80)] = ""


class DressCodeIO(BaseModel):
    note: Annotated[str, Field(max_length=120)] = ""
    colors: Annotated[list[Annotated[str, Field(max_length=7)]], Field(max_length=12)] = Field(
        default_factory=list
    )


class RsvpIO(BaseModel):
    url: Url = ""
    deadline: Annotated[str, Field(max_length=10)] = ""


class BankAccountIO(BaseModel):
    bank: Short = ""
    number: Annotated[str, Field(max_length=40)] = ""
    holder: Short = ""

    def to_domain(self) -> BankAccount:
        return BankAccount(bank=self.bank, number=self.number, holder=self.holder)

    @classmethod
    def of(cls, item: BankAccount) -> BankAccountIO:
        return cls(bank=item.bank, number=item.number, holder=item.holder)


class GiftIO(BaseModel):
    show: bool = False
    groom: BankAccountIO = Field(default_factory=BankAccountIO)
    bride: BankAccountIO = Field(default_factory=BankAccountIO)


Color = Annotated[str, Field(max_length=7)]
FontName = Annotated[str, Field(max_length=40)]


class WordingSuggestIn(BaseModel):
    field: Annotated[str, Field(max_length=20)]
    tone: Annotated[str, Field(max_length=20)]


class WordingSuggestOut(BaseModel):
    suggestions: list[str]


class AiStatusOut(BaseModel):
    enabled: bool


class ThemeIO(BaseModel):
    """Tuỳ chỉnh giao diện; ô rỗng (hoặc `density` = 0) = theo mẫu."""

    accent: Color = ""
    accent2: Color = ""
    ink: Color = ""
    font_display: FontName = ""
    font_script: FontName = ""
    font_body: FontName = ""
    ambient: Annotated[str, Field(max_length=20)] = ""
    density: Annotated[float, Field(ge=0, le=2)] = 0.0
    intro: Color = ""
    intro2: Color = ""
    sections: Annotated[list[Annotated[str, Field(max_length=20)]], Field(max_length=12)] = []
    hidden: Annotated[list[Annotated[str, Field(max_length=20)]], Field(max_length=12)] = []

    def to_domain(self) -> Theme:
        return Theme(
            **{
                **self.model_dump(),
                "sections": tuple(self.sections),
                "hidden": tuple(self.hidden),
            }
        )

    @classmethod
    def of(cls, item: Theme) -> ThemeIO:
        return cls(
            accent=item.accent,
            accent2=item.accent2,
            ink=item.ink,
            font_display=item.font_display,
            font_script=item.font_script,
            font_body=item.font_body,
            ambient=item.ambient,
            density=item.density,
            intro=item.intro,
            intro2=item.intro2,
            sections=list(item.sections),
            hidden=list(item.hidden),
        )


class DesignLayerIO(BaseModel):
    """Một lớp của thiệp tự thiết kế. Khoảng giá trị kiểm ở domain (`validate_design`)."""

    id: Annotated[str, Field(min_length=1, max_length=24)]
    kind: Annotated[str, Field(max_length=10)]
    x: float = 10.0
    y: float = 10.0
    w: float = 80.0
    h: float = 10.0
    rotate: float = 0.0
    opacity: float = 1.0
    hidden: bool = False
    locked: bool = False
    text: Annotated[str, Field(max_length=500)] = ""
    field: Annotated[str, Field(max_length=24)] = ""
    font: Annotated[str, Field(max_length=40)] = ""
    size: float = 4.0
    color: Annotated[str, Field(max_length=10)] = ""
    align: Annotated[str, Field(max_length=6)] = "center"
    weight: int = 400
    italic: bool = False
    upper: bool = False
    spacing: float = 0.0
    line: float = 1.2
    foil: bool = False
    photo: int = 0
    fit: Annotated[str, Field(max_length=8)] = "cover"
    radius: float = 0.0
    decor: Annotated[str, Field(max_length=20)] = ""
    shape: Annotated[str, Field(max_length=8)] = "rect"
    fill: Annotated[str, Field(max_length=10)] = ""
    stroke: Annotated[str, Field(max_length=10)] = ""
    stroke_w: float = 0.0


class CardDesignIO(BaseModel):
    enabled: bool = False
    base: Annotated[str, Field(max_length=40)] = ""
    layers: Annotated[list[DesignLayerIO], Field(max_length=MAX_LAYERS)] = Field(
        default_factory=list
    )

    def to_domain(self) -> CardDesign:
        return CardDesign(
            enabled=self.enabled,
            base=self.base,
            layers=tuple(DesignLayer(**item.model_dump()) for item in self.layers),
        )

    @classmethod
    def of(cls, item: CardDesign) -> CardDesignIO:
        return cls(
            enabled=item.enabled,
            base=item.base,
            layers=[
                DesignLayerIO.model_validate(layer, from_attributes=True) for layer in item.layers
            ],
        )


class WeddingContentIO(BaseModel):
    """Nội dung đám cưới — thân của `PUT /wedding` và một phần của `WeddingOut`."""

    groom: PersonIO = Field(default_factory=PersonIO)
    bride: PersonIO = Field(default_factory=PersonIO)
    groom_parents: ParentsIO = Field(default_factory=ParentsIO)
    bride_parents: ParentsIO = Field(default_factory=ParentsIO)
    events: Annotated[list[EventIO], Field(max_length=50)] = Field(default_factory=list)
    story: Text = ""
    quote: Text = ""
    rsvp: RsvpIO = Field(default_factory=RsvpIO)
    gift: GiftIO = Field(default_factory=GiftIO)
    music_url: Url = ""
    default_template: Annotated[str, Field(max_length=40)] = ""
    group_templates: dict[str, Annotated[str, Field(max_length=40)]] = Field(default_factory=dict)
    wording: dict[str, dict[str, Line]] = Field(default_factory=dict)
    messages: dict[str, Text] = Field(default_factory=dict)
    open_style: OpenStyle = OpenStyle.BY_TEMPLATE
    theme: ThemeIO = Field(default_factory=ThemeIO)
    card_design: CardDesignIO = Field(default_factory=CardDesignIO)
    schedule: Annotated[list[ScheduleItemIO], Field(max_length=30)] = Field(default_factory=list)
    dress_code: DressCodeIO = Field(default_factory=DressCodeIO)

    def to_domain(self) -> WeddingContent:
        return WeddingContent(
            groom=self.groom.to_domain(),
            bride=self.bride.to_domain(),
            groom_parents=self.groom_parents.to_domain(),
            bride_parents=self.bride_parents.to_domain(),
            events=tuple(item.to_domain() for item in self.events),
            story=self.story,
            quote=self.quote,
            rsvp=Rsvp(url=self.rsvp.url, deadline=self.rsvp.deadline),
            gift=Gift(
                show=self.gift.show,
                groom=self.gift.groom.to_domain(),
                bride=self.gift.bride.to_domain(),
            ),
            music_url=self.music_url,
            default_template=self.default_template,
            group_templates=dict(self.group_templates),
            wording={tone: dict(fields) for tone, fields in self.wording.items()},
            messages=dict(self.messages),
            open_style=self.open_style,
            theme=self.theme.to_domain(),
            card_design=self.card_design.to_domain(),
            schedule=tuple(ScheduleItem(time=i.time, label=i.label.strip()) for i in self.schedule),
            dress_code=DressCode(
                note=self.dress_code.note.strip(),
                colors=tuple(color.upper() for color in self.dress_code.colors),
            ),
        )

    @classmethod
    def of(cls, content: WeddingContent) -> WeddingContentIO:
        return cls(
            groom=PersonIO.of(content.groom),
            bride=PersonIO.of(content.bride),
            groom_parents=ParentsIO.of(content.groom_parents),
            bride_parents=ParentsIO.of(content.bride_parents),
            events=[EventIO.of(item) for item in content.events],
            story=content.story,
            quote=content.quote,
            rsvp=RsvpIO(url=content.rsvp.url, deadline=content.rsvp.deadline),
            gift=GiftIO(
                show=content.gift.show,
                groom=BankAccountIO.of(content.gift.groom),
                bride=BankAccountIO.of(content.gift.bride),
            ),
            music_url=content.music_url,
            default_template=content.default_template,
            group_templates=dict(content.group_templates),
            wording={tone: dict(fields) for tone, fields in content.wording.items()},
            messages=dict(content.messages),
            open_style=content.open_style,
            theme=ThemeIO.of(content.theme),
            card_design=CardDesignIO.of(content.card_design),
            schedule=[ScheduleItemIO(time=i.time, label=i.label) for i in content.schedule],
            dress_code=DressCodeIO(
                note=content.dress_code.note, colors=list(content.dress_code.colors)
            ),
        )


class WeddingOut(WeddingContentIO):
    """Đám cưới đầy đủ: nội dung + xuất bản + tiến độ."""

    id: UUID
    slug: str
    published: bool
    site_url: str
    checklist: dict[str, bool]
    updated_at: datetime | None = None

    @classmethod
    def of_wedding(cls, wedding: Wedding) -> WeddingOut:
        return cls(
            **WeddingContentIO.of(wedding.content).model_dump(),
            id=wedding.id,
            slug=wedding.slug,
            published=wedding.published,
            site_url=site_url(wedding.slug),
            checklist=dict(wedding.checklist),
            updated_at=wedding.updated_at,
        )


class PlanViolationOut(BaseModel):
    code: str
    message: str
    plan: str
    #: Khoá mẫu khi `code="template"` — web gợi ý đổi đúng mẫu đó.
    subject: str = ""


class PlanCheckOut(BaseModel):
    """Kết quả xét gói: gói hiện tại, gói cần có, và từng thứ đang vượt gói."""

    plan: str
    plan_label: str
    required: str
    required_label: str
    violations: list[PlanViolationOut]


class SetupIn(BaseModel):
    """`sample` = lưu dữ liệu mẫu (kèm khách mẫu); `blank` = bắt đầu trống."""

    mode: Literal["sample", "blank"]


class ChecklistIn(BaseModel):
    done: dict[Annotated[str, Field(max_length=10)], bool] = Field(default_factory=dict)


class PublicationIn(BaseModel):
    slug: Annotated[str, Field(min_length=3, max_length=60)]
    published: bool


class StudioOverviewOut(BaseModel):
    """Một dòng của màn giám sát xưởng thiệp."""

    studio_id: UUID
    couple: str
    slug: str
    published: bool
    site_url: str
    main_date: str
    events: int
    guests: int
    updated_at: datetime | None = None

    @classmethod
    def of(cls, item: StudioOverview) -> StudioOverviewOut:
        content = item.wedding.content
        return cls(
            studio_id=item.wedding.tenant_id,
            couple=f"{content.groom.short} & {content.bride.short}",
            slug=item.wedding.slug,
            published=item.wedding.published,
            site_url=site_url(item.wedding.slug),
            main_date=item.main_date,
            events=len(content.events),
            guests=item.guest_count,
            updated_at=item.wedding.updated_at,
        )


__all__ = [
    "ChecklistIn",
    "PlanCheckOut",
    "PublicationIn",
    "SetupIn",
    "StudioOverviewOut",
    "ThemeIO",
    "WeddingContentIO",
    "WeddingOut",
]
