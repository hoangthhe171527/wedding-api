"""Cấu hình ứng dụng — nguồn duy nhất đọc biến môi trường.

Không module nào được gọi `os.environ` trực tiếp; luôn đi qua `get_settings()`.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    """Môi trường chạy."""

    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


#: Bí mật giữ chỗ dùng cho local. Bị từ chối ở staging/production.
PLACEHOLDER_JWT_SECRET = "doi-chuoi-nay-truoc-khi-len-that-toi-thieu-32-ky-tu"  # noqa: S105
PLACEHOLDER_ZALO_PHONE = "0912345678"
#: Khoá / mật khẩu mẫu của máy dev (docker-compose.yml, .env.example) — đã công khai.
KNOWN_DEV_SECRETS: frozenset[str] = frozenset(
    {"wedding-local-secret", "local-dev-webhook-key", PLACEHOLDER_JWT_SECRET}
)


class Settings(BaseSettings):
    """Toàn bộ cấu hình runtime, nạp từ biến môi trường hoặc file `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Ứng dụng -----------------------------------------------------------
    #: Mặc định `production` — "hỏng thì ĐÓNG": quên khai biến là mọi chốt chặn bật lên.
    #: Máy dev khai `ENV=local` tường minh (docker-compose.yml, .env).
    ENV: Environment = Environment.PRODUCTION
    APP_NAME: str = "wedding-api"
    API_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # --- Cơ sở dữ liệu ------------------------------------------------------
    MONGODB_URL: str = "mongodb://mongodb:27017/?replicaSet=rs0&directConnection=true"
    MONGODB_DB: str = "wedding"
    TEST_MONGODB_DB: str | None = None
    MONGODB_MIN_POOL_SIZE: Annotated[int, Field(ge=0, le=100)] = 0
    MONGODB_MAX_POOL_SIZE: Annotated[int, Field(ge=1, le=500)] = 50
    MONGODB_TIMEOUT_MS: Annotated[int, Field(ge=500, le=60_000)] = 10_000

    # --- Kho object (MinIO / S3) --------------------------------------------
    #: Byte ảnh và file tải lên. MongoDB chỉ giữ siêu dữ liệu.
    S3_ENDPOINT: str = "http://minio:9000"
    #: Khoá truy cập kho. Local lấy từ docker-compose; môi trường khác bắt buộc đặt.
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "wedding-media"
    TEST_S3_BUCKET: str | None = None
    S3_REGION: str = "us-east-1"
    #: Địa chỉ công khai của kho (domain MinIO / CDN). Có thì URL ảnh chuyển hướng
    #: thẳng tới kho — API không phải gánh byte ảnh; để trống thì API đọc hộ.
    S3_PUBLIC_URL: str = ""

    # --- Redis --------------------------------------------------------------
    #: Chỉ dùng cho danh sách phiên bị thu hồi và bộ đếm tần suất. Cả hai hỏng
    #: thì MỞ, không đóng — xem `app.core.security.revocation`.
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_KEY_PREFIX: str = "wedding"

    # --- Token --------------------------------------------------------------
    JWT_SECRET: str = PLACEHOLDER_JWT_SECRET
    JWT_ALG: Literal["HS256"] = "HS256"
    JWT_ISSUER: str = "wedding-api"
    ACCESS_TTL_MIN: Annotated[int, Field(ge=1, le=1440)] = 15
    REFRESH_TTL_DAYS: Annotated[int, Field(ge=1, le=365)] = 30

    # --- Tài khoản ----------------------------------------------------------
    #: Cho khách tự đăng ký tài khoản dùng mẫu. Tắt đi thì chỉ admin cấp được.
    ALLOW_SELF_REGISTRATION: bool = True

    # --- Giới hạn tần suất --------------------------------------------------
    #: Số lần thử đăng nhập tối đa từ MỘT địa chỉ IP trong một cửa sổ.
    LOGIN_RATE_LIMIT_IP: Annotated[int, Field(ge=1, le=1000)] = 20
    #: Số lần thử tối đa cho MỘT định danh — chặt hơn theo IP vì kẻ dò mật khẩu
    #: một tài khoản cụ thể mới là mối nguy thật.
    LOGIN_RATE_LIMIT_IDENTIFIER: Annotated[int, Field(ge=1, le=1000)] = 8
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: Annotated[int, Field(ge=10, le=3600)] = 300
    #: Số tài khoản tạo được từ MỘT địa chỉ IP trong một giờ.
    REGISTER_RATE_LIMIT_IP: Annotated[int, Field(ge=1, le=1000)] = 5
    #: Số lớp proxy đứng trước API — đọc IP client từ PHÍA CUỐI `X-Forwarded-For`
    #: (phần đầu là thứ client tự khai). `0` = bỏ qua header, lấy IP kết nối TCP.
    #: Mặc định 0: API nhận kết nối trực tiếp thì `X-Forwarded-For` do client tự viết.
    #: Chỉ đặt >= 1 khi thật sự có proxy đứng trước và API KHÔNG lộ trực tiếp ra ngoài.
    TRUSTED_PROXY_HOPS: Annotated[int, Field(ge=0, le=10)] = 0

    # --- Ảnh cưới -----------------------------------------------------------
    #: Thiết kế giới hạn 12 ảnh/xưởng: ảnh đầu là ảnh bìa, còn lại vào album.
    PHOTO_MAX_COUNT: Annotated[int, Field(ge=1, le=100)] = 12
    #: Trình duyệt đã thu ảnh về ~1400px trước khi gửi; đây là lưới chặn cuối.
    PHOTO_MAX_BYTES: Annotated[int, Field(ge=10_000, le=20_000_000)] = 2_500_000
    #: Tuổi thọ URL ảnh đã ký. Web thiệp mở lại trong vòng một tuần không phải
    #: xin URL mới; lộ URL thì cũng chỉ lộ đúng một tấm, và tự hết hạn.
    MEDIA_URL_TTL_SECONDS: Annotated[int, Field(ge=60, le=2_592_000)] = 604_800

    # --- Địa chỉ công khai --------------------------------------------------
    #: Gốc web: link thiệp của khách là `<PUBLIC_WEB_URL>/invite/<slug>#<mã>`.
    PUBLIC_WEB_URL: str = "http://localhost:8091"
    #: Gốc API như trình duyệt nhìn thấy — URL ảnh đã ký trỏ về đây.
    PUBLIC_API_URL: str = "http://localhost:28080"

    # --- Nâng gói -----------------------------------------------------------
    #: Khách nâng gói bằng cách nhắn Zalo cho đội tư vấn; đội vận hành cấp gói
    #: ở màn quản trị. Bật `ONLINE_PAYMENT_ENABLED` thì khách tự thanh toán
    #: (VietQR / MoMo) như cũ.
    SUPPORT_ZALO_PHONE: str = PLACEHOLDER_ZALO_PHONE
    SUPPORT_ZALO_NAME: str = "Tư vấn Xưởng Thiệp Hỷ"
    ONLINE_PAYMENT_ENABLED: bool = False

    # --- Thanh toán ---------------------------------------------------------
    #: Giả lập thanh toán (nút "đã chuyển khoản" ở web). CHỈ local/test.
    PAYMENT_SANDBOX: bool = False
    #: Tài khoản nhận chuyển khoản VietQR. `BANK_BIN` là mã BIN 6 số của ngân hàng.
    BANK_BIN: str = ""
    BANK_NAME: str = ""
    BANK_ACCOUNT_NO: str = ""
    BANK_ACCOUNT_NAME: str = ""
    #: Khoá dịch vụ đọc sao kê gửi kèm webhook: `Authorization: Apikey <khoá>`.
    BANK_WEBHOOK_KEY: str = ""
    #: Ví MoMo — để trống là tắt cổng MoMo.
    MOMO_PARTNER_CODE: str = ""
    MOMO_ACCESS_KEY: str = ""
    MOMO_SECRET_KEY: str = ""
    MOMO_ENDPOINT: str = "https://test-payment.momo.vn/v2/gateway/api/create"

    # --- Gợi ý câu chữ bằng AI (Claude) ------------------------------------
    #: Để trống là tắt tính năng — nút "Gợi ý bằng AI" ẩn đi, endpoint trả 503.
    ANTHROPIC_API_KEY: str = ""
    AI_WORDING_MODEL: str = "claude-opus-5"

    # --- Theo dõi lỗi (Sentry) — để trống là tắt ----------------------------
    SENTRY_DSN: str = ""
    #: Tỉ lệ request được đo hiệu năng (0 = chỉ báo lỗi).
    SENTRY_TRACES_SAMPLE_RATE: Annotated[float, Field(ge=0, le=1)] = 0.05
    #: Phiên bản đang chạy (vd tag git) — gắn vào sự kiện để biết lỗi từ bản nào.
    APP_RELEASE: str = ""

    # --- Khởi động ----------------------------------------------------------
    AUTO_SEED: bool = False

    # --- CORS ---------------------------------------------------------------
    # `NoDecode` bắt buộc: pydantic-settings JSON-decode trường phức TRƯỚC khi
    # validator `mode="before"` chạy, nên chuỗi ngăn cách dấu phẩy sẽ ném lỗi.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:8091", "http://127.0.0.1:8091"]
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Cho phép khai báo dạng chuỗi ngăn cách bằng dấu phẩy trong `.env`."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("PUBLIC_WEB_URL", "PUBLIC_API_URL")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        """Bỏ `/` cuối để ghép đường dẫn không sinh `//`."""
        return value.rstrip("/")

    @field_validator("JWT_SECRET")
    @classmethod
    def _secret_must_be_strong_outside_local(cls, value: str, info: ValidationInfo) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET phải dài tối thiểu 32 ký tự.")
        # `ENV` khai trước `JWT_SECRET` nên chắc chắn đã có trong `info.data`.
        env = info.data.get("ENV")
        if value == PLACEHOLDER_JWT_SECRET and env not in {Environment.LOCAL, Environment.TEST}:
            raise ValueError(
                "JWT_SECRET vẫn là giá trị giữ chỗ. Đặt bí mật riêng trước khi chạy "
                f"ở môi trường {env}."
            )
        return value

    @model_validator(mode="after")
    def _deployment_guard(self) -> Settings:
        """Ngoài máy dev: từ chối khởi động với cấu hình dev / khoá mẫu đã công khai."""
        if self.ENV in {Environment.LOCAL, Environment.TEST}:
            return self
        problems: list[str] = []
        if not self.S3_ACCESS_KEY or not self.S3_SECRET_KEY:
            problems.append("chưa đặt S3_ACCESS_KEY / S3_SECRET_KEY")
        elif self.S3_SECRET_KEY in KNOWN_DEV_SECRETS:
            problems.append("S3_SECRET_KEY đang là khoá mẫu của máy dev")
        if self.BANK_WEBHOOK_KEY and (
            len(self.BANK_WEBHOOK_KEY) < 32 or self.BANK_WEBHOOK_KEY in KNOWN_DEV_SECRETS
        ):
            problems.append("BANK_WEBHOOK_KEY phải là khoá riêng, dài tối thiểu 32 ký tự")
        if self.AUTO_SEED:
            problems.append("không được bật AUTO_SEED (tài khoản demo có mật khẩu công khai)")
        if self.ENV is Environment.PRODUCTION:
            if self.MOMO_PARTNER_CODE and "test-" in self.MOMO_ENDPOINT:
                problems.append("MOMO_ENDPOINT vẫn trỏ cổng thử nghiệm của MoMo")
            if self.SUPPORT_ZALO_PHONE == PLACEHOLDER_ZALO_PHONE:
                problems.append("SUPPORT_ZALO_PHONE vẫn là số mẫu")
        if problems:
            raise ValueError(f"Cấu hình chưa sẵn sàng cho {self.ENV}: " + "; ".join(problems) + ".")
        return self

    @field_validator("PAYMENT_SANDBOX")
    @classmethod
    def _sandbox_only_local(cls, value: bool, info: ValidationInfo) -> bool:
        env = info.data.get("ENV")
        if value and env not in {Environment.LOCAL, Environment.TEST}:
            raise ValueError(f"Không được bật PAYMENT_SANDBOX ở môi trường {env}.")
        return value

    # --- Thuộc tính dẫn xuất ------------------------------------------------
    @property
    def is_local(self) -> bool:
        return self.ENV is Environment.LOCAL

    @property
    def effective_test_database(self) -> str:
        """Tên database cho pytest; mặc định thêm hậu tố `_test` vào DB chính."""
        return self.TEST_MONGODB_DB or f"{self.MONGODB_DB}_test"

    @property
    def effective_test_bucket(self) -> str:
        return self.TEST_S3_BUCKET or f"{self.S3_BUCKET}-test"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Trả về Settings đã cache. Dùng ở mọi nơi thay cho `os.environ`."""
    return Settings()


__all__ = ["PLACEHOLDER_JWT_SECRET", "Environment", "Settings", "get_settings"]
