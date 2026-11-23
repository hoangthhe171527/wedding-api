"""Kiểm tra URL ký CDN neo theo giờ và metadata Cache-Control cho S3."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from app.core.config import get_settings
from app.core.storage import ObjectStore


def test_direct_url_none_khi_chua_cau_hinh_public_url(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = get_settings()
    monkeypatch.setattr(cfg, "S3_PUBLIC_URL", "")
    store = ObjectStore()
    assert store.has_public_url is False
    assert store.direct_url("photos/a/b", timedelta(hours=6)) is None


def test_direct_url_giong_nhau_trong_cung_mot_gio_va_gioi_han_expires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = get_settings()
    monkeypatch.setattr(cfg, "S3_PUBLIC_URL", "https://media.thiephy.test")
    monkeypatch.setattr(cfg, "S3_ACCESS_KEY", "test-access")
    monkeypatch.setattr(cfg, "S3_SECRET_KEY", "test-secret")
    store = ObjectStore()
    assert store.has_public_url is True

    first = store.direct_url(
        "photos/t/p",
        timedelta(seconds=30),
        now=datetime(2026, 11, 23, 10, 5, 12, tzinfo=UTC),
    )
    second = store.direct_url(
        "photos/t/p",
        timedelta(seconds=30),
        now=datetime(2026, 11, 23, 10, 54, 59, tzinfo=UTC),
    )
    assert first is not None
    assert first == second
    assert first.startswith("https://media.thiephy.test/")
    query = parse_qs(urlsplit(first).query)
    assert "X-Amz-Signature" in query
    assert query["X-Amz-Expires"] == [str(2 * 3600)]
    assert query["response-cache-control"] == ["public, max-age=31536000, immutable"]

    clamped_max = store.direct_url(
        "photos/t/p",
        timedelta(days=30),
        now=datetime(2026, 11, 23, 10, 15, 0, tzinfo=UTC),
    )
    assert clamped_max is not None
    assert parse_qs(urlsplit(clamped_max).query)["X-Amz-Expires"] == [str(168 * 3600)]


async def test_put_gan_header_cache_control_immutable(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = get_settings()
    monkeypatch.setattr(cfg, "S3_PUBLIC_URL", "")
    store = ObjectStore()
    captured: list[dict[str, Any]] = []

    class _FakeInternal:
        def put_object(
            self,
            bucket_name: str,
            object_name: str,
            data: Any,
            length: int,
            *,
            content_type: str,
            metadata: dict[str, str],
        ) -> None:
            captured.append(
                {
                    "bucket": bucket_name,
                    "key": object_name,
                    "bytes": data.read(),
                    "length": length,
                    "content_type": content_type,
                    "metadata": metadata,
                }
            )

    monkeypatch.setattr(store, "_internal", _FakeInternal())
    await store.put("photos/1/2", b"abc", "image/jpeg")
    assert len(captured) == 1
    assert captured[0]["metadata"] == {"Cache-Control": "public, max-age=31536000, immutable"}
