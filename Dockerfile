# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# wedding-api — cùng khuôn image với ad-tracker-api.
#
#   dev  (mặc định của docker-compose.yml): kèm ruff/mypy/pytest và tests. Máy dev
#        không cài Python: mọi lệnh (api, test, lint, seed) chạy trong image này.
#   prod: docker build --target prod -t wedding-api .
#        Không công cụ dev, không tests; module / model import lỗi là DỪNG khởi động.
# ---------------------------------------------------------------------------

FROM python:3.12-slim-bookworm AS base

# Bytecode đẩy sang một cây riêng ngoài bind mount: đọc/ghi qua mount từ Windows
# chậm hơn hệ tệp container cả chục lần (xem giải thích đầy đủ ở ad-tracker-api).
ENV PYTHONUNBUFFERED=1 \
    PYTHONPYCACHEPREFIX=/var/cache/pycache \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# curl cho healthcheck; libjpeg/zlib/libwebp cho Pillow đọc ảnh cưới.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libjpeg62-turbo \
        zlib1g \
        libwebp7 \
    && rm -rf /var/lib/apt/lists/*

# Ghim phiên bản uv: tag trôi (0.5) có thể đổi cách resolve giữa hai lần build.
COPY --from=ghcr.io/astral-sh/uv:0.5.31 /uv /uvx /usr/local/bin/

WORKDIR /app

# Người dùng thường; thư mục cache phải thuộc về appuser NGAY TRONG IMAGE để
# volume rỗng gắn vào thừa hưởng đúng quyền sở hữu.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /var/cache/pycache \
    && chown -R appuser:appuser /app /var/cache/pycache

# ---------------------------------------------------------------------------
# Phụ thuộc: `--locked` — uv.lock phải có và khớp pyproject, không resolve lại.
# ---------------------------------------------------------------------------
FROM base AS deps-prod
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

FROM base AS deps-dev
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --group dev

# ---------------------------------------------------------------------------
# prod
# ---------------------------------------------------------------------------
FROM base AS prod
COPY --from=deps-prod /opt/venv /opt/venv
ENV STRICT_MODULE_IMPORT=1 \
    STRICT_MODEL_IMPORT=1
COPY --chown=appuser:appuser pyproject.toml ./
COPY --chown=appuser:appuser app ./app
COPY docker/entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -fsS http://localhost:8000/health/live || exit 1
ENTRYPOINT ["entrypoint"]
CMD ["api"]

# ---------------------------------------------------------------------------
# dev — để CUỐI để `docker build .` không target vẫn ra image dev như trước.
# ---------------------------------------------------------------------------
FROM base AS dev
COPY --from=deps-dev /opt/venv /opt/venv
# Cấu hình ruff/mypy/pytest nằm trong pyproject nên phải có mặt trong image.
COPY --chown=appuser:appuser pyproject.toml ./
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser tests ./tests
COPY --chown=appuser:appuser contracts ./contracts
COPY docker/entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -fsS http://localhost:8000/health/live || exit 1
ENTRYPOINT ["entrypoint"]
CMD ["api"]
