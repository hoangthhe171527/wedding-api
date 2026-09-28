"""Lắp ráp phụ thuộc của `wedding` — nơi DUY NHẤT biết `guest`, `template`, `billing` tồn tại."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.billing import build_plan_gate
from app.modules.guest import build_guest_counter, build_guest_seeder, build_guest_usage_reader
from app.modules.template import build_catalog_defaults_reader, build_template_catalog_reader
from app.modules.wedding.application.use_cases import (
    CheckWeddingPlan,
    GetWedding,
    ListStudios,
    SaveChecklist,
    SaveWedding,
    SetPublication,
    SetupWedding,
    SuggestWording,
)
from app.modules.wedding.infrastructure.external.wording_ai import build_wording_writer
from app.modules.wedding.infrastructure.persistence.repositories import BeanieWeddingRepository


def provide_get_wedding() -> GetWedding:
    return GetWedding(BeanieWeddingRepository())


def provide_setup_wedding() -> SetupWedding:
    return SetupWedding(
        BeanieWeddingRepository(),
        build_guest_seeder(),
        build_catalog_defaults_reader(),
        build_plan_gate(),
    )


def provide_save_wedding() -> SaveWedding:
    return SaveWedding(
        BeanieWeddingRepository(),
        build_template_catalog_reader(),
        build_guest_usage_reader(),
        build_plan_gate(),
    )


def provide_save_checklist() -> SaveChecklist:
    return SaveChecklist(BeanieWeddingRepository())


def provide_set_publication() -> SetPublication:
    return SetPublication(BeanieWeddingRepository(), build_guest_usage_reader(), build_plan_gate())


def provide_check_wedding_plan() -> CheckWeddingPlan:
    return CheckWeddingPlan(
        BeanieWeddingRepository(), build_guest_usage_reader(), build_plan_gate()
    )


def provide_list_studios() -> ListStudios:
    return ListStudios(BeanieWeddingRepository(), build_guest_counter())


def provide_suggest_wording() -> SuggestWording:
    return SuggestWording(BeanieWeddingRepository(), build_wording_writer())


GetWeddingDep = Annotated[GetWedding, Depends(provide_get_wedding)]
SetupWeddingDep = Annotated[SetupWedding, Depends(provide_setup_wedding)]
SaveWeddingDep = Annotated[SaveWedding, Depends(provide_save_wedding)]
SaveChecklistDep = Annotated[SaveChecklist, Depends(provide_save_checklist)]
SetPublicationDep = Annotated[SetPublication, Depends(provide_set_publication)]
ListStudiosDep = Annotated[ListStudios, Depends(provide_list_studios)]
CheckWeddingPlanDep = Annotated[CheckWeddingPlan, Depends(provide_check_wedding_plan)]
SuggestWordingDep = Annotated[SuggestWording, Depends(provide_suggest_wording)]

__all__ = [
    "CheckWeddingPlanDep",
    "GetWeddingDep",
    "ListStudiosDep",
    "SaveChecklistDep",
    "SaveWeddingDep",
    "SetPublicationDep",
    "SetupWeddingDep",
]
