"""Puntaje = 0,75 · P (prioridades) + 0,25 · A (aptitud agronómica). ESPECIFICACION.md §3."""

import math

from app.engine.filters import sources_matching
from app.engine.models import (
    ALTITUDE_MARGIN_M, CONFIDENCE_NAME, CONFIDENCE_RANK, EDGE_CONFIDENCE, EDGE_SEQUENCE_SCORE, NEUTRAL, PRIORITY_SHARE,
    UNKNOWN, WEIGHTS, Crop, KnowledgeBase, PlotInput, Transition, norm,
)

TEXTURE_STEMS = {"sandy": "arenos", "loam": "franc", "clay": "arcill"}


def clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


def round1(x: float) -> float:
    """Redondeo a 1 decimal «hacia arriba en .5», igual que Math.round de JavaScript."""
    return math.floor(x * 10 + 0.5) / 10


def _sub(value: float, detail: str, source: str | None, confidence: str, missing: bool) -> dict:
    return {"value": value, "detail": detail, "source": source, "confidence": confidence, "missing": missing}


def _missing(detail: str) -> dict:
    return _sub(NEUTRAL, detail, None, "low", True)


def _mean_cycle(c: Crop) -> float | None:
    if c.cycle_min is not None and c.cycle_max is not None:
        return (c.cycle_min + c.cycle_max) / 2
    return c.cycle_min if c.cycle_min is not None else c.cycle_max


def _g(value: float | None) -> str:
    return "?" if value is None else f"{value:g}"


# --- Subpuntajes por prioridad (0–100) ---------------------------------------------------------------

def sub_market_value(kb: KnowledgeBase, crop_id: str, prev: str | None) -> dict:
    c = kb.crops[crop_id]
    if not c.is_commercial:
        return _sub(0.0, "No comercial: no genera ingreso directo.", "Ficha", "high", False)
    if c.market_level is None:
        return _missing("Sin dato de mercado fiable (puntúa neutro).")
    ref = f"{c.market_price:g} {c.market_unit or ''} ({c.market_date or 's/f'})" if c.market_price is not None else "nivel por inferencia"
    src = ", ".join(f"F{n}" for n in c.market_source_ids) or "Ficha"
    detail = f"Nivel de mercado {c.market_level}/5; {ref}; volatilidad {c.market_volatility or 'desconocida'}"
    return _sub(clamp((c.market_level - 1) / 4 * 100), detail, src, c.market_confidence or "low", False)


def sub_speed(kb: KnowledgeBase, crop_id: str, prev: str | None) -> dict:
    c = kb.crops[crop_id]
    m = _mean_cycle(c)
    if m is None:
        return _missing("Sin dato de ciclo (puntúa neutro).")
    detail = f"Ciclo {_g(c.cycle_min)}–{_g(c.cycle_max)} meses (media {m:.1f})"
    return _sub(clamp(100 * (1 - (m - 3) / 9)), detail, sources_matching(c, r"ciclo|cosecha|dias|meses"), c.confidence, False)


def sub_low_labor(kb: KnowledgeBase, crop_id: str, prev: str | None) -> dict:
    c = kb.crops[crop_id]
    if c.labor_level is None:
        return _missing("Sin dato de mano de obra (puntúa neutro).")
    days = f"; {c.labor_days_per_ha:g} jornales/ha" if c.labor_days_per_ha is not None else ""
    mech = f"; mecanizable: {c.labor_mechanizable}" if c.labor_mechanizable else ""
    from_source = c.labor_data_type == "source"
    detail = f"Mano de obra nivel {c.labor_level}/5{days}{mech}{'' if from_source else ' (inferencia)'}"
    source = sources_matching(c, r"jornal|costo|mano de obra") if from_source else "inferencia propia"
    return _sub(clamp((5 - c.labor_level) / 4 * 100), detail, source, c.confidence if from_source else "low", False)


def sub_fewer_pests(kb: KnowledgeBase, crop_id: str, prev: str | None) -> dict:
    """60 % presión propia (nº de plagas y enfermedades) + 40 % efecto sanitario tras el cultivo previo."""
    c = kb.crops[crop_id]
    if not c.pests and not c.diseases and c.is_commercial:
        return _missing("Sin lista de plagas o enfermedades (puntúa neutro).")
    n = len(c.pests) + len(c.diseases)
    own = clamp(100 - 10 * n)
    rot, note = 60.0, ""
    if prev:
        p = kb.crops[prev]
        common = [h for h in c.host_of if h in p.host_of]
        breaks = [h for h in p.host_of if any(r in h or h in r for r in c.breaks_cycles_of)]
        if common:
            rot, note = 15.0, f"; comparte hospedero con {p.name}: {', '.join(common)}"
        elif breaks:
            rot, note = 95.0, f"; rompe el ciclo de: {', '.join(breaks)}"
        elif p.family != c.family:
            rot, note = 70.0, "; otra familia que el ciclo anterior"
    detail = f"{n} plaga(s) o enfermedad(es) principal(es){note}"
    return _sub(clamp(0.6 * own + 0.4 * rot), detail, sources_matching(c, r"plaga|enfermedad"), c.confidence, False)


SUBSCORES = {"market_value": sub_market_value, "speed": sub_speed, "fewer_pests": sub_fewer_pests, "low_labor": sub_low_labor}

FERTILITY_MATRIX = {
    "low": {"high": 15.0, "medium": 50.0, "low": 85.0},
    "medium": {"high": 50.0, "medium": 80.0, "low": 90.0},
    "high": {"high": 95.0, "medium": 90.0, "low": 85.0},
}


def aptitude(kb: KnowledgeBase, crop_id: str, prev: str | None, plot: PlotInput, edge: Transition | None) -> tuple[float, list[dict], bool]:
    c = kb.crops[crop_id]
    parts: list[dict] = []
    missing = False

    fert, demand = plot.soil.get("fertility", UNKNOWN), c.fertility_demand
    if fert == UNKNOWN or demand is None:
        a_fert, missing = NEUTRAL, True
    else:
        a_fert = FERTILITY_MATRIX[fert][demand]
        if fert == "low" and c.fixes_nitrogen:
            a_fert = max(a_fert, 95.0)
    parts.append({"name": "fertility_vs_demand", "value": a_fert,
                  "detail": f"suelo {fert}; exigencia del cultivo {demand or 'desconocida'}"})

    if edge:
        a_seq, seq_detail = EDGE_SEQUENCE_SCORE.get(edge.kind, NEUTRAL), f"transición {edge.kind}: {edge.source_note}"
    elif prev is None:
        a_seq, seq_detail = 80.0, "tierra nueva, cultivo con tag starter"
    else:
        a_seq, seq_detail = NEUTRAL, "sin transición registrada"
    parts.append({"name": "graph_sequence", "value": a_seq, "detail": seq_detail})

    a_n = 60.0
    if prev:
        p = kb.crops[prev]
        if p.depletes_soil == "high" and c.fixes_nitrogen:
            a_n = 100.0
        elif p.depletes_soil == "high" and c.depletes_soil == "high":
            a_n = 15.0
        elif p.fixes_nitrogen and c.depletes_soil == "high":
            a_n = 90.0
        elif p.depletes_soil == "high" and c.depletes_soil == "low":
            a_n = 80.0
        elif p.depletes_soil is None or c.depletes_soil is None:
            a_n, missing = NEUTRAL, True
        n_detail = (f"tras {p.name}: {p.depletes_soil or '?'} → {c.depletes_soil or '?'}"
                    f"{' (fija N)' if c.fixes_nitrogen else ''}")
    else:
        a_n = 80.0 if c.fixes_nitrogen else 60.0
        n_detail = "sin cultivo previo"
    parts.append({"name": "nitrogen_balance", "value": a_n, "detail": n_detail})

    texture = plot.soil.get("texture", UNKNOWN)
    text = norm(c.soil_texture_text)
    if texture != UNKNOWN and text:
        admitted = [k for k, stem in TEXTURE_STEMS.items() if stem in text]
        if admitted:
            parts.append({"name": "texture", "value": 95.0 if texture in admitted else 35.0,
                          "detail": f"suelo {texture}; ficha: «{c.soil_texture_text}»"})

    if plot.soil.get("compaction") == "yes" and c.improves_structure is True:
        parts.append({"name": "compaction", "value": 95.0, "detail": "suelo compactado; el cultivo mejora la estructura"})

    return sum(x["value"] for x in parts) / len(parts), parts, missing


# --- Puntaje de un cultivo en un paso ----------------------------------------------------------------

def score_crop(crop_id: str, history: list[str], plot: PlotInput, kb: KnowledgeBase) -> dict:
    c = kb.crops[crop_id]
    prev = history[0] if history else None
    edge = kb.edge(prev, crop_id)
    weights = WEIGHTS[len(plot.priorities)]
    priorities = [{"priority": p, "weight": weights[i], **SUBSCORES[p](kb, crop_id, prev)} for i, p in enumerate(plot.priorities)]
    p_score = sum(x["weight"] * x["value"] for x in priorities)
    a_score, a_parts, a_missing = aptitude(kb, crop_id, prev, plot, edge)
    total = PRIORITY_SHARE * p_score + (1 - PRIORITY_SHARE) * a_score

    level = min(CONFIDENCE_RANK.get(c.confidence, 1), EDGE_CONFIDENCE[edge.kind] if edge else 3)
    missing = [x["priority"] for x in priorities if x["missing"]] + (["aptitude"] if a_missing else [])
    if missing:
        level = max(1, level - 1)

    warnings: list[str] = []
    if edge and edge.kind == "inferred":
        warnings.append("La transición desde el cultivo anterior es inferencia propia, no de una fuente.")
    if edge and edge.kind == "source5":
        warnings.append("La transición solo la respalda el blog Radeco (fuente 5).")
    if c.geographic_scope and "ecuador" not in c.geographic_scope.lower():
        warnings.append(f"Datos del cultivo con respaldo de {c.geographic_scope}; no necesariamente de Ecuador.")
    if missing:
        warnings.append(f"Datos faltantes que se puntuaron como neutros: {', '.join(missing)}.")
    alt = plot.altitude_masl
    if alt is not None and ((c.altitude_min is not None and alt < c.altitude_min) or (c.altitude_max is not None and alt > c.altitude_max)):
        warnings.append(f"Altitud {alt:g} m fuera del rango {_g(c.altitude_min)}–{_g(c.altitude_max)} m "
                        f"(dentro del margen de {ALTITUDE_MARGIN_M} m): adaptación marginal.")
    ph = plot.soil.get("ph")
    if isinstance(ph, float) and ((c.ph_min is not None and ph < c.ph_min) or (c.ph_max is not None and ph > c.ph_max)):
        warnings.append(f"pH {ph:g} fuera del rango óptimo {_g(c.ph_min)}–{_g(c.ph_max)} (dentro del margen): adaptación marginal.")
    if prev and any(h in kb.crops[prev].host_of for h in c.host_of):
        warnings.append(f"Comparte hospedero de plagas con {kb.crops[prev].name}.")

    return {
        "crop": crop_id, "name": c.name, "score": round1(total),
        "priority_score": round1(p_score), "aptitude_score": round1(a_score),
        "breakdown": {"priorities": priorities, "aptitude": a_parts},
        "transition": {"kind": edge.kind, "source_note": edge.source_note} if edge else None,
        "confidence": CONFIDENCE_NAME[level], "warnings": warnings,
    }
