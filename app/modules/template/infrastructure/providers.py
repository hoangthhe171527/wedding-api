"""Lắp ráp phụ thuộc của `template`."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.template.application.use_cases import (
    EnsureCatalog,
    GetCatalogDefaults,
    ListTemplates,
    SaveCatalogDefaults,
    UpdateTemplate,
)
from app.modules.template.infrastructure.persistence.defaults_repository import (
    BeanieCatalogDefaultsRepository,
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

__all__ = [
    "GetCatalogDefaultsDep",
    "ListTemplatesDep",
    "SaveCatalogDefaultsDep",
    "UpdateTemplateDep",
    "build_ensure_catalog",
]
