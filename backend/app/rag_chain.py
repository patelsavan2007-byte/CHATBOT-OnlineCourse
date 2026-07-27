from __future__ import annotations

from typing import List, Tuple

from langchain_core.documents import Document

from app.llm import LLMClient
from app.prompt import build_prompt
from app.retriever import RAGRetriever
from app.utils import logger


class RAGChain:
    def __init__(self, retriever: RAGRetriever, llm_client: LLMClient) -> None:
        self.retriever = retriever
        self.llm_client = llm_client

    def answer(self, question: str) -> Tuple[str, List[Tuple[Document, float]]]:
        retrieved = self.retriever.retrieve(question)
        context = "\n\n---\n\n".join(
            f"Source: {doc.metadata.get('source', 'unknown')}\nChunk ID: {doc.metadata.get('chunk_id', 'n/a')}\nContent:\n{doc.page_content}"
            for doc, _ in retrieved
        )

        prompt = build_prompt(context=context, question=question)
        response_text = self.llm_client.generate(prompt)
        logger.info("LLM response generated")
        return response_text, retrieved
