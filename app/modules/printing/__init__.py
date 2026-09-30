"""Module `printing` — yêu cầu in thiệp giấy. Giá tư vấn qua Zalo, không thanh toán online.

Sở hữu `print_requests`.
"""

from app.modules.printing.infrastructure.external.account_deletion import build_account_data_deleter
from app.modules.printing.interfaces.http.router import router

__all__ = ["build_account_data_deleter", "router"]
