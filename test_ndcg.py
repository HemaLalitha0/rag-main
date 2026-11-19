import math

def calculate_mrr(retrieved, expected_phrase):
    for i, res in enumerate(retrieved):
        if expected_phrase and expected_phrase in res.get("source", ""):
            return 1.0 / (i + 1)
    return 0.0

def calculate_ndcg(retrieved, expected_phrase, k):
    dcg = 0.0
    idcg = 1.0 # Max 1 relevant document
    for i, res in enumerate(retrieved[:k]):
        if expected_phrase and expected_phrase in res.get("source", ""):
            dcg += 1.0 / math.log2(i + 2)
    return dcg / idcg

# Test cases
# 1: relevant document is ranked first
ret1 = [{"source": "A text containing the expected phrase."}]
print("Rank 1 - MRR:", calculate_mrr(ret1, "expected phrase"), "NDCG:", calculate_ndcg(ret1, "expected phrase", 5))

# 2: relevant document is ranked second
ret2 = [{"source": "Not relevant"}, {"source": "A text containing the expected phrase."}]
print("Rank 2 - MRR:", calculate_mrr(ret2, "expected phrase"), "NDCG:", calculate_ndcg(ret2, "expected phrase", 5))

# 3: no relevant document exists
ret3 = [{"source": "Not relevant"}]
print("No Rel - MRR:", calculate_mrr(ret3, "expected phrase"), "NDCG:", calculate_ndcg(ret3, "expected phrase", 5))

# 4: multiple relevant documents exist
ret4 = [{"source": "Not relevant"}, {"source": "A text containing the expected phrase."}, {"source": "Another expected phrase here."}]
print("Multi Rel - MRR:", calculate_mrr(ret4, "expected phrase"), "NDCG:", calculate_ndcg(ret4, "expected phrase", 5))
