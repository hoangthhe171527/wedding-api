"""Use case: khách gửi phản hồi và đọc lời chúc trên web thiệp công khai.

`invitation` không sở hữu dữ liệu nào: nó tra xưởng theo slug rồi chuyển phản
hồi cho `guest` (chủ sở hữu `guests`, `guest_wishes`) qua cầu nối.
"""

from __future__ import annotations

from typing import Any

from app.modules.invitation.application.ports import (
    Entitlements,
    GuestReplies,
    PublishedWeddings,
)
from app.modules.invitation.application.use_cases.get_invitation import invitation_not_found

#: Số lời chúc hiện trên web thiệp.
PUBLIC_WISHES_LIMIT = 60


class SubmitReply:
    def __init__(
        self, weddings: PublishedWeddings, replies: GuestReplies, entitlements: Entitlements
    ) -> None:
        self._weddings = weddings
        self._replies = replies
        self._entitlements = entitlements

    async def execute(
        self, slug: str, *, code: str, name: str, status: str, count: int, message: str
    ) -> dict[str, Any]:
        """Raises: NotFoundError (thiệp chưa mở), ValidationError (thiếu tên...)."""
        found = await self._weddings.by_slug(slug)
        if found is None:
            raise invitation_not_found()
        tenant_id, _ = found
        plan = await self._entitlements.plan_for(tenant_id)
        return await self._replies.respond(
            tenant_id,
            code=code if plan.get("per_guest_links") else "",
            name=name,
            status=status,
            count=count,
            message=message,
        )


class SubmitWish:
    """Sổ lưu bút trên web thiệp: chỉ lời chúc, không xác nhận tham dự."""

    def __init__(self, weddings: PublishedWeddings, replies: GuestReplies) -> None:
        self._weddings = weddings
        self._replies = replies

    async def execute(self, slug: str, *, name: str, message: str) -> dict[str, Any]:
        """Raises: NotFoundError (thiệp chưa mở), ValidationError (thiếu tên / lời chúc)."""
        found = await self._weddings.by_slug(slug)
        if found is None:
            raise invitation_not_found()
        return await self._replies.wish(found[0], name=name, message=message)


class ListPublicWishes:
    def __init__(self, weddings: PublishedWeddings, replies: GuestReplies) -> None:
        self._weddings = weddings
        self._replies = replies

    async def execute(self, slug: str) -> list[dict[str, Any]]:
        found = await self._weddings.by_slug(slug)
        if found is None:
            raise invitation_not_found()
        return await self._replies.public_wishes(found[0], PUBLIC_WISHES_LIMIT)


class RecordOpen:
    """Khách mở link riêng — để cặp đôi biết ai đã xem thiệp.

    Chỉ ghi khi gói có link riêng từng khách (gói miễn phí không nhận diện khách).
    Mã sai / khách đã xoá thì lặng lẽ bỏ qua: không cho dò mã qua endpoint này.
    """

    def __init__(
        self, weddings: PublishedWeddings, replies: GuestReplies, entitlements: Entitlements
    ) -> None:
        self._weddings = weddings
        self._replies = replies
        self._entitlements = entitlements

    async def execute(self, slug: str, code: str) -> None:
        found = await self._weddings.by_slug(slug)
        if found is None:
            raise invitation_not_found()
        tenant_id, _ = found
        plan = await self._entitlements.plan_for(tenant_id)
        if code and plan.get("per_guest_links"):
            await self._replies.record_open(tenant_id, code)


__all__ = ["ListPublicWishes", "RecordOpen", "SubmitReply", "SubmitWish"]
