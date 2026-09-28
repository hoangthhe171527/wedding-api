"""Use case của `template`."""

from app.modules.template.application.use_cases.catalog_defaults import (
    GetCatalogDefaults,
    SaveCatalogDefaults,
)
from app.modules.template.application.use_cases.ensure_catalog import EnsureCatalog
from app.modules.template.application.use_cases.list_templates import ListTemplates
from app.modules.template.application.use_cases.update_template import (
    TemplatePatch,
    UpdateTemplate,
)

__all__ = [
    "EnsureCatalog",
    "GetCatalogDefaults",
    "ListTemplates",
    "SaveCatalogDefaults",
    "TemplatePatch",
    "UpdateTemplate",
]
