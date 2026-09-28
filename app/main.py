"""Điểm vào ứng dụng FastAPI.

Router của từng module được nạp qua `app.modules.<name>` — mỗi module bắt buộc
export biến `router` (APIRouter) trong `__init__.py` của mình.

Nạp mềm có chủ ý: module chưa dựng xong không làm chết cả ứng dụng, chỉ ghi cảnh
báo. Đặt `STRICT_MODULE_IMPORT=1` để bắt lỗi ngay — CI và production dùng cờ này.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Final

from fastapi import APIRouter, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.database import close_database, init_database, ping
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import AccessLogMiddleware, RequestContextMiddleware
from app.core.observability import init_observability
from app.core.redis import close_redis, redis_healthy
from app.core.storage import get_object_store
from app.models_registry import MODULE_NAMES, collection_names
from app.modules.access import build_ensure_default_roles
from app.modules.template import build_ensure_catalog

log = get_logger(__name__)

STRICT_MODULE_IMPORT: Final[bool] = os.environ.get("STRICT_MODULE_IMPORT", "").lower() in {
    "1",
    "true",
    "yes",
}

#: Origin được chấp nhận khi chạy local: mọi cổng của localhost, kể cả dạng IPv6.
#: Liệt kê cứng từng cổng là chắc chắn có lúc quên, và triệu chứng rất khó đoán —
#: đăng nhập hỏng mà server không ghi lỗi nào, vì trình duyệt chặn ở preflight.
LOCAL_CORS_ORIGIN_REGEX: Final[str] = (
    r"http://(localhost|127\.0\.0\.1|\[::1\]|\[0:0:0:0:0:0:0:1\])(:\d+)?"
)


def _load_module_routers() -> list[tuple[str, APIRouter]]:
    """Import `app.modules.<name>` và lấy biến `router` của từng module."""
    routers: list[tuple[str, APIRouter]] = []
    for name in MODULE_NAMES:
        path = f"app.modules.{name}"
        try:
            module = importlib.import_module(path)
        except ModuleNotFoundError as exc:
            if STRICT_MODULE_IMPORT:
                raise
            log.warning("module_missing", module=path, reason=str(exc))
            continue

        router = getattr(module, "router", None)
        if router is None:
            if STRICT_MODULE_IMPORT:
                message = f"Module {path} không export biến `router`."
                raise RuntimeError(message)
            log.warning("module_without_router", module=path)
            continue
        routers.append((name, router))
    return routers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Khởi động và tắt: nối Mongo + tạo index, dọn tài nguyên."""
    cfg: Settings = get_settings()
    log.info("app_starting", env=str(cfg.ENV), modules=list(MODULE_NAMES))
    await init_database()
    log.info("collections_ready", collections=list(collection_names()))
    await get_object_store().ensure_bucket()
    # Dữ liệu nền (idempotent, chỉ bổ sung): vai trò mặc định + bộ mẫu. Mọi môi
    # trường cần chúng — thiếu là khách đăng ký nhận 503. Tài khoản admin đầu tiên
    # tạo bằng `python -m app.seeds.bootstrap_admin`, không tạo ở đây.
    await build_ensure_default_roles().execute()
    await build_ensure_catalog().execute()
    yield
    await close_redis()
    await close_database()
    log.info("app_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Dựng ứng dụng. Test gọi trực tiếp hàm này để có instance sạch."""
    cfg = settings or get_settings()
    configure_logging(cfg)
    init_observability(cfg)

    app = FastAPI(
        title="wedding API — Xưởng Thiệp Hỷ",
        description=(
            "API soạn thiệp cưới theo bộ mẫu: thông tin cưới, ảnh, khách mời, "
            "xuất bản web thiệp có link riêng từng khách."
        ),
        version="0.1.0",
        # Bản đồ endpoint (kể cả webhook, màn quản trị) chỉ mở ở máy dev.
        docs_url="/docs" if cfg.is_local else None,
        redoc_url="/redoc" if cfg.is_local else None,
        openapi_url="/openapi.json" if cfg.is_local else None,
        lifespan=lifespan,
    )

    cors: dict[str, Any] = {
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "expose_headers": ["X-Request-ID"],
    }
    if cfg.is_local:
        cors["allow_origin_regex"] = LOCAL_CORS_ORIGIN_REGEX
    else:
        cors["allow_origins"] = cfg.CORS_ORIGINS
    app.add_middleware(CORSMiddleware, **cors)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    api = APIRouter(prefix=cfg.API_PREFIX)
    for name, router in _load_module_routers():
        api.include_router(router)
        log.info("module_registered", module=name)
    app.include_router(api)

    @app.get("/health", tags=["health"], summary="Kiểm tra sức khoẻ")
    async def health(response: Response) -> dict[str, Any]:
        """Probe **readiness**: suy giảm thì trả 503, không phải 200.

        Bộ cân tải đọc mã trạng thái chứ không đọc thân — endpoint sức khoẻ luôn
        trả 200 thì không phải endpoint sức khoẻ.
        """
        mongo_ok = await ping()
        redis_ok = await redis_healthy()
        storage_ok = await get_object_store().healthy()
        # Redis hỏng thì hệ vẫn phục vụ được (thu hồi phiên và đếm tần suất đều
        # mở khi hỏng), nên chỉ Mongo và kho ảnh quyết định sẵn sàng hay không.
        # Kho ảnh hỏng thì web thiệp mất ảnh và không tải ảnh lên được: coi là chưa sẵn sàng.
        if not mongo_ok or not storage_ok:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            log.error("health_degraded", database=mongo_ok, redis=redis_ok, storage=storage_ok)
        return {
            "status": "ok" if mongo_ok and storage_ok else "degraded",
            "app": cfg.APP_NAME,
            "env": str(cfg.ENV),
            "dependencies": {"database": mongo_ok, "redis": redis_ok, "storage": storage_ok},
        }

    @app.get("/health/live", tags=["health"], summary="Kiểm tra tiến trình còn sống")
    async def liveness() -> dict[str, str]:
        """Liveness: chỉ xác nhận tiến trình còn phục vụ được, không kiểm phụ thuộc."""
        return {"status": "ok"}

    return app


app = create_app()

__all__ = ["app", "create_app", "lifespan"]
