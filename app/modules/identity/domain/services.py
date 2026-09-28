"""Hàm thuần của `identity`: chuẩn hoá định danh, chính sách mật khẩu."""

from __future__ import annotations

import re
from typing import Final

from app.modules.identity.domain.enums import IdentifierKind
from app.modules.identity.domain.errors import (
    InvalidEmailError,
    InvalidIdentifierError,
    InvalidPhoneError,
    WeakPasswordError,
)

_EMAIL_RE: Final = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
#: Số di động Việt Nam sau chuẩn hoá: 0 + 9 chữ số (03x, 05x, 07x, 08x, 09x).
_PHONE_RE: Final = re.compile(r"^0[35789]\d{8}$")

MIN_PASSWORD_LENGTH: Final[int] = 8


def normalize_email(raw: str) -> str:
    """Email viết thường, bỏ khoảng trắng hai đầu.

    Raises:
        InvalidEmailError: sai định dạng.
    """
    value = raw.strip().lower()
    if not _EMAIL_RE.match(value) or len(value) > 190:
        raise InvalidEmailError
    return value


def normalize_phone(raw: str) -> str:
    """Số điện thoại về dạng `0xxxxxxxxx`: bỏ khoảng trắng, dấu chấm, gạch; `+84` -> `0`.

    Thiết kế in số theo nhóm (`0912 345 678`), người dùng gõ đủ kiểu — lưu một
    dạng duy nhất thì ràng buộc duy nhất mới có nghĩa.

    Raises:
        InvalidPhoneError: sai định dạng.
    """
    digits = re.sub(r"[\s.\-()]", "", raw.strip())
    if digits.startswith("+84"):
        digits = "0" + digits[3:]
    elif digits.startswith("84") and len(digits) == 11:
        digits = "0" + digits[2:]
    if not _PHONE_RE.match(digits):
        raise InvalidPhoneError
    return digits


def normalize_identifier(raw: str) -> tuple[IdentifierKind, str]:
    """Nhận diện và chuẩn hoá một ô `identifier` (email hoặc số điện thoại).

    Raises:
        InvalidIdentifierError: không phải email, cũng không phải số điện thoại.
    """
    value = raw.strip()
    try:
        if "@" in value:
            return IdentifierKind.EMAIL, normalize_email(value)
        return IdentifierKind.PHONE, normalize_phone(value)
    except (InvalidEmailError, InvalidPhoneError):
        raise InvalidIdentifierError from None


def check_password_policy(password: str, *, field: str = "password") -> None:
    """Tối thiểu 8 ký tự, có cả chữ và số.

    Raises:
        WeakPasswordError: không đạt.
    """
    has_letter = any(char.isalpha() for char in password)
    has_digit = any(char.isdigit() for char in password)
    if len(password) < MIN_PASSWORD_LENGTH or not has_letter or not has_digit:
        raise WeakPasswordError(field=field)


def studio_name_for(full_name: str) -> str:
    """Tên mặc định của xưởng khi khách tự đăng ký."""
    return f"Xưởng thiệp của {full_name.strip()}"


__all__ = [
    "MIN_PASSWORD_LENGTH",
    "check_password_policy",
    "normalize_email",
    "normalize_identifier",
    "normalize_phone",
    "studio_name_for",
]
