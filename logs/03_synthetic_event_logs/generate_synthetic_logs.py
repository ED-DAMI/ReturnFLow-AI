import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
N_CASES = 200
random.seed(SEED)

OUT_DIR = Path(__file__).resolve().parent
EVENT_LOG = OUT_DIR / "shein_returns_event_log_synthetic_200.csv"
CASE_SUMMARY = OUT_DIR / "case_summary_synthetic_200.csv"

categories = ["Dress", "Jeans", "Top", "Shirt", "Skirt", "Trousers", "Jacket"]
sizes = ["XS", "S", "M", "L", "XL", "XXL"]
colors = ["Black", "White", "Blue", "Green", "Beige", "Red", "Pink", "Brown"]
fabrics = ["Polyester", "Cotton", "Denim", "Viscose", "Polyamide", "Linen blend", "Knit"]
reasons = [
    ("SIZE_FIT", 0.34),
    ("COLOR_MISMATCH", 0.15),
    ("FABRIC_QUALITY", 0.14),
    ("SHAPE_CUT", 0.10),
    ("DEFECTIVE", 0.12),
    ("WRONG_ITEM", 0.07),
    ("NOT_AS_DESCRIBED", 0.08),
]
variants = [
    ("standard_accepted", 0.44),
    ("standard_refused", 0.15),
    ("missing_information", 0.10),
    ("ai_fallback_manual", 0.08),
    ("sla_escalation", 0.08),
    ("refund_without_return", 0.07),
    ("qc_exception", 0.08),
]

resources = {
    "system": "ReturnFlow-System",
    "ai": "OpenRouter-LLM",
    "rag": "PostgreSQL-pgvector",
    "agent": "Agent-SAV",
    "supervisor": "Superviseur-SAV",
    "customer": "Client",
    "warehouse": "Entrepot-SHEIN",
    "finance": "Service-Remboursement",
}


def weighted_choice(items):
    r = random.random()
    acc = 0.0
    for value, weight in items:
        acc += weight
        if r <= acc:
            return value
    return items[-1][0]


def add_event(rows, case, activity, ts, resource, aftersales_status=None, return_status=None,
              eligibility="pending", resolution="none", sla_breached=False):
    rows.append({
        "case_id": case["case_id"],
        "return_order_no": case["return_order_no"],
        "order_id": case["order_id"],
        "product_id": case["product_id"],
        "sku": case["sku"],
        "product_category": case["product_category"],
        "size": case["size"],
        "color": case["color"],
        "fabric": case["fabric"],
        "return_reason": case["return_reason"],
        "activity": activity,
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "resource": resource,
        "aftersales_sub_status": "" if aftersales_status is None else aftersales_status,
        "return_order_status": "" if return_status is None else return_status,
        "eligibility": eligibility,
        "resolution": resolution,
        "ai_category": case["ai_category"],
        "ai_confidence": f"{case['ai_confidence']:.2f}",
        "sla_breached": str(bool(sla_breached)).lower(),
        "variant": case["variant"],
        "is_synthetic": "true",
        "source_basis": "SHEIN public API schema + academic simulation"
    })


def advance(ts, minutes=(2, 15)):
    return ts + timedelta(minutes=random.randint(*minutes))


def hours(ts, lo, hi):
    return ts + timedelta(hours=random.uniform(lo, hi))


def days(ts, lo, hi):
    return ts + timedelta(days=random.uniform(lo, hi))


rows = []
summaries = []
base = datetime(2026, 9, 1, 8, 0, 0)

for i in range(1, N_CASES + 1):
    variant = weighted_choice(variants)
    reason = weighted_choice(reasons)
    start = base + timedelta(days=random.randint(0, 59), hours=random.randint(0, 10), minutes=random.randint(0, 59))
    case = {
        "case_id": f"RMA-{i:04d}",
        "return_order_no": f"RF26{i:08d}",
        "order_id": f"ORD26{random.randint(100000, 999999)}",
        "product_id": f"P{random.randint(10000, 99999)}",
        "sku": f"SKU-{random.randint(100000, 999999)}",
        "product_category": random.choice(categories),
        "size": random.choice(sizes),
        "color": random.choice(colors),
        "fabric": random.choice(fabrics),
        "return_reason": reason,
        "ai_category": reason,
        "ai_confidence": random.uniform(0.72, 0.98),
        "variant": variant,
    }

    t = start
    add_event(rows, case, "Return request received", t, resources["customer"], 2, 2)
    t = advance(t, (1, 5))
    add_event(rows, case, "Order retrieved", t, resources["system"], 1, 2)

    if variant == "missing_information":
        t = advance(t, (1, 4))
        add_event(rows, case, "Missing information detected", t, resources["system"], 16, 2)
        t = hours(t, 2, 20)
        add_event(rows, case, "Customer feedback requested", t, resources["agent"], 16, 2)
        t = hours(t, 1, 18)
        add_event(rows, case, "Customer information received", t, resources["customer"], 1, 2)

    t = advance(t, (1, 6))
    if variant == "ai_fallback_manual":
        add_event(rows, case, "AI analysis failed", t, resources["ai"], 1, 2)
        t = advance(t, (5, 25))
        add_event(rows, case, "Manual return reason analysis", t, resources["agent"], 1, 2)
        case["ai_confidence"] = random.uniform(0.45, 0.69)
    else:
        add_event(rows, case, "Return reason analyzed by AI", t, resources["ai"], 1, 2)

    t = advance(t, (1, 3))
    add_event(rows, case, "RAG policy retrieved", t, resources["rag"], 1, 2)
    t = advance(t, (1, 5))
    add_event(rows, case, "Eligibility checked", t, resources["system"], 2, 2)

    if variant == "standard_refused":
        t = advance(t, (1, 10))
        add_event(rows, case, "Return rejected", t, resources["agent"], 11, 13, "refused", "none")
        t = advance(t, (1, 5))
        add_event(rows, case, "Refusal response generated", t, resources["ai"], 11, 13, "refused", "none")
        t = advance(t, (1, 5))
        add_event(rows, case, "Customer notified", t, resources["system"], 11, 13, "refused", "none")
        t = advance(t, (1, 3))
        add_event(rows, case, "Case closed", t, resources["system"], 11, 1, "refused", "none")
        resolution = "none"
        eligible = "refused"

    elif variant == "refund_without_return":
        t = advance(t, (1, 10))
        add_event(rows, case, "Refund without return approved", t, resources["agent"], 9, 9, "eligible", "refund")
        t = hours(t, 1, 8)
        add_event(rows, case, "Refund completed", t, resources["finance"], 12, 9, "eligible", "refund")
        t = advance(t, (1, 5))
        add_event(rows, case, "Customer notified", t, resources["system"], 12, 9, "eligible", "refund")
        t = advance(t, (1, 3))
        add_event(rows, case, "Case closed", t, resources["system"], 12, 9, "eligible", "refund")
        resolution = "refund"
        eligible = "eligible"

    else:
        t = advance(t, (2, 20))
        add_event(rows, case, "Agent validation started", t, resources["agent"], 1, 2, "eligible")

        sla = variant == "sla_escalation"
        if sla:
            t = hours(t, 25, 34)
            add_event(rows, case, "SLA 24h breached", t, resources["system"], 1, 2, "eligible", sla_breached=True)
            t = advance(t, (5, 60))
            add_event(rows, case, "Supervisor escalation", t, resources["supervisor"], 1, 2, "eligible", sla_breached=True)
        else:
            t = hours(t, 0.2, 8)

        resolution = random.choices(["refund", "exchange", "repair"], weights=[0.58, 0.34, 0.08], k=1)[0]
        add_event(rows, case, "Return solution validated", t, resources["agent"], 4, 2, "eligible", resolution, sla)
        t = advance(t, (1, 10))
        add_event(rows, case, "Return instructions sent", t, resources["system"], 4, 7, "eligible", resolution, sla)
        t = days(t, 0.2, 2.5)
        add_event(rows, case, "Return package handed over", t, resources["customer"], 5, 7, "eligible", resolution, sla)
        t = days(t, 1.0, 4.5)
        add_event(rows, case, "Return package delivered", t, resources["warehouse"], 6, 6, "eligible", resolution, sla)
        t = hours(t, 0.5, 12)
        add_event(rows, case, "Product inspected", t, resources["warehouse"], 6, 5, "eligible", resolution, sla)

        if variant == "qc_exception":
            t = advance(t, (5, 60))
            add_event(rows, case, "QC exception detected", t, resources["warehouse"], 7, 5, "pending", "manual", sla)
            t = hours(t, 2, 18)
            add_event(rows, case, "Platform review completed", t, resources["supervisor"], 2, 5, "eligible", resolution, sla)

        t = advance(t, (3, 30))
        if resolution == "refund":
            add_event(rows, case, "Refund approved", t, resources["agent"], 9, 5, "eligible", resolution, sla)
            t = hours(t, 1, 24)
            add_event(rows, case, "Refund completed", t, resources["finance"], 12, 9, "eligible", resolution, sla)
        elif resolution == "exchange":
            add_event(rows, case, "Replacement approved", t, resources["agent"], 14, 5, "eligible", resolution, sla)
            t = hours(t, 2, 18)
            add_event(rows, case, "Replacement dispatched", t, resources["system"], 12, 9, "eligible", resolution, sla)
        else:
            add_event(rows, case, "Repair handling initiated", t, resources["agent"], 1, 5, "eligible", resolution, sla)
            t = days(t, 1, 3)
            add_event(rows, case, "Repair completed", t, resources["system"], 12, 9, "eligible", resolution, sla)

        t = advance(t, (1, 10))
        add_event(rows, case, "Final response generated", t, resources["ai"], 12, 9, "eligible", resolution, sla)
        t = advance(t, (1, 5))
        add_event(rows, case, "Customer notified", t, resources["system"], 12, 9, "eligible", resolution, sla)
        t = advance(t, (1, 3))
        add_event(rows, case, "Case closed", t, resources["system"], 12, 9, "eligible", resolution, sla)
        eligible = "eligible"

    duration_hours = (t - start).total_seconds() / 3600.0
    summaries.append({
        "case_id": case["case_id"],
        "return_order_no": case["return_order_no"],
        "variant": variant,
        "return_reason": reason,
        "product_category": case["product_category"],
        "resolution": resolution,
        "eligibility": eligible,
        "ai_confidence": f"{case['ai_confidence']:.2f}",
        "sla_breached": str(variant == "sla_escalation").lower(),
        "start_time": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": t.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_hours": f"{duration_hours:.2f}",
        "is_synthetic": "true"
    })

fieldnames = [
    "case_id", "return_order_no", "order_id", "product_id", "sku", "product_category",
    "size", "color", "fabric", "return_reason", "activity", "timestamp", "resource",
    "aftersales_sub_status", "return_order_status", "eligibility", "resolution",
    "ai_category", "ai_confidence", "sla_breached", "variant", "is_synthetic", "source_basis"
]
with EVENT_LOG.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(sorted(rows, key=lambda x: (x["case_id"], x["timestamp"])))

summary_fields = list(summaries[0].keys())
with CASE_SUMMARY.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=summary_fields)
    writer.writeheader()
    writer.writerows(summaries)

print(f"Generated {len(rows)} events across {N_CASES} cases")
print(EVENT_LOG)
print(CASE_SUMMARY)
