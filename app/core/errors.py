"""Cây lỗi ứng dụng và bộ xử lý ngoại lệ HTTP.

Envelope lỗi (ARCHITECTURE §1.6) — FE đọc `message`::

    {"message": "<tiếng Việt>", "code": "<snake_case>", "errors": {"field": ["..."]}?}

Use case ném `AppError`; router KHÔNG bắt lại, handler đăng ký ở `app.main` lo
chuyển thành HTTP. Không bao giờ ném `HTTPException` trong tầng nghiệp vụ.
"""

from __future__ import annotations

from typing import Any, Final

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = structlog.get_logger(__name__)

FieldErrors = dict[str, list[str]]


class AppError(Exception):
    """Gốc của mọi lỗi nghiệp vụ.

    Attributes:
        message: Câu tiếng Việt hiển thị thẳng cho người dùng.
        code: Mã snake_case để client phân nhánh xử lý.
        status_code: Mã HTTP tương ứng.
        errors: Lỗi theo từng trường, tuỳ chọn.
    """

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "bad_request"
    message: str = "Yêu cầu không hợp lệ."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        errors: FieldErrors | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or type(self).message
        self.code = code or type(self).code
        self.errors = errors
        self.context = context or {}
        super().__init__(self.message)


class ValidationError(AppError):
    """Dữ liệu vào sai theo quy tắc nghiệp vụ (sai kiểu thì là 422)."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "validation_error"
    message = "Dữ liệu gửi lên không hợp lệ."


class UnauthorizedError(AppError):
    """Chưa đăng nhập hoặc token hỏng/hết hạn."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"
    message = "Phiên đăng nhập không hợp lệ hoặc đã hết hạn."


class ForbiddenError(AppError):
    """Đã đăng nhập nhưng thiếu quyền."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"
    message = "Bạn không có quyền thực hiện thao tác này."


class NotFoundError(AppError):
    """Không tìm thấy tài nguyên."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "Không tìm thấy dữ liệu."


class OutOfScopeError(NotFoundError):
    """Tài nguyên có tồn tại nhưng thuộc xưởng khác.

    ARCHITECTURE §1.5: trả **404**, không phải 403 — không tiết lộ sự tồn tại.
    Lớp riêng để log nội bộ phân biệt được, còn client thấy y hệt `NotFoundError`.
    """


class ConflictError(AppError):
    """Xung đột trạng thái: trùng khoá tự nhiên, vượt số lượng cho phép..."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
    message = "Thao tác xung đột với trạng thái hiện tại của dữ liệu."


class RateLimitedError(AppError):
    """Gọi quá tần suất cho phép."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"
    message = "Bạn thao tác quá nhanh. Vui lòng thử lại sau ít phút."


class ServiceUnavailableError(AppError):
    """Phụ thuộc ngoài không dùng được."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "service_unavailable"
    message = "Dịch vụ tạm thời không sẵn sàng. Vui lòng thử lại."


# --- Ánh xạ mã HTTP mặc định -> câu tiếng Việt ------------------------------
_HTTP_MESSAGES: Final[dict[int, tuple[str, str]]] = {
    status.HTTP_400_BAD_REQUEST: ("bad_request", "Yêu cầu không hợp lệ."),
    status.HTTP_401_UNAUTHORIZED: ("unauthorized", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn."),
    status.HTTP_403_FORBIDDEN: ("forbidden", "Bạn không có quyền thực hiện thao tác này."),
    status.HTTP_404_NOT_FOUND: ("not_found", "Không tìm thấy dữ liệu."),
    status.HTTP_405_METHOD_NOT_ALLOWED: ("method_not_allowed", "Phương thức không được hỗ trợ."),
    status.HTTP_409_CONFLICT: ("conflict", "Thao tác xung đột với trạng thái hiện tại."),
    status.HTTP_413_CONTENT_TOO_LARGE: ("payload_too_large", "Tệp tải lên quá lớn."),
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: (
        "unsupported_media_type",
        "Định dạng tệp không được hỗ trợ.",
    ),
    status.HTTP_429_TOO_MANY_REQUESTS: (
        "rate_limited",
        "Bạn thao tác quá nhanh. Vui lòng thử lại sau ít phút.",
    ),
    status.HTTP_500_INTERNAL_SERVER_ERROR: (
        "internal_error",
        "Hệ thống gặp sự cố. Vui lòng thử lại sau.",
    ),
}

# --- Câu tiếng Việt cho lỗi validate của Pydantic ---------------------------
_VALIDATION_MESSAGES: Final[dict[str, str]] = {
    "missing": "Trường này là bắt buộc.",
    "string_type": "Giá trị phải là chuỗi ký tự.",
    "string_too_short": "Giá trị quá ngắn.",
    "string_too_long": "Giá trị quá dài.",
    "string_pattern_mismatch": "Giá trị không đúng định dạng.",
    "int_type": "Giá trị phải là số nguyên.",
    "int_parsing": "Giá trị phải là số nguyên.",
    "bool_type": "Giá trị phải là đúng/sai.",
    "bool_parsing": "Giá trị phải là đúng/sai.",
    "uuid_parsing": "Mã định danh không đúng định dạng UUID.",
    "uuid_type": "Mã định danh không đúng định dạng UUID.",
    "date_parsing": "Ngày không đúng định dạng yyyy-mm-dd.",
    "date_from_datetime_parsing": "Ngày không đúng định dạng yyyy-mm-dd.",
    "enum": "Giá trị không nằm trong danh sách cho phép.",
    "literal_error": "Giá trị không nằm trong danh sách cho phép.",
    "greater_than": "Giá trị phải lớn hơn mức cho phép.",
    "greater_than_equal": "Giá trị phải lớn hơn hoặc bằng mức cho phép.",
    "less_than": "Giá trị phải nhỏ hơn mức cho phép.",
    "less_than_equal": "Giá trị phải nhỏ hơn hoặc bằng mức cho phép.",
    "too_short": "Danh sách có quá ít phần tử.",
    "too_long": "Danh sách có quá nhiều phần tử.",
    "list_type": "Giá trị phải là danh sách.",
    "dict_type": "Giá trị phải là đối tượng.",
    "model_attributes_type": "Giá trị phải là đối tượng.",
    "json_invalid": "Nội dung JSON không hợp lệ.",
    "value_error": "Giá trị không hợp lệ.",
}


def _field_path(location: tuple[Any, ...]) -> str:
    """Rút gọn `loc` của Pydantic thành đường dẫn trường đọc được."""
    parts = [str(item) for item in location if item not in {"body", "query", "path", "header"}]
    return ".".join(parts) if parts else "body"


def _vietnamese_validation_message(detail: dict[str, Any]) -> str:
    """Chuyển một mục lỗi Pydantic sang câu tiếng Việt."""
    error_type = str(detail.get("type", ""))
    if error_type in _VALIDATION_MESSAGES and error_type != "value_error":
        return _VALIDATION_MESSAGES[error_type]
    # `value_error` do `raise ValueError("...")` trong validator: giữ câu gốc.
    raw = str(detail.get("msg", "")).removeprefix("Value error, ").strip()
    return raw or "Giá trị không hợp lệ."


def error_response(
    *,
    status_code: int,
    message: str,
    code: str,
    errors: FieldErrors | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Dựng JSONResponse đúng envelope lỗi."""
    payload: dict[str, Any] = {"message": message, "code": code}
    if errors:
        payload["errors"] = errors
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """`AppError` -> envelope lỗi, giữ nguyên mã HTTP của lớp lỗi."""
    assert isinstance(exc, AppError)
    log.info(
        "app_error",
        code=exc.code,
        status_code=exc.status_code,
        error_class=type(exc).__name__,
        path=request.url.path,
        **exc.context,
    )
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    retry_after = exc.context.get("retry_after")
    if exc.status_code == 429 and retry_after:
        headers = {"Retry-After": str(retry_after)}
    return error_response(
        status_code=exc.status_code,
        message=exc.message,
        code=exc.code,
        errors=exc.errors,
        headers=headers,
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """`RequestValidationError` -> 422 với message tiếng Việt theo từng trường."""
    assert isinstance(exc, RequestValidationError)
    errors: FieldErrors = {}
    for detail in exc.errors():
        field = _field_path(tuple(detail.get("loc", ())))
        errors.setdefault(field, []).append(_vietnamese_validation_message(dict(detail)))

    log.info("validation_error", path=request.url.path, fields=sorted(errors))
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        message="Dữ liệu gửi lên chưa hợp lệ. Vui lòng kiểm tra lại các trường được đánh dấu.",
        code="validation_error",
        errors=errors,
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """`HTTPException` của Starlette -> envelope lỗi, câu chữ tiếng Việt."""
    assert isinstance(exc, StarletteHTTPException)
    code, default_message = _HTTP_MESSAGES.get(
        exc.status_code, ("http_error", "Yêu cầu không thực hiện được.")
    )
    message = exc.detail if isinstance(exc.detail, str) and exc.detail else default_message
    # Starlette đặt detail mặc định bằng tiếng Anh; thay bằng câu tiếng Việt.
    if message in {"Not Found", "Method Not Allowed", "Forbidden", "Unauthorized"}:
        message = default_message
    headers = dict(exc.headers) if exc.headers else None
    return error_response(status_code=exc.status_code, message=message, code=code, headers=headers)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Lỗi không lường trước -> 500, log đầy đủ, không lộ chi tiết ra ngoài."""
    log.exception(
        "unhandled_error",
        path=request.url.path,
        method=request.method,
        error_class=type(exc).__name__,
    )
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Hệ thống gặp sự cố. Vui lòng thử lại sau.",
        code="internal_error",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Gắn toàn bộ handler vào ứng dụng. Gọi một lần trong `create_app()`."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)


__all__ = [
    "AppError",
    "ConflictError",
    "FieldErrors",
    "ForbiddenError",
    "NotFoundError",
    "OutOfScopeError",
    "RateLimitedError",
    "ServiceUnavailableError",
    "UnauthorizedError",
    "ValidationError",
    "error_response",
    "register_exception_handlers",
]
