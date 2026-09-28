"""Thực thể thuần của `wedding` — đúng mô hình `W` của thiết kế.

Một xưởng có đúng một đám cưới. Phần nội dung (`WeddingContent`) tách khỏi phần
trạng thái xuất bản/tiến độ để `PUT /wedding` (lưu tự động từ form) không bao giờ
vô tình đè slug hay tiến độ lộ trình.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.modules.wedding.domain.design import CardDesign
from app.modules.wedding.domain.enums import EventKind, OpenStyle, Side


@dataclass(frozen=True, slots=True)
class Person:
    """Cô dâu hoặc chú rể."""

    full: str = ""
    short: str = ""
    rank: str = ""
    phone: str = ""


@dataclass(frozen=True, slots=True)
class Parents:
    """Bố mẹ một bên — ghi cả danh xưng, vd "Ông Trần Văn Thành"."""

    father: str = ""
    mother: str = ""
    address: str = ""


@dataclass(frozen=True, slots=True)
class Event:
    """Một lễ hoặc tiệc. `date` là chuỗi `yyyy-mm-dd`, `time` là `HH:MM` (§1.6)."""

    id: str
    name: str
    kind: EventKind
    side: Side
    date: str = ""
    time: str = ""
    venue: str = ""
    address: str = ""
    map_url: str = ""
    #: Giờ đón khách (`HH:MM`), trước giờ khai tiệc `time`. Rỗng = không hiện.
    arrival: str = ""


@dataclass(frozen=True, slots=True)
class ScheduleItem:
    """Một mốc trong lịch trình ngày cưới (đón khách, khai tiệc, cắt bánh...)."""

    time: str = ""
    label: str = ""


@dataclass(frozen=True, slots=True)
class DressCode:
    """Trang phục gợi ý: một dòng ghi chú + vài màu (`#RRGGBB`)."""

    note: str = ""
    colors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Rsvp:
    """Xác nhận tham dự: link Google Form (có thể chứa `{ten}`) + hạn phản hồi."""

    url: str = ""
    deadline: str = ""


@dataclass(frozen=True, slots=True)
class BankAccount:
    bank: str = ""
    number: str = ""
    holder: str = ""
    #: Ảnh QR do cặp đôi tải lên (data URL); trống thì web thiệp tự tạo VietQR.
    qr: str = ""


@dataclass(frozen=True, slots=True)
class Gift:
    """Hộp mừng cưới trên web thiệp — tắt thì số tài khoản không lộ ra ngoài."""

    show: bool = False
    groom: BankAccount = field(default_factory=BankAccount)
    bride: BankAccount = field(default_factory=BankAccount)


@dataclass(frozen=True, slots=True)
class Theme:
    """Tuỳ chỉnh giao diện đè lên màu, font, hiệu ứng nền của mẫu. Ô trống = theo mẫu.

    Attributes:
        accent: Màu nhấn (tên cô dâu chú rể, nút, đường viền).
        accent2: Màu nhũ / màu phụ.
        ink: Màu chữ chính.
        ambient: Hiệu ứng nền (`petals`, `lanterns`...); `none` = tắt; rỗng = theo mẫu.
        density: Mật độ hiệu ứng nền; 0 = theo mẫu.
    """

    accent: str = ""
    accent2: str = ""
    ink: str = ""
    font_display: str = ""
    font_script: str = ""
    font_body: str = ""
    ambient: str = ""
    density: float = 0.0
    #: Màu màn mở thiệp: thân phong bì / cánh cửa / hộp quà, và màu viền / cánh hoa.
    intro: str = ""
    intro2: str = ""
    #: Thứ tự các phần của web thiệp (rỗng = theo mẫu) và các phần ẩn đi.
    sections: tuple[str, ...] = ()
    hidden: tuple[str, ...] = ()

    @property
    def customized(self) -> bool:
        return any(
            (
                self.accent,
                self.accent2,
                self.ink,
                self.font_display,
                self.font_script,
                self.font_body,
                self.ambient,
                self.density,
                self.intro,
                self.intro2,
                self.sections,
                self.hidden,
            )
        )


@dataclass(frozen=True, slots=True)
class WeddingContent:
    """Mọi thứ người soạn thiệp sửa ở tab Thông tin cưới và Mẫu thiệp."""

    groom: Person
    bride: Person
    groom_parents: Parents
    bride_parents: Parents
    events: tuple[Event, ...]
    story: str = ""
    quote: str = ""
    rsvp: Rsvp = field(default_factory=Rsvp)
    gift: Gift = field(default_factory=Gift)
    music_url: str = ""
    default_template: str = ""
    group_templates: dict[str, str] = field(default_factory=dict)
    #: `{giọng văn: {ô câu chữ: nội dung}}` — ô bỏ trống dùng câu mặc định.
    wording: dict[str, dict[str, str]] = field(default_factory=dict)
    #: `{giọng văn: tin nhắn gửi kèm link}` với các ô `{khach}`, `{link}`...
    messages: dict[str, str] = field(default_factory=dict)
    open_style: OpenStyle = OpenStyle.BY_TEMPLATE
    theme: Theme = field(default_factory=Theme)
    #: Thiệp tự thiết kế (lớp đặt tự do); tắt = dùng bố cục của mẫu.
    card_design: CardDesign = field(default_factory=CardDesign)
    #: Lịch trình ngày cưới — rỗng thì web thiệp bỏ hẳn phần này.
    schedule: tuple[ScheduleItem, ...] = ()
    dress_code: DressCode = field(default_factory=DressCode)


@dataclass(frozen=True, slots=True)
class Wedding:
    """Đám cưới của một xưởng.

    Attributes:
        slug: Đường dẫn công khai `/invite/<slug>`; duy nhất toàn hệ thống.
        published: Tắt thì link công khai trả 404 — soạn xong mới mở cho khách.
        checklist: Tiến độ lộ trình `{c1: True, ...}`, lưu chung cho cả hai người.
    """

    id: UUID
    tenant_id: UUID
    content: WeddingContent
    slug: str
    published: bool = False
    checklist: dict[str, bool] = field(default_factory=dict)
    updated_at: datetime | None = None


__all__ = [
    "BankAccount",
    "Event",
    "Gift",
    "Parents",
    "Person",
    "Rsvp",
    "Theme",
    "Wedding",
    "WeddingContent",
]
