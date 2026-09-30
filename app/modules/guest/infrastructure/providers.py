"""Lắp ráp phụ thuộc của `guest` — nơi DUY NHẤT biết `template` tồn tại."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.guest.application.ports import PlanGuestLimit
from app.modules.guest.application.use_cases import (
    CreateGuest,
    CreateLink,
    DeleteGuest,
    DeleteLink,
    DeleteWish,
    ImportGuests,
    ListGuests,
    ListLinks,
    ListWishes,
    UpdateGuest,
    UpdateLink,
)
from app.modules.guest.infrastructure.persistence.repositories import (
    BeanieGuestRepository,
    BeanieInviteLinkRepository,
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


def provide_list_links() -> ListLinks:
    return ListLinks(BeanieInviteLinkRepository())


def provide_create_link() -> CreateLink:
    return CreateLink(BeanieInviteLinkRepository(), build_template_catalog_reader())


def provide_update_link() -> UpdateLink:
    return UpdateLink(BeanieInviteLinkRepository(), build_template_catalog_reader())


def provide_delete_link() -> DeleteLink:
    return DeleteLink(BeanieInviteLinkRepository())


ListLinksDep = Annotated[ListLinks, Depends(provide_list_links)]
CreateLinkDep = Annotated[CreateLink, Depends(provide_create_link)]
UpdateLinkDep = Annotated[UpdateLink, Depends(provide_update_link)]
DeleteLinkDep = Annotated[DeleteLink, Depends(provide_delete_link)]
ListWishesDep = Annotated[ListWishes, Depends(provide_list_wishes)]
DeleteWishDep = Annotated[DeleteWish, Depends(provide_delete_wish)]
ListGuestsDep = Annotated[ListGuests, Depends(provide_list_guests)]
CreateGuestDep = Annotated[CreateGuest, Depends(provide_create_guest)]
UpdateGuestDep = Annotated[UpdateGuest, Depends(provide_update_guest)]
DeleteGuestDep = Annotated[DeleteGuest, Depends(provide_delete_guest)]
ImportGuestsDep = Annotated[ImportGuests, Depends(provide_import_guests)]

__all__ = [
    "CreateGuestDep",
    "CreateLinkDep",
    "DeleteGuestDep",
    "DeleteLinkDep",
    "DeleteWishDep",
    "ImportGuestsDep",
    "ListGuestsDep",
    "ListLinksDep",
    "ListWishesDep",
    "UpdateGuestDep",
    "UpdateLinkDep",
]
