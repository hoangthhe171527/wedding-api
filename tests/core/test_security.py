"""Nguyên thuỷ bảo mật: token, chữ ký URL, mật khẩu."""

from __future__ import annotations

import time
import uuid

import jwt
import pytest

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.security import signing
from app.core.security.password import hash_password, verify_password
from app.core.security.tokens import (
    decode_access_token,
    encode_access_token,
    generate_refresh_token,
    verify_refresh_token,
)


def test_access_token_khu_hoi_giu_nguyen_claim() -> None:
    user_id, tenant_id = uuid.uuid4(), uuid.uuid4()
    issued = encode_access_token(
        user_id=user_id, tenant_id=tenant_id, permissions={"guest.manage", "studio.manage"}
    )
    claims = decode_access_token(issued.token)
    assert claims.user_id == user_id
    assert claims.tenant_id == tenant_id
    assert claims.session_id == issued.session_id
    assert claims.permissions == frozenset({"guest.manage", "studio.manage"})


def test_slug_quyen_la_trong_token_khong_cap_duoc_gi() -> None:
    issued = encode_access_token(
        user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), permissions={"superuser.everything"}
    )
    assert decode_access_token(issued.token).permissions == frozenset()


def test_token_bi_sua_bi_tu_choi() -> None:
    issued = encode_access_token(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), permissions=set())
    payload = jwt.decode(issued.token, options={"verify_signature": False})
    payload["perms"] = ["user.manage"]
    forged = jwt.encode(payload, "khoa-cua-ke-gia-mao-dai-hon-32-ky-tu!!", algorithm="HS256")
    with pytest.raises(UnauthorizedError) as caught:
        decode_access_token(forged)
    assert caught.value.code == "token_invalid"


def test_token_het_han_bi_tu_choi() -> None:
    cfg = get_settings()
    now = int(time.time())
    expired = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "jti": str(uuid.uuid4()),
            "iss": cfg.JWT_ISSUER,
            "iat": now - 3600,
            "exp": now - 60,
        },
        cfg.JWT_SECRET,
        algorithm="HS256",
    )
    with pytest.raises(UnauthorizedError) as caught:
        decode_access_token(expired)
    assert caught.value.code == "token_expired"


def test_refresh_token_chi_luu_ban_bam() -> None:
    issued = generate_refresh_token()
    assert issued.raw not in issued.hashed
    assert verify_refresh_token(issued.raw, issued.hashed)
    assert not verify_refresh_token(issued.raw + "x", issued.hashed)


def test_chu_ky_url_dung_moi_qua() -> None:
    exp, sig = signing.sign("photo", "abc", ttl_seconds=60)
    assert signing.verify("photo", "abc", expires_at=exp, signature=sig)
    assert not signing.verify("photo", "abd", expires_at=exp, signature=sig)
    assert not signing.verify("other", "abc", expires_at=exp, signature=sig)
    assert not signing.verify("photo", "abc", expires_at=exp + 1, signature=sig)


def test_chu_ky_url_het_han_bi_tu_choi() -> None:
    exp, sig = signing.sign("photo", "abc", ttl_seconds=10, now=time.time() - 100)
    assert not signing.verify("photo", "abc", expires_at=exp, signature=sig)


def test_mat_khau_bam_argon2() -> None:
    hashed = hash_password("matkhau123")
    assert hashed.startswith("$argon2id$")
    assert verify_password("matkhau123", hashed)
    assert not verify_password("matkhau124", hashed)
