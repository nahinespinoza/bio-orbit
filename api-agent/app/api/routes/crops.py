"""GET /v1/crops: cultivos que conoce el sistema y su ficha."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import Services, get_services
from app.engine.validation import resolve_crop
from app.repository import crops as crops_repo

router = APIRouter(prefix="/v1/crops", tags=["crops"])


@router.get("", summary="Lista de cultivos")
def list_crops(services: Services = Depends(get_services)) -> list[dict]:
    return crops_repo.list_crops(services.conn)


@router.get("/{crop}", summary="Ficha de un cultivo (acepta nombres comunes: tarwi, ataco, fréjol…)")
def get_crop(crop: str, services: Services = Depends(get_services)) -> dict:
    crop_id, suggestions = resolve_crop(crop, services.kb)
    if crop_id is None:
        raise HTTPException(404, {"code": "UNKNOWN_CROP", "message": f"«{crop}» no está en el pool.", "suggestions": suggestions})
    return crops_repo.get_crop_profile(services.conn, crop_id)
