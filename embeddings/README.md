# RAG embeddings

ReturnFlow uses separate components for retrieval and text generation:

- **Embeddings:** `intfloat/multilingual-e5-small` runs locally through Sentence Transformers. It supports the French and English material in this corpus and produces 384-dimensional vectors. No embeddings API key is needed.
- **Vector storage:** PostgreSQL with pgvector stores the indexed passages and their source metadata.
- **Chat generation:** the API calls Groq through its OpenAI-compatible chat endpoint. The Groq key is only used for generation; Groq is not used to embed documents or queries.

## Index the corpus

From the project root, start PostgreSQL and install the project dependencies, then run:

```powershell
uv run python embeddings/ingest_rag_documents.py
```

The indexer reads only manifest entries marked `use_for_rag=true`, extracts PDF text and page numbers, splits it into 420-token passages with 60-token overlap, and stores E5 `passage:` vectors in `returnflow_rag_embeddings`. Re-running it replaces this pipeline's index in a database transaction. The API embeds each question using the matching E5 `query:` prefix and returns source IDs and page numbers with the answer.

The default embedding model is `intfloat/multilingual-e5-small`; set `RAG_EMBEDDING_MODEL` consistently for both indexing and API use if changing it. The pgvector column is 384-dimensional for this default model.

The notebook and `vector_db_rules/` are an earlier single-summary-PDF experiment. They are not used by the current API index.
