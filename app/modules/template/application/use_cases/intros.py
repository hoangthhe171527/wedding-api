"""Use case: thư viện video mở thiệp.

Đội vận hành (`template.manage`) tải lên, đổi tên, sắp xếp, bật/tắt, xoá. Khách
dùng mẫu (`template.view`) chỉ thấy video đang mở — để chọn cho thiệp và cho từng
link đối tượng. Phân nhánh theo QUYỀN, không theo tên vai trò (§0.1).

Video đã tắt vẫn PHÁT được qua URL đã ký: tắt chỉ ẩn khỏi bộ chọn, thiệp đã chọn
không bị đổi ngầm. Video đã xoá thì URL trả 404, web thiệp lùi về hiệu ứng cửa.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from app.core import audit
from app.core.config import get_settings
from app.core.context import ActorContext
from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.permissions import Permission
from app.core.security import signing
from app.modules.template.application.intro_urls import SIGN_KIND, intro_url
from app.modules.template.domain.entities import Intro
from app.modules.template.domain.intros import intro_name, sniff_video
from app.modules.template.domain.repositories import IntroRepository

log = get_logger(__name__)

#: URL ký của kho sống tối thiểu chừng này, kể cả khi URL của API sắp hết hạn —
#: đủ để trình duyệt tải xong video sau khi được chuyển hướng.
_MIN_DIRECT_SECONDS = 300


@dataclass(frozen=True, slots=True)
class IntroView:
    """Một video kèm URL đã ký (dùng thẳng trong `<video src>`)."""

    intro: Intro
    url: str


@dataclass(frozen=True, slots=True)
class IntroPatch:
    """Chỉ các trường gửi lên mới được đổi."""

    name: str | None = None
    is_active: bool | None = None
    order: int | None = None


def intro_not_found() -> NotFoundError:
    return NotFoundError("Không tìm thấy video mở thiệp.", code="intro_not_found")


class ListIntros:
    """Thư viện theo thứ tự hiển thị; người quản lý thấy cả video đã tắt."""

    def __init__(self, intros: IntroRepository) -> None:
        self._intros = intros

    async def execute(self, actor: ActorContext) -> list[IntroView]:
        include_inactive = actor.has(Permission.TEMPLATE_MANAGE.value)
        items = await self._intros.list_all(include_inactive=include_inactive)
        return [IntroView(intro=item, url=intro_url(item.id)) for item in items]


class UploadIntro:
    """Kiểm định dạng theo byte đầu tệp rồi thêm vào CUỐI thư viện."""

    def __init__(self, intros: IntroRepository) -> None:
        self._intros = intros

    async def execute(
        self, actor: ActorContext, data: bytes, *, filename: str | None, name: str | None
    ) -> Intro:
        """Raises: ValidationError (rỗng / quá lớn / không phải MP4, WebM)."""
        if not data:
            raise ValidationError("Tệp video rỗng.", code="intro_empty")
        limit = get_settings().INTRO_MAX_BYTES
        if len(data) > limit:
            raise ValidationError(
                f"Video quá lớn (tối đa {limit / 1_000_000:.0f} MB).", code="intro_too_large"
            )
        content_type = sniff_video(data)
        if content_type is None:
            raise ValidationError("Chỉ nhận video MP4 hoặc WebM.", code="intro_unsupported")
        intro = await self._intros.create(
            name=intro_name(name, filename),
            data=data,
            content_type=content_type,
            order=await self._intros.next_order(),
            actor_id=actor.user_id,
        )
        log.info("intro_uploaded", intro_id=str(intro.id), size=intro.size)
        await audit.record(
            "intro.created",
            actor_id=actor.user_id,
            target_type="intro",
            target_id=intro.id,
            details={"name": intro.name, "size": intro.size},
        )
        return intro


class UpdateIntro:
    """Đổi tên, bật/tắt, đổi thứ tự một video."""

    def __init__(self, intros: IntroRepository) -> None:
        self._intros = intros

    async def execute(self, actor: ActorContext, intro_id: UUID, patch: IntroPatch) -> Intro:
        """Raises: NotFoundError, ValidationError (tên trống)."""
        name = patch.name.strip() if patch.name is not None else None
        if name is not None and not name:
            raise ValidationError(
                "Đặt tên cho video.", code="intro_name_required", errors={"name": ["Bắt buộc."]}
            )
        updated = await self._intros.update(
            intro_id, name=name, is_active=patch.is_active, order=patch.order
        )
        if updated is None:
            raise intro_not_found()
        await audit.record(
            "intro.updated",
            actor_id=actor.user_id,
            target_type="intro",
            target_id=intro_id,
            details={
                field: value
                for field, value in (
                    ("name", name),
                    ("is_active", patch.is_active),
                    ("order", patch.order),
                )
                if value is not None
            },
        )
        return updated


class DeleteIntro:
    """Xoá hẳn video — thiệp đang chọn video này lùi về hiệu ứng cửa."""

    def __init__(self, intros: IntroRepository) -> None:
        self._intros = intros

    async def execute(self, actor: ActorContext, intro_id: UUID) -> None:
        """Raises: NotFoundError."""
        if not await self._intros.delete(intro_id):
            raise intro_not_found()
        log.info("intro_deleted", intro_id=str(intro_id), by=str(actor.user_id))
        await audit.record(
            "intro.deleted", actor_id=actor.user_id, target_type="intro", target_id=intro_id
        )


@dataclass(frozen=True, slots=True)
class IntroMedia:
    """Kết quả mở URL đã ký: chuyển hướng thẳng tới kho, hoặc video để API đọc hộ."""

    intro: Intro | None = None
    redirect: str | None = None


class ReadIntro:
    """Phục vụ byte video qua URL đã ký (công khai, không cần đăng nhập).

    Chữ ký sai, hết hạn hay video đã xoá đều trả **404** — không xác nhận cho
    người dò rằng id đó có tồn tại.
    """

    def __init__(self, intros: IntroRepository) -> None:
        self._intros = intros

    async def open(self, intro_id: UUID, *, expires_at: int, signature: str) -> IntroMedia:
        """Raises: NotFoundError."""
        if not signing.verify(SIGN_KIND, str(intro_id), expires_at=expires_at, signature=signature):
            raise intro_not_found()
        intro = await self._intros.get(intro_id)
        if intro is None:
            raise intro_not_found()
        ttl = max(expires_at - int(time.time()), _MIN_DIRECT_SECONDS)
        # S3 giới hạn URL ký tối đa 7 ngày.
        url = self._intros.direct_url(intro, timedelta(seconds=min(ttl, 7 * 86400)))
        if url:
            return IntroMedia(redirect=url)
        return IntroMedia(intro=intro)

    async def read(self, intro: Intro, start: int, end: int) -> bytes:
        """Byte `[start, end]` (gồm hai đầu). Raises: NotFoundError (object đã mất)."""
        data = await self._intros.read_range(intro, start, end)
        if data is None:
            raise intro_not_found()
        return data


__all__ = [
    "DeleteIntro",
    "IntroMedia",
    "IntroPatch",
    "IntroView",
    "ListIntros",
    "ReadIntro",
    "UpdateIntro",
    "UploadIntro",
    "intro_not_found",
]
