"""Catalog quyền — chốt cứng theo ARCHITECTURE §1.4.

Đúng sáu slug, trùng khớp tuyệt đối với `wedding-web/src/core/access/permissions.ts`.
Thêm quyền mới là quyết định kiến trúc: phải sửa cả hai phía cùng lúc.

Vai trò (`admin`, `customer`) là **dữ liệu** trong collection `roles` do module
`access` sở hữu — không bao giờ hard-code trong code nghiệp vụ. Code chỉ kiểm slug.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class PermissionGroup(StrEnum):
    """Nhóm gom quyền để hiển thị."""

    STUDIO = "studio"
    TEMPLATE = "template"
    SYSTEM = "system"


PERMISSION_GROUP_LABELS: Final[dict[PermissionGroup, str]] = {
    PermissionGroup.STUDIO: "Xưởng thiệp",
    PermissionGroup.TEMPLATE: "Mẫu thiệp",
    PermissionGroup.SYSTEM: "Quản trị hệ thống",
}


class Permission(StrEnum):
    """Sáu slug quyền. Dùng `Permission.GUEST_MANAGE` thay cho chuỗi trần."""

    STUDIO_MANAGE = "studio.manage"
    GUEST_MANAGE = "guest.manage"
    TEMPLATE_VIEW = "template.view"
    TEMPLATE_MANAGE = "template.manage"
    USER_MANAGE = "user.manage"
    STUDIO_OVERSEE = "studio.oversee"


@dataclass(frozen=True, slots=True)
class PermissionDefinition:
    """Một quyền cùng nhãn tiếng Việt để hiện cho người dùng."""

    slug: Permission
    label: str
    group: PermissionGroup
    description: str


PERMISSION_CATALOG: Final[tuple[PermissionDefinition, ...]] = (
    PermissionDefinition(
        slug=Permission.STUDIO_MANAGE,
        label="Soạn xưởng thiệp",
        group=PermissionGroup.STUDIO,
        description="Sửa thông tin cưới, ảnh, lộ trình chuẩn bị và xuất bản web thiệp.",
    ),
    PermissionDefinition(
        slug=Permission.GUEST_MANAGE,
        label="Quản lý khách mời",
        group=PermissionGroup.STUDIO,
        description="Thêm, sửa, nhập nhanh khách mời và theo dõi gửi thiệp, phản hồi.",
    ),
    PermissionDefinition(
        slug=Permission.TEMPLATE_VIEW,
        label="Xem bộ mẫu thiệp",
        group=PermissionGroup.TEMPLATE,
        description="Xem các mẫu thiệp đang mở cho khách dùng.",
    ),
    PermissionDefinition(
        slug=Permission.TEMPLATE_MANAGE,
        label="Quản lý bộ mẫu thiệp",
        group=PermissionGroup.TEMPLATE,
        description="Bật/tắt mẫu, gắn nhãn Mới, sắp thứ tự hiển thị.",
    ),
    PermissionDefinition(
        slug=Permission.USER_MANAGE,
        label="Quản lý tài khoản",
        group=PermissionGroup.SYSTEM,
        description="Xem mọi tài khoản, khoá hoặc mở khoá đăng nhập.",
    ),
    PermissionDefinition(
        slug=Permission.STUDIO_OVERSEE,
        label="Giám sát xưởng thiệp",
        group=PermissionGroup.SYSTEM,
        description="Xem danh sách xưởng thiệp của mọi khách cùng số liệu tổng quan.",
    ),
)

_BY_SLUG: Final[dict[str, PermissionDefinition]] = {
    item.slug.value: item for item in PERMISSION_CATALOG
}


def all_slugs() -> tuple[str, ...]:
    """Toàn bộ slug quyền theo đúng thứ tự catalog."""
    return tuple(_BY_SLUG)


def is_valid_slug(slug: str) -> bool:
    """Slug có nằm trong catalog hay không."""
    return slug in _BY_SLUG


def label_of(slug: str) -> str:
    """Nhãn tiếng Việt của một slug; trả lại chính slug nếu không có trong catalog."""
    found = _BY_SLUG.get(slug)
    return found.label if found else slug


def normalize(slugs: object) -> frozenset[str]:
    """Lọc danh sách slug bất kỳ về đúng tập slug hợp lệ.

    Dùng khi đọc `perms` từ JWT hoặc DB: token cũ có thể chứa slug đã bỏ.
    """
    if not isinstance(slugs, list | tuple | set | frozenset):
        return frozenset()
    return frozenset(str(item) for item in slugs if isinstance(item, str) and item in _BY_SLUG)


__all__ = [
    "PERMISSION_CATALOG",
    "PERMISSION_GROUP_LABELS",
    "Permission",
    "PermissionDefinition",
    "PermissionGroup",
    "all_slugs",
    "is_valid_slug",
    "label_of",
    "normalize",
]
