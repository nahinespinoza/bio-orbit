"""Configuración leída de variables de entorno o de `.env` (en la raíz del repo)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # api-agent/
REPO_ROOT = PROJECT_ROOT.parent  # el .env vive en la raíz del monorepo


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str | None = None
    chat_model: str = "gpt-5.4-mini"
    chat_reasoning_effort: str = "low"  # minimal | low | medium | high (modelos de razonamiento gpt-5.x)
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    db_path: Path = Path("data/knowledge.db")
    structured_data_dir: Path = Path("knowledge/structured")
    pdf_dir: Path = Path("knowledge/pdfs")
    web_dir: Path = Path("knowledge/web")
    project_docs_dir: Path = Path("knowledge/docs")

    session_ttl_minutes: int = 120
    session_cleanup_interval_seconds: int = 300
    max_conversation_turns: int = 12

    rag_top_k: int = 5

    def resolve(self, path: Path) -> Path:
        """Rutas relativas se resuelven contra la carpeta del proyecto, no contra el cwd."""
        return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()

    @property
    def llm_enabled(self) -> bool:
        """Hay clave real (no vacía ni el placeholder del .env)."""
        key = (self.openai_api_key or "").strip()
        return bool(key) and not key.upper().startswith("PON_AQUI")


@lru_cache
def get_settings() -> Settings:
    return Settings()
