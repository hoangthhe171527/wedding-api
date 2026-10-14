"""Use case của `template`."""

from app.modules.template.application.use_cases.catalog_defaults import (
    GetCatalogDefaults,
    SaveCatalogDefaults,
)
from app.modules.template.application.use_cases.ensure_catalog import EnsureCatalog
from app.modules.template.application.use_cases.intros import (
    DeleteIntro,
    IntroMedia,
    IntroPatch,
    IntroView,
    ListIntros,
    ReadIntro,
    UpdateIntro,
    UploadIntro,
)
from app.modules.template.application.use_cases.list_templates import ListTemplates
from app.modules.template.application.use_cases.update_template import (
    TemplatePatch,
    UpdateTemplate,
)

__all__ = [
    "DeleteIntro",
    "EnsureCatalog",
    "GetCatalogDefaults",
    "IntroMedia",
    "IntroPatch",
    "IntroView",
    "ListIntros",
    "ListTemplates",
    "ReadIntro",
    "SaveCatalogDefaults",
    "TemplatePatch",
    "UpdateIntro",
    "UpdateTemplate",
    "UploadIntro",
]
