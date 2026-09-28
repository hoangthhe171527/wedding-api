"""Dữ liệu mẫu và trang trắng — chép nguyên `SAMPLE_W` và `seed(blank)` của thiết kế.

Xưởng mới mở ra thấy dữ liệu mẫu kèm lời mời "Lưu mẫu này để chỉnh thành đám cưới
của bạn, hoặc bắt đầu từ trang trắng" — hai hàm dưới đây là hai lựa chọn đó.
"""

from __future__ import annotations

from app.modules.wedding.domain.entities import (
    BankAccount,
    DressCode,
    Event,
    Gift,
    Parents,
    Person,
    Rsvp,
    ScheduleItem,
    WeddingContent,
)
from app.modules.wedding.domain.enums import EventKind, Side

#: Mẫu mặc định theo nhóm khách của dữ liệu mẫu thiết kế.
#: Chỉ dùng mẫu của gói Miễn phí: xưởng mới (gói Miễn phí) lưu mẫu hay bắt đầu trống
#: đều xuất bản được ngay. Trước đây mẫu gán sẵn mẫu trả phí — người dùng làm theo
#: gợi ý rồi bị chặn ở bước xuất bản. Khoá bởi test_setup_mien_phi_xuat_ban_duoc.
SAMPLE_GROUP_TEMPLATES: dict[str, str] = {
    "Họ hàng": "songhy",
    "Bạn bố mẹ": "hongphuc",
    "Hàng xóm": "hongphuc",
    "Thầy cô": "ngoctrai",
    "Đồng nghiệp": "ngoctrai",
    "Đối tác": "ngoctrai",
    "Bạn bè": "maudon",
}
#: Mẫu của link chung (khách không mã) — trang trọng vừa phải, hợp mọi nhóm.
SAMPLE_DEFAULT_TEMPLATE = "ngoctrai"


#: Lịch trình mẫu của tiệc tối — cùng các mốc mà web thiệp mẫu thường dùng.
SAMPLE_SCHEDULE: tuple[ScheduleItem, ...] = (
    ScheduleItem(time="17:00", label="Đón khách"),
    ScheduleItem(time="18:00", label="Khai tiệc"),
    ScheduleItem(time="18:30", label="Nghi thức cưới"),
    ScheduleItem(time="19:00", label="Cắt bánh & nâng ly"),
    ScheduleItem(time="20:30", label="Kết thúc tiệc"),
)


def sample_content() -> WeddingContent:
    """Đám cưới mẫu Huy Hoàng & Hải Hà."""
    return WeddingContent(
        groom=Person(
            full="Trần Huy Hoàng", short="Huy Hoàng", rank="Trưởng nam", phone="0912 345 678"
        ),
        bride=Person(full="Nguyễn Hải Hà", short="Hải Hà", rank="Út nữ", phone="0987 654 321"),
        groom_parents=Parents(
            father="Ông Trần Văn Thành",
            mother="Bà Lê Thị Hạnh",
            address="Xã Đông Anh, TP. Hà Nội",
        ),
        bride_parents=Parents(
            father="Ông Nguyễn Quang Vinh",
            mother="Bà Phạm Thị Thu",
            address="Phường Kinh Bắc, tỉnh Bắc Ninh",
        ),
        events=(
            Event(
                id="e1",
                name="Lễ Vu Quy",
                kind=EventKind.LE,
                side=Side.GAI,
                date="2026-11-28",
                time="08:00",
                venue="Tư gia nhà gái",
                address="Số 18 ngõ Hoa Mai, phường Kinh Bắc, tỉnh Bắc Ninh",
            ),
            Event(
                id="e2",
                name="Tiệc cưới nhà gái",
                kind=EventKind.TIEC,
                side=Side.GAI,
                date="2026-11-28",
                time="11:00",
                arrival="10:30",
                venue="Sảnh Hoàng Lan – Nhà hàng Hương Cau",
                address="Số 25 đường Nguyễn Trãi, phường Kinh Bắc, tỉnh Bắc Ninh",
            ),
            Event(
                id="e3",
                name="Lễ Thành Hôn",
                kind=EventKind.LE,
                side=Side.TRAI,
                date="2026-11-29",
                time="09:00",
                venue="Tư gia nhà trai",
                address="Thôn Đông, xã Đông Anh, TP. Hà Nội",
            ),
            Event(
                id="e4",
                name="Tiệc cưới nhà trai",
                kind=EventKind.TIEC,
                side=Side.TRAI,
                date="2026-11-29",
                time="18:00",
                arrival="17:30",
                venue="Sảnh Ngọc Bích – Trung tâm tiệc cưới Hoa Sen Vàng",
                address="Số 88 đường Lạc Long Quân, phường Tây Hồ, TP. Hà Nội",
            ),
        ),
        story=("Gặp nhau ở giảng đường năm 2019, bảy năm sau hai đứa quyết định về chung một nhà."),
        quote="Cảm ơn vì đã đến, để ngày chung đôi của chúng mình thêm trọn vẹn.",
        rsvp=Rsvp(url="", deadline="2026-11-20"),
        # Hộp mừng cưới thuộc Gói Hỷ: điền sẵn số tài khoản để bật là dùng được ngay,
        # nhưng mặc định tắt để gói Miễn phí xuất bản được.
        gift=Gift(
            show=False,
            groom=BankAccount(bank="Vietcombank", number="0123 456 789", holder="TRAN HUY HOANG"),
            bride=BankAccount(bank="Techcombank", number="1903 5555 8888", holder="NGUYEN HAI HA"),
        ),
        default_template=SAMPLE_DEFAULT_TEMPLATE,
        group_templates=dict(SAMPLE_GROUP_TEMPLATES),
        schedule=SAMPLE_SCHEDULE,
        dress_code=DressCode(note="Trang phục lịch sự, tông màu ấm"),
    )


def blank_content() -> WeddingContent:
    """Trang trắng — giữ mẫu theo nhóm để khách mới vẫn tự nhận mẫu phù hợp."""
    return WeddingContent(
        groom=Person(short="Chú rể", rank="Trưởng nam"),
        bride=Person(short="Cô dâu", rank="Trưởng nữ"),
        groom_parents=Parents(),
        bride_parents=Parents(),
        events=(),
        gift=Gift(show=False),
        default_template=SAMPLE_DEFAULT_TEMPLATE,
        group_templates=dict(SAMPLE_GROUP_TEMPLATES),
    )


__all__ = ["SAMPLE_GROUP_TEMPLATES", "blank_content", "sample_content"]
