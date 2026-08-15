"""Claim-level conflict detection for the RAG pipeline.

The vector store frequently contains several sources that discuss the same
topic from different angles. Merely comparing arbitrary numbers or phrases
across chunks produces false "inconsistencies" (e.g. an annual fee versus a
total fee, or a per-semester credit count versus a total credit count).

This module detects conflicts at the level of a *claim*: a concrete
(attribute, aspect, value, source, page) tuple extracted from evidence text.

Rules
-----
* same attribute + same aspect + different values  -> conflict
* same attribute + different aspects               -> supporting (not a conflict)
* different attributes                             -> supporting (not a conflict)
* same value repeated across chunks                -> supporting (not a conflict)
* numeric ranges (e.g. "2 - 4 years")              -> never conflict-eligible
* multi-valued attributes (per-semester credits)   -> never conflict-eligible

Attribute and aspect vocabulary are configurable in config.ATTRIBUTE_TAXONOMY
so the logic remains document- and question-independent.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app import config
from app.utils import logger

Claim = Dict[str, Any]
Conflict = Dict[str, Any]

# ---------------------------------------------------------------------------
# Aspect vocabulary: columns/labels that qualify a value within an attribute
# (e.g. "total" vs "per year" vs "per semester" for a fee).
# ---------------------------------------------------------------------------
_ASPECT_KEYWORDS: List[Tuple[str, List[str]]] = [
    ("total", ["total", "entire programme", "whole programme"]),
    ("annual", [
        "1st year", "2nd year", "3rd year", "4th year",
        "first year", "second year", "third year", "fourth year",
        "per year", "per annum", "each year", "yearly", "annual",
    ]),
    ("per_semester", ["per semester", "semester-wise", "semester wise", "in each semester"]),
    ("per_month", ["per month", "monthly"]),
]

# Family grouping used by the fallback when the question is generic
# (e.g. a bare "fee" question focuses the whole fee family).
ATTRIBUTE_FAMILIES: Dict[str, List[str]] = {
    "fee": ["total_fee", "annual_fee", "semester_fee", "examination_fee", "caution_deposit"],
    "credit": ["total_credits", "per_semester_credits"],
    "duration": ["duration"],
    "eligib": ["eligibility"],
    "speciali": ["specializations"],
}


# ---------------------------------------------------------------------------
# Number helpers
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(
    r"(?:Rs\.?\s*|₹\s*|INR\s*|\$\s*)?"
    r"\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|"
    r"\d+(?:\.\d+)?"
)


def extract_numbers(text: str) -> List[float]:
    """Extract all plain/international/Indian-format numbers from text."""
    numbers: List[float] = []
    for match in _NUMBER_RE.findall(text or ""):
        clean = re.sub(r"[^\d.]", "", match).strip(".")
        if clean and clean != ".":
            try:
                numbers.append(float(clean))
            except ValueError:
                continue
    return numbers


def normalize_number(text: str) -> Optional[float]:
    """Return the first number found in *text* (or None)."""
    numbers = extract_numbers(text)
    return numbers[0] if numbers else None


def _first_number(cell: str) -> Optional[float]:
    return normalize_number(cell)


# ---------------------------------------------------------------------------
# Attribute / aspect matching
# ---------------------------------------------------------------------------

def match_attribute(text: str) -> Optional[str]:
    """Return the attribute key whose keyword matches *text* (longest match)."""
    lower = (text or "").lower()
    best_key: Optional[str] = None
    best_len = -1
    for key, spec in config.ATTRIBUTE_TAXONOMY.items():
        for kw in spec.get("keywords", []):
            if kw in lower and len(kw) > best_len:
                best_key, best_len = key, len(kw)
    return best_key


def match_aspect(text: str) -> str:
    """Return the aspect qualifier (e.g. 'total', 'annual', 'per_semester')."""
    lower = (text or "").lower()
    for aspect, words in _ASPECT_KEYWORDS:
        for word in words:
            if word in lower:
                return aspect
    return ""


def focus_attributes(question: str) -> List[str]:
    """Return attribute keys the question is asking about.

    Specific taxonomy matches take priority; otherwise the attribute family
    hinted by a generic word (fee, credit, duration, ...) is returned.
    """
    specific = []
    for key in config.ATTRIBUTE_TAXONOMY:
        spec = config.ATTRIBUTE_TAXONOMY[key]
        for kw in spec.get("keywords", []):
            if kw in question.lower():
                specific.append(key)
                break
    if specific:
        return specific

    lower = question.lower()
    for word, keys in ATTRIBUTE_FAMILIES.items():
        if word in lower:
            return keys
    return []


# ---------------------------------------------------------------------------
# Claim extraction
# ---------------------------------------------------------------------------

def _make_claim(
    attribute: str,
    aspect: str,
    value_text: str,
    number: Optional[float],
    numbers: List[float],
    source: str,
    page: Any,
    context: str,
    programme: str,
) -> Claim:
    spec = config.ATTRIBUTE_TAXONOMY.get(attribute, {})
    return {
        "attribute": attribute,
        "aspect": aspect,
        "label": spec.get("label", attribute),
        "semantics": spec.get("semantics", "text"),
        "value_text": value_text,
        "number": number,
        "numbers": numbers,
        "source": source,
        "page": page,
        "context": context,
        "programme": programme,
    }


def _extract_text_claims(content: str, metadata: Dict[str, Any]) -> List[Claim]:
    """Extract claims from plain (non-table) text lines."""
    claims: List[Claim] = []
    lines = content.splitlines()
    source = str(metadata.get("source", "unknown"))
    page = metadata.get("page")
    programme = str(metadata.get("program_name", "") or "")

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        attribute = match_attribute(stripped)
        if not attribute:
            continue
        spec = config.ATTRIBUTE_TAXONOMY[attribute]
        semantics = spec.get("semantics", "text")

        if semantics == "text":
            value = _value_after_keyword(stripped, spec["keywords"], lines, i)
            if value:
                claims.append(_make_claim(
                    attribute, match_aspect(stripped), value, None, [],
                    source, page, stripped, programme,
                ))
            continue

        numbers = _numbers_in_window(lines, i)
        if not numbers:
            continue
        value_text = _trimmed(stripped)
        if not re.search(r"\d", value_text):
            value_text = f"{value_text} {_numbers_to_text(numbers)}"
        claims.append(_make_claim(
            attribute, match_aspect(stripped), value_text, numbers[0], numbers,
            source, page, stripped, programme,
        ))
    return claims


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def _numbers_to_text(numbers: List[float]) -> str:
    return " ".join(_format_number(number) for number in numbers[:6])


def _value_after_keyword(line: str, keywords: List[str], lines: List[str], i: int) -> Optional[str]:
    """Extract the descriptive value after a ``keyword : value`` separator."""
    for kw in sorted(keywords, key=len, reverse=True):
        match = re.search(rf"{re.escape(kw)}\s*[:=-]\s*(.+)", line, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value and value not in {":", "-"}:
                return value[: config.CLAIM_VALUE_WINDOW]
    # value may sit on the following line
    for j in range(i + 1, min(i + 3, len(lines))):
        nxt = lines[j].strip()
        if nxt and not nxt.startswith(("•", "-", "|", "#", "o ", "O ")):
            return nxt[: config.CLAIM_VALUE_WINDOW]
    return None


def _numbers_in_window(lines: List[str], i: int) -> List[float]:
    """Collect numbers from the current line and the next line with digits."""
    window = [lines[i]]
    for j in range(i + 1, min(i + 3, len(lines))):
        window.append(lines[j])
        if re.search(r"\d", lines[j]):
            break
        if len("\n".join(window)) >= config.CLAIM_VALUE_WINDOW:
            break
    return extract_numbers("\n".join(window))


def _parse_markdown_table(content: str) -> Optional[Tuple[List[str], List[List[str]]]]:
    """Parse a markdown table into (headers, data_rows). None if not a table."""
    lines = [line for line in content.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return None

    def cells(line: str) -> List[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    rows: List[List[str]] = []
    for line in lines:
        row = cells(line)
        if all(re.fullmatch(r":?-{2,}:?", cell.replace(" ", "")) for cell in row):
            continue
        rows.append(row)
    if not rows:
        return None
    headers = rows[0]
    data = rows[1:]
    # Pad short rows so column indexing is safe.
    normalized = [row + [""] * (len(headers) - len(row)) for row in data]
    return headers, normalized


def _extract_table_claims(content: str, metadata: Dict[str, Any]) -> List[Claim]:
    """Extract claims from markdown table chunks.

    The row label determines the attribute family; the column header
    determines the aspect (total/annual/semester). This keeps e.g. the
    "examination fee" row from being confused with the "programme fee" row.

    PDF table extractions frequently merge the row label into a later column
    (e.g. ``| | Total Credits | 102 |``), so the label is taken as the first
    non-empty cell in the row rather than blindly assuming column 0.
    """
    parsed = _parse_markdown_table(content)
    if not parsed:
        return []
    headers, data = parsed

    source = str(metadata.get("source", "unknown"))
    page = metadata.get("page")
    programme = str(metadata.get("program_name", "") or "")

    col_attributes = [match_attribute(h) for h in headers]
    col_aspects = [match_aspect(h) for h in headers]

    claims: List[Claim] = []
    for row in data:
        if not row:
            continue

        label_idx = 0
        for idx, cell in enumerate(row):
            if cell.strip():
                label_idx = idx
                break
        row_label = row[label_idx].strip()
        row_attribute = match_attribute(row_label)
        row_aspect = match_aspect(row_label)

        for ci in range(label_idx + 1, len(row)):
            cell = row[ci]
            number = _first_number(cell)
            if number is None:
                continue
            attribute = row_attribute or col_attributes[ci]
            if not attribute:
                continue
            aspect = row_aspect if (row_attribute and row_aspect) else col_aspects[ci]
            claims.append(_make_claim(
                attribute, aspect, _trimmed(cell), number, [number],
                source, page, row_label, programme,
            ))
    return claims


def _trimmed(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def extract_claims(content: str, metadata: Dict[str, Any]) -> List[Claim]:
    """Extract all claims from one chunk (content + metadata)."""
    content_type = str(metadata.get("content_type", ""))
    if content_type == "table":
        return _extract_table_claims(content, metadata)
    return _extract_text_claims(content, metadata)


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def detect_conflicts(
    chunks: List[Tuple[str, Dict[str, Any]]],
    question: str,
    query_program: str = "",
) -> List[Conflict]:
    """Detect genuine same-attribute conflicts across the evidence chunks.

    *chunks* is a list of ``(content, metadata)`` pairs.
    Returns a list of conflict descriptors (possibly empty).
    """
    if not config.CONFLICT_ENABLED:
        return []

    claims_by_key: Dict[Tuple[str, str, str], List[Claim]] = defaultdict(list)
    for content, metadata in chunks:
        for claim in extract_claims(content, metadata):
            if claim["semantics"] != "single":
                continue
            programme = claim.get("programme") or "unknown"
            if query_program:
                # retrieval is already scoped to the query programme
                key_program = query_program
            else:
                key_program = programme if programme.startswith("online_") else "general"
            claims_by_key[(claim["attribute"], claim["aspect"], key_program)].append(claim)

    conflicts: List[Conflict] = []
    for (attribute, aspect, programme), claims in sorted(claims_by_key.items()):
        distinct = _distinct_numbers(claims)
        if len(distinct) >= config.CONFLICT_MIN_VALUE_COUNT:
            spec = config.ATTRIBUTE_TAXONOMY.get(attribute, {})
            values = [_representative(claims, n) for n in distinct]
            conflicts.append({
                "attribute": attribute,
                "aspect": aspect,
                "label": spec.get("label", attribute),
                "programme": programme,
                "values": values,
            })

    if conflicts:
        logger.warning(
            "Detected %d conflict(s): %s",
            len(conflicts),
            "; ".join(f"{c['label']} -> {', '.join(v['value_text'] for v in c['values'])}" for c in conflicts),
        )
    return conflicts


def _distinct_numbers(claims: List[Claim]) -> List[float]:
    distinct: List[float] = []
    for claim in claims:
        number = claim.get("number")
        if number is None:
            continue
        if any(abs(number - existing) < 1e-6 for existing in distinct):
            continue
        distinct.append(number)
    return distinct


def _representative(claims: List[Claim], number: float) -> Claim:
    for claim in claims:
        if claim.get("number") is not None and abs(claim["number"] - number) < 1e-6:
            return claim
    return claims[0]


def detect_conflicts_from_documents(
    documents: List[Any],
    question: str,
    query_program: str = "",
) -> List[Conflict]:
    """Wrapper accepting LangChain Document objects."""
    pairs = [(doc.page_content, doc.metadata) for doc in documents]
    return detect_conflicts(pairs, question, query_program)


def format_conflict_notice(conflicts: List[Conflict], include_locations: bool = True) -> str:
    """Build the human-readable conflict notice included in the LLM context.

    Locations (source file/page) are included when the notice is sent to the
    LLM so it can report both values. They are omitted when the notice is
    embedded in an end-user answer (deterministic fallback) so the UI never
    shows internal source details.
    """
    lines = ["Conflict Notice:"]
    for conflict in conflicts:
        lines.append(f'The retrieved documents disagree about "{conflict["label"]}":')
        for value in conflict["values"]:
            location = value["source"]
            if value.get("page") is not None:
                location += f", page {value['page']}"
            if include_locations:
                lines.append(f"- {value['value_text']} ({location})")
            else:
                lines.append(f"- {value['value_text']}")
    return "\n".join(lines)
