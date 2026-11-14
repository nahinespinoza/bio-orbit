"""Filtros duros F1–F4 (ESPECIFICACION.md §2). Un cultivo que falla uno se descarta."""

import re

from app.engine.models import (
    ALTITUDE_MARGIN_M, F1B_CROPS, F2_EXEMPT_FAMILIES, PH_MARGIN, SOLANACEAE_WINDOW, Crop, KnowledgeBase, PlotInput, norm,
)


def sources_matching(crop: Crop | None, pattern: str) -> str | None:
    """Fuentes de la ficha cuyo dato o ubicación coincide con `pattern`; si ninguna, todas. Formato 'F1, F2'."""
    if crop is None or not crop.sources:
        return None
    rx = re.compile(pattern)
    matched = [s for s in crop.sources if rx.search(norm(s.get("detail")) + " " + norm(s.get("location")))]
    ids = list(dict.fromkeys(s.get("source_id") for s in (matched or crop.sources)))
    return ", ".join(f"F{i}" for i in ids) if ids else None


def hard_filters(crop_id: str, history: list[str], plot: PlotInput, kb: KnowledgeBase,
                 first_step: bool = True) -> dict | None:
    """None si pasa; si no, {filter, reason, source}. `history` va del más reciente al más antiguo."""
    crop = kb.crops[crop_id]
    prev = history[0] if history else None
    family = crop.family

    # F1 / F1b
    if prev == crop_id:
        streak = next((i for i, c in enumerate(history) if c != crop_id), len(history))
        if not (crop_id in F1B_CROPS and streak < 2):
            reason = ("Ya lleva 2 temporadas seguidas (máximo permitido para quinua y maíz)." if crop_id in F1B_CROPS
                      else "No se repite el mismo cultivo en el mismo lote.")
            return {"filter": "F1", "reason": reason, "source": "Fuente 1"}

    # F2
    if family and family not in F2_EXEMPT_FAMILIES:
        if prev and prev != crop_id and kb.crops[prev].family == family:
            return {"filter": "F2", "reason": f"Misma familia botánica ({family}) que el ciclo anterior ({kb.crops[prev].name}).",
                    "source": "Fuente 5 (sin respaldo técnico); coincide con el principio de las fuentes 1 y 2"}
        if family == "Solanáceas":
            k = next((i for i, c in enumerate(history[:SOLANACEAE_WINDOW]) if kb.crops[c].family == "Solanáceas"), None)
            if k is not None:
                return {"filter": "F2", "reason": f"Solanácea sembrada hace {k + 1} ciclo(s); deben pasar "
                                                  f"{SOLANACEAE_WINDOW} ciclos antes de repetir la familia.",
                        "source": "Fuente 5 (propuesta; ventana en ciclos, no en años)"}

    # F3
    if plot.last_pest and first_step:
        hit = next((p for p in plot.last_pest if any(h in p or p in h for h in crop.host_of)), None)
        if hit:
            return {"filter": "F3", "reason": f"Es hospedero de «{hit}», la plaga o enfermedad del ciclo anterior.",
                    "source": f"Ficha de {crop.name}"}

    # F4 clima
    alt = plot.altitude_masl
    if alt is not None:
        lo, hi = crop.altitude_min, crop.altitude_max
        src = sources_matching(crop, "altitud") or "Ficha"
        if lo is not None and alt < lo - ALTITUDE_MARGIN_M:
            return {"filter": "F4-climate", "reason": f"Altitud {alt:g} m por debajo del rango del cultivo ({lo:g}–{_fmt(hi)} m).", "source": src}
        if hi is not None and alt > hi + ALTITUDE_MARGIN_M:
            return {"filter": "F4-climate", "reason": f"Altitud {alt:g} m por encima del rango del cultivo ({_fmt(lo)}–{hi:g} m).", "source": src}
    if plot.irrigation == "no" and crop.requires_irrigation is True:
        return {"filter": "F4-climate", "reason": "El cultivo requiere riego y el lote es de secano.", "source": "Ficha"}

    # F4 suelo
    ph = plot.soil.get("ph")
    if isinstance(ph, float):
        a, b = crop.ph_min, crop.ph_max
        src = sources_matching(crop, r"\bph\b") or "Ficha"
        if a is not None and ph < a - PH_MARGIN:
            return {"filter": "F4-soil", "reason": f"pH {ph:g} por debajo del rango tolerado ({a:g}–{_fmt(b)}).", "source": src}
        if b is not None and ph > b + PH_MARGIN:
            return {"filter": "F4-soil", "reason": f"pH {ph:g} por encima del rango tolerado ({_fmt(a)}–{b:g}).", "source": src}
    if plot.soil.get("drainage") == "poor" and crop.drainage_required == "good":
        return {"filter": "F4-soil", "reason": "Drenaje malo: el cultivo no tolera encharcamiento.", "source": "Ficha"}
    if plot.soil.get("depth") == "shallow" and crop.min_depth_cm is not None and crop.min_depth_cm >= 40:
        return {"filter": "F4-soil", "reason": f"Suelo somero y el cultivo pide ≥ {crop.min_depth_cm:g} cm de profundidad.", "source": "Ficha"}

    if crop.source5_only and not plot.use_source5:
        return {"filter": "SOURCE5", "reason": "Cultivo respaldado solo por el blog de Radeco (fuente 5); desactivado por defecto.",
                "source": "Fuente 5"}
    return None


def _fmt(value: float | None) -> str:
    return "?" if value is None else f"{value:g}"
