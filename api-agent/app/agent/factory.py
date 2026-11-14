"""Construcción del agente con create_agent de LangChain."""

import json
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, before_model, dynamic_prompt
from langchain.messages import HumanMessage, RemoveMessage
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.runtime import Runtime

from app.agent.tools import TOOLS
from app.config import Settings
from app.engine.validation import missing_fields
from app.memory.state import AgentContext, CropAdvisorState

SYSTEM_PROMPT = (Path(__file__).with_name("system_prompt.md")).read_text(encoding="utf-8")


@dynamic_prompt
def plot_aware_prompt(request: ModelRequest) -> str:
    """System prompt fijo + lo que ya se sabe del lote en esta sesión (lo validó update_plot)."""
    plot = request.state.get("plot") or {}
    missing = missing_fields(plot)
    return (f"{SYSTEM_PROMPT}\n\n## Datos del lote registrados en esta conversación\n"
            f"```json\n{json.dumps(plot, ensure_ascii=False)}\n```\n"
            f"Datos que aún faltan (por orden de importancia): {', '.join(missing) if missing else 'ninguno'}.")


def make_history_trimmer(max_turns: int):
    """Conserva los últimos `max_turns` turnos, cortando siempre en un mensaje del usuario
    para no separar una llamada a herramienta de su resultado. El plot estructurado no se toca."""

    @before_model
    def trim_history(state: CropAdvisorState, runtime: Runtime) -> dict[str, Any] | None:
        messages = state["messages"]
        human_idx = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
        if len(human_idx) <= max_turns:
            return None
        cut = human_idx[-max_turns]
        return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *messages[cut:]]}

    return trim_history


def build_chat_model(settings: Settings) -> BaseChatModel:
    # Responses API: los modelos gpt-5.4 no aceptan herramientas + reasoning_effort en /v1/chat/completions.
    return ChatOpenAI(model=settings.chat_model, api_key=settings.openai_api_key,
                      reasoning_effort=settings.chat_reasoning_effort, use_responses_api=True)


def build_agent(model: BaseChatModel, checkpointer: BaseCheckpointSaver, max_turns: int):
    return create_agent(
        model=model,
        tools=TOOLS,
        state_schema=CropAdvisorState,
        context_schema=AgentContext,
        middleware=[plot_aware_prompt, make_history_trimmer(max_turns)],
        checkpointer=checkpointer,
    )
