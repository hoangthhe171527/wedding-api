"""Bộ vai trò mặc định — **dữ liệu khởi tạo**, không phải logic nghiệp vụ.

Hai vai trò theo yêu cầu sản phẩm:

* `admin` — đội vận hành: TOÀN QUYỀN — quản lý bộ mẫu, mặc định hệ thống, tài
  khoản, giám sát mọi xưởng, và có xưởng riêng để soạn / thiết kế thử như khách.
* `customer` — "khách dùng mẫu": cặp đôi tự soạn thiệp trong xưởng của mình.

Không code nghiệp vụ nào được `if role.slug == "admin"`. Kiểm tra quyền luôn
bằng slug quyền (ARCHITECTURE §0.1). Hai hằng slug dưới đây chỉ dùng ở đường
CẤP vai trò (đăng ký, seed) — nơi phải gọi tên một vai trò cụ thể để gán.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.core.permissions import Permission


@dataclass(frozen=True, slots=True)
class RoleBlueprint:
    """Khuôn để tạo một vai trò mặc định."""

    slug: str
    label: str
    permissions: tuple[str, ...]


ADMIN_ROLE_SLUG: Final[str] = "admin"
CUSTOMER_ROLE_SLUG: Final[str] = "customer"

DEFAULT_ROLES: Final[tuple[RoleBlueprint, ...]] = (
    RoleBlueprint(
        slug=ADMIN_ROLE_SLUG,
        label="Quản trị viên",
        # Toàn quyền: mọi slug trong danh mục.
        permissions=tuple(item.value for item in Permission),
    ),
    RoleBlueprint(
        slug=CUSTOMER_ROLE_SLUG,
        label="Khách dùng mẫu",
        permissions=(
            Permission.STUDIO_MANAGE.value,
            Permission.GUEST_MANAGE.value,
            Permission.TEMPLATE_VIEW.value,
        ),
    ),
)

_BY_SLUG: Final[dict[str, RoleBlueprint]] = {item.slug: item for item in DEFAULT_ROLES}


def blueprint_of(slug: str) -> RoleBlueprint | None:
    """Khuôn vai trò mặc định theo slug, hoặc None nếu không có."""
    return _BY_SLUG.get(slug)


__all__ = [
    "ADMIN_ROLE_SLUG",
    "CUSTOMER_ROLE_SLUG",
    "DEFAULT_ROLES",
    "RoleBlueprint",
    "blueprint_of",
]
