"""Mẫu cho nghỉ: khách không chọn được nữa, nhưng không bị xoá và bật lại được.

Catalog công khai chỉ còn đúng một mẫu `daile` ("Đại Lễ Hỷ Sự"); mọi khoá khác
(bộ Độc bản 2026 `db*` và toàn bộ mẫu cũ) đổi sang `daile`.
"""

from __future__ import annotations

from httpx import AsyncClient

from app.modules.template import build_ensure_catalog
from app.modules.template.domain.catalog import (
    DAILE_TEMPLATE_KEY,
    DEFAULT_TEMPLATE_KEY,
    DOC_BAN_2026_KEYS,
    FREE_KEYS,
    LEGACY_TEMPLATE_REPLACEMENTS,
    ORIGINAL_TEMPLATE_KEYS,
    RETIRED_KEYS,
    TEMPLATE_BLUEPRINTS,
    canonical_template_key,
)
from app.modules.template.domain.enums import Tier, Tone
from app.modules.template.infrastructure.persistence.models import TemplateDocument
from tests.conftest import API, Session


def test_chi_cho_nghi_mau_co_that_va_khong_dung_mau_mien_phi() -> None:
    keys = {item.key for item in TEMPLATE_BLUEPRINTS}
    assert set(RETIRED_KEYS) <= keys
    assert not set(RETIRED_KEYS) & FREE_KEYS
    assert DEFAULT_TEMPLATE_KEY not in RETIRED_KEYS
    assert all(reason.strip() for reason in RETIRED_KEYS.values())
    assert set(DOC_BAN_2026_KEYS) <= set(RETIRED_KEYS)
    assert RETIRED_KEYS["dbgomlam"] == "Thay bằng mẫu duy nhất Đại Lễ Hỷ Sự"


def test_catalog_cong_khai_chi_con_dai_le() -> None:
    alive = [item for item in TEMPLATE_BLUEPRINTS if item.key not in RETIRED_KEYS]
    assert [item.key for item in alive] == ["daile"]
    assert ORIGINAL_TEMPLATE_KEYS == ("daile",)
    assert set(FREE_KEYS) == {"daile"}
    assert DEFAULT_TEMPLATE_KEY == DAILE_TEMPLATE_KEY == "daile"
    daile = alive[0]
    assert daile.name == "Đại Lễ Hỷ Sự"
    assert daile.tone is Tone.FAMILY
    assert daile.tier is Tier.FREE
    assert daile.is_new
    assert daile.sort_order == min(item.sort_order for item in TEMPLATE_BLUEPRINTS)
    assert TEMPLATE_BLUEPRINTS[0].key == "daile"


def test_moi_khoa_cu_doi_sang_dai_le() -> None:
    assert set(LEGACY_TEMPLATE_REPLACEMENTS) == set(RETIRED_KEYS)
    assert set(LEGACY_TEMPLATE_REPLACEMENTS.values()) == {"daile"}
    for key in ("songhy", "uyenuong", "stsonghydo", "sgsonmai", "dbgomlam", "dbluadao"):
        assert canonical_template_key(key) == "daile"
    assert canonical_template_key("daile") == "daile"
    assert canonical_template_key("") == ""
    assert canonical_template_key("khongco") == "khongco"


async def test_khach_chi_thay_dai_le_quan_tri_thay_ca_mau_nghi(
    client: AsyncClient, admin: Session, customer: Session
) -> None:
    seen_by_customer = await client.get(f"{API}/templates", headers=customer.headers)
    seen_by_admin = await client.get(f"{API}/templates", headers=admin.headers)
    customer_ids = [item["id"] for item in seen_by_customer.json()["data"]]
    admin_rows = {item["id"]: item for item in seen_by_admin.json()["data"]}
    assert customer_ids == ["daile"]
    assert admin_rows["daile"]["is_active"] is True
    assert all(admin_rows[key]["is_active"] is False for key in RETIRED_KEYS)


async def test_csdl_cu_tat_bo_doc_ban_va_mau_tung_bat_lai_dung_mot_lan(
    client: AsyncClient, admin: Session
) -> None:
    """CSDL đã qua đợt Độc bản 2026: `db*` đang bật, chưa có dấu đợt mới; một mẫu cũ
    đội vận hành từng bật lại. Seed tắt cả hai đúng một lần, `daile` được tạo và bật."""
    collection = TemplateDocument.get_motor_collection()
    await collection.delete_many({"key": "daile"})
    await collection.update_many(
        {"key": {"$in": [*DOC_BAN_2026_KEYS, "vogue"]}},
        {"$set": {"is_active": True}, "$unset": {"single_catalog_v1": ""}},
    )

    await build_ensure_catalog().execute()

    rows = (await client.get(f"{API}/templates", headers=admin.headers)).json()["data"]
    active = {row["id"] for row in rows if row["is_active"]}
    assert active == {"daile"}


async def test_bat_lai_thi_seed_khong_tat_lan_nua(client: AsyncClient, admin: Session) -> None:
    on = await client.patch(
        f"{API}/templates/vogue", json={"is_active": True}, headers=admin.headers
    )
    assert on.status_code == 200
    await build_ensure_catalog().execute()
    rows = (await client.get(f"{API}/templates", headers=admin.headers)).json()["data"]
    assert next(row for row in rows if row["id"] == "vogue")["is_active"] is True
