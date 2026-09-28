"""Use case: đọc / lưu mặc định hệ thống (mẫu theo nhóm khách, câu chữ theo giọng văn)."""

from __future__ import annotations

from app.core import audit
from app.core.context import ActorContext
from app.core.errors import ValidationError
from app.modules.template.application.ports import DefaultsStore, TemplateKeys
from app.modules.template.domain.defaults import CatalogDefaults, clean_defaults, defaults_errors


class GetCatalogDefaults:
    def __init__(self, store: DefaultsStore) -> None:
        self._store = store

    async def execute(self) -> CatalogDefaults:
        return await self._store.get()


class SaveCatalogDefaults:
    def __init__(self, store: DefaultsStore, templates: TemplateKeys) -> None:
        self._store = store
        self._templates = templates

    async def execute(self, actor: ActorContext, defaults: CatalogDefaults) -> CatalogDefaults:
        """Raises: ValidationError (nhóm / mẫu / giọng văn / ô câu chữ không tồn tại)."""
        cleaned = clean_defaults(defaults)
        errors = defaults_errors(cleaned, known_templates=await self._templates.keys())
        if errors:
            raise ValidationError(
                "Mặc định hệ thống chưa hợp lệ.", code="defaults_invalid", errors=errors
            )
        saved = await self._store.save(cleaned, actor_id=actor.user_id)
        await audit.record(
            "catalog.defaults_saved",
            actor_id=actor.user_id,
            target_type="catalog_defaults",
            target_id="system",
            details={
                "group_templates": saved.group_templates,
                "default_template": saved.default_template,
                "wording_tones": sorted(saved.wording),
                "message_tones": sorted(saved.messages),
            },
        )
        return saved


__all__ = ["GetCatalogDefaults", "SaveCatalogDefaults"]
