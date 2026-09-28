"""Thực thể thuần của `template`."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.template.domain.enums import Family, Layout, Tier, Tone


@dataclass(frozen=True, slots=True)
class Template:
    """Một mẫu thiệp.

    Backend giữ phần **siêu dữ liệu** (tên, dòng, giọng văn, bố cục, trạng thái
    mở/đóng). Phần hình — màu, phông, canvas, hiệu ứng — nằm ở thư viện render
    của web (`InviteLib`), khoá theo cùng `key`. Tách vậy để đội vận hành bật/tắt
    một mẫu mà không phải phát hành lại web.

    Attributes:
        key: Khoá tự nhiên, trùng `id` trong `InviteLib.TEMPLATES` (vd `uyenuong`).
        is_active: Tắt thì khách không chọn được nữa; thiệp đã gán vẫn hiển thị.
    """

    key: str
    name: str
    family: Family
    tone: Tone
    layout: Layout
    is_new: bool = False
    is_active: bool = True
    sort_order: int = 0
    #: Gói tối thiểu để xuất bản thiệp dùng mẫu này (xem `Tier`).
    tier: Tier = Tier.STANDARD


__all__ = ["Template"]
