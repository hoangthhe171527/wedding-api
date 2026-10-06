# Repository conventions

- Đọc `ARCHITECTURE.md` trước khi sửa: module chỉ nói chuyện qua barrel, domain không import framework, phạm vi dữ liệu kiểm ở use case (ngoài phạm vi -> 404).
- Mọi lệnh Python chạy trong container (`make test`, `make lint`); máy dev không cài Python.
- Chữ người dùng thấy là tiếng Việt; tên mã, slug, route là tiếng Anh.
- Danh mục quyền (`app/core/permissions.py`) phải khớp `wedding-web/src/core/access/permissions.ts` — sửa cả hai phía cùng lúc.
- Không commit bí mật, `.env`, dữ liệu thật. Seed chỉ chạy ở `local`/`test`.
- Commit/push không đồng nghĩa được phép merge hay triển khai.

## Shipping

- Repository dùng một nhánh chính `main`, không có nhánh tích hợp riêng.
- Mỗi thay đổi đi qua nhánh ngắn `ship/<slug>` và pull request vào `main`.
- Dùng merge commit; triển khai production là bước riêng theo `deploy/README.md`.
