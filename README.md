# wedding-api — Xưởng Thiệp Hỷ

Backend soạn thiệp cưới theo bộ mẫu: thông tin cưới, ảnh, khách mời có link
riêng, web thiệp công khai. FastAPI + MongoDB (Beanie) + Redis, cấu trúc module
chép khuôn `evo-adtracker-api` — xem [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Chạy lần đầu

Máy dev **không cần Python** — mọi thứ chạy trong container.

```sh
cp .env.example .env
make up          # mongodb (replica set) + redis + kho S3 (SeaweedFS) + api, seed tự chạy ở local
```

- API: <http://localhost:28080/docs>
- Kho ảnh S3 (SeaweedFS): <http://localhost:28900> — khoá `wedding` / `wedding-local-secret`
- Production: xem [deploy/README.md](deploy/README.md) (compose prod, Caddy, backup, runbook)
- Tài khoản demo (seed):

| Vai trò | Đăng nhập | Mật khẩu |
|---|---|---|
| Quản trị viên (toàn quyền, có xưởng riêng Gói Lộng Lẫy) | `admin@thiephy.vn` | `Admin@2026` |
| Khách dùng mẫu | `0912345678` hoặc `demo@thiephy.vn` | `Demo@2026` |

Khách demo có sẵn Gói Lộng Lẫy, đám cưới mẫu Huy Hoàng & Hải Hà (đã xuất bản tại
`/invite/h-hoang-ha`) và 10 khách mẫu của thiết kế.

Local bật `PAYMENT_SANDBOX`: trang Gói dịch vụ có nút "Giả lập đã chuyển khoản"
để thử trọn luồng mua gói mà không cần tài khoản ngân hàng hay MoMo. Cấu hình
thanh toán thật (`BANK_*`, `MOMO_*`) xem `.env.example`.

## Lưu trữ ảnh

MongoDB chỉ giữ siêu dữ liệu; byte ảnh cưới nằm ở kho object S3 (SeaweedFS ở local,
bucket `wedding-media`, khoá `photos/<xưởng>/<ảnh>`). API tự tạo bucket lúc khởi động.

- Prod: trỏ `S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET` tới SeaweedFS,
  AWS S3 hoặc Cloudflare R2 (khoá bắt buộc ngoài local — thiếu là không khởi động).
- Đặt `S3_PUBLIC_URL` (domain công khai của kho / CDN) để URL ảnh chuyển hướng 302
  thẳng tới kho — API không phải gánh byte ảnh. Kho / CDN phải cho phép CORS từ
  domain web (xuất PNG/PDF đọc ảnh bằng `fetch`).
- Nâng cấp từ bản lưu ảnh trong Mongo: `docker compose exec api python -m app.seeds.migrate_photos`
  (chạy lại bao nhiêu lần cũng được; ảnh chưa chuyển vẫn đọc được trong lúc chờ).
- Ảnh tải lên trước khi có bản nhỏ (800px): `docker compose exec api python -m app.seeds.backfill_photo_variants`.

## Lệnh thường dùng

```sh
make test        # pytest trên Mongo/Redis thật (DB wedding_test)
make lint        # ruff check + ruff format --check + mypy --strict
make format
make seed        # idempotent
make lock        # sinh lại uv.lock trong container
make logs
```

## Bản đồ endpoint

| Nhóm | Endpoint | Quyền |
|---|---|---|
| Xác thực | `POST /auth/login` `/auth/register` `/auth/refresh` `/auth/logout` `/auth/change-password`, `GET /auth/me` | công khai / đã đăng nhập |
| Phân quyền | `GET /permissions`, `GET /roles` | đăng nhập / `user.manage` |
| Mẫu thiệp | `GET /templates`, `PATCH /templates/{key}` | `template.view` / `template.manage` |
| Mặc định hệ thống | `GET /templates/defaults` (công khai), `PUT /templates/defaults` — mẫu theo nhóm khách cho xưởng mới, câu chữ mặc định theo giọng văn | `template.manage` |
| Thông tin cưới | `GET/PUT /wedding` (gồm `theme` — màu, font, màn mở, thứ tự/ẩn phần web — và `card_design` — thiệp tự thiết kế), `POST /wedding/setup`, `PUT /wedding/checklist`, `PUT /wedding/publication` | `studio.manage` |
| Gợi ý câu chữ (AI) | `GET /wedding/wording/ai`, `POST /wedding/wording/suggest` — tắt khi thiếu `ANTHROPIC_API_KEY` (503 `ai_disabled`) | `studio.manage` |
| Khách mời | `GET/POST /guests`, `POST /guests/import`, `PATCH/DELETE /guests/{id}`, `GET /guests/wishes`, `DELETE /guests/wishes/{id}` | `guest.manage` |
| Gói dịch vụ | `GET /billing/plans`, `GET /billing/contact`, `GET /billing`, `POST /billing/iap/apple/verify` (xác thực signed transaction StoreKit 2), `POST /billing/orders`, `GET /billing/orders/{id}`, `POST /billing/orders/{id}/cancel`, `POST /billing/orders/{id}/simulate-paid` (chỉ giả lập) | `studio.manage` |
| Webhook thanh toán | `POST /billing/webhooks/bank` (khoá `Apikey`), `POST /billing/webhooks/momo` (chữ ký HMAC) | công khai, xác thực riêng |
| Xét gói | `GET /wedding/plan-check` | `studio.manage` |
| Ảnh cưới | `GET/POST /photos`, `POST /photos/{id}/cover`, `DELETE /photos/{id}` | `studio.manage` |
| Ảnh (URL ký) | `GET /media/photos/{id}?exp&sig` | công khai, chữ ký HMAC |
| Web thiệp | `GET /public/invitations/{slug}?g=<mã>`, `POST /public/invitations/{slug}/rsvp`, `GET /public/invitations/{slug}/wishes`, `POST /public/invitations/{slug}/open` (ghi khách đã mở link riêng) | công khai |
| In thiệp | `GET /printing/options` (công khai), `GET/POST /printing/requests`, `POST /printing/requests/{id}/cancel` | `studio.manage` |
| Quản trị | `GET /admin/users`, `PATCH /admin/users/{id}/status`, `GET /admin/studios`, `GET /admin/orders`, `POST /admin/orders/{id}/confirm`, `GET /admin/payment-events`, `POST /admin/studios/{id}/plan` (cấp gói sau tư vấn Zalo), `GET /admin/studio-plans?ids=`, `GET /admin/print-requests`, `PATCH /admin/print-requests/{id}` | `user.manage` / `studio.oversee` |

Tiền tố chung `/api/v1`.

## Cấu trúc

```
app/
  core/            hạ tầng dùng chung — KHÔNG import app.modules
  modules/<tên>/
    domain/        dataclass, enum, hàm thuần, Protocol repository
    application/   use case (mỗi file một việc), cổng sang module khác
    infrastructure/persistence (Beanie), external (cầu nối công bố), providers
    interfaces/http router + schema
    __init__.py    barrel: `router` + hàm dựng cầu nối
  seeds/           dữ liệu demo cho local
tests/             pytest (Mongo + Redis thật)
```

Thêm module mới: tạo đủ bốn lớp, export `router` và `DOCUMENTS`, thêm tên vào
`app/models_registry.py::MODULE_NAMES`.
