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
        r"\b(?:refund|money\s+back|cancell(?:ation|ed|ing)?|withdraw(?:al)?)\b", re.I
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

_COMPARE_RE = re.compile(
    r"\b(?:compare|comparison|difference|differ|vs|versus|all\s+programme?s?|each\s+programme?s?|across\s+programme?s?)\b",
    re.I,
)

_FOLLOWUP_SHORT_PROG_RE = re.compile(
    r"^\s*(?:and\s+)?(?:for|what\s+about|how\s+about)\s+(?:the\s+)?(?:online\s+)?(bca|bba|mba|mca)\s*[!?.]*\s*$",
    re.I,
)

_YEAR_RE = re.compile(
    r"\b(?:year\s*([1-3])|([1-3])(?:st|nd|rd)?\s*year|(first|second|third)\s*year)\b", re.I
)

_SEM_RE = re.compile(
    r"\b(?:sem(?:ester)?\s*([1-6])|([1-6])(?:st|nd|rd|th)?\s*sem(?:ester)?)\b", re.I
)

_WORD_TO_NUM = {"first": 1, "second": 2, "third": 3}


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
    """Detect topic category from text."""
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
            # "for mba" / "and for MCA?" -> switches programme, retains topic & year
            is_followup = True
            if prev_plan.topic != "general":
                resolved_topic = prev_plan.topic
            if resolved_year is None:
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
    """Construct an unambiguous, self-contained search query from the TurnPlan."""
    # If not a follow-up and already names the programme or is a general query, return cleaned raw
    if not is_followup and not is_compare:
        return raw_question

    if is_compare or len(programmes) >= 2:
        progs_str = ", ".join(PROGRAM_MAP.get(p, p) for p in programmes) or "Online BBA, BCA, MBA and MCA"
        if topic == "fees":
            return f"Compare fees across {progs_str}"
        elif topic == "subjects":
            return f"Compare curriculum and subjects across {progs_str}"
        elif topic == "duration":
            return f"Compare duration and semesters across {progs_str}"
        elif topic == "eligibility":
            return f"Compare eligibility criteria across {progs_str}"
        return f"Comparison across {progs_str}: {raw_question}"

    prog_name = PROGRAM_MAP.get(programmes[0]) if programmes else ""

    if not is_followup:
        return raw_question

    # Rebuild from plan elements
    parts = []
    if prog_name:
        parts.append(prog_name)

    if year:
        parts.append(f"Year {year}")
    elif semester:
        parts.append(f"Semester {semester}")

    if topic == "fees":
        parts.append("fee structure and payment details")
    elif topic == "subjects":
        parts.append("syllabus and course subjects")
    elif topic == "specializations":
        parts.append("specializations and elective choices")
    elif topic == "eligibility":
        parts.append("eligibility criteria and qualification requirements")
    elif topic == "admission":
        parts.append("admission procedure and required documents")
    elif topic == "duration":
        parts.append("duration, semesters, and credits")
    elif topic == "grading":
        parts.append("grading system and examination rules")
    elif topic == "refund":
        parts.append("fees refund policy and cancellation")
    elif topic == "lms":
        parts.append("LMS portal login and password support")
    elif topic == "career":
        parts.append("placement opportunities and recruiter companies")
    elif topic == "contact":
        parts.append("contact details and helpline numbers")
    else:
        parts.append(raw_question)

    return " ".join(parts).strip()
