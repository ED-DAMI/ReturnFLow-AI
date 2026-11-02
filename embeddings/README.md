# RAG embeddings

ReturnFlow uses separate components for retrieval and text generation:

- **Embeddings:** `intfloat/multilingual-e5-small` runs locally through Sentence Transformers. It supports the French and English material in this corpus and produces 384-dimensional vectors. No embeddings API key is needed.
- **Vector storage:** PostgreSQL with pgvector stores the indexed passages and their source metadata.
- **Chat generation:** the API and BPMN worker call Groq through its OpenAI-compatible chat endpoint. The request includes the user query and selected RAG passages, so use only content approved for that cloud service. The Groq key is only used for generation; Groq is not used to embed documents or queries.

## Index the corpus

From the project root, start PostgreSQL and install the project dependencies, then run:

```powershell
uv run python embeddings/ingest_rag_documents.py
```

The manifest enables exactly one source: `rag_documents/Synthese_Politique_de_Retour_SHEIN_Maroc.pdf`. The indexer rejects any other enabled PDF, extracts text and page numbers, splits it into 420-token passages with 60-token overlap, and stores E5 `passage:` vectors in `returnflow_rag_embeddings`. Every vector row keeps its passage text and vector together with the chunk ID, source PDF SHA-256, source page, chunk ordinal, exact half-open character offsets into that page's pypdf-extracted text, page-text and chunk SHA-256 hashes, chunking settings, and embedding model details. The API includes these trace references with each retrieved source so a passage can be checked against the exact PDF version and located in its source page. Re-running it replaces this pipeline's previous index in a database transaction. Retrieval filters on this exact source ID as well, so stale vectors from other PDFs cannot be returned. The API embeds each question using the matching E5 `query:` prefix.

The 60-token overlap is a configurable starting point, not a measured optimum. With 420-token chunks it limits repeated text and vector storage while retaining some context across boundaries. Raising it to 100 may help if a policy condition is frequently split across chunks, but it repeats more text and can increase the number of passages. Compare retrieval on representative policy questions before choosing a final value; set `RAG_CHUNK_OVERLAP` in `.env` and re-run ingestion to rebuild the vectors.

The default embedding model is `intfloat/multilingual-e5-small`; set `RAG_EMBEDDING_MODEL` consistently for both indexing and API use if changing it. The pgvector column is 384-dimensional for this default model.

Model weights are cached under the ignored project directory `.model-cache/` so indexing and serving use the same local copy. Set `RAG_EMBEDDING_LOCAL_ONLY=true` to prevent Hugging Face downloads and require the model to already exist in that cache.

The notebook and `vector_db_rules/` are an earlier single-summary-PDF experiment. They are not used by the current API index.
