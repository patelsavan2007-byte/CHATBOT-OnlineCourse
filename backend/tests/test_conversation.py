import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.conversation import analyze_turn


def test_interleaved_conversations():
    # Chat 1: MBA fee -> for year 2?
    hist1 = [
        {"role": "user", "content": "What is the MBA first year fee?"},
        {"role": "assistant", "content": "The first year fee for Online MBA is 75,000 INR."}
    ]
    plan1 = analyze_turn("for year 2?", history=hist1)
    assert plan1.programmes == ["online_mba"], f"Expected online_mba, got {plan1.programmes}"
    assert plan1.topic == "fees", f"Expected fees, got {plan1.topic}"
    assert plan1.year == 2, f"Expected year 2, got {plan1.year}"
    assert "Online MBA" in plan1.standalone_question
    assert "Year 2" in plan1.standalone_question
    assert "fee" in plan1.standalone_question

    # Chat 2: BCA eligibility -> for year 2?
    hist2 = [
        {"role": "user", "content": "What are the eligibility criteria for BCA?"},
        {"role": "assistant", "content": "Eligibility for BCA requires 10+2 in any stream."}
    ]
    plan2 = analyze_turn("for year 2?", history=hist2)
    assert plan2.programmes == ["online_bca"], f"Expected online_bca, got {plan2.programmes}"
    assert plan2.topic == "eligibility", f"Expected eligibility, got {plan2.topic}"
    assert plan2.year == 2, f"Expected year 2, got {plan2.year}"
    assert "Online BCA" in plan2.standalone_question
    assert "Year 2" in plan2.standalone_question
    assert "eligibility" in plan2.standalone_question

    # Ensure Chat 1 and Chat 2 do not contaminate each other
    assert plan1.standalone_question != plan2.standalone_question
    assert plan1.programmes != plan2.programmes


def test_sequence_switching():
    # Sequence: "What is the MBA first year fee?" -> "for year 2?" -> "year 2 subjects" -> "for bca?" -> "fees?"
    h = []

    # Turn 1
    p1 = analyze_turn("What is the MBA first year fee?", h)
    assert p1.programmes == ["online_mba"]
    assert p1.topic == "fees"
    assert p1.year == 1
    h.append({"role": "user", "content": "What is the MBA first year fee?"})
    h.append({"role": "assistant", "content": "MBA 1st year fee is 75,000 INR."})

    # Turn 2
    p2 = analyze_turn("for year 2?", h)
    assert p2.programmes == ["online_mba"]
    assert p2.topic == "fees"
    assert p2.year == 2
    h.append({"role": "user", "content": "for year 2?"})
    h.append({"role": "assistant", "content": "MBA 2nd year fee is 75,000 INR."})

    # Turn 3
    p3 = analyze_turn("year 2 subjects", h)
    assert p3.programmes == ["online_mba"]
    assert p3.topic == "subjects"
    assert p3.year == 2
    assert p3.semesters_for_year == [3, 4]
    h.append({"role": "user", "content": "year 2 subjects"})
    h.append({"role": "assistant", "content": "Year 2 subjects are ..."})

    # Turn 4: "for bca?" -> switches to BCA, keeps subjects and year 2
    p4 = analyze_turn("for bca?", h)
    assert p4.programmes == ["online_bca"]
    assert p4.topic == "subjects"
    assert p4.year == 2
    h.append({"role": "user", "content": "for bca?"})
    h.append({"role": "assistant", "content": "BCA year 2 subjects are ..."})

    # Turn 5: "fees?" -> keeps BCA, switches to fees
    p5 = analyze_turn("fees?", h)
    assert p5.programmes == ["online_bca"]
    assert p5.topic == "fees"


def test_comparison_detection():
    p = analyze_turn("How do fees compare across Online BBA, BCA, MBA and MCA?")
    assert p.is_compare is True
    assert set(p.programmes) == {"online_bba", "online_bca", "online_mba", "online_mca"}
    assert p.topic == "fees"


if __name__ == "__main__":
    test_interleaved_conversations()
    test_sequence_switching()
    test_comparison_detection()
    print("ALL CONVERSATION TESTS PASSED PERFECTLY!")
