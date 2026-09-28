"""Cầu nối: xưởng thiệp có tồn tại không — cho `billing` kiểm trước khi cấp gói."""

from __future__ import annotations

from uuid import UUID

from app.modules.identity.infrastructure.persistence.repositories import BeanieStudioRepository


class StudioDirectory:
    def __init__(self) -> None:
        self._studios = BeanieStudioRepository()

    async def exists(self, studio_id: UUID) -> bool:
        return await self._studios.find_by_id(studio_id) is not None


def build_studio_directory() -> StudioDirectory:
    return StudioDirectory()


__all__ = ["StudioDirectory", "build_studio_directory"]
