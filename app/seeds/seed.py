"""Nạp dữ liệu mẫu cho local — idempotent, chạy lần hai là `{"noop": true}`.

Hai tài khoản demo, đúng hai vai trò của sản phẩm:

| Vai trò          | Đăng nhập                 | Mật khẩu      |
|------------------|---------------------------|---------------|
| Quản trị viên    | admin@thiephy.vn          | Admin@2026    |
| Khách dùng mẫu   | 0912345678 / demo@...     | Demo@2026     |

Tài khoản khách demo có sẵn Gói Lộng Lẫy và đám cưới mẫu Huy Hoàng & Hải Hà (đã xuất bản tại
`/invite/h-hoang-ha`) cùng 10 khách mẫu của thiết kế.

**Chỉ chạy ở `local`/`test`** — hai lớp chặn (`ensure_seedable` + entrypoint):
seed ghi bằng khoá tự nhiên cố định, chạy nhầm ở môi trường thật là trộn dữ liệu
giả vào dữ liệu thật.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Final

from app.core.base_model import new_id
from app.core.config import Environment, get_settings
from app.core.context import ActorContext
from app.core.database import close_database, init_database
from app.core.logging import get_logger
from app.core.permissions import all_slugs
from app.core.redis import close_redis
from app.modules.access import ADMIN_ROLE_SLUG, CUSTOMER_ROLE_SLUG, build_ensure_default_roles
from app.modules.billing import build_plan_granter
from app.modules.identity import build_account_provisioner
from app.modules.template import build_ensure_catalog
from app.modules.wedding import build_demo_wedding_seeder

log = get_logger(__name__)

#: Khoá tự nhiên cố định — chạy lại không sinh bản ghi mới.
OPS_STUDIO_ID: Final = uuid.UUID("01930000-0000-7000-8000-00000000a001")
ADMIN_USER_ID: Final = uuid.UUID("01930000-0000-7000-8000-00000000a002")
DEMO_STUDIO_ID: Final = uuid.UUID("01930000-0000-7000-8000-00000000b001")
DEMO_USER_ID: Final = uuid.UUID("01930000-0000-7000-8000-00000000b002")

ADMIN_PASSWORD: Final = "Admin@2026"
DEMO_PASSWORD: Final = "Demo@2026"


class SeedRefusedError(RuntimeError):
    """Seed bị gọi ở môi trường không cho phép."""


def ensure_seedable() -> None:
    """Chốt chặn thứ nhất: chỉ `local`/`test`."""
    env = get_settings().ENV
    if env not in {Environment.LOCAL, Environment.TEST}:
        message = f"Từ chối seed ở môi trường {env}. Seed chỉ chạy ở local/test."
        raise SeedRefusedError(message)


async def ensure_admin() -> Any:
    """Tài khoản quản trị demo (vai trò phải có sẵn). Dùng riêng được trong test."""
    ensure_seedable()
    return await build_account_provisioner().ensure(
        studio_id=OPS_STUDIO_ID,
        studio_name="Vận hành Xưởng Thiệp Hỷ",
        user_id=ADMIN_USER_ID,
        full_name="Quản trị hệ thống",
        email="admin@thiephy.vn",
        phone=None,
        password=ADMIN_PASSWORD,
        role_slug=ADMIN_ROLE_SLUG,
    )


async def run_seed() -> dict[str, Any]:
    """Nạp vai trò, bộ mẫu, hai tài khoản demo và đám cưới mẫu."""
    ensure_seedable()
    roles = await build_ensure_default_roles().execute()
    templates_created = await build_ensure_catalog().execute()

    provisioner = build_account_provisioner()
    admin = await ensure_admin()
    demo = await provisioner.ensure(
        studio_id=DEMO_STUDIO_ID,
        studio_name="Xưởng thiệp của Trần Huy Hoàng",
        user_id=DEMO_USER_ID,
        full_name="Trần Huy Hoàng",
        email="demo@thiephy.vn",
        phone="0912345678",
        password=DEMO_PASSWORD,
        role_slug=CUSTOMER_ROLE_SLUG,
    )
    demo_actor = ActorContext(
        user_id=DEMO_USER_ID,
        tenant_id=DEMO_STUDIO_ID,
        permissions=frozenset(all_slugs()),
        session_id=new_id(),
    )
    # Đám cưới mẫu dùng mẫu hoạt hình 3D (Gói Lộng Lẫy): cấp gói TRƯỚC khi xuất
    # bản, vì seed đi qua đúng luồng xét gói của người dùng thật.
    plan_granted = await build_plan_granter().grant(
        DEMO_STUDIO_ID, "premium", actor_id=DEMO_USER_ID, note="Tài khoản demo"
    )
    wedding_created = await build_demo_wedding_seeder().ensure(demo_actor, slug="h-hoang-ha")
    # Xưởng của đội vận hành: dùng mọi mẫu / thiết kế tự do để soạn thử như khách.
    ops_plan_granted = await build_plan_granter().grant(
        OPS_STUDIO_ID, "premium", actor_id=ADMIN_USER_ID, note="Xưởng vận hành"
    )

    changed = (
        templates_created > 0
        or admin.created
        or demo.created
        or plan_granted
        or ops_plan_granted
        or wedding_created
    )
    summary: dict[str, Any] = {
        "noop": not changed,
        "roles": [role.slug for role in roles],
        "templates_created": templates_created,
        "admin_created": admin.created,
        "demo_created": demo.created,
        "plan_granted": plan_granted,
        "wedding_created": wedding_created,
    }
    log.info("seed_done", **summary)
    return summary


async def _main() -> None:
    await init_database()
    try:
        summary = await run_seed()
    finally:
        await close_redis()
        await close_database()
    log.info("seed_summary", summary=json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(_main())
