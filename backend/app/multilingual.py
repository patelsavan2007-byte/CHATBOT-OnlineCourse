"""Multilingual support for the chatbot.

This module provides language detection and multilingual response capabilities
for Indic languages (Hindi, Gujarati) in addition to English.
"""
from __future__ import annotations

import re
from typing import Optional

from app import config
from app.utils import logger


# Simple script detection patterns (not comprehensive but functional)
SCRIPT_PATTERNS = {
    "gu": re.compile(r"[\u0A80-\u0AFF]"),  # Gujarati script range
    "hi": re.compile(r"[\u0900-\u097F]"),  # Devanagari script range (Hindi)
    "en": re.compile(r"[a-zA-Z]"),  # Latin script
}


def detect_language(text: str) -> str:
    """Detect the primary language of the input text.

    Args:
        text: Input text to analyze

    Returns:
        Language code ("en", "hi", "gu", or default)
    """
    if not text or not text.strip():
        return config.DEFAULT_LANGUAGE

    # Count characters matching each script
    scores = {}
    for lang, pattern in SCRIPT_PATTERNS.items():
        matches = len(pattern.findall(text))
        if matches > 0:
            scores[lang] = matches

    if not scores:
        return config.DEFAULT_LANGUAGE

    # Return the language with the highest score
    detected = max(scores.items(), key=lambda x: x[1])[0]

    # Only return detected language if it's supported
    if detected in config.SUPPORTED_LANGUAGES:
        logger.info("Detected language: %s (text length: %d)", detected, len(text))
        return detected

    return config.DEFAULT_LANGUAGE


def get_language_name(lang_code: str) -> str:
    """Get human-readable language name from code.

    Args:
        lang_code: Language code (en, hi, gu)

    Returns:
        Human-readable language name
    """
    names = {
        "en": "English",
        "hi": "Hindi",
        "gu": "Gujarati",
    }
    return names.get(lang_code, "Unknown")


def should_translate_response(query_lang: str, target_lang: str) -> bool:
    """Determine if response should be translated.

    Args:
        query_lang: Language of the user's query
        target_lang: Preferred response language

    Returns:
        True if translation is needed
    """
    return query_lang != target_lang and config.MULTILINGUAL_ENABLED


def get_multilingual_system_prompt(lang: str) -> str:
    """Get system prompt for multilingual responses.

    Args:
        lang: Target language code

    Returns:
        System prompt string
    """
    base_prompt = """You are a helpful assistant for CHARUSAT Online Programmes.
Provide accurate, concise answers based on the retrieved context.
Always cite specific details from the sources when available."""

    if lang == "en":
        return base_prompt
    elif lang == "hi":
        return base_prompt + "\n\nPlease respond in Hindi (Devanagari script) when the user asks in Hindi."
    elif lang == "gu":
        return base_prompt + "\n\nPlease respond in Gujarati when the user asks in Gujarati."
    else:
        return base_prompt
