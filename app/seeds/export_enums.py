"""Xuất các danh sách giá trị mà web cũng giữ một bản chép — hợp đồng API ↔ web.

    docker compose exec -T api python -m app.seeds.export_enums > contracts/enums.json

Web đối chiếu hằng số của mình với bản chép `wedding-web/src/lib/invite/api-enums.json`
(chép từ file này bằng `bun run sync:enums`). Test ở cả hai phía khoá sự trôi lệch.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from app.modules.guest.domain.enums import GUEST_GROUPS
from app.modules.wedding.domain.design import DECOR_KEYS, FIELD_KEYS
from app.modules.wedding.domain.enums import (
    SITE_SECTIONS,
    THEME_AMBIENTS,
    THEME_FONTS,
    WORDING_KEYS,
    OpenStyle,
    Tone,
)


def enums() -> dict[str, Any]:
    return {
        "card_fields": sorted(FIELD_KEYS),
        "card_decors": sorted(DECOR_KEYS),
        "theme_fonts": sorted(THEME_FONTS),
        "theme_ambients": sorted(THEME_AMBIENTS),
        "site_sections": list(SITE_SECTIONS),
        "wording_keys": sorted(WORDING_KEYS),
        "guest_groups": list(GUEST_GROUPS),
        "open_styles": sorted(item.value for item in OpenStyle),
        "tones": sorted(item.value for item in Tone),
    }


def dump() -> str:
    return json.dumps(enums(), ensure_ascii=False, indent=2) + "\n"


if __name__ == "__main__":
    sys.stdout.write(dump())
