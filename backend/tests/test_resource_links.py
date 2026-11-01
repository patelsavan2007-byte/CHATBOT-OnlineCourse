import pytest
from app.resource_post_processor import apply_resource_links, get_matching_resources

REFUND_URL = "https://charusat.online/catalogs/Fees%20Refund%20Policy.pdf"
CANCELLATION_URL = "https://charusat.online/mandatory-disclosures.html"


def test_fee_refund_triggers():
    test_questions = [
        "fee refund",
        "refund policy",
        "how do I get my money back",
        "Can I get a fees refund?",
        "what is the refund policy?",
    ]
    for q in test_questions:
        base_answer = "Students eligible for refunds may apply per university guidelines."
        result = apply_resource_links(q, base_answer)
        assert REFUND_URL in result, f"Failed for question: {q}"
        assert "Official fees refund policy (PDF):" in result
        assert "\u2014" not in result, f"Em-dash found in result for question: {q}"


def test_admission_cancellation_triggers():
    test_questions = [
        "cancel my admission",
        "admission cancellation form",
        "withdraw admission",
        "how to cancel admission?",
    ]
    for q in test_questions:
        base_answer = "You can request admission cancellation through the portal."
        result = apply_resource_links(q, base_answer)
        assert CANCELLATION_URL in result, f"Failed for question: {q}"
        assert "Admission cancellation steps:" in result
        assert "1. Open https://charusat.online/mandatory-disclosures.html" in result
        assert "2. Scroll down to the section titled \"Admission and Fees Refund\"." in result
        assert "3. Click \"Admission Cancellation Form\"" in result
        assert "\u2014" not in result, f"Em-dash found in result for question: {q}"


def test_unrelated_questions_show_no_resource_blocks():
    unrelated = [
        "what is the fee structure",
        "fee structure for bca",
        "which company recruits",
        "who are top recruiters",
        "what is the duration of mba",
        "how many semesters in mca",
    ]
    for q in unrelated:
        base_answer = "Here is the information about the programme."
        result = apply_resource_links(q, base_answer)
        assert result == base_answer, f"Resource block unexpectedly added for: {q}"
        assert REFUND_URL not in result
        assert CANCELLATION_URL not in result


def test_both_refund_and_cancellation_order():
    q = "how do I cancel my admission and get a fee refund?"
    base_answer = "Here are the details regarding admission withdrawal."
    result = apply_resource_links(q, base_answer)

    assert CANCELLATION_URL in result
    assert REFUND_URL in result
    # Check that cancellation steps appear BEFORE refund policy link
    pos_cancellation = result.index(CANCELLATION_URL)
    pos_refund = result.index(REFUND_URL)
    assert pos_cancellation < pos_refund, "Cancellation steps must appear before refund policy link"
    assert "\u2014" not in result


def test_deduplication_if_already_present():
    q = "tell me about refund policy"
    base_answer = f"The details are at {REFUND_URL}. Please read carefully."
    result = apply_resource_links(q, base_answer)
    assert result == base_answer
    assert result.count(REFUND_URL) == 1
