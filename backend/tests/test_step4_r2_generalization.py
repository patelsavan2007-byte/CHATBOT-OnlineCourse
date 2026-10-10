"""Verify R2 multi-programme generalization for Step 4 on MCA and BBA."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.conversation import analyze_turn

tests = [
    # Programme: MCA (Test 1)
    {
        "prog": "MCA",
        "history": [{"role": "user", "content": "How many credits are there in the Online MCA?"}],
        "query": "and what about semester 3?",
        "expected_prog": "online_mca",
        "expected_topic": "duration",  # credits/semesters
        "expected_sem": 3,
        "expected_year": 2,
    },
    # Programme: MCA (Test 2)
    {
        "prog": "MCA",
        "history": [{"role": "user", "content": "Tell me about MCA programme duration"}],
        "query": "subjects for year 2",
        "expected_prog": "online_mca",
        "expected_topic": "subjects",
        "expected_sem": None,
        "expected_year": 2,
    },
    # Programme: MCA (Test 3)
    {
        "prog": "MCA",
        "history": [{"role": "user", "content": "What is the fee for Online MCA?"}],
        "query": "how about year 2",
        "expected_prog": "online_mca",
        "expected_topic": "fees",
        "expected_sem": None,
        "expected_year": 2,
    },
    # Programme: BBA (Test 4)
    {
        "prog": "BBA",
        "history": [{"role": "user", "content": "Tell me about the Online BBA course"}],
        "query": "what are the 2nd year subjects?",
        "expected_prog": "online_bba",
        "expected_topic": "subjects",
        "expected_sem": None,
        "expected_year": 2,
    },
    # Programme: BBA (Test 5)
    {
        "prog": "BBA",
        "history": [{"role": "user", "content": "What is the tuition fee for BBA?"}],
        "query": "how much for year 2",
        "expected_prog": "online_bba",
        "expected_topic": "fees",
        "expected_sem": None,
        "expected_year": 2,
    },
    # Programme: BBA (Test 6)
    {
        "prog": "BBA",
        "history": [{"role": "user", "content": "BBA qualification requirements"}],
        "query": "what about semester 4",
        "expected_prog": "online_bba",
        "expected_topic": "eligibility",
        "expected_sem": 4,
        "expected_year": 2,
    },
]

print("Running R2 multi-programme generalization tests for Step 4...")
for i, t in enumerate(tests, 1):
    plan = analyze_turn(t["query"], history=t["history"])
    print(f"[{i}] [{t['prog']}] Query: {t['query']!r}")
    print(f"    Standalone: {plan.standalone_question!r}")
    print(f"    Programmes: {plan.programmes}, Topic: {plan.topic}, Year: {plan.year}, Sem: {plan.semester}")
    assert t["expected_prog"] in plan.programmes, f"Expected {t['expected_prog']} in {plan.programmes}"
    assert plan.topic == t["expected_topic"], f"Expected topic {t['expected_topic']} got {plan.topic}"
    assert plan.year == t["expected_year"], f"Expected year {t['expected_year']} got {plan.year}"
    if t["expected_sem"]:
        assert plan.semester == t["expected_sem"], f"Expected sem {t['expected_sem']} got {plan.semester}"

print("\nSUCCESS: All 6 multi-programme generalization tests passed for MCA and BBA!")
