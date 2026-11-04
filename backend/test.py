"""
Smoke test de l'API ReturnFlow AI (version Groq + embeddings locaux).

Usage :
    1. Terminal 1 :  python main.py            (API sur le port 8000)
    2. Terminal 2 :  python smoke_test.py

Dépendances : pip install requests python-dotenv psycopg2-binary
"""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

AGENT_URL = os.getenv("AGENT_URL", "http://localhost:8000")
RULES_TABLE = os.getenv("RULES_TABLE", "business_rules_embeddings")  # adaptez si besoin

OK, KO = "[OK]", "[KO]"
failures = 0
health = {}


def check(label, fn):
    global failures
    try:
        detail = fn()
        print(f"{OK} {label}" + (f" - {detail}" if detail else ""))
        return True
    except Exception as e:  # noqa: BLE001
        failures += 1
        print(f"{KO} {label} - {type(e).__name__}: {e}")
        return False


# --- 1. Environnement -------------------------------------------------------
def test_env():
    needed = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "GROQ_API_KEY"]
    missing = [k for k in needed if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"variables manquantes dans .env : {', '.join(missing)}")
    return "toutes presentes"


# --- 2. API en ligne --------------------------------------------------------
def test_health():
    r = requests.get(f"{AGENT_URL}/health", timeout=10)
    r.raise_for_status()
    health.update(r.json())
    return f"chat={health.get('chat_model')} | embeddings={health.get('embedding_model')}"


# --- 3. Base de données + pgvector -----------------------------------------
def get_conn():
    import psycopg2

    return psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"), connect_timeout=5,
    )


def test_db():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1")
    return "connexion OK"


def test_pgvector():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        row = cur.fetchone()
    if not row:
        raise RuntimeError("extension pgvector absente (CREATE EXTENSION vector;)")
    return f"pgvector {row[0]}"


def test_rows():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {RULES_TABLE}")
        n = cur.fetchone()[0]
    if n == 0:
        raise RuntimeError(f"table {RULES_TABLE} vide : le RAG ne retournera rien")
    return f"{n} regles indexees"


def test_dimension():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT atttypmod FROM pg_attribute "
            f"WHERE attrelid = '{RULES_TABLE}'::regclass AND attname = 'embedding'"
        )
        db_dim = cur.fetchone()[0]

    model_name = health.get("embedding_model")
    try:
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            from langchain_community.embeddings import HuggingFaceEmbeddings
        model_dim = len(HuggingFaceEmbeddings(model_name=model_name).embed_query("test"))
    except Exception:  # noqa: BLE001
        return f"colonne en {db_dim} dimensions (modele non verifie)"

    if model_dim != db_dim:
        raise RuntimeError(f"colonne en {db_dim} dimensions mais {model_name} produit {model_dim}")
    return f"{db_dim} dimensions (colonne = modele)"


# --- 4. Groq ----------------------------------------------------------------
def test_groq():
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"},
        json={
            "model": health.get("chat_model", "llama-3.3-70b-versatile"),
            "messages": [{"role": "user", "content": "Reponds juste: OK"}],
            "max_tokens": 10,
        },
        timeout=20,
    )
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} : {r.text[:200]}")
    return f"reponse : {r.json()['choices'][0]['message']['content'].strip()[:30]!r}"


# --- 5. Endpoint /process-return -------------------------------------------
def test_validation():
    r = requests.post(f"{AGENT_URL}/process-return", json={}, timeout=10)
    assert r.status_code == 422, f"attendu 422, recu {r.status_code}"
    return "payload invalide rejete (422)"


def test_process_return():
    payload = {
        "client_query": (
            "J'ai recu une robe avec une dechirure a la couture. "
            "Je voudrais la retourner pour un remboursement."
        ),
        "order_id": "TEST-0001",
    }
    r = requests.post(f"{AGENT_URL}/process-return", json=payload, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} : {r.text[:300]}")
    body = r.json()
    assert body.get("status") == "success", f"status inattendu : {body.get('status')}"
    assert body.get("order_id") == "TEST-0001", "order_id non renvoye"
    assert body.get("response"), "champ 'response' vide"
    assert isinstance(body.get("sources"), list), "champ 'sources' absent"
    assert isinstance(body.get("needs_human_review"), bool), "champ 'needs_human_review' absent"
    if not body["sources"]:
        print("    ! sources vide : le RAG n'a retrouve aucune regle")
    print(f"    sources : {body['sources']}")
    print(f"    needs_human_review : {body['needs_human_review']}")
    print("    reponse :\n    " + body["response"][:500].replace("\n", "\n    "))
    return "200 + reponse valide"


if __name__ == "__main__":
    print(f"API testee : {AGENT_URL}\n")
    env_ok = check("Variables d'environnement", test_env)
    api_ok = check("API en ligne (/health)", test_health)
    if env_ok:
        if check("Connexion PostgreSQL", test_db):
            check("Extension pgvector", test_pgvector)
            check(f"Table {RULES_TABLE}", test_rows)
            if api_ok:
                check("Dimension des vecteurs", test_dimension)
        check("Appel Groq", test_groq)
    if api_ok:
        check("Validation des entrees", test_validation)
        check("Endpoint /process-return (RAG + LLM)", test_process_return)

    print()
    if failures:
        print(f"{KO} {failures} test(s) en echec")
        sys.exit(1)
    print(f"{OK} Tout fonctionne")