"""Module `invitation` — web thiệp công khai cho khách mời.

**Chỉ đọc**: ghép dữ liệu từ `wedding`, `guest`, `media` qua cổng; không sở hữu
collection nào và không ghi gì.
"""

from app.modules.invitation.interfaces.http.router import router

__all__ = ["router"]
