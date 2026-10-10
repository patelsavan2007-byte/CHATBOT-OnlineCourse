# Vector Database Migration Plan

## Current State
- **Current Vector DB**: Chroma (local SQLite-based)
- **Chunk Count**: 389 chunks (237 md + 152 pdf)
- **Deployment**: Local storage at `backend/vector_db/`

## Migration Options

### Option 1: Qdrant (Recommended)
**Pros:**
- Open-source and self-hosted
- Excellent performance and scalability
- Rich filtering capabilities
- Good Python SDK support
- Supports hybrid search natively

**Cons:**
- Requires additional infrastructure (Docker deployment)
- More complex setup than Chroma

**Migration Steps:**
1. Deploy Qdrant instance (Docker or cloud)
2. Install Qdrant client: `pip install qdrant-client`
3. Export existing Chroma data
4. Migrate embeddings and metadata to Qdrant
5. Update `EmbeddingStore` to use Qdrant
6. Test retrieval quality
7. Deploy and monitor

### Option 2: Pinecone
**Pros:**
- Fully managed service
- Excellent performance
- Simple API
- Good free tier for testing

**Cons:**
- Not open-source
- Vendor lock-in
- Cost at scale
- Limited filtering in free tier

**Migration Steps:**
1. Create Pinecone account and index
2. Install Pinecone client: `pip install pinecone-client`
3. Export Chroma data
4. Migrate to Pinecone
5. Update embedding store
6. Test and deploy

### Option 3: Milvus
**Pros:**
- Open-source and feature-rich
- Excellent for large-scale deployments
- Advanced filtering and indexing
- Good performance

**Cons:**
- Complex setup and maintenance
- Heavy resource requirements
- Steeper learning curve

**Migration Steps:**
1. Deploy Milvus (Docker/Kubernetes)
2. Install client: `pip install pymilvus`
3. Export and migrate data
4. Update integration
5. Test and deploy

## Recommended Approach

**Phase 1 (Current):** Keep Chroma for development (working well for 389 chunks)

**Phase 2 (When needed):** Migrate to Qdrant when:
- Chunk count exceeds 10,000
- Concurrent users > 100
- Need advanced filtering
- Production deployment required

**Phase 3 (Long-term):** Consider Pinecone for managed simplicity if team prefers reduced infrastructure

## Migration Implementation Notes

When migrating, ensure:
1. **Preserve embeddings** - Re-use existing vectors to avoid re-computation
2. **Maintain metadata** - Keep all metadata fields (source, page, program_name, etc.)
3. **Test retrieval** - Verify results match before/after migration
4. **Fallback mechanism** - Keep Chroma as backup during transition
5. **Configuration** - Use environment variables to switch between vector DBs

## Example Configuration Update

```python
# In config.py
VECTOR_DB_TYPE = os.getenv("VECTOR_DB_TYPE", "chroma")  # chroma, qdrant, pinecone
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
```

## Migration Script Structure

```python
# scripts/migrate_to_qdrant.py
1. Load existing Chroma data
2. Initialize Qdrant client
3. Create collection with matching schema
4. Batch insert documents with embeddings
5. Verify count and metadata
6. Update configuration
7. Test retrieval
```

## Rollback Plan

If migration fails:
1. Keep Chroma data intact
2. Use configuration flag to switch back
3. Document the rollback procedure
4. Have monitoring to detect issues early
