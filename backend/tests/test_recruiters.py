import sys
from pathlib import Path
from unittest.mock import MagicMock

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.conversation import analyze_turn
from app.lexicon import is_topic_programme_independent, get_topic_synonyms
from app.retriever import RAGRetriever
from langchain_core.documents import Document


def test_recruiter_queries_classified_as_placement():
    queries = [
        "which company recruites",
        "which company recruits",
        "list of recruiters",
        "recruiters name",
        "who hires CCOE students",
        "Do companies recruit online degree students?",
        "which companies visit for placement",
    ]
    for q in queries:
        plan = analyze_turn(q, history=[])
        assert plan.topic == "placement", f"Expected topic 'placement' for query: {q}, got: {plan.topic}"
        assert is_topic_programme_independent(plan.topic) is True, f"Placement must be programme independent for: {q}"


def test_recruiter_followup_turn_preserves_topic():
    h = [
        {"role": "user", "content": "Do companies recruit online degree students?"},
        {"role": "assistant", "content": "Yes, online degree students are eligible for campus placements and recruitments at CHARUSAT."},
    ]
    plan = analyze_turn("which company recruites", history=h)
    assert plan.topic == "placement", f"Expected 'placement', got {plan.topic}"
    assert is_topic_programme_independent(plan.topic) is True


def test_retriever_placement_targeted_search_invoked():
    recruiter_doc = Document(
        page_content="## Our Recruiters\n\n- Adani Group\n- Asian Paints\n- Berger Paints\n- Crest Data Systems\n- ICICI Bank\n- Infosys\n- Jeavio\n- Meditab Software\n- Tata Group (TCS/Tata Companies)",
        metadata={"source": "home.md", "program_name": ""}
    )
    
    mock_vector_store = MagicMock()
    mock_vector_store.similarity_search_with_relevance_scores.return_value = [(recruiter_doc, 0.75)]
    mock_vector_store._collection = MagicMock()
    mock_vector_store._collection.count.return_value = 1
    mock_vector_store.get.return_value = {"ids": ["1"], "metadatas": [{"source": "home.md", "program_name": ""}], "documents": [recruiter_doc.page_content]}
    mock_vector_store.get_by_ids.return_value = [recruiter_doc]

    retriever = RAGRetriever(mock_vector_store)
    plan = analyze_turn("which company recruites", history=[])
    
    results = retriever.retrieve("which company recruites", plan=plan)
    assert len(results) > 0, "Expected retrieved results"
    assert any("Adani Group" in doc.page_content for doc, _ in results), "Expected recruiter document in results"


def test_retriever_placement_recruiters_unmanaged_file():
    recruiter_doc = Document(
        page_content="# CHARUSAT Campus Placement & Prominent Recruiters\n\n- Adani Group\n- Infosys\n- Tata Group (TCS)",
        metadata={"source": "placement_recruiters.md", "program_name": ""}
    )
    
    mock_vector_store = MagicMock()
    mock_vector_store.similarity_search_with_relevance_scores.return_value = [(recruiter_doc, 0.75)]
    mock_vector_store._collection = MagicMock()
    mock_vector_store._collection.count.return_value = 1
    mock_vector_store.get.return_value = {
        "ids": ["1"],
        "metadatas": [{"source": "placement_recruiters.md", "chunk_id": "0"}],
        "documents": [recruiter_doc.page_content]
    }
    mock_vector_store.get_by_ids.return_value = [recruiter_doc]

    retriever = RAGRetriever(mock_vector_store)
    plan = analyze_turn("list of recruiters", history=[])
    
    results = retriever.retrieve("list of recruiters", plan=plan)
    assert len(results) > 0, "Expected retrieved results from placement_recruiters.md"
    assert any("Adani Group" in doc.page_content for doc, _ in results)
