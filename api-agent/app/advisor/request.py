"""Petición de POST /v1/recommendations (las respuestas de la pantalla de opciones) y su traducción al motor."""

from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["market_value", "speed", "fewer_pests", "low_labor"]

PRIORITY_LABEL = {"market_value": "Valor de venta", "speed": "Cosechar antes",
                  "fewer_pests": "Menos plagas", "low_labor": "Menos trabajo"}
IRRIGATION = {"rain_only": "no", "pump": "yes", "canal": "yes", "sprinkler_drip": "yes", "manual": "yes"}
DRAINAGE = {"no": "good", "briefly": "fair", "long": "poor"}
IRRIGATION_TEXT = {"rain_only": "solo lluvia", "pump": "bomba", "canal": "acequia o canal",
                   "sprinkler_drip": "aspersión o goteo", "manual": "manual (regadera o manguera)"}
WATERLOGGING_TEXT = {"no": "no se empoza", "briefly": "se empoza un poco", "long": "se empoza por mucho tiempo"}
NEW_LAND = "new_land"


class AdvisorRequest(BaseModel):
    previous_crop: str = Field(min_length=1, description="Último cultivo (id o nombre del pool) o «new_land»",
                               examples=["cebada"])
    priority: Priority = Field(description="Una sola prioridad, como en la pantalla")
    irrigation: Literal["rain_only", "pump", "canal", "sprinkler_drip", "manual"]
    waterlogging: Literal["no", "briefly", "long"] = Field(description="¿Se empoza el agua?")
    # MVP: se acepta sin validar y se IGNORA; siempre se usa la copia del servidor (knowledge/structured/remote_sensing.json).
    altitude_masl: float | None = Field(default=None, ge=-50, le=6000,
                                        description="Altitud del lote; si falta se usa la de la parcela monitoreada")
    fertility: Literal["low", "medium", "high"] | None = Field(default=None, description="Fertilidad del suelo, si se conoce")
    remote_sensing: object = Field(default=None, description="Ignorado en el MVP: se usa la copia del servidor")

    model_config = {"json_schema_extra": {"examples": [
        {"previous_crop": "cebada", "priority": "low_labor", "irrigation": "rain_only", "waterlogging": "long"}]}}


def to_plot_raw(req: AdvisorRequest, crop_id: str | None, altitude_masl: float | None) -> dict:
    """Petición → entrada del motor. `crop_id` ya resuelto (None si es tierra nueva)."""
    raw: dict = {"priorities": [req.priority],
                 "climate": {"altitude_masl": altitude_masl, "irrigation": IRRIGATION[req.irrigation]},
                 "soil": {"drainage": DRAINAGE[req.waterlogging]}}
    if req.fertility:
        raw["soil"]["fertility"] = req.fertility
    if crop_id is None:
        raw["new_land"] = True
    else:
        raw["previous_crops"] = [crop_id]
    return raw
