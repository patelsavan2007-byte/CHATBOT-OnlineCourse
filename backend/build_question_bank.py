"""Build Question Bank from CHANGES/Online program questions.docx.

Parses docx using zipfile and XML (no python-docx dependency).
Outputs structured question items to backend/app/data/question_bank.json.
Kept in repository per Step 8 instructions.
"""
from __future__ import annotations

import html
import json
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Any, Dict, List

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DOCX_PATH = os.path.join(PROJECT_ROOT, "CHANGES", "Online program questions.docx")
OUTPUT_DIR = os.path.join(BACKEND_DIR, "app", "data")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "question_bank.json")

CATEGORIES = [
    "General Questions",
    "Fees Related Questions",
    "Academic Questions",
    "Technical Questions",
    "Career & Placement Questions",
    "Admission Questions",
    "Student Support Questions",
]


def determine_topics(cat: str, text: str) -> List[str]:
    """Map category and question text to standardized turn topics."""
    t_lower = text.lower()
    topics: List[str] = []

    if any(k in t_lower for k in ["fee", "cost", "installment", "refund", "payment", "pay", "charge"]):
        topics.append("fees")
    if any(k in t_lower for k in ["subject", "syllabus", "curriculum", "course content", "topics"]):
        topics.append("subjects/syllabus")
    if any(k in t_lower for k in ["specializ", "elective", "stream"]):
        topics.append("specializations")
    if any(k in t_lower for k in ["eligib", "criteria", "qualif"]):
        topics.append("eligibility")
    if any(k in t_lower for k in ["admission", "apply", "document", "last date", "deadline", "procedure"]):
        topics.append("admission")
    if any(k in t_lower for k in ["duration", "semester", "credit", "how long"]):
        topics.append("duration/semesters/credits")
    if any(k in t_lower for k in ["exam", "grade", "grading", "evaluation", "test", "assessment", "score"]):
        topics.append("exams/grading")
    if "refund" in t_lower:
        topics.append("refund")
    if any(k in t_lower for k in ["lms", "portal", "login", "password", "device", "internet", "technical", "app", "software", "browser"]):
        topics.append("lms/technical")
    if any(k in t_lower for k in ["placement", "job", "career", "recruit", "company", "companies", "industry", "hire"]):
        topics.append("placement/career")
    if any(k in t_lower for k in ["support", "mentor", "contact", "help", "coordinator", "faculty", "assistance"]):
        topics.append("support/contact")

    if not topics:
        if "General" in cat:
            topics.append("general")
        elif "Academic" in cat:
            topics.append("academic")
        elif "Admission" in cat:
            topics.append("admission")
        elif "Fees" in cat:
            topics.append("fees")
        elif "Technical" in cat:
            topics.append("lms/technical")
        elif "Support" in cat:
            topics.append("support/contact")
        elif "Career" in cat:
            topics.append("placement/career")

    return list(dict.fromkeys(topics))


def is_programme_specific(text: str) -> bool:
    """Determine whether a question targets programme-varying facts."""
    t_lower = text.lower()
    return any(
        k in t_lower
        for k in [
            "fee", "subject", "syllabus", "specializ", "eligib", "duration",
            "semester", "credit", "course structure", "curriculum", "stream"
        ]
    )


def build_question_bank() -> List[Dict[str, Any]]:
    """Read docx XML, parse questions and metadata, and save question_bank.json."""
    if not os.path.exists(DOCX_PATH):
        raise FileNotFoundError(f"Source document not found: {DOCX_PATH}")

    z = zipfile.ZipFile(DOCX_PATH)
    xml_content = z.read("word/document.xml")
    tree = ET.fromstring(xml_content)

    texts: List[str] = []
    for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        t = "".join(node.text for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text)
        if t.strip():
            texts.append(html.unescape(t.strip()))

    curr_cat = "General Questions"
    questions: List[Dict[str, Any]] = []
    q_idx = 1

    for t in texts:
        matched_cat = next((c for c in CATEGORIES if t.lower().startswith(c.lower())), None)
        if matched_cat:
            curr_cat = matched_cat
        else:
            q_id = f"Q{q_idx:02d}"
            topics = determine_topics(curr_cat, t)
            prog_spec = is_programme_specific(t)
            questions.append({
                "id": q_id,
                "text": t,
                "category": curr_cat,
                "topics": topics,
                "programme_specific": prog_spec,
            })
            q_idx += 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print(f"Successfully generated question bank with {len(questions)} questions at:\n  {OUTPUT_PATH}")
    return questions


if __name__ == "__main__":
    build_question_bank()
