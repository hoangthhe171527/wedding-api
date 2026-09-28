#!/usr/bin/env bash
# Điểm vào container. Lệnh đầu tiên quyết định vai: api | seed | shell.
set -euo pipefail

ROLE="${1:-api}"
shift || true

wait_for_mongo() {
  echo "[entrypoint] Chờ MongoDB..."
  python - <<'PY'
import asyncio
import sys

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings


async def main() -> None:
    cfg = get_settings()
    for attempt in range(1, 61):
        client = AsyncIOMotorClient(cfg.MONGODB_URL, serverSelectionTimeoutMS=1000)
        try:
            await client.admin.command("ping")
        except Exception as exc:  # noqa: BLE001
            print(f"[entrypoint] lần {attempt}: {exc}")
            await asyncio.sleep(1)
            continue
        finally:
            client.close()
        print("[entrypoint] MongoDB sẵn sàng.")
        return
    sys.exit("[entrypoint] MongoDB không phản hồi sau 60 giây.")


asyncio.run(main())
PY
}

run_seed() {
  # Chốt chặn thứ hai, sau `app.seeds.seed.ensure_seedable`: seed ghi tài khoản
  # demo bằng khoá tự nhiên cố định, chạy nhầm ở môi trường thật là trộn dữ liệu
  # giả vào dữ liệu thật.
  # Không có ENV = production (khớp mặc định của Settings): KHÔNG seed.
  if [ "${ENV:-production}" != "local" ]; then
    echo "[entrypoint] BỎ QUA seed: ENV=${ENV}. Seed chỉ chạy ở local." >&2
    return 0
  fi
  echo "[entrypoint] nạp dữ liệu mẫu"
  python -m app.seeds.seed
}

case "$ROLE" in
  api)
    wait_for_mongo
    if [ "${AUTO_SEED:-false}" = "true" ]; then
      run_seed || echo "[entrypoint] SEED HỎNG — xem log phía trên." >&2
    fi
    # Nhiều worker: một tiến trình chỉ dùng một lõi CPU (xử lý ảnh, băm mật khẩu).
    # Rate limit và thu hồi phiên nằm trên Redis nên nhiều worker vẫn đúng.
    # `--forwarded-allow-ips`: chỉ tin X-Forwarded-* từ proxy đã khai.
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
      --workers "${UVICORN_WORKERS:-1}" \
      --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
      --timeout-graceful-shutdown 20 \
      "$@"
    ;;
  seed)
    wait_for_mongo
    run_seed
    ;;
  shell)
    exec "$@"
    ;;
  *)
    exec "$ROLE" "$@"
    ;;
esac
