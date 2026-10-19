"""Fragment URL mang cách hiển thị ảnh tới web thiệp: `#focus=x,y&zoom=…&f=…`.

Fragment không gửi lên máy chủ và không đụng chữ ký của URL. Chỉ ghi khoá khác mặc
định, `focus` luôn đứng đầu — web cũ chỉ đọc `#focus=x,y` vẫn đúng. Bộ đọc phía web:
`wedding-web/src/lib/invite/photo-focus.ts`.

| Khoá    | Trường            |
|---------|-------------------|
| `zoom`  | `zoom`            |
| `rot`   | `rotate`          |
| `flip`  | `flip` (`1`)      |
| `b` `c` `s` `w` | `brightness` `contrast` `saturation` `warmth` |
| `f` `fs` | `filter` `filter_strength` |
| `cap`   | `caption` (mã hoá phần trăm) |
"""

from __future__ import annotations

from urllib.parse import quote

from app.modules.media.domain.entities import Photo, PhotoAdjust

_TONES = (("b", "brightness"), ("c", "contrast"), ("s", "saturation"), ("w", "warmth"))


def photo_fragment(photo: Photo) -> str:
    """Phần sau `#` của URL ảnh."""
    adjust = photo.adjust
    default = PhotoAdjust()
    parts = [f"focus={photo.focus_x:g},{photo.focus_y:g}"]
    if adjust.zoom != default.zoom:
        parts.append(f"zoom={adjust.zoom:g}")
    if adjust.rotate:
        parts.append(f"rot={adjust.rotate}")
    if adjust.flip:
        parts.append("flip=1")
    parts.extend(f"{key}={getattr(adjust, name)}" for key, name in _TONES if getattr(adjust, name))
    if adjust.filter != default.filter:
        parts.append(f"f={adjust.filter}")
        if adjust.filter_strength != default.filter_strength:
            parts.append(f"fs={adjust.filter_strength}")
    if adjust.caption:
        # `safe=""`: mã hoá cả `'` `"` `&` `#` — URL được chèn thẳng vào thuộc tính HTML.
        parts.append(f"cap={quote(adjust.caption, safe='')}")
    return "&".join(parts)


__all__ = ["photo_fragment"]
