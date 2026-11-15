"""Estado de la sesión del agente (memoria de corto plazo, guardada por InMemorySaver por thread_id)."""

import operator
from dataclasses import dataclass
from sqlite3 import Connection
from typing import Annotated, NotRequired

from langchain.agents import AgentState
from langchain_core.retrievers import BaseRetriever

from app.engine.models import KnowledgeBase


class CropAdvisorState(AgentState):
    # Datos del lote ya VALIDADOS (los escribe update_plot). No se recortan con los mensajes.
    plot: NotRequired[dict]
    # Último resultado del motor (lo escribe recommend_crop).
    last_recommendation: NotRequired[dict | None]
    # Citas acumuladas en la sesión; la API devuelve solo las del turno actual.
    citations: Annotated[list[dict], operator.add]


@dataclass
class AgentContext:
    """Dependencias de solo lectura que reciben las herramientas (runtime.context)."""
    kb: KnowledgeBase
    conn: Connection
    retriever: BaseRetriever
