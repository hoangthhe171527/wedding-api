"""Module `media` — ảnh cưới: nhận, chuẩn hoá (bỏ EXIF), lưu, phục vụ qua URL đã ký.

Sở hữu `photos` (siêu dữ liệu) và byte ảnh trong kho object S3; `photo_blobs` chỉ còn cho ảnh cũ.
"""

from app.modules.media.infrastructure.external.account_deletion import build_account_data_deleter
from app.modules.media.infrastructure.external.public_photos import build_public_photo_lister
from app.modules.media.interfaces.http.router import router

__all__ = ["build_account_data_deleter", "build_public_photo_lister", "router"]
