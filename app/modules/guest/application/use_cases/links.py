"""Use case: link theo đối tượng — MỘT link cho cả một nhóm người, mẫu thiệp riêng.

Cặp đôi dán link vào nhóm Zalo công ty, nhóm lớp... mà không phải nhập từng
khách. Mỗi link một đuôi (`/invite/<slug thiệp>/<đuôi>`) và một mẫu.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.context import ActorContext
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.modules.guest.application.ports import TemplateCatalog
from app.modules.guest.domain.entities import InviteLink
from app.modules.guest.domain.enums import MAX_LINKS_PER_STUDIO
from app.modules.guest.domain.repositories import InviteLinkRepository, LinkSlugTakenError
from app.modules.guest.domain.services import LINK_SLUG_MAX, link_slug_from, validate_link

log = get_logger(__name__)

#: Đuôi tự sinh trùng thì thêm `-2`, `-3`... — vài lượt là đủ, có trần để không lặp mãi.
_SLUG_ATTEMPTS = 20


@dataclass(frozen=True, slots=True)
class LinkInput:
    """Nội dung form link. `slug` rỗng = tự sinh từ tên."""

    name: str
    slug: str = ""
    template: str = ""


def link_not_found() -> NotFoundError:
    return NotFoundError("Không tìm thấy link.", code="link_not_found")


def _slug_taken(slug: str) -> ConflictError:
    return ConflictError(
        f"Đuôi link “{slug}” đã dùng cho link khác.",
        code="link_slug_taken",
        errors={"slug": ["Đuôi link đã dùng cho link khác."]},
    )


def _ensure_valid(data: LinkInput, slug: str, known: frozenset[str]) -> None:
    errors = validate_link(name=data.name, slug=slug, template=data.template, known_templates=known)
    if errors:
        first = next(iter(errors.values()))[0]
        raise ValidationError(first, errors=errors)


def _numbered(base: str, attempt: int) -> str:
    if attempt == 0:
        return base
    suffix = f"-{attempt + 1}"
    return base[: LINK_SLUG_MAX - len(suffix)].rstrip("-") + suffix


class ListLinks:
    def __init__(self, links: InviteLinkRepository) -> None:
        self._links = links

    async def execute(self, actor: ActorContext) -> list[InviteLink]:
        return await self._links.list_all(actor.tenant_id)


class CreateLink:
    def __init__(self, links: InviteLinkRepository, templates: TemplateCatalog) -> None:
        self._links = links
        self._templates = templates

    async def execute(self, actor: ActorContext, data: LinkInput) -> InviteLink:
        """Raises: ValidationError, ConflictError (trùng đuôi, quá số link)."""
        chosen = data.slug.strip().lower()
        base = chosen or link_slug_from(data.name)
        _ensure_valid(data, base, await self._templates.known_keys())
        if await self._links.count(actor.tenant_id) >= MAX_LINKS_PER_STUDIO:
            raise ConflictError(
                f"Mỗi thiệp tối đa {MAX_LINKS_PER_STUDIO} link theo đối tượng.",
                code="link_limit",
            )
        # Đuôi người dùng tự đặt mà trùng thì báo; đuôi tự sinh thì đánh số tiếp.
        attempts = 1 if chosen else _SLUG_ATTEMPTS
        for attempt in range(attempts):
            slug = _numbered(base, attempt)
            try:
                link = await self._links.create(
                    actor.tenant_id,
                    slug=slug,
                    name=data.name,
                    template=data.template,
                    actor_id=actor.user_id,
                )
            except LinkSlugTakenError:
                continue
            log.info("guest_link_created", tenant_id=str(actor.tenant_id), slug=slug)
            return link
        raise _slug_taken(base)


class UpdateLink:
    def __init__(self, links: InviteLinkRepository, templates: TemplateCatalog) -> None:
        self._links = links
        self._templates = templates

    async def execute(self, actor: ActorContext, link_id: UUID, data: LinkInput) -> InviteLink:
        """Raises: NotFoundError, ValidationError, ConflictError (trùng đuôi).

        Đổi đuôi là link cũ đã gửi thôi nhận diện — giao diện phải cảnh báo trước.
        """
        current = await self._links.get(actor.tenant_id, link_id)
        if current is None:
            raise link_not_found()
        slug = data.slug.strip().lower() or current.slug
        _ensure_valid(data, slug, await self._templates.known_keys())
        try:
            saved = await self._links.update(
                actor.tenant_id,
                link_id,
                slug=slug,
                name=data.name,
                template=data.template,
                actor_id=actor.user_id,
            )
        except LinkSlugTakenError as exc:
            raise _slug_taken(slug) from exc
        if saved is None:
            raise link_not_found()
        return saved


class DeleteLink:
    def __init__(self, links: InviteLinkRepository) -> None:
        self._links = links

    async def execute(self, actor: ActorContext, link_id: UUID) -> None:
        """Raises: NotFoundError. Link đã gửi mở ra như link chung từ đây."""
        if not await self._links.soft_delete(actor.tenant_id, link_id, actor_id=actor.user_id):
            raise link_not_found()
        log.info("guest_link_deleted", tenant_id=str(actor.tenant_id), link_id=str(link_id))


__all__ = ["CreateLink", "DeleteLink", "LinkInput", "ListLinks", "UpdateLink", "link_not_found"]
