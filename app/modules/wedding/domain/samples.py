"""Dữ liệu mẫu và trang trắng — chép nguyên `SAMPLE_W` và `seed(blank)` của thiết kế.

Xưởng mới mở ra thấy dữ liệu mẫu kèm lời mời "Lưu mẫu này để chỉnh thành đám cưới
của bạn, hoặc bắt đầu từ trang trắng" — hai hàm dưới đây là hai lựa chọn đó.
"""

from __future__ import annotations

from app.modules.wedding.domain.entities import (
    BankAccount,
    Event,
    Gift,
    Parents,
    Person,
    Rsvp,
    WeddingContent,
)
from app.modules.wedding.domain.enums import EventKind, Side

#: Mẫu mặc định theo nhóm khách của dữ liệu mẫu thiết kế.
SAMPLE_GROUP_TEMPLATES: dict[str, str] = {
    "Họ hàng": "songhy",
    "Bạn bố mẹ": "hongphuc",
    "Hàng xóm": "hongphuc",
    "Thầy cô": "luadao",
    "Đồng nghiệp": "cucquang",
    "Đối tác": "hatkim",
    "Bạn bè": "uyenuong",
}


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
                venue="Sảnh Ngọc Bích – Trung tâm tiệc cưới Hoa Sen Vàng",
                address="Số 88 đường Lạc Long Quân, phường Tây Hồ, TP. Hà Nội",
            ),
        ),
        story=("Gặp nhau ở giảng đường năm 2019, bảy năm sau hai đứa quyết định về chung một nhà."),
        quote="Cảm ơn vì đã đến, để ngày chung đôi của chúng mình thêm trọn vẹn.",
        rsvp=Rsvp(url="", deadline="2026-11-20"),
        gift=Gift(
            show=True,
            groom=BankAccount(bank="Vietcombank", number="0123 456 789", holder="TRAN HUY HOANG"),
            bride=BankAccount(bank="Techcombank", number="1903 5555 8888", holder="NGUYEN HAI HA"),
        ),
        default_template="uyenuong",
        group_templates=dict(SAMPLE_GROUP_TEMPLATES),
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
        default_template="uyenuong",
        group_templates=dict(SAMPLE_GROUP_TEMPLATES),
    )


__all__ = ["SAMPLE_GROUP_TEMPLATES", "blank_content", "sample_content"]
