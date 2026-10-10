"""Test interleaved multi-turn requests through HTTP API."""
import urllib.request
import json

URL = "http://127.0.0.1:8000/api/chat"

def send(question, history=None):
    payload = json.dumps({"question": question, "history": history or []}).encode("utf-8")
    req = urllib.request.Request(URL, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

# Chat 1: MBA
res1_turn1 = send("What is the MBA first year fee?")
h1 = [
    {"role": "user", "content": "What is the MBA first year fee?"},
    {"role": "assistant", "content": res1_turn1["answer"]}
]
res1_turn2 = send("for year 2?", history=h1)
def safe_str(s):
    return s.encode("ascii", errors="replace").decode("ascii")

print(f"Chat 1 (MBA for year 2?): {safe_str(res1_turn2['answer'][:120])}...")
print(f"Chat 1 sources: {[s.get('program') for s in res1_turn2.get('sources', [])]}")

# Chat 2: BCA
res2_turn1 = send("What is the eligibility for BCA?")
h2 = [
    {"role": "user", "content": "What is the eligibility for BCA?"},
    {"role": "assistant", "content": res2_turn1["answer"]}
]
res2_turn2 = send("for year 2?", history=h2)
print(f"Chat 2 (BCA for year 2?): {safe_str(res2_turn2['answer'][:120])}...")
print(f"Chat 2 sources: {[s.get('program') for s in res2_turn2.get('sources', [])]}")

assert res1_turn2["answer"] != res2_turn2["answer"], "Answers must not be shared between chats"
print("SUCCESS: HTTP interleaved multi-turn requests completely isolated!")
