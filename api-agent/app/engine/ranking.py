"""Candidatos agronómicos para la recomendación con evidencia (POST /v1/recommendations).

Usa las piezas del motor (filtros duros, aptitud, rotación, advertencias, datos de la ficha) SIN las prioridades del
agricultor: el orden es solo por aptitud agronómica. Las prioridades y el riesgo de la parcela los califica el modelo
(ver app/advisor). `recommend()` no cambia: la conversación y /v1/recommend siguen igual.

A diferencia de `recommend()`, aquí NO se aplica la regla de no comerciales: barbecho, pasto y abono verde entran como
candidatos (decisión del usuario, para tener más opciones). Su ficha dice que no generan ingreso, así que el modelo y la
afinidad los dejan abajo si la prioridad es el mercado.
"""

from app.engine.advisories import advisories_for
from app.engine.crop_facts import crop_facts
from app.engine.models import KnowledgeBase, PlotInput
from app.engine.recommender import _candidates_now
from app.engine.rotation import build_rotation
from app.engine.scoring import SUBSCORES, round1, score_crop

TOP_N = 5


def _priority_data(kb: KnowledgeBase, crop_id: str, prev: str | None) -> dict[str, dict]:
    """Lo que dice la ficha de cada prioridad, sin puntaje: {detail, source, confidence, missing}."""
    return {p: {k: v for k, v in fn(kb, crop_id, prev).items() if k != "value"} for p, fn in SUBSCORES.items()}


def rank_by_aptitude(plot: PlotInput, kb: KnowledgeBase, n: int = TOP_N, signals: dict | None = None) -> dict:
    """`signals`: alertas del remote-sensing de esta parcela (por defecto, las del kb)."""
    ok, discarded, outside = _candidates_now(plot, kb)
    outside_names = [kb.crops[c].name for c in outside]
    if not ok:
        return {"status": "no_candidates", "discarded": discarded, "outside_graph": outside_names}

    history = plot.history
    prev = history[0] if history else None
    scored = []
    for cid in ok:
        s = score_crop(cid, history, plot, kb)   # aptitud, confianza, transición y avisos; su puntaje de prioridades no se usa
        c = kb.crops[cid]
        scored.append({
            "crop": cid, "name": c.name, "aptitude": round1(s["aptitude_score"]),
            "aptitude_parts": s["breakdown"]["aptitude"], "transition": s["transition"],
            "confidence": s["confidence"], "warnings": s["warnings"],
            "priority_data": _priority_data(kb, cid, prev),
            "sources": sorted({src["source_id"] for src in c.sources if isinstance(src.get("source_id"), int)}
                              | set(c.market_source_ids)),
        })
    scored.sort(key=lambda s: (-s["aptitude"], s["crop"]))
    top = scored[:n]
    for t in top:
        t["rotation"] = build_rotation(t["crop"], history, plot, kb)
        t["advisories"] = advisories_for(t["crop"], kb, signals=signals, observations=plot.observations,
                                         altitude_masl=plot.altitude_masl)
        t["facts"] = crop_facts(kb.crops[t["crop"]])
    return {"status": "ok", "candidates": top, "discarded": discarded, "outside_graph": outside_names}
