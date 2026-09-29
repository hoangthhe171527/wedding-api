# ARCHITECTURE — hợp đồng kiến trúc Xưởng Thiệp Hỷ

Chép khuôn `evo-adtracker-api/ARCHITECTURE.md`: mỗi luật ghi **thực thi ở đâu**
và **khoá bởi bài test nào**. Mục không có dòng "Khoá bởi" là mục chưa được khoá.

## §0 — Nguyên tắc chung

### §0.1 — Vai trò là dữ liệu, không phải mã

Hai vai trò của sản phẩm nằm trong collection `roles`:

| Vai trò    | Nhãn             | Quyền                                                        |
|------------|------------------|--------------------------------------------------------------|
| `admin`    | Quản trị viên    | **mọi quyền** — kể cả `studio.manage` `guest.manage` trên xưởng RIÊNG của mình (dữ liệu vẫn theo `tenant_id` trong token) |
| `customer` | Khách dùng mẫu   | `studio.manage` `guest.manage` `template.view`               |

Mã nghiệp vụ chỉ kiểm **slug quyền**, không bao giờ kiểm tên vai trò. Ngoại lệ
duy nhất: đường CẤP vai trò (đăng ký khách, seed) phải gọi tên vai trò để gán.

- Thực thi ở: `app/core/permissions.py`, `app/modules/access/domain/role_blueprints.py`.
- Khoá bởi: `tests/modules/test_authorization.py`.

### §0.2 — `domain` không biết framework

Tầng `domain` chỉ có dataclass, enum, hàm thuần. Không Beanie/Motor/Pydantic/FastAPI.
Kiểu phân trang thuần nằm ở `app/core/pages.py` (không phải `pagination.py`, nơi
có dependency FastAPI).

- Khoá bởi: `tests/modules/test_module_seam_boundaries.py::test_domain_khong_biet_framework`.

### §0.3 — Câu báo lỗi là tiếng Việt, nói phải làm gì

Cờ máy sinh trả dạng `{"slug", "label"}` (vd `status` của khách, `family`/`tone`
của mẫu) — client không hardcode nhãn.

### §0.4 — Tenant = Xưởng thiệp; mọi index bắt đầu bằng `tenant_id`

Mỗi khách dùng mẫu có một **xưởng** (studio). Mọi document nghiệp vụ kế thừa
`TenantScopedDocument`; repository luôn vào qua `.scoped(tenant_id, ...)`.

Ngoại lệ có chủ ý (đều ghi chú tại chỗ):

| Nơi | Vì sao |
|---|---|
| `roles`, `templates` | Danh mục toàn hệ thống, mọi xưởng dùng chung |
| `users.email` / `users.phone` | Đăng nhập chưa biết tenant; một người = một tài khoản |
| `auth_sessions.refresh_token_hash`, `auth_sessions.user_id` | `/auth/refresh` chỉ gửi token; "cắt mọi phiên của một người" |
| `weddings.slug` | Link công khai `/invite/<slug>` chưa biết tenant |
| `photo_blobs.photo_id` | URL ảnh đã ký chỉ mang id ảnh |
| `/admin/*` | Màn quản trị hệ thống — quyền đã kiểm ở router |
| `orders.code` | Webhook ngân hàng chỉ mang nội dung chuyển khoản — tra đơn khi chưa biết xưởng |
| `payment_events` | Tiền về không khớp đơn nào thì chưa biết của xưởng nào — chính là thứ cần đối soát |

### §0.5 — Router chỉ làm ba việc

Dịch request → gọi use case → bọc envelope. Không `if` nghiệp vụ, không bắt lỗi.

### §0.6 — Log có cấu trúc, cấm `print` (ruff `T20`)

## §1 — Backend

### §1.2 — Module độc lập

Chín module dưới `app/modules/`, bốn lớp mỗi module (`domain → application →
infrastructure → interfaces`):

| Module       | Sở hữu                                   |
|--------------|------------------------------------------|
| `identity`   | `studios`, `users`, `auth_sessions`      |
| `access`     | `roles`, `role_assignments`              |
| `template`   | `templates` (46 mẫu, kèm hạng gói), `catalog_defaults` (mẫu theo nhóm khách + câu chữ mặc định do admin đặt) |
| `wedding`    | `weddings` (một đám cưới mỗi xưởng)      |
| `guest`      | `guests` (mã link riêng 6 ký tự), `guest_wishes` (phản hồi, lời chúc từ web thiệp), `guest_links` (link theo đối tượng) |
| `media`      | `photos` (siêu dữ liệu); byte ảnh ở kho object S3 qua `app/core/storage.py` (`photo_blobs` chỉ còn cho ảnh cũ chưa chuyển) |
| `billing`    | `orders`, `payment_events` (gói, thanh toán, đối soát) |
| `printing`   | `print_requests` (yêu cầu in thiệp giấy; báo giá qua Zalo) |
| `invitation` | Không sở hữu dữ liệu — web thiệp công khai; phản hồi của khách ghi qua cầu nối của `guest` |

Module khác chỉ vào qua **barrel** `app.modules.<x>`; module sở hữu dữ liệu tự
viết cầu nối trong `infrastructure/external/` và trả **dữ liệu thuần** (không trả
thực thể của mình). Enum dùng ở hai module được **chép** (vd `GUEST_GROUPS`,
`Tone`) và bài parity khoá cho hai bản trùng nhau.

- Khoá bởi: `tests/modules/test_module_seam_boundaries.py`, `tests/modules/test_parity.py`.

### §1.4 — Đúng sáu permission slug

`studio.manage` · `guest.manage` · `template.view` · `template.manage` ·
`user.manage` · `studio.oversee` — trùng tuyệt đối
`wedding-web/src/core/access/permissions.ts`. Slug lạ trong token không cấp gì.

- **Chưa khoá**: chưa có test đối chiếu với web.

### §1.5 — Xác thực, phạm vi dữ liệu

- Access token JWT HS256 15 phút; refresh token 256-bit, DB chỉ lưu SHA-256,
  **xoay vòng** mỗi lần dùng, dùng lại token đã thu hồi = cắt mọi phiên.
- Đăng xuất / đổi mật khẩu / khoá tài khoản chặn access token còn hạn ngay qua
  danh sách thu hồi trên Redis (hỏng thì mở).
- Sai thông tin đăng nhập: 401 với **đúng một câu**; so khớp Argon2 giả khi không
  có tài khoản để không lộ qua thời gian phản hồi. Giới hạn tần suất theo IP và
  theo định danh.
- Tài nguyên của xưởng khác trả **404, không 403** (`OutOfScopeError`).
- Web thiệp công khai trả đúng MỘT vị khách theo mã; mã sai = link chung. Không
  trả ghi chú, trạng thái gửi, tin nhắn mời; tắt hộp mừng cưới thì số tài khoản
  bị bỏ khỏi payload.
- Ảnh bị mã hoá lại (bỏ EXIF/GPS) trước khi lưu; phục vụ qua URL ký HMAC tự hết hạn.

- Khoá bởi: `tests/modules/identity/test_auth_flow.py`, `tests/modules/test_authorization.py`,
  `tests/modules/wedding/test_wedding_flow.py`, `tests/modules/media/test_photos.py`.

### §1.6 — Hợp đồng HTTP

| | |
|---|---|
| Thành công | `{"data": ..., "meta": {...}}` |
| Lỗi | `{"message": "<tiếng Việt>", "code": "<snake_case>", "errors": {"field": [...]}}` |
| Phân trang | `?page=1&per_page=20` (tối đa 500) |
| Ngày / giờ sự kiện | chuỗi `yyyy-mm-dd` / `HH:MM` |
| Định danh | UUIDv7 dạng chuỗi |

### §1.9 — Local một lệnh

`docker compose up -d` (hoặc `make up`) là đủ; seed tự chạy ở `ENV=local`, hai
lớp chặn ở môi trường khác. Chạy lần hai là `{"noop": true}`.

- Khoá bởi: `tests/test_seed.py`.

### §1.10 — Gói dịch vụ chỉ xét khi XUẤT BẢN

Soạn và xem trước dùng thoải mái mọi mẫu, màn mở, tuỳ chỉnh. `wedding` gom
"đang dùng gì" (mẫu thật sự hiện cho khách, màn mở, số thiệp, nhạc, hộp mừng
cưới, tuỳ chỉnh giao diện) rồi hỏi `billing` qua cầu nối `PlanGate`; vượt gói
thì `PUT /wedding/publication` trả 409 `plan_required` kèm từng lý do.
`billing` không đọc dữ liệu đám cưới — không phụ thuộc vòng.

Gói = gói cao nhất trong các đơn ĐÃ TRẢ của xưởng. Tiền về chỉ kích hoạt khi
đủ số tiền của đơn; mỗi giao dịch ghi một dòng `payment_events` với khoá
`(nguồn, mã giao dịch)` duy nhất nên gửi lại không bao giờ kích hoạt hai lần.
`PAYMENT_SANDBOX` (nút giả lập đã trả) bị Settings từ chối ngoài local/test.

- Thực thi ở: `app/modules/billing/domain/services.py::violations`,
  `app/modules/wedding/application/use_cases/set_publication.py`,
  `app/modules/billing/application/use_cases/record_payment.py`.
- Khoá bởi: `tests/modules/billing/test_billing.py`, `tests/modules/billing/test_billing_rules.py`.

### §1.11 — Nâng gói qua tư vấn Zalo, không hiện giá

`ONLINE_PAYMENT_ENABLED=False` (mặc định): API không trả giá; `POST /billing/orders`
trả 403 `contact_zalo`. Khách bấm "Nhắn Zalo" (lời nhắn soạn sẵn có mã xưởng),
đội vận hành cấp gói ở màn Tài khoản qua `POST /admin/studios/{id}/plan` — ghi
một đơn đã trả với số tiền thực thu và lý do (bắt buộc), nên "gói = đơn đã trả
cao nhất" vẫn đúng. Mã VietQR / MoMo giữ nguyên, bật lại bằng cấu hình.
Yêu cầu in thiệp (`printing`) theo cùng tinh thần: không giá, đội vận hành
liên hệ rồi cập nhật tiến độ.

- Thực thi ở: `app/modules/billing/application/use_cases/create_order.py`,
  `app/modules/billing/application/use_cases/grant_plan.py`.
- Khoá bởi: `tests/modules/billing/test_billing.py`, `tests/modules/printing/test_printing.py`.

### §1.12 — Tuỳ chỉnh thiệp là DỮ LIỆU, không phải mã

`theme` (màu, font, hiệu ứng, màu màn mở, thứ tự / ẩn phần web) và
`card_design` (lớp chữ / dữ liệu / ảnh / hoạ tiết / hình đặt theo % khung) chỉ
nhận giá trị trong danh sách trắng (font, hoạ tiết, trường dữ liệu, màu #RRGGBB
hoặc màu của mẫu) — không HTML/CSS tự do nào đi qua API. Web vẽ lại chúng sau
thư viện render (`applyDesignToSite`, `applySiteLayout`), không sửa mã sinh.
Tuỳ chỉnh giao diện cần Gói Hỷ, thiết kế tự do cần Gói Lộng Lẫy (xét khi xuất bản).

- Thực thi ở: `app/modules/wedding/domain/services.py`, `app/modules/wedding/domain/design.py`.

### §1.13 — Gợi ý câu chữ bằng AI

`POST /wedding/wording/suggest` gọi Claude (`AI_WORDING_MODEL`, mặc định
`claude-opus-5`, đầu ra ép JSON schema, bật dự phòng phía máy chủ khi bị bộ lọc
an toàn từ chối). Chỉ gửi tên ngắn hai người, sự kiện chính, ngày, địa điểm,
chuyện tình — KHÔNG gửi khách mời, số điện thoại, tài khoản ngân hàng. Không có
`ANTHROPIC_API_KEY` thì tắt hẳn (web ẩn nút). Giới hạn 40 lượt / giờ / xưởng.

- Thực thi ở: `app/modules/wedding/application/use_cases/suggest_wording.py`,
  `app/modules/wedding/infrastructure/external/wording_ai.py`.
- Khoá bởi: `tests/modules/billing/test_wording_ai.py`.

### §1.14 — "Hỏng thì ĐÓNG" cho cấu hình, "hỏng thì MỞ" cho việc phụ

`ENV` mặc định là `production`: quên khai là mọi chốt chặn bật. Ngoài máy dev,
Settings từ chối khởi động với khoá mẫu (JWT, S3, webhook), `AUTO_SEED`, số Zalo
mẫu, MoMo cổng thử. Ngược lại, Redis (rate limit, thu hồi phiên, cache) hỏng thì
MỞ — không bao giờ để việc phụ làm sập đăng nhập hay web thiệp.

- Thực thi ở: `app/core/config.py::_deployment_guard`, `app/core/cache.py`, `app/core/rate_limit.py`.
- Khoá bởi: `tests/modules/test_production_guards.py`.

### §1.15 — Web thiệp công khai là đường nóng

Bản công khai của đám cưới cache trên Redis 30 giây, repository xoá khoá mỗi lần
đám cưới được ghi (sửa thiệp là khách thấy ngay). Các nguồn độc lập (gói, câu chữ
hệ thống, ảnh) hỏi song song. Rate limit tính theo (IP, thiệp) — khách dự tiệc
dùng chung WiFi / CGNAT. Việc CPU nặng (Argon2, Pillow) chạy trong thread có giới
hạn số lượt đồng thời; API chạy nhiều worker (`UVICORN_WORKERS`).

- Thực thi ở: `wedding/infrastructure/external/published_reader.py`,
  `invitation/application/use_cases/get_invitation.py`, `core/security/password.py`.

### §1.16 — Phiên đăng nhập của web

Refresh token trong cookie `HttpOnly; SameSite=Strict` (path `/api/v1/auth`), access
token 15 phút chỉ trong bộ nhớ trình duyệt — lỗ XSS không lấy được phiên dài hạn.
Web tuần tự hoá việc làm mới giữa các tab (Web Locks) vì refresh token xoay vòng.

### §1.17 — Hợp đồng giá trị API ↔ web

Danh sách web cũng giữ bản chép (trường dữ liệu thiệp, hoạ tiết, font, hiệu ứng,
phần web thiệp, ô câu chữ, nhóm khách, màn mở) xuất ra `contracts/enums.json`;
web chép bằng `bun run sync:enums`. Test hai phía đỏ khi lệch.

- Khoá bởi: `tests/modules/test_contracts.py`, `tests/modules/test_parity.py`,
  `wedding-web/src/lib/invite/enums.test.ts`.

Web còn KIỂM LÚC CHẠY hình dạng dữ liệu đám cưới / thiệp công khai bằng zod ngay ở
adapter HTTP: API lệch hợp đồng thì báo đúng trường sai thay vì vỡ trắng trang.

- Thực thi ở: `wedding-web/src/lib/invite/payload-schema.ts`.

### §1.18 — Thao tác quản trị để lại dấu vết

Mọi thao tác của đội vận hành lên dữ liệu khách (cấp gói, xác nhận đơn, đổi tiến độ
in, khoá/mở tài khoản, sửa mẫu, lưu mặc định hệ thống) ghi vào `audit_events`: ai,
lúc nào, lên đối tượng nào, chi tiết gì, kèm `request_id` để nối với log. Chỉ ghi
thêm — API không có đường sửa/xoá. Ghi hỏng KHÔNG làm hỏng thao tác chính (§1.14).
Lỗi không bắt được gửi Sentry khi đặt `SENTRY_DSN` (không gửi dữ liệu cá nhân).

- Thực thi ở: `core/audit.py`, `core/observability.py`; xem ở `/admin/audit` (web).

### §1.19 — Ảnh hai cỡ

Ảnh tải lên lưu bản đầy đủ (cạnh dài 1600px) và bản nhỏ (ngang 800px, `<khoá>.sm`).
URL đã ký thêm `&w=sm` là bản nhỏ; ảnh cũ chưa có bản nhỏ trả bản đầy đủ. Web thiệp
nhận `photos_small` và ghép `srcset` — điện thoại tải ~1/4 dung lượng.

- Thực thi ở: `media/infrastructure/external/pillow_processor.py`,
  `seeds/backfill_photo_variants.py` (chạy bù cho ảnh cũ),
  `wedding-web/src/lib/invite/responsive-photos.ts`.

## Ngoại lệ đã biết

| Luật | Chỗ | Ghi chú |
|---|---|---|
| Nguyên tử khi đăng ký | `RegisterCustomer` | Xuyên hai module nên dùng bù trừ (xoá xưởng/tài khoản khi gán vai trò hỏng) thay vì giao dịch |
| §1.4 | Danh mục quyền | Khớp với web nhờ con người canh |
