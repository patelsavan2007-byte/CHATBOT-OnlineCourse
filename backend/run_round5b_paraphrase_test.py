"""Test 20 new paraphrases with typos + 10 parallel requests for Step 8 verification.
"""
import concurrent.futures
import io
import json
import os
import sys
import time
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
API_URL = "http://127.0.0.1:8000/api/chat"

def query_chat(q):
    data = json.dumps({"question": q}).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            elapsed = time.time() - t0
            body = json.loads(resp.read().decode("utf-8"))
            return True, body.get("answer", ""), elapsed
    except Exception as exc:
        return False, str(exc), time.time() - t0

def test_paraphrases():
    test_queries = [
        "wht r the subjekts in bba 2nd year",
        "hw much is bba fees per sem",
        "bba eligibility with 48 percent",
        "is there organizational attachment in bba",
        "bca semester 3 syllabus",
        "is online bca degree valid for wes evaluation",
        "bca continuous internal assessment weightage",
        "what is the exam fee for bca",
        "specialisation options in mba online",
        "cost of online mba whole course",
        "is comprehensive project mandatory for mba",
        "mba passing grade criteria",
        "can arts student apply for mca",
        "mca dissertation project work credits",
        "mca external exam percentage",
        "refund policy if i cancel admission",
        "how to login to lms portal",
        "attendance tracking for live webinars",
        "installment emi options available",
        "whom to contact for examination issues",
    ]
    
    print(f"--- Running 20 New Paraphrase Tests ---")
    passed = 0
    for i, q in enumerate(test_queries, 1):
        ok, ans, elapsed = query_chat(q)
        ans_clean = (ans[:60] + "...") if len(ans) > 60 else ans
        if ok and len(ans) > 20:
            print(f"[{i:02d}/20] PASS: {q!r} -> {ans_clean!r} ({elapsed:.2f}s)")
            passed += 1
        else:
            print(f"[{i:02d}/20] FAIL: {q!r} -> {ans_clean!r} ({elapsed:.2f}s)")
    print(f"Paraphrase Test Result: {passed}/{len(test_queries)} PASSED\n")
    return passed == len(test_queries)

def test_parallel():
    parallel_queries = [
        "Tell me about BBA fee structure",
        "What are MCA eligibility rules",
        "How many credits in MBA",
        "What is BCA course syllabus",
        "Is webinar attendance tracked",
        "What is the exam fee for BBA",
        "Can I pay tuition in installments",
        "Does MCA require mathematics",
        "What is WES approval status",
        "Who is the contact for LMS technical help",
    ]
    print(f"--- Running 10 Parallel Live Requests ---")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(query_chat, q): q for q in parallel_queries}
        for f in concurrent.futures.as_completed(futures):
            q = futures[f]
            ok, ans, elapsed = f.result()
            print(f"Parallel: {q!r} -> ok={ok}, len={len(ans)}, elapsed={elapsed:.2f}s")
            results.append(ok and len(ans) > 20)
    passed = sum(results)
    print(f"Parallel Test Result: {passed}/{len(parallel_queries)} PASSED\n")
    return passed == len(parallel_queries)

if __name__ == "__main__":
    p_ok = test_paraphrases()
    par_ok = test_parallel()
    if p_ok and par_ok:
        print("ALL STEP 8 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    else:
        print("SOME TESTS FAILED")
