"""Enhanced chat API route with conversation persistence.

This route wraps the existing RAG pipeline to add:
  - Conversation creation/association for authenticated users
  - Message persistence (user + assistant) in MongoDB
  - Guest mode support (no persistence, message count tracking)
  - Guest conversation migration on signup/login
  - Context-aware suggested follow-up questions

The existing ``POST /chat`` endpoint in api.py is kept unchanged for
backward compatibility.

Endpoints:
  POST /api/chat         — send a message (guest or authenticated)
  POST /api/chat/migrate — migrate guest conversation to authenticated user
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import get_optional_user, get_current_user
from app.database import get_db
from app.models import (
    create_conversation,
    create_message,
    generate_conversation_title,
    get_conversation,
    get_conversation_messages,
    update_conversation,
)
from app.utils import logger

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Context-aware suggested questions
# ---------------------------------------------------------------------------

# Patterns that indicate a greeting/casual message (not a real question)
_GREETING_RE = re.compile(
    r"^\s*(?:hi|hello|hey|good\s+(?:morning|afternoon|evening)|"
    r"thanks|thank\s+you|ok|okay|sure|great|nice|cool|bye|goodbye|"
    r"how\s+are\s+you|what'?s?\s+up|sup|yo|namaste|hii+)\s*[!?.]*\s*$",
    re.IGNORECASE,
)

# Topic detection for smarter suggestions
_TOPIC_PATTERNS = {
    "fees": re.compile(r"\b(?:fee|fees|cost|price|tuition|payment|refund|scholarship|scholarships)\b", re.IGNORECASE),
    "eligibility": re.compile(r"\b(?:eligib(?:le|ility)?|criteri[ao]|requirement|requirements|qualif(?:y|ication)|who\s+can)\b", re.IGNORECASE),
    "admission": re.compile(r"\b(?:admiss(?:ion|ions|ions?)?|apply|application|applications|enro?l(?:l?|l?ment)?|registration|registrations|intake|seat|seats)\b", re.IGNORECASE),
    "curriculum": re.compile(r"\b(?:curriculum|curricula|syllabus|subject|subjects|course|module|semester|semesters|credit|credits)\b", re.IGNORECASE),
    "exam": re.compile(r"\b(?:exam|exams|examination|examinations|assesment|assessment|test|grade|mark|result|evaluation|pass)\b", re.IGNORECASE),
    "duration": re.compile(r"\b(?:duration|year|years|how\s+long|period|time|length)\b", re.IGNORECASE),
    "program_bba": re.compile(r"\bbba\b", re.IGNORECASE),
    "program_bca": re.compile(r"\bbca\b", re.IGNORECASE),
    "program_mba": re.compile(r"\bmba\b", re.IGNORECASE),
    "program_mca": re.compile(r"\bmca\b", re.IGNORECASE),
}

# Follow-up suggestion pools organized by topic
_TOPIC_FOLLOWUPS: Dict[str, List[str]] = {
    "fees": [
        "Is there a refund policy if I withdraw?",
        "Are there any scholarships available?",
        "Can fees be paid in installments?",
        "What is the total cost for the entire program?",
    ],
    "eligibility": [
        "What documents are needed for admission?",
        "Is there an entrance exam required?",
        "What is the minimum percentage needed?",
        "Can working professionals apply?",
    ],
    "admission": [
        "What is the last date to apply?",
        "How long does the admission process take?",
        "What are the eligibility criteria?",
        "Is there an entrance test?",
    ],
    "curriculum": [
        "How many subjects are there per semester?",
        "Are there any elective options?",
        "Is there a project or dissertation required?",
        "What is the total credit requirement?",
    ],
    "exam": [
        "What is the passing criteria?",
        "Are exams conducted online or offline?",
        "How many attempts are allowed?",
        "When are the exams usually scheduled?",
    ],
    "duration": [
        "Can the program be completed early?",
        "Is there a maximum duration to finish?",
        "How many semesters are there?",
        "What is the fee structure for each year?",
    ],
    "program_bba": [
        "What is the fee structure for Online BBA?",
        "What are the eligibility criteria for BBA?",
        "What subjects are covered in the BBA curriculum?",
    ],
    "program_bca": [
        "What is the fee structure for Online BCA?",
        "What are the eligibility criteria for BCA?",
        "What programming languages are taught in BCA?",
    ],
    "program_mba": [
        "What is the fee structure for Online MBA?",
        "What specializations are available in MBA?",
        "What is the eligibility for Online MBA?",
    ],
    "program_mca": [
        "What is the fee structure for Online MCA?",
        "What is the eligibility for Online MCA?",
        "What is the curriculum for MCA?",
    ],
}

_GENERAL_FOLLOWUPS = [
    "What online programs are available at CHARUSAT?",
    "How does the admission process work?",
    "How many semesters are there in each online programme?",
    "What is the fee structure for each online programme?",
]

# Follow-up templates tied to an attribute, formatted with the programme the
# user actually mentioned ("How many semesters are there in Online BBA?").
_ATTR_FOLLOWUPS_WITH_PROG: Dict[str, List[str]] = {
    "fees": [
        "What is the fee structure for {prog}?",
        "Can the {prog} fee be paid in installments?",
        "Is there a refund policy if I withdraw from {prog}?",
        "What is the total cost for {prog}?",
    ],
    "eligibility": [
        "What is the eligibility for {prog}?",
        "What documents are required for {prog} admission?",
        "Can working professionals join {prog}?",
    ],
    "admission": [
        "How do I apply for {prog}?",
        "What is the admission process for {prog}?",
        "When is the last date to apply for {prog}?",
    ],
    "curriculum": [
        "How many semesters are there in {prog}?",
        "What subjects are covered in the {prog} curriculum?",
        "How many credits are required to complete {prog}?",
        "Does {prog} include any elective or specialisation options?",
    ],
    "exam": [
        "How are {prog} examinations conducted?",
        "What is the passing criteria for {prog} exams?",
        "When are {prog} exams usually scheduled?",
    ],
    "duration": [
        "How long does {prog} take to complete?",
        "Can {prog} be completed early?",
        "What is the maximum duration allowed for {prog}?",
    ],
    "credits": [
        "How many total credits are required for {prog}?",
        "How many credits are offered per semester in {prog}?",
    ],
    "specializations": [
        "What specializations are available in {prog}?",
        "Can I choose electives in {prog}?",
    ],
}

# Same attributes, but worded across every programme when the user did not
# name one ("How many semesters are there in each online programme?").
_ATTR_FOLLOWUPS_ALL: Dict[str, List[str]] = {
    "fees": [
        "How do fees compare across Online BBA, BCA, MBA and MCA?",
        "Is there a refund policy if I withdraw from a programme?",
        "Can fees be paid in installments?",
        "What is the total fee for each online programme?",
    ],
    "eligibility": [
        "What is the eligibility for each online programme?",
        "What documents are required for admission?",
        "Can working professionals apply?",
    ],
    "admission": [
        "How does the admission process work?",
        "When is the last date to apply?",
        "Is there an entrance exam for admission?",
    ],
    "curriculum": [
        "How many semesters are there in each online programme?",
        "How do the curricula of the four online programmes differ?",
        "How many total credits are required across the programmes?",
        "Which programme has the most semesters?",
    ],
    "exam": [
        "How are examinations conducted for the online programmes?",
        "What is the passing criteria?",
        "When are exams usually held?",
    ],
    "duration": [
        "How long does each online programme take to complete?",
        "Which programme can be completed in the shortest time?",
        "What is the maximum duration allowed to finish a programme?",
    ],
    "credits": [
        "How many total credits are required for each online programme?",
        "How many credits are offered per semester?",
    ],
    "specializations": [
        "What specializations are available in the online programmes?",
        "Can I choose electives in any of the programmes?",
    ],
}

_PROGRAM_DISPLAY_TUPLE = [
    (r"\b(?:online\s+)?b\.?\s*b\.?\s*a\b", "Online BBA"),
    (r"\b(?:online\s+)?b\.?\s*c\.?\s*a\b", "Online BCA"),
    (r"\b(?:online\s+)?m\.?\s*b\.?\s*a\b", "Online MBA"),
    (r"\b(?:online\s+)?m\.?\s*c\.?\s*a\b", "Online MCA"),
]


def _detect_program_display_names(text: str) -> List[str]:
    """Return display names of programmes explicitly named in the text."""
    query = " " + text.lower() + " "
    found = []
    for pattern, display in _PROGRAM_DISPLAY_TUPLE:
        if re.search(pattern, query):
            found.append(display)
    return found


# Warm, conversational replies for pure greetings / small talk.
# These are short on purpose — they should feel chatty, not document-based.
_WARM_REPLIES = [
    "Hi there! 👋 I'm the CHARUSAT assistant. Ask me anything about our online degree programmes — "
    "fees, eligibility, curriculum, admissions or exams.",
    "Hello! What can I help you with? You could ask about fees, eligibility, programmes, or how admission works.",
    "Hey! I can help you with questions about CHARUSAT's online programmes. What would you like to know?",
]


def _is_pure_smalltalk(question: str) -> bool:
    """True when the message is only a greeting/pleasantry, not a real question."""
    q = question.strip()
    if len(q) > 60:
        return False
    if "?" in q and _GREETING_RE.match(q.split("?")[0].strip()):
        # "How are you?" / "sup?" style — still small talk unless it's a real query
        if re.search(r"\b(what|fee|cost|eligib|admiss|apply|curriculum|exam|program|bba|bca|mba|mca)\b", q, re.IGNORECASE):
            return False
        return True
    if _GREETING_RE.match(q):
        return True

    # Normalised exact-phrase check covers multi-word pleasantries
    # ("thank you so much", "good to know", "hi there", "ok great", ...).
    norm = re.sub(r"[^a-z0-9\s'-]", "", q.lower()).strip()
    norm = re.sub(r"\s+", " ", norm)

    smalltalk_phrases = {
        "hi", "hello", "hey", "heyy", "yo", "sup", "bye", "goodbye", "namaste",
        "ok", "okay", "sure", "great", "nice", "cool", "thanks", "thank you",
        "thank you so much", "thank you very much", "thanks a lot", "thx",
        "good to know", "got it", "understood", "perfect", "awesome", "fine",
        "how are you", "how are you doing", "whats up", "good morning",
        "good afternoon", "good evening", "good day", "hi there", "hello there",
        "hey there", "hi charusat", "hello charusat", "hey charusat",
        "ok great", "ok thanks", "great thanks", "cool thanks", "thanks great",
        "perfect thanks", "alright", "ok got it", "sounds good",
    }
    if norm in smalltalk_phrases:
        return True

    # Strip a leading acknowledgement ("ok", "great", ...) and re-check the rest.
    remainder = re.sub(r"^(?:ok|okay|sure|great|nice|cool|perfect|awesome|thanks|thank you|alright|good)\s+", "", norm)
    if remainder and remainder in smalltalk_phrases:
        return True

    # If it contains a real question or a topic keyword, it's a real query.
    if any(w in norm for w in (
        "what", "how", "tell", "explain", "which", "can you", "who",
        "fee", "cost", "eligib", "admiss", "apply", "curriculum",
        "exam", "program", "bba", "bca", "mba", "mca", "duration", "semester",
    )):
        return False

    return False


def _generate_suggestions(
    question: str,
    answer: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> List[str]:
    """Generate 3 context-aware follow-up suggestions.

    Suggestions echo the user's own prompt: when they name a programme
    (e.g. "BBA semesters") the follow-ups are built for that programme;
    when they ask generically ("How many semesters are there?") the
    follow-ups cover all programmes. Already-asked questions are never
    re-suggested.
    """
    if _is_pure_smalltalk(question):
        return []

    q_lower = question.strip().lower()

    # Questions the user has actually asked in this conversation
    asked = {q_lower.strip("? ").strip()}
    for msg in history or []:
        role = msg.get("role") if isinstance(msg, dict) else "user"
        if role == "assistant":
            continue
        content = (msg.get("content") or msg.get("question") or "") if isinstance(msg, dict) else str(msg)
        content = content.strip().lower()
        if content and len(content) < 200:
            asked.add(content.strip("? ").strip())

    def _already_asked(followup: str) -> bool:
        f = followup.lower().strip("? ").strip()
        if f in asked:
            return True
        f_tokens = f.split()
        if len(f_tokens) < 4:
            return False
        return any(a.split()[:4] == f_tokens[:4] for a in asked)

    # Which programme did the user name? (history establishes context too)
    programs = _detect_program_display_names(question)
    if not programs:
        for msg in (history or [])[::-1][:6]:
            content = (msg.get("content") or msg.get("question") or "") if isinstance(msg, dict) else str(msg)
            programs = programs or _detect_program_display_names(content)
            if programs:
                break

    # Topics: user's own words first, then the answer, then history.
    detected: List[str] = []
    for topic, pattern in _TOPIC_PATTERNS.items():
        if pattern.search(question):
            detected.append(topic)
        elif pattern.search(answer[:300]):
            detected.append(topic)
    for msg in (history or [])[::-1][:4]:
        content = (msg.get("content") or msg.get("question") or "") if isinstance(msg, dict) else str(msg)
        if not content:
            continue
        for topic, pattern in _TOPIC_PATTERNS.items():
            if pattern.search(content) and topic not in detected:
                detected.append(topic)

    if not detected and not programs:
        return [f for f in _GENERAL_FOLLOWUPS if not _already_asked(f)][:3] or _GENERAL_FOLLOWUPS[:3]

    # One programme named -> programme-flavoured follow-ups; otherwise
    # cross-programme suggestions that match a generic question.
    if len(programs) == 1:
        prog = programs[0]
        templates = _ATTR_FOLLOWUPS_WITH_PROG
    else:
        prog = None
        templates = _ATTR_FOLLOWUPS_ALL
        detected = [t for t in detected if not t.startswith("program_")]

    candidates: List[str] = []
    seen: set = set()

    def _push(followup: str) -> None:
        if followup in seen or _already_asked(followup):
            return
        seen.add(followup)
        candidates.append(followup)

    # Attribute templates for the topics the user touched (most relevant first)
    attr_order = ["fees", "eligibility", "admission", "curriculum", "exam",
                  "duration", "credits", "specializations"]
    used = set()
    for attr in attr_order:
        if attr not in detected:
            continue
        used.add(attr)
        pool = templates.get(attr, [])
        if prog:
            pool = [t.format(prog=prog) for t in pool]
        for f in pool:
            _push(f)

    # Programme-follow-ups when a programme was named but no attribute matched
    for topic in detected:
        if topic.startswith("program_"):
            for f in _TOPIC_FOLLOWUPS.get(topic, []):
                _push(f)

    # Fill remaining slots from the programme's other attributes for variety
    if prog and len(candidates) < 3:
        for attr in attr_order:
            if attr in used or attr not in templates:
                continue
            for f in templates.get(attr, [])[:1]:
                f = f.format(prog=prog)
                _push(f)
            if len(candidates) >= 3:
                break

    if not candidates:
        return [f for f in _GENERAL_FOLLOWUPS if not _already_asked(f)][:3] or _GENERAL_FOLLOWUPS[:3]

    return candidates[:3]


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatMessageRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None


class ChatMessageResponse(BaseModel):
    answer: str
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    sources: List[Dict[str, Any]] = []
    suggested_questions: List[str] = []


class MigrateConversationRequest(BaseModel):
    """Migrate a guest conversation to the authenticated user's account."""
    messages: List[Dict[str, Any]] = Field(
        ...,
        description="List of {role, content} message objects from the guest session",
    )
    title: Optional[str] = None


class MigrateConversationResponse(BaseModel):
    conversation_id: str
    message_count: int


# ---------------------------------------------------------------------------
# RAG pipeline access (lazy import to avoid circular dependencies)
# ---------------------------------------------------------------------------

def _get_rag_chain():
    """Get the RAG chain from the main api module.

    The RAG pipeline is initialized in api.py. We access it through the
    module-level variables set during startup.
    """
    import sys
    api_module = sys.modules.get("api")
    if api_module is None:
        return None, False

    rag_ready = getattr(api_module, "_rag_ready", False)
    rag_chain = getattr(api_module, "rag_chain", None)
    return rag_chain, rag_ready


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=ChatMessageResponse)
async def chat_message(
    request: ChatMessageRequest,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
):
    """Send a chat message.

    For authenticated users: creates/uses a conversation, persists messages.
    For guests: just calls RAG pipeline, no persistence.
    Greetings / small talk are answered conversationally without hitting RAG.
    """
    import random

    conversation_id = request.conversation_id

    # ------------------------------------------------------------------
    # Persist a guest/auth turn against a conversation (helper)
    # ------------------------------------------------------------------
    def _persist_turn(assistant_answer: str, assmt_suggestions: List[str]):
        """Save user + assistant messages; returns the assistant message."""
        nonlocal conversation_id
        db = get_db()
        if db is None or user is None:
            return None, conversation_id

        if not conversation_id:
            title = generate_conversation_title(request.question)
            conv = create_conversation(db, user_id=user["id"], title=title)
            conversation_id = conv["id"]

        create_message(
            db,
            conversation_id=conversation_id,
            role="user",
            content=request.question,
        )
        assistant_msg = create_message(
            db,
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_answer,
            sources=[],
            suggested_questions=assmt_suggestions,
        )
        return assistant_msg, conversation_id

    # ------------------------------------------------------------------
    # Greeting / small talk — natural conversational reply, no RAG needed.
    # No suggestion chips here: after a greeting, quiet is more natural
    # than pushing programme questions unprompted.
    # ------------------------------------------------------------------
    if _is_pure_smalltalk(request.question):
        answer_text = random.choice(_WARM_REPLIES)
        suggestions: List[str] = []
        assistant_msg, conv_id = _persist_turn(answer_text, suggestions)
        return ChatMessageResponse(
            answer=answer_text,
            conversation_id=conv_id,
            message_id=assistant_msg["id"] if assistant_msg else None,
            sources=[],
            suggested_questions=suggestions,
        )

    rag_chain, rag_ready = _get_rag_chain()

    if not rag_ready or rag_chain is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chatbot RAG pipeline is not available.",
        )

    # ------------------------------------------------------------------
    # Conversation context for smarter suggestions (dedup already-asked)
    # ------------------------------------------------------------------
    history: Optional[List[Dict[str, Any]]] = None
    if request.history:
        history = request.history
    elif user is not None and conversation_id:
        db = get_db()
        if db is not None:
            recent = get_conversation_messages(db, conversation_id)
            if recent:
                history = recent[-8:]

    # Call the existing RAG pipeline
    try:
        answer_text, retrieved = rag_chain.answer(request.question)
    except Exception as exc:
        logger.error("RAG chain failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate answer",
        ) from exc

    # Extract source information from retrieved chunks.
    # Only official PDF sources are reported — .md website pages are not
    # shown as citations so the UI stays clean and trustworthy.
    sources = []
    if retrieved:
        for doc, score in retrieved:
            meta = doc.metadata
            source_path = str(meta.get("source", ""))
            if not source_path.lower().endswith(".pdf"):
                continue
            sources.append({
                "source": source_path,
                "page": meta.get("page"),
                "program": meta.get("program_name"),
                "score": round(score, 3),
            })

    # Generate context-aware follow-up suggestions
    suggestions = _generate_suggestions(request.question, answer_text, history)

    # For guests, return without persistence
    if user is None:
        return ChatMessageResponse(
            answer=answer_text,
            sources=sources,
            suggested_questions=suggestions,
        )

    # For authenticated users, persist to MongoDB
    db = get_db()
    if db is None:
        # MongoDB unavailable — return answer without persistence
        return ChatMessageResponse(
            answer=answer_text,
            sources=sources,
            suggested_questions=suggestions,
        )

    # Create new conversation if needed
    if not conversation_id:
        title = generate_conversation_title(request.question)
        conv = create_conversation(db, user_id=user["id"], title=title)
        conversation_id = conv["id"]
    else:
        # Verify conversation belongs to user
        conv = get_conversation(db, conversation_id, user["id"])
        if not conv:
            # Create a new one instead of failing
            title = generate_conversation_title(request.question)
            conv = create_conversation(db, user_id=user["id"], title=title)
            conversation_id = conv["id"]

    # Save user message
    create_message(
        db,
        conversation_id=conversation_id,
        role="user",
        content=request.question,
    )

    # Save assistant response
    assistant_msg = create_message(
        db,
        conversation_id=conversation_id,
        role="assistant",
        content=answer_text,
        sources=sources,
        suggested_questions=suggestions,
    )

    return ChatMessageResponse(
        answer=answer_text,
        conversation_id=conversation_id,
        message_id=assistant_msg["id"],
        sources=sources,
        suggested_questions=suggestions,
    )


@router.post("/migrate", response_model=MigrateConversationResponse)
async def migrate_guest_conversation(
    request: MigrateConversationRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Migrate a guest conversation to the authenticated user's account.

    Called after a guest user signs up or logs in. The guest's local
    messages are saved as a new conversation owned by the user.
    """
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    if not request.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages to migrate",
        )

    # Generate title from first user message
    first_user_msg = next(
        (m for m in request.messages if m.get("role") == "user"),
        None,
    )
    title = request.title or (
        generate_conversation_title(first_user_msg["content"])
        if first_user_msg and first_user_msg.get("content")
        else "Migrated Chat"
    )

    # Create conversation
    conv = create_conversation(db, user_id=user["id"], title=title)

    # Save all messages
    count = 0
    for msg in request.messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if not content:
            continue
        create_message(
            db,
            conversation_id=conv["id"],
            role=role,
            content=content,
            sources=msg.get("sources", []),
        )
        count += 1

    logger.info(
        "Migrated guest conversation: user_id=%s, conversation_id=%s, messages=%d",
        user["id"], conv["id"], count,
    )

    return MigrateConversationResponse(
        conversation_id=conv["id"],
        message_count=count,
    )
