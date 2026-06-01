from collections import deque
from dataclasses import dataclass, field
import uuid


MAX_TURNS = 6  # user/assistant pairs kept per session


@dataclass
class Turn:
    role: str   # "user" | "assistant"
    content: str


@dataclass
class Session:
    session_id: str
    turns: deque = field(default_factory=lambda: deque(maxlen=MAX_TURNS * 2))


class MemoryService:
    """
    In-process session store. Holds the last MAX_TURNS user/assistant
    pairs per session. Not thread-safe for concurrent writes to the
    same session_id; acceptable for single-worker dev deployments.
    Replace the backing store with Redis for production.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, session_id: str | None = None) -> str:
        if session_id and session_id in self._sessions:
            return session_id
        sid = session_id or str(uuid.uuid4())
        self._sessions[sid] = Session(session_id=sid)
        return sid

    def add_turn(self, session_id: str, role: str, content: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Session not found: {session_id!r}")
        session.turns.append(Turn(role=role, content=content))

    def get_history(self, session_id: str) -> list[Turn]:
        session = self._sessions.get(session_id)
        if session is None:
            return []
        return list(session.turns)

    def format_history_for_prompt(self, session_id: str) -> str:
        turns = self.get_history(session_id)
        if not turns:
            return ""
        lines = []
        for turn in turns:
            prefix = "User" if turn.role == "user" else "Assistant"
            lines.append(f"{prefix}: {turn.content}")
        return "\n".join(lines)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def active_sessions(self) -> int:
        return len(self._sessions)
