"""Unit tests for the general-purpose RAG helper modules.

No vector store or API access is required. Run with:
    python test_unit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_core.documents import Document

from app import config
from app.conflict import (
    detect_conflicts,
    extract_claims,
    extract_numbers,
    focus_attributes,
    format_conflict_notice,
    match_attribute,
    normalize_number,
)
from app.deduplicate import (
    apply_diversity_cap,
    deduplicate_results,
    is_near_duplicate,
    normalize_text,
    token_jaccard,
)
from app.source_authority import SourceAuthority

PASSED = 0
FAILED = 0


def check(name: str, condition: bool) -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  [PASSED] {name}")
    else:
        FAILED += 1
        print(f"  [FAILED] {name}")


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def test_deduplicate() -> None:
    print("\n--- Deduplicate ---")
    check("normalize_text lowercases and strips punctuation", normalize_text("Fee: 75,000 INR!") == "fee 75 000 inr")
    check("token_jaccard identical is 1.0", token_jaccard("a b c", "a b c") == 1.0)
    check("token_jaccard disjoint is 0.0", token_jaccard("a b c", "x y z") == 0.0)

    check("identical texts are near-duplicates", is_near_duplicate("the total fee is 75000", "the total fee is 75000"))
    long_text = "a " * 50
    check(
        "long substring is a near-duplicate",
        is_near_duplicate(long_text, long_text + "b " * 20),
    )
    check(
        "unrelated texts are not near-duplicates",
        not is_near_duplicate("the total fee is seventy five thousand", "eligibility requires a bachelor degree"),
    )

    results = [
        (Document(page_content="total fee is 75000 INR", metadata={"source": "a.md"}), 0.8),
        (Document(page_content="total fee is 75000 INR", metadata={"source": "b.md"}), 0.9),
    ]
    kept, removed = deduplicate_results(results)
    check("higher-scoring duplicate is kept", len(kept) == 1 and kept[0][1] == 0.9)
    check("duplicate is reported removed", len(removed) == 1)

    diverse = [
        (Document(page_content=f"chunk {i}", metadata={"source": "same.md", "page": 1}), 1.0 - i * 0.01)
        for i in range(5)
    ]
    kept, dropped = apply_diversity_cap(diverse, max_per_source_page=2)
    check("diversity cap keeps 2 per (source, page)", len(kept) == 2 and len(dropped) == 3)


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def test_conflict() -> None:
    print("\n--- Conflict detection ---")
    check(
        "match_attribute resolves total credits",
        match_attribute("Total Number of Credits") == "total_credits",
    )
    check(
        "match_attribute resolves total programme fee",
        match_attribute("Total Programme Fee") == "total_fee",
    )

    check(
        "focus_attributes catches specific keyword",
        focus_attributes("What is the total number of credits in the MBA programme?") == ["total_credits", "per_semester_credits"],
    )
    check(
        "focus_attributes falls back to fee family",
        focus_attributes("How much is the fee?") == [
            "total_fee", "annual_fee", "semester_fee", "examination_fee", "caution_deposit",
        ],
    )

    check("extract_numbers handles Indian format", extract_numbers("Rs. 1,50,000") == [150000.0])
    check("normalize_number returns first number", normalize_number("around 102 credits") == 102.0)

    text_claims = extract_claims("Total Number of Credits: 102", {"source": "s.md"})
    check("text claim extracted from label: value", len(text_claims) == 1 and text_claims[0]["number"] == 102.0)

    table = (
        "| Sl. No. | Semester | Number of Credits |\n"
        "| ------- | -------- | ----------------- |\n"
        "| 1 | Semester 1 | 28 |\n"
        "| | Total Credits | 102 |\n"
    )
    table_claims = extract_claims(table, {"source": "t.md", "content_type": "table"})
    total_claims = [c for c in table_claims if c["attribute"] == "total_credits"]
    check("table 'Total Credits | 102' claim extracted", len(total_claims) == 1 and total_claims[0]["number"] == 102.0)
    per_sem = [c for c in table_claims if c["attribute"] == "per_semester_credits"]
    check("per-semester credit claims extracted", {c["number"] for c in per_sem} == {28.0})

    chunks = [
        ("Total Number of Credits: 102", {"source": "page4.md", "page": 4, "program_name": "online_mba"}),
        ("Total Number of Credits: 100", {"source": "page12.md", "page": 12, "program_name": "online_mba"}),
    ]
    conflicts = detect_conflicts(chunks, "total credits in MBA?", query_program="online_mba")
    check("conflict detected for 102 vs 100", len(conflicts) == 1)
    notice = format_conflict_notice(conflicts)
    check("conflict notice mentions both values", "102" in notice and "100" in notice)

    agreeing = [
        ("Total Number of Credits: 102", {"source": "a.md", "page": 4}),
        ("Total Number of Credits: 102", {"source": "b.md", "page": 10}),
    ]
    check("agreeing values produce no conflict", detect_conflicts(agreeing, "credits?") == [])

    annual_vs_total = [
        ("Annual fee for first year: Rs. 75,000", {"source": "a.md"}),
        ("Total Programme Fee: Rs. 1,50,000", {"source": "b.md"}),
    ]
    check("annual vs total fee is not a conflict", detect_conflicts(annual_vs_total, "fee?") == [])


# ---------------------------------------------------------------------------
# Source authority
# ---------------------------------------------------------------------------

def test_source_authority() -> None:
    print("\n--- Source authority ---")
    pdf_priority = SourceAuthority.priority({"source": "pdfs/PPR_Online MBA.pdf", "document_type": "pdf"})
    check("PPR PDF gets top priority", pdf_priority == 1.0)

    website_priority = SourceAuthority.priority({"source": "programs/online_mba.md"})
    check("programme website page gets high priority", website_priority == 0.9)

    check(
        "programme match adds priority bonus",
        SourceAuthority.authority_bonus(
            {"source": "programs/online_mba.md", "program_name": "online_mba"}, query_program="online_mba"
        )
        > SourceAuthority.authority_bonus({"source": "programs/online_mba.md", "program_name": "online_mba"}),
    )
    check(
        "authority bonus is bounded",
        SourceAuthority.authority_bonus(
            {"source": "pdfs/PPR_Online MBA.pdf", "document_type": "pdf", "program_name": "online_mba"},
            query_program="online_mba",
        )
        <= config.SOURCE_AUTHORITY_MAX_BONUS,
    )


def test_config_sanity() -> None:
    print("\n--- Config sanity ---")
    check("SCORE_CAP <= 1.0", 0.0 < config.SCORE_CAP <= 1.0)
    check("keyword boost capped below SCORE_CAP", config.KEYWORD_BOOST_MAX < config.SCORE_CAP)
    check("candidate pool larger than TOP_K", config.CANDIDATE_POOL_SIZE > config.TOP_K)
    check(
        "all taxonomy keywords non-empty",
        all(kw for spec in config.ATTRIBUTE_TAXONOMY.values() for kw in spec.get("keywords", [])),
    )
    check("policy patterns non-empty", len(config.GENERAL_POLICY_SOURCE_PATTERNS) > 0)


if __name__ == "__main__":
    test_deduplicate()
    test_conflict()
    test_source_authority()
    test_config_sanity()
    print(f"\n=== Unit tests: {PASSED} passed, {FAILED} failed ===")
    sys.exit(1 if FAILED else 0)
