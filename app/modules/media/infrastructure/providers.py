"""Lắp ráp phụ thuộc của `media`."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.media.application.use_cases import (
    DeletePhoto,
    ListPhotos,
    MakeCover,
    ReadPhoto,
    ReorderPhotos,
    UpdatePhotoFocus,
    UploadPhoto,
)
from app.modules.media.infrastructure.external.pillow_processor import PillowImageProcessor
from app.modules.media.infrastructure.persistence.repositories import BeaniePhotoRepository


def provide_list_photos() -> ListPhotos:
    return ListPhotos(BeaniePhotoRepository())


def provide_upload_photo() -> UploadPhoto:
    return UploadPhoto(BeaniePhotoRepository(), PillowImageProcessor())


def provide_make_cover() -> MakeCover:
    return MakeCover(BeaniePhotoRepository())


def provide_delete_photo() -> DeletePhoto:
    return DeletePhoto(BeaniePhotoRepository())


def provide_read_photo() -> ReadPhoto:
    return ReadPhoto(BeaniePhotoRepository())


def provide_reorder_photos() -> ReorderPhotos:
    return ReorderPhotos(BeaniePhotoRepository())


def provide_update_photo_focus() -> UpdatePhotoFocus:
    return UpdatePhotoFocus(BeaniePhotoRepository())


ListPhotosDep = Annotated[ListPhotos, Depends(provide_list_photos)]
UploadPhotoDep = Annotated[UploadPhoto, Depends(provide_upload_photo)]
MakeCoverDep = Annotated[MakeCover, Depends(provide_make_cover)]
DeletePhotoDep = Annotated[DeletePhoto, Depends(provide_delete_photo)]
ReadPhotoDep = Annotated[ReadPhoto, Depends(provide_read_photo)]
ReorderPhotosDep = Annotated[ReorderPhotos, Depends(provide_reorder_photos)]
UpdatePhotoFocusDep = Annotated[UpdatePhotoFocus, Depends(provide_update_photo_focus)]

__all__ = [
    "DeletePhotoDep",
    "ListPhotosDep",
    "MakeCoverDep",
    "ReadPhotoDep",
    "ReorderPhotosDep",
    "UpdatePhotoFocusDep",
    "UploadPhotoDep",
]
