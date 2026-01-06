from typing import Dict, Any


class ConversationStateManager:
    """Simple in-memory session store keyed by session/user id."""

    def __init__(self) -> None:
        self._state: Dict[str, Dict[str, Any]] = {}

    def get_state(self, session_id: str) -> Dict[str, Any]:
        return self._state.setdefault(session_id, {})

    def update_state(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = self._state.setdefault(session_id, {})
        state.update(payload)
        return state
