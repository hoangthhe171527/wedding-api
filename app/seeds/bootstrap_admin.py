"""Tạo tài khoản quản trị ĐẦU TIÊN — dùng được ở mọi môi trường, kể cả production.

    docker compose exec api python -m app.seeds.bootstrap_admin --email ops@ten-mien.vn

Mật khẩu đọc từ biến `BOOTSTRAP_ADMIN_PASSWORD` hoặc nhập tay (không hiện lên màn
hình) — không bao giờ nằm trong mã nguồn như tài khoản demo của seed. Chạy lại với
cùng email là idempotent: id suy ra từ email, không tạo trùng.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
import uuid

from app.core.database import close_database, init_database
from app.core.redis import close_redis
from app.modules.access import ADMIN_ROLE_SLUG, build_ensure_default_roles
from app.modules.identity import build_account_provisioner

MIN_LENGTH = 12
_NAMESPACE = uuid.UUID("5b0d8a4e-3c55-4f0e-9a51-7d1b8b2f6a10")


def _password() -> str:
    value = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD") or getpass.getpass("Mật khẩu admin: ")
    if len(value) < MIN_LENGTH:
        sys.exit(f"Mật khẩu phải dài tối thiểu {MIN_LENGTH} ký tự.")
    return value


async def bootstrap(email: str, name: str, password: str) -> bool:
    await build_ensure_default_roles().execute()
    account = await build_account_provisioner().ensure(
        studio_id=uuid.uuid5(_NAMESPACE, f"studio:{email}"),
        studio_name="Vận hành Xưởng Thiệp Hỷ",
        user_id=uuid.uuid5(_NAMESPACE, f"user:{email}"),
        full_name=name,
        email=email,
        phone=None,
        password=password,
        role_slug=ADMIN_ROLE_SLUG,
    )
    return account.created


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Tạo tài khoản quản trị đầu tiên.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Quản trị hệ thống")
    args = parser.parse_args()
    password = _password()
    await init_database()
    try:
        created = await bootstrap(args.email.strip().lower(), args.name, password)
    finally:
        await close_redis()
        await close_database()
    message = "Đã tạo tài khoản quản trị." if created else "Tài khoản đã có — giữ mật khẩu cũ."
    sys.stdout.write(f"{message}\n")


if __name__ == "__main__":
    asyncio.run(_main())
