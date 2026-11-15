"""Servicios compartidos de la aplicación (se crean una vez en el lifespan de FastAPI)."""

import sqlite3
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Request
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.factory import build_agent, build_chat_model
from app.config import Settings
from app.engine.models import KnowledgeBase
from app.memory.sessions import Clock, SessionRegistry, utc_now
from app.memory.state import AgentContext
from app.rag.db import connect
from app.rag.retriever import SourceSearch
from app.repository.crops import load_knowledge_base


@dataclass
class Services:
    settings: Settings
    conn: sqlite3.Connection
    kb: KnowledgeBase
    sources: SourceSearch
    retrieval_mode: str
    checkpointer: InMemorySaver
    registry: SessionRegistry
    agent: object | None          # None si no hay OPENAI_API_KEY ni modelo inyectado
    agent_context: AgentContext


def build_services(settings: Settings, chat_model: BaseChatModel | None = None, clock: Clock = utc_now) -> Services:
    db_path = settings.resolve(settings.db_path)
    if not db_path.exists():
        raise RuntimeError(f"No existe {db_path}. Ejecuta: uv run python -m ingestion.build_db")
    conn = connect(db_path)
    kb = load_knowledge_base(conn)
    sources = SourceSearch(conn, settings, kb)
    checkpointer = InMemorySaver()
    registry = SessionRegistry(checkpointer, timedelta(minutes=settings.session_ttl_minutes), clock)
    model = chat_model if chat_model is not None else (build_chat_model(settings) if settings.llm_enabled else None)
    agent = build_agent(model, checkpointer, settings.max_conversation_turns) if model is not None else None
    return Services(settings, conn, kb, sources, sources.mode, checkpointer, registry, agent,
                    AgentContext(kb=kb, conn=conn, sources=sources))


def get_services(request: Request) -> Services:
    return request.app.state.services
