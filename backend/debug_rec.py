from app.rag_chain import RAGChain
from app.embeddings import EmbeddingStore
from app.retriever import RAGRetriever
from app.llm import LLMClient
es=EmbeddingStore()
vs=es.load_vector_store()
r=RAGRetriever(vs)
llm=LLMClient()
chain=RAGChain(r,llm)
res=chain.answer('Which companies recruit from CHARUSAT online?', history=None)
print('STATUS:', res.status)
print('LEN:', len(res.retrieved))
for d,s in res.retrieved:
    print(s, d.metadata.get('source'))
    print(d.page_content[:80])
    print()
