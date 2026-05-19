# RAG Artifacts

- `corpus_manifest.json`: build manifest for the current local RAG corpus snapshot, including source paths, chunk counts, and known limitations.
- `retrieval_baseline_report.json`: latest sparse retrieval smoke report produced by `scripts/build_rag_corpus.py`.

This directory intentionally does not contain embeddings or reranker artifacts yet. Week 7 only establishes the reproducible corpus and sparse baseline foundation.
