"""Check rule R1 compliance:
No currency amounts (e.g. 75,000, 1,20,000), phone-like numbers, +91, or full test-question sentences
in backend/app/**/*.py and frontend/src/**.
"""
import os
import re

PATTERNS = [
    (re.compile(r"\b\d{1,3}(?:,\d{3})+\b"), "Formatted currency amount (e.g. 75,000)"),
    (re.compile(r"\+91"), "+91 country code"),
    (re.compile(r"\b[6-9]\d{9}\b"), "10-digit Indian phone number"),
    (re.compile(r"What is the total fee for the Online MBA programme\?", re.I), "Full test question sentence"),
    (re.compile(r"What is the duration of the Online BCA programme\?", re.I), "Full test question sentence"),
    (re.compile(r"How many semesters are there in the Online MCA programme\?", re.I), "Full test question sentence"),
]

def scan():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    targets = [
        os.path.join(root, "backend", "app"),
        os.path.join(root, "frontend", "src"),
    ]
    violations = []
    for target in targets:
        for r, _, files in os.walk(target):
            for f in files:
                if not f.endswith((".py", ".js", ".jsx", ".ts", ".tsx")):
                    continue
                path = os.path.join(r, f)
                rel_path = os.path.relpath(path, root)
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    for line_num, line in enumerate(fh, 1):
                        for pat, desc in PATTERNS:
                            m = pat.search(line)
                            if m:
                                violations.append((rel_path, line_num, desc, m.group(0), line.strip()))
    return violations

if __name__ == "__main__":
    v = scan()
    if not v:
        print("R1 CHECK PASSED: 0 violations found in backend/app/**/*.py and frontend/src/**")
    else:
        print(f"R1 CHECK FAILED: {len(v)} violations found:")
        for rel_path, line_num, desc, val, line in v:
            safe_line = line.encode("ascii", errors="replace").decode("ascii")
            print(f"  {rel_path}:{line_num} [{desc} -> {val}]: {safe_line}")
        exit(1)
