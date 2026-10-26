"""Conversation state and turn analysis for the CHARUSAT Online Course Chatbot.

Provides pure functional analysis of user turns and dialogue history to construct
a structured TurnPlan, resolving programme inheritance, topic tracking, year/semester
context, and query rebuilding for robust multi-turn retrieval without shared global state.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


PROGRAM_MAP = {
    "online_bca": "Online BCA",
    "online_bba": "Online BBA",
    "online_mba": "Online MBA",
    "online_mca": "Online MCA",
}

# Regex patterns for programme recognition (case-insensitive, 3-letter acronym safe)
_PROGRAM_PATTERNS = [
    (re.compile(r"\b(?:online\s+)?bca\b|bachelor\s+of\s+computer\s+applications", re.I), "online_bca"),
    (re.compile(r"\b(?:online\s+)?bba\b|bachelor\s+of\s+business\s+administration", re.I), "online_bba"),
    (re.compile(r"\b(?:online\s+)?mba\b|master\s+of\s+business\s+administration", re.I), "online_mba"),
    (re.compile(r"\b(?:online\s+)?mca\b|master\s+of\s+computer\s+applications", re.I), "online_mca"),
]

# Year to semester structural configuration (standard Indian university structure)
YEAR_TO_SEMESTERS = {
    1: [1, 2],
    2: [3, 4],
    3: [5, 6],
}

SEMESTER_TO_YEAR = {
    1: 1, 2: 1,
    3: 2, 4: 2,
    5: 3, 6: 3,
}

_TOPIC_REGEXES = {
    "fees": re.compile(
        r"\b(?:fee|fees|cost|tuition|price|installment|installments|payment|pay)\b", re.I
    ),
    "subjects": re.compile(
        r"\b(?:subject|subjects|syllabus|curriculum|course\s+structure|what\s+is\s+taught)\b", re.I
    ),
    "specializations": re.compile(
        r"\b(?:speciali[zs]ation|speciali[zs]ations|elective|electives|stream|streams|branch|branches)\b", re.I
    ),
    "eligibility": re.compile(
        r"\b(?:eligib(?:le|ility)?|criteri[ao]|qualif(?:y|ication|ications)|requirement|requirements|who\s+can\s+apply)\b", re.I
    ),
    "admission": re.compile(
        r"\b(?:admiss(?:ion|ions)?|apply|application|applications|enro?l(?:l?|l?ment)?|registration|registrations|intake|documents?)\b", re.I
    ),
    "duration": re.compile(
        r"\b(?:duration|how\s+long|how\s+many\s+years|how\s+many\s+semesters?|credit|credits|total\s+credits)\b", re.I
    ),
    "grading": re.compile(
        r"\b(?:grad(?:ing|e|es)|pass(?:ing)?|cgpa|sgpa|marks|evaluat(?:ion|e)|exam|exams|examination|examinations)\b", re.I
    ),
    "refund": re.compile(
        r"\b(?:refund\w*|money\s+back|cancell(?:ation|ed|ing)?|withdraw(?:al)?)\b", re.I
    ),
    "lms": re.compile(
        r"\b(?:lms|password|login|portal|forgot\s+password|technical\s+support)\b", re.I
    ),
    "career": re.compile(
        r"\b(?:placement|placements|recruit|recruiters|recruiting|job|jobs|career|hiring|companies)\b", re.I
    ),
    "contact": re.compile(
        r"\b(?:contact|phone|email|helpline|reach\s+out|address|office)\b", re.I
    ),
}

# Step 2 fix: extended _COMPARE_RE to match program and programme variants, both/each/every/all four
_COMPARE_RE = re.compile(
    r"\b(?:compare|comparison|difference|differ|vs|versus"
    r"|all\s+program(?:me)?s?|each\s+program(?:me)?s?"
    r"|across\s+program(?:me)?s?"
    r"|every\s+program(?:me)?s?|both\s+program(?:me)?s?"
    r"|all\s+four(?: program(?:me)?s?)?)\b",
    re.I,
)

_FOLLOWUP_SHORT_PROG_RE = re.compile(
    r"^\s*(?:and\s+|or\s+)?(?:for\s+|what\s+about\s+|how\s+about\s+)?(?:the\s+)?(?:online\s+)?(bca|bba|mba|mca)(?:\s+(?:programme|program|course|degree))?\s*[!?.]*\s*$",
    re.I,
)

_YEAR_RE = re.compile(
    r"\b(?:year\s*([1-3])|([1-3])(?:st|nd|rd)?\s*year|(first|second|third)\s*year)\b", re.I
)

_SEM_RE = re.compile(
    r"\b(?:sem(?:ester)?\s*([1-6])|([1-6])(?:st|nd|rd|th)?\s*sem(?:ester)?)\b", re.I
)

_WORD_TO_NUM = {"first": 1, "second": 2, "third": 3}

_NAME_INTRO_RE = re.compile(
    r"\b(?:my\s+name\s+is|call\s+me|i\s+am|i'm)\s+([A-Za-z][A-Za-z'’.-]*(?:\s+[A-Za-z][A-Za-z'’.-]*)?)",
    re.IGNORECASE,
)
_NAME_STOPWORDS = {
    "a", "an", "the", "interested", "looking", "planning", "from", "here",
    "currently", "not", "just", "only", "still", "also", "very", "so",
    "and", "or", "but", "with", "in", "for", "about", "trying", "considering",
    "student", "studying", "working", "applying", "asking", "sorry", "good",
    "fine", "okay", "ok", "confused", "new", "unable", "not",
}
_NAME_QUERY_RE = re.compile(
    r"\b(?:what(?:'s|\s+is)\s+my\s+name|do\s+you\s+(?:know|remember)\s+my\s+name|who\s+am\s+i)\b",
    re.IGNORECASE,
)


def _clean_name(value: str) -> Optional[str]:
    tokens = [t for t in (value or "").replace("’", "'").split() if t]
    kept: List[str] = []
    for token in tokens:
        cleaned = token.strip(".,!?;:'\"")
        if not cleaned:
            continue
        if cleaned.lower() in _NAME_STOPWORDS:
            break
        kept.append(cleaned)
        if len(kept) == 2:
            break
    if not kept:
        return None
    name = " ".join(kept)
    if len(name) < 2:
        return None
    return name


def extract_user_name(
    question: str = "",
    history: Optional[List[Dict[str, Any]]] = None,
) -> Optional[str]:
    """Return the user's name from the current turn or earlier user turns."""
    candidates: List[str] = []
    if question:
        candidates.append(question)
    for msg in reversed(history or []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = (msg.get("content") or "").strip()
            if content:
                candidates.append(content)
        elif isinstance(msg, (tuple, list)) and msg:
            candidates.append(str(msg[0]))

    for text in candidates:
        match = _NAME_INTRO_RE.search(text)
        if match:
            name = _clean_name(match.group(1))
            if name:
                return name
    return None


def build_session_state(
    question: str,
    plan: TurnPlan,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build the compact session state sent to the prompt and the client."""
    last_topic = plan.topic if plan.topic != "general" else ""
    if not last_topic:
        for msg in reversed(history or []):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = (msg.get("content") or "").strip()
                if content:
                    prior = analyze_turn(content, history=None)
                    if prior.topic != "general":
                        last_topic = prior.topic
                        break
    return {
        "activeProgrammes": list(plan.programmes),
        "userName": extract_user_name(question, history),
        "lastTopic": last_topic or "general",
    }


@dataclass
class TurnPlan:
    """Structured understanding of user's query and dialogue context."""
    raw_question: str
    programmes: List[str] = field(default_factory=list)
    topic: str = "general"
    year: Optional[int] = None
    semester: Optional[int] = None
    semesters_for_year: List[int] = field(default_factory=list)
    is_followup: bool = False
    is_compare: bool = False
    standalone_question: str = ""

    @property
    def primary_program(self) -> Optional[str]:
        return self.programmes[0] if self.programmes else None

    @property
    def program_display_names(self) -> List[str]:
        return [PROGRAM_MAP.get(p, p) for p in self.programmes]


def _detect_programmes_in_text(text: str) -> List[str]:
    """Find all programmes mentioned in text in order of appearance."""
    matches: List[Tuple[int, str]] = []
    for pat, prog_id in _PROGRAM_PATTERNS:
        for m in pat.finditer(text):
            matches.append((m.start(), prog_id))
    matches.sort(key=lambda x: x[0])
    seen = set()
    result = []
    for _, prog_id in matches:
        if prog_id not in seen:
            seen.add(prog_id)
            result.append(prog_id)
    return result


def _detect_year_semester(text: str) -> Tuple[Optional[int], Optional[int], List[int]]:
    """Extract explicit year or semester numbers from text."""
    year: Optional[int] = None
    semester: Optional[int] = None

    sem_m = _SEM_RE.search(text)
    if sem_m:
        val_str = sem_m.group(1) or sem_m.group(2)
        if val_str:
            semester = int(val_str)
            year = SEMESTER_TO_YEAR.get(semester)

    if year is None:
        year_m = _YEAR_RE.search(text)
        if year_m:
            if year_m.group(1):
                year = int(year_m.group(1))
            elif year_m.group(2):
                year = int(year_m.group(2))
            elif year_m.group(3):
                year = _WORD_TO_NUM.get(year_m.group(3).lower())

    semesters = YEAR_TO_SEMESTERS.get(year, []) if year else ([semester] if semester else [])
    return year, semester, semesters


def _detect_topic(text: str) -> str:
    """Detect topic category from text using multi-label lexicon scoring."""
    try:
        from app.lexicon import detect_primary_topic
        return detect_primary_topic(text)
    except Exception:
        for topic, pat in _TOPIC_REGEXES.items():
            if pat.search(text):
                return topic
        return "general"


def analyze_turn(
    question: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> TurnPlan:
    """Analyze the user's current question and conversational history into a TurnPlan.

    Inheritance Rules:
    1. Only USER messages in history are scanned for context; assistant messages are never used.
    2. A message that contains both its own programme and its own topic inherits nothing.
    3. If current query lacks a programme, inherit from the most recent user turn that named one.
    4. Switching queries ("for mba", "and for MCA?") replace the programme, inheriting topic & year.
    5. Follow-ups specifying a year/semester ("for year 2?", "year 2 subjects") keep the active programme.
    """
    raw_q = question.strip()
    curr_progs = _detect_programmes_in_text(raw_q)
    curr_topic = _detect_topic(raw_q)
    curr_year, curr_sem, curr_sems = _detect_year_semester(raw_q)

    # Determine if this message is a switch/follow-up
    short_switch_m = _FOLLOWUP_SHORT_PROG_RE.match(raw_q)
    is_compare = len(curr_progs) >= 2 or bool(_COMPARE_RE.search(raw_q))

    # Extract user history from history list
    user_queries: List[str] = []
    if history:
        for msg in history:
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "").strip()
                if content:
                    user_queries.append(content)
            elif isinstance(msg, (tuple, list)) and len(msg) >= 1:
                content = str(msg[0]).strip()
                if content:
                    user_queries.append(content)

    resolved_progs = list(curr_progs)
    resolved_topic = curr_topic
    resolved_year = curr_year
    resolved_sem = curr_sem
    resolved_sems = list(curr_sems)
    is_followup = False

    # Check if we should inherit from history
    if user_queries:
        # Analyze previous user turn
        prev_plan = analyze_turn(user_queries[-1], history=None)

        if short_switch_m:
            # "for mba" / "and for MCA?" / "mca" -> switches programme, retains topic & year
            is_followup = True
            inherited_topic = None
            for uq in reversed(user_queries):
                plan_t = analyze_turn(uq, history=None)
                if plan_t.topic != "general":
                    inherited_topic = plan_t.topic
                    break
            if inherited_topic:
                resolved_topic = inherited_topic
            elif prev_plan.topic != "general":
                resolved_topic = prev_plan.topic

            if resolved_year is None:
                for uq in reversed(user_queries):
                    y, s, sems = _detect_year_semester(uq)
                    if y is not None or s is not None:
                        resolved_year = y
                        resolved_sem = s
                        resolved_sems = list(sems)
                        break
                if resolved_year is None and prev_plan.year is not None:
                    resolved_year = prev_plan.year
                    resolved_sem = prev_plan.semester
                    resolved_sems = list(prev_plan.semesters_for_year)
        elif not curr_progs:
            # Current message did NOT name a programme
            # Scan backwards for most recent user message naming a programme
            inherited_progs = []
            for uq in reversed(user_queries):
                found = _detect_programmes_in_text(uq)
                if found:
                    inherited_progs = found
                    break

            if inherited_progs and not is_compare:
                resolved_progs = inherited_progs
                is_followup = True

            # If current message is just "for year 2?" or "year 2", inherit topic
            if curr_topic == "general" and prev_plan.topic != "general":
                resolved_topic = prev_plan.topic
                is_followup = True
            elif curr_topic != "general":
                is_followup = bool(inherited_progs)
        else:
            # Current message names programme and topic -> inherits nothing unless explicit follow-up
            pass

    # Build standalone question
    standalone_q = _build_standalone_question(
        raw_question=raw_q,
        programmes=resolved_progs,
        topic=resolved_topic,
        year=resolved_year,
        semester=resolved_sem,
        is_compare=is_compare,
        is_followup=is_followup,
    )

    return TurnPlan(
        raw_question=raw_q,
        programmes=resolved_progs,
        topic=resolved_topic,
        year=resolved_year,
        semester=resolved_sem,
        semesters_for_year=resolved_sems,
        is_followup=is_followup,
        is_compare=is_compare,
        standalone_question=standalone_q,
    )


def _build_standalone_question(
    raw_question: str,
    programmes: List[str],
    topic: str,
    year: Optional[int],
    semester: Optional[int],
    is_compare: bool,
    is_followup: bool,
) -> str:
    """Construct an unambiguous, self-contained search query from the TurnPlan.

    RULE (Step 1 fix): Always keep the user's own words.  Only APPEND the
    resolved context (programme name and/or year/semester) in parentheses when
    it was inherited from history and is not already present in the raw question.
    Never replace the user's wording with a generic topic template like
    "fee structure and payment details" — that caused cache cross-talk.
    """
    # Not a follow-up and not a compare -> return the raw question unchanged.
    if not is_followup and not is_compare:
        return raw_question

    # Compare / multi-programme: keep user words, prefix with "Compare across <progs>:"
    if is_compare or len(programmes) >= 2:
        progs_str = ", ".join(PROGRAM_MAP.get(p, p) for p in programmes) or "all online programmes"
        user_words = raw_question.strip()
        return f"Compare across {progs_str}: {user_words}"

    prog_name = PROGRAM_MAP.get(programmes[0]) if programmes else ""

    # Not actually a follow-up (guard): return raw question
    if not is_followup:
        return raw_question

    # Build context suffix only from elements NOT already in the raw question
    raw_lower = raw_question.lower()
    context_parts: List[str] = []

    # Add programme if not already present in the user's words
    if prog_name:
        acronym = programmes[0].replace("online_", "").lower()  # "bca", "mba", …
        if prog_name.lower() not in raw_lower and acronym not in raw_lower:
            context_parts.append(prog_name)

    # Add year/semester if not already mentioned in the user's words
    if year:
        ord_map = {1: "1st", 2: "2nd", 3: "3rd"}
        yr_str = ord_map.get(year, str(year))
        already_year = (
            f"year {year}" in raw_lower
            or f"{yr_str} year" in raw_lower
        )
        if not already_year:
            context_parts.append(f"{yr_str} year")
    elif semester:
        if f"semester {semester}" not in raw_lower and f"sem {semester}" not in raw_lower:
            context_parts.append(f"semester {semester}")

    if context_parts:
        suffix = ", ".join(context_parts)
        return f"{raw_question.strip()} ({suffix})"

    # No new context to add: return the raw question as-is
    return raw_question
