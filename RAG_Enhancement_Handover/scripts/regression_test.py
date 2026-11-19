import helps

def run_regression_test():
    print("--- REGRESSION TEST ---")
    
    # 1. FAISS Store
    print("Testing Vector Store Initialization...")
    vs = helps.get_vector_store()
    print("Vector Store:", type(vs).__name__)
    
    # 2. Normal query with Reranking and Logging
    print("\nTesting Normal Query...")
    kb = helps.load_persisted_kb()
    q = "Why is leadership a human activity?"
    candidates = helps.hybrid_retrieve(q, kb, topk=2, rerank_topk=5)
    print(f"Retrieved {len(candidates)} candidates.")
    if candidates:
        print(f"Top candidate source snippet: {candidates[0]['source'][:100]}...")
        
    # 3. Empty retrieval (simulate by creating dummy KB or querying gibberish)
    print("\nTesting Empty Retrieval/Fallback...")
    candidates_empty = helps.hybrid_retrieve("zxczxc qweqwe asdasd", kb, topk=2)
    print(f"Retrieved {len(candidates_empty)} candidates for gibberish query.")
    
    print("\nRegression test completed successfully (without LLM api calls).")

if __name__ == "__main__":
    run_regression_test()
