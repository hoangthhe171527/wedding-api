"""Module `identity` — xưởng thiệp (tenant), người dùng, phiên đăng nhập.

Sở hữu `studios`, `users`, `auth_sessions`. Đây là cửa vào duy nhất của hệ thống:
mọi actor của mọi module khác đều sinh ra từ access token do module này phát.

Vai trò (admin / khách dùng mẫu) KHÔNG xuất hiện ở đây — chúng là dữ liệu của
`access`. `identity` chỉ hỏi `access` qua cổng.
"""

from fastapi import APIRouter

from app.modules.identity.infrastructure.external.accounts import build_account_provisioner
from app.modules.identity.infrastructure.external.studios import build_studio_directory
from app.modules.identity.interfaces.http.admin_router import router as admin_router
from app.modules.identity.interfaces.http.router import router as auth_router

#: Module chỉ export MỘT `router`; hai nhóm đường dẫn gộp ở đây.
router = APIRouter()
router.include_router(auth_router)
router.include_router(admin_router)

__all__ = ["build_account_provisioner", "build_studio_directory", "router"]
