"""Schema HTTP của `invitation`."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from app.modules.invitation.application.use_cases import Invitation


class BrandingOut(BaseModel):
    """`badge` = hiện dấu "Tạo bởi Xưởng Thiệp Hỷ" cuối web thiệp."""

    badge: bool
    plan: str


class InvitationOut(BaseModel):
    """Dữ liệu web thiệp.

    `wedding` cùng hình với `GET /wedding` (trừ trường nội bộ); `guest` là null
    khi mở link chung (hoặc gói chưa có link riêng); `template` là mẫu đã chọn
    sẵn cho người mở link.
    """

    wedding: dict[str, Any]
    photos: list[str]
    #: Bản nhỏ cùng thứ tự với `photos` — ghép thành `srcset`.
    photos_small: list[str] = []
    guest: dict[str, Any] | None
    #: Đuôi link đối tượng đã nhận diện; rỗng = link chung.
    link: str = ""
    template: str
    branding: BrandingOut
    #: Câu chữ mặc định hệ thống: `{wording: {giọng: {ô: câu}}, messages: {giọng: tin}}`.
    defaults: dict[str, Any] = {}

    @classmethod
    def of(cls, item: Invitation) -> InvitationOut:
        return cls(
            wedding=item.wedding,
            photos=item.photos,
            photos_small=item.photos_small,
            guest=item.guest,
            link=item.link,
            template=item.template,
            defaults=item.defaults,
            branding=BrandingOut(
                badge=bool(item.branding.get("badge")), plan=str(item.branding.get("plan"))
            ),
        )


class ReplyIn(BaseModel):
    """Phản hồi từ web thiệp. Mở link chung thì bắt buộc ghi `name`."""

    g: Annotated[str, Field(max_length=12)] = ""
    #: Đuôi link đối tượng khách đang mở — để cặp đôi biết phản hồi đến từ nhóm nào.
    link: Annotated[str, Field(max_length=40)] = ""
    name: Annotated[str, Field(max_length=160)] = ""
    status: Literal["yes", "maybe", "no"]
    count: Annotated[int, Field(ge=1, le=20)] = 1
    message: Annotated[str, Field(max_length=500)] = ""


class WishIn(BaseModel):
    """Sổ lưu bút: tên + lời chúc, không kèm xác nhận tham dự."""

    name: Annotated[str, Field(min_length=1, max_length=160)]
    message: Annotated[str, Field(min_length=1, max_length=500)]


class OpenIn(BaseModel):
    """Khách mở link riêng (`g` = mã sau dấu #) hoặc link đối tượng (`link` = đuôi link)."""

    g: Annotated[str, Field(max_length=12)] = ""
    link: Annotated[str, Field(max_length=40)] = ""


class ReplyOut(BaseModel):
    name: str
    status: str
    count: int


class PublicWishOut(BaseModel):
    name: str
    message: str
    created_at: datetime


__all__ = ["BrandingOut", "InvitationOut", "OpenIn", "PublicWishOut", "ReplyIn", "ReplyOut"]
