"""Module `wedding` — thông tin cưới, lộ trình chuẩn bị, xuất bản web thiệp.

Sở hữu `weddings` (đúng một đám cưới mỗi xưởng).
"""

from app.modules.wedding.infrastructure.external.account_deletion import build_account_data_deleter
from app.modules.wedding.infrastructure.external.demo_seeder import build_demo_wedding_seeder
from app.modules.wedding.infrastructure.external.guest_limit import build_published_guest_limit
from app.modules.wedding.infrastructure.external.published_reader import (
    build_published_wedding_reader,
)
from app.modules.wedding.interfaces.http.router import router

__all__ = [
    "build_account_data_deleter",
    "build_demo_wedding_seeder",
    "build_published_guest_limit",
    "build_published_wedding_reader",
    "router",
]
