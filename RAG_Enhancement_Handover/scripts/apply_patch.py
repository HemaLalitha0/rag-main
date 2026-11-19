import os

file_path = r"c:\Users\lenovo\Downloads\rag-main\helps.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Snippet 1
s1_old = """# ---------------------------
# Paths & caches
# ---------------------------"""
s1_new = """# ---------------------------
# Monitoring & Observability
# ---------------------------
import logging
from logging.handlers import RotatingFileHandler
import json

def setup_rag_logger():
    logger = logging.getLogger("RAG_Monitor")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        import os
        from pathlib import Path
        fh = RotatingFileHandler(str(Path.cwd() / "rag_metrics.jsonl"), maxBytes=5000000, backupCount=2)
        fh.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(fh)
    return logger

rag_logger = setup_rag_logger()

def log_rag_event(event_type: str, data: dict):
    import time
    event = {"event": event_type, "timestamp": time.time(), **data}
    rag_logger.info(json.dumps(event))

# ---------------------------
# Paths & caches
# ---------------------------"""
content = content.replace(s1_old, s1_new, 1)

# Snippet 2
s2_old = """def build_faiss_index(vecs):
    if faiss is None or np is None or not vecs:
        return None
    try:
        arr = np.array(vecs, dtype="float32")
        idx = faiss.IndexFlatL2(arr.shape[1])
        idx.add(arr)
        faiss.write_index(idx, str(FAISS_INDEX_PATH))
        return idx
    except Exception as e:
        st.error(f"FAISS index build failed: {e}")
        return None"""
s2_new = """# ---------------------------
# Scalable Vector Store Abstraction
# ---------------------------
class VectorStoreBase:
    def add(self, vectors, metadatas): pass
    def search(self, query_vector, topk): pass
    def persist(self): pass
    def load(self): pass

class FAISSVectorStore(VectorStoreBase):
    def __init__(self):
        self.idx = None
    def add(self, vectors, metadatas):
        if not vectors or faiss is None or np is None: return
        arr = np.array(vectors, dtype="float32")
        self.idx = faiss.IndexFlatL2(arr.shape[1])
        self.idx.add(arr)
    def search(self, query_vector, topk):
        if self.idx is None or np is None: return [], []
        arr = np.array([query_vector], dtype="float32")
        D, I = self.idx.search(arr, topk)
        return (D[0].tolist(), I[0].tolist()) if len(D) > 0 else ([], [])
    def persist(self):
        if self.idx and faiss is not None:
            faiss.write_index(self.idx, str(FAISS_INDEX_PATH))
    def load(self):
        if FAISS_INDEX_PATH.exists() and faiss is not None:
            self.idx = faiss.read_index(str(FAISS_INDEX_PATH))
            return True
        return False

class QdrantVectorStore(VectorStoreBase):
    def __init__(self, collection_name="rag_collection", host="localhost", port=6333):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import VectorParams, Distance, PointStruct
            self.client = QdrantClient(location=":memory:") 
            self.collection_name = collection_name
            self.PointStruct = PointStruct
            self.VectorParams = VectorParams
            self.Distance = Distance
            self._ensure_collection()
        except Exception:
            self.client = None
    def _ensure_collection(self):
        if not self.client: return
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=self.VectorParams(size=384, distance=self.Distance.COSINE)
            )
    def add(self, vectors, metadatas):
        if not self.client: return
        points = [self.PointStruct(id=i, vector=v.tolist() if hasattr(v, "tolist") else v, payload={"idx": i}) for i, v in enumerate(vectors)]
        self.client.upsert(collection_name=self.collection_name, points=points)
    def search(self, query_vector, topk):
        if not self.client: return [], []
        vec = query_vector.tolist() if hasattr(query_vector, "tolist") else query_vector
        res = self.client.search(collection_name=self.collection_name, query_vector=vec, limit=topk)
        return [1.0 - r.score for r in res], [r.payload["idx"] for r in res]
    def persist(self): pass
    def load(self): return self.client is not None

def get_vector_store():
    use_qdrant = os.getenv("USE_QDRANT", "false").lower() == "true"
    return QdrantVectorStore() if use_qdrant else FAISSVectorStore()"""
content = content.replace(s2_old, s2_new, 1)

# Snippet 3
s3_old = """    _save_embed_cache(cache)
    faiss_index = build_faiss_index(vecs)
    bm25_obj = None"""
s3_new = """    _save_embed_cache(cache)
    vector_store = get_vector_store()
    vector_store.add(vecs, metas)
    vector_store.persist()
    faiss_index = vector_store
    bm25_obj = None"""
content = content.replace(s3_old, s3_new, 1)

# Snippet 4
s4_old = """        if FAISS_INDEX_PATH.exists() and faiss is not None:
            kb["faiss"] = faiss.read_index(str(FAISS_INDEX_PATH))"""
s4_new = """        vs = get_vector_store()
        if vs.load():
            kb["faiss"] = vs"""
content = content.replace(s4_old, s4_new, 1)

# Snippet 5
s5_old = """        qv = emb.encode([query])[0].astype("float32")
        D, I = idx.search(np.array([qv]), topk)
        dists = D[0]
        sims = [1.0 / (1.0 + d) for d in dists]
        min_sim, max_sim = min(sims), max(sims)
        normalized = [(s - min_sim) / (max_sim - min_sim + 1e-8) for s in sims] if max_sim != min_sim else [1.0]*len(sims)
        for pos, i in enumerate(I[0]):
            if 0 <= i < len(kb.get("chunks", [])):
                score_val = normalized[pos]
                scores[i] = max(0.0, min(1.0, float(score_val)))"""
s5_new = """        qv = emb.encode([query])[0].astype("float32")
        dists, I = idx.search(qv, topk)
        if len(dists) == 0: return scores
        sims = [1.0 / (1.0 + d) for d in dists]
        min_sim, max_sim = min(sims), max(sims)
        normalized = [(s - min_sim) / (max_sim - min_sim + 1e-8) for s in sims] if max_sim != min_sim else [1.0]*len(sims)
        for pos, i in enumerate(I):
            if 0 <= i < len(kb.get("chunks", [])):
                score_val = normalized[pos]
                scores[i] = max(0.0, min(1.0, float(score_val)))"""
content = content.replace(s5_old, s5_new, 1)

# Snippet 6
s6_old = """def hybrid_retrieve(query: str, kb: Dict[str, Any], topk: int = 6, rerank_topk: int = 6, boost_terms: List[str] = None, reranker_model: str = None) -> List[Dict[str, Any]]:
    chunks = kb.get("chunks", [])
    metas = kb.get("metas", [])
    if not chunks:
        return []
    terms = expand_query_terms(query)
    merged_scores: Dict[int, float] = {}
    merged_scores.update(_bm25_scores(terms, kb))
    merged_scores.update({k: merged_scores.get(k, 0) + v for k, v in _faiss_scores(query, kb, topk=max(topk, 12)).items()})
    if not merged_scores:
        for i, ch in enumerate(chunks):
            cnt = sum(1 for t in terms if t in ch.lower())
            if cnt > 0:
                merged_scores[i] = float(cnt)
    _apply_boosts(merged_scores, chunks, boost_terms or BOOST_TERMS)
    prelim = sorted(merged_scores.items(), key=lambda x: -x[1])[:max(topk, rerank_topk)]
    candidates = [{"source": chunks[i], "meta": metas[i], "score": max(0.0, min(1.0, float(s)))} for i, s in prelim]
    if reranker_model and CrossEncoder is not None:
        reranker = load_reranker()
        if reranker:
            pairs = [(query, c["source"]) for c in candidates[:rerank_topk]]
            try:
                scores = reranker.predict(pairs)
                min_score = min(scores) if len(scores) > 0 else 0
                max_score = max(scores) if len(scores) > 0 else 1
                score_range = max_score - min_score
                for j, s in enumerate(scores):
                    normalized_score = (s - min_score) / (score_range + 1e-8) if score_range > 0 else 0.5
                    normalized_score = max(0.0, min(1.0, normalized_score))
                    candidates[j]["rerank_score"] = normalized_score
                candidates = sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)
            except Exception as e:
                st.warning(f"Reranking failed: {e}")
    return candidates[:topk]"""
s6_new = """def hybrid_retrieve(query: str, kb: Dict[str, Any], topk: int = 6, rerank_topk: int = 6, boost_terms: List[str] = None, reranker_model: str = None, faiss_weight: float = 0.5, bm25_weight: float = 0.5) -> List[Dict[str, Any]]:
    import time
    t_start = time.time()
    chunks = kb.get("chunks", [])
    metas = kb.get("metas", [])
    if not chunks:
        log_rag_event("retrieval_failure", {"query": query, "reason": "empty_kb"})
        return []
    terms = expand_query_terms(query)
    merged_scores: Dict[int, float] = {}
    
    bm25_results = _bm25_scores(terms, kb)
    faiss_results = _faiss_scores(query, kb, topk=max(topk, 12))
    
    all_keys = set(bm25_results.keys()).union(set(faiss_results.keys()))
    for k in all_keys:
        score = (bm25_results.get(k, 0) * bm25_weight) + (faiss_results.get(k, 0) * faiss_weight)
        merged_scores[k] = score
        
    if not merged_scores:
        for i, ch in enumerate(chunks):
            cnt = sum(1 for t in terms if t in ch.lower())
            if cnt > 0:
                merged_scores[i] = float(cnt)
    _apply_boosts(merged_scores, chunks, boost_terms or BOOST_TERMS)
    prelim = sorted(merged_scores.items(), key=lambda x: -x[1])[:max(topk, rerank_topk)]
    candidates = [{"source": chunks[i], "meta": metas[i], "score": max(0.0, min(1.0, float(s)))} for i, s in prelim]
    
    if reranker_model and CrossEncoder is not None:
        t_rerank_start = time.time()
        reranker = load_reranker()
        if reranker:
            pairs = [(query, c["source"]) for c in candidates[:rerank_topk]]
            try:
                scores = reranker.predict(pairs)
                min_score = min(scores) if len(scores) > 0 else 0
                max_score = max(scores) if len(scores) > 0 else 1
                score_range = max_score - min_score
                for j, s in enumerate(scores):
                    normalized_score = (s - min_score) / (score_range + 1e-8) if score_range > 0 else 0.5
                    normalized_score = max(0.0, min(1.0, normalized_score))
                    candidates[j]["rerank_score"] = normalized_score
                candidates = sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)
                
                final_candidates = []
                seen_texts = set()
                for c in candidates:
                    txt_prefix = c["source"][:100].lower()
                    if txt_prefix not in seen_texts:
                        seen_texts.add(txt_prefix)
                        final_candidates.append(c)
                candidates = final_candidates
                log_rag_event("reranking_success", {"latency": time.time() - t_rerank_start, "candidates_count": len(candidates)})
            except Exception as e:
                st.warning(f"Reranking failed: {e}")
                log_rag_event("reranking_failure", {"error": str(e)})
    
    final_results = candidates[:topk]
    log_rag_event("retrieval_success", {"query": query, "latency": time.time() - t_start, "retrieved_count": len(final_results)})
    return final_results"""
content = content.replace(s6_old, s6_new, 1)

# Snippet 7
s7_old = """    return (answer.strip(), verification, followups)"""
s7_new = """    log_rag_event("llm_generation", {
        "question": question,
        "answer_length": len(answer),
        "citations_found": bool(verification and "claim" in verification)
    })
    return (answer.strip(), verification, followups)"""
content = content.replace(s7_old, s7_new, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("helps.py successfully patched.")
