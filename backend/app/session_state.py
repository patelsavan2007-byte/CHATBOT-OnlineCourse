import time
from typing import Dict, Any

_store: Dict[str, Dict[str, Any]] = {}


def get_state(conversation_id: str):
    if not conversation_id:
        return {}
    return _store.get(conversation_id, {})


def set_state(conversation_id: str, state: Dict[str, Any]):
    if not conversation_id:
        return
    _store[conversation_id] = state


def update_state(conversation_id: str, **kwargs):
    if not conversation_id:
        return {}
    st = dict(_store.get(conversation_id, {}))
    st.update(kwargs)
    _store[conversation_id] = st
    return st


def clear_state(conversation_id: str):
    if not conversation_id:
        return
    _store.pop(conversation_id, None)
