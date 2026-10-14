"""Conversational smalltalk and out-of-scope intent handling.

Provides dynamic conversational responses for greetings, thanks, compliments,
rudeness, off-topic requests, and non-English inquiries without stating any facts.

Step 6 fixes:
- Greetings tolerate repeated letters (hii, heyy, helloo, helo).
- Off-topic / rude checks run ONLY when the message has no programme keyword
  AND no course topic, preventing legit questions like "what subjects match my score"
  from being refused.
- Hindi/Gujarati Unicode ranges and word lists removed (R5 English-only rule).
  Non-ASCII-only messages get a brief English-only notice.
"""
from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional

from app.utils import logger

# Guard against accidental factual numbers or currency in conversational replies
_GUARD_NUMERIC_RE = re.compile(r"[\d₹%]|INR\b", re.IGNORECASE)

# -----------------------------------------------------------------------
# Step 6: greeting pattern now uses \b only at start and tolerates repeated
# letters (hi+, hey+, hello+, helo+, hii+, hiii+).
# -----------------------------------------------------------------------
_GREETING_RE = re.compile(
    r"^\s*(?:h+i+h*|h+e+y+|h+e+l+o+|h+e+l+l+o+|good\s+(?:morning|afternoon|evening|day)|greetings|hola)\b",
    re.IGNORECASE,
)
_THANKS_RE = re.compile(
    r"^\s*(?:thank\s+you|thanks|thx|thank\s+u|many\s+thanks|much\s+appreciated)\b",
    re.IGNORECASE,
)
_BYE_RE = re.compile(
    r"^\s*(?:bye|goodbye|cya|see\s+you|have\s+a\s+good\s+day|take\s+care)\b",
    re.IGNORECASE,
)
_WHO_ARE_YOU_RE = re.compile(
    r"\b(?:who\s+are\s+you|what\s+is\s+your\s+name|what\s+can\s+you\s+do|introduce\s+yourself|tell\s+me\s+about\s+yourself)\b",
    re.IGNORECASE,
)
_RUDE_RE = re.compile(
    r"\b(?:idiot|stupid|useless|dumb|fool|shut\s+up|hate\s+you|rubbish|garbage|worst\s+bot)\b",
    re.IGNORECASE,
)
# Step 6: off-topic terms that are also innocent substrings in course questions
# are matched ONLY when no programme/course context is present.
_OFFTOPIC_RE = re.compile(
    r"\b(?:weather|temperature|rain|joke|sing|song|recipe|cook|cricket|football"
    r"|python\s+code|write\s+code|algorithm|capital\s+of|president|prime\s+minister)\b",
    re.IGNORECASE,
)

# Step 6: removed Hindi/Gujarati Unicode ranges and word lists per R5.
# Only pure-non-ASCII detection remains (no ASCII letters at all).
_NO_ASCII_LETTERS_RE = re.compile(r"^[^a-zA-Z]+$")

# Detect any course-related keyword that should override off-topic/rude checks
_COURSE_KEYWORD_RE = re.compile(
    r"\b(?:bca|bba|mba|mca|fee|fees|admission|syllabus|subject|subjects|"
    r"course|programme|program|semester|year|exam|examination|placement|"
    r"eligib|document|enrol|credit|specializ|duration|lms|mentor|"
    r"charusat|online\s+degree|score|marks|cgpa|sgpa|grading|internship|"
    r"scholarship|faculty|tuition|payment|refund|cancel|attend|webinar)\b",
    re.IGNORECASE,
)

# Pool of at least 6 varied conversational templates
_DEFAULT_TEMPLATES = [
    "Hello! I am the CHARUSAT Online degree assistant. How can I assist you today with our online BCA, BBA, MBA, or MCA programmes?",
    "Hi there! I am here to help you with admissions, curriculum, fees, and guidelines for CHARUSAT's online degree programmes. What would you like to know?",
    "Greetings! Feel free to ask any questions about CHARUSAT's online programmes (BBA, BCA, MBA, MCA) or admission details.",
    "Welcome! I can assist you with details regarding our online degrees, syllabus, examination policies, and admissions. How may I assist you?",
    "Hello! Please let me know what questions you have about CHARUSAT Online degree programmes.",
    "Hi! I am here to assist with any questions about CHARUSAT's online undergraduate and postgraduate degree programmes. What would you like to explore today?",
]

_GREETING_TEMPLATES = [
    "Hello! How can I help you today with CHARUSAT's online degree programmes?",
    "Hi there! What information can I provide about our online BCA, BBA, MBA, or MCA programmes?",
    "Greetings! I am ready to help you with admissions, curriculum, and details for CHARUSAT Online programmes.",
    "Hello! Welcome to CHARUSAT Online. What questions can I answer for you today?",
]

_THANKS_TEMPLATES = [
    "You are very welcome! Let me know if you need any more details about our online programmes.",
    "Happy to help! Feel free to ask if you have any further questions about CHARUSAT Online.",
    "Glad I could help! I am here whenever you have more questions about our online degrees.",
]

_BYE_TEMPLATES = [
    "Goodbye! Feel free to return anytime if you have more questions about CHARUSAT Online programmes.",
    "Have a wonderful day! Best wishes with your educational journey at CHARUSAT.",
    "Thank you for chatting. Feel free to reach back out whenever you need assistance.",
]

_WHO_ARE_YOU_TEMPLATES = [
    "I am the CHARUSAT Online Degree Assistant. I help prospective and current learners with information on Online BCA, BBA, MBA, and MCA programmes, including admissions, curriculum, and policies.",
    "I am an AI assistant dedicated to CHARUSAT's online degree programmes. I can help answer questions regarding our online courses, admission criteria, fee structures, and academic guidelines.",
]

_RUDE_TEMPLATES = [
    "I apologize for any frustration. I am here to assist you with information about CHARUSAT online degree programmes whenever you are ready.",
    "I am sorry if my previous responses were not helpful. Please let me know what specific course information you need, and I will do my best to help.",
]

_OFFTOPIC_TEMPLATES = [
    "I am designed specifically to assist with CHARUSAT Online degree programmes (BCA, BBA, MBA, MCA). I cannot help with external topics, but please feel free to ask about our courses!",
    "My focus is limited to CHARUSAT's online degree courses, admissions, and academic procedures. How can I help you regarding our online programmes?",
]

_NON_ENGLISH_TEMPLATES = [
    "I can only assist in English. Please feel free to ask your questions about CHARUSAT online degree programmes in English, and I will be happy to help!",
    "I am available to assist you in English. Please share your questions regarding our online courses or admissions in English.",
]

SMALLTALK_SYSTEM_PROMPT = """You are the friendly, helpful AI admissions and academic assistant for CHARUSAT Online Degree Programmes (Online BCA, BBA, MBA, MCA).
Your persona and rules:
- Polite, professional, and friendly in English only.
- Keep replies brief (1-3 sentences).
- NEVER state any factual numbers, currency amounts, fee figures, dates, or eligibility percentages.
- State clearly what you can help with: CHARUSAT online programmes, admissions, curriculum, and academic procedures.
- If the user greets you, thank you, or asks who you are, introduce yourself warmly and invite questions about the online programmes.
- If the user is rude or frustrated, remain calm, polite, and brief, and offer assistance.
- If the user asks off-topic things (jokes, weather, sports, programming code), politely state in one sentence that your scope is CHARUSAT online degree programmes.
- If the user writes in any language other than English, reply in English stating that you can assist in English.
- Do NOT provide contact phone numbers or email addresses in small talk."""


def is_smalltalk(question: str) -> bool:
    """Check if query is purely conversational or out-of-scope.

    Step 6 fix: off-topic and rude checks are suppressed when the message
    contains programme or course keywords.  This prevents legitimate questions
    containing words like "score", "match", "function", "rain" from being
    wrongly flagged as off-topic.
    """
    q = question.strip()
    if not q:
        return True

    # Pure non-ASCII (no English letters) -> non-English path
    if _NO_ASCII_LETTERS_RE.match(q):
        return True

    # Fast-path for definite conversational patterns
    if (
        _GREETING_RE.match(q)
        or _THANKS_RE.match(q)
        or _BYE_RE.match(q)
        or _WHO_ARE_YOU_RE.search(q)
    ):
        return True

    # Off-topic / rude ONLY when no course context is present
    has_course_context = bool(_COURSE_KEYWORD_RE.search(q))
    if not has_course_context:
        if _RUDE_RE.search(q) or _OFFTOPIC_RE.search(q):
            return True

    return False


def converse(
    question: str,
    history: Optional[List[Any]] = None,
    llm_client: Optional[Any] = None,
) -> str:
    """Generate a conversational response via LLM chat with template fallbacks and output safety guards."""
    q = question.strip()

    # Pure non-ASCII -> English-only notice
    if _NO_ASCII_LETTERS_RE.match(q):
        return random.choice(_NON_ENGLISH_TEMPLATES)

    has_course_context = bool(_COURSE_KEYWORD_RE.search(q))

    # Off-topic / rude only when no course keywords
    if not has_course_context:
        if _OFFTOPIC_RE.search(q):
            return random.choice(_OFFTOPIC_TEMPLATES)
        if _RUDE_RE.search(q):
            return random.choice(_RUDE_TEMPLATES)

    if _BYE_RE.search(q):
        return random.choice(_BYE_TEMPLATES)
    if _THANKS_RE.search(q):
        return random.choice(_THANKS_TEMPLATES)
    if _WHO_ARE_YOU_RE.search(q):
        return random.choice(_WHO_ARE_YOU_TEMPLATES)
    if _GREETING_RE.match(q):
        return random.choice(_GREETING_TEMPLATES)

    # Try LLM chat if client provided
    if llm_client is not None and hasattr(llm_client, "chat"):
        try:
            reply = llm_client.chat(system=SMALLTALK_SYSTEM_PROMPT, user=q)
            if reply and reply.strip():
                clean_reply = reply.strip()
                # Output guard: discard if numeric, currency, or percent detected
                if not _GUARD_NUMERIC_RE.search(clean_reply):
                    return clean_reply
                logger.info("Smalltalk LLM reply contained numeric/currency tokens; falling back to template pool")
        except Exception as exc:
            logger.warning("Smalltalk LLM chat failed: %s", exc)

    return random.choice(_DEFAULT_TEMPLATES)
