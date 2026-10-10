# Recent Changes - SGP Preparation Improvements

## Overview
Implemented 11 out of 12 improvements from `sgp_prepration.pdf` (page 6) to enhance the CHARUSAT Online Course Chatbot RAG system.

## Completed Improvements

### 1. Switch to Gemini as Primary LLM with Groq Failover
**Files Modified:**
- `backend/app/llm.py`
- `backend/app/config.py`

**Changes:**
- Modified LLM initialization to use Gemini as primary LLM
- Groq now serves as failover when Gemini is unavailable
- Added model discovery and cooldown mechanisms
- Updated configuration with preferred Gemini models (gemini-3.6-flash, gemini-3.5-flash, gemini-2.5-flash, gemini-2.5-pro)
- Kept Groq configuration for failover with multiple model options

**Key Features:**
- Automatic model discovery for Gemini
- Circuit breaker with cooldown after failures
- Graceful degradation to Groq and local fallback

---

### 2. Hybrid Retrieval (BM25/Keyword Search + RRF Fusion)
**Files Created:**
- `backend/app/hybrid_retrieval.py` (new file)

**Files Modified:**
- `backend/app/retriever.py`
- `backend/requirements.txt`

**Changes:**
- Implemented BM25 keyword search using `rank-bm25` library
- Added Reciprocal Rank Fusion (RRF) for combining semantic and keyword results
- Integrated hybrid retriever into existing pipeline
- Added fallback to semantic search if hybrid unavailable
- Document tokenization and phrase extraction for BM25

**Key Features:**
- RRF constant (k=60) for score fusion
- Normalized BM25 scores for consistency
- Lazy loading of BM25 index
- Integrated with existing candidate search methods

---

### 3. Cross-Encoder Reranker (BGE-Reranker/Cohere Rerank)
**Files Created:**
- `backend/app/reranker.py` (new file)

**Files Modified:**
- `backend/app/retriever.py`
- `backend/app/config.py`
- `backend/requirements.txt`

**Changes:**
- Implemented BGE local reranker using FlagEmbedding
- Added Cohere API reranker as alternative option
- Factory function for creating rerankers
- Weighted score combination (70% reranker, 30% original)
- Integrated reranking into retrieval pipeline
- Configurable via environment variables

**Key Features:**
- Multiple reranker support (BGE, Cohere)
- Score normalization and combination
- Graceful fallback on failure
- Configurable top-k reranking

**Configuration:**
```python
RERANKER_ENABLED = True
RERANKER_TYPE = "bge"  # or "cohere"
RERANKER_MODEL = "BAAI/bge-reranker-base"
RERANKER_TOP_K = 10
```

---

### 4. Streaming Responses (SSE/WebSocket) + Typing Indicator
**Files Modified:**
- `backend/app/routes/chat_routes.py`

**Changes:**
- Added `/api/chat/stream` endpoint for streaming responses
- Implemented Server-Sent Events (SSE) for real-time streaming
- Added typing indicator events
- Chunked response delivery for smoother UX
- Maintained conversation persistence in streaming mode
- Refactored persistence logic into helper function

**Key Features:**
- Typing indicator events
- Chunked answer streaming
- Error handling in streaming mode
- Conversation history support
- Guest and authenticated user support

**Frontend Integration Required:**
Frontend needs to be updated to consume SSE stream from `/api/chat/stream`

---

### 5. Multilingual/Indic Support (BGE-M3 Embeddings, Gujarati/Hindi)
**Files Created:**
- `backend/app/multilingual.py` (new file)

**Files Modified:**
- `backend/app/config.py`
- `backend/app/prompt.py`
- `backend/app/rag_chain.py`

**Changes:**
- Changed default embedding model to `BAAI/bge-m3` (multilingual)
- Implemented language detection using script patterns
- Support for English, Hindi (Devanagari), and Gujarati
- Language-specific system prompts
- Integrated language detection into RAG pipeline

**Key Features:**
- Script-based language detection (Unicode ranges)
- Language name mapping
- Multilingual system prompts
- Language parameter in prompt building

**Configuration:**
```python
EMBEDDING_MODEL = "BAAI/bge-m3"
MULTILINGUAL_ENABLED = True
SUPPORTED_LANGUAGES = ["en", "hi", "gu"]
DEFAULT_LANGUAGE = "en"
```

---

### 6. Evaluation Harness (RAGAS/Golden Set)
**Files Created:**
- `backend/app/evaluation.py` (new file)

**Files Modified:**
- `backend/requirements.txt`

**Changes:**
- Implemented `GoldenSet` class for test question management
- Created `EvaluationMetrics` class with:
  - Retrieval hit rate calculation
  - Mean Reciprocal Rank (MRR)
  - Answer relevance scoring
- Implemented `RAGEvaluator` for running evaluations
- Added sample golden set generator
- JSON-based result export

**Key Features:**
- Golden set management from JSON files
- Retrieval quality metrics
- Answer relevance scoring
- Per-question result tracking
- Aggregate statistics

**Usage:**
```python
from app.evaluation import GoldenSet, RAGEvaluator

golden_set = GoldenSet.from_file("golden_set.json")
evaluator = RAGEvaluator(retriever, llm_client)
results = evaluator.evaluate_golden_set(golden_set)
evaluator.save_results(results, "evaluation_results.json")
```

---

### 7. Query Expansion/Rewrite for Multi-Turn Retrieval
**Files Created:**
- `backend/app/query_expansion.py` (new file)

**Files Modified:**
- `backend/app/retriever.py`
- `backend/app/rag_chain.py`

**Changes:**
- Implemented key term extraction from conversation history
- Programme context detection from history
- Pronoun and context-dependent phrase rewriting
- Query expansion with relevant terms from history
- Contextual query generation
- Added conversation history tracking to retriever

**Key Features:**
- Programme context detection (BBA, BCA, MBA, MCA)
- Pronoun resolution (it, they, this, that)
- Key term extraction and expansion
- Conversation history management (last 10 turns)
- Query contextualization

---

### 8. Vector DB Migration Plan (Qdrant/Pinecone/Milvus)
**Files Created:**
- `VECTOR_DB_MIGRATION_PLAN.md` (new file)

**Changes:**
- Comprehensive migration plan document
- Comparison of Qdrant, Pinecone, and Milvus
- Recommended phased approach (keep Chroma for now)
- Migration steps and implementation notes
- Rollback plan and configuration examples

**Status:** Planning complete, migration deferred until needed (current Chroma works well for 389 chunks)

**Recommendation:** Migrate to Qdrant when:
- Chunk count exceeds 10,000
- Concurrent users > 100
- Need advanced filtering
- Production deployment required

---

### 9. Feedback Loop (Thumbs-Up/Down + User Corrections)
**Files Modified:**
- `backend/app/models.py`
- `backend/app/routes/chat_routes.py`

**Changes:**
- Updated `create_message()` to include `feedback` and `user_correction` fields
- Added `add_message_feedback()` function
- Added `add_user_correction()` function
- Added `get_message_by_id()` function
- Added `get_feedback_stats()` function for analytics
- Added `/api/chat/feedback` endpoint
- Added `/api/chat/correction` endpoint
- Added `/api/chat/feedback/stats` endpoint

**Key Features:**
- Thumbs-up/down feedback collection
- User correction storage
- Feedback statistics and analytics
- Per-user and global stats
- MongoDB persistence

**New Endpoints:**
- `POST /api/chat/feedback` - Add feedback to message
- `POST /api/chat/correction` - Add user correction
- `GET /api/chat/feedback/stats` - Get feedback statistics

---

### 10. Upgrade Scraper to Playwright for JS-Heavy Pages
**Files Modified:**
- `backend/app/scraper.py`
- `backend/app/config.py`
- `backend/requirements.txt`

**Changes:**
- Added Playwright import and availability check
- Implemented `_fetch_url_playwright()` for JS-heavy pages
- Updated `_fetch_url()` to support both requests and Playwright
- Added `use_playwright` parameter to `crawl_internal_pages()`
- Graceful fallback to requests if Playwright fails
- Added configuration flag for Playwright usage

**Key Features:**
- JavaScript rendering support
- Fallback to requests on failure
- Configurable via environment variable
- Network idle waiting for dynamic content

**Configuration:**
```python
USE_PLAYWRIGHT_SCRAPER = False  # enable for JS-heavy sites
```

---

### 11. Caching Layer and Latency Metrics
**Files Created:**
- `backend/app/cache.py` (new file)

**Files Modified:**
- `backend/app/rag_chain.py`
- `backend/app/routes/admin_routes.py`

**Changes:**
- Implemented `QuestionCache` class with:
  - In-memory caching of question-answer pairs
  - TTL-based expiration
  - Cache size limits with eviction
  - Cache statistics (hits, misses, hit rate)
  - Expired entry cleanup
- Integrated cache into RAG pipeline
- Cache check before retrieval
- Cache storage after successful generation
- Updated timing metrics to include cache hits
- Added admin endpoints for cache management

**Key Features:**
- MD5-based cache keys
- Configurable TTL (default 3600s)
- Max size limit (default 1000 entries)
- Oldest entry eviction
- Cache statistics tracking
- Global cache instance

**New Admin Endpoints:**
- `GET /api/admin/cache` - Get cache statistics
- `DELETE /api/admin/cache` - Clear cache
- `GET /api/admin/stats` - Now includes cache stats

---

## Pending Implementation

### 12. Multimodal RAG for PDF Images
**Status:** Not implemented (complex, requires significant additional work)

**Requirements:**
- Vision model integration (e.g., GPT-4 Vision, Claude Vision)
- PDF image extraction using pymupdf
- Image embedding generation
- Multimodal search and retrieval
- Additional infrastructure and testing

**Recommendation:** Defer to Phase B of roadmap as outlined in PDF

---

## Configuration Changes

### New Environment Variables
Add to `.env` file as needed:

```bash
# Multilingual
MULTILINGUAL_ENABLED=true

# Reranker
RERANKER_ENABLED=true
RERANKER_TYPE=bge  # or cohere
RERANKER_MODEL=BAAI/bge-reranker-base
COHERE_API_KEY=your_cohere_key  # if using Cohere

# Playwright Scraper
USE_PLAYWRIGHT_SCRAPER=false  # enable for JS-heavy sites

# Vector DB (future)
VECTOR_DB_TYPE=chroma  # chroma, qdrant, pinecone
QDRANT_HOST=localhost
QDRANT_PORT=6333
PINECONE_API_KEY=your_pinecone_key
```

---

## Installation Commands

```bash
# Install new dependencies
pip install -r requirements.txt

# Install Playwright browsers (if using Playwright)
playwright install chromium

# Optional: Install FlagEmbedding for local reranking
pip install FlagEmbedding
```

---

## Files Summary

### Modified Files (9):
1. `backend/app/llm.py` - LLM client changes
2. `backend/app/config.py` - Configuration updates
3. `backend/app/retriever.py` - Retrieval enhancements
4. `backend/app/prompt.py` - Multilingual prompts
5. `backend/app/rag_chain.py` - RAG pipeline updates
6. `backend/app/models.py` - Feedback support
7. `backend/app/routes/chat_routes.py` - Streaming and feedback endpoints
8. `backend/app/routes/admin_routes.py` - Cache management
9. `backend/app/scraper.py` - Playwright integration
10. `backend/requirements.txt` - New dependencies

### New Files (8):
1. `backend/app/hybrid_retrieval.py` - BM25 + RRF fusion
2. `backend/app/reranker.py` - Cross-encoder reranking
3. `backend/app/multilingual.py` - Language detection
4. `backend/app/query_expansion.py` - Context-aware queries
5. `backend/app/evaluation.py` - Evaluation harness
6. `backend/app/cache.py` - Question caching
7. `VECTOR_DB_MIGRATION_PLAN.md` - Migration planning
8. `RECENT_CHANGES.md` - This file

---

## Testing Recommendations

1. **Test LLM Failover:** Temporarily disable Gemini API key to verify Groq failover
2. **Test Hybrid Retrieval:** Compare results with/without BM25 for keyword-heavy queries
3. **Test Reranking:** Evaluate retrieval quality improvements with reranker enabled
4. **Test Streaming:** Verify SSE endpoint works with frontend integration
5. **Test Multilingual:** Try queries in Hindi/Gujarati scripts
6. **Test Caching:** Verify repeated questions return cached results
7. **Test Feedback:** Submit thumbs-up/down and corrections via API
8. **Test Evaluation:** Run golden set evaluation to establish baseline metrics

---

## Backward Compatibility

All changes maintain backward compatibility:
- Existing API endpoints remain functional
- Optional features can be disabled via configuration
- Graceful fallbacks for unavailable dependencies
- No breaking changes to database schema

---

## Git Status

- All changes made to main branch as requested
- No commits or pushes made without permission
- Ready for review and testing
