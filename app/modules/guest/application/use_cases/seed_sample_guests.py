"""Use case: nạp danh sách khách mẫu vào một xưởng ("Lưu dữ liệu mẫu").

Khớp cổng `wedding.application.ports.GuestSeeder`. Chỉ nạp khi xưởng CHƯA có khách
nào — chạy lại không nhân đôi.

Mã khách ngẫu nhiên như khách thật: cặp đôi hay sửa dòng mẫu thành khách thật, và mã
mẫu cố định (công khai trong mã nguồn) sẽ cho người lạ mở link riêng của khách đó.
Chỉ tài khoản demo của seed dùng mã cố định (`fixed_codes=True`) — để thiệp demo có
link ổn định trong tài liệu.
"""

from __future__ import annotations

from uuid import UUID

from app.modules.guest.application.support import create_with_code
from app.modules.guest.domain.repositories import GuestRepository
from app.modules.guest.domain.samples import SAMPLE_GUESTS


class SeedSampleGuests:
    """Tạo khách mẫu cho xưởng chưa có khách; trả số khách vừa tạo."""

    def __init__(self, guests: GuestRepository, *, fixed_codes: bool = False) -> None:
        self._guests = guests
        self._fixed_codes = fixed_codes

    async def seed_sample(self, tenant_id: UUID, *, actor_id: UUID | None) -> int:
        if await self._guests.count(tenant_id) > 0:
            return 0
        for code, draft in SAMPLE_GUESTS:
            await create_with_code(
                self._guests,
                tenant_id,
                draft,
                actor_id=actor_id,
                code=code if self._fixed_codes else None,
            )
        return len(SAMPLE_GUESTS)


__all__ = ["SeedSampleGuests"]
