"""Punto de entrada del motor: recommend(raw_input, kb) → resultado estructurado (ESPECIFICACION.md §6)."""

from app.engine.filters import hard_filters
from app.engine.models import SPEC_VERSION, WEIGHTS, KnowledgeBase, PlotInput
from app.engine.rotation import build_rotation
from app.engine.scoring import score_crop
from app.engine.validation import validate_plot

NOTE = ("Recomendación agronómica de apoyo basada en fuentes de la sierra andina. "
        "No es una promesa de rendimiento ni de ingreso.")


def _candidates_now(plot: PlotInput, kb: KnowledgeBase) -> tuple[list[str], list[dict], list[str]]:
    history = plot.history
    prev = history[0] if history else None
    if plot.new_land or prev is None:
        ids = [cid for cid, c in kb.crops.items() if c.has_tag("starter")]
    else:
        ids = list(dict.fromkeys(e.to_crop for e in kb.edges.get(prev, [])))
    outside = [cid for cid in kb.crops if cid not in ids]
    ok, discarded = [], []
    for cid in ids:
        edge = kb.edge(prev, cid)
        if edge and edge.kind == "source5" and not plot.use_source5:
            discarded.append({"crop": cid, "filter": "SOURCE5", "reason": "Transición solo respaldada por la fuente 5.", "source": "Fuente 5"})
            continue
        result = hard_filters(cid, history, plot, kb)
        if result:
            discarded.append({"crop": cid, **result})
        else:
            ok.append(cid)
    return ok, discarded, outside


def _non_commercial_allowed(plot: PlotInput, kb: KnowledgeBase) -> bool:
    """Abono, pasto o barbecho solo se proponen «ahora» si el suelo lo justifica."""
    if plot.soil.get("fertility") == "low" or plot.soil.get("compaction") == "yes":
        return True
    return sum(kb.crops[c].depletes_soil == "high" for c in plot.history[:2]) >= 2


def recommend(raw: dict, kb: KnowledgeBase, *, allow_unknown_crops: bool = False) -> dict:
    v = validate_plot(raw, kb, allow_unknown_crops=allow_unknown_crops)
    if not v.ok:
        return {"status": "invalid_input", "errors": v.errors, "warnings": v.warnings,
                "ask": [e["message"] for e in v.errors]}
    plot = v.plot
    assert plot is not None
    warnings = list(v.warnings)
    if plot.new_land:
        warnings.append({"code": "NEW_LAND", "message": "Tierra nueva: no hay historial, así que F1–F3 no se aplican; se parte de "
                         "los cultivos con tag «starter». No se conoce la carga de plagas ni la fertilidad real: conviene un análisis de suelo."})

    ok, discarded, outside = _candidates_now(plot, kb)
    history = plot.history
    scored = [score_crop(cid, history, plot, kb) for cid in ok]
    if not _non_commercial_allowed(plot, kb):
        kept = []
        for s in scored:
            if kb.crops[s["crop"]].is_commercial:
                kept.append(s)
            else:
                discarded.append({"crop": s["crop"], "filter": "NON_COMMERCIAL_RULE",
                                  "reason": "Cultivo sin mercado: solo se propone ahora si el suelo es pobre o está compactado, "
                                            "o si los dos ciclos previos fueron muy exigentes.",
                                  "source": "Propuesta propia (ver especificación)"})
        scored = kept
    scored.sort(key=lambda s: (-s["score"], s["crop"]))

    if not scored:
        return {"status": "no_candidates", "input": v.normalized, "warnings": warnings, "discarded": discarded,
                "outside_graph": [kb.crops[c].name for c in outside],
                "message": "Ningún cultivo pasa los filtros duros. Revisa los descartados: quizá conviene barbecho o "
                           "pasto, o corregir datos de suelo o clima."}

    top = scored[:3]
    for t in top:
        t["rotation"] = build_rotation(t["crop"], history, plot, kb)
    weights = WEIGHTS[len(plot.priorities)]
    missing = list(dict.fromkeys(f"{t['name']}: {p['priority']}" for t in top for p in t["breakdown"]["priorities"] if p["missing"]))
    return {
        "status": "ok",
        "spec_version": SPEC_VERSION,
        "input": v.normalized,
        "priority_weights": [{"priority": p, "weight": weights[i]} for i, p in enumerate(plot.priorities)],
        "recommendation": top[0],
        "alternatives": top[1:],
        "rotation": top[0]["rotation"],
        "discarded": discarded,
        "outside_graph": [kb.crops[c].name for c in outside],
        "warnings": warnings,
        "missing_data": missing,
        "note": NOTE,
    }
