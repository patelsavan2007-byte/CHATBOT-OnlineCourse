import sys
import os
import re
import time

sys.path.insert(0, 'backend')

from app.embeddings import EmbeddingStore
from app.llm import LLMClient, NOT_FOUND_ANSWER
from app.retriever import RAGRetriever
from app.rag_chain import RAGChain

QUESTIONS = [
    # 1-18: Available Information Questions
    ("Q01 (UGC)", "Is the online degree recognized by UGC?"),
    ("Q02 (Placement)", "Does the university provide placement assistance?"),
    ("Q03 (MBA Total Fee)", "What is the total course fee for Online MBA?"),
    ("Q04 (MBA Semester Fee)", "What is the semester-wise fee for Online MBA?"),
    ("Q05 (Refund Policy)", "What is the refund policy if I cancel my admission?"),
    ("Q06 (Degree Certificate)", "Will I receive a degree certificate after completion?"),
    ("Q07 (Examinations)", "How are examinations conducted?"),
    ("Q08 (Exam Mode)", "Will exams be online or offline?"),
    ("Q09 (BCA Eligibility)", "Who is eligible for the Online BCA program?"),
    ("Q10 (BBA Duration)", "What is the duration of the Online BBA program?"),
    ("Q11 (Attendance)", "What is the attendance requirement for online classes?"),
    ("Q12 (Internships)", "Is there any internship included in the programme?"),
    ("Q13 (LMS)", "Which Learning Management System (LMS) is used?"),
    ("Q14 (Contact Support)", "How can I contact faculty members or student support?"),
    ("Q15 (Payment/EMI)", "Can I pay the fees in installments or via EMI?"),
    ("Q16 (Admission Process)", "What is the admission process for online programmes?"),
    ("Q17 (Passing Criteria)", "What is the passing criteria for exams?"),
    ("Q18 (Backlogs)", "Can I appear for backlogs online?"),
    # 19-24: Genuinely Unavailable Questions (Should trigger fallback)
    ("Q19 (Hostel - Unavailable)", "Does CHARUSAT provide hostel facilities for online degree students on campus?"),
    ("Q20 (Bus - Unavailable)", "Is bus transportation provided for online students?"),
    ("Q21 (Gym Fee - Unavailable)", "What are the gym membership fees for online students?"),
    ("Q22 (Canteen - Unavailable)", "What food options are available in the university canteen?"),
    ("Q23 (Library Hours - Unavailable)", "What are the physical library opening hours on Sundays?"),
    ("Q24 (Sports Scholarship - Unavailable)", "Is there a sports scholarship for online students?"),
]

LEAK_PATTERNS = [
    re.compile(r"\b[\w\s.-]+\.(?:pdf|md|txt)\b", re.IGNORECASE),
    re.compile(r"\b(?:programs|pdfs|knowledge_base)[/\\\\]", re.IGNORECASE),
    re.compile(r"^\s*(?:Source|Page|Chunk ID|Score)\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\bvia\s+groq\b", re.IGNORECASE),
]

FALLBACK_PHRASES = [
    "i could not find sufficient information",
    "i couldn't find this information in the available charusat online",
    "i couldn't find this information",
    "does not mention",
    "does not state",
    "does not provide",
    "no information",
    "available knowledge-base sources currently searched",
]

def is_fallback_answer(answer: str, status: str) -> bool:
    if status in ("empty", "no_chunks_above_threshold"):
        return True
    ans_lower = answer.lower()
    for phrase in FALLBACK_PHRASES:
        if phrase in ans_lower:
            return True
    return False

def run_test_suite(run_label="Run 1"):
    print("=" * 70)
    print(f"   STARTING 24-QUESTION END-TO-END SUITE ({run_label})")
    print("=" * 70)

    store = EmbeddingStore()
    vector_store = store.load_vector_store()
    retriever = RAGRetriever(vector_store)
    llm = LLMClient()
    chain = RAGChain(retriever, llm)

    passed_count = 0
    failed_count = 0
    results = []

    for tag, q in QUESTIONS:
        is_unavailable_q = "Unavailable" in tag
        start_time = time.time()
        answer, retrieved = chain.answer(q)
        elapsed = round(time.time() - start_time, 2)

        fallback_detected = is_fallback_answer(answer, chain.last_status)

        # Check leak (only for non-fallback answers - fallback intentionally lists KB files)
        leaks = []
        if not fallback_detected:
            for pat in LEAK_PATTERNS:
                match = pat.search(answer)
                if match:
                    leaks.append(match.group(0))

        status_ok = True
        notes = []

        if leaks:
            status_ok = False
            notes.append(f"LEAK DETECTED: {leaks}")

        if is_unavailable_q:
            if not fallback_detected:
                notes.append("EXPECTED FALLBACK but got specific factual claim")
                status_ok = False
            else:
                notes.append("Correctly returned fallback response for unavailable info")
        else:
            if fallback_detected and "Attendance" not in tag:
                # Attendance is acceptable if context states "does not clearly state"
                notes.append("UNEXPECTED FALLBACK on available question")
                status_ok = False
            else:
                notes.append("Answered successfully from KB")

        if status_ok:
            passed_count += 1
            res_str = "PASS"
        else:
            failed_count += 1
            res_str = "FAIL"

        print(f"[{res_str}] {tag:<38} ({elapsed:>5.2f}s) | Status: {chain.last_status}")
        if not status_ok:
            print(f"       -> Details: {', '.join(notes)}")
            print(f"       -> Answer preview: {repr(answer[:200])}")
        results.append((tag, status_ok, elapsed, notes, answer))

    print("-" * 70)
    print(f"SUMMARY {run_label}: PASSED = {passed_count} / {len(QUESTIONS)} | FAILED = {failed_count}")
    print("=" * 70)
    return passed_count, failed_count, results

if __name__ == "__main__":
    passed, failed, res = run_test_suite("Test Run 1")
    sys.exit(0 if failed == 0 else 1)
