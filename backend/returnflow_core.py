"""Shared RAG and BPMN task logic for the ReturnFlow prototype."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypedDict

# Keep local model loading within the memory budget of typical Windows machines.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
os.environ.setdefault("HF_HOME", str(PROJECT_ROOT / ".model-cache"))
LOGGER = logging.getLogger("returnflow")

RAG_PIPELINE_ID = "returnflow_manifest_v1"
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_MIN_SIMILARITY = float(os.getenv("RAG_MIN_SIMILARITY", "0.30"))
RETURN_WINDOW_DAYS = int(os.getenv("RETURN_WINDOW_DAYS", "30"))

_embeddings_model: Any = None


def get_embeddings_model() -> Any:
    """Load E5 on first retrieval, not while the API or worker is starting."""
    global _embeddings_model
    if _embeddings_model is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        local_only = _bool(os.getenv("RAG_EMBEDDING_LOCAL_ONLY", "false")) is True
        _embeddings_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"local_files_only": True} if local_only else {},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings_model


class ReturnState(TypedDict):
    client_query: str
    retrieved_rules: str
    sources: list[dict]
    response: str | None
    needs_human_review: bool


def create_llm() -> Any:
    """Create a Groq chat client through its OpenAI-compatible endpoint."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=GROQ_MODEL,
        api_key=api_key,
        base_url=GROQ_BASE_URL,
        temperature=0.1,
    )


def retrieve_policy(client_query: str) -> tuple[str, list[dict], list[float]]:
    """Retrieve policy passages using local E5 embeddings and pgvector."""
    query_vector = get_embeddings_model().embed_query(f"query: {client_query}")
    import psycopg2
    from pgvector.psycopg2 import register_vector

    db_settings = {
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_PORT": os.getenv("DB_PORT"),
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
    }
    missing = [name for name, value in db_settings.items() if not value]
    if missing:
        raise RuntimeError("Missing database settings: " + ", ".join(missing))

    conn = psycopg2.connect(
        host=db_settings["DB_HOST"],
        port=db_settings["DB_PORT"],
        database=db_settings["DB_NAME"],
        user=db_settings["DB_USER"],
        password=db_settings["DB_PASSWORD"],
        connect_timeout=5,
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
                LIMIT %s;
                """,
                (query_vector, RAG_PIPELINE_ID, query_vector, RAG_TOP_K),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    passages: list[str] = []
    sources: list[dict] = []
    scores: list[float] = []
    for content, metadata, distance in rows:
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        similarity = round(1 - float(distance), 4)
        if similarity < RAG_MIN_SIMILARITY:
            continue
        source_id = str(metadata.get("source_id", "unknown"))
        page = int(metadata.get("page", 0))
        citation = f"{source_id}, page {page}"
        passages.append(f"[Source: {citation}]\n{content}")
        sources.append(
            {
                "source_id": source_id,
                "page": page,
                "source_type": metadata.get("source_type", "unknown"),
                "similarity": similarity,
            }
        )
        scores.append(similarity)
    return "\n\n---\n\n".join(passages), sources, scores


def retrieve_rules_node(state: ReturnState) -> dict:
    rules, sources, _ = retrieve_policy(state["client_query"])
    return {"retrieved_rules": rules, "sources": sources}


def generate_response_node(state: ReturnState) -> dict:
    rules = state["retrieved_rules"].strip()
    if not rules:
        return {
            "response": "Aucun extrait suffisamment pertinent n’a été retrouvé. Une vérification par un agent SAV est nécessaire.",
            "needs_human_review": True,
        }

    system_prompt = (
        "Tu es l’assistant RAG ReturnFlow AI. Réponds en français en t’appuyant uniquement sur les extraits fournis. "
        "N’invente aucune règle ni source. Cite les passages utilisés avec leur identifiant de source et leur page. "
        "Si les extraits ne suffisent pas, indique-le clairement et demande une vérification humaine.\n\n"
        f"Extraits récupérés :\n{rules}"
    )
    from langchain_core.messages import HumanMessage, SystemMessage

    response = create_llm().invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=state["client_query"])]
    )
    return {"response": str(response.content), "needs_human_review": False}


_return_agent_graph: Any = None


def run_return_agent(initial_state: ReturnState) -> ReturnState:
    """Build the heavier LangGraph pipeline only when an RAG request arrives."""
    global _return_agent_graph
    if _return_agent_graph is None:
        from langgraph.graph import END, START, StateGraph

        workflow = StateGraph(ReturnState)
        workflow.add_node("retrieve_rules", retrieve_rules_node)
        workflow.add_node("generate_response", generate_response_node)
        workflow.add_edge(START, "retrieve_rules")
        workflow.add_edge("retrieve_rules", "generate_response")
        workflow.add_edge("generate_response", END)
        _return_agent_graph = workflow.compile()
    return _return_agent_graph.invoke(initial_state)


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _first_text(values: dict, *keys: str) -> str:
    for key in keys:
        value = _text(values.get(key))
        if value:
            return value
    return ""


def _bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = _text(value).casefold()
    if text in {"yes", "oui", "true", "1", "y", "vrai", "confirmed", "conforming"}:
        return True
    if text in {"no", "non", "false", "0", "n", "faux", "not_confirmed", "non_conforming"}:
        return False
    return None


def _date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _days_since_receipt(values: dict) -> int | None:
    supplied = values.get("days_since_receipt")
    if supplied is not None:
        try:
            days = int(float(supplied))
            return days if days >= 0 else None
        except (TypeError, ValueError):
            pass
    delivered = _date(values.get("delivery_date") or values.get("delivered_at"))
    request_date = _date(values.get("return_request_date")) or datetime.now(timezone.utc).date()
    if not delivered:
        return None
    days = (request_date - delivered).days
    return days if days >= 0 else None


def _json_object(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("The model did not return a JSON object.")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("The model response is not a JSON object.")
    return data


def _llm_json(system_prompt: str, user_prompt: str) -> dict:
    from langchain_core.messages import HumanMessage, SystemMessage

    response = create_llm().invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    )
    return _json_object(str(response.content))


def _query_text(values: dict) -> str:
    parts = [
        _first_text(values, "return_reason", "category"),
        _first_text(values, "description", "ai_summary"),
        _first_text(values, "product_name", "product_category", "product_type"),
        _first_text(values, "requested_resolution"),
    ]
    return " | ".join(part for part in parts if part)


def _known_facts(values: dict) -> dict:
    facts = {
        "category": _first_text(values, "category", "return_reason") or None,
        "days_since_receipt": _days_since_receipt(values),
        "item_worn": _bool(values.get("item_worn")),
        "item_washed": _bool(values.get("item_washed")),
        "item_modified": _bool(values.get("item_modified")),
        "original_tags_attached": _bool(values.get("original_tags_attached")),
        "item_damaged": _bool(values.get("item_damaged")),
        "defect_confirmed": _bool(values.get("defect_confirmed")),
    }
    required = (
        "days_since_receipt",
        "item_worn",
        "item_washed",
        "item_modified",
        "original_tags_attached",
        "item_damaged",
        "defect_confirmed",
    )
    facts["facts_completeness_gaps"] = [key for key in required if facts[key] is None]
    facts["factsComplete"] = not facts["facts_completeness_gaps"]
    return facts


def _source_ids(values: dict) -> list[str]:
    source_ids = values.get("sourceIds") or values.get("policy_source_ids") or []
    if isinstance(source_ids, str):
        return [part.strip() for part in source_ids.split(",") if part.strip()]
    if isinstance(source_ids, list):
        return [str(part).strip() for part in source_ids if str(part).strip()]
    return []


def _fetch_order(values: dict) -> dict:
    # There is no SHEIN order-system connection in this academic prototype.
    # An upstream adapter may supply the verified fields and orderFound flag.
    corrected = _bool(values.get("correctionProvided")) is True
    if values.get("orderFound") is not None and not corrected:
        return {
            "orderFound": bool(_bool(values.get("orderFound"))),
            "order_lookup_status": "provided_by_upstream_adapter",
            "looked_up_order_id": _text(values.get("order_id")),
            "looked_up_item_id": _text(values.get("order_item_id")),
        }
    if _bool(os.getenv("DEMO_ORDER_LOOKUP", "false")):
        order_id = _text(values.get("order_id"))
        item_id = _text(values.get("order_item_id"))
        if order_id == "DEMO-ORDER-001" and item_id == "DEMO-ITEM-001":
            today = datetime.now(timezone.utc).date()
            return {
                "orderFound": True,
                "order_lookup_status": "simulated_demo_fixture",
                "looked_up_order_id": order_id,
                "looked_up_item_id": item_id,
                "product_id": "DEMO-PRODUCT-001",
                "product_name": "T-shirt coton moyen stretch (article fictif)",
                "product_category": "t-shirt",
                "ordered_quantity": 1,
                "purchase_date": (today - timedelta(days=25)).isoformat(),
                "delivery_date": (today - timedelta(days=10)).isoformat(),
                "unit_price": 149.0,
                "currency": "MAD",
            }
    return {
        "orderFound": False,
        "order_lookup_status": "not_found_no_live_order_connector",
        "looked_up_order_id": _text(values.get("order_id")),
        "looked_up_item_id": _text(values.get("order_item_id")),
    }


def _validate_return_data(values: dict) -> dict:
    required = {
        "order_id": "le numéro de commande",
        "order_item_id": "la ligne d’article",
        "return_quantity": "la quantité à retourner",
        "return_reason": "le motif du retour",
        "description": "la description du problème",
        "requested_resolution": "la solution souhaitée",
    }
    missing = [label for key, label in required.items() if not _text(values.get(key))]
    try:
        if int(float(values.get("return_quantity", 0))) < 1:
            missing.append("une quantité supérieure à zéro")
    except (TypeError, ValueError):
        if "la quantité à retourner" not in missing:
            missing.append("une quantité valide")
    return {
        "infoComplete": not missing,
        "missing_information_text": ", ".join(missing),
    }


def _request_additional_information(values: dict) -> dict:
    missing = _text(values.get("missing_information_text"))
    message = (
        "Bonjour, pour poursuivre votre demande de retour, merci de nous transmettre : "
        f"{missing}. Cette notification est simulée dans le prototype académique."
    )
    return {
        "customer_message": message,
        "additional_information_status": "simulated",
        "customer_notification_status": "sent",
    }


def _classify_return(values: dict) -> dict:
    description = _text(values.get("description"))
    reason = _text(values.get("return_reason"))
    if not description and not reason:
        return {"aiAvailable": False, "ai_error": "missing_return_description"}
    categories = "SIZE_FIT, COLOR_MISMATCH, FABRIC_QUALITY, SHAPE_CUT, DEFECTIVE, WRONG_ITEM, NOT_AS_DESCRIBED, OTHER"
    try:
        result = _llm_json(
            "Tu classes des demandes de retour de vêtements. Réponds uniquement par un objet JSON valide. "
            "N’ajoute aucun fait absent des entrées. category doit être exactement l’une des catégories autorisées. "
            "confidence doit être un nombre de 0 à 1, sentiment et urgency de courts libellés en français. "
            "Champs requis: category, ai_summary, confidence, sentiment, urgency.",
            f"Catégories autorisées: {categories}\nMotif déclaré: {reason}\nDescription: {description}",
        )
        category = _text(result.get("category")).upper()
        if category not in categories.split(", "):
            raise ValueError("Unknown return category")
        confidence = max(0.0, min(1.0, float(result.get("confidence", 0))))
        if confidence < 0.5:
            return {"aiAvailable": False, "ai_error": "low_classification_confidence"}
        return {
            "aiAvailable": True,
            "category": category,
            "ai_summary": _text(result.get("ai_summary"))[:1200],
            "confidence": confidence,
            "sentiment": _text(result.get("sentiment"))[:80],
            "urgency": _text(result.get("urgency"))[:80],
        }
    except Exception as exc:
        LOGGER.warning("Return classification unavailable (%s).", type(exc).__name__)
        return {"aiAvailable": False, "ai_error": "classification_unavailable"}


def _retrieve_return_policy(values: dict) -> dict:
    query = _query_text(values)
    if not query:
        return {"policyChunks": "", "sourceIds": [], "similarityScores": [], "ragContextFound": False}
    try:
        passages, sources, scores = retrieve_policy(query)
    except Exception as exc:
        LOGGER.warning("Policy retrieval unavailable (%s).", type(exc).__name__)
        return {"policyChunks": "", "sourceIds": [], "similarityScores": [], "ragContextFound": False}
    return {
        "policyChunks": passages,
        "sourceIds": list(dict.fromkeys(source["source_id"] for source in sources)),
        "similarityScores": scores,
        "policySources": sources,
        "ragContextFound": bool(sources),
    }


def _extract_grounded_facts(values: dict) -> dict:
    description = _text(values.get("description"))
    policy = _text(values.get("policyChunks"))
    prompt = (
        "Extrais uniquement les faits explicitement présents dans la demande du client. "
        "Ne prends aucune décision d’éligibilité et n’infère pas l’état du vêtement. "
        "Pour les booléens, utilise true, false ou null. Réponds par un objet JSON avec "
        "item_worn, item_washed, item_modified, original_tags_attached, item_damaged, defect_confirmed, evidence."
    )
    try:
        extracted = _llm_json(
            prompt,
            f"Motif: {_text(values.get('return_reason'))}\nDescription client: {description}\n"
            f"Faits déclarés dans le formulaire: {json.dumps({key: values.get(key) for key in ('item_worn', 'item_washed', 'item_modified', 'original_tags_attached', 'item_damaged', 'defect_confirmed')}, ensure_ascii=False)}",
        )
    except Exception as exc:
        LOGGER.warning("Fact extraction unavailable (%s).", type(exc).__name__)
        extracted = {}

    facts = _known_facts(values)
    for key in ("item_worn", "item_washed", "item_modified", "original_tags_attached", "item_damaged", "defect_confirmed"):
        if facts[key] is None:
            facts[key] = _bool(extracted.get(key))
    required = (
        "days_since_receipt",
        "item_worn",
        "item_washed",
        "item_modified",
        "original_tags_attached",
        "item_damaged",
        "defect_confirmed",
    )
    facts["facts_completeness_gaps"] = [key for key in required if facts[key] is None]
    facts["factsComplete"] = not facts["facts_completeness_gaps"]
    source_ids = _source_ids(values)
    evidence = _text(extracted.get("evidence"))[:1200]
    if evidence and evidence not in description:
        evidence = ""
    valid_ids = {source.get("source_id") for source in values.get("policySources", []) if isinstance(source, dict)}
    cited_ids = [source_id for source_id in source_ids if source_id in valid_ids] if valid_ids else source_ids
    return {
        **facts,
        "policy_evidence": policy,
        "policy_source_ids": ", ".join(cited_ids),
        "fact_evidence": evidence,
    }


def _evaluate_eligibility(values: dict) -> dict:
    facts = _known_facts(values)
    days = facts["days_since_receipt"]
    policy_source_ids = _source_ids(values)
    product_category = _first_text(values, "product_category", "item_category", "product_type", "product_name").casefold()
    excluded_terms = (
        "body", "bodys", "maillot", "swimwear", "lingerie", "sous-vêtement", "sous vetement", "underwear"
    )
    reasons: list[str] = []
    if not facts["factsComplete"]:
        # Eligibility here is provisional: the following SAV task must confirm it.
        return {
            "eligibility": True,
            "eligibility_reason": "Faits incomplets; validation humaine obligatoire avant toute autorisation.",
            "recommendation": "Compléter les faits manquants et confirmer la décision dans le formulaire SAV.",
            "agent_decision": "manual_review_required",
            "returnRequired": True,
            "eligibility_sources": policy_source_ids,
        }
    if any(term in product_category for term in excluded_terms):
        reasons.append("La catégorie déclarée figure parmi les exclusions du périmètre académique.")
    if days is not None and days > RETURN_WINDOW_DAYS:
        reasons.append(f"La demande dépasse le délai de {RETURN_WINDOW_DAYS} jours retenu par le modèle académique.")
    if facts["item_worn"] is True:
        reasons.append("L’article a été porté au-delà de l’essayage.")
    if facts["item_washed"] is True:
        reasons.append("L’article a été lavé.")
    if facts["item_modified"] is True:
        reasons.append("L’article a été modifié.")
    if facts["original_tags_attached"] is False:
        reasons.append("Les étiquettes d’origine ne sont plus attachées.")

    reason_category = _first_text(values, "category", "return_reason").upper()
    defect_claim = (
        facts["defect_confirmed"] is True
        or facts["item_damaged"] is True
        or reason_category == "DEFECTIVE"
    )
    if defect_claim:
        return {
            "eligibility": True,
            "eligibility_reason": "Défaut ou dommage signalé; validation dédiée par le SAV requise, sans décision automatique.",
            "recommendation": "Transmettre au SAV pour examiner les preuves et confirmer la résolution.",
            "agent_decision": "manual_review_required",
            "returnRequired": True,
            "eligibility_sources": policy_source_ids,
        }
    if reasons:
        return {
            "eligibility": False,
            "eligibility_reason": " ".join(reasons),
            "recommendation": "Expliquer les règles applicables et les éléments établis au client.",
            "agent_decision": "ineligible_under_academic_rules",
            "returnRequired": True,
            "eligibility_sources": policy_source_ids,
        }
    return {
        "eligibility": True,
        "eligibility_reason": "Les faits fournis satisfont les contrôles déterministes du modèle académique; confirmation SAV requise.",
        "recommendation": "Faire confirmer les faits et le besoin de retour physique par le SAV.",
        "agent_decision": "candidate_for_sav_confirmation",
        "returnRequired": True,
        "eligibility_sources": policy_source_ids,
    }


def _generate_refusal(values: dict) -> dict:
    reason = _text(values.get("eligibility_reason"))
    sources = _source_ids(values)
    source_pages = values.get("policySources", [])
    citations = ", ".join(
        f"{source['source_id']}, page {source['page']}"
        for source in source_pages
        if isinstance(source, dict) and source.get("source_id") in sources
    ) or ", ".join(str(source) for source in sources)
    response = f"Bonjour, après examen de votre demande, nous ne pouvons pas confirmer son éligibilité. Motif : {reason}"
    if citations:
        response += f" Références consultées : {citations}."
    response += " Cette décision suit les règles du prototype académique et peut être vérifiée par le service client."
    return {"final_response": response, "responseSources": sources}


def _notify_client(values: dict) -> dict:
    message = _first_text(values, "customer_message", "final_response", "notification_message", "closure_note")
    if not message:
        if _bool(values.get("orderFound")) is False:
            message = "Nous n’avons pas pu retrouver la commande et la ligne d’article après la vérification des références. Le dossier est clôturé dans ce prototype."
        elif _bool(values.get("infoComplete")) is False:
            message = "Nous n’avons pas reçu les informations demandées dans le délai prévu. Le dossier est clôturé dans ce prototype."
        elif _bool(values.get("eligibility")) is False:
            message = _text(values.get("eligibility_reason")) or "Les conditions du modèle académique ne sont pas satisfaites."
        else:
            message = "Une mise à jour concernant votre demande de retour est disponible."
    return {
        "customer_notification_status": "sent",
        "last_customer_notification": message[:2000],
        "notification_delivery_mode": "simulated_no_external_message_sent",
    }


def _send_return_instructions(values: dict) -> dict:
    instructions = (
        "Instructions de démonstration : placez l’article non porté dans son emballage, joignez les références du dossier "
        "et suivez les indications de retour communiquées par le service client. Aucune étiquette réelle n’est générée."
    )
    return {
        "return_instructions": instructions,
        "return_instruction_status": "simulated",
    }


def _refund(values: dict, method: str) -> dict:
    amount = values.get("refund_amount")
    if amount is None:
        try:
            amount = round(float(values["unit_price"]) * int(values.get("return_quantity", 1)), 2)
        except (KeyError, TypeError, ValueError):
            amount = None
    return {
        "refund_status": "simulated_recorded",
        "refundMethod": method,
        "refund_amount": amount,
        "refund_currency": _text(values.get("currency")) or "MAD",
        "resolution_status": f"{method}_simulated",
        "payment_execution_mode": "simulation_no_payment_provider_connected",
    }


def _generate_final_response(values: dict) -> dict:
    query = _query_text(values)
    facts_summary = _text(values.get("eligibility_reason")) or "Votre dossier a été traité par le processus de démonstration."
    policy = _text(values.get("policyChunks"))
    source_pages = values.get("policySources", [])
    citations = ", ".join(
        f"{source['source_id']}, page {source['page']}"
        for source in source_pages
        if isinstance(source, dict) and source.get("source_id")
    )
    if policy:
        try:
            result = _llm_json(
                "Tu rédiges une réponse client en français à partir du dossier et des extraits de politique fournis. "
                "N’invente ni délai, ni promesse de paiement, ni source. Réponds en JSON avec le champ response. "
                "Cite les sources et pages pertinentes en utilisant les références exactes ci-dessous. "
                "Précise que le traitement est simulé lorsque cela concerne notification ou remboursement.",
                f"Demande: {query}\nDécision/validation: {facts_summary}\nRésolution: {_text(values.get('resolution_status'))}\n"
                f"Extraits: {policy}\nSources exactes: {citations or _text(values.get('policy_source_ids'))}",
            )
            response = _text(result.get("response"))
            if response:
                return {"final_response": response[:3000], "responseSources": values.get("sourceIds", [])}
        except Exception as exc:
            LOGGER.warning("Final response generation unavailable (%s); using a safe template.", type(exc).__name__)
    return {
        "final_response": (
            f"Bonjour, votre dossier a été traité. {facts_summary} "
            f"État de résolution : {_text(values.get('resolution_status')) or 'à confirmer par le SAV'}. "
            "Les notifications et éventuelles opérations financières de ce prototype sont simulées."
        ),
        "responseSources": values.get("sourceIds", []),
    }


TASK_HANDLERS = {
    "fetch-fashion-order-item": _fetch_order,
    "validate-return-data": _validate_return_data,
    "request-additional-information": _request_additional_information,
    "classify-fashion-return": _classify_return,
    "retrieve-return-policy-rag": _retrieve_return_policy,
    "extract-grounded-return-facts": _extract_grounded_facts,
    "evaluate-return-eligibility": _evaluate_eligibility,
    "generate-grounded-refusal-response": _generate_refusal,
    "notify-client": _notify_client,
    "send-return-instructions": _send_return_instructions,
    "refund-shein-wallet": lambda values: _refund(values, "shein_wallet"),
    "refund-original-payment": lambda values: _refund(values, "original_payment"),
    "refund-without-return": lambda values: _refund(values, "returnless"),
    "generate-grounded-final-response": _generate_final_response,
}


def process_bpmn_task(operation: str, variables: dict) -> dict:
    """Run one of the BPMN's 14 operation headers and return process variables."""
    handler = TASK_HANDLERS.get(operation)
    if handler is None:
        raise ValueError(f"Unsupported shein-agent operation: {operation!r}")
    return handler(variables)
