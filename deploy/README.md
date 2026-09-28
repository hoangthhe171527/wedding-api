# Vận hành production — Xưởng Thiệp Hỷ

Một máy chủ Linux có Docker. Web và API **chung một domain** sau Caddy (HTTPS tự
động). Chỉ Caddy mở cổng 80/443; MongoDB, Redis, kho ảnh S3 nằm trong mạng nội bộ
và có mật khẩu.

```
Internet ──► Caddy ──┬─ /api/*  ──► api  (FastAPI, nhiều worker)
                     ├─ /*      ──► web  (TanStack Start, Node)
                     └─ MEDIA_DOMAIN ──► s3 (SeaweedFS) — ảnh cưới qua URL đã ký
                api ──► mongodb (replica set, xác thực) · redis (mật khẩu) · s3
```

Thư mục: `wedding-api/` và `wedding-web/` nằm cạnh nhau (compose build web từ
`../../wedding-web`).

## 1. Triển khai lần đầu

1. DNS: trỏ `DOMAIN` và `MEDIA_DOMAIN` về IP máy chủ.
2. Bí mật:
   ```sh
   cd wedding-api/deploy
   cp .env.prod.example .env.prod && chmod 600 .env.prod
   openssl rand -base64 48    # dùng cho JWT_SECRET, mật khẩu Mongo/Redis, S3_SECRET_KEY
   openssl rand -base64 756   # MONGO_REPLICA_KEY (một dòng)
   ```
   API **từ chối khởi động** nếu còn khoá mẫu, thiếu khoá S3, bật `AUTO_SEED`,
   `SUPPORT_ZALO_PHONE` là số mẫu, hay MoMo trỏ cổng thử nghiệm — xem log api.
3. Chạy:
   ```sh
   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
   ```
   Vai trò mặc định và bộ 46 mẫu tự tạo lúc API khởi động (idempotent).
4. Tạo tài khoản quản trị đầu tiên (mật khẩu nhập tay, không lưu ở đâu cả):
   ```sh
   docker compose -f docker-compose.prod.yml --env-file .env.prod exec api \
     python -m app.seeds.bootstrap_admin --email ops@ten-mien.vn
   ```
   Không có tài khoản demo nào ở production (`seed` chỉ chạy ở `ENV=local`).

Staging: như trên với `APP_ENV=staging` trong `.env.prod`.

## 2. Sao lưu — BẮT BUỘC trước khi có khách thật

```sh
./backup.sh                       # MongoDB (mongodump --oplog) + volume ảnh -> backups/<thời điểm>
```
Cron hằng ngày và đẩy ra NGOÀI máy chủ (hỏng đĩa là mất cả máy lẫn bản sao lưu):
```cron
15 3 * * * cd /srv/wedding/wedding-api/deploy && ./backup.sh && rclone sync backups r2:wedding-backups
```
Script tự kiểm archive không rỗng / không hỏng, giữ 14 bản mới nhất (`KEEP=`).

Khôi phục (ghi đè, dừng api trong lúc làm):
```sh
./restore.sh backups/20261001-031500
```
**Diễn tập khôi phục mỗi quý** trên một máy thử: bản sao lưu chưa từng khôi phục
thử là bản sao lưu chưa chắc dùng được.

## 3. Cập nhật phiên bản

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build api web
```
- Thay đổi schema: field mới có giá trị mặc định nên dữ liệu cũ đọc được ngay;
  index mới tạo lúc khởi động. Collection lớn: tạo index trước bằng tay ngoài giờ cao điểm.
- Nâng cấp từ bản lưu ảnh trong Mongo:
  `docker compose ... exec api python -m app.seeds.migrate_photos` (chạy **sau** khi
  đã có bản sao lưu; chạy lại bao nhiêu lần cũng được).
- Nâng cấp lên bản có ảnh hai cỡ: `docker compose ... exec api python -m
  app.seeds.backfill_photo_variants` — tạo bản nhỏ cho ảnh cũ (chưa chạy thì web
  thiệp vẫn đúng, chỉ tải ảnh to hơn).
- CSP của trang web do container `web` dựng (nonce theo từng request, cần
  `CSP_MEDIA_ORIGIN` — compose đã đặt từ `MEDIA_DOMAIN`); Caddy chỉ đặt CSP dự phòng
  khi phản hồi chưa có.
- Quay lại bản trước: `git checkout <tag>` rồi `up -d --build`. Dữ liệu tương thích
  ngược với bản trước nếu chỉ thêm trường.

## 4. Xoay vòng bí mật

| Bí mật | Ảnh hưởng khi đổi |
|---|---|
| `JWT_SECRET` | Mọi người phải đăng nhập lại; URL ảnh đã phát hết hạn (web lấy URL mới khi tải lại) |
| `MONGO_ROOT_PASSWORD` | Đổi user trong Mongo (`db.changeUserPassword`) TRƯỚC, rồi mới đổi `.env.prod` và khởi động lại api |
| `REDIS_PASSWORD` | Khởi động lại redis + api; mất bộ đếm rate limit (vô hại) |
| `S3_SECRET_KEY` | Khởi động lại s3 + api |
| `BANK_WEBHOOK_KEY` | Đổi đồng thời ở dịch vụ đọc sao kê |

## 5. Kho ảnh

Mặc định SeaweedFS tự host (Docker Hub đã ngừng phát image MinIO công khai). Dùng
Cloudflare R2 / AWS S3 thay thế (khuyến nghị khi lưu lượng lớn — có CDN, bền vững,
không phải tự sao lưu ảnh):
1. Tạo bucket riêng tư + khoá truy cập.
2. `.env.prod`: `S3_ENDPOINT=https://<account>.r2.cloudflarestorage.com`, `S3_ACCESS_KEY`,
   `S3_SECRET_KEY`, `S3_BUCKET`; trỏ `MEDIA_DOMAIN` về domain công khai của bucket.
3. Chép dữ liệu cũ (`rclone copy`), bỏ service `s3` khỏi compose, cập nhật CSP trong Caddyfile.

## 6. Bảo mật đã có sẵn

- Refresh token trong cookie `HttpOnly; Secure; SameSite=Strict`, access token 15 phút
  chỉ trong bộ nhớ trình duyệt.
- CSP, HSTS, `X-Content-Type-Options`, `frame-ancestors 'none'` do Caddy đặt.
  CSP còn `script-src 'unsafe-inline'` (SSR cần script inline để hydrate) — nâng lên
  nonce khi TanStack Start hỗ trợ.
- `/docs`, `/openapi.json` tắt ngoài máy dev. Webhook thanh toán trả 404 khi
  `ONLINE_PAYMENT_ENABLED=false`.

## 7. Theo dõi

- `docker compose ... logs -f api` — log JSON, mỗi dòng có `request_id` (cũng trả về
  ở header `X-Request-ID` để đối chiếu khi khách báo lỗi).
- `GET /health` (readiness: Mongo + Redis) cho giám sát uptime; `/health/live` cho Docker.
- Việc còn nên làm: gửi log / lỗi về Sentry hoặc Grafana Loki, cảnh báo khi
  `/health` trả 503 hay dung lượng đĩa > 80%.
