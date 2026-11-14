"""Validación y normalización de la entrada del motor.

Códigos de error en inglés; mensajes en español (los lee el agente y se los transmite al agricultor).
`partial=True` valida solo los campos presentes: lo usa la herramienta update_plot del agente.
"""

import difflib
from dataclasses import dataclass, field

from app.engine.models import (
    DEFAULT_CYCLES, IRRIGATION, PH_WORDS, PRIORITIES, SOIL_SCALES, UNKNOWN, KnowledgeBase, PlotInput, norm,
)

ALIASES = {
    "papas": "papa", "frijol": "frejol", "frijoles": "frejol", "frejoles": "frejol", "poroto": "frejol",
    "tarwi": "chocho", "lupino": "chocho", "chochos": "chocho",
    "ataco": "amaranto", "kiwicha": "amaranto", "sangorache": "amaranto",
    "zanahoria blanca": "arracacha", "canihua": "qaniwa", "kaniwa": "qaniwa", "qanihua": "qaniwa",
    "ulluco": "olluco", "mellocos": "melloco", "isano": "mashua", "mashwa": "mashua",
    "vicia": "abono", "trebol": "abono", "abono verde": "abono", "abonos verdes": "abono",
    "alfalfa": "pasto", "pradera": "pasto", "pastos": "pasto", "descanso": "barbecho",
    "habas": "haba", "arvejas": "arveja", "lentejas": "lenteja", "maiz suave": "maiz", "maiz duro": "maiz",
    "choclo": "maiz", "tomates": "tomate", "soja": "soya", "ocas": "oca",
}
MAX_HISTORY = 4


@dataclass
class ValidationResult:
    errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    plot: PlotInput | None = None
    normalized: dict = field(default_factory=dict)   # JSON-serializable (para el estado del agente)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, code: str, message: str, **extra: object) -> None:
        self.errors.append({"code": code, "message": message, **extra})

    def warn(self, code: str, message: str, **extra: object) -> None:
        self.warnings.append({"code": code, "message": message, **extra})


def resolve_crop(text: str, kb: KnowledgeBase) -> tuple[str | None, list[str]]:
    """Nombre libre → (crop_id, sugerencias)."""
    n = norm(text)
    if n in kb.crops:
        return n, []
    if n in ALIASES and ALIASES[n] in kb.crops:
        return ALIASES[n], []
    for cid, crop in kb.crops.items():
        if norm(crop.name) == n:
            return cid, []
    options = list(kb.crops) + list(ALIASES)
    close = difflib.get_close_matches(n, options, n=5, cutoff=0.6)
    return None, list(dict.fromkeys(ALIASES.get(c, c) for c in close))[:3]


def _is_unknown(value: object) -> bool:
    return value is None or norm(value) in ("", UNKNOWN, "desconocido", "no se", "no sabe")


def validate_plot(raw: dict, kb: KnowledgeBase, *, allow_unknown_crops: bool = False,
                  partial: bool = False) -> ValidationResult:
    r = ValidationResult()
    out: dict = {}

    # --- Cultivos previos / tierra nueva ---
    new_land = raw.get("new_land") is True
    prev = raw.get("previous_crops")
    if isinstance(prev, str):
        prev = [p for p in prev.split(",") if p.strip()]
    previous: list[str | None] = []
    if new_land and prev:
        r.error("NEW_LAND_WITH_CROPS", "No se puede combinar «tierra nueva» con cultivos previos. Aclara cuál aplica.")
    elif new_land:
        out["new_land"] = True
        out["previous_crops"] = []
    elif prev:
        errors_before = len(r.errors)
        for item in prev:
            cid, suggestions = resolve_crop(item, kb)
            if cid:
                previous.append(cid)
            elif allow_unknown_crops:
                previous.append(None)
                r.warn("UNKNOWN_PREVIOUS_CROP", f"«{item}» no está en el pool; se trata como «desconocido»: "
                                                "no se aplican F1/F2/F3 ni reglas del grafo a ese ciclo.")
            else:
                r.error("UNKNOWN_CROP", f"«{item}» no está en el pool de cultivos.", value=item, suggestions=suggestions)
        if len(previous) > 6:
            r.warn("LONG_HISTORY", "Se usan solo los 4 ciclos más recientes; el resto se ignora.")
        previous = previous[:MAX_HISTORY]
        if previous and all(p is None for p in previous):
            r.error("ALL_PREVIOUS_UNKNOWN", "Ningún cultivo previo es reconocible; pide que los nombre de nuevo o indica «tierra nueva».")
        if len(r.errors) == errors_before:  # la secuencia se guarda completa o no se guarda: el orden importa
            out["new_land"] = False
            out["previous_crops"] = previous
    elif not partial:
        r.error("MISSING_PREVIOUS_CROPS", "Faltan los cultivos previos (del más reciente al más antiguo) o indicar «tierra nueva».")

    # --- Suelo ---
    soil_raw = raw.get("soil") or {}
    soil: dict[str, object] = {}
    for key, valid in SOIL_SCALES.items():
        if partial and key not in soil_raw:
            continue
        value = soil_raw.get(key)
        if _is_unknown(value):
            soil[key] = UNKNOWN
        elif norm(value) in valid:
            soil[key] = norm(value)
        else:
            r.error("INVALID_VALUE", f"soil.{key} = «{value}» no es válido. Opciones: {', '.join(valid)} o unknown.", field=f"soil.{key}")
    if not partial or "ph" in soil_raw:
        ph = soil_raw.get("ph")
        if _is_unknown(ph):
            soil["ph"] = UNKNOWN
        elif isinstance(ph, (int, float)) and not isinstance(ph, bool) or str(ph).replace(",", ".").replace(".", "", 1).isdigit():
            v = float(str(ph).replace(",", "."))
            if 3 <= v <= 10:
                soil["ph"] = v
            else:
                r.error("INVALID_VALUE", f"soil.ph = {ph} fuera de rango plausible (3 a 10).", field="soil.ph")
        elif norm(ph) in PH_WORDS:
            soil["ph"] = PH_WORDS[norm(ph)]
        else:
            r.error("INVALID_VALUE", f"soil.ph = «{ph}» no es válido. Usa un número (3 a 10) o acidic/neutral/alkaline.", field="soil.ph")
    if soil:
        out["soil"] = soil
    unknown_soil = [k for k, v in soil.items() if v == UNKNOWN]
    if unknown_soil and not partial:
        r.warn("UNKNOWN_SOIL", f"Datos de suelo desconocidos: {', '.join(unknown_soil)}. No se usan para descartar ni "
                               "para puntuar (puntúan neutro y bajan la confianza).", fields=unknown_soil)

    # --- Clima ---
    climate_raw = raw.get("climate") or {}
    climate: dict[str, object] = {}
    if not partial or "altitude_masl" in climate_raw:
        alt = climate_raw.get("altitude_masl")
        if _is_unknown(alt):
            climate["altitude_masl"] = None
        else:
            try:
                a = float(alt)
            except (TypeError, ValueError):
                a = None
            if a is None or not -50 <= a <= 6000:
                r.error("INVALID_VALUE", f"climate.altitude_masl = «{alt}» no es válida (−50 a 6000).", field="climate.altitude_masl")
            else:
                climate["altitude_masl"] = a
    if not partial or "irrigation" in climate_raw:
        irr = climate_raw.get("irrigation")
        if _is_unknown(irr):
            climate["irrigation"] = UNKNOWN
        elif norm(irr) in IRRIGATION:
            climate["irrigation"] = norm(irr)
        else:
            r.error("INVALID_VALUE", f"climate.irrigation = «{irr}» no es válido. Opciones: yes, no o unknown.", field="climate.irrigation")
    if climate:
        out["climate"] = climate
    if not partial and climate.get("altitude_masl") is None:
        r.warn("UNKNOWN_ALTITUDE", "Sin altitud no se puede filtrar por clima (F4); conviene preguntarla.")

    # --- Prioridades ---
    pr = raw.get("priorities")
    if isinstance(pr, str):
        pr = [p for p in pr.split(",") if p.strip()]
    if pr is None and partial:
        pass
    elif not pr:
        r.error("NO_PRIORITIES", "Faltan de 1 a 3 prioridades en orden de importancia: " + ", ".join(PRIORITIES) + ".")
    else:
        clean = [norm(p).replace(" ", "_") for p in pr]
        bad = [p for p in clean if p not in PRIORITIES]
        if bad:
            r.error("INVALID_PRIORITY", f"Prioridad no reconocida: {', '.join(bad)}. Opciones: {', '.join(PRIORITIES)}.", values=bad)
        if len(set(clean)) != len(clean):
            r.error("DUPLICATE_PRIORITIES", "Hay prioridades repetidas; cada una puede aparecer una sola vez.")
        if len(clean) > 3:
            r.error("TOO_MANY_PRIORITIES", f"Se indicaron {len(clean)} prioridades; el máximo es 3. Pide al agricultor "
                                           "que elija cuáles conserva (no se recortan automáticamente).")
        if not bad and len(set(clean)) == len(clean) and len(clean) <= 3:
            out["priorities"] = clean

    # --- Opciones ---
    if not partial or "rotation_cycles" in raw:
        cycles = raw.get("rotation_cycles", DEFAULT_CYCLES)
        if not isinstance(cycles, int) or isinstance(cycles, bool) or not 1 <= cycles <= 8:
            r.error("INVALID_VALUE", f"rotation_cycles = «{cycles}» no es válido (entero de 1 a 8).", field="rotation_cycles")
        else:
            out["rotation_cycles"] = cycles
    if not partial or "use_source5" in raw:
        out["use_source5"] = raw.get("use_source5") is True
        if out["use_source5"]:
            r.warn("SOURCE5_ENABLED", "Se activaron transiciones y cultivos que solo respalda el blog de Radeco (fuente 5, baja fiabilidad).")
    if not partial or "last_pest" in raw:
        lp = raw.get("last_pest")
        items = lp if isinstance(lp, list) else ([p for p in str(lp).split(",")] if lp else [])
        out["last_pest"] = [norm(p) for p in items if norm(p)]

    r.normalized = out
    if r.ok and not partial:
        r.plot = PlotInput(
            previous_crops=out.get("previous_crops", []), new_land=out.get("new_land", False), soil=soil,
            altitude_masl=climate.get("altitude_masl"), irrigation=str(climate.get("irrigation", UNKNOWN)),
            priorities=out["priorities"], last_pest=out.get("last_pest", []),
            rotation_cycles=out.get("rotation_cycles", DEFAULT_CYCLES), use_source5=out.get("use_source5", False),
        )
    return r


def missing_fields(plot: dict) -> list[str]:
    """Qué falta preguntar, por orden de importancia (para el estado del agente).

    Obligatorios: cultivos previos o tierra nueva, y prioridades. Recomendados: altitud, riego, fertilidad.
    """
    missing = []
    if not plot.get("new_land") and not plot.get("previous_crops"):
        missing.append("previous_crops")
    if not plot.get("priorities"):
        missing.append("priorities")
    climate, soil = plot.get("climate") or {}, plot.get("soil") or {}
    if "altitude_masl" not in climate:
        missing.append("climate.altitude_masl")
    if "irrigation" not in climate:
        missing.append("climate.irrigation")
    if "fertility" not in soil:
        missing.append("soil.fertility")
    return missing


REQUIRED_FIELDS = ("previous_crops", "priorities")
