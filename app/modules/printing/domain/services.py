"""Luật thuần của `printing`."""

from __future__ import annotations

import re

from app.modules.printing.domain.entities import PrintSpec
from app.modules.printing.domain.enums import MAX_QUANTITY, MIN_QUANTITY, PAPERS, SIZES

_PHONE = re.compile(r"^(\+?84|0)\d{9,10}$")


def normalize_phone(value: str) -> str:
    return re.sub(r"[\s.\-()]", "", value)


def spec_errors(spec: PrintSpec) -> dict[str, list[str]]:
    """Lỗi theo trường — rỗng là hợp lệ."""
    errors: dict[str, list[str]] = {}

    def add(field: str, message: str) -> None:
        errors.setdefault(field, []).append(message)

    if not MIN_QUANTITY <= spec.quantity <= MAX_QUANTITY:
        add("quantity", f"Số lượng từ {MIN_QUANTITY} đến {MAX_QUANTITY} thiệp.")
    if spec.paper not in PAPERS:
        add("paper", "Chất giấy không có trong danh sách.")
    if spec.size not in SIZES:
        add("size", "Khổ thiệp không có trong danh sách.")
    if not spec.contact_name.strip():
        add("contact_name", "Cho chúng tôi biết tên người nhận.")
    if not _PHONE.match(normalize_phone(spec.contact_phone)):
        add("contact_phone", "Số điện thoại chưa đúng (VD: 0912 345 678).")
    if len(spec.address.strip()) < 8:
        add("address", "Ghi rõ địa chỉ nhận thiệp.")
    return errors
