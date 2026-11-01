import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_RESOURCES_CACHE: Optional[List[Dict[str, Any]]] = None


def _load_resources() -> List[Dict[str, Any]]:
    global _RESOURCES_CACHE
    if _RESOURCES_CACHE is not None:
        return _RESOURCES_CACHE

    json_path = Path(__file__).resolve().parent / "data" / "resource_links.json"
    if not json_path.exists():
        logger.warning("resource_links.json not found at %s", json_path)
        _RESOURCES_CACHE = []
        return _RESOURCES_CACHE

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            _RESOURCES_CACHE = json.load(f)
    except Exception as exc:
        logger.error("Failed to load resource_links.json: %s", exc)
        _RESOURCES_CACHE = []

    return _RESOURCES_CACHE


def _matches_trigger(text: str, trigger: str) -> bool:
    """Check if trigger phrase matches within text on word boundaries."""
    # Build regex with word boundaries around the trigger phrase
    pattern = r"\b" + re.escape(trigger.strip().lower()) + r"\b"
    return bool(re.search(pattern, text.lower()))


def get_matching_resources(question: str) -> List[Dict[str, Any]]:
    """Return resource entries that match the question.
    Preserves strict priority order: admission cancellation first, then fees refund policy.
    """
    if not question:
        return []

    resources = _load_resources()
    matched = []
    for entry in resources:
        triggers = entry.get("triggers", [])
        for trig in triggers:
            if _matches_trigger(question, trig):
                matched.append(entry)
                break

    # Ensure admission_cancellation comes before fees_refund_policy if both match
    def sort_key(item: Dict[str, Any]) -> int:
        if item.get("id") == "admission_cancellation":
            return 0
        if item.get("id") == "fees_refund_policy":
            return 1
        return 2

    matched.sort(key=sort_key)
    return matched


def format_resource_block(resource: Dict[str, Any]) -> str:
    """Format a resource block for insertion into assistant response."""
    res_id = resource.get("id")
    url = resource.get("url", "")

    if res_id == "admission_cancellation":
        steps = resource.get("steps", [])
        steps_text = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(steps))
        return f"Admission cancellation steps:\n{steps_text}"

    if res_id == "fees_refund_policy":
        title = resource.get("title", "Official fees refund policy (PDF)")
        return f"{title}: {url}"

    # Generic fallback
    title = resource.get("title", "")
    return f"{title}: {url}" if title else url


def apply_resource_links(question: str, answer_text: str) -> str:
    """Appends matching official resource links/steps to the answer.
    Skips resources if their URL is already present in answer_text.
    Never alters unrelated answers.
    Strictly forbids em dash (U+2014).
    """
    if not question or not answer_text:
        return answer_text

    matched = get_matching_resources(question)
    if not matched:
        return answer_text

    blocks_to_append = []
    for res in matched:
        url = res.get("url", "")
        # Check if URL (or decoded variant) already in answer
        if url and (url in answer_text or url.replace("%20", " ") in answer_text):
            continue

        block = format_resource_block(res)
        # Enforce no em-dash
        block = block.replace("\u2014", "-")
        blocks_to_append.append(block)

    if not blocks_to_append:
        return answer_text

    combined_blocks = "\n\n".join(blocks_to_append)
    return f"{answer_text.rstrip()}\n\n{combined_blocks}"
