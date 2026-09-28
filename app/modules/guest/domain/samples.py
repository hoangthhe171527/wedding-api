"""Danh sách khách mẫu — chép nguyên `SAMPLE_GUESTS` của thiết kế (kèm mã khách)."""

from __future__ import annotations

from typing import Final

from app.modules.guest.domain.entities import GuestDraft
from app.modules.guest.domain.enums import RsvpStatus, Side

SAMPLE_GUESTS: Final[tuple[tuple[str, GuestDraft], ...]] = (
    ("bh7k2m", GuestDraft(title="Bác", name="Hùng", plus="& gia đình", group="Họ hàng",
        side=Side.TRAI, events=("e3", "e4"), count=4, status=RsvpStatus.YES, sent=True,
        note="Anh trai bố")),
    ("cl3q8t", GuestDraft(title="Cô chú", name="Lan – Tuấn", group="Họ hàng", side=Side.GAI,
        events=("e1", "e2"), count=2, template="hongphuc", status=RsvpStatus.YES, sent=True)),
    ("bt9w4d", GuestDraft(title="Bác", name="Tâm", plus="& gia đình", group="Bạn bố mẹ",
        side=Side.GAI, events=("e2",), count=3, sent=True)),
    ("op5r1x", GuestDraft(title="Ông bà", name="Phúc", group="Hàng xóm", side=Side.TRAI,
        events=("e4",), count=2, status=RsvpStatus.MAYBE, note="Nhà đối diện")),
    ("ta2n6v", GuestDraft(title="Thầy", name="Nguyễn Đức An", plus="& gia đình",
        group="Thầy cô", side=Side.TRAI, events=("e4",), count=2, note="GVCN cấp 3")),
    ("av8c3k", GuestDraft(title="Anh", name="Đặng Quốc Việt", plus="& chị", group="Đối tác",
        side=Side.TRAI, events=("e4",), count=2, status=RsvpStatus.YES, sent=True,
        note="Giám đốc khối")),
    ("cm4h7p", GuestDraft(title="Chị", name="Hoàng Mai Anh", group="Đồng nghiệp",
        side=Side.GAI, events=("e2",), count=1)),
    ("at6y2j", GuestDraft(title="Anh", name="Đỗ Thành Trung", group="Đồng nghiệp",
        side=Side.TRAI, events=("e4",), count=1, status=RsvpStatus.NO,
        sent=True, note="Đi công tác")),
    ("tt1s9b", GuestDraft(name="Thu Trang", plus="& người thương", group="Bạn bè",
        side=Side.GAI, events=("e2",), count=2, template="xothom", status=RsvpStatus.YES,
        sent=True)),
    ("hb5z0q", GuestDraft(name="Hội bạn lớp 12A1", group="Bạn bè", side=Side.TRAI,
        events=("e4",), count=8)),
)  # fmt: skip

__all__ = ["SAMPLE_GUESTS"]
