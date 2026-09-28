"""Enum của `identity`."""

from __future__ import annotations

from enum import StrEnum


class IdentifierKind(StrEnum):
    """Loại định danh đăng nhập.

    `POST /auth/login` nhận MỘT ô `identifier` là email hoặc số điện thoại —
    cặp đôi quen đăng nhập bằng số điện thoại, đội vận hành bằng email.
    """

    EMAIL = "email"
    PHONE = "phone"


__all__ = ["IdentifierKind"]
