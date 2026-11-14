"""Esquemas de POST /v1/recommend (motor directo, sin LLM y sin estado)."""

from typing import Literal

from pydantic import BaseModel, Field

Unknown = Literal["unknown"]


class Soil(BaseModel):
    fertility: Literal["low", "medium", "high", "unknown"] = "unknown"
    texture: Literal["sandy", "loam", "clay", "unknown"] = "unknown"
    depth: Literal["shallow", "medium", "deep", "unknown"] = "unknown"
    ph: float | Literal["acidic", "neutral", "alkaline", "unknown"] = "unknown"
    drainage: Literal["poor", "fair", "good", "unknown"] = "unknown"
    compaction: Literal["yes", "no", "unknown"] = "unknown"


class Climate(BaseModel):
    altitude_masl: float | None = Field(default=None, description="Metros sobre el nivel del mar; null = desconocida")
    irrigation: Literal["yes", "no", "unknown"] = "unknown"


class RecommendationInput(BaseModel):
    previous_crops: list[str] | None = Field(default=None, description="Del más reciente al más antiguo")
    new_land: bool = False
    soil: Soil = Soil()
    climate: Climate = Climate()
    # Se validan en el motor (códigos TOO_MANY_PRIORITIES, DUPLICATE_PRIORITIES, INVALID_PRIORITY…).
    priorities: list[str] = Field(default_factory=list, examples=[["market_value", "speed"]])
    last_pest: list[str] = Field(default_factory=list)
    rotation_cycles: int = 4
    use_source5: bool = False

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "previous_crops": ["papa", "cebada"],
                "soil": {"fertility": "medium", "drainage": "good"},
                "climate": {"altitude_masl": 2800, "irrigation": "yes"},
                "priorities": ["speed", "fewer_pests"],
            }]
        }
    }
