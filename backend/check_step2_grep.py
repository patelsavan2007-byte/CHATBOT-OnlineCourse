import os
import re

PATTERNS = [
    (re.compile(r"[\u0900-\u097F]"), "Devanagari characters"),
    (re.compile(r"[\u0A80-\u0AFF]"), "Gujarati characters"),
    (re.compile(r"hindi", re.I), "'hindi'"),
    (re.compile(r"gujarati", re.I), "'gujarati'"),
    (re.compile(r"multilingual", re.I), "'multilingual'"),
    (re.compile(r"hinglish", re.I), "'hinglish'"),
    (re.compile(r"detect_language"), "'detect_language'"),
    (re.compile(r"SUPPORTED_LANGUAGES"), "'SUPPORTED_LANGUAGES'"),
]

EXCLUDE_DIRS = {
    ".venv", "venv", "node_modules", "knowledge_base", "CHANGES", "REPORTS",
    "vector_db", "chroma_db", ".git", ".idea", "__pycache__"
}

def scan_dir(base_dir):
    matches = []
    for root, dirs, files in os.walk(base_dir):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not any(ex in os.path.join(root, d) for ex in EXCLUDE_DIRS)]
        for f in files:
            if f.endswith((".pyc", ".png", ".jpg", ".bin", ".sqlite3", ".log", ".jsonl")):
                continue
            # Also ignore the checker script itself and past round test scripts if needed, but let's check everything
            if f == "check_step2_grep.py":
                continue
            path = os.path.join(root, f)
            # check exclude dirs in full path
            parts = set(os.path.normpath(path).split(os.sep))
            if parts & EXCLUDE_DIRS:
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    for line_no, line in enumerate(fh, 1):
                        for pat, desc in PATTERNS:
                            if pat.search(line):
                                matches.append((path, line_no, desc, line.strip()))
            except Exception as e:
                pass
    return matches

def main():
    root = os.path.abspath(".")
    targets = [
        os.path.join(root, "backend"),
        os.path.join(root, "frontend", "src"),
    ]
    readmes = [os.path.join(root, f) for f in os.listdir(root) if f.lower().startswith("readme")]

    all_matches = []
    for t in targets:
        if os.path.exists(t):
            all_matches.extend(scan_dir(t))
    for r in readmes:
        if os.path.exists(r):
            try:
                with open(r, "r", encoding="utf-8", errors="ignore") as fh:
                    for line_no, line in enumerate(fh, 1):
                        for pat, desc in PATTERNS:
                            if pat.search(line):
                                all_matches.append((r, line_no, desc, line.strip()))
            except Exception:
                pass

    print(f"Total forbidden pattern matches found: {len(all_matches)}")
    for path, line_no, desc, text in all_matches:
        rel = os.path.relpath(path, root)
        print(f"  {rel}:{line_no} [{desc}] -> {text[:100]}")

if __name__ == "__main__":
    main()
