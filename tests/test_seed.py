"""Seed idempotent và chỉ chạy ở local/test."""

from __future__ import annotations

import pytest

from app.core.config import Environment, get_settings
from app.seeds.seed import SeedRefusedError, ensure_seedable, run_seed


async def test_seed_chay_lan_hai_la_noop() -> None:
    first = await run_seed()
    assert first["noop"] is False
    assert first["templates_created"] == 134
    second = await run_seed()
    assert second["noop"] is True


def test_seed_tu_choi_moi_truong_that(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "ENV", Environment.PRODUCTION)
    with pytest.raises(SeedRefusedError):
        ensure_seedable()
