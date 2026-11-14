"""Esquemas de /v1/sessions (agente conversacional con memoria de corto plazo)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000, examples=["Sembré papa y antes cebada, ¿qué siembro ahora?"])


class Citation(BaseModel):
    source_id: int | None
    title: str | None
    doc_kind: str | None
    reliability: str | None
    page: int | None
    page_label: str | None
    section: str | None


class MessageOut(BaseModel):
    session_id: str
    session_status: Literal["new", "active"]
    expires_at: datetime
    reply: str
    plot: dict
    missing_data: list[str]
    recommendation: dict | None = Field(description="Resultado del motor si se recomendó en este turno")
    citations: list[Citation] = Field(description="Fuentes consultadas en este turno")


class SessionState(BaseModel):
    session_id: str
    expires_at: datetime
    plot: dict
    missing_data: list[str]
    last_recommendation: dict | None
    turns: int
