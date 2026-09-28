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

#: Bộ "Tối giản" — mẫu hiện đại, chữ lớn dễ đọc, nền phẳng (không hiệu ứng canvas).
#: Bản vẽ ở web: `lib/invite/modern-templates.ts` — khoá phải trùng.
_MODERN_BLUEPRINTS: Final[tuple[Template, ...]] = (
    _t("tgdodo", "Thanh Nhã Đỏ Đô", Family.MINIMAL, Layout.MINIMAL, Tone.FAMILY, new=True),
    _t("tgreu", "Thanh Nhã Xanh Rêu", Family.MINIMAL, Layout.MINIMAL, Tone.FORMAL, new=True),
    _t("tglam", "Thanh Nhã Lam Đêm", Family.MINIMAL, Layout.MINIMAL, Tone.FORMAL, new=True),
    _t("tgnau", "Thanh Nhã Nâu Cà Phê", Family.MINIMAL, Layout.MINIMAL, Tone.FAMILY, new=True),
    _t("tgtim", "Thanh Nhã Tím Khói", Family.MINIMAL, Layout.MINIMAL, Tone.FRIENDS, new=True),
    _t("ncmuc", "Nét Chữ Mực Đỏ", Family.MINIMAL, Layout.TYPE, Tone.FRIENDS, new=True),
    _t("ncden", "Nét Chữ Đen Vàng", Family.MINIMAL, Layout.TYPE, Tone.FORMAL, new=True),
    _t("ncdat", "Nét Chữ Hồng Đất", Family.MINIMAL, Layout.TYPE, Tone.FRIENDS, new=True),
    _t("ncbien", "Nét Chữ Xanh Biển", Family.MINIMAL, Layout.TYPE, Tone.FORMAL, new=True),
    _t("ncreu", "Nét Chữ Rêu Đêm", Family.MINIMAL, Layout.TYPE, Tone.FAMILY, new=True),
)


def _story(key: str, name: str, family: Family, tone: Tone) -> Template:
    return _t(key, name, family, Layout.STORY, tone, new=True)


#: Web thiệp kiểu kể chuyện: mở bằng ảnh cưới, trang tự cuộn (web: `src/lib/story/themes`).
_STORY_BLUEPRINTS: Final[tuple[Template, ...]] = (
    _story("stsonghyxanh", "Song Hỷ Xanh", Family.STORY_TRAD, Tone.FAMILY),
    _story("stmndodam", "Minimalism Đỏ Đậm", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stminimalismnau", "Minimalism Nâu", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stsonglongdo", "Song Long Đỏ", Family.STORY_TRAD, Tone.FAMILY),
    _story("stsonghydo", "Song Hỷ Đỏ", Family.STORY_TRAD, Tone.FAMILY),
    _story("sthoamocxanh", "Hoa Mộc Xanh", Family.STORY_FLORAL, Tone.FRIENDS),
    _story("stlongphungv3do", "Long Phụng V3 Đỏ", Family.STORY_TRAD, Tone.FAMILY),
    _story("stsongphungdo", "Song Phụng Đỏ", Family.STORY_TRAD, Tone.FAMILY),
    _story("stlaudaixanh", "Lâu Đài Xanh", Family.STORY_ROMANCE, Tone.FRIENDS),
    _story("stmailantrang", "Mai Lan Trắng", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stvuonkinhhong", "Vườn Kính Hồng", Family.STORY_ROMANCE, Tone.FRIENDS),
    _story("stvuonkinhxanh", "Vườn Kính Xanh", Family.STORY_ROMANCE, Tone.FRIENDS),
    _story("stlongphungdo", "Long Phụng Đỏ", Family.STORY_TRAD, Tone.FAMILY),
    _story("stminimalismxanh", "Minimalism Xanh", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stbaroquev2dodam", "Baroque V2 Đỏ Đậm", Family.STORY_LUXE, Tone.FORMAL),
    _story("stvuonxuanlam", "Vườn Xuân Lam", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stlongphungv2do", "Long Phụng V2 Đỏ", Family.STORY_TRAD, Tone.FAMILY),
    _story("stthanhdiepxanh", "Thanh Diệp Xanh", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stnhatbinhdo", "Nhật Bình Đỏ", Family.STORY_TRAD, Tone.FAMILY),
    _story("stlongphungv4do", "Long Phụng V4 Đỏ", Family.STORY_TRAD, Tone.FAMILY),
    _story("sttoduyendodam", "Tơ Duyên Đỏ Đậm", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stchibired", "Chibi Đỏ", Family.STORY_ROMANCE, Tone.FRIENDS),
    _story("stsonglongxanh", "Song Long Xanh", Family.STORY_TRAD, Tone.FAMILY),
    _story("sttoduyenxanh", "Tơ Duyên Xanh", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stlongphungxanh", "Long Phụng Xanh", Family.STORY_TRAD, Tone.FAMILY),
    _story("sttoduyenhong", "Tơ Duyên Hồng", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stlaudailam", "Lâu Đài Lam", Family.STORY_LUXE, Tone.FORMAL),
    _story("stvuonxuanxanh", "Vườn Xuân Xanh", Family.STORY_ROMANCE, Tone.FRIENDS),
    _story("stsonghacdo", "Song Hạc Đỏ", Family.STORY_TRAD, Tone.FAMILY),
    _story("sthoamochong", "Hoa Mộc Hồng", Family.STORY_FLORAL, Tone.FRIENDS),
    _story("sthoangkimdo", "Hoàng Kim Đỏ", Family.STORY_LUXE, Tone.FORMAL),
    _story("stsonglonglam", "Song Long Lam", Family.STORY_TRAD, Tone.FAMILY),
    _story("stminimalismdo", "Minimalism Đỏ", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("sthoaluanau", "Hoa Lụa Nâu", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stminimalismlamdam", "Minimalism Lam Đậm", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("sthoamocnau", "Hoa Mộc Nâu", Family.STORY_FLORAL, Tone.FRIENDS),
    _story("stvuonxuando", "Vườn Xuân Đỏ", Family.STORY_ROMANCE, Tone.FRIENDS),
    _story("stsongphungxanh", "Song Phụng Xanh", Family.STORY_TRAD, Tone.FAMILY),
    _story("stanhdaohong", "Anh Đào Hồng", Family.STORY_ROMANCE, Tone.FRIENDS),
    _story("stlienhoahong", "Liên Hoa", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("sthoangkimxanh", "Hoàng Kim Xanh", Family.STORY_LUXE, Tone.FORMAL),
    _story("sthoanggiavang", "Baroque Gold", Family.STORY_LUXE, Tone.FORMAL),
    _story("stlienhoav2xanh", "Liên Hoa V2 Xanh", Family.STORY_TRAD, Tone.FAMILY),
    _story("stbaroquev2xanhdam", "Baroque V2 Xanh Đậm", Family.STORY_LUXE, Tone.FORMAL),
    _story("stlongphunglam", "Long Phụng Lam", Family.STORY_TRAD, Tone.FAMILY),
    _story("sthoatinhdo", "Hoạ Tình Đỏ", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("sthoathuytinhlam", "Hoa Thuỷ Tinh Lam", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stcobado", "Cô Ba Đỏ", Family.STORY_TRAD, Tone.FAMILY),
    _story("sthoangkimlam", "Hoàng Kim Lam", Family.STORY_LUXE, Tone.FORMAL),
    _story("stbaroquev2lamdam", "Baroque V2 Lam Đậm", Family.STORY_LUXE, Tone.FORMAL),
    _story("stbachsuv2hong", "Bạch Sứ V2 Hồng", Family.STORY_ROMANCE, Tone.FRIENDS),
    _story("sthoangkimiixanh", "Hoàng Kim II Xanh", Family.STORY_LUXE, Tone.FORMAL),
    _story("stlongphunghuyen", "Long Phụng Huyền", Family.STORY_TRAD, Tone.FAMILY),
    _story("sthoahuongduong", "Hoa Hướng Dương", Family.STORY_ROMANCE, Tone.FRIENDS),
    _story("stminimalismnaudam", "Minimalism Nâu Đậm", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stminimalismtim", "Minimalism Tím", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stbachsunau", "Bạch Sứ Nâu", Family.STORY_LUXE, Tone.FORMAL),
    _story("stbachsuv2xanh", "Bạch Sứ V2 Xanh", Family.STORY_ROMANCE, Tone.FRIENDS),
    _story("sthoathuytinhxanh", "Hoa Thuỷ Tinh Xanh", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stbachsulam", "Bạch Sứ Lam", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stbachsuv2do", "Bạch Sứ II Đỏ", Family.STORY_LUXE, Tone.FORMAL),
    _story("sthoathuytinhdo", "Hoa Thuỷ Tinh Đỏ", Family.STORY_MINIMAL, Tone.FORMAL),
    _story("stbachsudo", "Bạch Sứ Đỏ", Family.STORY_TRAD, Tone.FAMILY),
    _story("sthoangkimiitim", "Hoàng Kim II Tím", Family.STORY_LUXE, Tone.FORMAL),
    _story("stvuonkinhlam", "Vườn Kính Lam", Family.STORY_ROMANCE, Tone.FRIENDS),
    _story("sthoakhocam", "Hoa Khô", Family.STORY_FLORAL, Tone.FRIENDS),
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


def _ordered(item: Template, sort_order: int) -> Template:
    return Template(
        key=item.key,
        name=item.name,
        family=item.family,
        tone=item.tone,
        layout=item.layout,
        is_new=item.is_new,
        sort_order=sort_order,
        tier=tier_of(item),
    )


#: Thứ tự hiển thị mặc định bước 10 để đội vận hành chèn mẫu vào giữa được. Bộ Tối giản
#: đứng TRƯỚC (1, 2, 3...): seed chỉ tạo mẫu còn thiếu, không đổi thứ tự mẫu đã có.
TEMPLATE_BLUEPRINTS: Final[tuple[Template, ...]] = (
    tuple(_ordered(item, 0) for item in _STORY_BLUEPRINTS)
    + tuple(_ordered(item, index + 1) for index, item in enumerate(_MODERN_BLUEPRINTS))
) + tuple(_ordered(item, (index + 1) * 10) for index, item in enumerate(_BLUEPRINTS))

#: Mẫu mặc định cho khách chung (link không mã), theo dữ liệu mẫu của thiết kế.
DEFAULT_TEMPLATE_KEY: Final[str] = "uyenuong"

__all__ = ["DEFAULT_TEMPLATE_KEY", "TEMPLATE_BLUEPRINTS"]
