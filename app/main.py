"""Aplicación FastAPI.

Ejecutar (1 worker: la memoria de sesión vive en el proceso):
    uv run uvicorn app.main:app --reload
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI
from langchain_core.language_models import BaseChatModel
from loguru import logger

from app.api.deps import Services, build_services, get_services
from app.api.routes import crops, recommend, sessions
from app.config import Settings, get_settings
from app.memory.sessions import Clock, utc_now
from app.rag.db import meta


async def _purge_loop(services: Services) -> None:
    while True:
        await asyncio.sleep(services.settings.session_cleanup_interval_seconds)
        expired = services.registry.purge_expired()
        if expired:
            logger.info("Sesiones vencidas eliminadas: {}", len(expired))


def create_app(settings: Settings | None = None, chat_model: BaseChatModel | None = None, clock: Clock = utc_now) -> FastAPI:
    settings = settings or get_settings()

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        services = build_services(settings, chat_model, clock)
        app.state.services = services
        logger.info("API lista · LLM: {} · búsqueda: {} · cultivos: {}",
                    settings.chat_model if services.agent else "desactivado", services.retrieval_mode, len(services.kb.crops))
        task = asyncio.create_task(_purge_loop(services))
        try:
            yield
        finally:
            task.cancel()
            services.conn.close()

    app = FastAPI(title="Crop Advisor API", version="0.1.0", lifespan=lifespan,
                  description="Agente que guía al agricultor en la elección de cultivo y rotación (sierra andina).")
    app.include_router(sessions.router)
    app.include_router(recommend.router)
    app.include_router(crops.router)

    @app.get("/health", tags=["health"])
    def health(services: Services = Depends(get_services)) -> dict:
        return {
            "status": "ok",
            "llm_enabled": services.agent is not None,
            "retrieval_mode": services.retrieval_mode,
            "crops": len(services.kb.crops),
            "active_sessions": len(services.registry),
            "knowledge_base_built_at": meta(services.conn, "built_at"),
        }

    return app


app = create_app()
