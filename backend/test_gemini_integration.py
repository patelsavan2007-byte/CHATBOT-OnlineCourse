"""Test the Gemini LLMClient (google.genai SDK) integration and fallback.

The API may be quota-limited or models may reject new users; the test must
still pass: the client must always return a non-empty answer plus a valid
generation status, never raise.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_api_key
from app.llm import LLMClient, LLMStatus
from app.prompt import build_prompt

VALID_STATUSES = {
    LLMStatus.LLM,
    LLMStatus.FALLBACK,
    LLMStatus.QUOTA,
    LLMStatus.TIMEOUT,
    LLMStatus.GENERATION_ERROR,
    LLMStatus.API_ERROR,
    LLMStatus.EMPTY,
}


def test_gemini_llm_client() -> None:
    print("\n--- Testing Gemini LLM Integration ---\n")
    api_key = get_api_key()
    print(f"GOOGLE_API_KEY detected in .env: {bool(api_key)}")

    client = LLMClient()
    print(f"Candidate models: {client._working_models}")

    if api_key:
        assert client._client is not None, "Gemini client should be initialised when API key is present"
        assert client._working_models, "At least one candidate model should be available"
        print("PASS: Gemini client initialised with candidate models")
    else:
        assert client._client is None, "Gemini client should be None when API key is missing"
        print("PASS: Local fallback enabled (no API key)")

    sample_context = (
        "Source: programs/online_bca.md\nContent Type: text\n\nContent:\n"
        "Online BCA eligibility: Passed 12th standard with English.\n"
    )
    sample_question = "What is the eligibility for Online BCA?"
    prompt = build_prompt(sample_context, sample_question)

    print("\nGenerated Prompt Sample:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)

    print("\nTesting answer generation...")
    answer, status = client.generate(prompt)
    print(f"Status: {status}")
    print(f"Generated Answer:\n{answer}\n")

    assert status in VALID_STATUSES, f"Unexpected status: {status}"
    assert len(answer.strip()) > 0, "Answer should not be empty"
    print("PASS: Answer generation returned a non-empty answer with a valid status")

    # The client must never raise when repeatedly asked (quota caching).
    for _ in range(3):
        answer2, status2 = client.generate(prompt)
        assert len(answer2.strip()) > 0
        assert status2 in VALID_STATUSES
    print("PASS: Repeated generation calls remain stable")


if __name__ == "__main__":
    test_gemini_llm_client()
