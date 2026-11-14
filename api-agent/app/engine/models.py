"""Modelo de dominio del motor de recomendación (sin dependencias de LangChain ni de FastAPI)."""

import unicodedata
from dataclasses import dataclass, field

SPEC_VERSION = "1.0"
PRIORITIES = ("market_value", "speed", "fewer_pests", "low_labor")
WEIGHTS: dict[int, tuple[float, ...]] = {1: (1.0,), 2: (0.6, 0.4), 3: (0.5, 0.3, 0.2)}
PRIORITY_SHARE = 0.75          # el resto (0.25) es aptitud agronómica
DEFAULT_CYCLES = 4
ALTITUDE_MARGIN_M = 200        # fuera del rango pero dentro del margen = marginal (advertencia)
PH_MARGIN = 0.5
SOLANACEAE_WINDOW = 3          # ciclos sin solanáceas antes de repetir (propuesta, ver F2)
NEUTRAL = 50.0                 # subpuntaje cuando falta el dato
F1B_CROPS = ("maiz", "quinua")  # admiten 2 temporadas seguidas
F2_EXEMPT_FAMILIES = ("Pastos", "Descanso")

CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}
CONFIDENCE_NAME = {1: "low", 2: "medium", 3: "high"}
EDGE_CONFIDENCE = {"source": 3, "general": 2, "inferred": 1, "source5": 1}
EDGE_SEQUENCE_SCORE = {"source": 100.0, "general": 85.0, "inferred": 55.0, "source5": 40.0}

SOIL_SCALES = {
    "fertility": ("low", "medium", "high"),
    "texture": ("sandy", "loam", "clay"),
    "depth": ("shallow", "medium", "deep"),
    "drainage": ("poor", "fair", "good"),
    "compaction": ("yes", "no"),
}
PH_WORDS = {"acidic": 5.0, "neutral": 6.8, "alkaline": 8.0}
IRRIGATION = ("yes", "no")
UNKNOWN = "unknown"


def norm(text: object) -> str:
    """Minúsculas, sin tildes y con espacios simples."""
    s = unicodedata.normalize("NFD", str(text if text is not None else "")).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


@dataclass(frozen=True)
class Crop:
    crop_id: str
    name: str
    family: str | None
    crop_type: str                     # commercial | non_commercial
    tags: tuple[str, ...]
    source5_only: bool
    soil_texture_text: str | None
    ph_min: float | None
    ph_max: float | None
    drainage_required: str | None      # good | None
    min_depth_cm: float | None
    fertility_demand: str | None       # high | medium | low | None
    altitude_min: float | None
    altitude_max: float | None
    requires_irrigation: bool | None
    cycle_min: float | None
    cycle_max: float | None
    pests: tuple[str, ...]
    diseases: tuple[str, ...]
    fixes_nitrogen: bool
    depletes_soil: str | None          # high | medium | low | None
    host_of: tuple[str, ...]           # normalizado con norm()
    breaks_cycles_of: tuple[str, ...]  # normalizado con norm()
    improves_structure: bool | None
    labor_level: int | None
    labor_days_per_ha: float | None
    labor_mechanizable: str | None
    labor_data_type: str | None        # source | inference
    market_level: int | None
    market_price: float | None
    market_unit: str | None
    market_date: str | None
    market_volatility: str | None
    market_confidence: str | None
    market_source_ids: tuple[int, ...]
    geographic_scope: str | None
    confidence: str                    # high | medium | low
    sources: tuple[dict, ...]          # ({source_id, location, detail}, ...)

    @property
    def is_commercial(self) -> bool:
        return self.crop_type == "commercial"

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags


@dataclass(frozen=True)
class Transition:
    from_crop: str
    to_crop: str
    kind: str                          # source | general | inferred | source5
    source_note: str


@dataclass
class KnowledgeBase:
    crops: dict[str, Crop]                             # en el orden del grafo
    edges: dict[str, list[Transition]] = field(default_factory=dict)

    def edge(self, from_crop: str | None, to_crop: str) -> Transition | None:
        if from_crop is None:
            return None
        return next((e for e in self.edges.get(from_crop, []) if e.to_crop == to_crop), None)


@dataclass
class PlotInput:
    """Entrada ya validada y normalizada."""
    previous_crops: list[str | None]   # más reciente primero; None = cultivo desconocido aceptado
    new_land: bool
    soil: dict[str, object]            # fertility, texture, depth, drainage, compaction: str; ph: float | "unknown"
    altitude_masl: float | None
    irrigation: str                    # yes | no | unknown
    priorities: list[str]
    last_pest: list[str]               # normalizado
    rotation_cycles: int = DEFAULT_CYCLES
    use_source5: bool = False

    @property
    def history(self) -> list[str]:
        return [] if self.new_land else [c for c in self.previous_crops if c is not None]
