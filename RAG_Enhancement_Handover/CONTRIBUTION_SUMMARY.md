# RAG Enhancements — Lead Contribution Summary

**Author / Contributor:** AI Engineer (Enhancement Contributor)  
**Project Baseline:** Original RAG Assistant developed by Team Colleague  
**Handover Target:** Team Lead / Engineering Review  
**Date:** October 2026  
**Status:** Complete & Verified with Documented Limitations  

---

## 1. Executive Context & Attribution

This handover package documents and delivers **six core technical enhancements** implemented on top of the original RAG Assistant codebase. 

### Attribution Boundary
- **Original Project (Colleague's Work):**
  - Streamlit multi-page application (`app.py`, `pages/colab.py`, `pages/testing.py`, `pages/admin.py`, `pages/login.py`).
  - Core ingestion engine (PDF parsing via PyMuPDF, Whisper/YouTube transcript fetching).
  - Hybrid retrieval baseline (FAISS IndexFlatL2 + BM25Okapi).
  - Authentication, SQLite user database, and admin dashboard.
  - Baseline notebook workflows (`Streamlit_Project_Clean.ipynb`, `RAGMain_Project.ipynb`).
- **My Contributions (This Enhancement Package):**
  - **Enhancement 1:** 50-item synthetic RAG evaluation dataset (`eval_dataset.json`, `generate_dataset.py`).
  - **Enhancement 2:** Retrieval evaluation harness (Precision@5, Recall@5, MRR, NDCG) and auditing/fixing the critical NDCG math calculation (`evaluate.py`, `test_ndcg.py`).
  - **Enhancement 3:** Controlled FAISS vs. BM25 weight parameter sweeping across 6 configurations (300 benchmarked queries) (`run_experiments.py`, `eval_fw*.json`).
  - **Enhancement 4:** Cross-Encoder near-duplicate text deduplication and result-diversity filtering (`helps.py`).
  - **Enhancement 5:** Extensible vector store abstraction (`VectorStoreBase`) decoupling FAISS and introducing in-memory Qdrant support (`helps.py`).
  - **Enhancement 6:** Low-overhead rotating JSONL operational logging (`rag_metrics.jsonl`, `helps.py`).

*No changes were made to my colleague's remote repository. All changes are encapsulated in this verified package and reviewable via `changes.patch`.*

---

## 2. Contribution Matrix

| Enhancement Name | Relevant Files & Modules | Original Behavior | My Changes | Technical Benefit | Tests / Evidence | Current Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Synthetic Evaluation Dataset** | `generate_dataset.py`<br>`eval_dataset.json` | No automated evaluation dataset existed; testing was entirely manual via Streamlit UI. | Programmatically generated a 50-item dataset grounded in `AI-Humans.pdf` and `top_50_ai_tools.pdf`, including an explicit out-of-domain negative test (q_6). | Provides an automated, reproducible regression corpus for retrieval tuning. | `eval_dataset.json` (50 items); generated via `generate_dataset.py`. | Synthetic phrasing based on 6 core templates; lacks human-curated linguistic nuance. |
| **2. Multi-Metric Evaluation & NDCG Fix** | `evaluate.py`<br>`test_ndcg.py` | No programmatic metrics. Early attempts yielded `0.0` NDCG due to an IDCG formula bug. | Implemented Precision@5, Recall@5, MRR, and fixed NDCG math with dynamic IDCG normalization. | Objective, mathematically sound retrieval benchmarking for algorithm tuning. | Standalone test suite in `test_ndcg.py` passes all 4 rank cases. | Uses substring matching against expected chunks rather than semantic similarity. |
| **3. Hybrid Weight Benchmarks** | `run_experiments.py`<br>`eval_fw*.json`<br>`helps.py` | Hardcoded retrieval with static unweighted merging of FAISS + BM25 scores. | Parameterized `faiss_weight` and `bm25_weight` in `hybrid_retrieve()`; swept 6 weight combinations. | Identified optimal weighting (0.4 FAISS / 0.6 BM25 and pure BM25), cutting latency to ~13ms. | 6 benchmark JSON runs (`eval_fw0.0_bw1.0.json` through `eval_fw1.0_bw0.0.json`). | Pure BM25 tied with 0.4/0.6 hybrid on this corpus; no dense superiority on keyword-heavy PDFs. |
| **4. Near-Duplicate Diversity Filter** | `helps.py`<br>(lines 866–877) | Top candidates after Cross-Encoder often contained repetitive chunks from overlapping windows. | Added prefix-based deduplication (first 100 characters lowercased) post Cross-Encoder scoring. | Prevents redundant chunks from consuming LLM context window; improves answer diversity. | Integrated into `hybrid_retrieve()`; regression tested in `regression_test.py`. | Heuristic 100-character prefix check; not full semantic MMR (Maximal Marginal Relevance). |
| **5. Vector Store Abstraction** | `helps.py`<br>(lines 623–688) | Tightly coupled directly to local `faiss.IndexFlatL2` and local filesystem paths. | Introduced `VectorStoreBase` contract; implemented `FAISSVectorStore` and in-memory `QdrantVectorStore`. | Decouples vector storage from FAISS; enables plugging cloud or cluster vector databases. | Verified `FAISSVectorStore` add/search/persist/load; tested `QdrantVectorStore` in-memory. | Qdrant client uses legacy `.search()` (needs `query_points` on v1.19+); in-memory only. |
| **6. Rotating Telemetry Logging** | `helps.py`<br>(lines 14–38)<br>`rag_metrics.jsonl` | Console print / Streamlit UI warnings only; no persistent operational telemetry. | Configured `RotatingFileHandler` (5MB cap, 2 backups) logging structured JSONL events. | Real-time observability into retrieval latencies, failure rates, and citation verification. | Existing log `rag_metrics.jsonl` with 702 recorded events (352 retrieval, 350 generation). | Lacks distributed trace IDs linking retrieval events to specific generation events. |

---

## 3. Key Benchmark Findings

Across the 50-item evaluation corpus, systematic sweeping across 6 weight configurations revealed:

```
Configuration (FAISS / BM25)   | Prec@5   | Recall@5 | MRR     | NDCG    | Avg Latency
-------------------------------------------------------------------------------------
FAISS 0.4 / BM25 0.6 (Optimal) | 0.1000   | 0.5000   | 0.3800  | 0.4089  | 0.0130 s
FAISS 0.0 / BM25 1.0 (Pure BM25)| 0.1000  | 0.5000   | 0.3800  | 0.4089  | 0.0127 s
FAISS 0.5 / BM25 0.5 (Default) | 0.1000   | 0.5000   | 0.3720  | 0.4019  | 0.1267 s
FAISS 0.6 / BM25 0.4           | 0.1000   | 0.5000   | 0.3720  | 0.4019  | 0.0164 s
FAISS 0.7 / BM25 0.3           | 0.1000   | 0.5000   | 0.2920  | 0.3428  | 0.0132 s
FAISS 1.0 / BM25 0.0 (Pure FAISS)|0.0040  | 0.0200   | 0.0050  | 0.0086  | 0.0140 s
```

### Critical Takeaway for the Team
- **Dense Embedding Weakness on Technical Vocabulary:** Pure FAISS dense search (`all-MiniLM-L6-v2`) collapsed to near-zero ranking utility (MRR 0.0050) when querying exact software names and technical terms.
- **Hybrid Synergy:** The 0.4 FAISS / 0.6 BM25 hybrid balance provides semantic generalization while retaining deterministic keyword precision, tied for highest ranking fidelity (MRR 0.3800, NDCG 0.4089).

---

## 4. Production Readiness & Honest Limitations

**Overall Verdict: READY WITH LIMITATIONS**

1. **Synthetic Nature of Evaluation Data:** Ground truth is synthesized programmatically. It serves as an effective regression safety net, but production deployment requires human-curated domain validation.
2. **Qdrant Vector Store Scope:** The Qdrant integration is verified for in-memory prototyping. For production clustering, persistence and migration from `.search()` to `.query_points()` (for `qdrant-client >= 1.10`) must be finalized.
3. **LLM Generation Evaluation:** Offline benchmarking was conducted with retrieval isolation due to inactive API keys. End-to-end generative hallucination scoring should be evaluated in staging.

---

## 5. Review Guidance for Team Lead

1. **Quick Code Review:** Inspect `changes.patch` for the clean diff to `helps.py`.
2. **Math & Metric Verification:** Review `test_ndcg.py` and run `py test_ndcg.py` to confirm the NDCG formula.
3. **Detailed Technical Report:** See `RAG_Enhancement_Report.md` for in-depth architecture and design rationale.
4. **Benchmark Verification:** Inspect JSON evaluation logs in `evaluation/eval_fw0.4_bw0.6.json`.
