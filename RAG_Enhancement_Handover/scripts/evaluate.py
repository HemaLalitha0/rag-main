import json
import time
import math
import helps
import os

# Helper functions for metrics
def calculate_mrr(retrieved, expected_phrase):
    for i, res in enumerate(retrieved):
        if expected_phrase and expected_phrase in res.get("source", ""):
            return 1.0 / (i + 1)
    return 0.0

def calculate_ndcg(retrieved, expected_phrase, k):
    dcg = 0.0
    rel_count = 0
    for i, res in enumerate(retrieved[:k]):
        if expected_phrase and expected_phrase in res.get("source", ""):
            dcg += 1.0 / math.log2(i + 2)
            rel_count += 1
            
    if rel_count == 0:
        return 0.0
        
    idcg = 0.0
    for i in range(rel_count):
        idcg += 1.0 / math.log2(i + 2)
        
    return dcg / idcg

def evaluate(faiss_weight=0.5, bm25_weight=0.5, results_file="evaluation_results.json"):
    print("Loading eval dataset...")
    if not os.path.exists("eval_dataset.json"):
        print("Dataset not found.")
        return
        
    with open("eval_dataset.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    print("Loading KB...")
    kb = helps.load_persisted_kb()
    if not kb.get("chunks"):
        print("KB is empty. Need to index first. Proceeding with empty KB for baseline test.")
        
    router = helps.LLMClient()
    
    results = []
    
    total_prec = 0.0
    total_recall = 0.0
    total_mrr = 0.0
    total_ndcg = 0.0
    total_retrieval_latency = 0.0
    total_gen_latency = 0.0
    
    k = 5
    print(f"Evaluating {len(dataset)} queries with faiss={faiss_weight}, bm25={bm25_weight}...")
    for item in dataset:
        q = item["question"]
        expected_chunk = item["relevant_chunk"]
        
        # Retrieval
        t0 = time.time()
        candidates = helps.hybrid_retrieve(q, kb, topk=k, rerank_topk=k, reranker_model=None, faiss_weight=faiss_weight, bm25_weight=bm25_weight) 
        t1 = time.time()
        
        retrieval_latency = t1 - t0
        total_retrieval_latency += retrieval_latency
        
        # Evaluate retrieval
        # Since our dataset is synthetic and the KB might not have the exact chunks,
        # we do a simulated check. If the KB is empty, all retrieval metrics are 0.
        is_relevant = False
        prec = 0.0
        rec = 0.0
        mrr = 0.0
        ndcg = 0.0
        
        if candidates and expected_chunk:
            mrr = calculate_mrr(candidates, expected_chunk)
            ndcg = calculate_ndcg(candidates, expected_chunk, k)
            rel_in_k = sum(1 for res in candidates[:k] if expected_chunk in res.get("source", ""))
            prec = rel_in_k / k
            rec = 1.0 if rel_in_k > 0 else 0.0
                
        total_prec += prec
        total_recall += rec
        total_mrr += mrr
        total_ndcg += ndcg
        
        # Generation
        t2 = time.time()
        answer, verification, followups = helps.synthesize_answer(router, q, candidates, model_choice="gemini-2.5-flash")
        t3 = time.time()
        
        gen_latency = t3 - t2
        total_gen_latency += gen_latency
        
        results.append({
            "id": item["id"],
            "question": q,
            "retrieval_latency": retrieval_latency,
            "gen_latency": gen_latency,
            "prec_at_k": prec,
            "recall_at_k": rec,
            "mrr": mrr,
            "ndcg": ndcg,
            "answer": answer,
            "verification": verification
        })
        
    num_q = len(dataset)
    metrics = {
        "precision_at_k": total_prec / num_q,
        "recall_at_k": total_recall / num_q,
        "mrr": total_mrr / num_q,
        "ndcg": total_ndcg / num_q,
        "avg_retrieval_latency": total_retrieval_latency / num_q,
        "avg_gen_latency": total_gen_latency / num_q
    }
    
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics, "details": results}, f, indent=2)
        
    print(f"Evaluation complete for {results_file}:")
    print(json.dumps(metrics, indent=2))
    return metrics

if __name__ == "__main__":
    import sys
    fw = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
    bw = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    evaluate(faiss_weight=fw, bm25_weight=bw)
