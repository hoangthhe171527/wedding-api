"""Danh mục mẫu khởi tạo — chép nguyên thứ tự và thuộc tính `TEMPLATES` của thiết kế.

Đây là **dữ liệu khởi tạo**: seed tạo mẫu còn thiếu, không đè trạng thái mà đội
vận hành đã chỉnh (bật/tắt, nhãn Mới, thứ tự).
"""

from __future__ import annotations

from typing import Final

from app.modules.template.domain.entities import Template
from app.modules.template.domain.enums import Family, Layout, Tier, Tone


def _t(key: str, name: str, family: Family, layout: Layout, tone: Tone, *, new: bool) -> Template:
    return Template(key=key, name=name, family=family, tone=tone, layout=layout, is_new=new)


_BLUEPRINTS: Final[tuple[Template, ...]] = (
    _t("uyenuong", "Uyên Ương 3D", Family.MOTION, Layout.LUX, Tone.FORMAL, new=True),
    _t("songhy3d", "Song Hỷ 3D", Family.MOTION, Layout.LUX, Tone.FAMILY, new=True),
    _t("hongphale", "Hồng Pha Lê", Family.MOTION, Layout.LUX, Tone.FRIENDS, new=True),
    _t("hatkim", "Hạt Ánh Kim", Family.MOTION, Layout.LUX, Tone.FORMAL, new=True),
    _t("nganha", "Ngân Hà", Family.MOTION, Layout.LUX, Tone.FRIENDS, new=True),
    _t("phaohoa", "Đêm Pháo Hoa", Family.MODERN, Layout.CINEMA, Tone.FORMAL, new=True),
    _t("canhhong", "Mưa Cánh Hồng", Family.MODERN, Layout.CINEMA, Tone.FAMILY, new=True),
    _t("hoanghon", "Hoàng Hôn Kính", Family.MODERN, Layout.GLASS, Tone.FRIENDS, new=True),
    _t("cucquang", "Cực Quang", Family.MODERN, Layout.GLASS, Tone.FORMAL, new=True),
    _t("tapchi", "Tạp Chí Ngà", Family.MODERN, Layout.EDITORIAL, Tone.FRIENDS, new=True),
    _t("noir", "Bìa Đen", Family.MODERN, Layout.EDITORIAL, Tone.FORMAL, new=True),
    _t("denlong", "Đèn Lồng Hỷ", Family.RED, Layout.TRAD, Tone.FAMILY, new=True),
    _t("luadao", "Lụa Đào", Family.RED, Layout.DECO, Tone.FORMAL, new=True),
    _t("hongnhung", "Hồng Nhung", Family.RED, Layout.FLORA, Tone.FRIENDS, new=True),
    _t("biado", "Bìa Đỏ", Family.RED, Layout.EDITORIAL, Tone.FORMAL, new=True),
    _t("hongngoc", "Hồng Ngọc", Family.RED, Layout.GLASS, Tone.FRIENDS, new=True),
    _t("songhy", "Song Hỷ Đỏ Son", Family.TRAD, Layout.TRAD, Tone.FAMILY, new=False),
    _t("hongphuc", "Hồng Phúc", Family.TRAD, Layout.TRAD, Tone.FAMILY, new=False),
    _t("ngoctrai", "Ngọc Trai Champagne", Family.GOLD, Layout.DECO, Tone.FORMAL, new=False),
    _t("demnhung", "Đêm Nhung", Family.GOLD, Layout.DECO, Tone.FORMAL, new=False),
    _t("maudon", "Mẫu Đơn", Family.FLORA, Layout.FLORA, Tone.FRIENDS, new=False),
    _t("xothom", "Lá Xô Thơm", Family.FLORA, Layout.FLORA, Tone.FRIENDS, new=False),
    # Bộ mẫu lộng lẫy bổ sung — mỗi mẫu một màn mở riêng (cổng son, sen nở, cuộn thư, hộp quà).
    _t("cungdinh", "Cổng Son Cung Đình", Family.ROYAL, Layout.TRAD, Tone.FAMILY, new=True),
    _t("longphung", "Long Phụng Hoà Minh", Family.ROYAL, Layout.LUX, Tone.FAMILY, new=True),
    _t("hoangkim", "Hoàng Kim Dạ Yến", Family.ROYAL, Layout.DECO, Tone.FORMAL, new=True),
    _t("ngocbich", "Ngọc Bích Hoàng Triều", Family.ROYAL, Layout.DECO, Tone.FORMAL, new=True),
    _t("nhungtim", "Nhung Tím Hoàng Gia", Family.ROYAL, Layout.DECO, Tone.FORMAL, new=True),
    _t("phale", "Pha Lê Kim Cương", Family.ROYAL, Layout.GLASS, Tone.FORMAL, new=True),
    _t("senhong", "Sen Hồng Ngự Uyển", Family.TRAD, Layout.LOTUS, Tone.FAMILY, new=True),
    _t("senvangdem", "Sen Vàng Đêm Hội", Family.RED, Layout.LOTUS, Tone.FORMAL, new=True),
    _t("phaohong", "Pháo Hồng Rộn Rã", Family.RED, Layout.TRAD, Tone.FAMILY, new=True),
    _t("hoian", "Phố Hội Đèn Lồng", Family.TRAD, Layout.TRAD, Tone.FAMILY, new=True),
    _t("maycattuong", "Mây Hồng Cát Tường", Family.TRAD, Layout.TRAD, Tone.FAMILY, new=True),
    _t("maivang", "Mai Vàng Phú Quý", Family.TRAD, Layout.FLORA, Tone.FAMILY, new=True),
    _t("anhdao", "Anh Đào Xuân Thì", Family.PASTEL, Layout.FLORA, Tone.FRIENDS, new=True),
    _t("oaihuong", "Oải Hương Provence", Family.PASTEL, Layout.FLORA, Tone.FRIENDS, new=True),
    _t("hongtrang", "Hồng Trắng Tinh Khôi", Family.PASTEL, Layout.FLORA, Tone.FORMAL, new=True),
    _t("camtu", "Cẩm Tú Cầu", Family.PASTEL, Layout.FLORA, Tone.FRIENDS, new=True),
    _t("hoadao", "Đào Thắm Ngày Xuân", Family.FLORA, Layout.FLORA, Tone.FAMILY, new=True),
    _t("daquy", "Dã Quỳ Cao Nguyên", Family.FLORA, Layout.FLORA, Tone.FRIENDS, new=True),
    _t("dasao", "Dạ Tiệc Ánh Sao", Family.MODERN, Layout.CINEMA, Tone.FORMAL, new=True),
    _t("champagne", "Ly Champagne", Family.MODERN, Layout.GLASS, Tone.FRIENDS, new=True),
    _t("bienxanh", "Hoàng Hôn Biển", Family.MODERN, Layout.GLASS, Tone.FRIENDS, new=True),
    _t("vogue", "Vogue Hồng Phấn", Family.MODERN, Layout.EDITORIAL, Tone.FRIENDS, new=True),
    _t("anhtrang", "Ánh Trăng Bạc", Family.MOTION, Layout.LUX, Tone.FORMAL, new=True),
    _t("kimtuyen", "Mưa Kim Tuyến", Family.MOTION, Layout.LUX, Tone.FRIENDS, new=True),
)

#: Mẫu dùng được ở gói Miễn phí: năm mẫu cổ điển, mở bằng phong bì hoặc cuộn thư.
FREE_KEYS: Final[frozenset[str]] = frozenset({"songhy", "hongphuc", "ngoctrai", "maudon", "xothom"})

#: Dòng cần Gói Lộng Lẫy: hoạt hình 3D (three.js) và cung đình (màn mở lộng lẫy).
PREMIUM_FAMILIES: Final[frozenset[Family]] = frozenset({Family.MOTION, Family.ROYAL})
PREMIUM_KEYS: Final[frozenset[str]] = frozenset({"phaohoa", "dasao"})


def tier_of(item: Template) -> Tier:
    """Hạng khởi tạo của một mẫu; đội vận hành đổi được sau đó."""
    if item.key in FREE_KEYS:
        return Tier.FREE
    if item.family in PREMIUM_FAMILIES or item.key in PREMIUM_KEYS:
        return Tier.PREMIUM
    return Tier.STANDARD


#: Thứ tự hiển thị mặc định bước 10 để đội vận hành chèn mẫu vào giữa được.
TEMPLATE_BLUEPRINTS: Final[tuple[Template, ...]] = tuple(
    Template(
        key=item.key,
        name=item.name,
        family=item.family,
        tone=item.tone,
        layout=item.layout,
        is_new=item.is_new,
        sort_order=(index + 1) * 10,
        tier=tier_of(item),
    )
    for index, item in enumerate(_BLUEPRINTS)
)

#: Mẫu mặc định cho khách chung (link không mã), theo dữ liệu mẫu của thiết kế.
DEFAULT_TEMPLATE_KEY: Final[str] = "uyenuong"

__all__ = ["DEFAULT_TEMPLATE_KEY", "TEMPLATE_BLUEPRINTS"]
