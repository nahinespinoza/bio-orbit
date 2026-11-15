"""POST /v1/recommendations: petición → motor (candidatos) → modelo (notas) → combinación → JSON del contrato."""

import json
from functools import lru_cache

from app.advisor.combine import ScoresMissingError, combine
from app.advisor.payload import build_payload
from app.advisor.request import PRIORITY_LABEL, AdvisorRequest, to_plot_raw
from app.advisor.scoring import AdvisorModelError, Scorer
from app.engine.advisories import read_signals, remote_sensing_scope
from app.engine.conditions import ALERT_TOPICS, plot_conditions
from app.engine.models import KnowledgeBase, norm
from app.engine.ranking import rank_by_aptitude
from app.engine.validation import resolve_crop, validate_plot
from app.repository.crops import STRUCTURED_DIR


class AdvisorInputError(Exception):
    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__("; ".join(e["message"] for e in errors))


@lru_cache
def server_remote_sensing() -> dict | None:
    path = STRUCTURED_DIR / "remote_sensing.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def advise(req: AdvisorRequest, kb: KnowledgeBase, conn, scorer: Scorer) -> dict:
    if norm(req.previous_crop).replace("_", " ").strip() in ("new land", "tierra nueva"):
        crop_id = None
    else:
        crop_id, suggestions = resolve_crop(req.previous_crop, kb)
        if crop_id is None:
            hint = f" ¿Quiso decir: {', '.join(s for s in suggestions if s in kb.crops)}?" if suggestions else ""
            raise AdvisorInputError([{"code": "UNKNOWN_CROP", "field": "previous_crop",
                                      "message": f"«{req.previous_crop}» no está en el pool de cultivos.{hint}"}])

    rs = server_remote_sensing()   # MVP: siempre la copia del servidor; `req.remote_sensing` se ignora
    extra = frozenset({"exceso_agua"}) if req.waterlogging == "long" else frozenset()
    signals = read_signals(rs) if rs else {}
    conditions = plot_conditions(rs, extra) if rs else {}
    rs_altitude = rs["output"].get("altitud_parcela_msnm") if rs else None
    altitude = req.altitude_masl if req.altitude_masl is not None else rs_altitude

    v = validate_plot(to_plot_raw(req, crop_id, altitude), kb)
    if not v.ok:
        raise AdvisorInputError(v.errors)
    plot = v.plot
    # UNKNOWN_SOIL se omite: la petición solo trae drenaje, así que avisaría siempre; se avisa solo de la fertilidad.
    warnings = [w for w in v.warnings if w["code"] != "UNKNOWN_SOIL"]
    if req.fertility is None:
        warnings.append({"code": "UNKNOWN_FERTILITY", "message": "Sin fertilidad del suelo: puntúa neutro y baja la confianza."})
    ranked = rank_by_aptitude(plot, kb, signals=signals)
    if ranked["status"] != "ok":
        return {"status": "no_candidates", "discarded": ranked["discarded"], "outside_graph": ranked["outside_graph"],
                "message": "Ningún cultivo pasa las reglas de rotación y altitud para este lote."}

    scope_applies = bool(signals) and remote_sensing_scope(signals, plot.altitude_masl)["applies"]
    crop_name = kb.crops[crop_id].name if crop_id else None
    payload, refs, trimmed = build_payload(req, crop_name, conditions, ranked["candidates"], conn, scope_applies)
    scoring = scorer(payload)
    active_alerts = [t for t in conditions.get("temas_activos", []) if t in ALERT_TOPICS] if scope_applies else []
    try:
        ranked_out = combine(ranked["candidates"], payload["candidatos"], scoring, req.priority, refs, active_alerts,
                             previous_name=crop_name.split(" (")[0] if crop_name else None)
    except ScoresMissingError as exc:
        raise AdvisorModelError(str(exc)) from exc

    cited = {r for c in ranked_out for w in c["why"] for r in w["references"]}
    return {
        "status": "ok",
        "data_date": signals.get("_fecha_datos", {}).get("mensaje"),
        "priority": {"id": req.priority, "label": PRIORITY_LABEL[req.priority]},
        "recommendation": ranked_out[0],
        "alternatives": ranked_out[1:],
        "how_to_compare": scoring.how_to_compare,
        "sources": [refs[r] for r in sorted(cited, key=lambda x: (x[0], int(x[1:])))],
        "warnings": warnings,
        "missing_data": [f"{c['name']}: {PRIORITY_LABEL[req.priority].lower()}" for c in ranked_out if c["priority_missing"]],
        "discarded": ranked["discarded"],
        "plot_conditions": conditions if scope_applies else None,
        "flags": {"evidence_trimmed": trimmed, "remote_sensing_applies": scope_applies},
        "weights": {"priority": 0.30, "risk": 0.40, "aptitude": 0.30},
    }
