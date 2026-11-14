"""Herramientas del agente. El LLM conversa; estas herramientas validan, recomiendan y buscan evidencia."""

import json
from typing import Literal

from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langgraph.types import Command

from app.engine.recommender import recommend
from app.engine.validation import REQUIRED_FIELDS, missing_fields, resolve_crop, validate_plot
from app.memory.state import AgentContext, CropAdvisorState
from app.rag.retriever import format_citation
from app.repository import crops as crops_repo

Runtime = ToolRuntime[AgentContext, CropAdvisorState]
Priority = Literal["market_value", "speed", "fewer_pests", "low_labor"]
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
    for key in ("priorities", "last_pest", "rotation_cycles", "use_source5"):
        if key in update:
            merged[key] = update[key]
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
) -> Command:
    """Registra datos del lote que dio el agricultor. Envía SOLO los campos que mencionó en la conversación;
    deja en null todo lo que no ha dicho (así se sabe qué falta preguntar).

    previous_crops: cultivos anteriores del más reciente al más antiguo (nombres comunes, p. ej. ["papa", "cebada"]).
    new_land: true si el lote nunca se cultivó (excluye previous_crops).
    priorities: de 1 a 3, en orden de importancia.
    "unknown" solo cuando el agricultor DIJO que no sabe ese dato; nunca para datos que no se han preguntado.
    last_pest: plaga o enfermedad fuerte del último ciclo, solo si la mencionó.
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


def _summary(result: dict) -> dict:
    """Versión compacta del resultado del motor para el LLM."""
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
        }

    rot = result["rotation"]
    return {
        "status": "ok",
        "recommendation": crop(result["recommendation"]),
        "alternatives": [crop(a) for a in result["alternatives"]],
        "rotation": {"sequence": [f"{s['cycle']}. {s['name']} ({s['role']}; "
                                  f"{s['transition']['kind'] + ': ' + s['transition']['source_note'] if s['transition'] else 'inicio'})"
                                  for s in rot["sequence"]],
                     "ends_with_ender": rot["ends_with_ender"], "warnings": rot["warnings"]} if rot else None,
        "discarded": [f"{d['crop']}: {d['filter']} — {d['reason']}" for d in result["discarded"]],
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
        "messages": [ToolMessage(_json(_summary(result)), tool_call_id=runtime.tool_call_id)],
    })


@tool
def search_sources(runtime: Runtime, query: str) -> Command:
    """Busca pasajes en las fuentes (FAO, MAGAP, INIAP, estudios de Ecuador y documentos del proyecto).

    Úsala para explicar el porqué de una recomendación o para preguntas sobre cultivos, plagas, suelo y rotación.
    Escribe la consulta en español con palabras clave (p. ej. "plagas de la quinua", "rotación después de papa").
    """
    docs = runtime.context.retriever.invoke(query)
    citations = [format_citation(d) for d in docs]
    passages = []
    for i, (d, c) in enumerate(zip(docs, citations, strict=True), start=1):
        where = f"p. {c['page_label'] or c['page']}" if c["page"] else (c["section"] or "")
        passages.append(f"[{i}] {c['title']} ({where}; fiabilidad {c['reliability']}):\n{d.page_content[:PASSAGE_CHARS]}")
    content = "\n\n".join(passages) if passages else "No se encontraron pasajes relevantes."
    return Command(update={"citations": citations,
                           "messages": [ToolMessage(content, tool_call_id=runtime.tool_call_id)]})


@tool
def get_crop_profile(runtime: Runtime, crop: str) -> str:
    """Devuelve la ficha de un cultivo: suelo, clima, ciclo, plagas, mano de obra, mercado, fuentes y huecos de datos."""
    crop_id, suggestions = resolve_crop(crop, runtime.context.kb)
    if crop_id is None:
        return _json({"error": f"«{crop}» no está en el pool de cultivos.", "suggestions": suggestions})
    return _json(crops_repo.get_crop_profile(runtime.context.conn, crop_id))


@tool
def list_crops(runtime: Runtime) -> str:
    """Lista los cultivos que conoce el sistema, con su familia y su tipo (comercial o no comercial)."""
    return _json([{k: c[k] for k in ("crop_id", "name", "family", "crop_type")}
                  for c in crops_repo.list_crops(runtime.context.conn)])


TOOLS = [update_plot, recommend_crop, search_sources, get_crop_profile, list_crops]
