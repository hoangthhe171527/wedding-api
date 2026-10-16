"""Design riêng theo mẫu: đồng bộ trường cũ <-> designs[mẫu chính] (spec §5.1)."""

from __future__ import annotations

from dataclasses import replace

from app.modules.wedding.domain.design import CardDesign
from app.modules.wedding.domain.designs import (
    legacy_design,
    main_design,
    main_key,
    normalize_designs,
)
from app.modules.wedding.domain.entities import (
    Parents,
    Person,
    TemplateDesign,
    Theme,
    WeddingContent,
)
from app.modules.wedding.domain.enums import OpenStyle
from app.modules.wedding.domain.services import plan_usage, validate_content


def _content(**changes: object) -> WeddingContent:
    base = WeddingContent(
        groom=Person(),
        bride=Person(),
        groom_parents=Parents(),
        bride_parents=Parents(),
        events=(),
        default_template="daile",
    )
    return replace(base, **changes)  # type: ignore[arg-type]


RED = Theme(accent="#AA0000")
BLUE = Theme(accent="#0000AA")


def test_main_key_lui_ve_daile_khi_rong() -> None:
    assert main_key(_content(default_template="")) == "daile"
    assert main_key(_content(default_template="other")) == "other"


def test_client_cu_khong_gui_designs_giu_design_khac_va_cap_nhat_mau_chinh() -> None:
    stored = _content(designs={"other": TemplateDesign(theme=BLUE)})
    incoming = _content(theme=RED, music_url="https://x.vn/a.mp3")
    out = normalize_designs(incoming, designs_sent=False, stored=stored)
    assert out.designs["other"].theme == BLUE
    assert out.designs["daile"].theme == RED
    assert out.designs["daile"].music_url == "https://x.vn/a.mp3"
    assert out.theme == RED


def test_client_moi_gui_designs_thi_truong_cu_theo_mau_chinh() -> None:
    incoming = _content(
        theme=BLUE,  # trường cũ lệch — designs thắng
        designs={"daile": TemplateDesign(theme=RED, open_style=OpenStyle.BY_TEMPLATE)},
    )
    out = normalize_designs(incoming, designs_sent=True, stored=None)
    assert out.theme == RED
    assert main_design(out).theme == RED


def test_client_moi_thieu_design_mau_chinh_thi_lay_tu_truong_cu() -> None:
    incoming = _content(theme=RED, designs={"other": TemplateDesign(theme=BLUE)})
    out = normalize_designs(incoming, designs_sent=True, stored=None)
    assert out.designs["daile"].theme == RED
    assert out.designs["other"].theme == BLUE


def test_legacy_design_doc_truong_cu() -> None:
    content = _content(
        card_design=CardDesign(enabled=True), intro="", open_style=OpenStyle.BY_TEMPLATE
    )
    assert legacy_design(content).card_design.enabled is True


def test_validate_design_key_la_va_mau_sai() -> None:
    content = _content(designs={"khong-co": TemplateDesign(theme=Theme(accent="đỏ"))})
    errors = validate_content(content, known_templates=frozenset({"daile"}))
    assert "designs.khong-co" in errors


def test_validate_mau_trong_design() -> None:
    content = _content(designs={"daile": TemplateDesign(theme=Theme(accent="đỏ"))})
    errors = validate_content(content, known_templates=frozenset({"daile"}))
    assert "designs.daile.theme.accent" in errors


def test_plan_usage_gom_design_cua_moi_mau_dang_dung() -> None:
    content = _content(
        designs={
            "daile": TemplateDesign(),
            "other": TemplateDesign(theme=RED, card_design=CardDesign(enabled=True)),
            "unused": TemplateDesign(music_url="https://x.vn/a.mp3"),
        }
    )
    usage = plan_usage(content, guest_count=3, guest_templates={"other"})
    assert usage["templates"] == ["daile", "other"]
    assert usage["theme"] is True
    assert usage["design"] is True
    assert usage["music"] is False  # mẫu "unused" không ai thấy
