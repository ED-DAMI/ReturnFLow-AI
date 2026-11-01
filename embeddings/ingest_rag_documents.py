"""Embed every RAG-enabled PDF from the manifest into PostgreSQL/pgvector."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import psycopg2
import tiktoken
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pgvector.psycopg2 import register_vector
from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAG_DIR = PROJECT_ROOT / "rag_documents"
MANIFEST_PATH = RAG_DIR / "manifest.csv"
PIPELINE_ID = "returnflow_manifest_v1"
DEFAULT_MODEL = "intfloat/multilingual-e5-small"
EMBEDDING_DIMENSIONS = 384

load_dotenv(PROJECT_ROOT / ".env")


def read_manifest() -> list[dict[str, str]]:
    rag_root = RAG_DIR.resolve()
    entries = []
    missing = []
    with MANIFEST_PATH.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["use_for_rag"].strip().lower() != "true":
                continue
            path = (RAG_DIR / row["file"]).resolve()
            if not path.is_relative_to(rag_root):
                raise ValueError(f"Manifest path escapes rag_documents/: {row['file']}")
            if not path.is_file():
                missing.append(row["file"])
                continue
            entries.append({**row, "resolved_path": str(path)})
    if missing:
        raise FileNotFoundError("Missing RAG manifest files: " + ", ".join(missing))
    if not entries:
        raise ValueError("The RAG manifest contains no files enabled for indexing.")
    return entries


def build_chunks(entries: list[dict[str, str]]) -> list[dict[str, Any]]:
    tokenizer = tiktoken.get_encoding("cl100k_base")
    chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "420"))
    chunk_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "60"))
    if chunk_size <= chunk_overlap or chunk_overlap < 0:
        raise ValueError("RAG_CHUNK_SIZE must be greater than RAG_CHUNK_OVERLAP >= 0.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=lambda text: len(tokenizer.encode(text)),
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks: list[dict[str, Any]] = []
    for entry in entries:
        source_id = Path(entry["file"]).as_posix()
        reader = PdfReader(entry["resolved_path"])
        for page_index, pdf_page in enumerate(reader.pages):
            page_text = pdf_page.extract_text() or ""
            if not page_text.strip():
                continue
            page_document = Document(page_content=page_text, metadata={"page": page_index})
            for chunk_index, document in enumerate(splitter.split_documents([page_document])):
                content = document.page_content.strip()
                if not content:
                    continue
                page = page_index + 1
                digest = hashlib.sha256(
                    f"{source_id}|{page}|{chunk_index}|{content}".encode("utf-8")
                ).hexdigest()
                metadata = {
                    "source_id": source_id,
                    "source_type": entry["source_type"],
                    "language": entry["language"],
                    "country": entry["country"],
                    "page": page,
                    "chunk_index": chunk_index,
                    "embedding_pipeline": PIPELINE_ID,
                }
                chunks.append({"chunk_id": digest, "content": content, "metadata": metadata})
    if not chunks:
        raise ValueError("No non-empty PDF passages were extracted from the RAG manifest.")
    return chunks


def connect_database():
    required = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("Missing database settings in .env: " + ", ".join(missing))
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def store_chunks(chunks: list[dict[str, Any]], vectors: list[list[float]]) -> None:
    if len(chunks) != len(vectors):
        raise ValueError("Each RAG passage must have exactly one embedding.")
    if any(len(vector) != EMBEDDING_DIMENSIONS for vector in vectors):
        raise ValueError(f"The configured embedding model must produce {EMBEDDING_DIMENSIONS}-dimensional vectors.")

    conn = connect_database()
    try:
        with conn.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()
        register_vector(conn)
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS returnflow_rag_embeddings (
                    chunk_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata JSONB NOT NULL,
                    embedding vector({EMBEDDING_DIMENSIONS}) NOT NULL
                );
                """
            )
            cursor.execute(
                "DELETE FROM returnflow_rag_embeddings WHERE metadata->>'embedding_pipeline' = %s;",
                (PIPELINE_ID,),
            )
            cursor.executemany(
                """
                INSERT INTO returnflow_rag_embeddings (chunk_id, content, metadata, embedding)
                VALUES (%s, %s, %s::jsonb, %s)
                ON CONFLICT (chunk_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding;
                """,
                [
                    (chunk["chunk_id"], chunk["content"], json.dumps(chunk["metadata"], ensure_ascii=False), vector)
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ],
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    entries = read_manifest()
    chunks = build_chunks(entries)
    model_name = os.getenv("RAG_EMBEDDING_MODEL", DEFAULT_MODEL)
    embedding_model = HuggingFaceEmbeddings(
        model_name=model_name,
        encode_kwargs={"normalize_embeddings": True},
    )
    # E5 expects these task prefixes for retrieval, including non-English text.
    passage_texts = [f"passage: {chunk['content']}" for chunk in chunks]
    vectors = embedding_model.embed_documents(passage_texts)
    store_chunks(chunks, vectors)
    print(f"Indexed {len(chunks)} chunks from {len(entries)} manifest PDFs into returnflow_rag_embeddings.")


if __name__ == "__main__":
    main()
