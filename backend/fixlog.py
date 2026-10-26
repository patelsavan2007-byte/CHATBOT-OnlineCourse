p='app/routes/chat_routes.py'
with open(p,'rb') as f:
    data=f.read()
bad = b'Record an interaction event in db.chat_events for admin analytics."""\n'
good = b'def _log_chat_event(\n    db,\n    question: str,\n    answer: str,\n    user: Optional[Dict[str, Any]] = None,\n    conversation_id: Optional[str] = None,\n    message_id: Optional[str] = None,\n    rag_result: Any = None,\n    rag_chain: Any = None,\n) -> None:\n    """Record an interaction event in db.chat_events for admin analytics."""\n'
data2 = data.replace(bad, good)
open(p,'wb').write(data2)
