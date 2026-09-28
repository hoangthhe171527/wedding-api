"""Lắp ráp phụ thuộc của `invitation` — cắm các cổng vào barrel của chủ sở hữu."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.billing import build_entitlement_reader
from app.modules.guest import build_guest_by_code_reader, build_guest_responder
from app.modules.invitation.application.use_cases import (
    GetInvitation,
    ListPublicWishes,
    RecordOpen,
    SubmitReply,
)
from app.modules.media import build_public_photo_lister
from app.modules.template import build_catalog_defaults_reader
from app.modules.wedding import build_published_wedding_reader


def provide_get_invitation() -> GetInvitation:
    return GetInvitation(
        build_published_wedding_reader(),
        build_guest_by_code_reader(),
        build_public_photo_lister(),
        build_entitlement_reader(),
        build_catalog_defaults_reader(),
    )


def provide_submit_reply() -> SubmitReply:
    return SubmitReply(
        build_published_wedding_reader(), build_guest_responder(), build_entitlement_reader()
    )


def provide_list_public_wishes() -> ListPublicWishes:
    return ListPublicWishes(build_published_wedding_reader(), build_guest_responder())


def provide_record_open() -> RecordOpen:
    return RecordOpen(
        build_published_wedding_reader(), build_guest_responder(), build_entitlement_reader()
    )


GetInvitationDep = Annotated[GetInvitation, Depends(provide_get_invitation)]
SubmitReplyDep = Annotated[SubmitReply, Depends(provide_submit_reply)]
ListPublicWishesDep = Annotated[ListPublicWishes, Depends(provide_list_public_wishes)]

RecordOpenDep = Annotated[RecordOpen, Depends(provide_record_open)]

__all__ = ["GetInvitationDep", "ListPublicWishesDep", "RecordOpenDep", "SubmitReplyDep"]
