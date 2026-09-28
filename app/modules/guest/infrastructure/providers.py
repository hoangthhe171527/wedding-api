"""Lắp ráp phụ thuộc của `guest` — nơi DUY NHẤT biết `template` tồn tại."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.guest.application.ports import PlanGuestLimit
from app.modules.guest.application.use_cases import (
    CreateGuest,
    DeleteGuest,
    DeleteWish,
    ImportGuests,
    ListGuests,
    ListWishes,
    UpdateGuest,
)
from app.modules.guest.infrastructure.persistence.repositories import (
    BeanieGuestRepository,
    BeanieWishRepository,
)
from app.modules.template import build_template_catalog_reader


def provide_list_guests() -> ListGuests:
    return ListGuests(BeanieGuestRepository())


def _plan_guest_limit() -> PlanGuestLimit:
    # Import lười: `wedding` phụ thuộc `guest` (đếm khách, khách mẫu) — import ở đầu
    # file là vòng import giữa hai barrel lúc khởi động.
    from app.modules.wedding import build_published_guest_limit

    return build_published_guest_limit()


def provide_create_guest() -> CreateGuest:
    return CreateGuest(
        BeanieGuestRepository(), build_template_catalog_reader(), _plan_guest_limit()
    )


def provide_update_guest() -> UpdateGuest:
    return UpdateGuest(BeanieGuestRepository(), build_template_catalog_reader())


def provide_delete_guest() -> DeleteGuest:
    return DeleteGuest(BeanieGuestRepository())


def provide_import_guests() -> ImportGuests:
    return ImportGuests(BeanieGuestRepository(), _plan_guest_limit())


def provide_list_wishes() -> ListWishes:
    return ListWishes(BeanieWishRepository())


def provide_delete_wish() -> DeleteWish:
    return DeleteWish(BeanieWishRepository())


ListWishesDep = Annotated[ListWishes, Depends(provide_list_wishes)]
DeleteWishDep = Annotated[DeleteWish, Depends(provide_delete_wish)]
ListGuestsDep = Annotated[ListGuests, Depends(provide_list_guests)]
CreateGuestDep = Annotated[CreateGuest, Depends(provide_create_guest)]
UpdateGuestDep = Annotated[UpdateGuest, Depends(provide_update_guest)]
DeleteGuestDep = Annotated[DeleteGuest, Depends(provide_delete_guest)]
ImportGuestsDep = Annotated[ImportGuests, Depends(provide_import_guests)]

__all__ = [
    "CreateGuestDep",
    "DeleteGuestDep",
    "DeleteWishDep",
    "ImportGuestsDep",
    "ListGuestsDep",
    "ListWishesDep",
    "UpdateGuestDep",
]
