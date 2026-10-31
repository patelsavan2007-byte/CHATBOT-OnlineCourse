import threading

_lock = threading.Lock()
_calls = {}


def record_call(question_id: str):
    with _lock:
        _calls[question_id] = _calls.get(question_id, 0) + 1
        return _calls[question_id]


def get_calls(question_id: str):
    with _lock:
        return _calls.get(question_id, 0)


def reset(question_id: str = None):
    with _lock:
        if question_id:
            _calls.pop(question_id, None)
        else:
            _calls.clear()
