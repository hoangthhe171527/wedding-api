"""Luồng xác thực đầu-cuối qua HTTP: đăng ký, đăng nhập, me, refresh, đăng xuất."""

from __future__ import annotations

from httpx import AsyncClient

from app.modules.identity.application.use_cases.login_user import INVALID_CREDENTIALS_MESSAGE
from tests.conftest import API, Session, login, register


async def test_dang_ky_cap_vai_tro_khach_dung_mau(client: AsyncClient) -> None:
    session = await register(client, email="Hoang@Example.com")
    assert session.actor["user"]["email"] == "hoang@example.com"
    assert set(session.actor["permissions"]) == {"guest.manage", "studio.manage", "template.view"}

    me = await client.get(f"{API}/auth/me", headers=session.headers)
    assert me.status_code == 200
    assert me.json()["data"]["studio"]["name"].startswith("Xưởng thiệp của")


async def test_dang_ky_trung_email_tra_409(client: AsyncClient, customer: Session) -> None:
    response = await client.post(
        f"{API}/auth/register",
        json={"full_name": "Ai Đó", "email": "COUPLEA@example.com", "password": "matkhau123"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "identifier_taken"


async def test_dang_ky_mat_khau_yeu_bi_tu_choi(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/auth/register",
        json={"full_name": "Ai Đó", "email": "x@example.com", "password": "chicochu"},
    )
    assert response.status_code == 400
    assert "password" in response.json()["errors"]


async def test_dang_ky_can_email_hoac_so_dien_thoai(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/auth/register", json={"full_name": "Ai Đó", "password": "matkhau123"}
    )
    assert response.status_code == 400


async def test_dang_nhap_bang_so_dien_thoai_moi_dinh_dang(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/auth/register",
        json={"full_name": "Hải Hà", "phone": "+84 987 654 321", "password": "matkhau123"},
    )
    assert response.status_code == 201
    session = await login(client, "0987.654.321", "matkhau123")
    assert session.actor["user"]["phone"] == "0987654321"


async def test_sai_mat_khau_va_sai_tai_khoan_cung_mot_cau(
    client: AsyncClient, customer: Session
) -> None:
    wrong_password = await client.post(
        f"{API}/auth/login", json={"identifier": "coupleA@example.com", "password": "saibet123"}
    )
    no_account = await client.post(
        f"{API}/auth/login", json={"identifier": "khongco@example.com", "password": "saibet123"}
    )
    assert wrong_password.status_code == no_account.status_code == 401
    assert wrong_password.json() == no_account.json()
    assert wrong_password.json()["message"] == INVALID_CREDENTIALS_MESSAGE


async def test_thieu_token_tra_401_tieng_viet(client: AsyncClient) -> None:
    response = await client.get(f"{API}/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "missing_token"


async def test_refresh_xoay_vong_va_bat_dung_lai(client: AsyncClient, customer: Session) -> None:
    first = await client.post(f"{API}/auth/refresh", json={"refresh_token": customer.refresh_token})
    assert first.status_code == 200
    rotated = first.json()["data"]
    assert rotated["refresh_token"] != customer.refresh_token

    # Dùng lại token cũ = dấu hiệu trộm: mọi phiên bị cắt, kể cả phiên vừa xoay.
    reused = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": customer.refresh_token}
    )
    assert reused.status_code == 401
    assert reused.json()["code"] == "refresh_token_reused"

    after = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
    )
    assert after.status_code == 401
    me = await client.get(
        f"{API}/auth/me", headers={"Authorization": f"Bearer {rotated['access_token']}"}
    )
    assert me.status_code == 401


async def test_dang_xuat_giet_access_token_ngay(client: AsyncClient, customer: Session) -> None:
    out = await client.post(
        f"{API}/auth/logout",
        json={"refresh_token": customer.refresh_token},
        headers=customer.headers,
    )
    assert out.status_code == 200
    me = await client.get(f"{API}/auth/me", headers=customer.headers)
    assert me.status_code == 401
    assert me.json()["code"] == "token_revoked"
    refresh = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": customer.refresh_token}
    )
    assert refresh.status_code == 401


async def test_tai_khoan_tu_xoa_duoc_toan_bo_du_lieu(
    client: AsyncClient, customer: Session
) -> None:
    wrong = await client.request(
        "DELETE",
        f"{API}/auth/account",
        json={"password": "sai-mat-khau"},
        headers=customer.headers,
    )
    assert wrong.status_code == 400
    assert wrong.json()["code"] == "wrong_password"

    deleted = await client.request(
        "DELETE",
        f"{API}/auth/account",
        json={"password": "matkhau123"},
        headers=customer.headers,
    )
    assert deleted.status_code == 200, deleted.text
    assert (await client.get(f"{API}/auth/me", headers=customer.headers)).status_code == 401
    login_again = await client.post(
        f"{API}/auth/login",
        json={"identifier": "coupleA@example.com", "password": "matkhau123"},
    )
    assert login_again.status_code == 401


async def test_doi_mat_khau_cat_thiet_bi_khac_giu_thiet_bi_nay(
    client: AsyncClient, customer: Session
) -> None:
    other_device = await login(client, "coupleA@example.com", "matkhau123")
    changed = await client.post(
        f"{API}/auth/change-password",
        json={"current_password": "matkhau123", "new_password": "matkhaumoi456"},
        headers=customer.headers,
    )
    assert changed.status_code == 200
    assert (await client.get(f"{API}/auth/me", headers=customer.headers)).status_code == 200
    assert (await client.get(f"{API}/auth/me", headers=other_device.headers)).status_code == 401
    await login(client, "coupleA@example.com", "matkhaumoi456")


async def test_khoa_tai_khoan_cat_phien_va_chan_dang_nhap(
    client: AsyncClient, admin: Session, customer: Session
) -> None:
    user_id = customer.actor["user"]["id"]
    locked = await client.patch(
        f"{API}/admin/users/{user_id}/status", json={"is_active": False}, headers=admin.headers
    )
    assert locked.status_code == 200
    assert (await client.get(f"{API}/auth/me", headers=customer.headers)).status_code == 401
    denied = await client.post(
        f"{API}/auth/login", json={"identifier": "coupleA@example.com", "password": "matkhau123"}
    )
    assert denied.status_code == 401
    assert denied.json()["code"] == "account_disabled"


async def test_admin_khong_tu_khoa_duoc_minh(client: AsyncClient, admin: Session) -> None:
    response = await client.patch(
        f"{API}/admin/users/{admin.actor['user']['id']}/status",
        json={"is_active": False},
        headers=admin.headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "self_lock"


async def test_gioi_han_dang_nhap_khong_lach_bang_cach_viet_so(client: AsyncClient) -> None:
    """Mọi cách viết cùng một số điện thoại dùng CHUNG một bộ đếm."""
    await client.post(
        f"{API}/auth/register",
        json={"full_name": "Nạn Nhân", "phone": "0987654321", "password": "MatKhau@2026"},
    )
    variants = ["0987654321", "0987 654 321", "+84987654321", "84987654321", "(0987)654.321"]
    statuses = []
    for index in range(10):
        response = await client.post(
            f"{API}/auth/login",
            json={"identifier": variants[index % len(variants)], "password": "sai-mat-khau"},
        )
        statuses.append(response.status_code)
    assert 429 in statuses, statuses


async def test_dang_nhap_dung_khong_xoa_bo_dem_ip(client: AsyncClient, customer: Session) -> None:
    """Xen lần đăng nhập đúng tài khoản của mình không làm bộ đếm IP về 0."""
    statuses = []
    for index in range(30):
        if index % 5 == 4:
            await client.post(
                f"{API}/auth/login",
                json={"identifier": "coupleA@example.com", "password": "matkhau123"},
            )
            continue
        response = await client.post(
            f"{API}/auth/login",
            json={"identifier": f"nguoi{index}@example.com", "password": "sai"},
        )
        statuses.append(response.status_code)
    assert 429 in statuses, statuses


async def test_refresh_token_nam_trong_cookie_httponly(
    client: AsyncClient, customer: Session
) -> None:
    logged = await client.post(
        f"{API}/auth/login",
        json={"identifier": "coupleA@example.com", "password": "matkhau123"},
    )
    cookie = logged.headers["set-cookie"]
    assert "wedding_refresh=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/api/v1/auth" in cookie

    # Web chỉ gửi cookie, không gửi token trong thân yêu cầu.
    refreshed = await client.post(f"{API}/auth/refresh", json={})
    assert refreshed.status_code == 200, refreshed.text
    access = refreshed.json()["data"]["access_token"]

    out = await client.post(
        f"{API}/auth/logout", json={}, headers={"Authorization": f"Bearer {access}"}
    )
    assert out.status_code == 200
    assert (
        'wedding_refresh=""' in out.headers["set-cookie"]
        or "Max-Age=0" in out.headers["set-cookie"]
    )
    client.cookies.clear()
    missing = await client.post(f"{API}/auth/refresh", json={})
    assert missing.status_code == 401
