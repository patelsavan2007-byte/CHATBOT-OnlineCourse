import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.conversation import analyze_turn
from app.query_expansion import is_vague_query, vague_clarification_message


def test_clarification_single_programme_carryforward():
    # User asks vague fee question -> Assistant clarifies -> User replies with "bca"
    history = [
        {"role": "user", "content": "What is the fee structure?"},
        {
            "role": "assistant",
            "content": "Which online degree programme are you inquiring about? CHARUSAT offers Online BCA, Online BBA, Online MBA, and Online MCA programmes.",
        },
    ]

    for answer, expected_prog, expected_label in [
        ("bca", "online_bca", "BCA"),
        ("Online BCA", "online_bca", "BCA"),
        ("for mca", "online_mca", "MCA"),
        ("mba", "online_mba", "MBA"),
        ("bba", "online_bba", "BBA"),
    ]:
        plan = analyze_turn(answer, history=history)
        assert plan.programmes == [expected_prog], f"Expected [{expected_prog}] for answer '{answer}'"
        assert plan.topic == "fees", f"Expected topic 'fees' for answer '{answer}'"
        assert "fee" in plan.standalone_question.lower(), f"Expected 'fee' in standalone question for '{answer}', got: {plan.standalone_question}"
        assert expected_label in plan.standalone_question, f"Expected {expected_label} in standalone question, got: {plan.standalone_question}"


def test_clarification_comparison_and_all_carryforward():
    history = [
        {"role": "user", "content": "What are the eligibility criteria?"},
        {
            "role": "assistant",
            "content": "Which online degree programme are you inquiring about? CHARUSAT offers Online BCA, Online BBA, Online MBA, and Online MCA programmes.",
        },
    ]

    # Test "bca and mca"
    plan_compare = analyze_turn("bca and mca", history=history)
    assert set(plan_compare.programmes) == {"online_bca", "online_mca"}
    assert plan_compare.is_compare is True
    assert plan_compare.topic == "eligibility"
    assert "eligibility" in plan_compare.standalone_question.lower()

    # Test "all"
    plan_all = analyze_turn("all", history=history)
    assert len(plan_all.programmes) == 4
    assert plan_all.is_compare is True
    assert plan_all.topic == "eligibility"
    assert "eligibility" in plan_all.standalone_question.lower()


def test_programme_switch_retains_question_and_topic():
    # Sequence: Ask fee for BCA -> then switch to "mca"
    history = [{"role": "user", "content": "What is the fee structure for BCA?"}]
    plan = analyze_turn("mca", history=history)
    assert plan.programmes == ["online_mca"]
    assert plan.topic == "fees"
    assert "fee" in plan.standalone_question.lower()
    assert "MCA" in plan.standalone_question
