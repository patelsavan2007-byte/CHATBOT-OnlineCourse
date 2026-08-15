"""LLM client using the modern ``google.genai`` SDK.

Responsibilities
----------------
* discover candidate Gemini models and keep a working list;
* generate answers with retries and exponential backoff;
* classify failures into typed errors so callers can distinguish a
  retrieval problem from an LLM problem, an API quota limit, a timeout or
  any other API error;
* produce a deterministic, structured local answer from the retrieved
  evidence when the API is unavailable (no key, quota exhausted, timeout,
  model retired, ...) so the chatbot always answers something useful.

The local fallback never performs arithmetic the source document does not
state, and it never dumps raw chunk text: it extracts concrete claims using
the same configurable taxonomy as conflict detection (see ``app.conflict``).
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None


try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    Groq = None
    HAS_GROQ = False

from app import config
from app.conflict import extract_claims, focus_attributes, format_conflict_notice
from app.utils import logger, print_info, print_warning

NOT_FOUND_ANSWER = (
    "I couldn't find this information in the available CHARUSAT Online "
    "Programme information. You may contact the university for the latest details."
)


def get_available_knowledge_sources() -> List[str]:
    """Return the currently available knowledge-base files, relative to the knowledge base root."""
    root = Path(config.KNOWLEDGE_BASE_DIR)
    if not root.exists():
        return []

    files: List[str] = []
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {'.md', '.pdf', '.txt'}:
            continue
        if any(part == '__pycache__' for part in path.parts):
            continue
        files.append(path.relative_to(root).as_posix())
    return files


def build_not_found_answer() -> str:
    """Return a professional fallback that lists the source files actually available to the chatbot."""
    sources = get_available_knowledge_sources()
    lines = [
        "I could not find sufficient information in the available university knowledge base for this query.",
        "",
        "Available knowledge-base sources currently searched:",
    ]
    if sources:
        lines.extend(f"- {source}" for source in sources)
    else:
        lines.append("- No knowledge-base files are currently available.")
    return "\n".join(lines)


_INTERNAL_REF_RE = re.compile(
    r"^[ 	]*(?:Source|Page|Chunk ID|Score|Content Type|Document Type|Programme)\s*:.*$",
    re.IGNORECASE | re.MULTILINE,
)
_SOURCE_AT_END_RE = re.compile(r"[ 	]*Source\s*:\s*[^\n]*$", re.IGNORECASE)
_FILE_PATH_RE = re.compile(
    r"\b(?:programs|pdfs|knowledge_base)[/\\][^\n\r,;:()]+\.(?:md|pdf|txt|docx)\b",
    re.IGNORECASE,
)
_SPECIFIC_FILES_RE = re.compile(
    r"\b(?:PPR_Online\s+(?:BBA|BCA|MBA|MCA)|Fees\s+Refund\s+Policy|ciqa|feedback|home|mandatory-disclosures|privacy-policy|terms-conditions|contact|online_bba|online_bca|online_mba|online_mca)(?:\.(?:pdf|md|txt))?\b",
    re.IGNORECASE,
)
_BARE_FILE_RE = re.compile(r"\b[\w\s.-]+\.(?:md|pdf|txt|docx)\b", re.IGNORECASE)
_AS_PER_LEFTOVER_RE = re.compile(
    r"\b(?:as\s+per|according\s+to|stated\s+in|mentioned\s+in|in\s+the\s+document|as\s+seen\s+in)\b",
    re.IGNORECASE,
)
_PAGE_REF_RE = re.compile(r"\(?\bpage\s+\d+\b\)?", re.IGNORECASE)
_VENDOR_RE = re.compile(r"\b(?:via|generated\s+by)\s+(?:groq|gemini)\b", re.IGNORECASE)
_RESOLVED_RE = re.compile(r"^(?:resolved|retrieved|search|source|sources)\s*[:\-].*$", re.IGNORECASE | re.MULTILINE)
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def strip_internal_references(text: str) -> str:
    """Remove source/page/score references from an answer before display.

    The LLM is instructed never to mention internal details, but the
    deterministic fallback and stubborn models occasionally echo them. This
    sanitizer removes the common shapes so the production UI never shows
    source files, page numbers, chunk IDs or scores.
    """
    if not text:
        return text
    cleaned = _INTERNAL_REF_RE.sub("", text)
    cleaned = _SOURCE_AT_END_RE.sub("", cleaned)
    cleaned = _FILE_PATH_RE.sub("", cleaned)
    cleaned = _SPECIFIC_FILES_RE.sub("", cleaned)
    cleaned = _BARE_FILE_RE.sub("", cleaned)
    cleaned = _AS_PER_LEFTOVER_RE.sub("", cleaned)
    cleaned = _PAGE_REF_RE.sub("", cleaned)
    cleaned = _VENDOR_RE.sub("", cleaned)
    cleaned = _RESOLVED_RE.sub("", cleaned)
    cleaned = re.sub(r"\b(?:via|generated\s+by)\s+(?:groq|gemini)\b.*$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\[\s*\]", "", cleaned)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"^[ 	]*[,.-]\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"[ 	]{2,}", " ", cleaned)
    cleaned = _MULTI_BLANK_RE.sub("\n\n", cleaned)

    lines = cleaned.split("\n")
    cleaned_lines = []
    for line in lines:
        l = line.strip()
        if l and l[0].islower():
            l = l[0].upper() + l[1:]
        cleaned_lines.append(l)
    return "\n".join(cleaned_lines).strip()


class LLMStatus:
    """Generation status returned alongside every answer."""

    LLM = "gemini"                   # answer generated by the Gemini API
    GEMINI = "gemini"                # alias for Gemini answer
    GROQ = "groq"                    # answer generated by Groq fallback tier
    FALLBACK = "fallback"         # deterministic local generation (no key/model)
    QUOTA = "quota"               # API quota exhausted -> local fallback used
    TIMEOUT = "timeout"           # request timed out -> local fallback used
    GENERATION_ERROR = "generation_error"  # empty/invalid model output -> fallback used
    API_ERROR = "api_error"       # any other API failure -> fallback used
    EMPTY = "empty"               # no evidence found at all


class RetrievalError(RuntimeError):
    """Raised when evidence cannot be retrieved from the knowledge base."""


class LLMGenerationError(RuntimeError):
    """Base error for LLM generation failures."""


class APIQuotaError(LLMGenerationError):
    """API quota/rate limit exceeded (HTTP 429, RESOURCE_EXHAUSTED)."""


class LLMTimeoutError(LLMGenerationError):
    """Generation request timed out."""


class APIAccessError(LLMGenerationError):
    """Any other API access failure (auth, unavailable model, 5xx, ...)."""

    def __init__(self, message: str, *, unavailable: bool = False) -> None:
        super().__init__(message)
        self.unavailable = unavailable


class LLMClient:
    """Generates answers with Gemini models, Groq fallback tier, and deterministic local fallback."""

    def __init__(self) -> None:
        self.api_key = config.get_api_key()
        self.groq_api_key = config.get_groq_api_key()
        self._client: Optional[genai.Client] = None
        self._groq_client: Optional[Groq] = None
        self._gen_config = None
        self._working_models: List[str] = []
        self._quota_exhausted = False
        self._cooldown_until = 0.0
        self._last_status = LLMStatus.FALLBACK
        self._initialize()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _initialize(self) -> None:
        if self.groq_api_key and HAS_GROQ:
            try:
                self._groq_client = Groq(api_key=self.groq_api_key)
                print_info(f"Groq client initialised as PRIMARY LLM (model: {config.GROQ_MODEL}).")
                logger.info("Groq client initialised as primary LLM: %s", config.GROQ_MODEL)
            except Exception as exc:
                logger.error("Failed to initialise Groq client: %s", exc)
                self._groq_client = None

        if not self._groq_client:
            print_warning("[WARNING] GROQ_API_KEY is missing or invalid in environment. Using local fallback.")
            logger.warning("Groq client unavailable; using local fallback")

    def _discover_models(self) -> List[str]:
        """Disabled for Groq primary deployment."""
        return []

    # ------------------------------------------------------------------
    # Generation
    # Primary: Groq API (llama-3.3-70b-versatile) -> Local Fallback
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        *,
        context_chunks: Optional[List[Tuple[str, Dict[str, object]]]] = None,
        conflicts: Optional[List[Dict[str, object]]] = None,
    ) -> Tuple[str, str]:
        """Generate an answer using Groq directly as primary LLM.

        Returns ``(text, status)`` where status is one of ``LLMStatus``.
        """
        groq_text = self._try_groq(prompt)
        if groq_text:
            self._last_status = LLMStatus.GROQ
            return strip_internal_references(groq_text), LLMStatus.GROQ

        logger.warning("Groq API unavailable or failed; using local deterministic fallback")
        self._last_status = LLMStatus.FALLBACK
        return self._fallback_generate(prompt, context_chunks, conflicts), LLMStatus.FALLBACK

    def _try_groq(self, prompt: str) -> Optional[str]:
        """Attempt answer generation using Groq API.

        Tries the primary configured model (llama-3.3-70b-versatile) first.
        If a 429 rate limit or error occurs, automatically fails over to
        secondary Groq models (llama-3.1-8b-instant, mixtral-8x7b-32768, gemma2-9b-it)
        before ever resorting to deterministic fallback.
        """
        if not self._groq_client:
            if not self.groq_api_key or not HAS_GROQ:
                return None
            try:
                self._groq_client = Groq(api_key=self.groq_api_key)
            except Exception as exc:
                logger.error("Failed to initialise Groq client: %s", exc)
                return None

        # Tiered list of Groq models to try in order
        groq_models = [
            getattr(config, "GROQ_MODEL", "llama-3.3-70b-versatile"),
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]

        for model_name in groq_models:
            try:
                logger.info("Calling Groq API model: %s", model_name)
                response = self._groq_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "user", "content": prompt},
                    ],
                    temperature=config.LLM_TEMPERATURE,
                    max_tokens=1024,
                    timeout=config.GROQ_TIMEOUT,
                )
                if response.choices and len(response.choices) > 0:
                    text = response.choices[0].message.content
                    if text and text.strip():
                        print_info(f"Groq generation succeeded with model: {model_name}")
                        return text.strip()
                logger.warning("Groq API model %s returned an empty response", model_name)
            except Exception as exc:
                logger.warning("Groq API model %s failed (%s), trying failover model...", model_name, exc)
                continue

        logger.error("All Groq API models exhausted or failed")
        return None

    def _generate_once(self, model: str, prompt: str) -> str:
        attempt = 0
        while True:
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=self._gen_config,
                )
                text = self._extract_text(response)
                if not text or not text.strip():
                    raise LLMGenerationError("Model returned an empty response")
                return text.strip()
            except Exception as exc:  # noqa: BLE001 - classified below
                error = self._classify_error(exc)
                retryable = isinstance(error, (APIQuotaError, LLMTimeoutError))
                if retryable and attempt + 1 < config.LLM_MAX_RETRIES:
                    delay = config.LLM_RETRY_DELAY * (config.LLM_BACKOFF_FACTOR ** attempt)
                    logger.warning(
                        "Transient %s from %s; retrying in %.1fs",
                        type(error).__name__, model, delay,
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                raise error

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    @staticmethod
    def _error_code(exc: Exception) -> Optional[int]:
        code = getattr(exc, "code", None)
        if isinstance(code, int):
            return code
        value = getattr(code, "value", None)
        if isinstance(value, int):
            return value
        return None

    @classmethod
    def _classify_error(cls, exc: Exception) -> LLMGenerationError:
        code = cls._error_code(exc)
        err_str = str(exc).lower()

        if code == 429 or "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
            return APIQuotaError(str(exc))
        if code in (408, 504, 529):
            return LLMTimeoutError(str(exc))
        if any(
            phrase in err_str
            for phrase in (
                "deadline exceeded",
                "timed out",
                "timeout exceeded",
                "request timeout",
                "read timeout",
                "connect timeout",
                "connection timeout",
            )
        ):
            return LLMTimeoutError(str(exc))
        if (
            code in (403, 404, 401)
            or "permission_denied" in err_str
            or "not_found" in err_str
            or "no longer available" in err_str
            or "not found" in err_str
        ):
            unavailable = code == 404 or "no longer available" in err_str
            return APIAccessError(str(exc), unavailable=unavailable)
        return APIAccessError(str(exc), unavailable=False)

    @staticmethod
    def _status_for(error: Optional[Exception]) -> str:
        if isinstance(error, APIQuotaError):
            return LLMStatus.QUOTA
        if isinstance(error, LLMTimeoutError):
            return LLMStatus.TIMEOUT
        if isinstance(error, LLMGenerationError):
            return LLMStatus.GENERATION_ERROR
        return LLMStatus.API_ERROR

    @staticmethod
    def _extract_text(response: object) -> str:
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text

        parts: List[str] = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            if content is None:
                continue
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", "")
                if part_text:
                    parts.append(part_text)
        return "".join(parts)

    # ------------------------------------------------------------------
    # Deterministic local fallback
    # ------------------------------------------------------------------

    def _fallback_generate(
        self,
        prompt: str,
        context_chunks: Optional[List[Tuple[str, Dict[str, object]]]] = None,
        conflicts: Optional[List[Dict[str, object]]] = None,
    ) -> str:
        chunks, question = self._prepare_chunks(prompt, context_chunks)
        if not chunks:
            return NOT_FOUND_ANSWER

        output: List[str] = []
        if conflicts:
            output.append(format_conflict_notice(conflicts, include_locations=False))

        focused = focus_attributes(question)
        if focused:
            for attribute in focused:
                lines = self._extract_attribute(chunks, attribute)
                if lines:
                    output.extend(lines)
            if output:
                return "\n".join(output)

        return self._general_extract(chunks, question)

    def _prepare_chunks(
        self,
        prompt: str,
        context_chunks: Optional[List[Tuple[str, Dict[str, object]]]],
    ) -> Tuple[List[Tuple[str, Dict[str, object]]], str]:
        if context_chunks is not None:
            cleaned = [
                (content, metadata)
                for content, metadata in context_chunks
                if content and content.strip()
            ]
            return cleaned, self._extract_question(prompt)

        prefix = "Retrieved Context:\n"
        if prefix not in prompt:
            return [], ""
        rest = prompt.split(prefix, 1)[1]
        question = ""
        if "\n\nUser Question:\n" in rest:
            rest, question = rest.split("\n\nUser Question:\n", 1)

        chunks: List[Tuple[str, Dict[str, object]]] = []
        for block in re.split(r"\n\n---\n\n", rest):
            block = block.strip()
            if not block:
                continue
            metadata: Dict[str, object] = {}
            content_lines: List[str] = []
            for line in block.splitlines():
                stripped = line.strip()
                if stripped.startswith("Source:"):
                    metadata["source"] = stripped[len("Source:"):].strip()
                elif stripped.startswith("Page:"):
                    metadata["page"] = stripped[len("Page:"):].strip()
                elif stripped.startswith("Content Type:"):
                    metadata["content_type"] = stripped[len("Content Type:"):].strip()
                elif stripped.startswith("Document Type:"):
                    metadata["document_type"] = stripped[len("Document Type:"):].strip()
                elif stripped.startswith("Programme:"):
                    metadata["program_name"] = stripped[len("Programme:"):].strip()
                elif stripped.startswith(("Chunk ID:", "Score:")):
                    continue
                elif stripped.startswith("Content:"):
                    continue
                else:
                    content_lines.append(line)
            content = "\n".join(content_lines).strip()
            if content:
                chunks.append((content, metadata))
        return chunks, question.strip()

    @staticmethod
    def _extract_question(prompt: str) -> str:
        marker = "\n\nUser Question:\n"
        if marker in prompt:
            return prompt.split(marker, 1)[1].strip()
        return ""

    def _extract_attribute(
        self,
        chunks: List[Tuple[str, Dict[str, object]]],
        attribute: str,
    ) -> Optional[List[str]]:
        """Extract structured claims for one attribute from the evidence."""
        spec = config.ATTRIBUTE_TAXONOMY.get(attribute)
        if not spec:
            return None

        claims = []
        for content, metadata in chunks:
            for claim in extract_claims(content, metadata):
                if claim["attribute"] == attribute:
                    claims.append(claim)
        if not claims:
            return None

        label = spec.get("label", attribute)
        semantics = spec.get("semantics", "text")

        if semantics == "single":
            distinct = self._distinct_claim_groups(claims)
            if len(distinct) > 1:
                lines = [f'Note: The retrieved documents contain conflicting values for "{label}":']
                for claim in distinct:
                    lines.append(f"- {claim['value_text']}")
                return lines
            claim = claims[0]
            return [f"{label}: {claim['value_text']}"]

        if semantics == "set":
            seen = []
            for claim in claims:
                value = claim["value_text"]
                if value and not any(value == existing for existing in seen):
                    seen.append(value)
            if not seen:
                return None
            lines = [f"{label}:"]
            for value in seen[:12]:
                lines.append(f"- {value}")
            return lines

        claim = claims[0]
        return [f"{label}: {claim['value_text']}"]

    @staticmethod
    def _distinct_claim_groups(claims: List[Dict[str, object]]) -> List[Dict[str, object]]:
        groups = []
        for claim in claims:
            number = claim.get("number")
            if number is None:
                continue
            if any(abs(float(number) - float(group["number"])) < 1e-6 for group in groups):
                continue
            groups.append(claim)
        return groups

    def _general_extract(
        self,
        chunks: List[Tuple[str, Dict[str, object]]],
        question: str,
    ) -> str:
        """Fallback keyword-based line extraction for non-attribute questions."""
        stop_words = {
            "what", "is", "the", "for", "and", "of", "in", "to", "a", "an",
            "about", "tell", "me", "how", "much", "does", "it", "are", "can",
            "do", "which", "where", "when", "why", "program", "programme",
        }
        tokens = [
            token for token in re.split(r"[^a-z0-9]+", question.lower())
            if len(token) > 1 and token not in stop_words
        ]
        if not tokens:
            return NOT_FOUND_ANSWER

        relevant: List[str] = []
        for content, metadata in chunks:
            for line in content.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                lowered = stripped.lower()
                if stripped.startswith("# ") and len(tokens) > 1:
                    continue
                if any(token in lowered for token in tokens):
                    relevant.append(stripped)

        if relevant:
            answer = "\n".join(relevant[:6])
            if len(answer) > 1400:
                answer = answer[:1400]
            return answer

        # No token matched: fall back to a short excerpt of the top chunks.
        excerpt = []
        for content, _metadata in chunks:
            for line in content.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith(("# ", "|")):
                    excerpt.append(stripped)
                if len(excerpt) >= 6:
                    break
            if len(excerpt) >= 6:
                break
        if excerpt:
            return ' '.join(excerpt)[:1400]
        return NOT_FOUND_ANSWER
