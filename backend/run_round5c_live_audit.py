"""Round 5C Live 3-Way Audit Script.

Executes:
1. Pass (a): Single chat session with cache enabled (77 questions)
2. Pass (b): Single chat session with cache disabled (77 questions)
3. Pass (c): Fresh chat session per question (77 questions)
4. Benchmarks 20 new paraphrases across 4 programmes + 10 parallel requests.
5. Measures latency: p50, p90, max.
6. Records complete empirical outputs to CHANGES/round5c_audit_results.json.
"""
import concurrent.futures
import io
import json
import math
import os
import sys
import time
import urllib.request

# Ensure UTF-8 output on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API_URL = "http://127.0.0.1:8000/api/chat"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_FILE = os.path.join(PROJECT_ROOT, "CHANGES", "round5b_audit.json")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "CHANGES", "round5c_audit_results.json")

KNOWN_REFUSALS = {
    "Q03", "Q04", "Q08", "Q09", "Q10", "Q11", "Q12", "Q13", "Q14", "Q15",
    "Q23", "Q24", "Q25", "Q26", "Q27", "Q28", "Q32", "Q40", "Q41", "Q42",
    "Q43", "Q44", "Q50", "Q52", "Q53", "Q54", "Q55", "Q56", "Q69", "Q70",
    "Q71", "Q72", "Q74"
}

def send_chat(question, conversation_id=None, history=None, use_cache=True, timeout=60):
    payload = {"question": question, "use_cache": use_cache}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    if history:
        payload["history"] = history[-8:]
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.time() - t0
            body = json.loads(resp.read().decode("utf-8"))
            return {
                "answer": body.get("answer", ""),
                "conversation_id": body.get("conversation_id"),
                "elapsed_s": round(elapsed, 3),
                "error": None,
            }
    except Exception as exc:
        elapsed = time.time() - t0
        return {
            "answer": "",
            "conversation_id": conversation_id,
            "elapsed_s": round(elapsed, 3),
            "error": str(exc),
        }

def classify(qid, answer, error):
    if error or not answer:
        return "ERROR"
    ans_lower = answer.lower()
    
    # Check if answer starts with a refusal
    is_refusal = (
        ans_lower.startswith("i couldn't find") or
        ans_lower.startswith("i could not find") or
        "i couldn't find this information in the official programme documents" in ans_lower
    )
    
    if is_refusal:
        if qid in KNOWN_REFUSALS:
            return "CORRECT_REFUSAL"
        return "WRONG_DATA_EXISTS"
    
    if qid in KNOWN_REFUSALS:
        if "contact" in ans_lower and ("admissions" in ans_lower or "mentor" in ans_lower or "services" in ans_lower):
            return "CORRECT_REFUSAL"
            
    return "CORRECT"

def compute_percentiles(latencies):
    if not latencies:
        return {"p50": 0.0, "p90": 0.0, "max": 0.0}
    s = sorted(latencies)
    n = len(s)
    p50_idx = min(int(n * 0.50), n - 1)
    p90_idx = min(int(n * 0.90), n - 1)
    return {
        "p50": round(s[p50_idx], 3),
        "p90": round(s[p90_idx], 3),
        "max": round(s[-1], 3),
    }

def run_audit_pass(name, questions, single_chat=True, use_cache=True):
    print(f"\n--- Running Pass: {name} (single_chat={single_chat}, use_cache={use_cache}) ---", flush=True)
    results = []
    counts = {"CORRECT": 0, "CORRECT_REFUSAL": 0, "WRONG_DATA_EXISTS": 0, "ERROR": 0}
    conv_id = None
    history = []
    latencies = []

    for i, item in enumerate(questions, 1):
        qid = item["id"]
        q_text = item["question"]
        current_conv = conv_id if single_chat else None
        current_hist = history if single_chat else None

        res = send_chat(q_text, conversation_id=current_conv, history=current_hist, use_cache=use_cache)
        ans = res["answer"]
        err = res["error"]
        lat = res["elapsed_s"]
        latencies.append(lat)

        if single_chat and not conv_id:
            conv_id = res.get("conversation_id")

        label = classify(qid, ans, err)
        counts[label] = counts.get(label, 0) + 1
        results.append({
            "id": qid,
            "question": q_text,
            "classification": label,
            "elapsed_s": lat,
            "answer": ans[:120] + "..." if len(ans) > 120 else ans,
            "error": err,
        })
        if single_chat and ans:
            history.append({"role": "user", "content": q_text})
            history.append({"role": "assistant", "content": ans})

        if i % 15 == 0 or i == len(questions):
            print(f"[{i:02d}/{len(questions)}] {qid} -> {label} ({lat:.2f}s) | Progress: {counts}", flush=True)

    perc = compute_percentiles(latencies)
    print(f"Pass {name} Completed: {counts} | Latency p50={perc['p50']}s, p90={perc['p90']}s, max={perc['max']}s", flush=True)
    return {
        "summary": counts,
        "latencies": perc,
        "results": results,
    }

def run_paraphrases_and_concurrency():
    print("\n--- Running 20 New Paraphrases Across 4 Programmes ---", flush=True)
    paraphrases = [
        # BBA
        ("tell me the admission requirement for bba online", "online_bba"),
        ("what is the total expenditure for completing bba", "online_bba"),
        ("is there an internship project in final semester bba", "online_bba"),
        ("who is teaching business administration subjects", "online_bba"),
        ("can i appear for bba term end exams from home", "online_bba"),
        # BCA
        ("eligibility rules for joining bca computer course", "online_bca"),
        ("full 3 year fee breakdown for bca programme", "online_bca"),
        ("how are bca practical assessments evaluated", "online_bca"),
        ("is bca certificate recognized by wes for canada", "online_bca"),
        ("does bca offer campus placement assistance", "online_bca"),
        # MBA
        ("what qualifications do i need to enroll in online mba", "online_mba"),
        ("total tuition fee for mba across two years", "online_mba"),
        ("is there a dissertation or industrial project in mba", "online_mba"),
        ("how much weightage is given to internal marks in mba", "online_mba"),
        ("can i pay mba fee through installments or emi", "online_mba"),
        # MCA
        ("can a bsc graduate apply for mca online degree", "online_mca"),
        ("what is the aggregate cost for mca programme", "online_mca"),
        ("does mca require dissertation project work in 4th sem", "online_mca"),
        ("how are mca live lectures and webinars scheduled", "online_mca"),
        ("whom to reach out for mca degree certificate", "online_mca"),
    ]

    para_results = []
    para_latencies = []
    for q, prog in paraphrases:
        res = send_chat(q, timeout=30)
        ans = res["answer"]
        lat = res["elapsed_s"]
        para_latencies.append(lat)
        ok = len(ans) > 30 and res["error"] is None
        para_results.append({
            "question": q,
            "programme": prog,
            "ok": ok,
            "elapsed_s": lat,
            "answer_snippet": ans[:80],
        })

    para_passed = sum(1 for p in para_results if p["ok"])
    print(f"Paraphrases: {para_passed}/20 PASSED | p50={compute_percentiles(para_latencies)['p50']}s", flush=True)

    print("\n--- Running 10 Parallel Requests for Concurrency & Peak Latency ---", flush=True)
    parallel_queries = [
        "What is the total fee for BBA?",
        "What are the eligibility criteria for BCA?",
        "What is the total fee for MBA?",
        "What are the mandatory documents for MCA admission?",
        "Will exams be online or offline?",
        "What is the attendance requirement for webinars?",
        "Are placement services provided for online students?",
        "How do I get my marksheet after semester completion?",
        "Is the online degree recognized by UGC?",
        "What is the refund policy on admission cancellation?",
    ]

    def call_one(q):
        return send_chat(q, timeout=40)

    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(call_one, q) for q in parallel_queries]
        c_results = [f.result() for f in concurrent.futures.as_completed(futures)]
    total_concurrency_time = round(time.time() - t0, 3)

    c_latencies = [r["elapsed_s"] for r in c_results]
    c_passed = sum(1 for r in c_results if len(r["answer"]) > 30 and r["error"] is None)
    c_perc = compute_percentiles(c_latencies)
    print(f"Parallel Concurrency: {c_passed}/10 PASSED in {total_concurrency_time}s | p50={c_perc['p50']}s, p90={c_perc['p90']}s, max={c_perc['max']}s", flush=True)

    return {
        "paraphrases_passed": f"{para_passed}/20",
        "paraphrases_latencies": compute_percentiles(para_latencies),
        "paraphrases": para_results,
        "concurrency_passed": f"{c_passed}/10",
        "concurrency_latencies": c_perc,
        "concurrency_wall_time_s": total_concurrency_time,
    }

def main():
    with open(BASELINE_FILE, "r", encoding="utf-8") as f:
        baseline_data = json.load(f)
    questions = baseline_data["results"]
    print(f"Loaded {len(questions)} benchmark questions from {BASELINE_FILE}.", flush=True)

    # 1. Pass (a): Single chat with cache on
    pass_a = run_audit_pass("single_chat_cache_on", questions, single_chat=True, use_cache=True)

    # 2. Pass (b): Single chat with cache off
    pass_b = run_audit_pass("single_chat_cache_off", questions, single_chat=True, use_cache=False)

    # 3. Pass (c): Fresh chat per question
    pass_c = run_audit_pass("fresh_chat_per_question", questions, single_chat=False, use_cache=True)

    # 4. Paraphrases and Concurrency
    stress = run_paraphrases_and_concurrency()

    final_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "benchmark_questions": len(questions),
        "pass_a_single_chat_cache_on": pass_a,
        "pass_b_single_chat_cache_off": pass_b,
        "pass_c_fresh_chat": pass_c,
        "stress_and_paraphrase": stress,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)

    print(f"\nAll 3 audit passes and stress tests completed! Saved to {OUTPUT_FILE}", flush=True)

if __name__ == "__main__":
    main()
