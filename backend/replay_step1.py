import json
import os
import time
import urllib.request

API_URL = "http://127.0.0.1:8000/api/chat"

def send_chat(question, history=None):
    payload = {"question": question}
    if history:
        payload["history"] = history[-8:]
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            elapsed = time.time() - t0
            body = json.loads(resp.read().decode("utf-8"))
            return {
                "question": question,
                "history": history or [],
                "answer": body.get("answer", ""),
                "sources": body.get("sources", []),
                "suggested_questions": body.get("suggested_questions", []),
                "latency_sec": round(elapsed, 3),
                "status_code": resp.status
            }
    except urllib.error.HTTPError as e:
        elapsed = time.time() - t0
        return {
            "question": question,
            "history": history or [],
            "error": str(e),
            "body": e.read().decode("utf-8", errors="ignore"),
            "latency_sec": round(elapsed, 3),
            "status_code": e.code
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "question": question,
            "history": history or [],
            "error": str(e),
            "latency_sec": round(elapsed, 3),
            "status_code": 0
        }

def run_baseline():
    results = {}

    # 1. Small talk
    print("--- Running Small Talk ---")
    small_talk_queries = [
        "hello",
        "thank you",
        "good morning",
        "who are you",
        "idiot",
        "km cho majama ne",
        "bye"
    ]
    small_talk_results = []
    for q in small_talk_queries:
        print(f"Query: {q}")
        res = send_chat(q)
        print(f"  -> Ans: {res.get('answer', '')[:80].replace(chr(10), ' ')} (latency: {res['latency_sec']}s)")
        small_talk_results.append(res)
    results["small_talk"] = small_talk_results

    # 2. One conversation
    print("\n--- Running Multi-turn Conversation ---")
    conv_steps = [
        "What is the MBA first year fee?",
        "for year 2?",
        "year 2 subjects",
        "for bca?",
        "fees?"
    ]
    conv_history = []
    conv_results = []
    for q in conv_steps:
        print(f"Conversation Turn: {q}")
        res = send_chat(q, history=list(conv_history))
        print(f"  -> Ans: {res.get('answer', '')[:80].replace(chr(10), ' ')} (latency: {res['latency_sec']}s)")
        conv_results.append(res)
        conv_history.append({"role": "user", "content": q})
        conv_history.append({"role": "assistant", "content": res.get("answer", "")})
    results["conversation"] = conv_results

    # 3. Separately
    print("\n--- Running Separate Queries ---")
    separate_results = []

    # "What subjects are covered in the MBA program?"
    print("Query: What subjects are covered in the MBA program?")
    res = send_chat("What subjects are covered in the MBA program?")
    print(f"  -> Ans: {res.get('answer', '')[:80].replace(chr(10), ' ')}")
    separate_results.append(res)

    # "for mba" after "year 2 subjects"
    print("Query: for mba (after year 2 subjects)")
    # run year 2 subjects first to get realistic prior assistant turn
    res_y2 = send_chat("year 2 subjects")
    hist_for_mba = [
        {"role": "user", "content": "year 2 subjects"},
        {"role": "assistant", "content": res_y2.get("answer", "")}
    ]
    res_for_mba = send_chat("for mba", history=hist_for_mba)
    print(f"  -> Ans: {res_for_mba.get('answer', '')[:80].replace(chr(10), ' ')}")
    separate_results.append({
        "label": "for mba (after year 2 subjects)",
        "setup_turn": res_y2,
        "result": res_for_mba
    })

    other_queries = [
        "How do fees compare across Online BBA, BCA, MBA and MCA?",
        "What documents are required for Online BBA admission?",
        "Are e-books provided?",
        "How is the grading system structured?",
        "Do companies recruit online degree students?",
        "What if I forget my LMS password?"
    ]
    for q in other_queries:
        print(f"Query: {q}")
        res = send_chat(q)
        print(f"  -> Ans: {res.get('answer', '')[:80].replace(chr(10), ' ')} (latency: {res['latency_sec']}s)")
        separate_results.append(res)

    results["separate"] = separate_results

    # Save to CHANGES/round3_logs.json
    out_path = os.path.join("CHANGES", "round3_logs.json")
    data = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["before"] = results
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved before baseline results to {out_path}")

if __name__ == "__main__":
    run_baseline()
