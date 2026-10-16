"""Các chốt chặn trước khi lên production: gói sau khi xuất bản, cấu hình không an toàn."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.core.config import Environment, Settings
from tests.conftest import API, Session

SECRET = "x" * 40


def _content(wedding: dict[str, Any]) -> dict[str, Any]:
    meta = {"id", "slug", "published", "site_url", "checklist", "updated_at"}
    return {key: value for key, value in wedding.items() if key not in meta}


async def _publish_free(client: AsyncClient, session: Session) -> dict[str, Any]:
    created = await client.post(
        f"{API}/wedding/setup", json={"mode": "blank"}, headers=session.headers
    )
    content = _content(created.json()["data"])
    content["default_template"] = "songhy"
    content["group_templates"] = {}
    content["gift"]["show"] = False
    assert (await client.put(f"{API}/wedding", json=content, headers=session.headers)).is_success
    published = await client.put(
        f"{API}/wedding/publication",
        json={"slug": "thiep-mien-phi", "published": True},
        headers=session.headers,
    )
    assert published.status_code == 200, published.text
    return content


async def test_thiep_dang_xuat_ban_khong_sua_vuot_goi(
    client: AsyncClient, customer: Session
) -> None:
    content = await _publish_free(client, customer)
    content["gift"]["show"] = True
    content["theme"] = {"accent": "#B8323F"}
    blocked = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "plan_required"

    content["gift"]["show"] = False
    content["theme"] = {}
    content["story"] = "Chúng mình gặp nhau năm 2019."
    ok = await client.put(f"{API}/wedding", json=content, headers=customer.headers)
    assert ok.status_code == 200, "sửa trong gói vẫn lưu được"


async def test_thiep_dang_xuat_ban_khong_them_khach_vuot_goi(
    client: AsyncClient, customer: Session
) -> None:
    await _publish_free(client, customer)
    lines = "\n".join(f"Bạn | Khách {index}" for index in range(50))
    imported = await client.post(
        f"{API}/guests/import", json={"text": lines}, headers=customer.headers
    )
    assert imported.status_code in (200, 201), imported.text
    extra = await client.post(f"{API}/guests", json={"name": "Thêm"}, headers=customer.headers)
    assert extra.status_code == 409
    assert extra.json()["code"] == "plan_required"


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "ENV": Environment.PRODUCTION,
        "JWT_SECRET": SECRET,
        "S3_ACCESS_KEY": "ops",
        "S3_SECRET_KEY": SECRET,
        "SUPPORT_ZALO_PHONE": "0987000111",
        "PAYMENT_SANDBOX": False,
        "AUTO_SEED": False,
        "BANK_WEBHOOK_KEY": "",
    }
    return Settings(**{**base, **overrides})


def test_mac_dinh_la_production() -> None:
    assert Settings.model_fields["ENV"].default is Environment.PRODUCTION


@pytest.mark.parametrize(
    "overrides",
    [
        {"S3_SECRET_KEY": "wedding-local-secret"},
        {"S3_ACCESS_KEY": ""},
        {"BANK_WEBHOOK_KEY": "local-dev-webhook-key"},
        {"BANK_WEBHOOK_KEY": "ngan"},
        {"AUTO_SEED": True},
        {"SUPPORT_ZALO_PHONE": "0912345678"},
        {"MOMO_PARTNER_CODE": "MOMO", "MOMO_ENDPOINT": "https://test-payment.momo.vn/x"},
    ],
)
def test_production_tu_choi_cau_hinh_dev(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="Cấu hình chưa sẵn sàng"):
        _settings(**overrides)


def test_production_cau_hinh_du() -> None:
    assert _settings(BANK_WEBHOOK_KEY="k" * 40).ENV is Environment.PRODUCTION


def test_thiep_cong_khai_chi_gom_truong_cho_phep() -> None:
    from app.modules.invitation.domain.services import public_wedding

    snapshot = {
        "groom": {"short": "Hoàng"},
        "messages": {"family": "ghi chú riêng"},
        "group_templates": {"Họ hàng": "songhy"},
        "truong_moi_chua_khai": "bí mật",
        "gift": {"show": False},
    }
    data = public_wedding(snapshot)
    assert set(data) == {"groom", "gift"}


async def test_cache_thiep_cong_khai_xoa_ngay_khi_sua(
    client: AsyncClient, customer: Session
) -> None:
    content = await _publish_free(client, customer)
    base = f"{API}/public/invitations/thiep-mien-phi"
    first = (await client.get(base)).json()["data"]["wedding"]
    assert first["story"] != "Chuyện mới"

    content["story"] = "Chuyện mới"
    assert (await client.put(f"{API}/wedding", json=content, headers=customer.headers)).is_success
    assert (await client.get(base)).json()["data"]["wedding"]["story"] == "Chuyện mới"

    await client.put(
        f"{API}/wedding/publication",
        json={"slug": "thiep-mien-phi", "published": False},
        headers=customer.headers,
    )
    assert (await client.get(base)).status_code == 404, "tắt xuất bản là tắt ngay"


async def test_them_khach_song_song_khong_vuot_han_muc(
    client: AsyncClient, customer: Session
) -> None:
    """Hai lượt nhập nhanh cùng lúc: tổng không được vượt hạn mức gói khi đang xuất bản."""
    import asyncio

    await _publish_free(client, customer)
    batch = "\n".join(f"Bạn | Khách {index}" for index in range(30))
    results = await asyncio.gather(
        *[
            client.post(f"{API}/guests/import", json={"text": batch}, headers=customer.headers)
            for _ in range(2)
        ]
    )
    # Cả hai cùng ghi rồi mới đếm lại thì có thể cả hai tự gỡ (409) — vẫn đúng cam kết:
    # tổng không bao giờ vượt hạn mức. Thử lại một lượt là qua.
    assert {item.status_code for item in results} <= {200, 201, 409}
    guests = (await client.get(f"{API}/guests?per_page=500", headers=customer.headers)).json()
    assert len(guests["data"]) <= 50, "gói Miễn phí tối đa 50 thiệp khi đang xuất bản"


async def test_nhap_nhanh_hang_loat(client: AsyncClient, customer: Session) -> None:
    await client.post(f"{API}/wedding/setup", json={"mode": "blank"}, headers=customer.headers)
    batch = "\n".join(f"Bạn | Khách {index} | | Bạn bè | gái | 2" for index in range(300))
    imported = await client.post(
        f"{API}/guests/import", json={"text": batch}, headers=customer.headers
    )
    assert imported.status_code in (200, 201), imported.text
    guests = (await client.get(f"{API}/guests?per_page=500", headers=customer.headers)).json()
    codes = {item["code"] for item in guests["data"]}
    assert len(codes) == 300, "mỗi khách một mã riêng"
    assert all(item["count"] == 2 for item in guests["data"])
