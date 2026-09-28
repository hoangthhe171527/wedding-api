"""Lỗi thuần của tầng domain `identity`.

Domain không biết HTTP, nên các lỗi ở đây KHÔNG kế thừa `AppError`. Use case bắt
chúng rồi ném lại lỗi tương ứng của `app.core.errors` (ARCHITECTURE §0.2).
"""

from __future__ import annotations


class IdentityDomainError(Exception):
    """Gốc của mọi lỗi nghiệp vụ thuần trong `identity`.

    Attributes:
        message: Câu tiếng Việt hiển thị được cho người dùng.
        field: Tên trường gây lỗi, để use case dựng `errors` theo từng trường.
    """

    message: str = "Dữ liệu định danh không hợp lệ."
    field: str | None = None

    def __init__(self, message: str | None = None, *, field: str | None = None) -> None:
        self.message = message or type(self).message
        self.field = field or type(self).field
        super().__init__(self.message)


class InvalidIdentifierError(IdentityDomainError):
    """Chuỗi định danh không phải email cũng không phải số điện thoại hợp lệ."""

    message = "Email hoặc số điện thoại không đúng định dạng."
    field = "identifier"


class InvalidEmailError(IdentityDomainError):
    """Email sai định dạng."""

    message = "Email không đúng định dạng."
    field = "email"


class InvalidPhoneError(IdentityDomainError):
    """Số điện thoại sai định dạng."""

    message = "Số điện thoại không đúng định dạng (ví dụ 0912 345 678)."
    field = "phone"


class WeakPasswordError(IdentityDomainError):
    """Mật khẩu không đạt chính sách tối thiểu."""

    message = "Mật khẩu phải dài tối thiểu 8 ký tự, gồm cả chữ và số."
    field = "password"


class DuplicateIdentifierError(IdentityDomainError):
    """Email/số điện thoại đã thuộc một tài khoản khác (index duy nhất từ chối)."""

    message = "Email hoặc số điện thoại này đã có tài khoản. Hãy đăng nhập."
    field = "email"


class SamePasswordError(IdentityDomainError):
    """Mật khẩu mới trùng mật khẩu hiện tại."""

    message = "Mật khẩu mới phải khác mật khẩu hiện tại."
    field = "new_password"


__all__ = [
    "DuplicateIdentifierError",
    "IdentityDomainError",
    "InvalidEmailError",
    "InvalidIdentifierError",
    "InvalidPhoneError",
    "SamePasswordError",
    "WeakPasswordError",
]
