"""Dedicated Gemini client for SkillForge AI career features.

Separate from the chatbot's LLM client — this one uses structured JSON
output mode and is optimised for career analysis tasks.

Uses the ``google.genai`` SDK (same as the existing chatbot code) with:
- Structured JSON output via ``response_mime_type``
- Retry logic with exponential backoff
- Pydantic validation of every response
- Web-search grounding for course/cert lookups (when available)
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

from app import config
from app.utils import logger, print_info, print_warning

try:
    from google import genai
    from google.genai import types as genai_types
    HAS_GENAI = True
except ImportError:
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]
    HAS_GENAI = False

T = TypeVar("T", bound=BaseModel)

# Gemini models to try in priority order for career features
CAREER_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

MAX_RETRIES = 3
RETRY_DELAY = 2.0
BACKOFF_FACTOR = 1.5


class GeminiCareerClient:
    """Gemini client for SkillForge AI career analysis and plan generation."""

    def __init__(self) -> None:
        self._client: Optional[genai.Client] = None
        self._working_model: Optional[str] = None
        self._initialized = False
        self._init()

    def _init(self) -> None:
        """Initialize the Gemini client."""
        if not HAS_GENAI:
            print_warning("[Gemini] google-genai SDK not installed.")
            return

        api_key = config.get_api_key()
        if not api_key:
            print_warning("[Gemini] No GOOGLE_API_KEY found in .env. Career AI features will be limited.")
            return

        try:
            self._client = genai.Client(api_key=api_key)
            # Discover working model
            self._working_model = self._discover_model()
            if self._working_model:
                self._initialized = True
                print_info(f"[Gemini] Career client ready with model: {self._working_model}")
            else:
                print_warning("[Gemini] No working Gemini model found.")
        except Exception as exc:
            print_warning(f"[Gemini] Failed to initialize: {exc}")
            logger.error("Gemini init failed: %s", exc)

    def _discover_model(self) -> Optional[str]:
        """Find the first available Gemini model."""
        if not self._client:
            return None

        for model_name in CAREER_MODELS:
            try:
                # Try a minimal generation to verify model availability
                response = self._client.models.generate_content(
                    model=model_name,
                    contents="Reply with just the word OK",
                    config=genai_types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=10,
                    ),
                )
                if response and hasattr(response, "text") and response.text:
                    logger.info("Discovered working Gemini model: %s", model_name)
                    return model_name
            except Exception as exc:
                logger.warning("Model %s unavailable: %s", model_name, exc)
                continue
        return None

    @property
    def is_available(self) -> bool:
        return self._initialized and self._client is not None

    def generate_json(
        self,
        prompt: str,
        *,
        response_model: Optional[Type[T]] = None,
        temperature: float = 0.3,
        max_tokens: int = 8192,
        use_search: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Generate structured JSON output from Gemini.

        Parameters
        ----------
        prompt : str
            The full prompt to send.
        response_model : Optional[Type[BaseModel]]
            Pydantic model for validating the response.
        temperature : float
            Generation temperature.
        max_tokens : int
            Max output tokens.
        use_search : bool
            Whether to enable web search grounding for real URLs.

        Returns
        -------
        dict or None
            Parsed JSON dict, or None on failure.
        """
        if not self.is_available:
            logger.warning("Gemini client not available")
            return None

        config_kwargs: Dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "response_mime_type": "application/json",
        }

        # Add search tool if requested
        tools = []
        if use_search:
            try:
                tools.append(genai_types.Tool(google_search=genai_types.GoogleSearch()))
                config_kwargs["tools"] = tools
            except Exception:
                logger.warning("Web search grounding not available, proceeding without it")

        gen_config = genai_types.GenerateContentConfig(**config_kwargs)

        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.models.generate_content(
                    model=self._working_model,
                    contents=prompt,
                    config=gen_config,
                )

                text = self._extract_text(response)
                if not text:
                    logger.warning("Gemini returned empty response (attempt %d)", attempt + 1)
                    continue

                # Parse JSON
                parsed = self._parse_json(text)
                if parsed is None:
                    logger.warning("Failed to parse Gemini JSON (attempt %d)", attempt + 1)
                    continue

                # Validate with Pydantic model if provided
                if response_model:
                    try:
                        validated = response_model.model_validate(parsed)
                        return validated.model_dump()
                    except Exception as exc:
                        logger.warning("Pydantic validation failed: %s", exc)
                        # Return raw parsed dict anyway — partial data is better than nothing
                        return parsed

                return parsed

            except Exception as exc:
                logger.warning("Gemini generation failed (attempt %d): %s", attempt + 1, exc)
                if attempt + 1 < MAX_RETRIES:
                    delay = RETRY_DELAY * (BACKOFF_FACTOR ** attempt)
                    time.sleep(delay)
                continue

        logger.error("All Gemini attempts exhausted")
        return None

    def generate_text(
        self,
        prompt: str,
        *,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Optional[str]:
        """Generate plain text output from Gemini."""
        if not self.is_available:
            return None

        gen_config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.models.generate_content(
                    model=self._working_model,
                    contents=prompt,
                    config=gen_config,
                )
                text = self._extract_text(response)
                if text:
                    return text
            except Exception as exc:
                logger.warning("Gemini text gen failed (attempt %d): %s", attempt + 1, exc)
                if attempt + 1 < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * (BACKOFF_FACTOR ** attempt))
        return None

    @staticmethod
    def _extract_text(response: Any) -> Optional[str]:
        """Extract text from a Gemini response object."""
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        # Try candidates
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            if content is None:
                continue
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", "")
                if part_text and part_text.strip():
                    return part_text.strip()
        return None

    @staticmethod
    def _parse_json(text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from Gemini response text, handling markdown fences."""
        text = text.strip()

        # Remove markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last fence lines
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass

            # Try to find JSON array
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass

        return None


# Module-level singleton
_gemini_client: Optional[GeminiCareerClient] = None


def get_gemini_client() -> GeminiCareerClient:
    """Return the shared GeminiCareerClient instance."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiCareerClient()
    return _gemini_client
