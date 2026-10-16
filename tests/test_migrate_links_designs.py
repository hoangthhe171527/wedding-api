"""Chuyển đổi một lần: design mẫu chính + khách theo link (spec §8)."""

from __future__ import annotations

from uuid import uuid4

from app.modules.guest.infrastructure.persistence.models import GuestDocument, InviteLinkDocument
from app.modules.wedding.infrastructure.persistence.models import WeddingDocument
from app.seeds.migrate_links_designs import run


async def _seed() -> None:
    tenant = uuid4()
    await WeddingDocument(
        tenant_id=tenant,
        slug="h-hoang-ha",
        default_template="daile",
        group_templates={"Họ hàng": "daile"},
        theme={"accent": "#AA0000"},
    ).insert()
    for name, group, template in (
        ("Bác Bình", "Họ hàng", ""),
        ("Chú Nam", "Họ hàng", ""),
        ("Bạn Khoa", "Bạn bè", ""),
        ("Bạn Vy", "Bạn bè", "noir"),
    ):
        await GuestDocument(
            tenant_id=tenant, code=uuid4().hex[:6], name=name, group=group, template=template
        ).insert()
    await InviteLinkDocument(tenant_id=tenant, slug="dong-nghiep", name="Đồng nghiệp").insert()


async def test_migrate_tao_link_theo_nhom_va_design_mau_chinh(catalog: None) -> None:
    await _seed()
    stats = await run()
    assert stats["weddings"] == 1
    wedding = await WeddingDocument.find_one({})
    assert wedding is not None
    assert wedding.schema_version == 1
    assert wedding.designs["daile"].theme.accent == "#AA0000"
    links = {link.name: link for link in await InviteLinkDocument.find({}).to_list()}
    assert set(links) >= {"Họ hàng", "Bạn bè", "Đồng nghiệp"}
    assert links["Đồng nghiệp"].template == "daile"  # link có sẵn: điền mẫu chính
    guests = await GuestDocument.find({}).to_list()
    assert all(guest.link for guest in guests)
    by_name = {guest.name: guest.link for guest in guests}
    assert by_name["Bác Bình"] == by_name["Chú Nam"] == str(links["Họ hàng"].id)
    # "noir" đã nghỉ -> thay bằng daile -> trùng mẫu nhóm -> cùng link "Bạn bè"
    assert by_name["Bạn Vy"] == by_name["Bạn Khoa"]


async def test_migrate_chay_lai_khong_doi(catalog: None) -> None:
    await _seed()
    await run()
    links_before = await InviteLinkDocument.find({}).count()
    stats = await run()
    assert stats["weddings"] == 0
    assert await InviteLinkDocument.find({}).count() == links_before
