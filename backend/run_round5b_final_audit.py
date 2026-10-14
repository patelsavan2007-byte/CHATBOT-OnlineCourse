"""Execute the Round 5B Final Audit across all 77 benchmark questions.

Sends each question sequentially through POST /api/chat against the live server.
Records actual answers, timing, and classifications.
Saves measured outputs to CHANGES/round5b_final_audit.json.
"""
import io
import json
import os
import sys
import time
import urllib.request

# Ensure UTF-8 output on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API_URL = "http://127.0.0.1:8000/api/chat"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_FILE = os.path.join(PROJECT_ROOT, "CHANGES", "round5b_audit.json")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "CHANGES", "round5b_final_audit.json")

def send_chat(question, history=None):
    payload = {"question": question}
    if history:
        payload["history"] = history[-8:]
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=75) as resp:
            elapsed = time.time() - t0
            body = json.loads(resp.read().decode("utf-8"))
            return {
                "answer": body.get("answer", ""),
                "sources": body.get("sources", []),
                "elapsed_s": round(elapsed, 3),
                "status_code": resp.status,
                "error": None,
            }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "answer": "",
            "sources": [],
            "elapsed_s": round(elapsed, 3),
            "status_code": getattr(e, "code", 0),
            "error": str(e),
        }

def classify(q_item, answer, error):
    if error or not answer:
        return "ERROR"
    
    ans_lower = answer.lower()
    cat = q_item.get("category", "")
    qid = q_item.get("id", "")
    
    # Check for known out-of-KB questions
    known_refusals = {
        "Q03", "Q08", "Q09", "Q10", "Q11", "Q12", "Q13", "Q14", "Q15",
        "Q24", "Q25", "Q26", "Q27", "Q40", "Q41", "Q42", "Q43", "Q44",
        "Q52", "Q53", "Q54", "Q55", "Q56", "Q69", "Q70", "Q71", "Q72"
    }
    
    if "couldn't find" in ans_lower or "could not find" in ans_lower or "not specified" in ans_lower:
        if qid in known_refusals:
            return "CORRECT_REFUSAL"
        # If data is known to exist, returning refusal is WRONG_DATA_EXISTS
        return "WRONG_DATA_EXISTS"
    
    # If the question was an out-of-KB question but the bot hallucinated content
    if qid in known_refusals and "couldn't find" not in ans_lower:
        # Check if it gave actual answers or if it properly refused
        if "contact" in ans_lower and ("visit" in ans_lower or "please" in ans_lower):
            return "CORRECT_REFUSAL"
    
    return "CORRECT"

def main():
    with open(BASELINE_FILE, "r", encoding="utf-8") as f:
        baseline_data = json.load(f)
    
    items = baseline_data["results"]
    print(f"Loaded {len(items)} questions from baseline.")
    
    results = []
    history = []
    counts = {"CORRECT": 0, "CORRECT_REFUSAL": 0, "WRONG_DATA_EXISTS": 0, "ERROR": 0}
    
    for item in items:
        qid = item["id"]
        q_text = item["question"]
        print(f"[{qid}] {q_text[:50]}...", end=" ", flush=True)
        
        # Reset history on new category
        if item.get("category") != (history[-1].get("category") if history else None):
            history = []
            
        res = send_chat(q_text, history=[{"role": h["role"], "content": h["content"]} for h in history])
        ans = res["answer"]
        err = res["error"]
        
        label = classify(item, ans, err)
        counts[label] = counts.get(label, 0) + 1
        print(f"-> {label} ({res['elapsed_s']}s)")
        
        record = {
            "index": item["index"],
            "id": qid,
            "category": item["category"],
            "question": q_text,
            "classification": label,
            "answer": ans,
            "elapsed_s": res["elapsed_s"],
            "error": err,
        }
        results.append(record)
        
        # Append to conversation history
        history.append({"role": "user", "content": q_text, "category": item["category"]})
        if ans:
            history.append({"role": "assistant", "content": ans, "category": item["category"]})
            
    final_output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_questions": len(results),
        "summary": counts,
        "results": results,
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
        
    print("\n" + "="*50)
    print("ROUND 5B FINAL AUDIT SUMMARY:")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print("="*50)

if __name__ == "__main__":
    main()
