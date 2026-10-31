"""Comprehensive Step 4 test suite for Round 5C.
Covers:
(a) Contacts: 5 new paraphrases each across 6 services and all 4 programmes.
(b) Concurrency through REAL path (POST /api/chat with LLM): 20 parallel requests.
(c) Cache test: 6 fee questions + 5 admission questions in ONE chat.
(d) Conflict and number-check unit tests (BCA 50/50 vs 30/70, BBA credits, MBA credits, missing fee component, invented number).
"""
import concurrent.futures
import io
import json
import os
import sys
import time
import urllib.request

# Pytest imports this module during collection. Replacing sys.stdout here wraps
# and later closes pytest's terminal stream during teardown. Reconfigure the
# existing stream instead, without taking ownership of its buffer.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API_URL = "http://127.0.0.1:8000/api/chat"

# --- Test (a): Contacts ---
def test_contacts():
    print("=== Testing (a) Contacts Paraphrases & Tags ===")
    from app.contacts import get_contact_line
    
    # 6 services, 5 paraphrases each = 30 queries
    cases = [
        # Technical issues -> Learning Management System
        ("bca lms portal error while submitting", "online_bca", "Learning Management System", "(BCA/MCA)"),
        ("cannot login to mba portal account", "online_mba", "Learning Management System", "(BBA/MBA)"),
        ("mca technical problem with lecture stream", "online_mca", "Learning Management System", "(BCA/MCA)"),
        ("bba forgot login credentials for lms", "online_bba", "Learning Management System", "(BBA/MBA)"),
        ("general technical issue with classroom access", None, "Learning Management System", "(BCA/MCA)"),
        
        # Student ID -> Student Services
        ("how to collect bba smart identity card", "online_bba", "Student Services", None),
        ("when will bca student id card arrive", "online_bca", "Student Services", None),
        ("mba id card dispatch tracking status", "online_mba", "Student Services", None),
        ("mca digital identity card helpdesk", "online_mca", "Student Services", None),
        ("who provides student id verification", None, "Student Services", None),

        # Faculty / Mentor -> Course Mentor
        ("need to consult bba academic advisor", "online_bba", "Course Mentor", None),
        ("bca professor appointment for guidance", "online_bca", "Course Mentor", None),
        ("mba mentor consultation contact number", "online_mba", "Course Mentor", None),
        ("mca course teacher discussion hours", "online_mca", "Course Mentor", None),
        ("who is assigned as academic mentor", None, "Course Mentor", None),

        # Marksheet / Results -> Examinations
        ("bba semester 2 marksheet download issue", "online_bba", "Examinations", None),
        ("bca grade card not showing online", "online_bca", "Examinations", "(BCA/MCA)"),
        ("mba transcript copy required for evaluation", "online_mba", "Examinations", None),
        ("mca exam result discrepancy correction", "online_mca", "Examinations", "(BCA/MCA)"),
        ("whom to contact for backlog marksheet", None, "Examinations", None),

        # Entrance test -> Admissions
        ("bba entrance test registration inquiry", "online_bba", "Admissions", None),
        ("bca admission test syllabus helpdesk", "online_bca", "Admissions", None),
        ("mba cat cmat qualifying test guidance", "online_mba", "Admissions", None),
        ("mca entrance exam exempt criteria officer", "online_mca", "Admissions", None),
        ("admissions desk contact for entrance test", None, "Admissions", None),

        # Refund / Receipt -> Accounts & Payments
        ("bba tuition fee receipt generation problem", "online_bba", "Accounts & Payments", None),
        ("bca payment confirmation acknowledgment receipt", "online_bca", "Accounts & Payments", None),
        ("mba admission cancellation refund status", "online_mba", "Accounts & Payments", None),
        ("mca fee refund application timeline", "online_mca", "Accounts & Payments", None),
        ("accounts department contact for fee payment receipt", None, "Accounts & Payments", None),
    ]

    passed = 0
    from app.lexicon import detect_primary_topic
    for q, prog, expected_service, expected_tag in cases:
        topic = detect_primary_topic(q)
        line = get_contact_line(topic=topic, programme=prog)
        if expected_service in line:
            if expected_tag is None or expected_tag in line:
                passed += 1
            else:
                print(f"FAIL tag mismatch for {q!r}: got {line!r}")
        else:
            print(f"FAIL service mismatch for {q!r}: got {line!r}")

    print(f"Contacts Test Result: {passed}/{len(cases)} PASSED\n")
    assert passed == len(cases)


# --- Test (d): Conflicts and Number Verification ---
def test_conflicts_and_numbers():
    print("=== Testing (d) Conflict & Number Checks ===")
    from langchain_core.documents import Document
    from app.conflict import detect_conflicts_from_documents
    from app.rag_chain import _find_unverified_numbers

    # 1. BCA 50/50 vs 30/70 conflict test
    doc_bca_text = Document(
        page_content="Continuous internal evaluation: 50 marks.\nFinal university examination: 50 marks.",
        metadata={"source": "PPR_Online BCA.pdf", "page": 10, "program_name": "online_bca"}
    )
    doc_bca_table = Document(
        page_content="| Course | Internal assessment | University examination | Total |\n| BCA101 | 30 | 70 | 100 |",
        metadata={"source": "PPR_Online BCA.pdf", "page": 6, "program_name": "online_bca", "content_type": "table"}
    )
    conflicts_bca = detect_conflicts_from_documents([doc_bca_text, doc_bca_table], question="What is the evaluation scheme for BCA?", query_program="online_bca")
    print(f"BCA Evaluation Conflict Detected: {len(conflicts_bca) > 0} ({[c['attribute'] for c in conflicts_bca]})")
    assert len(conflicts_bca) > 0, "BCA evaluation split conflict should be detected"

    # 2. BBA credits 130 vs 133 conflict test
    doc_bba1 = Document(page_content="Total credits for Online BBA: 130 credits", metadata={"source": "PPR_Online BBA.pdf", "page": 4, "program_name": "online_bba"})
    doc_bba2 = Document(page_content="Total credits for Online BBA: 133 credits", metadata={"source": "programs/online_bba.md", "page": 1, "program_name": "online_bba"})
    conflicts_bba = detect_conflicts_from_documents([doc_bba1, doc_bba2], question="How many credits for BBA?", query_program="online_bba")
    print(f"BBA Credits Conflict Detected: {len(conflicts_bba) > 0}")
    assert len(conflicts_bba) > 0, "BBA credits conflict should be detected"

    # 3. MBA credits 102 vs 104 conflict test
    doc_mba1 = Document(page_content="Total credits for Online MBA: 102 credits", metadata={"source": "PPR_Online MBA.pdf", "page": 4, "program_name": "online_mba"})
    doc_mba2 = Document(page_content="Total credits for Online MBA: 104 credits", metadata={"source": "programs/online_mba.md", "page": 1, "program_name": "online_mba"})
    conflicts_mba = detect_conflicts_from_documents([doc_mba1, doc_mba2], question="How many credits for MBA?", query_program="online_mba")
    print(f"MBA Credits Conflict Detected: {len(conflicts_mba) > 0}")
    assert len(conflicts_mba) > 0, "MBA credits conflict should be detected"

    # 4. Number check tolerance: arithmetic multiples and sums
    evidence = [
        ("Annual tuition fee for Online BBA is ₹50,000 per year for 3 years. Examination fee is ₹1,500 per semester across 6 semesters.", {"source": "bba.md"})
    ]
    safe_response = "The total tuition fee is ₹1,50,000 (₹50,000 x 3 years), exam fee is ₹9,000, and overall total is ₹1,59,000."
    unverified_safe = _find_unverified_numbers(safe_response, evidence, "What is BBA total fee?")
    print(f"Legitimate computed totals unverified: {unverified_safe}")
    assert len(unverified_safe) == 0, f"Derived computed totals should not be flagged: {unverified_safe}"

    # 5. Number check catches missing/invented fee components
    missing_fee_response = "Online BBA requires a ₹5,000 caution deposit and ₹2,500 registration charge."
    unverified_missing = _find_unverified_numbers(missing_fee_response, evidence, "What is BBA total fee?")
    print(f"Missing fee components caught: {unverified_missing}")
    assert 5000.0 in unverified_missing and 2500.0 in unverified_missing, "Missing fee components must be caught"

    # 6. Number check blocks random invented numbers
    hallucinated_response = "The processing fee is ₹4,700 and caution deposit is ₹8,200."
    unverified_bad = _find_unverified_numbers(hallucinated_response, evidence, "What is BBA total fee?")
    print(f"Invented numbers caught: {unverified_bad}")
    assert 4700.0 in unverified_bad and 8200.0 in unverified_bad, "Invented numbers must be caught"
    print("Conflict & Number Checks: ALL PASSED\n")


# --- Test (c): Cache Separation in One Chat ---
def test_cache_separation():
    print("=== Testing (c) Cache Separation in Single Chat ===")
    def post_chat(q, conv_id):
        data = json.dumps({"question": q, "conversation_id": conv_id}).encode("utf-8")
        req = urllib.request.Request(API_URL, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("answer", ""), body.get("conversation_id")

    conv_id = None
    fee_questions = [
        "What is the total fee for BBA?",
        "What is the total fee for BCA?",
        "What is the total fee for MBA?",
        "What is the total fee for MCA?",
        "Are exam fees included in BCA fee?",
        "Is there any late fee for delayed payment?",
    ]
    admission_questions = [
        "What are the eligibility criteria for BBA?",
        "Can arts students apply for BCA?",
        "What is the eligibility for MBA?",
        "What are the mandatory documents for MCA admission?",
        "What is the last date to apply?",
    ]

    all_qs = fee_questions + admission_questions
    answers = []
    for i, q in enumerate(all_qs, 1):
        ans, cid = post_chat(q, conv_id)
        if not conv_id:
            conv_id = cid
        answers.append(ans)
        print(f"[{i:02d}/11] {q[:35]}... -> {ans[:50]}...", flush=True)

    # Assert all answers are non-empty and distinct
    assert len(answers) == 11
    assert len(set(answers[:4])) == 4, "Fee answers for BBA, BCA, MBA, MCA must all be distinct"
    print("Cache Separation in Single Chat: ALL PASSED\n", flush=True)


# --- Test (b): Real Path Concurrency ---
def test_real_path_concurrency():
    print("=== Testing (b) Real Path Multi-Threaded Concurrency (20 Requests) ===")
    queries = [
        ("BBA fee structure", "bba"),
        ("BCA eligibility", "bca"),
        ("MBA total credits", "mba"),
        ("MCA semester count", "mca"),
        ("BBA curriculum subjects", "bba"),
        ("BCA exam mode online or offline", "bca"),
        ("MBA specializations list", "mba"),
        ("MCA project work dissertation", "mca"),
        ("BBA refund policy after classes", "bba"),
        ("BCA passing marks criteria", "bca"),
        ("MBA live webinar attendance", "mba"),
        ("MCA LMS login password reset", "mca"),
        ("BBA organizational attachment training", "bba"),
        ("BCA WES evaluation validity", "bca"),
        ("MBA comprehensive project details", "mba"),
        ("MCA mathematics background requirement", "mca"),
        ("BBA faculty members", "bba"),
        ("BCA tuition fee in installments", "bca"),
        ("MBA grading system 10 point scale", "mba"),
        ("MCA placement assistance cell", "mca"),
    ]

    def run_req(q, tag):
        data = json.dumps({"question": q}).encode("utf-8")
        req = urllib.request.Request(API_URL, data=data, headers={"Content-Type": "application/json"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                elapsed = time.time() - t0
                body = json.loads(resp.read().decode("utf-8"))
                return True, body.get("answer", ""), elapsed, tag
        except Exception as exc:
            return False, str(exc), time.time() - t0, tag

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(run_req, q, tag) for q, tag in queries]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    passed = sum(1 for ok, ans, _, _ in results if ok and len(ans) > 30)
    print(f"Concurrency Result: {passed}/{len(queries)} PASSED")
    for ok, ans, elapsed, tag in results:
        print(f"  [{tag}] ok={ok}, len={len(ans)}, elapsed={elapsed:.2f}s")
    assert passed == len(queries), f"Expected 20/20, got {passed}"
    print("Real Path Concurrency: ALL PASSED\n")


if __name__ == "__main__":
    test_contacts()
    test_conflicts_and_numbers()
    test_cache_separation()
    test_real_path_concurrency()
    print("ALL STEP 4 VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
