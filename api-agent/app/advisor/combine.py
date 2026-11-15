"""Combinación: las notas del modelo + la aptitud del motor → afinidad de 0 a 100 (100 = el mejor cultivo).

Afinidad = 0,30 · prioridad + 0,40 · riesgo + 0,30 · aptitud. Antes de combinar, el código aplica reglas fijas que no
dependen del modelo (ver el diseño, punto 6).
"""

import re

from app.advisor.payload import TRIMMED
from app.advisor.request import PRIORITY_LABEL
from app.advisor.scoring import CropScore, ScoringOutput
from app.engine.conditions import ALERT_TOPICS
from app.engine.models import norm

WEIGHTS = {"priority": 0.30, "risk": 0.40, "aptitude": 0.30}
NEUTRAL = 60                 # nota cuando el modelo no calificó un criterio
NO_PRIORITY_DATA = 30        # regla 1: la ficha no tiene el dato de la prioridad
RISK_CAP = {"ALTO": 40, "MEDIO": 70}   # regla 2: advertencia del motor
WEAK_EVIDENCE_FLOOR = 50     # regla 3: evidencia solo de otra región o sin verificar
NO_EVIDENCE_RISK = 60        # regla 4: sin investigación de los temas activos
RISK_FIRST_THRESHOLD, RISK_FIRST_CAP = 40, 40   # regla 5: riesgo alto → la afinidad no pasa de 40
CONFIDENCE = ["baja", "media", "alta"]
CONFIDENCE_IN = {"low": 0, "medium": 1, "high": 2}
WEAK = re.compile(r"otra región|sin verificar", re.IGNORECASE)
SOURCE_N = re.compile(r"[Ff]uente\s*(\d+)")
LEADING_SOURCE = re.compile(r"^\s*(\d+)\s*·\s*(.*)$")   # «1 · rotación de haba (…)»


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, float(x)))


def _alert_items(evidence: object) -> list[dict] | None:
    """Fragmentos de los temas ligados a alertas. [] si se recortó (cuenta como sin evidencia); None si no aplica."""
    if evidence == TRIMMED:
        return []
    if not isinstance(evidence, dict):
        return None
    return [i for t, v in evidence.items() if t in ALERT_TOPICS and isinstance(v, list) for i in v]


class ScoresMissingError(Exception):
    """El modelo no calificó a ningún candidato (ningún `crop` coincide)."""


def _refs(ids: list[str], catalog: dict[str, dict]) -> list[str]:
    return list(dict.fromkeys(r for r in ids if r in catalog))


FALLOW = "barbecho"


def rotation_why(transition: dict | None, crop_name: str, previous_name: str | None,
                 crop_id: str | None = None) -> tuple[str, list[str]]:
    """Transición del grafo → (frase en español sencillo, referencias F<n>). El barbecho no se «siembra»: se deja
    el terreno en descanso."""
    action = "dejar el terreno en descanso" if crop_id == FALLOW else f"sembrar {crop_name.lower()}"
    if not transition:
        if crop_id == FALLOW:
            return "Su terreno es nuevo: dejarlo en descanso es una forma de empezar la rotación.", []
        return f"Su terreno es nuevo: {crop_name.lower()} es un buen cultivo para empezar una rotación.", []
    note = transition.get("source_note") or ""
    m = LEADING_SOURCE.match(note)
    n, detail = (m.group(1), m.group(2)) if m else (None, note)
    refs = [f"F{n}"] if n else [f"F{x}" for x in SOURCE_N.findall(note)]
    after = f"después de {previous_name.lower()}" if previous_name else "en esta rotación"
    kind = transition.get("kind")
    if kind == "source":
        text = f"Una fuente agrícola recomienda {action} {after} ({detail})."
    elif kind == "general":
        text = f"Es una práctica general de rotación {action} {after} ({detail})."
    elif kind == "inferred":
        text = f"{action.capitalize()} {after} es una propuesta propia, sin fuente que la confirme ({detail})."
    else:
        text = f"{action.capitalize()} {after} solo lo respalda una fuente de baja fiabilidad ({detail})."
    return text, refs


def combine(candidates: list[dict], payload_candidates: list[dict], scoring: ScoringOutput, priority: str,
            catalog: dict[str, dict], active_alert_topics: list[str], previous_name: str | None = None) -> list[dict]:
    """→ candidatos con afinidad, confianza y porqué, ordenados de mejor a peor."""
    key_of = {norm(k): c["crop"] for c in candidates for k in (c["crop"], c["name"])}
    by_crop: dict[str, CropScore] = {}
    for s in scoring.scores:                   # por id o por nombre, sin importar mayúsculas ni tildes
        crop = key_of.get(norm(s.crop))
        if crop is not None:
            by_crop.setdefault(crop, s)        # si el modelo repite un cultivo, vale la primera calificación
    if candidates and not by_crop:
        raise ScoresMissingError("El modelo no calificó a ningún candidato.")
    evidence_of = {p["crop"]: p["evidencia"] for p in payload_candidates}

    out = []
    for c in candidates:
        s = by_crop.get(c["crop"])
        rules: list[str] = []
        p_score = _clamp(s.priority.score) if s else NEUTRAL
        r_score = _clamp(s.risk.score) if s else NEUTRAL
        if s is None:
            rules.append("sin_calificacion_del_modelo")
        drop = 0

        if c["priority_data"][priority]["missing"]:                                    # regla 1
            p_score = NO_PRIORITY_DATA
            rules.append("prioridad_sin_dato")
            drop += 1
        # Primero los pisos y valores fijos por la evidencia (reglas 3 y 4), al final los topes por advertencia
        # (regla 2): una advertencia del motor nunca queda anulada por la calidad de la evidencia.
        evidence = evidence_of.get(c["crop"])
        items = _alert_items(evidence)
        if items is not None and active_alert_topics:
            if not items:                                                              # regla 4
                r_score = NO_EVIDENCE_RISK
                rules.append("evidencia_recortada" if evidence == TRIMMED else "sin_evidencia")
                drop += 1
            elif all(WEAK.search(i["texto"]) for i in items):                          # regla 3
                r_score = max(r_score, WEAK_EVIDENCE_FLOOR)
                rules.append("evidencia_debil")
                drop += 1
        levels = {a["level"] for a in c["advisories"]}
        for level in ("ALTO", "MEDIO"):                                                # regla 2
            if level in levels:
                r_score = min(r_score, RISK_CAP[level])
                rules.append(f"advertencia_{level.lower()}")
                break

        affinity = WEIGHTS["priority"] * p_score + WEIGHTS["risk"] * r_score + WEIGHTS["aptitude"] * c["aptitude"]
        if r_score < RISK_FIRST_THRESHOLD and affinity > RISK_FIRST_CAP:              # regla 5
            affinity = RISK_FIRST_CAP
            rules.append("tope_riesgo_primero")

        apt_detail, apt_ids = rotation_why(c["transition"], c["name"].split(" (")[0], previous_name, c["crop"])
        apt_refs = _refs(apt_ids, catalog)
        pdata = c["priority_data"][priority]
        out.append({
            "crop": c["crop"], "name": c["name"], "affinity": round(affinity, 1),
            "confidence": CONFIDENCE[max(0, CONFIDENCE_IN.get(c["confidence"], 0) - drop)],
            "summary": s.summary if s else None,
            "why": [
                {"criterion": "priority", "title": PRIORITY_LABEL[priority], "score": round(p_score),
                 "detail": s.priority.reason if s else pdata["detail"],
                 "data": pdata["detail"], "references": _refs(s.priority.references, catalog) if s else []},
                {"criterion": "risk", "title": "Condiciones de tu parcela", "score": round(r_score),
                 "detail": s.risk.reason if s else "Sin calificación del riesgo: se usó un valor neutro.",
                 "references": _refs(s.risk.references, catalog) if s else []},
                {"criterion": "aptitude", "title": "Un cambio en tu rotación", "score": round(c["aptitude"]),
                 "detail": apt_detail, "references": apt_refs},
            ],
            "rules_applied": rules,
            "warnings": c["warnings"],
            "rotation_warnings": (c["rotation"] or {}).get("warnings", []),
            "rotation": [{"cycle": st["cycle"], "crop": st["crop"], "name": st["name"],
                          "confidence": CONFIDENCE[CONFIDENCE_IN.get(st["confidence"], 0)]}
                         for st in (c["rotation"] or {}).get("sequence", [])],
            "advisories": [{"level": a["level"], "message": a["message"], "signal": a["signal"], "crop_field": a["crop_field"]}
                           for a in c["advisories"]],
            "priority_missing": pdata["missing"],
        })
    out.sort(key=lambda x: (-x["affinity"], x["crop"]))
    return out
