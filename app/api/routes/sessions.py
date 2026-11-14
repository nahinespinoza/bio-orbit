"""Agente conversacional con memoria de corto plazo por sesión.

El frontend genera el UUID v4 de la sesión. El primer mensaje la crea; vence tras SESSION_TTL_MINUTES
de inactividad o con DELETE. No hay memoria entre sesiones.
"""

from uuid import UUID

import openai
from fastapi import APIRouter, Depends, HTTPException, Response
from langchain.messages import AIMessage
from loguru import logger

from app.api.deps import Services, get_services
from app.engine.validation import missing_fields
from app.schemas.session import MessageIn, MessageOut, SessionState

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


def _session_id(session_id: UUID) -> str:
    if session_id.version != 4:
        raise HTTPException(422, {"code": "INVALID_SESSION_ID", "message": "session_id debe ser un UUID v4."})
    return str(session_id)


def _config(sid: str) -> dict:
    return {"configurable": {"thread_id": sid}}


@router.post("/{session_id}/messages", response_model=MessageOut, summary="Enviar un mensaje al agente")
def post_message(session_id: UUID, body: MessageIn, services: Services = Depends(get_services)) -> MessageOut:
    sid = _session_id(session_id)
    if services.agent is None:
        raise HTTPException(503, {"code": "LLM_NOT_CONFIGURED",
                                  "message": "Falta OPENAI_API_KEY en .env. /v1/recommend funciona sin ella."})
    status, lock = services.registry.begin(sid)
    with lock:  # mensajes de la misma sesión, uno a la vez
        config = _config(sid)
        before = services.agent.get_state(config).values
        before_ids = {m.id for m in before.get("messages", [])}
        citations_before = len(before.get("citations", []))
        try:
            state = services.agent.invoke({"messages": [{"role": "user", "content": body.message}]}, config,
                                          context=services.agent_context)
        except openai.OpenAIError as exc:
            logger.exception("Error de OpenAI en la sesión {}", sid)
            raise HTTPException(502, {"code": "LLM_ERROR", "message": f"El modelo no respondió: {type(exc).__name__}"}) from exc
        services.registry.touch(sid)

    new_messages = [m for m in state["messages"] if m.id not in before_ids]
    tools_used = [tc["name"] for m in new_messages if isinstance(m, AIMessage) for tc in m.tool_calls]
    logger.info("Sesión {} ({}): herramientas {}", sid, status, tools_used or "ninguna")
    recommended = "recommend_crop" in tools_used
    last_ai = next(m for m in reversed(state["messages"]) if isinstance(m, AIMessage))
    plot = state.get("plot") or {}
    return MessageOut(
        session_id=sid, session_status=status, expires_at=services.registry.expires_at(sid),
        reply=last_ai.text, plot=plot, missing_data=missing_fields(plot),
        recommendation=state.get("last_recommendation") if recommended else None,
        citations=state.get("citations", [])[citations_before:],
    )


@router.get("/{session_id}", response_model=SessionState, summary="Estado de la sesión")
def get_session(session_id: UUID, services: Services = Depends(get_services)) -> SessionState:
    sid = _session_id(session_id)
    if services.agent is None or not services.registry.is_active(sid):
        raise HTTPException(404, {"code": "SESSION_NOT_FOUND", "message": "La sesión no existe o venció."})
    values = services.agent.get_state(_config(sid)).values
    plot = values.get("plot") or {}
    return SessionState(session_id=sid, expires_at=services.registry.expires_at(sid), plot=plot,
                        missing_data=missing_fields(plot), last_recommendation=values.get("last_recommendation"),
                        turns=sum(1 for m in values.get("messages", []) if m.type == "human"))


@router.delete("/{session_id}", status_code=204, summary="Olvidar la sesión de inmediato")
def delete_session(session_id: UUID, services: Services = Depends(get_services)) -> Response:
    sid = _session_id(session_id)
    services.registry.delete(sid)
    return Response(status_code=204)
