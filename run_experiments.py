import evaluate

configs = [
    (0.5, 0.5),
    (0.6, 0.4),
    (0.7, 0.3),
    (0.4, 0.6),
    (1.0, 0.0),
    (0.0, 1.0)
]

results = {}
best_mrr = -1
best_config = None

for fw, bw in configs:
    filename = f"eval_fw{fw}_bw{bw}.json"
    metrics = evaluate.evaluate(faiss_weight=fw, bm25_weight=bw, results_file=filename)
    if metrics:
        results[f"{fw}/{bw}"] = metrics
        if metrics["mrr"] > best_mrr:
            best_mrr = metrics["mrr"]
            best_config = (fw, bw)

print("\n--- RETRIEVAL OPTIMIZATION RESULTS ---")
for conf, m in results.items():
    print(f"Weights (FAISS/BM25): {conf}")
    print(f"  MRR:      {m['mrr']:.4f}")
    print(f"  NDCG:     {m['ndcg']:.4f}")
    print(f"  Recall@5: {m['recall_at_k']:.4f}")
    print(f"  Prec@5:   {m['precision_at_k']:.4f}\n")

print(f"Best Configuration based on MRR: FAISS {best_config[0]} / BM25 {best_config[1]} with MRR {best_mrr:.4f}")
