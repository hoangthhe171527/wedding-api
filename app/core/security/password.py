"""Băm mật khẩu bằng Argon2id."""

from __future__ import annotations

import asyncio
import weakref
from typing import Final

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

# Tham số theo khuyến nghị OWASP cho Argon2id (19 MiB, 2 lượt, song song 1).
_hasher: Final[PasswordHasher] = PasswordHasher(
    time_cost=2,
    memory_cost=19_456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

MIN_PASSWORD_LENGTH: Final[int] = 8


def hash_password(plain: str) -> str:
    """Băm mật khẩu thô. Chuỗi trả về đã gồm salt và tham số."""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """So khớp mật khẩu thô với chuỗi băm. Không bao giờ ném lỗi."""
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


#: Số lượt băm chạy cùng lúc trong MỘT tiến trình: mỗi lượt Argon2 giữ ~19 MiB RAM
#: và một lõi CPU. Dồn quá mức này thì xếp hàng thay vì làm cạn bộ nhớ.
_HASH_SLOTS: Final[int] = 4
#: Mỗi event loop một semaphore: semaphore của asyncio gắn với loop tạo ra nó.
_slots: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = (
    weakref.WeakKeyDictionary()
)


def _semaphore() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    slots = _slots.get(loop)
    if slots is None:
        slots = _slots[loop] = asyncio.Semaphore(_HASH_SLOTS)
    return slots


async def hash_password_async(plain: str) -> str:
    """Như `hash_password` nhưng chạy trong thread — không chặn event loop.

    Argon2 cố ý tốn ~30-80ms CPU; chạy thẳng trên event loop là mỗi lượt đăng nhập
    làm đứng MỌI request khác của tiến trình (kể cả web thiệp công khai).
    """
    async with _semaphore():
        return await asyncio.to_thread(hash_password, plain)


async def verify_password_async(plain: str, hashed: str) -> bool:
    """Như `verify_password` nhưng chạy trong thread (argon2-cffi nhả GIL)."""
    async with _semaphore():
        return await asyncio.to_thread(verify_password, plain, hashed)


def needs_rehash(hashed: str) -> bool:
    """Chuỗi băm có được tạo bằng tham số cũ hơn hiện tại hay không."""
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return True


__all__ = [
    "MIN_PASSWORD_LENGTH",
    "hash_password",
    "hash_password_async",
    "needs_rehash",
    "verify_password",
    "verify_password_async",
]
