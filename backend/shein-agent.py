from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Optional
import os
from dotenv import load_dotenv
import psycopg2
from pgvector.psycopg2 import register_vector
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()
app = FastAPI(title="Shein Return AI Agent - Camunda Worker")

# --- 1. Définition de l'état LangGraph ---
class ReturnState(TypedDict):
    client_query: str
    retrieved_rules: str
    response: Optional[str]


embeddings_model = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def retrieve_rules_node(state: ReturnState):
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD")
    )
    register_vector(conn)
    cur = conn.cursor()
    
    query_vector = embeddings_model.embed_query(state["client_query"])
    cur.execute("SELECT content FROM business_rules_embeddings ORDER BY embedding <=> %s::vector LIMIT 3;", (query_vector,))
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return {"retrieved_rules": "\n\n".join([row[0] for row in results])}

def generate_response_node(state: ReturnState):
    system_prompt = f"Tu es l'agent expert retours SHEIN. Applique strictement ces règles :\n{state['retrieved_rules']}"
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=state["client_query"])]
    ai_response = llm.invoke(messages)
    return {"response": ai_response.content}

# Assemblage LangGraph
workflow = StateGraph(ReturnState)
workflow.add_node("retrieve_rules", retrieve_rules_node)
workflow.add_node("generate_response", generate_response_node)
workflow.add_edge(START, "retrieve_rules")
workflow.add_edge("retrieve_rules", "generate_response")
workflow.add_edge("generate_response", END)
return_agent_graph = workflow.compile()

# --- 3. Modèle de données pour Camunda ---
class ReturnRequest(BaseModel):
    client_query: str
    order_id: Optional[str] = None

@app.post("/process-return")
def process_return_task(data: ReturnRequest):
    try:
        initial_state = {
            "client_query": data.client_query,
            "retrieved_rules": "",
            "response": None
        }
        
        # Exécution du graphe LangGraph
        final_state = return_agent_graph.invoke(initial_state)
        
        return {
            "status": "success",
            "order_id": data.order_id,
            "ai_decision": final_state["response"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)