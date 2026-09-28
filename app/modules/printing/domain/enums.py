"""Danh mục của `printing`: chất giấy, khổ thiệp, trạng thái yêu cầu."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class PrintStatus(StrEnum):
    """Vòng đời một yêu cầu in. Đội vận hành chuyển tay sau khi gọi / nhắn Zalo."""

    NEW = "new"
    CONTACTED = "contacted"
    PRINTING = "printing"
    SHIPPED = "shipped"
    DONE = "done"
    CANCELLED = "cancelled"


PRINT_STATUS_LABELS: Final[dict[PrintStatus, str]] = {
    PrintStatus.NEW: "Mới gửi",
    PrintStatus.CONTACTED: "Đã liên hệ",
    PrintStatus.PRINTING: "Đang in",
    PrintStatus.SHIPPED: "Đang giao",
    PrintStatus.DONE: "Hoàn tất",
    PrintStatus.CANCELLED: "Đã huỷ",
}

#: Chất giấy nhận in. Khoá trùng web (`PAPERS` ở module printing phía web).
PAPERS: Final[dict[str, str]] = {
    "my-thuat": "Giấy mỹ thuật 300gsm",
    "kraft": "Giấy kraft mộc",
    "nhung": "Giấy nhung ép nổi",
    "ngoc-trai": "Giấy ánh ngọc trai",
}

SIZES: Final[dict[str, str]] = {
    "5x7": "5×7 inch (127×178 mm)",
    "4x6": "4×6 inch (102×152 mm)",
    "gap-doi": "Thiệp gập đôi 5×7",
}

#: Đang xử lý thì khách không huỷ tự do được nữa — phải nhắn Zalo.
CANCELLABLE: Final[frozenset[PrintStatus]] = frozenset({PrintStatus.NEW, PrintStatus.CONTACTED})

MIN_QUANTITY: Final[int] = 10
MAX_QUANTITY: Final[int] = 3000
