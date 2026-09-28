"""Hợp đồng giá trị API ↔ web (`contracts/enums.json`) phải khớp code hiện tại.

Hỏng bài này: chạy lại
    docker compose exec -T api python -m app.seeds.export_enums > contracts/enums.json
rồi ở wedding-web: `bun run sync:enums` và sửa hằng số web cho khớp.
"""

from __future__ import annotations

from pathlib import Path

from app.seeds.export_enums import dump

CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "enums.json"


def test_hop_dong_gia_tri_khop_code() -> None:
    assert CONTRACT.read_text(encoding="utf-8") == dump()
