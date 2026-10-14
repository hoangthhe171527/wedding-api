"""Thực thể thuần của `template`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

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


@dataclass(frozen=True, slots=True)
class Intro:
    """Một video mở thiệp trong thư viện chung (đội vận hành tải lên).

    Cặp đôi chọn một video làm mặc định cho thiệp, và đổi riêng cho từng link đối
    tượng. Byte video nằm ở kho object (`key`), Mongo chỉ giữ siêu dữ liệu.

    Attributes:
        key: Khoá object trong kho S3 (`intros/<id>.mp4`).
        is_active: Tắt thì khách không chọn được nữa; thiệp đã chọn vẫn phát.
    """

    id: UUID
    name: str
    key: str
    content_type: str
    size: int
    order: int = 0
    is_active: bool = True
    created_at: datetime | None = None


__all__ = ["Intro", "Template"]
