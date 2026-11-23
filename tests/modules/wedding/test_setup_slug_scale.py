"""Kiểm tra `SetupWedding` không bị kẹt trần 50 user khi slug gốc đã tồn tại."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.core.context import ActorContext
from app.modules.wedding.application.use_cases.setup_wedding import SetupMode, SetupWedding
from app.modules.wedding.domain.entities import Wedding, WeddingContent
from app.modules.wedding.domain.repositories import SlugTakenError
from app.modules.wedding.domain.services import slug_problem


class _FakeWeddingRepo:
    def __init__(self, taken: set[str]) -> None:
        self._taken = set(taken)

    async def find_by_tenant(self, tenant_id: UUID) -> Wedding | None:
        return None

    async def find_published_by_slug(self, slug: str) -> Wedding | None:
        return None

    async def slug_exists(self, slug: str) -> bool:
        return slug in self._taken

    async def create(
        self, *, tenant_id: UUID, content: WeddingContent, slug: str, actor_id: UUID | None
    ) -> Wedding:
        if slug in self._taken:
            raise SlugTakenError()
        self._taken.add(slug)
        return Wedding(id=uuid4(), tenant_id=tenant_id, content=content, slug=slug)

    async def save_content(
        self, tenant_id: UUID, content: WeddingContent, *, actor_id: UUID
    ) -> Wedding | None:
        return None

    async def save_checklist(
        self, tenant_id: UUID, checklist: dict[str, bool], *, actor_id: UUID
    ) -> Wedding | None:
        return None

    async def save_publication(
        self, tenant_id: UUID, *, slug: str, published: bool, actor_id: UUID
    ) -> Wedding | None:
        return None

    async def list_all(self) -> list[Wedding]:
        return []


class _NoopGuestSeeder:
    async def seed_sample(self, tenant_id: UUID, *, actor_id: UUID | None) -> int:
        return 0


async def test_setup_wedding_vuot_tran_50_nguoi_trung_slug_mau() -> None:
    taken = {"h-hoang-ha", *(f"h-hoang-ha-{i}" for i in range(2, 60))}
    use_case = SetupWedding(_FakeWeddingRepo(taken), _NoopGuestSeeder())
    actor = ActorContext(user_id=uuid4(), tenant_id=uuid4(), permissions=frozenset())

    wedding = await use_case.execute(actor, SetupMode.SAMPLE)

    assert wedding.slug.startswith("h-hoang-ha-")
    assert wedding.slug not in taken
    assert slug_problem(wedding.slug) is None
