"""Registro de sesiones: vencimiento por inactividad (TTL) y serialización de mensajes por sesión.

InMemorySaver guarda los mensajes pero no tiene TTL propio: este registro decide cuándo vence una sesión
y borra su hilo del checkpointer. Todo vive en memoria del proceso (exige 1 worker de uvicorn).
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from langgraph.checkpoint.base import BaseCheckpointSaver

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class _Session:
    last_seen: datetime
    lock: threading.Lock = field(default_factory=threading.Lock)


class SessionRegistry:
    def __init__(self, checkpointer: BaseCheckpointSaver, ttl: timedelta, clock: Clock = utc_now):
        self._checkpointer = checkpointer
        self._ttl = ttl
        self._clock = clock
        self._sessions: dict[str, _Session] = {}
        self._guard = threading.Lock()

    def _expired(self, s: _Session, now: datetime) -> bool:
        return now - s.last_seen > self._ttl

    def begin(self, session_id: str) -> tuple[str, threading.Lock]:
        """Marca actividad. Devuelve ('new' | 'active', lock de la sesión). Una sesión vencida empieza de cero."""
        now = self._clock()
        with self._guard:
            s = self._sessions.get(session_id)
            if s is not None and self._expired(s, now):
                self._checkpointer.delete_thread(session_id)
                s = None
            status = "active" if s is not None else "new"
            if s is None:
                s = _Session(last_seen=now)
                self._sessions[session_id] = s
            s.last_seen = now
            return status, s.lock

    def touch(self, session_id: str) -> None:
        with self._guard:
            if session_id in self._sessions:
                self._sessions[session_id].last_seen = self._clock()

    def expires_at(self, session_id: str) -> datetime | None:
        with self._guard:
            s = self._sessions.get(session_id)
            return s.last_seen + self._ttl if s else None

    def is_active(self, session_id: str) -> bool:
        with self._guard:
            s = self._sessions.get(session_id)
            return s is not None and not self._expired(s, self._clock())

    def delete(self, session_id: str) -> bool:
        with self._guard:
            existed = self._sessions.pop(session_id, None) is not None
        self._checkpointer.delete_thread(session_id)
        return existed

    def purge_expired(self) -> list[str]:
        now = self._clock()
        with self._guard:
            expired = [sid for sid, s in self._sessions.items() if self._expired(s, now)]
            for sid in expired:
                del self._sessions[sid]
        for sid in expired:
            self._checkpointer.delete_thread(sid)
        return expired

    def __len__(self) -> int:
        with self._guard:
            return len(self._sessions)
