"""Herramientas del agente. El LLM conversa; estas herramientas validan, recomiendan y buscan evidencia."""

import json
from typing import Annotated, Literal

from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langgraph.types import Command
from pydantic import Field

from app.engine.crop_facts import crop_facts
from app.engine.models import KnowledgeBase
from app.engine.recommender import recommend
from app.engine.validation import REQUIRED_FIELDS, missing_fields, resolve_crop, validate_plot
from app.memory.state import AgentContext, CropAdvisorState
from app.rag.retriever import format_citation
from app.repository import crops as crops_repo

Runtime = ToolRuntime[AgentContext, CropAdvisorState]
Priority = Literal["market_value", "speed", "fewer_pests", "low_labor"]
Observation = Literal["frost", "blight", "dry_soil", "waterlogging"]
# Mismos valores que crops_repo.PROFILE_SECTIONS (lo verifica una prueba).
Section = Literal["suelo", "clima", "ciclo_meses", "plagas", "enfermedades", "efecto_rotacion", "mano_obra",
                  "facilidad_cultivo", "mercado", "huecos", "fuentes", "siguientes", "sensibilidades"]
PASSAGE_CHARS = 900


def _json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False)


def _merge_plot(current: dict, update: dict) -> dict:
    merged = {**current}
    if "new_land" in update or "previous_crops" in update:
        merged["new_land"] = update.get("new_land", False)
        merged["previous_crops"] = update.get("previous_crops", [])
    for group in ("soil", "climate"):
        if group in update:
            merged[group] = {**merged.get(group, {}), **update[group]}
    for key in ("priorities", "last_pest", "rotation_cycles", "use_source5", "observations"):
        if key in update:
            merged[key] = update[key]
    if "notes" in update:   # las notas se acumulan: cada turno agrega las nuevas
        merged["notes"] = list(dict.fromkeys([*merged.get("notes", []), *update["notes"]]))
    return merged


@tool
def update_plot(
    runtime: Runtime,
    previous_crops: list[str] | None = None,
    new_land: bool | None = None,
    priorities: list[Priority] | None = None,
    fertility: Literal["low", "medium", "high", "unknown"] | None = None,
    texture: Literal["sandy", "loam", "clay", "unknown"] | None = None,
    depth: Literal["shallow", "medium", "deep", "unknown"] | None = None,
    drainage: Literal["poor", "fair", "good", "unknown"] | None = None,
    compaction: Literal["yes", "no", "unknown"] | None = None,
    ph: float | Literal["acidic", "neutral", "alkaline", "unknown"] | None = None,
    altitude_masl: float | Literal["unknown"] | None = None,
    irrigation: Literal["yes", "no", "unknown"] | None = None,
    last_pest: list[str] | None = None,
    rotation_cycles: int | None = None,
    observations: list[Observation] | None = None,
    notes: list[str] | None = None,
) -> Command:
    """Registra datos del lote que dio el agricultor. Envía SOLO los campos que mencionó en la conversación;
    deja en null todo lo que no ha dicho (así se sabe qué falta preguntar).

    previous_crops: cultivos anteriores del más reciente al más antiguo (nombres comunes, p. ej. ["papa", "cebada"]).
    new_land: true si el lote nunca se cultivó (excluye previous_crops).
    priorities: de 1 a 3, en orden de importancia.
    "unknown" solo cuando el agricultor DIJO que no sabe ese dato; nunca para datos que no se han preguntado.
    last_pest: plaga o enfermedad fuerte del último ciclo, solo si la mencionó.
    observations: lo que el agricultor ve HOY en su lote, solo si lo mencionó: frost (heladas), blight (lancha),
    dry_soil (suelo seco), waterlogging (agua empozada). Envía la lista completa de lo que ha contado.
    notes: SOLO lo que el agricultor cuenta y no cabe en ningún otro campo (tipo de riego, tamaño de la parcela, si tiene
    comprador o semilla, recursos, preferencias). Una frase corta por nota, con sus palabras; envía solo las nuevas.
    """
    raw: dict = {}
    if previous_crops is not None:
        raw["previous_crops"] = previous_crops
    if new_land is not None:
        raw["new_land"] = new_land
    if priorities is not None:
        raw["priorities"] = priorities
    soil = {k: v for k, v in {"fertility": fertility, "texture": texture, "depth": depth, "drainage": drainage,
                              "compaction": compaction, "ph": ph}.items() if v is not None}
    if soil:
        raw["soil"] = soil
    climate = {k: v for k, v in {"altitude_masl": altitude_masl, "irrigation": irrigation}.items() if v is not None}
    if climate:
        raw["climate"] = climate
    if last_pest is not None:
        raw["last_pest"] = last_pest
    if rotation_cycles is not None:
        raw["rotation_cycles"] = rotation_cycles
    if observations is not None:
        raw["observations"] = observations
    if notes is not None:
        raw["notes"] = notes

    result = validate_plot(raw, runtime.context.kb, partial=True)
    plot = _merge_plot(runtime.state.get("plot") or {}, result.normalized)
    missing = missing_fields(plot)
    content = {
        "saved": result.normalized,
        "errors": result.errors,
        "plot": plot,
        "missing": missing,
        "ready_to_recommend": not any(m in REQUIRED_FIELDS for m in missing),
    }
    return Command(update={"plot": plot, "messages": [ToolMessage(_json(content), tool_call_id=runtime.tool_call_id)]})


def _summary(result: dict, kb: KnowledgeBase) -> dict:
    """Versión compacta del resultado del motor para el LLM. El cultivo recomendado trae `facts` de su ficha."""
    if result["status"] != "ok":
        return result

    def crop(t: dict) -> dict:
        return {
            "crop": t["crop"], "name": t["name"], "score": t["score"], "confidence": t["confidence"],
            "reasons": [{"priority": p["priority"], "weight": p["weight"], "subscore": round(p["value"]),
                         "detail": p["detail"], "source": p["source"], "missing": p["missing"]}
                        for p in t["breakdown"]["priorities"]],
            "agronomy": [f"{a['name']}: {a['detail']} ({round(a['value'])}/100)" for a in t["breakdown"]["aptitude"]],
            "transition": t["transition"], "warnings": t["warnings"],
            "advisories": [{"rule": a["rule"], "level": a["level"], "message": a["message"]} for a in t.get("advisories", [])],
        }

    rot = result["rotation"]
    return {
        "status": "ok",
        "recommendation": {**crop(result["recommendation"]), "facts": crop_facts(kb.crops[result["recommendation"]["crop"]])},
        "alternatives": [crop(a) for a in result["alternatives"]],
        "rotation": {"sequence": [f"{s['cycle']}. {s['name']} ({s['role']}; "
                                  f"{s['transition']['kind'] + ': ' + s['transition']['source_note'] if s['transition'] else 'inicio'})"
                                  for s in rot["sequence"]],
                     "ends_with_ender": rot["ends_with_ender"], "warnings": rot["warnings"]} if rot else None,
        "discarded": [f"{d['crop']}: {d['filter']} — {d['reason']}" for d in result["discarded"]],
        # cultivos que el motor ni siquiera evaluó: no siguen a lo que sembró antes según las reglas de rotación
        "not_after_previous_crop": result.get("outside_graph", []),
        "warnings": [w["message"] for w in result["warnings"]],
        "missing_data": result["missing_data"],
        "note": result["note"],
    }


@tool
def recommend_crop(runtime: Runtime) -> Command:
    """Ejecuta el motor de recomendación con los datos del lote ya registrados.

    Devuelve el cultivo recomendado, 2 alternativas, la rotación sugerida, los descartes con su motivo,
    las advertencias y los datos faltantes. Requiere cultivos previos (o tierra nueva) y prioridades.
    """
    plot = runtime.state.get("plot") or {}
    missing = [m for m in missing_fields(plot) if m in REQUIRED_FIELDS]
    if missing:
        content = {"status": "missing_required", "missing": missing,
                   "message": "Antes de recomendar, pregunta por: " + ", ".join(missing)}
        return Command(update={"messages": [ToolMessage(_json(content), tool_call_id=runtime.tool_call_id)]})
    result = recommend(plot, runtime.context.kb)
    return Command(update={
        "last_recommendation": result,
        "messages": [ToolMessage(_json(_summary(result, runtime.context.kb)), tool_call_id=runtime.tool_call_id)],
    })


@tool
def search_sources(runtime: Runtime, query: str, crop: str | None = None) -> Command:
    """Busca pasajes en las fuentes (FAO (cultivos andinos), MAGAP y documentos del proyecto).

    Úsala para explicar el porqué de una recomendación o para preguntas sobre cultivos, plagas, suelo y rotación.
    Escribe la consulta en español con palabras clave (p. ej. "plagas de la quinua", "rotación después de papa").
    Si la pregunta es sobre un cultivo, pasa `crop` para buscar solo en pasajes que lo mencionan.
    """
    result = runtime.context.sources.search(query, crop)
    docs = result.docs
    citations = [format_citation(d) for d in docs]
    passages = []
    for i, (d, c) in enumerate(zip(docs, citations, strict=True), start=1):
        where = f"p. {c['page_label'] or c['page']}" if c["page"] else (c["section"] or "")
        passages.append(f"[{i}] {c['title']} ({where}; fiabilidad {c['reliability']}):\n{d.page_content[:PASSAGE_CHARS]}")
    content = "\n\n".join(passages) if passages else "No se encontraron pasajes relevantes."
    if crop and result.crop is None:     # nombre que no está en el pool
        hint = f" (parecidos: {', '.join(result.suggestions)})" if result.suggestions else ""
        content = f"No reconozco «{crop}» como cultivo{hint}; resultados generales.\n\n{content}"
    elif crop and not result.filtered:   # cultivo del pool con pasajes sin etiquetar: no se afirma que no existan
        content = f"No pude filtrar los pasajes por «{crop}»; resultados generales.\n\n{content}"
    return Command(update={"citations": citations,
                           "messages": [ToolMessage(content, tool_call_id=runtime.tool_call_id)]})


@tool
def get_crop_profile(runtime: Runtime, crop: str, sections: Annotated[list[Section], Field(min_length=1)]) -> str:
    """Devuelve solo las secciones pedidas de la ficha de un cultivo. Pide solo las secciones que necesitas para responder.

    Secciones:
    - suelo: textura, pH, drenaje, profundidad y exigencia de fertilidad.
    - clima: altitud, temperatura, lluvia y si necesita riego.
    - ciclo_meses: duración del ciclo en meses.
    - plagas / enfermedades: las que lo atacan.
    - efecto_rotacion: qué aporta o quita al suelo (nitrógeno, plagas que hospeda o corta).
    - mano_obra: jornales por hectárea y si se puede mecanizar.
    - facilidad_cultivo: qué tan fácil es de cultivar.
    - mercado: precio de referencia, volatilidad y fuentes.
    - huecos: datos que faltan en la ficha.
    - fuentes: de dónde sale cada dato.
    - siguientes: qué cultivos pueden ir después según las reglas de rotación.
    - sensibilidades: helada, lancha, sequía, nitrógeno y exceso de agua.
    """
    crop_id, suggestions = resolve_crop(crop, runtime.context.kb)
    if crop_id is None:
        return _json({"error": f"«{crop}» no está en el pool de cultivos.", "suggestions": suggestions})
    return _json(crops_repo.get_crop_sections(runtime.context.conn, crop_id, sections, runtime.context.kb.sensitivities))


@tool
def list_crops(runtime: Runtime) -> str:
    """Lista los cultivos que conoce el sistema, con su familia y su tipo (comercial o no comercial)."""
    return _json([{k: c[k] for k in ("crop_id", "name", "family", "crop_type")}
                  for c in crops_repo.list_crops(runtime.context.conn)])


TOOLS = [update_plot, recommend_crop, search_sources, get_crop_profile, list_crops]
