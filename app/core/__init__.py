"""Hạ tầng dùng chung cho mọi module.

Quy tắc bất di bất dịch: `app.core` KHÔNG được import bất kỳ thứ gì trong
`app.modules`. Chiều phụ thuộc luôn là module -> core, không bao giờ ngược lại.
"""
