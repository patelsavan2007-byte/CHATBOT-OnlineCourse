"""Topic lexicon loader and multi-label scorer."""
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

LEXICON_PATH = Path(__file__).resolve().parent / "data" / "topic_lexicon.json"

_LEXICON_CACHE: Optional[Dict[str, Any]] = None
_COMPILED_PATTERNS: Optional[List[Tuple[str, re.Pattern, int, str, bool]]] = None
_ALL_KEYWORDS_RE: Optional[re.Pattern] = None

def load_lexicon() -> Dict[str, Any]:
    global _LEXICON_CACHE
    if _LEXICON_CACHE is None:
        if not LEXICON_PATH.exists():
            return {"topics": {}}
        with open(LEXICON_PATH, "r", encoding="utf-8") as f:
            _LEXICON_CACHE = json.load(f)
    return _LEXICON_CACHE

def _compile_patterns():
    global _COMPILED_PATTERNS, _ALL_KEYWORDS_RE
    if _COMPILED_PATTERNS is not None:
        return
    lex = load_lexicon()
    topics = lex.get("topics", {})
    compiled = []
    all_stems = set(["bca", "bba", "mba", "mca", "charusat", "online"])
    
    for topic_id, info in topics.items():
        stems = info.get("stems", [])
        synonyms = info.get("synonyms", [])
        contact = info.get("contact_service", "Admissions")
        is_prog_indep = info.get("programme_independent", False)
        
        # Compile each stem
        for stem in stems:
            # Clean stem for word boundary if not regex
            pat_str = r"\b" + stem if not stem.startswith(r"\b") else stem
            if not pat_str.endswith(r"\b") and not pat_str.endswith(r"\w*"):
                pat_str = pat_str + r"\b"
            pat = re.compile(pat_str, re.I)
            # Weight: length of pattern as specificity proxy
            weight = len(stem.replace("\\s+", " ").replace("\\b", "").replace("\\w*", ""))
            compiled.append((topic_id, pat, weight, contact, is_prog_indep))
            all_stems.add(stem.replace(r"\s+", " ").replace(r"\b", "").replace(r"\w*", ""))
            
        for syn in synonyms:
            pat = re.compile(r"\b" + re.escape(syn) + r"\b", re.I)
            compiled.append((topic_id, pat, len(syn) + 5, contact, is_prog_indep))
            all_stems.add(syn)
            
    _COMPILED_PATTERNS = compiled
    
    # Combined regex for course keyword detection
    clean_stems = [re.escape(s) for s in all_stems if s and len(s) > 2]
    # Add common course terms
    clean_stems.extend(["bca", "bba", "mba", "mca", "charusat", "online\\s+degree", "semester", "course", "programme", "program"])
    joined = "|".join(sorted(set(clean_stems), key=len, reverse=True))
    _ALL_KEYWORDS_RE = re.compile(r"\b(?:" + joined + r")\b", re.I)

def score_topics(text: str) -> List[Tuple[str, int, str, bool]]:
    """Score all topics against text. Returns sorted (topic_id, score, contact_service, is_independent)."""
    _compile_patterns()
    scores: Dict[str, Tuple[int, str, bool]] = {}
    
    # Entrance exam special guard: if entrance test is mentioned, prevent exams_grading from winning
    is_entrance = bool(re.search(r"\bentrance\b", text, re.I))
    
    for topic_id, pat, weight, contact, is_indep in _COMPILED_PATTERNS:
        matches = pat.findall(text)
        if matches:
            # Special case: don't let generic exam patterns score on entrance exam queries
            if is_entrance and topic_id == "exams_grading":
                continue
            curr_score = scores.get(topic_id, (0, contact, is_indep))[0]
            scores[topic_id] = (curr_score + weight * len(matches), contact, is_indep)
            
    ranked = sorted([(k, v[0], v[1], v[2]) for k, v in scores.items()], key=lambda x: x[1], reverse=True)
    return ranked

def detect_primary_topic(text: str) -> str:
    """Return the highest scoring topic or 'general'."""
    ranked = score_topics(text)
    if ranked:
        return ranked[0][0]
    return "general"

def get_topic_contact_service(topic: str) -> str:
    """Return the designated contact service for a topic."""
    lex = load_lexicon()
    return lex.get("topics", {}).get(topic, {}).get("contact_service", "Admissions")

def is_topic_programme_independent(topic: str) -> bool:
    """Check if a topic is programme-independent."""
    lex = load_lexicon()
    return lex.get("topics", {}).get(topic, {}).get("programme_independent", False)

def get_course_keywords_regex() -> re.Pattern:
    """Return regex matching any course/topic keyword from lexicon."""
    _compile_patterns()
    return _ALL_KEYWORDS_RE
