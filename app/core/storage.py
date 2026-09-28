"""Kho object S3 (SeaweedFS ở local; SeaweedFS / R2 / AWS S3 ở prod) cho file nhị phân.

MongoDB chỉ giữ siêu dữ liệu; byte ảnh và mọi file tải lên nằm ở đây. SDK
`minio` là đồng bộ nên mỗi lệnh chạy trong thread (`asyncio.to_thread`) để
không chặn vòng lặp sự kiện.

Hai client: một client nội bộ (`S3_ENDPOINT`, vd `http://s3:8333`) để đọc
ghi, và — khi có `S3_PUBLIC_URL` — một client chỉ để KÝ URL theo địa chỉ công
khai mà trình duyệt với tới được (chữ ký S3 gắn với host, ký bằng host nội bộ
thì trình duyệt không dùng được).
"""

from __future__ import annotations

import asyncio
import io
from datetime import timedelta
from functools import lru_cache
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_MISSING = {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}


def _client(url: str, access_key: str, secret_key: str, region: str) -> Minio:
    parsed = urlparse(url if "://" in url else f"http://{url}")
    # `region` truyền sẵn: không cần hỏi vị trí bucket qua mạng trước mỗi lệnh / chữ ký.
    return Minio(
        parsed.netloc,
        access_key=access_key,
        secret_key=secret_key,
        secure=parsed.scheme == "https",
        region=region,
    )


class ObjectStore:
    """Đọc / ghi / xoá object trong một bucket, ký URL đọc tạm thời."""

    def __init__(self) -> None:
        cfg = get_settings()
        self._internal = _client(
            cfg.S3_ENDPOINT, cfg.S3_ACCESS_KEY, cfg.S3_SECRET_KEY, cfg.S3_REGION
        )
        self._public = (
            _client(cfg.S3_PUBLIC_URL, cfg.S3_ACCESS_KEY, cfg.S3_SECRET_KEY, cfg.S3_REGION)
            if cfg.S3_PUBLIC_URL
            else None
        )

    @property
    def bucket(self) -> str:
        # Đọc mỗi lần: test đổi sang bucket riêng sau khi kho đã được dựng.
        return get_settings().S3_BUCKET

    async def healthy(self) -> bool:
        """Kho object có phản hồi và bucket còn đó không — cho `/health`."""
        try:
            return bool(await asyncio.to_thread(self._internal.bucket_exists, self.bucket))
        except Exception:
            return False

    async def ensure_bucket(self) -> None:
        """Tạo bucket nếu chưa có. Bucket để RIÊNG TƯ — mọi lượt đọc đi qua chữ ký."""
        bucket = self.bucket
        exists = await asyncio.to_thread(self._internal.bucket_exists, bucket)
        if not exists:
            await asyncio.to_thread(self._internal.make_bucket, bucket)
            log.info("bucket_created", bucket=bucket)

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._internal.put_object,
            self.bucket,
            key,
            io.BytesIO(data),
            len(data),
            content_type=content_type,
        )

    async def get(self, key: str) -> bytes | None:
        def read() -> bytes | None:
            try:
                response = self._internal.get_object(self.bucket, key)
            except S3Error as exc:
                if exc.code in _MISSING:
                    return None
                raise
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        return await asyncio.to_thread(read)

    async def delete(self, key: str) -> None:
        """Xoá; object không tồn tại cũng coi là xong."""
        await asyncio.to_thread(self._internal.remove_object, self.bucket, key)

    def direct_url(self, key: str, expires: timedelta) -> str | None:
        """URL đọc trực tiếp từ kho (qua `S3_PUBLIC_URL`); None nếu chưa cấu hình."""
        if self._public is None:
            return None
        return self._public.presigned_get_object(self.bucket, key, expires=expires)


@lru_cache(maxsize=1)
def get_object_store() -> ObjectStore:
    return ObjectStore()


__all__ = ["ObjectStore", "get_object_store"]
