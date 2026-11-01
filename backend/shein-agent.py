"""FastAPI RAG prototype; this is not a Camunda Zeebe job worker."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pgvector.psycopg2 import register_vector
from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

RAG_PIPELINE_ID = "returnflow_manifest_v1"
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

app = FastAPI(title="ReturnFlow AI RAG API (prototype)")


class ReturnState(TypedDict):
    client_query: str
    retrieved_rules: str
    sources: list[dict]
    response: str | None
    needs_human_review: bool


embeddings_model = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL,
    encode_kwargs={"normalize_embeddings": True},
)


def create_llm() -> ChatOpenAI:
    """Create a Groq chat client through its OpenAI-compatible endpoint."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Set GROQ_API_KEY in .env before requesting a generated response.")
    return ChatOpenAI(
        model=GROQ_MODEL,
        api_key=api_key,
        base_url=GROQ_BASE_URL,
        temperature=0.1,
    )


def retrieve_rules_node(state: ReturnState) -> dict:
    query_vector = embeddings_model.embed_query(f"query: {state['client_query']}")
    db_settings = {
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_PORT": os.getenv("DB_PORT"),
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
    }
    missing = [name for name, value in db_settings.items() if not value]
    if missing:
        raise RuntimeError("Missing database settings in .env: " + ", ".join(missing))
    conn = psycopg2.connect(
        host=db_settings["DB_HOST"],
        port=db_settings["DB_PORT"],
        database=db_settings["DB_NAME"],
        user=db_settings["DB_USER"],
        password=db_settings["DB_PASSWORD"],
    )
    try:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT content, metadata, embedding <=> %s::vector AS distance
                FROM returnflow_rag_embeddings
                WHERE metadata->>'embedding_pipeline' = %s
                ORDER BY embedding <=> %s::vector
                LIMIT 4;
                """,
                (query_vector, RAG_PIPELINE_ID, query_vector),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    passages = []
    sources = []
    for content, metadata, distance in rows:
        source_id = metadata["source_id"]
        page = int(metadata["page"])
        citation = f"{source_id}, page {page}"
        passages.append(f"[Source: {citation}]\n{content}")
        sources.append(
            {
                "source_id": source_id,
                "page": page,
                "source_type": metadata.get("source_type", "unknown"),
                "similarity": round(1 - float(distance), 4),
            }
        )
    return {"retrieved_rules": "\n\n---\n\n".join(passages), "sources": sources}


def generate_response_node(state: ReturnState) -> dict:
    rules = state["retrieved_rules"].strip()
    if not rules:
        return {
            "response": "Aucun extrait pertinent n’a été retrouvé. Une vérification par un agent SAV est nécessaire.",
            "needs_human_review": True,
        }

    system_prompt = (
        "Tu es l’assistant RAG ReturnFlow AI. Réponds en français en t’appuyant uniquement sur les extraits fournis. "
        "N’invente aucune règle ni source. Cite les passages utilisés avec leur identifiant de source et leur page. "
        "Si les extraits ne suffisent pas, indique-le clairement et demande une vérification humaine.\n\n"
        f"Extraits récupérés :\n{rules}"
    )
    response = create_llm().invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=state["client_query"])]
    )
    return {"response": str(response.content), "needs_human_review": False}


workflow = StateGraph(ReturnState)
workflow.add_node("retrieve_rules", retrieve_rules_node)
workflow.add_node("generate_response", generate_response_node)
workflow.add_edge(START, "retrieve_rules")
workflow.add_edge("retrieve_rules", "generate_response")
workflow.add_edge("generate_response", END)
return_agent_graph = workflow.compile()


class ReturnRequest(BaseModel):
    client_query: str
    order_id: str | None = None


@app.post("/process-return")
def process_return_task(data: ReturnRequest) -> dict:
    try:
        final_state = return_agent_graph.invoke(
            {
                "client_query": data.client_query,
                "retrieved_rules": "",
                "sources": [],
                "response": None,
                "needs_human_review": False,
            }
        )
        return {
            "status": "success",
            "order_id": data.order_id,
            "response": final_state["response"],
            "sources": final_state["sources"],
            "needs_human_review": final_state["needs_human_review"],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
