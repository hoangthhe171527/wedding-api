"""Lắp ráp phụ thuộc của `printing`."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.printing.application.use_cases import (
    CancelPrintRequest,
    ListAllPrintRequests,
    ListPrintRequests,
    SubmitPrintRequest,
    UpdatePrintRequest,
)
from app.modules.printing.infrastructure.persistence.repositories import (
    BeaniePrintRequestRepository,
)


def provide_submit() -> SubmitPrintRequest:
    return SubmitPrintRequest(BeaniePrintRequestRepository())


def provide_list() -> ListPrintRequests:
    return ListPrintRequests(BeaniePrintRequestRepository())


def provide_cancel() -> CancelPrintRequest:
    return CancelPrintRequest(BeaniePrintRequestRepository())


def provide_list_all() -> ListAllPrintRequests:
    return ListAllPrintRequests(BeaniePrintRequestRepository())


def provide_update() -> UpdatePrintRequest:
    return UpdatePrintRequest(BeaniePrintRequestRepository())


SubmitPrintRequestDep = Annotated[SubmitPrintRequest, Depends(provide_submit)]
ListPrintRequestsDep = Annotated[ListPrintRequests, Depends(provide_list)]
CancelPrintRequestDep = Annotated[CancelPrintRequest, Depends(provide_cancel)]
ListAllPrintRequestsDep = Annotated[ListAllPrintRequests, Depends(provide_list_all)]
UpdatePrintRequestDep = Annotated[UpdatePrintRequest, Depends(provide_update)]

__all__ = [
    "CancelPrintRequestDep",
    "ListAllPrintRequestsDep",
    "ListPrintRequestsDep",
    "SubmitPrintRequestDep",
    "UpdatePrintRequestDep",
]
