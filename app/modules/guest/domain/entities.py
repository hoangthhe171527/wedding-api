"""Thực thể thuần của `guest`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.guest.domain.enums import DEFAULT_GROUP, RsvpStatus, Side


@dataclass(frozen=True, slots=True)
class GuestDraft:
    """Nội dung một thiệp mời — thứ người soạn nhập ở form khách.

    Attributes:
        title: Danh xưng ("Bác", "Cô chú"...).
        plus: Kèm theo ("& gia đình", "& người thương"...).
        events: Id sự kiện được mời. Rỗng = mời theo nhà (sự kiện cùng `side`
            hoặc `chung`), đúng luật `eventsFor()` của thiết kế.
        count: Số người của thiệp — dùng ước tính số bàn.
        template: Mẫu riêng; rỗng = theo mẫu của nhóm.
    """

    name: str
    title: str = ""
    plus: str = ""
    group: str = DEFAULT_GROUP
    side: Side = Side.TRAI
    events: tuple[str, ...] = ()
    count: int = 1
    template: str = ""
    status: RsvpStatus = RsvpStatus.NONE
    sent: bool = False
    note: str = ""


@dataclass(frozen=True, slots=True)
class GuestReply:
    """Phản hồi khách tự gửi từ web thiệp (khác `status` người soạn đánh dấu tay)."""

    count: int
    message: str
    replied_at: datetime


@dataclass(frozen=True, slots=True)
class GuestOpens:
    """Khách đã mở link riêng: số lần, lần đầu, lần gần nhất."""

    count: int
    first_at: datetime
    last_at: datetime


@dataclass(frozen=True, slots=True)
class Guest:
    """Một thiệp mời đã lưu.

    `code` là mã 6 ký tự nằm cuối link riêng (`<link thiệp>#<code>`), mở ra đúng
    tên, đúng mẫu, đúng tiệc của khách. Duy nhất trong một xưởng.
    """

    id: UUID
    tenant_id: UUID
    code: str
    draft: GuestDraft
    created_at: datetime | None = None
    updated_at: datetime | None = None
    reply: GuestReply | None = None
    opens: GuestOpens | None = None


@dataclass(frozen=True, slots=True)
class Wish:
    """Một lời chúc / phản hồi gửi từ web thiệp.

    Khách mở link riêng thì `guest_code` là mã của họ; khách mở link chung tự
    ghi tên — đó là cách duy nhất cặp đôi biết họ là ai.
    """

    id: UUID
    tenant_id: UUID
    name: str
    message: str
    status: RsvpStatus
    count: int
    guest_code: str
    created_at: datetime
    #: Đuôi link đối tượng phản hồi được gửi từ đó; rỗng = link chung hoặc link riêng.
    link: str = ""


@dataclass(frozen=True, slots=True)
class InviteLink:
    """Link theo đối tượng: MỘT link gửi cho cả một nhóm người (nhóm Zalo công ty,
    lớp đại học...) — ai mở cũng thấy đúng mẫu thiệp dành cho nhóm đó.

    Khác link riêng (`#mã`, một người, mở ra đúng tên): link đối tượng không biết
    người mở là ai, nên phản hồi gửi từ đây vẫn phải ghi tên.

    Attributes:
        slug: Đuôi link sau slug thiệp — `/invite/<slug thiệp>/<slug>`.
        name: Tên để cặp đôi nhận ra ("Đồng nghiệp công ty"); không lên thiệp.
        template: Mẫu riêng; rỗng = mẫu mặc định của thiệp.
    """

    id: UUID
    tenant_id: UUID
    slug: str
    name: str
    template: str = ""
    opens: int = 0
    last_opened_at: datetime | None = None
    created_at: datetime | None = None


__all__ = ["Guest", "GuestDraft", "GuestReply", "InviteLink", "Wish"]
