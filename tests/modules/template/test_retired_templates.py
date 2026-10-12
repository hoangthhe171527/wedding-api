"""Mẫu cho nghỉ: khách không chọn được nữa, nhưng không bị xoá và bật lại được."""

from __future__ import annotations

from httpx import AsyncClient

from app.modules.template import build_ensure_catalog
from app.modules.template.domain.catalog import (
    DEFAULT_TEMPLATE_KEY,
    FREE_KEYS,
    LEGACY_TEMPLATE_REPLACEMENTS,
    ORIGINAL_TEMPLATE_KEYS,
    RETIRED_KEYS,
    TEMPLATE_BLUEPRINTS,
    canonical_template_key,
)
from tests.conftest import API, Session


def test_chi_cho_nghi_mau_co_that_va_khong_dung_mau_mien_phi() -> None:
    keys = {item.key for item in TEMPLATE_BLUEPRINTS}
    assert set(RETIRED_KEYS) <= keys
    assert not set(RETIRED_KEYS) & FREE_KEYS
    assert DEFAULT_TEMPLATE_KEY not in RETIRED_KEYS
    assert all(reason.strip() for reason in RETIRED_KEYS.values())


def test_catalog_cong_khai_chi_con_bo_doc_ban_tu_tao() -> None:
    alive = {item.key for item in TEMPLATE_BLUEPRINTS if item.key not in RETIRED_KEYS}
    assert alive == set(ORIGINAL_TEMPLATE_KEYS)
    assert alive == FREE_KEYS


def test_moi_khoa_cu_co_mau_doc_ban_thay_the() -> None:
    assert set(LEGACY_TEMPLATE_REPLACEMENTS) == set(RETIRED_KEYS)
    assert set(LEGACY_TEMPLATE_REPLACEMENTS.values()) <= set(ORIGINAL_TEMPLATE_KEYS)
    assert canonical_template_key("songhy") in ORIGINAL_TEMPLATE_KEYS
    assert canonical_template_key("dbgomlam") == "dbgomlam"


async def test_khach_khong_thay_mau_nghi_quan_tri_van_thay(
    client: AsyncClient, admin: Session, customer: Session
) -> None:
    seen_by_customer = await client.get(f"{API}/templates", headers=customer.headers)
    seen_by_admin = await client.get(f"{API}/templates", headers=admin.headers)
    customer_ids = {item["id"] for item in seen_by_customer.json()["data"]}
    admin_rows = {item["id"]: item for item in seen_by_admin.json()["data"]}
    assert not customer_ids & set(RETIRED_KEYS)
    assert all(admin_rows[key]["is_active"] is False for key in RETIRED_KEYS)


async def test_bat_lai_thi_seed_khong_tat_lan_nua(client: AsyncClient, admin: Session) -> None:
    on = await client.patch(
        f"{API}/templates/vogue", json={"is_active": True}, headers=admin.headers
    )
    assert on.status_code == 200
    await build_ensure_catalog().execute()
    rows = (await client.get(f"{API}/templates", headers=admin.headers)).json()["data"]
    assert next(row for row in rows if row["id"] == "vogue")["is_active"] is True
