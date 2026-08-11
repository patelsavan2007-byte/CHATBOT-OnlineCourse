from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
VECTOR_DB_DIR = BASE_DIR / "vector_db"
PDF_DIR = KNOWLEDGE_BASE_DIR / "pdfs"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
FALLBACK_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
PDF_CHUNK_SIZE = 800
PDF_TABLE_CHUNK_SIZE = 1200
SCRAPE_START_URL = "https://charusat.online/"
SCRAPE_MAX_PAGES = 250
CRAWL_DELAY = 0.5

load_dotenv(BASE_DIR / ".env")


def get_api_key() -> Optional[str]:
    """Return the configured GOOGLE_API_KEY from .env if present."""
    key = os.getenv("GOOGLE_API_KEY")
    if key and key.strip() and not key.startswith("#"):
        return key.strip()
    return None


def get_groq_api_key() -> Optional[str]:
    """Return the configured GROQ_API_KEY from .env if present."""
    key = os.getenv("GROQ_API_KEY") or os.getenv("groq_API_KEY")
    if key and key.strip() and not key.startswith("#"):
        return key.strip()
    return None


def ensure_directories() -> None:
    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# Retrieval / Ranking
# ===========================================================================

# Number of chunks sent to the LLM for answer generation.
TOP_K = 5

# Raw candidates retrieved from the vector store before re-ranking,
# deduplication and final top-K selection. A larger pool lets the ranking
# stage prefer the best non-duplicate, diverse chunks instead of simply
# taking the first K neighbours.
CANDIDATE_POOL_SIZE = 20

# Hard ceiling applied to every final score. Prevents boosting from
# flattening many chunks onto the same maximum value.
SCORE_CAP = 0.95

# ---------------------------------------------------------------------------
# Bounded keyword boosting.
#
# Semantic similarity remains the primary signal. Keyword and value-proximity
# matches provide a small, capped bonus so they can refine ordering without
# letting weakly-relevant chunks leapfrog clearly-relevant ones.
# ---------------------------------------------------------------------------
KEYWORD_BOOST_FACTOR = 0.02       # bonus per matched attribute keyword
KEYWORD_BOOST_MAX = 0.06          # absolute cap on the keyword contribution
VALUE_PROXIMITY_BONUS = 0.015     # bonus per keyword-with-nearby-value hit
VALUE_PROXIMITY_MAX = 0.03        # absolute cap on the value-proximity contribution

# Attribute keywords used for controlled keyword scoring.
ATTRIBUTE_KEYWORDS: set = {
    "total programme fee", "annual fee", "semester fee", "examination fee",
    "tuition fee", "course fee", "caution deposit", "fee structure",
    "refund policy", "total fee", "fee", "payment", "payment mode", "payment modes",
    "mode of payment", "pay fee", "pay fees", "installment",
    "programme duration", "duration",
    "total credits", "semester credits", "number of credits", "credits",
    "eligibility", "eligible",
    "admission process", "admission requirements", "admission",
    "examination", "exam",
    "syllabus", "curriculum", "subjects",
    "specialization", "specialisation", "elective", "streams",
    "refund", "cancellation", "withdrawal",
    "policy", "rules", "regulation",
}

# ---------------------------------------------------------------------------
# Source authority
# ---------------------------------------------------------------------------
SOURCE_AUTHORITY_ENABLED = True
# Scales a source priority (0..1) into a bounded score bonus.
SOURCE_AUTHORITY_WEIGHT = 0.05
# Absolute cap on the source-authority contribution to a chunk score.
SOURCE_AUTHORITY_MAX_BONUS = 0.06
# Extra priority (added to a source priority) when the chunk's programme
# matches the programme detected in the user query.
PROGRAMME_MATCH_PRIORITY_BONUS = 0.2

# Source priority tiers. The first matching pattern wins for the highest
# priority. Patterns are matched against "<source> <document_type>".
# Priority is a float in [0, 1].
SOURCE_AUTHORITY_TIERS: List[Tuple[str, float]] = [
    (r"pdfs/PPR_Online", 1.00),               # official programme PDFs
    (r"pdfs/Fees Refund Policy", 0.95),       # official policy PDF
    (r"programs/online_", 0.90),              # official website programme pages
    (r"-admission-data", 0.85),               # admission procedure pages
    (r"mandatory-disclosures", 0.80),         # statutory disclosures
    (r"terms-conditions", 0.75),              # general terms & conditions
    (r"privacy-policy", 0.75),                # privacy policy
    (r"ciqa", 0.60),                          # quality assurance pages
    (r"contact", 0.55),                       # contact page
    (r"home", 0.45),                          # homepage overview
    (r"feedback", 0.40),                      # feedback page
]

# Website documents (programme-scoped queries) whose content carries general
# university policy information and should therefore remain retrievable
# alongside the official programme documents. Matched against the source path.
GENERAL_POLICY_SOURCE_PATTERNS: List[str] = [
    "terms-conditions",
    "privacy-policy",
    "mandatory-disclosures",
    "-admission-data",
    "ciqa",
]

# ---------------------------------------------------------------------------
# Deduplication / diversity
# ---------------------------------------------------------------------------
DEDUP_ENABLED = True
# Token-set Jaccard similarity above which two chunks are treated as
# near-duplicates (the higher-scoring one is kept).
DEDUP_SIMILARITY_THRESHOLD = 0.82
# Keep at most this many chunks per (source, page) in the final selection so
# that one page cannot crowd out genuinely different sections.
DEDUP_MAX_PER_SOURCE_PAGE = 2

# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------
CONFLICT_ENABLED = True
# How far (in characters) to look around an attribute keyword for a value.
CLAIM_VALUE_WINDOW = 160
# Minimum number of distinct source values required before a conflict is
# reported for a single-valued attribute.
CONFLICT_MIN_VALUE_COUNT = 2

# Attribute taxonomy used for claim extraction, conflict detection and the
# deterministic local fallback. Each attribute maps a set of phrases to a
# semantics:
#   "single" : one numeric value per source -> conflict-eligible
#   "range"  : a numeric range (e.g. "2 - 4 years") -> never conflict-eligible
#   "set"    : several acceptable values (e.g. per-semester credits) -> never
#   "text"   : non-numeric descriptive value (e.g. eligibility) -> never
ATTRIBUTE_TAXONOMY: Dict[str, Dict[str, object]] = {
    "total_fee": {
        "label": "Total programme fee",
        "semantics": "single",
        "keywords": [
            "total fee (for the entire programme)", "total programme fee",
            "total course fee", "overall programme fee", "total fee",
            "fee for the entire programme", "entire programme fee",
        ],
    },
    "annual_fee": {
        "label": "Year-wise fee",
        "semantics": "single",
        "keywords": [
            "fee for 1st year", "fee for 2nd year", "fee for first year",
            "fee for second year", "first year fee", "second year fee",
            "annual fee", "yearly fee", "per year fee", "year-wise fee",
            "year wise fee", "fee for each year",
        ],
    },
    "semester_fee": {
        "label": "Semester fee",
        "semantics": "single",
        "keywords": [
            "semester fee", "per semester fee", "fee per semester",
            "semester-wise fee", "semester wise fee",
        ],
    },
    "examination_fee": {
        "label": "Examination fee",
        "semantics": "single",
        "keywords": [
            "examination fee", "examination fees", "exam fee",
            "examination charge",
        ],
    },
    "caution_deposit": {
        "label": "Caution deposit",
        "semantics": "single",
        "keywords": ["caution deposit", "security deposit", "refundable deposit"],
    },
    "total_credits": {
        "label": "Total credits",
        "semantics": "single",
        "keywords": [
            "total number of credits", "total no of credits", "total credits",
            "total credit",
        ],
    },
    "per_semester_credits": {
        "label": "Credits per semester",
        "semantics": "set",
        "keywords": [
            "credits in each semester", "credits per semester",
            "semester-wise distribution of credits",
            "semester wise distribution of credits", "semester credits",
            "number of credits",
        ],
    },
    "duration": {
        "label": "Duration",
        "semantics": "range",
        "keywords": [
            "duration of the programme", "programme duration", "duration",
        ],
    },
    "eligibility": {
        "label": "Eligibility",
        "semantics": "text",
        "keywords": ["eligibility", "eligible"],
    },
    "specializations": {
        "label": "Specializations",
        "semantics": "set",
        "keywords": [
            "specialization", "specialisation", "functional area",
            "stream of management", "streams",
        ],
    },
}

# ---------------------------------------------------------------------------
# Context construction
# ---------------------------------------------------------------------------
# Minimum relevance score threshold for candidate chunks to be included in top-K.
MIN_RELEVANCE_SCORE = 0.52

# Minimum score threshold for a source chunk to be displayed in the response sources list.
MIN_SOURCE_SCORE = 0.60

# Maximum characters of a single chunk's content included in the LLM context.
CONTEXT_CHUNK_MAX_CHARS = 800
# Maximum total context size (headers + content + separators) sent to the LLM.
CONTEXT_TOTAL_MAX_CHARS = 4200

# ---------------------------------------------------------------------------
# LLM / API
# ---------------------------------------------------------------------------
LLM_MAX_RETRIES = 2          # maximum number of attempts for a generation call
LLM_RETRY_DELAY = 1.0        # initial delay (seconds) before a retry
LLM_BACKOFF_FACTOR = 1.5     # multiplier applied to the delay between retries
LLM_TIMEOUT = 15             # per-attempt timeout in seconds (fast fail)
LLM_TEMPERATURE = 0.2
LLM_COOLDOWN_SECONDS = 300   # circuit-breaker: skip Gemini for 5 mins after a full failure sweep


# Preferred Gemini models in priority order (exact names from the API).
PREFERRED_MODELS: List[str] = [
    "models/gemini-3.6-flash",
    "models/gemini-3.5-flash",
    "models/gemini-2.5-flash",
    "models/gemini-2.5-pro",
]

# Groq fallback tier settings.
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_TIMEOUT = 10.0  # seconds

# ---------------------------------------------------------------------------
# Chat History / Session
# ---------------------------------------------------------------------------
# Maximum number of messages (user + assistant combined) retained per session
# when sending conversation history to the LLM.  Only the most recent
# messages are kept.  Increase this for longer contextual memory at the cost
# of larger prompts; decrease it to save tokens.
CHAT_HISTORY_MAX_MESSAGES = 10
