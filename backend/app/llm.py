from __future__ import annotations

import os
import re
from typing import Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config import get_api_key
from app.utils import logger, print_info, print_warning


class LLMClient:
    def __init__(self) -> None:
        self.api_key = get_api_key()
        self.model: Optional[BaseLanguageModel] = None
        self._initialize()

    def _initialize(self) -> None:
        if not self.api_key:
            print_warning("No API key found. Using local fallback answer generation from retrieved context.")
            logger.warning("No API key found; using fallback generation")
            return

        if os.getenv("GOOGLE_API_KEY"):
            print_info("Using Google Gemini model")
            logger.info("Using Google Gemini model")
            self.model = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=self.api_key,
                temperature=0.2,
            )
        else:
            print_info("Using OpenAI model")
            logger.info("Using OpenAI model")
            self.model = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=self.api_key,
                temperature=0.2,
            )

    def generate(self, prompt: str) -> str:
        if self.model is not None:
            response = self.model.invoke(prompt)
            return response.content if hasattr(response, "content") else str(response)

        return self._fallback_generate(prompt)

    def _fallback_generate(self, prompt: str) -> str:
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

        relevant_sentences = []
        keyword_tokens = [token for token in re.split(r"[^a-z0-9]+", question.lower()) if token]
        for chunk in chunks:
            lines = [line.strip() for line in chunk.splitlines() if line.strip()]
            for line in lines:
                lowered = line.lower()
                if any(token in lowered for token in keyword_tokens):
                    relevant_sentences.append(line)
                    break
                if not relevant_sentences and len(line) < 220:
                    relevant_sentences.append(line)

        if not relevant_sentences:
            return "I couldn't find this information in the university knowledge base."

        answer = " ".join(relevant_sentences[:4])
        answer = re.sub(r"\s+", " ", answer).strip()
        return answer[:1400] if len(answer) > 1400 else answer
