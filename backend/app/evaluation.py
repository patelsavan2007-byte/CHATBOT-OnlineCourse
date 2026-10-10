"""Evaluation harness for RAG system.

This module provides tools to evaluate retrieval quality and answer faithfulness
using golden test sets and RAGAS metrics.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.utils import logger


class GoldenSet:
    """Golden test set for evaluation."""

    def __init__(self, questions: List[Dict[str, Any]]) -> None:
        """Initialize golden set.

        Args:
            questions: List of question dictionaries with expected answers
        """
        self.questions = questions

    @classmethod
    def from_file(cls, filepath: str) -> "GoldenSet":
        """Load golden set from JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            GoldenSet instance
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Loaded golden set from %s with %d questions", filepath, len(data))
            return cls(data)
        except Exception as exc:
            logger.error("Failed to load golden set from %s: %s", filepath, exc)
            raise

    def get_questions(self) -> List[Dict[str, Any]]:
        """Get all questions in the golden set."""
        return self.questions


class EvaluationMetrics:
    """Compute evaluation metrics for RAG system."""

    @staticmethod
    def retrieval_hit_rate(
        retrieved_docs: List[Tuple[str, float]],
        expected_sources: List[str],
    ) -> float:
        """Compute retrieval hit rate.

        Args:
            retrieved_docs: List of (doc_content, score) tuples
            expected_sources: List of expected source paths

        Returns:
            Hit rate (0.0 to 1.0)
        """
        if not expected_sources:
            return 1.0

        retrieved_sources = []
        for doc, _ in retrieved_docs:
            # Extract source from metadata if available
            if isinstance(doc, tuple) and len(doc) > 1:
                metadata = doc[1] if isinstance(doc[1], dict) else {}
            else:
                metadata = {}
            source = metadata.get("source", "")
            if source:
                retrieved_sources.append(source)

        hits = sum(1 for expected in expected_sources if any(expected in retrieved for retrieved in retrieved_sources))
        return hits / len(expected_sources)

    @staticmethod
    def mean_reciprocal_rank(
        retrieved_docs: List[Tuple[str, float]],
        expected_sources: List[str],
    ) -> float:
        """Compute Mean Reciprocal Rank (MRR).

        Args:
            retrieved_docs: List of (doc_content, score) tuples
            expected_sources: List of expected source paths

        Returns:
            MRR score (0.0 to 1.0)
        """
        if not expected_sources:
            return 1.0

        reciprocal_ranks = []
        for expected in expected_sources:
            for rank, (doc, _) in enumerate(retrieved_docs, start=1):
                if isinstance(doc, tuple) and len(doc) > 1:
                    metadata = doc[1] if isinstance(doc[1], dict) else {}
                else:
                    metadata = {}
                source = metadata.get("source", "")
                if expected in source:
                    reciprocal_ranks.append(1.0 / rank)
                    break
            else:
                reciprocal_ranks.append(0.0)

        return sum(reciprocal_ranks) / len(reciprocal_ranks)

    @staticmethod
    def answer_relevance(
        generated_answer: str,
        expected_answer: str,
    ) -> float:
        """Simple answer relevance based on keyword overlap.

        Args:
            generated_answer: Generated answer
            expected_answer: Expected answer

        Returns:
            Relevance score (0.0 to 1.0)
        """
        if not expected_answer:
            return 1.0

        # Extract keywords from both answers
        def extract_keywords(text: str) -> set:
            import re
            words = re.findall(r"\b\w+\b", text.lower())
            stopwords = {
                "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
                "has", "have", "how", "i", "in", "is", "it", "its", "of", "on",
                "or", "that", "the", "this", "to", "was", "what", "when", "where",
                "who", "will", "with",
            }
            return {w for w in words if w not in stopwords and len(w) > 2}

        gen_keywords = extract_keywords(generated_answer)
        exp_keywords = extract_keywords(expected_answer)

        if not exp_keywords:
            return 1.0

        # Calculate Jaccard similarity
        intersection = len(gen_keywords & exp_keywords)
        union = len(gen_keywords | exp_keywords)

        return intersection / union if union > 0 else 0.0


class RAGEvaluator:
    """Evaluate RAG system performance."""

    def __init__(self, retriever, llm_client) -> None:
        """Initialize evaluator.

        Args:
            retriever: RAG retriever instance
            llm_client: LLM client instance
        """
        self.retriever = retriever
        self.llm_client = llm_client

    def evaluate_golden_set(
        self,
        golden_set: GoldenSet,
    ) -> Dict[str, Any]:
        """Evaluate against golden test set.

        Args:
            golden_set: GoldenSet instance

        Returns:
            Dictionary of evaluation results
        """
        results = {
            "total_questions": len(golden_set.questions),
            "retrieval_metrics": {
                "hit_rates": [],
                "mrr_scores": [],
            },
            "answer_metrics": {
                "relevance_scores": [],
            },
            "per_question_results": [],
        }

        for question_data in golden_set.questions:
            question = question_data.get("question", "")
            expected_sources = question_data.get("expected_sources", [])
            expected_answer = question_data.get("expected_answer", "")

            # Retrieve documents
            retrieved = self.retriever.retrieve(question)

            # Compute retrieval metrics
            hit_rate = EvaluationMetrics.retrieval_hit_rate(retrieved, expected_sources)
            mrr = EvaluationMetrics.mean_reciprocal_rank(retrieved, expected_sources)

            results["retrieval_metrics"]["hit_rates"].append(hit_rate)
            results["retrieval_metrics"]["mrr_scores"].append(mrr)

            # Generate answer
            try:
                from app.rag_chain import RAGChain
                rag_chain = RAGChain(self.retriever, self.llm_client)
                generated_answer, _ = rag_chain.answer(question)

                # Compute answer relevance
                relevance = EvaluationMetrics.answer_relevance(generated_answer, expected_answer)
                results["answer_metrics"]["relevance_scores"].append(relevance)
            except Exception as exc:
                logger.warning("Failed to generate answer for question: %s", exc)
                relevance = 0.0
                results["answer_metrics"]["relevance_scores"].append(relevance)

            # Store per-question results
            results["per_question_results"].append({
                "question": question,
                "hit_rate": hit_rate,
                "mrr": mrr,
                "relevance": relevance,
            })

        # Compute aggregate metrics
        results["avg_hit_rate"] = sum(results["retrieval_metrics"]["hit_rates"]) / len(results["retrieval_metrics"]["hit_rates"]) if results["retrieval_metrics"]["hit_rates"] else 0.0
        results["avg_mrr"] = sum(results["retrieval_metrics"]["mrr_scores"]) / len(results["retrieval_metrics"]["mrr_scores"]) if results["retrieval_metrics"]["mrr_scores"] else 0.0
        results["avg_relevance"] = sum(results["answer_metrics"]["relevance_scores"]) / len(results["answer_metrics"]["relevance_scores"]) if results["answer_metrics"]["relevance_scores"] else 0.0

        logger.info(
            "Evaluation complete: Avg Hit Rate=%.3f, Avg MRR=%.3f, Avg Relevance=%.3f",
            results["avg_hit_rate"],
            results["avg_mrr"],
            results["avg_relevance"],
        )

        return results

    def save_results(self, results: Dict[str, Any], output_path: str) -> None:
        """Save evaluation results to JSON file.

        Args:
            results: Evaluation results dictionary
            output_path: Path to save results
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            logger.info("Evaluation results saved to %s", output_path)
        except Exception as exc:
            logger.error("Failed to save results to %s: %s", output_path, exc)


def create_sample_golden_set(output_path: str) -> None:
    """Create a sample golden set for CHARUSAT programmes.

    Args:
        output_path: Path to save the golden set
    """
    sample_questions = [
        {
            "question": "What is the total fee for Online BBA?",
            "expected_sources": ["pdfs/PPR_Online_BBA"],
            "expected_answer": "The total fee for Online BBA is ₹90,000 for the entire programme.",
        },
        {
            "question": "What is the duration of Online MBA?",
            "expected_sources": ["pdfs/PPR_Online_MBA"],
            "expected_answer": "The Online MBA programme has a duration of 2 years (4 semesters).",
        },
        {
            "question": "What are the eligibility criteria for Online BCA?",
            "expected_sources": ["pdfs/PPR_Online_BCA"],
            "expected_answer": "Candidates must have passed 10+2 with minimum 45% marks.",
        },
    ]

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(sample_questions, f, indent=2)
        logger.info("Sample golden set created at %s with %d questions", output_path, len(sample_questions))
    except Exception as exc:
        logger.error("Failed to create sample golden set: %s", exc)
