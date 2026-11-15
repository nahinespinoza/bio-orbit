"""Lo que recibe el modelo: la petición, las condiciones de la parcela y los candidatos con su evidencia (≤ 12 KB).

Cada candidato trae los datos de la ficha para la prioridad elegida y los fragmentos de su investigación de los temas
activos (sin URL). Cada referencia tiene un id: `F<n>` (fuente de la ficha) o `I<n>` (fragmento de investigación). El
catálogo de referencias guarda título y URL para la respuesta.
"""

import json
import re
import sqlite3

from app.advisor.request import IRRIGATION_TEXT, PRIORITY_LABEL, WATERLOGGING_TEXT, AdvisorRequest
from app.engine.conditions import ALERT_TOPICS
from app.repository.research import _compact, research_evidence

MAX_BYTES = 12_000
NO_RESEARCH = "sin investigación"
TRIMMED = "recortada por tamaño"
URL = re.compile(r"https?://[^\s)]+")


def size(payload: dict) -> int:
    return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def _source_refs(conn: sqlite3.Connection, ids: set[int]) -> dict[str, dict]:
    if not ids:
        return {}
    rows = conn.execute(f"SELECT source_id, title, url FROM sources WHERE source_id IN ({','.join('?' * len(ids))})",
                        sorted(ids)).fetchall()
    return {f"F{r['source_id']}": {"id": f"F{r['source_id']}", "title": r["title"], "url": r["url"]} for r in rows}


def _evidence(conn: sqlite3.Connection, crop_id: str, topics: list[str], refs: dict[str, dict]) -> dict:
    found = research_evidence(conn, crop_id, topics, compact=False)
    out: dict = {}
    for topic in topics:
        items = []
        for full in found.get(topic, []):
            rid = f"I{sum(1 for k in refs if k.startswith('I')) + 1}"
            url = URL.search(full)
            refs[rid] = {"id": rid, "title": full.splitlines()[0].rstrip("."), "url": url.group(0) if url else None}
            items.append({"ref": rid, "texto": _compact(full)})
        out[topic] = items or NO_RESEARCH
    return out


def build_payload(req: AdvisorRequest, crop_name: str | None, conditions: dict, ranked: list[dict],
                  conn: sqlite3.Connection, scope_applies: bool) -> tuple[dict, dict[str, dict], bool]:
    """→ (payload para el modelo, catálogo de referencias usadas, evidencia_recortada)."""
    refs: dict[str, dict] = _source_refs(conn, {s for c in ranked for s in c["sources"]})
    topics = list(conditions.get("temas_activos", [])) if scope_applies else []
    candidates = []
    for c in ranked:
        pdata = c["priority_data"][req.priority]
        candidates.append({
            "crop": c["crop"], "nombre": c["name"], "aptitud": c["aptitude"],
            "transicion": c["transition"], "confianza_ficha": c["confidence"],
            "dato_prioridad": {"detalle": pdata["detail"], "fuente": pdata["source"], "sin_dato": pdata["missing"]},
            "advertencias": [{"nivel": a["level"], "mensaje": a["message"]} for a in c["advisories"]],
            "evidencia": _evidence(conn, c["crop"], topics, refs) if topics else "no aplica",
        })
    payload = {
        "prioridad": {"id": req.priority, "etiqueta": PRIORITY_LABEL[req.priority]},
        "lote": {"cultivo_anterior": crop_name or "tierra nueva", "riego": IRRIGATION_TEXT[req.irrigation],
                 "agua_empozada": WATERLOGGING_TEXT[req.waterlogging]},
        "condiciones_parcela": conditions if scope_applies else None,
        "candidatos": candidates,
    }

    def finalize() -> dict[str, dict]:
        used = {i["ref"] for c in candidates if isinstance(c["evidencia"], dict)
                for v in c["evidencia"].values() if isinstance(v, list) for i in v}
        kept = {k: v for k, v in refs.items() if k.startswith("F") or k in used}
        payload["referencias_disponibles"] = sorted(kept, key=lambda r: (r[0], int(r[1:])))
        return kept

    kept, trimmed = finalize(), False
    # 1) Del último candidato al segundo: solo los temas ligados a una alerta. 2) Si no alcanza: sin evidencia.
    for keep_alerts_only in (True, False):
        for cand in reversed(candidates[1:]):
            if size(payload) <= MAX_BYTES:
                break
            if isinstance(cand["evidencia"], dict):
                cand["evidencia"] = ({t: v for t, v in cand["evidencia"].items() if t in ALERT_TOPICS}
                                     if keep_alerts_only else TRIMMED)
                trimmed = True
                kept = finalize()
    return payload, kept, trimmed
