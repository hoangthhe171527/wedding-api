"""Cầu nối cho seed: đám cưới mẫu đã xuất bản cho tài khoản demo (idempotent).

Đi qua đúng hai use case người dùng thật đi qua ("Lưu dữ liệu mẫu" rồi "Xuất
bản") — seed không có lối tắt ghi thẳng vào collection.
"""

from __future__ import annotations

from app.core.context import ActorContext
from app.modules.billing import build_plan_gate
from app.modules.guest import build_guest_seeder, build_guest_usage_reader
from app.modules.wedding.application.use_cases import SetPublication, SetupMode, SetupWedding
from app.modules.wedding.infrastructure.persistence.repositories import BeanieWeddingRepository


class DemoWeddingSeeder:
    """Bảo đảm xưởng demo có đám cưới mẫu + khách mẫu, đã xuất bản tại `slug`."""

    def __init__(self) -> None:
        self._weddings = BeanieWeddingRepository()

    async def ensure(self, actor: ActorContext, *, slug: str) -> bool:
        """Trả True nếu vừa tạo mới."""
        if await self._weddings.find_by_tenant(actor.tenant_id) is not None:
            return False
        await SetupWedding(self._weddings, build_guest_seeder(fixed_codes=True)).execute(
            actor, SetupMode.SAMPLE
        )
        await SetPublication(self._weddings, build_guest_usage_reader(), build_plan_gate()).execute(
            actor, slug=slug, published=True
        )
        return True


def build_demo_wedding_seeder() -> DemoWeddingSeeder:
    """Hàm dựng công bố trên barrel `app.modules.wedding`."""
    return DemoWeddingSeeder()


__all__ = ["DemoWeddingSeeder", "build_demo_wedding_seeder"]
