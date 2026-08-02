"""Test Gemini 2.5 Flash LLMClient configuration and RAG pipeline integration."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_api_key
from app.llm import LLMClient
from app.prompt import build_prompt


def test_gemini_llm_client():
    print("\n--- Testing Gemini 2.5 Flash LLM Integration ---\n")
    api_key = get_api_key()
    print(f"GOOGLE_API_KEY detected in .env: {bool(api_key)}")

    client = LLMClient()

    if api_key:
        print("Model initialized:", client.model)
        assert client.model is not None, "Model should be initialized when API key is present"
        assert getattr(client.model, "model", "") == "gemini-2.5-flash", "Model name should be gemini-2.5-flash"
        print("PASS: Gemini 2.5 Flash correctly configured with model='gemini-2.5-flash'")
    else:
        print("Model initialized:", client.model)
        assert client.model is None, "Model should be None when API key is missing"
        print("PASS: Clear warning shown and fallback enabled when GOOGLE_API_KEY is missing")

    # Test prompt generation logic
    sample_context = "Source: programs/online_bca.md\nContent:\nOnline BCA eligibility: Passed 12th standard with English."
    sample_question = "What is the eligibility for Online BCA?"
    prompt = build_prompt(sample_context, sample_question)

    print("\nGenerated Prompt Sample:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)

    print("\nTesting answer generation...")
    answer = client.generate(prompt)
    print(f"Generated Answer:\n{answer}\n")
    assert len(answer) > 0, "Answer should not be empty"
    print("PASS: Answer generation working as expected!")


if __name__ == "__main__":
    test_gemini_llm_client()
