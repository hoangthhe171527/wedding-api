"""Gợi ý câu chữ thiệp bằng Claude (Anthropic SDK).

Một lượt gọi, đầu ra ép theo JSON schema (ba phương án). Không có
`ANTHROPIC_API_KEY` thì tính năng tắt — không đọc thông tin đăng nhập nào khác
trên máy chủ, để việc bật / tắt nằm hẳn trong cấu hình.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Final

import anthropic

from app.core.config import get_settings
from app.core.errors import RateLimitedError, ServiceUnavailableError
from app.core.logging import get_logger

log = get_logger(__name__)

#: Ô câu chữ -> mô tả cho người viết. Khoá trùng `WORDING_KEYS`.
FIELD_GUIDE: Final[dict[str, str]] = {
    "eyebrow": "tiêu đề nhỏ ở đầu thiệp, 2-5 chữ (ví dụ: Lễ Thành Hôn)",
    "eyebrowG": "tiêu đề nhỏ trên thiệp nhà gái, 2-5 chữ (ví dụ: Lễ Vu Quy)",
    "invite": "lời mời đứng ngay trước tên khách, 3-6 chữ (ví dụ: Trân trọng kính mời)",
    "announce": "một câu báo tin hai gia đình tổ chức lễ cưới, dưới 20 chữ",
    "attend": "một câu mời khách tới dự và chung vui, dưới 20 chữ",
    "closing": "câu kết cuối thiệp, dưới 16 chữ",
    "thanks": "lời cảm ơn khách, dưới 14 chữ",
}

TONE_GUIDE: Final[dict[str, str]] = {
    "family": "trang trọng, ấm áp, theo lối thiệp gia đình Việt Nam gửi họ hàng, người lớn",
    "formal": "lịch sự, chuẩn mực, dùng cho đồng nghiệp, đối tác",
    "friends": "thân mật, trẻ trung, vui vẻ, xưng hô với bạn bè",
}

SYSTEM: Final[str] = (
    "Bạn là người viết lời thiệp cưới tiếng Việt. Viết câu chữ tự nhiên, đúng chính tả, "
    "đúng phong tục cưới hỏi Việt Nam, không sáo rỗng, không dùng emoji, không bịa thêm "
    "thông tin ngoài dữ kiện được cho. Mỗi phương án là một câu hoàn chỉnh dùng được ngay "
    "trên thiệp, không kèm dấu ngoặc kép hay giải thích."
)

SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
        }
    },
    "required": ["suggestions"],
    "additionalProperties": False,
}

MAX_SUGGESTION_CHARS: Final[int] = 160


class ClaudeWordingWriter:
    """`WordingWriter` trên Claude."""

    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.AI_WORDING_MODEL
        self._client = (
            anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=45.0)
            if settings.ANTHROPIC_API_KEY
            else None
        )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def suggest(
        self, *, field: str, tone: str, facts: dict[str, str], current: str
    ) -> list[str]:
        if self._client is None:
            raise ServiceUnavailableError("Gợi ý bằng AI chưa được bật.", code="ai_disabled")
        lines = "\n".join(f"- {key}: {value}" for key, value in facts.items())
        prompt = (
            f"Viết 3 phương án khác nhau cho ô: {FIELD_GUIDE[field]}.\n"
            f"Giọng văn: {TONE_GUIDE[tone]}.\n"
            f"Dữ kiện đám cưới:\n{lines or '- (chưa có)'}\n"
            + (f"Câu hiện tại (viết khác đi): {current}\n" if current else "")
        )
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=2000,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
                output_config={
                    "effort": "low",
                    "format": {"type": "json_schema", "schema": SCHEMA},
                },
                # Bị bộ lọc an toàn từ chối thì máy chủ tự chạy lại trên mô hình dự phòng.
                extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
                extra_body={"fallbacks": "default"},
            )
        except anthropic.RateLimitError as exc:
            raise RateLimitedError(
                "Gợi ý bằng AI đang bận. Thử lại sau ít phút.", code="ai_busy"
            ) from exc
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
            log.warning("ai_wording_failed", error=str(exc))
            raise ServiceUnavailableError(
                "Chưa gợi ý được lúc này. Thử lại sau.", code="ai_unavailable"
            ) from exc
        if response.stop_reason in ("refusal", "max_tokens"):
            log.info("ai_wording_stopped", stop_reason=response.stop_reason)
            raise ServiceUnavailableError("Chưa gợi ý được cho ô này.", code="ai_unavailable")
        text = next((block.text for block in response.content if block.type == "text"), "")
        try:
            raw = json.loads(text).get("suggestions", [])
        except (json.JSONDecodeError, AttributeError) as exc:
            raise ServiceUnavailableError(
                "Chưa gợi ý được lúc này. Thử lại sau.", code="ai_unavailable"
            ) from exc
        cleaned = [
            " ".join(str(item).split()).strip('"“”')[:MAX_SUGGESTION_CHARS]
            for item in raw
            if str(item).strip()
        ]
        return cleaned[:3]


@lru_cache(maxsize=1)
def build_wording_writer() -> ClaudeWordingWriter:
    """MỘT client cho cả tiến trình: mỗi `AsyncAnthropic` giữ pool kết nối riêng —
    tạo mới mỗi request là rò socket và bắt tay TLS lại mỗi lượt gợi ý."""
    return ClaudeWordingWriter()


__all__ = ["FIELD_GUIDE", "ClaudeWordingWriter", "build_wording_writer"]
