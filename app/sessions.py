from __future__ import annotations

import uuid
from typing import Protocol

from app.types import SessionState


class SessionStore(Protocol):
    def get(self, session_id: str) -> SessionState: ...
    def put(self, state: SessionState) -> None: ...


class MemorySessionStore:
    def __init__(self) -> None:
        self._data: dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        if session_id not in self._data:
            self._data[session_id] = SessionState(session_id=session_id)
        return self._data[session_id]

    def put(self, state: SessionState) -> None:
        self._data[state.session_id] = state

    def new_id(self) -> str:
        return uuid.uuid4().hex


STORE = MemorySessionStore()
