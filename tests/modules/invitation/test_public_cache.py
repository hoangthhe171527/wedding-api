"""Kiểm tra lớp cache Redis nóng và Cache-Control HTTP cho thiệp công khai."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.core import cache, rate_limit
from app.core.config import get_settings
from app.core.storage import ObjectStore
from app.modules.billing.domain.enums import Plan
from app.modules.billing.infrastructure.external import bridges as billing_bridges
from app.modules.billing.infrastructure.external.bridges import EntitlementReader
from app.modules.guest.infrastructure.external.bridges import GuestResponder
from app.modules.invitation.application.use_cases import Invitation
from app.modules.invitation.interfaces.http import router as invitation_router
from app.modules.media.domain.entities import Photo
from app.modules.media.infrastructure.external.public_photos import PublicPhotoLister
from app.modules.template.domain.entities import Intro
from app.modules.template.infrastructure.external.intro_reader import IntroUrlReader


def _install_fake_cache(monkeypatch: pytest.MonkeyPatch) -> dict[tuple[object, ...], Any]:
    store: dict[tuple[object, ...], Any] = {}

    async def _get_json(*parts: object) -> Any | None:
        return store.get(parts)

    async def _set_json(value: Any, ttl_seconds: int, *parts: object) -> None:
        del ttl_seconds
        store[parts] = value

    async def _delete(*parts: object) -> None:
        store.pop(parts, None)

    monkeypatch.setattr(cache, "get_json", _get_json)
    monkeypatch.setattr(cache, "set_json", _set_json)
    monkeypatch.setattr(cache, "delete", _delete)
    return store


async def test_public_photo_lister_cache_va_cdn_url(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_cache(monkeypatch)
    cfg = get_settings()
    monkeypatch.setattr(cfg, "S3_PUBLIC_URL", "https://cdn.thiephy.test")
    monkeypatch.setattr(cfg, "S3_ACCESS_KEY", "k")
    monkeypatch.setattr(cfg, "S3_SECRET_KEY", "s")
    tenant_id = uuid4()
    photo_id = uuid4()
    calls = 0

    class _FakePhotos:
        async def list(self, _tenant_id: UUID) -> list[Photo]:
            nonlocal calls
            calls += 1
            return [
                Photo(
                    id=photo_id,
                    tenant_id=tenant_id,
                    order=0,
                    content_type="image/jpeg",
                    size=1024,
                    width=1600,
                    height=1200,
                    storage_key=f"photos/{tenant_id}/{photo_id}",
                    small_key=f"photos/{tenant_id}/{photo_id}.sm",
                )
            ]

    lister = PublicPhotoLister(photos=_FakePhotos(), store=ObjectStore())  # type: ignore[arg-type]
    first = await lister.album(tenant_id)
    second = await lister.album(tenant_id)
    assert calls == 1
    assert first == second
    assert first["full"][0].startswith("https://cdn.thiephy.test/")
    assert ".sm?" in first["small"][0]
    assert "#focus=50,50" in first["full"][0]


async def test_public_photo_lister_fallback_api_khi_khong_co_public_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_cache(monkeypatch)
    cfg = get_settings()
    monkeypatch.setattr(cfg, "S3_PUBLIC_URL", "")
    tenant_id = uuid4()
    photo_id = uuid4()

    class _FakePhotos:
        async def list(self, _tenant_id: UUID) -> list[Photo]:
            return [
                Photo(
                    id=photo_id,
                    tenant_id=tenant_id,
                    order=0,
                    content_type="image/jpeg",
                    size=500,
                    width=1200,
                    height=900,
                    storage_key=f"photos/{tenant_id}/{photo_id}",
                )
            ]

    lister = PublicPhotoLister(photos=_FakePhotos(), store=ObjectStore())  # type: ignore[arg-type]
    album = await lister.album(tenant_id)
    assert "/api/v1/media/photos/" in album["full"][0]
    assert parse_qs(urlsplit(album["small"][0]).query)["w"] == ["sm"]


async def test_entitlement_reader_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_cache(monkeypatch)
    calls = 0

    async def _fake_plan(*_args: object, **_kwargs: object) -> Plan:
        nonlocal calls
        calls += 1
        return Plan.PREMIUM

    monkeypatch.setattr(billing_bridges, "current_plan", _fake_plan)
    reader = EntitlementReader()
    tenant_id = uuid4()
    first = await reader.plan_for(tenant_id)
    second = await reader.plan_for(tenant_id)
    assert calls == 1
    assert first == second
    assert first["plan"] == "premium"
    assert first["remove_badge"] is True


async def test_intro_url_reader_cache_va_cdn(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_cache(monkeypatch)
    cfg = get_settings()
    monkeypatch.setattr(cfg, "S3_PUBLIC_URL", "https://cdn.thiephy.test")
    monkeypatch.setattr(cfg, "S3_ACCESS_KEY", "k")
    monkeypatch.setattr(cfg, "S3_SECRET_KEY", "s")
    intro_id = uuid4()
    calls = 0

    class _FakeIntros:
        async def get(self, target_id: UUID) -> Intro | None:
            nonlocal calls
            calls += 1
            if target_id != intro_id:
                return None
            return Intro(
                id=intro_id,
                name="Mở thiệp",
                key=f"intros/{intro_id}.mp4",
                content_type="video/mp4",
                size=1024,
                order=0,
                is_active=True,
                created_at=datetime.now(UTC),
            )

    reader = IntroUrlReader(intros=_FakeIntros(), store=ObjectStore())  # type: ignore[arg-type]
    assert await reader.url_of("khong-hop-le") == ""
    first = await reader.url_of(str(intro_id))
    second = await reader.url_of(str(intro_id))
    assert calls == 1
    assert first == second
    assert first.startswith(f"https://cdn.thiephy.test/{cfg.S3_BUCKET}/intros/{intro_id}.mp4?")


async def test_guest_responder_public_wishes_cache_va_cat_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_cache(monkeypatch)
    tenant_id = uuid4()
    calls = 0

    class _WishRow:
        def __init__(self, idx: int) -> None:
            self.name = f"Khách {idx}"
            self.message = f"Chúc {idx}"
            self.created_at = datetime.now(UTC) - timedelta(minutes=idx)

    class _FakeWishes:
        async def list_recent(
            self, _tenant_id: UUID, *, limit: int, with_message: bool
        ) -> list[_WishRow]:
            nonlocal calls
            calls += 1
            assert with_message is True
            return [_WishRow(i) for i in range(limit)]

    responder = GuestResponder()
    responder._wishes = _FakeWishes()  # type: ignore[assignment]
    first = await responder.public_wishes(tenant_id, 2)
    second = await responder.public_wishes(tenant_id, 5)
    assert calls == 1
    assert len(first) == 2
    assert len(second) == 5
    assert second[0]["name"] == "Khách 0"


async def test_invitation_http_cache_control_theo_an_danh_hay_ca_nhan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop_guard(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(rate_limit, "guard", _noop_guard)

    class _FakeUseCase:
        async def execute(self, slug: str, g: str | None, link: str | None) -> Invitation:
            del g, link
            return Invitation(
                wedding={"slug": slug},
                photos=[],
                photos_small=[],
                guest=None,
                link="",
                greeting="",
                template="daile",
                branding={"badge": True, "plan": "free"},
                defaults={"wording": {}, "messages": {}},
            )

    request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 12345)})
    anon_resp = Response()
    await invitation_router.get_invitation(
        "minh-linh",
        request,
        anon_resp,
        _FakeUseCase(),  # type: ignore[arg-type]
        g=None,
        link=None,
    )
    assert anon_resp.headers["Cache-Control"] == "public, max-age=30, stale-while-revalidate=120"

    guest_resp = Response()
    await invitation_router.get_invitation(
        "minh-linh",
        request,
        guest_resp,
        _FakeUseCase(),  # type: ignore[arg-type]
        g="k123",
        link=None,
    )
    assert guest_resp.headers["Cache-Control"] == "private, no-store"

    class _FakeWishesUseCase:
        async def execute(self, slug: str) -> list[dict[str, Any]]:
            del slug
            return []

    wishes_resp = Response()
    await invitation_router.list_wishes("minh-linh", wishes_resp, _FakeWishesUseCase())  # type: ignore[arg-type]
    assert wishes_resp.headers["Cache-Control"] == "public, max-age=15, stale-while-revalidate=60"
