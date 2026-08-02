from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import get_api_key
from app.utils import logger, print_info, print_warning

# Attribute keywords and their variations for fallback extraction
ATTRIBUTE_MAP: Dict[str, List[str]] = {
    "fee": ["fee", "fees", "annual fee", "total fee", "cost", "price", "tuition"],
    "duration": ["duration", "years", "year"],
    "credits": ["credits", "credit", "total credits"],
    "eligibility": ["eligibility", "eligible", "criteria", "requirement"],
    "admission": ["admission", "admission process"],
    "examination": ["examination", "exam"],
    "syllabus": ["syllabus", "curriculum", "semester", "subjects"],
}

# Preferred models in priority order (exact names from the API)
_PREFERRED_MODELS = [
    "models/gemini-3.6-flash",
    "models/gemini-3.5-flash",
    "models/gemini-2.5-flash",
    "models/gemini-2.5-pro",
]


class LLMClient:
    def __init__(self) -> None:
        self.api_key = get_api_key()
        self.model_name: Optional[str] = None
        self._initialize()

    def _initialize(self) -> None:
        if not self.api_key:
            print_warning("[WARNING] GOOGLE_API_KEY is missing or invalid in .env file.")
            print_warning("Using local fallback answer generation from retrieved context.")
            logger.warning("GOOGLE_API_KEY missing; using local fallback generation")
            return

        # Auto-detect available models from the API
        self.model_name = self._discover_model()
        if self.model_name:
            print_info(f"Using Gemini model: {self.model_name}")
        else:
            print_warning("[WARNING] No compatible Gemini model found via API.")
            print_warning("Using local fallback answer generation from retrieved context.")

    def _discover_model(self) -> Optional[str]:
        """Discover the best available Gemini model using the API."""
        try:
            genai.configure(api_key=self.api_key)
            available = set()
            for model in genai.list_models():
                if "generateContent" in model.supported_generation_methods:
                    available.add(model.name)
            logger.info("Available Gemini models: %s", available)

            # Known models that list_models() returns but cause 404 NOT_FOUND for new users
            deprecated_models = {"models/gemini-2.5-flash", "models/gemini-2.5-flash-preview"}

            # Pick the first preferred model that is available and not deprecated
            for preferred in _PREFERRED_MODELS:
                if preferred in available and preferred not in deprecated_models:
                    logger.info("Selected model: %s", preferred)
                    # Strip "models/" prefix for LangChain compatibility
                    return preferred.replace("models/", "")

            # If none of the preferred models match, pick the first available non-deprecated gemini model
            for name in sorted(available):
                if "gemini" in name and name not in deprecated_models:
                    logger.info("Fallback selected model: %s", name)
                    return name.replace("models/", "")

            logger.warning("No valid Gemini models found in available models list")
            return None
        except Exception as exc:
            print_warning(f"[WARNING] Failed to discover Gemini models: {exc}")
            logger.error("Model discovery failed: %s", exc)
            return None

    def generate(self, prompt: str) -> str:
        if self.api_key and self.model_name:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    temperature=0.2,
                )
                response = llm.invoke(prompt)
                raw_content = response.content if hasattr(response, "content") else response
                if isinstance(raw_content, str):
                    text = raw_content
                elif isinstance(raw_content, list):
                    text = "".join(
                        part if isinstance(part, str) else (part.get("text", "") if isinstance(part, dict) else str(part))
                        for part in raw_content
                    )
                else:
                    text = str(raw_content)

                if text and text.strip():
                    return text.strip()
            except Exception as exc:
                err_str = str(exc)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print_warning(f"[WARNING] Gemini API quota limit reached for {self.model_name} (429 RESOURCE_EXHAUSTED).")
                    print_warning("Falling back to local context answer generation.")
                    logger.warning("Gemini API quota limit (429) for %s", self.model_name)
                else:
                    print_warning(f"[WARNING] Gemini API error ({self.model_name}): {exc}")
                    logger.error("Gemini API error (%s): %s", self.model_name, exc)

        return self._fallback_generate(prompt)

    # ------------------------------------------------------------------
    # Fallback answer generation (no API key / quota exhausted)
    # ------------------------------------------------------------------

    def _fallback_generate(self, prompt: str) -> str:
        """Generate an answer from retrieved context without calling the LLM."""
        prefix = "Retrieved Context:\n"
        question_marker = "\n\nUser Question:\n"
        if prefix not in prompt:
            return "I couldn't find this information in the university knowledge base."

        context_and_question = prompt.split(prefix, 1)[1]
        if question_marker in context_and_question:
            context, question = context_and_question.split(question_marker, 1)
        else:
            context, question = context_and_question, ""

        context = context.strip()
        question = question.strip()
        if not context:
            return "I couldn't find this information in the university knowledge base."

        chunks = [segment.strip() for segment in re.split(r"\n\n---\n\n", context) if segment.strip()]
        if not chunks:
            chunks = [context]

        # Detect if this is an attribute-specific question
        attribute_type = self._detect_attribute(question)
        if attribute_type:
            result = self._extract_attribute(chunks, attribute_type, question)
            if result:
                return result

        # General question: use keyword-based line matching
        return self._general_extract(chunks, question)

    def _detect_attribute(self, question: str) -> Optional[str]:
        """Detect which attribute type the question is asking about."""
        q_lower = question.lower()
        for attr_type, keywords in ATTRIBUTE_MAP.items():
            # Check multi-word keywords first
            for kw in sorted(keywords, key=len, reverse=True):
                if kw in q_lower:
                    return attr_type
        return None

    def _extract_attribute(self, chunks: List[str], attribute_type: str, question: str) -> Optional[str]:
        """Extract a specific attribute value from chunks.

        Handles the scraped markdown format where attributes appear as:
            Annual Fee
            :
            50,000 INR
        or:
            Duration: 3 years
        """
        keywords = ATTRIBUTE_MAP.get(attribute_type, [])
        source = "unknown"

        for chunk in chunks:
            # Extract source from chunk metadata
            for line in chunk.splitlines():
                if line.strip().startswith("Source:"):
                    source = line.strip().replace("Source:", "").strip()
                    break

            content_lines = []
            for line in chunk.splitlines():
                stripped = line.strip()
                # Skip metadata lines
                if stripped.startswith(("Source:", "Chunk ID:", "Content:")):
                    continue
                content_lines.append(stripped)

            # Strategy 1: Look for "Key : Value" or "Key: Value" on same line
            for line in content_lines:
                line_lower = line.lower()
                for kw in keywords:
                    # Match patterns like "Annual Fee: 50,000 INR" or "Duration: 3 years"
                    pattern = re.compile(rf"({re.escape(kw)})\s*[:\-]\s*(.+)", re.IGNORECASE)
                    match = pattern.search(line)
                    if match:
                        key = match.group(1).strip()
                        value = match.group(2).strip()
                        if value and value != ":":
                            return f"{key}: {value}\n\nSource: {source}"

            # Strategy 2: Handle multi-line format (key on one line, value on next non-empty line)
            # The scraped markdown often has: "Annual Fee\n\n:\n\n50,000 INR"
            for i, line in enumerate(content_lines):
                line_lower = line.lower().strip()
                if not line_lower:
                    continue
                for kw in keywords:
                    if kw in line_lower and len(line_lower) < 40:
                        # This line looks like a label — find the next non-empty, non-colon line
                        value = self._find_next_value(content_lines, i)
                        if value:
                            label = line.strip().rstrip(":")
                            return f"{label}: {value}\n\nSource: {source}"

        return None

    def _find_next_value(self, lines: List[str], start_idx: int) -> Optional[str]:
        """Find the next meaningful value line after a label line."""
        for j in range(start_idx + 1, min(start_idx + 5, len(lines))):
            candidate = lines[j].strip()
            # Skip empty lines and standalone colons
            if not candidate or candidate == ":":
                continue
            # Skip if it looks like another label or metadata
            if candidate.startswith(("Source:", "Chunk ID:", "Content:", "#")):
                continue
            return candidate
        return None

    def _general_extract(self, chunks: List[str], question: str) -> str:
        """General keyword-based line extraction for non-attribute questions."""
        # Stop words to ignore when scanning for relevant tokens
        stop_words = {
            "what", "is", "the", "for", "and", "of", "in", "to", "a", "an",
            "about", "tell", "me", "how", "much", "does", "it", "are", "can",
            "do", "which", "where", "when", "why", "program", "programme",
        }
        question_tokens = [
            token for token in re.split(r"[^a-z0-9]+", question.lower())
            if len(token) > 1 and token not in stop_words
        ]

        source = "unknown"
        relevant_lines: List[str] = []
        for chunk in chunks:
            lines = [l.strip() for l in chunk.splitlines() if l.strip()]
            for line in lines:
                if line.startswith(("Source:", "Chunk ID:", "Content:")):
                    if line.startswith("Source:"):
                        source = line.replace("Source:", "").strip()
                    continue
                lowered = line.lower()
                # Skip top-level document titles if there are other tokens matching
                if line.startswith("# ") and len(question_tokens) > 1:
                    continue
                if any(token in lowered for token in question_tokens):
                    relevant_lines.append(line)

        if not relevant_lines:
            # Fallback to non-metadata content lines from chunks
            content_lines = []
            for chunk in chunks:
                for line in chunk.splitlines():
                    l = line.strip()
                    if l and not l.startswith(("Source:", "Chunk ID:", "Content:", "# ")):
                        content_lines.append(l)
            if content_lines:
                answer = "\n".join(content_lines[:6])
                return f"{answer}\n\nSource: {source}"
            return "I couldn't find this information in the university knowledge base."

        # Return up to 6 clean relevant lines
        answer = "\n".join(relevant_lines[:6])
        if len(answer) > 1400:
            answer = answer[:1400]
        return f"{answer}\n\nSource: {source}"
