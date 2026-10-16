"""Chuyển đổi một lần: design mẫu chính + khách theo link (spec §8)."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.base_model import utc_now
from app.modules.guest.infrastructure.persistence.models import GuestDocument, InviteLinkDocument
from app.modules.wedding.infrastructure.persistence.models import (
    SCHEMA_VERSION,
    EventModel,
    WeddingDocument,
)
from app.seeds import migrate_links_designs as migrate_module
from app.seeds.migrate_links_designs import run
from tests.conftest import API, Session


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
    assert set(links) == {"Họ hàng", "Bạn bè", "Đồng nghiệp"}
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


def _event(event_id: str, side: str) -> EventModel:
    return EventModel(id=event_id, name=event_id, side=side)


async def test_migrate_giu_dung_le_tiec_moi_khach_thay(catalog: None) -> None:
    tenant = uuid4()
    await WeddingDocument(
        tenant_id=tenant,
        slug="le-tiec",
        default_template="daile",
        events=[_event("t1", "trai"), _event("g1", "gai"), _event("c1", "chung")],
    ).insert()
    for name, side, events in (
        ("A", "trai", []),
        ("B", "trai", []),
        ("C", "gai", ["g1", "xoa"]),
    ):
        await GuestDocument(
            tenant_id=tenant,
            code=uuid4().hex[:6],
            name=name,
            group="Họ hàng",
            side=side,
            events=events,
        ).insert()
    stats = await run()
    assert stats["links_created"] == 2
    links = {str(link.id): link for link in await InviteLinkDocument.find({}).to_list()}
    guests = {guest.name: guest for guest in await GuestDocument.find({}).to_list()}
    assert guests["A"].link == guests["B"].link
    assert sorted(links[guests["A"].link].events) == ["c1", "t1"]
    assert links[guests["C"].link].events == ["g1"]
    assert {link.name for link in links.values()} == {"Họ hàng – Nhà trai", "Họ hàng – 2"}


async def test_migrate_cung_ben_le_tiec_rong_ra_mot_link(catalog: None) -> None:
    tenant = uuid4()
    await WeddingDocument(
        tenant_id=tenant,
        slug="mot-ben",
        default_template="daile",
        events=[_event("t1", "trai")],
    ).insert()
    for name in ("A", "B"):
        await GuestDocument(
            tenant_id=tenant, code=uuid4().hex[:6], name=name, group="Bạn bè", side="trai"
        ).insert()
    stats = await run()
    assert stats["links_created"] == 1
    link = await InviteLinkDocument.find_one({})
    assert link is not None
    assert link.name == "Bạn bè"
    assert link.events == []  # trùng toàn bộ lễ tiệc của đám cưới


async def test_migrate_bo_qua_dam_cuoi_tao_moi(client: AsyncClient, customer: Session) -> None:
    response = await client.post(
        f"{API}/wedding/setup", json={"mode": "blank"}, headers=customer.headers
    )
    assert response.status_code == 201, response.text
    wedding = await WeddingDocument.find_one({})
    assert wedding is not None
    assert wedding.schema_version == SCHEMA_VERSION
    await GuestDocument(
        tenant_id=wedding.tenant_id, code="abc123", name="Khách", group="Bạn bè"
    ).insert()
    stats = await run()
    assert stats["weddings"] == 0
    assert await InviteLinkDocument.find({}).count() == 0
    guest = await GuestDocument.find_one({})
    assert guest is not None
    assert guest.link == ""


async def test_migrate_mot_dam_cuoi_loi_khong_chan_cac_dam_khac(
    catalog: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad, good = uuid4(), uuid4()
    for tenant, slug in ((bad, "dam-hong"), (good, "dam-tot")):
        await WeddingDocument(tenant_id=tenant, slug=slug, default_template="daile").insert()
    real = migrate_module.migrate_wedding

    async def flaky(raw: dict[str, Any]) -> dict[str, int]:
        if raw["tenant_id"] == bad:
            message = "hỏng"
            raise RuntimeError(message)
        return await real(raw)

    monkeypatch.setattr(migrate_module, "migrate_wedding", flaky)
    stats = await run()
    assert stats["failed"] == 1
    assert stats["weddings"] == 1
    done = {w.slug: w.schema_version for w in await WeddingDocument.find({}).to_list()}
    assert done == {"dam-hong": 0, "dam-tot": 1}
    # Lỗi thì trả lại quyền chuyển: lần khởi động sau thử lại ngay, không chờ hết hạn.
    raws = await WeddingDocument.get_motor_collection().find({}).to_list(None)
    assert all("migrating_at" not in raw for raw in raws)


async def test_migrate_mau_chinh_da_nghi_doi_sang_khoa_chuan(catalog: None) -> None:
    await WeddingDocument(
        tenant_id=uuid4(), slug="bia-den", default_template="noir", theme={"accent": "#AA0000"}
    ).insert()
    await run()
    wedding = await WeddingDocument.find_one({})
    assert wedding is not None
    assert wedding.default_template == "daile"
    assert set(wedding.designs) == {"daile"}
    assert wedding.designs["daile"].theme.accent == "#AA0000"


async def test_migrate_mau_phu_dang_dung_giu_giao_dien_cu(catalog: None) -> None:
    tenant = uuid4()
    await WeddingDocument(
        tenant_id=tenant,
        slug="nhieu-mau",
        default_template="daile",
        group_templates={"Họ hàng": "moi", "Không ai": "trong"},
        theme={"accent": "#AA0000"},
        music_url="https://x.vn/a.mp3",
        designs={"lienket": {"theme": {"accent": "#0000AA"}}},
    ).insert()
    for name, group, template in (("Bác Bình", "Họ hàng", ""), ("Bạn Vy", "Bạn bè", "khac")):
        await GuestDocument(
            tenant_id=tenant, code=uuid4().hex[:6], name=name, group=group, template=template
        ).insert()
    await InviteLinkDocument(
        tenant_id=tenant, slug="dong-nghiep", name="Đồng nghiệp", template="lienket"
    ).insert()
    await InviteLinkDocument(
        tenant_id=tenant, slug="ban-cu", name="Bạn cũ", template="noir"
    ).insert()
    await run()
    wedding = await WeddingDocument.find_one({})
    assert wedding is not None
    assert set(wedding.designs) == {"daile", "moi", "khac", "lienket"}
    for key in ("daile", "moi", "khac"):
        assert wedding.designs[key].theme.accent == "#AA0000", key
        assert wedding.designs[key].music_url == "https://x.vn/a.mp3", key
    assert wedding.designs["lienket"].theme.accent == "#0000AA", "design có sẵn không bị đè"


async def test_migrate_le_tiec_rieng_da_xoa_het_thi_thay_tat_ca(catalog: None) -> None:
    tenant = uuid4()
    await WeddingDocument(
        tenant_id=tenant,
        slug="xoa-het",
        default_template="daile",
        events=[_event("t1", "trai"), _event("g1", "gai")],
    ).insert()
    await GuestDocument(
        tenant_id=tenant, code="abc123", name="A", group="Bạn bè", side="gai", events=["xoa"]
    ).insert()
    await run()
    link = await InviteLinkDocument.find_one({})
    assert link is not None
    assert link.events == [], "như eventsFor: danh sách riêng không còn id nào -> mọi lễ tiệc"


async def test_migrate_dem_video_rieng_cua_link_bi_bo(catalog: None) -> None:
    tenant = uuid4()
    await WeddingDocument(tenant_id=tenant, slug="video", default_template="daile").insert()
    await InviteLinkDocument(tenant_id=tenant, slug="co-video", name="A", intro="vid1").insert()
    await InviteLinkDocument(tenant_id=tenant, slug="khong-video", name="B").insert()
    stats = await run()
    assert stats["intro_overrides_dropped"] == 1


async def test_migrate_nhieu_worker_cung_luc_moi_link_tao_mot_lan(catalog: None) -> None:
    await _seed()
    first, second = await asyncio.gather(run(), run())
    assert first["weddings"] + second["weddings"] == 1
    assert first["failed"] + second["failed"] == 0
    names = sorted(link.name for link in await InviteLinkDocument.find({}).to_list())
    assert names == ["Bạn bè", "Họ hàng", "Đồng nghiệp"]
    raw = await WeddingDocument.get_motor_collection().find_one({})
    assert raw is not None
    assert raw["schema_version"] == SCHEMA_VERSION
    assert "migrating_at" not in raw


async def test_migrate_bo_qua_dam_cuoi_dang_duoc_worker_khac_chuyen(catalog: None) -> None:
    await _seed()
    collection = WeddingDocument.get_motor_collection()
    await collection.update_many({}, {"$set": {"migrating_at": utc_now()}})
    stats = await run()
    assert stats["weddings"] == 0
    assert await InviteLinkDocument.find({}).count() == 1  # chỉ link có sẵn


async def test_migrate_nhan_lai_khi_worker_truoc_qua_han(catalog: None) -> None:
    await _seed()
    collection = WeddingDocument.get_motor_collection()
    stale = utc_now() - timedelta(minutes=11)
    await collection.update_many({}, {"$set": {"migrating_at": stale}})
    stats = await run()
    assert stats["weddings"] == 1
