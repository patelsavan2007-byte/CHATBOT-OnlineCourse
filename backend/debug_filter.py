from app.embeddings import EmbeddingStore
es=EmbeddingStore()
vs=es.load_vector_store()
q="Which companies recruit from CHARUSAT online?"
tests={
 "none": None,
 "prog":{"program_name":"online_mca"},
 "or2":{"$or":[{"program_name":"online_mca"},{"program_name":"general"}]},
}
for name,f in tests.items():
    try:
        r=vs.similarity_search_with_relevance_scores(q,k=5,filter=f)
        print(name,"OK",len(r))
    except Exception as e:
        print(name,"ERR",repr(e)[:200])
# check policy sources
from app.retriever import RAGRetriever
r=RAGRetriever(vs)
ps=r._policy_sources()
print("policy_sources:",ps)
