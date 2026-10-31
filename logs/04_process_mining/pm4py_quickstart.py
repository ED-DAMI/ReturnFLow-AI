from pathlib import Path
import pandas as pd
import pm4py

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "03_synthetic_event_logs" / "shein_returns_event_log_synthetic_200.csv"

# 1) Lire le log
log_df = pd.read_csv(CSV_PATH)
log_df["timestamp"] = pd.to_datetime(log_df["timestamp"])

# 2) Formater pour PM4Py
formatted = pm4py.format_dataframe(
    log_df,
    case_id="case_id",
    activity_key="activity",
    timestamp_key="timestamp",
)

# 3) Variantes
variants = pm4py.get_variants_as_tuples(formatted)
print("Nombre de variantes:", len(variants))
print("Top 5 variantes:")
for variant, cases in sorted(variants.items(), key=lambda kv: len(kv[1]), reverse=True)[:5]:
    print(len(cases), "cases ::", " -> ".join(variant))

# 4) DFG
# Cette fonction retourne les arcs directement-follow avec frequences.
dfg, start_activities, end_activities = pm4py.discover_dfg(formatted)
print("\nStart activities:", start_activities)
print("End activities:", end_activities)
print("Nombre d'arcs DFG:", len(dfg))

# 5) Inductive Miner / Petri net
net, initial_marking, final_marking = pm4py.discover_petri_net_inductive(formatted)
print("Petri net places:", len(net.places), "transitions:", len(net.transitions))

# 6) Quelques KPI simples
case_summary = (
    log_df.groupby("case_id")
    .agg(start=("timestamp", "min"), end=("timestamp", "max"), variant=("variant", "first"), reason=("return_reason", "first"), sla_breached=("sla_breached", "max"))
)
case_summary["duration_hours"] = (case_summary["end"] - case_summary["start"]).dt.total_seconds() / 3600
print("\nDuree moyenne (h):", round(case_summary["duration_hours"].mean(), 2))
print("Taux SLA depasse (%):", round((case_summary["sla_breached"].astype(str).str.lower() == "true").mean() * 100, 2))
print("\nMotifs:")
print(case_summary["reason"].value_counts())
