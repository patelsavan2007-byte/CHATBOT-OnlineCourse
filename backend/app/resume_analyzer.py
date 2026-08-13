"""Resume analyzer for SkillForge AI.

Extracts a StudentProfile from uploaded PDF/DOCX resumes using:
1. pypdf/pymupdf for text extraction
2. Gemini for intelligent structured extraction

Never invents skills or projects — only extracts what is explicitly
present in the resume text.
"""
from __future__ import annotations

import io
from typing import Optional

from app.gemini_client import get_gemini_client
from app.schemas import StudentProfile, ProfileSource
from app.utils import logger, print_info, print_warning

try:
    import fitz  # pymupdf
    HAS_PYMUPDF = True
except ImportError:
    fitz = None
    HAS_PYMUPDF = False

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    PdfReader = None
    HAS_PYPDF = False


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text content from a PDF file.

    Tries pymupdf first (better quality), falls back to pypdf.
    """
    text = ""

    # Try pymupdf first
    if HAS_PYMUPDF:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            pages = []
            for page in doc:
                pages.append(page.get_text())
            doc.close()
            text = "\n\n".join(pages).strip()
            if text:
                return text
        except Exception as exc:
            logger.warning("pymupdf extraction failed: %s", exc)

    # Fallback to pypdf
    if HAS_PYPDF:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            pages = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
            text = "\n\n".join(pages).strip()
            if text:
                return text
        except Exception as exc:
            logger.warning("pypdf extraction failed: %s", exc)

    return text


RESUME_EXTRACTION_PROMPT = """You are an expert resume analyzer. Extract structured information from the following resume text.

CRITICAL RULES:
1. ONLY extract information that is EXPLICITLY stated in the resume.
2. DO NOT invent, assume, or fabricate any skills, projects, or experience.
3. If a section is missing or empty, return an empty list for that field.
4. Extract technologies mentioned in project descriptions and work experience.
5. Be thorough — capture ALL skills, technologies, projects, education, and certifications mentioned.

Resume text:
---
{resume_text}
---

Return a JSON object with these fields:
{{
  "skills": ["list of skills explicitly mentioned"],
  "technologies": ["list of technologies, frameworks, tools mentioned"],
  "projects": [
    {{
      "name": "project name",
      "description": "brief description",
      "technologies": ["tech used"],
      "url": "URL if mentioned, null otherwise",
      "source": "resume"
    }}
  ],
  "education": [
    {{
      "institution": "school/university name",
      "degree": "degree type",
      "field": "field of study",
      "year": "graduation year or expected",
      "gpa": "GPA if mentioned"
    }}
  ],
  "experience": [
    {{
      "company": "company name",
      "role": "job title",
      "duration": "time period",
      "description": "brief description of responsibilities",
      "technologies": ["tech used in this role"]
    }}
  ],
  "certifications": [
    {{
      "name": "certification name",
      "issuer": "issuing organization",
      "year": "year obtained",
      "url": "URL if available"
    }}
  ],
  "achievements": ["list of notable achievements, awards, honors"],
  "links": ["any URLs found: GitHub, LinkedIn, portfolio, etc."],
  "strengths": ["key strengths derived from resume content"],
  "summary": "2-3 sentence professional summary based on the resume",
  "confidence": "high if resume has good detail, medium if sparse, low if very limited"
}}"""


def analyze_resume(file_bytes: bytes) -> Optional[StudentProfile]:
    """Analyze a resume PDF and return a StudentProfile.

    Parameters
    ----------
    file_bytes : bytes
        Raw bytes of the uploaded PDF file.

    Returns
    -------
    StudentProfile or None
        Extracted profile, or None if extraction fails.
    """
    # Step 1: Extract text
    resume_text = extract_text_from_pdf(file_bytes)
    if not resume_text or len(resume_text.strip()) < 50:
        print_warning("[Resume] Insufficient text extracted from PDF")
        logger.warning("Resume text too short: %d chars", len(resume_text))
        return StudentProfile(
            source=ProfileSource.RESUME,
            confidence="low",
            extraction_notes="Resume contained insufficient readable text. The PDF may be image-based or empty.",
        )

    print_info(f"[Resume] Extracted {len(resume_text)} chars from PDF")

    # Step 2: Use Gemini for structured extraction
    client = get_gemini_client()
    if not client.is_available:
        # Fallback: basic text-based extraction without AI
        return _basic_text_extraction(resume_text)

    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=resume_text[:8000])

    result = client.generate_json(prompt, response_model=StudentProfile, temperature=0.1)

    if result is None:
        logger.warning("Gemini resume extraction returned None, using basic extraction")
        return _basic_text_extraction(resume_text)

    try:
        profile = StudentProfile.model_validate(result)
        profile.source = ProfileSource.RESUME
        print_info(f"[Resume] Extracted {len(profile.skills)} skills, {len(profile.projects)} projects")
        return profile
    except Exception as exc:
        logger.error("Failed to validate resume profile: %s", exc)
        return _basic_text_extraction(resume_text)


def _basic_text_extraction(text: str) -> StudentProfile:
    """Basic keyword-based extraction when Gemini is unavailable.

    This is a simple fallback — it will not be as accurate as Gemini
    but provides some structured data.
    """
    import re

    # Common tech keywords to look for
    tech_keywords = [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
        "Ruby", "PHP", "Swift", "Kotlin", "R", "MATLAB", "Scala",
        "React", "Angular", "Vue", "Next.js", "Node.js", "Express", "Django",
        "Flask", "FastAPI", "Spring", "Rails",
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Firebase",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "Linux",
        "TensorFlow", "PyTorch", "Pandas", "NumPy", "Scikit-learn",
        "HTML", "CSS", "SASS", "Tailwind", "Bootstrap",
        "REST", "GraphQL", "gRPC", "WebSocket",
        "CI/CD", "Jenkins", "GitHub Actions", "Terraform",
    ]

    text_lower = text.lower()
    found_skills = []
    for keyword in tech_keywords:
        # Match whole words only
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            found_skills.append(keyword)

    # Extract links
    urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)

    return StudentProfile(
        skills=found_skills,
        technologies=found_skills,
        links=urls[:10],
        source=ProfileSource.RESUME,
        confidence="low",
        extraction_notes="Extracted using basic keyword matching (Gemini unavailable). Results may be incomplete.",
        summary=text[:200].strip() if text else "",
    )
