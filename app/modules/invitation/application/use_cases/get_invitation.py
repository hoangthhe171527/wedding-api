"""Use case: dữ liệu web thiệp cho MỘT người mở link.

Thay cho `InviteLib.boot(DATA)` của thiết kế — nơi file web tĩnh nhúng TOÀN BỘ
danh sách khách vào trang công khai. Ở đây mỗi lượt mở chỉ nhận đúng vị khách
ứng với mã trong link (hoặc không ai, nếu là link chung).

Mã khách sai/không tồn tại KHÔNG phải lỗi: trang vẫn mở như link chung — đúng
hành vi `DATA.guests[code] || null` của thiết kế, và không cho người dò biết mã
nào có thật.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from app.core.errors import NotFoundError
from app.modules.invitation.application.ports import (
    Entitlements,
    GuestsByCode,
    IntroVideos,
    PhotoLister,
    PublishedWeddings,
    WordingDefaults,
)
from app.modules.invitation.domain.services import (
    apply_design,
    effective_intro,
    effective_template,
    for_audience,
    public_guest,
    public_wedding,
)


@dataclass(frozen=True, slots=True)
class Invitation:
    wedding: dict[str, Any]
    photos: list[str]
    #: Bản nhỏ cùng thứ tự với `photos` (điện thoại chọn qua `srcset`).
    photos_small: list[str]
    guest: dict[str, Any] | None
    #: Đuôi link đối tượng đã nhận diện; rỗng = link chung (hoặc đuôi lạ, gói miễn phí).
    link: str
    #: Người được mời của link đối tượng ("Quý đồng nghiệp"); rỗng = "Quý khách".
    greeting: str
    template: str
    #: `badge`: hiện dấu "Tạo bởi Xưởng Thiệp Hỷ" (gói chưa bỏ dấu).
    branding: dict[str, Any]
    #: Câu chữ mặc định hệ thống (`wording`, `messages`) — ô xưởng chưa tự sửa dùng câu này.
    defaults: dict[str, Any]


def invitation_not_found() -> NotFoundError:
    return NotFoundError(
        "Không tìm thấy thiệp mời. Link có thể đã đổi hoặc chưa được mở.",
        code="invitation_not_found",
    )


class GetInvitation:
    """Ghép đám cưới + ảnh + khách + mẫu hiệu lực."""

    def __init__(
        self,
        weddings: PublishedWeddings,
        guests: GuestsByCode,
        photos: PhotoLister,
        entitlements: Entitlements,
        wording: WordingDefaults,
        intros: IntroVideos,
    ) -> None:
        self._weddings = weddings
        self._guests = guests
        self._photos = photos
        self._entitlements = entitlements
        self._wording = wording
        self._intros = intros

    async def execute(self, slug: str, code: str | None, link: str | None = None) -> Invitation:
        """`link` là đuôi link đối tượng (`/invite/<slug>/<đuôi>`); đuôi lạ mở như link chung.

        Raises: NotFoundError nếu slug không tồn tại hoặc chưa xuất bản.
        """
        found = await self._weddings.by_slug(slug)
        if found is None:
            raise invitation_not_found()
        tenant_id, snapshot = found
        # Ba nguồn độc lập nhau: hỏi song song thay vì lần lượt.
        plan, system, album = await asyncio.gather(
            self._entitlements.plan_for(tenant_id),
            self._wording.defaults(),
            self._photos.album(tenant_id),
        )
        # Gói chưa có link riêng từng khách: mọi link (kể cả link đối tượng) mở như link chung.
        personal = bool(plan.get("per_guest_links"))
        guest = await self._guests.by_code(tenant_id, code) if code and personal else None
        guest_link = (guest or {}).get("link") or None
        url_link = await self._guests.by_link(tenant_id, link) if link and personal else None
        audience = guest_link or url_link
        template = effective_template(
            guest_link=guest_link,
            url_link=url_link,
            default_template=str(snapshot.get("default_template") or ""),
        )
        canonical = self._wording.canonical_template
        # Design và mẫu chính so theo khoá chuẩn: khoá mẫu đã nghỉ vẫn khớp.
        snapshot = apply_design(snapshot, template, canonical)
        wedding = public_wedding(snapshot)
        if wedding.get("default_template"):
            wedding["default_template"] = canonical(str(wedding["default_template"]))
        design = wedding.get("card_design")
        if isinstance(design, dict) and design.get("base"):
            wedding["card_design"] = {**design, "base": canonical(str(design["base"]))}
        shown_guest = public_guest(guest)
        if shown_guest is not None:
            shown_guest.pop("link", None)
            if shown_guest.get("template"):
                shown_guest["template"] = canonical(str(shown_guest["template"]))
        intro = effective_intro(str(snapshot.get("intro") or ""))
        intro_url = await self._intros.url_of(intro) if intro else ""
        return Invitation(
            wedding={**for_audience(wedding, audience), "intro_url": intro_url},
            photos=album["full"],
            photos_small=album["small"],
            guest=shown_guest,
            link=str(audience["slug"]) if audience else "",
            greeting=str(audience.get("greeting") or "") if audience else "",
            template=canonical(template),
            branding={"badge": not plan.get("remove_badge"), "plan": plan.get("plan", "free")},
            defaults={
                "wording": system.get("wording") or {},
                "messages": system.get("messages") or {},
            },
        )


__all__ = ["GetInvitation", "Invitation", "invitation_not_found"]
