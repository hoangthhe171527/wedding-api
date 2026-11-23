"""Gửi email đặt lại mật khẩu qua SMTP tiêu chuẩn."""

from __future__ import annotations

import asyncio
import html
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_SMTP_SSL_PORT = 465
_SMTP_TIMEOUT_SECONDS = 10


class SmtpPasswordResetMailer:
    """Hiện thực `PasswordResetMailer` dùng `smtplib` trong thread riêng."""

    async def send_reset_link(
        self, *, to_email: str, full_name: str, reset_url: str, ttl_minutes: int
    ) -> bool:
        cfg = get_settings()
        if not cfg.SMTP_HOST:
            if cfg.is_local:
                log.info(
                    "password_reset_link_local",
                    to_email=to_email,
                    reset_url=reset_url,
                )
            else:
                log.warning("password_reset_smtp_unconfigured", to_email=to_email)
            return False

        sender = cfg.SMTP_FROM or cfg.SMTP_USER or "no-reply@thiephy.vn"
        message = EmailMessage()
        message["Subject"] = "Đặt lại mật khẩu · Xưởng Thiệp Hỷ"
        message["From"] = sender
        message["To"] = to_email
        greeting_name = full_name.strip() or "bạn"
        message.set_content(
            f"Xin chào {greeting_name},\n\n"
            f"Bạn vừa yêu cầu đặt lại mật khẩu tài khoản Xưởng Thiệp Hỷ.\n"
            f"Nhấn vào liên kết sau (hết hạn sau {ttl_minutes} phút):\n{reset_url}\n\n"
            "Nếu không phải bạn yêu cầu, vui lòng bỏ qua email này."
        )
        safe_name = html.escape(greeting_name)
        safe_url = html.escape(reset_url, quote=True)
        message.add_alternative(
            f"""
<html>
  <body style="font-family:sans-serif;line-height:1.6;color:#222;">
    <p>Xin chào <strong>{safe_name}</strong>,</p>
    <p>Bạn vừa yêu cầu đặt lại mật khẩu tài khoản <strong>Xưởng Thiệp Hỷ</strong>.</p>
    <p>
      <a
        href="{safe_url}"
        style="display:inline-block;padding:10px 18px;background:#8B1E28;color:#fff;
               text-decoration:none;border-radius:8px;font-weight:600;"
      >
        Đặt lại mật khẩu
      </a>
    </p>
    <p style="font-size:13px;color:#555;">
      Liên kết có hiệu lực trong <strong>{ttl_minutes} phút</strong> và chỉ dùng được một lần.
      Nếu không phải bạn yêu cầu, vui lòng bỏ qua email này.
    </p>
  </body>
</html>
""".strip(),
            subtype="html",
        )

        def _send() -> None:
            if cfg.SMTP_PORT == _SMTP_SSL_PORT:
                with smtplib.SMTP_SSL(
                    cfg.SMTP_HOST, cfg.SMTP_PORT, timeout=_SMTP_TIMEOUT_SECONDS
                ) as smtp:
                    if cfg.SMTP_USER and cfg.SMTP_PASSWORD:
                        smtp.login(cfg.SMTP_USER, cfg.SMTP_PASSWORD)
                    smtp.send_message(message)
                return
            with smtplib.SMTP(cfg.SMTP_HOST, cfg.SMTP_PORT, timeout=_SMTP_TIMEOUT_SECONDS) as smtp:
                if cfg.SMTP_USE_TLS:
                    smtp.starttls()
                if cfg.SMTP_USER and cfg.SMTP_PASSWORD:
                    smtp.login(cfg.SMTP_USER, cfg.SMTP_PASSWORD)
                smtp.send_message(message)

        try:
            await asyncio.to_thread(_send)
        except Exception as exc:
            log.error("password_reset_mail_failed", to_email=to_email, error=str(exc))
            return False
        log.info("password_reset_mail_sent", to_email=to_email)
        return True


__all__ = ["SmtpPasswordResetMailer"]
