"""Test per-request conversation isolation and cache separation across interleaved chats."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conversation import analyze_turn
from app.cache import QuestionCache


def test_interleaved_turn_plans():
    # Chat 1: MBA fee flow
    chat1_h1 = [{"role": "user", "content": "What is the MBA first year fee?"}]
    plan1 = analyze_turn("for year 2?", history=chat1_h1)

    assert "online_mba" in plan1.programmes
    assert plan1.year == 2
    assert plan1.topic == "fees"
    assert "Online MBA" in plan1.standalone_question
    assert "Year 2" in plan1.standalone_question

    # Chat 2: BCA eligibility flow
    chat2_h1 = [{"role": "user", "content": "What is the eligibility for BCA?"}]
    plan2 = analyze_turn("for year 2?", history=chat2_h1)

    assert "online_bca" in plan2.programmes
    assert plan2.year == 2
    assert plan2.topic == "eligibility"
    assert "Online BCA" in plan2.standalone_question
    assert "Year 2" in plan2.standalone_question

    # Ensure plans and standalone queries are completely different
    assert plan1.programmes != plan2.programmes
    assert plan1.standalone_question != plan2.standalone_question


def test_cache_separation_for_same_raw_question():
    cache = QuestionCache()

    # Chat 1: MBA "for year 2?"
    plan1 = analyze_turn("for year 2?", history=[{"role": "user", "content": "What is the MBA first year fee?"}])
    sources1 = [{"source": "programs/online_mba.md", "score": 0.85}]
    answer1 = "MBA Year 2 fee is 75000"
    cache.set(plan1.standalone_question, plan1.programmes, answer1, sources1, status="gemini-2.5-flash")

    # Chat 2: BCA "for year 2?"
    plan2 = analyze_turn("for year 2?", history=[{"role": "user", "content": "What is the eligibility for BCA?"}])
    sources2 = [{"source": "programs/online_bca.md", "score": 0.88}]
    answer2 = "BCA Year 2 eligibility requirements"
    cache.set(plan2.standalone_question, plan2.programmes, answer2, sources2, status="gemini-2.5-flash")

    # Lookups should be completely isolated
    res1 = cache.get(plan1.standalone_question, plan1.programmes)
    assert res1 is not None
    assert res1[0] == answer1
    assert res1[1] == sources1

    res2 = cache.get(plan2.standalone_question, plan2.programmes)
    assert res2 is not None
    assert res2[0] == answer2
    assert res2[1] == sources2

    # Querying Chat 2's question with Chat 1's programmes must miss
    assert cache.get(plan2.standalone_question, plan1.programmes) is None
    assert cache.get(plan1.standalone_question, plan2.programmes) is None


if __name__ == "__main__":
    test_interleaved_turn_plans()
    test_cache_separation_for_same_raw_question()
    print("All interleaved chat tests passed successfully!")
