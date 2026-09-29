"""Mẫu cho nghỉ: khách không chọn được nữa, nhưng không bị xoá và bật lại được."""

from __future__ import annotations

from httpx import AsyncClient

from app.modules.template import build_ensure_catalog
from app.modules.template.domain.catalog import (
    DEFAULT_TEMPLATE_KEY,
    FREE_KEYS,
    RETIRED_KEYS,
    TEMPLATE_BLUEPRINTS,
)
from tests.conftest import API, Session


def test_chi_cho_nghi_mau_co_that_va_khong_dung_mau_mien_phi() -> None:
    keys = {item.key for item in TEMPLATE_BLUEPRINTS}
    assert set(RETIRED_KEYS) <= keys
    assert not set(RETIRED_KEYS) & FREE_KEYS
    assert DEFAULT_TEMPLATE_KEY not in RETIRED_KEYS
    assert all(reason.strip() for reason in RETIRED_KEYS.values())


def test_moi_dong_mau_van_con_mau_de_chon() -> None:
    families = {item.family for item in TEMPLATE_BLUEPRINTS}
    alive = {item.family for item in TEMPLATE_BLUEPRINTS if item.key not in RETIRED_KEYS}
    assert alive == families


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
