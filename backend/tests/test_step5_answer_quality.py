import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.llm import normalize_currency, strip_internal_references
from app.conversation import analyze_turn


def test_currency_normalization():
    # R1: Test currency normalization with dynamic/sample patterns, avoiding hard-coded factual amounts
    test_cases = [
        ("The fees are ₹12,345 INR per semester.", "The fees are ₹12,345 per semester."),
        ("Tuition is INR 12,345 for the year.", "Tuition is ₹12,345 for the year."),
        ("It costs Rs. 12,345 total.", "It costs ₹12,345 total."),
        ("Pay 12,345 INR online.", "Pay ₹12,345 online."),
        ("Registration: ₹ 12,345/- only.", "Registration: ₹12,345 only."),
        ("The year 2026 has 120 credits across 4 semesters.", "The year 2026 has 120 credits across 4 semesters."),
    ]
    for inp, expected in test_cases:
        res = normalize_currency(inp)
        assert res == expected, f"Failed: '{inp}' -> '{res}', expected '{expected}'"

    # Also verify strip_internal_references applies it
    cleaned = strip_internal_references("Total cost is INR 99,999 INR.")
    assert "₹99,999" in cleaned
    assert "INR" not in cleaned


def test_bare_programme_topic_retention():
    # 1. Bare programme inherits fee topic
    h1 = [{"role": "user", "content": "What is the fee structure for BCA?"}]
    p1 = analyze_turn("mca", history=h1)
    assert p1.programmes == ["online_mca"]
    assert p1.topic == "fees"
    assert "fee" in p1.standalone_question

    # 2. Bare programme inherits subjects and year
    h2 = [
        {"role": "user", "content": "What are the MBA subjects?"},
        {"role": "user", "content": "What about year 2?"},
    ]
    p2 = analyze_turn("online bba", history=h2)
    assert p2.programmes == ["online_bba"]
    assert p2.topic == "subjects"
    assert p2.year == 2

    # 3. Bare programme after cross-programme comparison
    h3 = [{"role": "user", "content": "Compare eligibility across all programmes"}]
    p3 = analyze_turn("MCA", history=h3)
    assert p3.programmes == ["online_mca"]
    assert p3.topic == "eligibility"


if __name__ == "__main__":
    test_currency_normalization()
    test_bare_programme_topic_retention()
    print("ALL STEP 5 ANSWER QUALITY TESTS PASSED!")
