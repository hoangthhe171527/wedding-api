"""Lắp ráp phụ thuộc của `template`."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.template.application.use_cases import (
    DeleteIntro,
    EnsureCatalog,
    GetCatalogDefaults,
    ListIntros,
    ListTemplates,
    ReadIntro,
    SaveCatalogDefaults,
    UpdateIntro,
    UpdateTemplate,
    UploadIntro,
)
from app.modules.template.infrastructure.persistence.defaults_repository import (
    BeanieCatalogDefaultsRepository,
)
from app.modules.template.infrastructure.persistence.intro_repository import (
    BeanieIntroRepository,
)
from app.modules.template.infrastructure.persistence.repositories import BeanieTemplateRepository


def provide_list_templates() -> ListTemplates:
    return ListTemplates(BeanieTemplateRepository())


def provide_update_template() -> UpdateTemplate:
    return UpdateTemplate(BeanieTemplateRepository())


def build_ensure_catalog() -> EnsureCatalog:
    return EnsureCatalog(BeanieTemplateRepository())


def provide_get_defaults() -> GetCatalogDefaults:
    return GetCatalogDefaults(BeanieCatalogDefaultsRepository())


def provide_save_defaults() -> SaveCatalogDefaults:
    return SaveCatalogDefaults(BeanieCatalogDefaultsRepository(), BeanieTemplateRepository())


ListTemplatesDep = Annotated[ListTemplates, Depends(provide_list_templates)]
UpdateTemplateDep = Annotated[UpdateTemplate, Depends(provide_update_template)]

GetCatalogDefaultsDep = Annotated[GetCatalogDefaults, Depends(provide_get_defaults)]
SaveCatalogDefaultsDep = Annotated[SaveCatalogDefaults, Depends(provide_save_defaults)]


def provide_list_intros() -> ListIntros:
    return ListIntros(BeanieIntroRepository())


def provide_upload_intro() -> UploadIntro:
    return UploadIntro(BeanieIntroRepository())


def provide_update_intro() -> UpdateIntro:
    return UpdateIntro(BeanieIntroRepository())


def provide_delete_intro() -> DeleteIntro:
    return DeleteIntro(BeanieIntroRepository())


def provide_read_intro() -> ReadIntro:
    return ReadIntro(BeanieIntroRepository())


ListIntrosDep = Annotated[ListIntros, Depends(provide_list_intros)]
UploadIntroDep = Annotated[UploadIntro, Depends(provide_upload_intro)]
UpdateIntroDep = Annotated[UpdateIntro, Depends(provide_update_intro)]
DeleteIntroDep = Annotated[DeleteIntro, Depends(provide_delete_intro)]
ReadIntroDep = Annotated[ReadIntro, Depends(provide_read_intro)]

__all__ = [
    "DeleteIntroDep",
    "GetCatalogDefaultsDep",
    "ListIntrosDep",
    "ListTemplatesDep",
    "ReadIntroDep",
    "SaveCatalogDefaultsDep",
    "UpdateIntroDep",
    "UpdateTemplateDep",
    "UploadIntroDep",
    "build_ensure_catalog",
]
