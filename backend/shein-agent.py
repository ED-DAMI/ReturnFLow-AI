"""FastAPI RAG demo API; the separate Zeebe worker is backend/zeebe_worker.py."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from returnflow_core import (
    EMBEDDING_MODEL,
    GROQ_MODEL,
    ReturnState,
    run_return_agent,
)


app = FastAPI(title="ReturnFlow AI RAG API (prototype)")


class ReturnRequest(BaseModel):
    client_query: str
    order_id: str | None = None


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "returnflow-rag-api",
        "chat_model": GROQ_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "embeddings": "local",
    }


@app.post("/process-return")
def process_return_task(data: ReturnRequest) -> dict:
    try:
        initial_state: ReturnState = {
            "client_query": data.client_query,
            "retrieved_rules": "",
            "sources": [],
            "response": None,
            "needs_human_review": False,
        }
        final_state = run_return_agent(initial_state)
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
