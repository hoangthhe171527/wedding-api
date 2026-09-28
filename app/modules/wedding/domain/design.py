"""Thiệp tự thiết kế: tài liệu gồm các LỚP đặt tự do trên nền của một mẫu.

Web vẽ tài liệu này thành mặt trước thiệp (xem trước, web thiệp, PNG, PDF in).
Toạ độ và kích thước tính theo PHẦN TRĂM khung thiệp 5×7, cỡ chữ theo phần trăm
bề ngang (`cqw`) — nên thiệp co giãn đúng tỉ lệ ở mọi kích cỡ.

Chỉ lưu dữ liệu đã kiểm: số trong khoảng, màu `#RRGGBB` hoặc token màu của mẫu,
font trong danh sách, trường dữ liệu trong danh sách. Không có HTML hay CSS tự do.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

from app.modules.wedding.domain.enums import THEME_FONTS

LAYER_KINDS: Final[frozenset[str]] = frozenset({"text", "field", "image", "decor", "shape"})

#: Trường dữ liệu chèn được vào thiệp — web thay bằng giá trị thật của từng khách.
FIELD_KEYS: Final[frozenset[str]] = frozenset(
    {
        "couple",
        "groom",
        "bride",
        "guest",
        "eyebrow",
        "invite",
        "announce",
        "attend",
        "closing",
        "date",
        "date_long",
        "weekday",
        "day",
        "month",
        "year",
        "time",
        "lunar",
        "venue",
        "address",
        "groom_parents",
        "bride_parents",
        "monogram",
    }
)

DECOR_KEYS: Final[frozenset[str]] = frozenset(
    {
        "hy",
        "hy-seal",
        "heart",
        "rings",
        "divider",
        "divider-diamond",
        "cloud",
        "star",
        "lotus",
        "frame-line",
        "frame-double",
        "frame-deco",
        "arch",
    }
)

SHAPE_KINDS: Final[frozenset[str]] = frozenset({"rect", "ellipse", "line"})
FONT_ROLES: Final[frozenset[str]] = frozenset({"", "script", "display", "body"})
COLOR_TOKENS: Final[frozenset[str]] = frozenset(
    {"", "accent", "accent2", "ink", "muted", "deep", "paper", "line", "none"}
)
ALIGNS: Final[frozenset[str]] = frozenset({"left", "center", "right"})
FITS: Final[frozenset[str]] = frozenset({"cover", "contain"})

MAX_LAYERS: Final[int] = 60
MAX_TEXT: Final[int] = 500
MAX_PHOTO_INDEX: Final[int] = 11

_HEX_RE: Final = re.compile(r"^#[0-9a-fA-F]{6}$")
_ID_RE: Final = re.compile(r"^[A-Za-z0-9_-]{1,24}$")


@dataclass(frozen=True, slots=True)
class DesignLayer:
    """Một lớp. Trường nào không dùng cho loại lớp đó thì bỏ qua khi vẽ."""

    id: str
    kind: str
    x: float = 10.0
    y: float = 10.0
    w: float = 80.0
    h: float = 10.0
    rotate: float = 0.0
    opacity: float = 1.0
    hidden: bool = False
    locked: bool = False
    text: str = ""
    field: str = ""
    font: str = ""
    size: float = 4.0
    color: str = ""
    align: str = "center"
    weight: int = 400
    italic: bool = False
    upper: bool = False
    spacing: float = 0.0
    line: float = 1.2
    foil: bool = False
    photo: int = 0
    fit: str = "cover"
    radius: float = 0.0
    decor: str = ""
    shape: str = "rect"
    fill: str = ""
    stroke: str = ""
    stroke_w: float = 0.0


@dataclass(frozen=True, slots=True)
class CardDesign:
    """Bật thì MỌI thiệp của đám cưới dùng thiết kế này thay cho bố cục của mẫu.

    `base` là mẫu lấy NỀN (màu nước, giấy, nhũ) và bảng màu; rỗng = mẫu mặc định.
    """

    enabled: bool = False
    base: str = ""
    layers: tuple[DesignLayer, ...] = field(default_factory=tuple)


def _color_ok(value: str) -> bool:
    return value in COLOR_TOKENS or bool(_HEX_RE.match(value))


def validate_design(design: CardDesign, *, known_templates: frozenset[str]) -> dict[str, list[str]]:
    """Lỗi theo đường dẫn trường; rỗng là hợp lệ."""
    errors: dict[str, list[str]] = {}

    def add(path: str, message: str) -> None:
        errors.setdefault(path, []).append(message)

    if design.base and design.base not in known_templates:
        add("card_design.base", "Mẫu nền không tồn tại.")
    if len(design.layers) > MAX_LAYERS:
        add("card_design.layers", f"Tối đa {MAX_LAYERS} lớp.")
    seen: set[str] = set()
    for index, layer in enumerate(design.layers):
        base = f"card_design.layers.{index}"
        if not _ID_RE.match(layer.id) or layer.id in seen:
            add(f"{base}.id", "Mã lớp không hợp lệ hoặc bị trùng.")
        seen.add(layer.id)
        if layer.kind not in LAYER_KINDS:
            add(f"{base}.kind", "Loại lớp không tồn tại.")
        if not (-50 <= layer.x <= 150 and -50 <= layer.y <= 150):
            add(f"{base}.x", "Vị trí nằm quá xa khung thiệp.")
        if not (0.5 <= layer.w <= 200 and 0.5 <= layer.h <= 200):
            add(f"{base}.w", "Kích thước lớp không hợp lệ.")
        if not -360 <= layer.rotate <= 360:
            add(f"{base}.rotate", "Góc xoay từ -360 đến 360 độ.")
        if not 0 <= layer.opacity <= 1:
            add(f"{base}.opacity", "Độ trong từ 0 đến 1.")
        if len(layer.text) > MAX_TEXT:
            add(f"{base}.text", f"Tối đa {MAX_TEXT} ký tự.")
        if layer.kind == "field" and layer.field not in FIELD_KEYS:
            add(f"{base}.field", "Trường dữ liệu không tồn tại.")
        if layer.font not in FONT_ROLES and layer.font not in THEME_FONTS:
            add(f"{base}.font", "Font không có trong danh sách.")
        if not 0.5 <= layer.size <= 60:
            add(f"{base}.size", "Cỡ chữ từ 0,5 đến 60.")
        for name in ("color", "fill", "stroke"):
            if not _color_ok(getattr(layer, name)):
                add(f"{base}.{name}", "Màu phải là #RRGGBB hoặc màu của mẫu.")
        if layer.align not in ALIGNS:
            add(f"{base}.align", "Căn lề không hợp lệ.")
        if not 100 <= layer.weight <= 900:
            add(f"{base}.weight", "Độ đậm từ 100 đến 900.")
        if not (-0.2 <= layer.spacing <= 1.5 and 0.6 <= layer.line <= 3):
            add(f"{base}.spacing", "Giãn chữ hoặc giãn dòng không hợp lệ.")
        if not 0 <= layer.photo <= MAX_PHOTO_INDEX:
            add(f"{base}.photo", "Ảnh không tồn tại.")
        if layer.fit not in FITS:
            add(f"{base}.fit", "Cách lấp ảnh không hợp lệ.")
        if not 0 <= layer.radius <= 50:
            add(f"{base}.radius", "Bo góc từ 0 đến 50%.")
        if layer.kind == "decor" and layer.decor not in DECOR_KEYS:
            add(f"{base}.decor", "Hoạ tiết không tồn tại.")
        if layer.shape not in SHAPE_KINDS:
            add(f"{base}.shape", "Hình không tồn tại.")
        if not 0 <= layer.stroke_w <= 10:
            add(f"{base}.stroke_w", "Độ dày viền từ 0 đến 10.")
    return errors


__all__ = [
    "DECOR_KEYS",
    "FIELD_KEYS",
    "LAYER_KINDS",
    "MAX_LAYERS",
    "CardDesign",
    "DesignLayer",
    "validate_design",
]
