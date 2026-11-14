"""Fixtures compartidas. Las pruebas NO llaman a OpenAI: la base se construye sin embeddings
y el agente usa un modelo de chat con respuestas guionadas."""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.config import Settings
from app.engine.models import KnowledgeBase
from app.main import create_app
from app.rag.db import connect
from app.repository.crops import load_knowledge_base
from ingestion.build_db import build


@pytest.fixture(scope="session")
def settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    db = tmp_path_factory.mktemp("kb") / "knowledge.db"
    s = Settings(openai_api_key="", db_path=db, _env_file=None)
    build(s, s.resolve(db), with_embeddings=False)
    return s


@pytest.fixture(scope="session")
def kb(settings: Settings) -> KnowledgeBase:
    return load_knowledge_base(connect(settings.resolve(settings.db_path)))


class ScriptedChatModel(BaseChatModel):
    """Devuelve, en orden, las respuestas guionadas. Guarda los mensajes que recibió en cada llamada."""

    responses: list[AIMessage]
    seen: list[list[BaseMessage]] = []

    def _generate(self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
        self.seen.append(messages)
        if not self.responses:
            raise AssertionError("El agente pidió más respuestas de las guionadas")
        return ChatResult(generations=[ChatGeneration(message=self.responses.pop(0))])

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedChatModel":
        return self

    @property
    def _llm_type(self) -> str:
        return "scripted"


def tool_call(name: str, args: dict, call_id: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}])


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, minutes: float) -> None:
        self.now += timedelta(minutes=minutes)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def make_client(settings: Settings, clock: FakeClock) -> Iterator[Callable[[ScriptedChatModel | None], TestClient]]:
    clients: list[TestClient] = []

    def factory(model: ScriptedChatModel | None = None) -> TestClient:
        client = TestClient(create_app(settings, chat_model=model, clock=clock))
        client.__enter__()
        clients.append(client)
        return client

    yield factory
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def scripted() -> Callable[..., ScriptedChatModel]:
    def factory(*responses: AIMessage) -> ScriptedChatModel:
        return ScriptedChatModel(responses=list(responses), seen=[])
    return factory


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent
