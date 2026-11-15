"""Investigación de las fichas (`indicadores` y `huecos_indicadores` de cultivos.json) → fragmentos del RAG.

Un fragmento por bloque de origen (cultivo × clave), con el tema normalizado como metadato: así el agente compara la
investigación de cada candidato con los indicadores del remote-sensing. El texto es español legible (no JSON) y conserva
valores, notas, citas con URL y los avisos de calidad (dato de otra región, citas sin verificar).
"""

import logging

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

TOPIC_OF: dict[str, str] = {
    "helada": "helada",
    "agua": "agua", "humedad_suelo": "agua",
    "exceso_agua": "exceso_agua",
    "sanidad": "sanidad", "sanidad_lancha": "sanidad", "hospedero_plagas_papa": "sanidad", "efecto_plagas": "sanidad",
    "fertilidad": "fertilidad", "N_aportado": "fertilidad", "biomasa_N": "fertilidad",
    "ciclo_siembra": "ciclo_siembra", "duracion_andina": "ciclo_siembra",
    "altitud_temperatura": "altitud_temperatura", "altitud_adaptacion": "altitud_temperatura",
    "rotacion": "rotacion", "tiempo_antes_papa": "rotacion", "riesgo_antes_papa": "rotacion",
    "abono_verde_papa": "rotacion", "momento_incorporacion": "rotacion", "especies_y_biomasa": "rotacion",
    "fenologia_indices": "fenologia",
}
GAPS_TOPIC = "vacios"
UNKNOWN_TOPIC = "otros"
SKIP = ("fuentes", "fuentes_no_verificadas_en_texto_completo", "origen")


def _short_name(profile: dict, crop_id: str) -> str:
    return str(profile.get("nombre") or crop_id).split(" (")[0]


def _label(key: str) -> str:
    return "Dato" if key == "valor" else key.replace("_", " ").capitalize()


def _render(value: object) -> str:
    if value is None:
        return "sin dato"
    if isinstance(value, dict):
        return "; ".join(f"{k.replace('_', ' ')}: {_render(v)}" for k, v in value.items())
    if isinstance(value, list):
        return "; ".join(_render(v) for v in value)
    return str(value)


def _block_text(name: str, topic: str, key: str, block: dict) -> str:
    lines = [f"Investigación del cultivo {name} · tema {topic} ({key})."]
    if block.get("origen"):
        lines.append(f"Dato de otra región: {block['origen']}.")
    unverified = block.get("fuentes_no_verificadas_en_texto_completo") or 0
    if isinstance(unverified, int) and unverified > 0:
        lines.append(f"{unverified} cita(s) sin verificar en texto completo (tomadas de resúmenes).")
    lines += [f"{_label(k)}: {_render(v)}" for k, v in block.items() if k not in SKIP]
    for src in block.get("fuentes") or []:
        if isinstance(src, dict):
            url = f" ({src['url']})" if src.get("url") else ""
            lines.append(f"Fuente: {src.get('cita') or 'sin cita'}{url}")
    return "\n".join(lines)


def _metadata(crop_id: str, name: str, key: str, topic: str) -> dict:
    return {"doc_id": f"cultivos.json#{crop_id}/{key}", "source_id": None, "doc_kind": "crop_research",
            "reliability_level": "medium", "title": f"Investigación del cultivo: {name} — {topic}",
            "section": key, "crops": [crop_id], "tema": topic}


def research_documents(crops_doc: dict) -> list[Document]:
    docs: list[Document] = []
    for crop_id, profile in crops_doc.get("cultivos", {}).items():
        name = _short_name(profile, crop_id)
        for key, block in (profile.get("indicadores") or {}).items():
            topic = TOPIC_OF.get(key, UNKNOWN_TOPIC)
            if topic == UNKNOWN_TOPIC:
                logger.warning("Clave de investigación sin tema: %s/%s → %s", crop_id, key, UNKNOWN_TOPIC)
            meta = _metadata(crop_id, name, key, topic)
            if isinstance(block, dict) and block.get("origen"):
                meta["origen"] = block["origen"]
            text = _block_text(name, topic, key, block) if isinstance(block, dict) else f"{name} · {key}: {_render(block)}"
            docs.append(Document(page_content=text, metadata=meta))
        gaps = profile.get("huecos_indicadores")
        if gaps:
            text = "\n".join([f"Investigación del cultivo {name} · lo que NO se encontró en las fuentes:",
                              *(f"- {g}" for g in (gaps if isinstance(gaps, list) else [gaps]))])
            docs.append(Document(page_content=text, metadata=_metadata(crop_id, name, "huecos_indicadores", GAPS_TOPIC)))
    return docs
