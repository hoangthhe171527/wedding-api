"""Hàm thuần của `access`."""

from __future__ import annotations

from collections.abc import Iterable

from app.core.permissions import normalize
from app.modules.access.domain.entities import Role


def merge_permissions(roles: Iterable[Role]) -> frozenset[str]:
    """Hợp tập quyền của nhiều vai trò, lọc qua catalog.

    Slug lạ nằm trong DB (catalog đã bỏ quyền đó) không cấp được gì — cùng luật
    với `perms` trong token.
    """
    merged: set[str] = set()
    for role in roles:
        merged.update(role.permissions)
    return normalize(list(merged))


__all__ = ["merge_permissions"]
