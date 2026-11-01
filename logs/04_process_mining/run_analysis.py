"""Run reproducible PM4Py discovery, performance, and BPMN conformance analyses."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pm4py


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "logs" / "03_synthetic_event_logs"
OUTPUT_DIR = PROJECT_ROOT / "process_mining" / "outputs"
MODELS = {
    "AS_IS": PROJECT_ROOT / "camunda" / "returnflow_as_is.bpmn",
    "TO_BE": PROJECT_ROOT / "camunda" / "returnflow_to_be.bpmn",
}
LOGS = {
    "AS_IS": LOG_DIR / "event_log_as_is_synthetic.csv",
    "TO_BE": LOG_DIR / "event_log_to_be_synthetic.csv",
}


def read_log(version: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(LOGS[version], parse_dates=["start_timestamp", "end_timestamp", "timestamp"])
    required = {
        "case_id",
        "process_version",
        "activity",
        "start_timestamp",
        "end_timestamp",
        "timestamp",
        "resource",
        "result",
    }
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"{LOGS[version]} is missing required columns: {sorted(missing)}")

    formatted = pm4py.format_dataframe(
        raw,
        case_id="case_id",
        activity_key="activity",
        timestamp_key="timestamp",
    )
    return raw, formatted


def write_discovery(version: str, raw: pd.DataFrame, formatted: pd.DataFrame) -> list[dict[str, object]]:
    variants = pm4py.get_variants_as_tuples(formatted)
    variant_rows = []
    for variant, traces in variants.items():
        variant_rows.append(
            {
                "process_version": version,
                "variant_frequency": len(traces),
                "activities": " -> ".join(variant),
            }
        )

    dfg, start_activities, end_activities = pm4py.discover_dfg(formatted)
    dfg_rows = [
        {
            "process_version": version,
            "from_activity": source,
            "to_activity": target,
            "frequency": frequency,
        }
        for (source, target), frequency in dfg.items()
    ]
    net, _, _ = pm4py.discover_petri_net_inductive(formatted)
    pd.DataFrame(
        [
            {
                "process_version": version,
                "place_count": len(net.places),
                "transition_count": len(net.transitions),
            }
        ]
    ).to_csv(OUTPUT_DIR / f"inductive_miner_{version.lower()}.csv", index=False)

    raw = raw.copy()
    raw["activity_duration_minutes"] = (raw["end_timestamp"] - raw["start_timestamp"]).dt.total_seconds() / 60
    activity_durations = (
        raw.groupby("activity", as_index=False)["activity_duration_minutes"]
        .agg(event_count="count", mean_minutes="mean", median_minutes="median")
        .assign(process_version=version)
    )
    activity_durations.to_csv(OUTPUT_DIR / f"activity_durations_{version.lower()}.csv", index=False)

    case_rows = (
        raw.groupby("case_id", as_index=False)
        .agg(
            start=("start_timestamp", "min"),
            end=("end_timestamp", "max"),
            scenario=("scenario", "first"),
            comparison_group=("comparison_group", "first"),
            sla_breached=("sla_breached", "max"),
        )
    )
    case_rows["duration_hours"] = (case_rows["end"] - case_rows["start"]).dt.total_seconds() / 3600
    case_rows["process_version"] = version
    case_rows.to_csv(OUTPUT_DIR / f"case_durations_{version.lower()}.csv", index=False)

    print(
        f"{version}: {len(case_rows)} cases, {len(raw)} events, {len(variants)} variants, "
        f"{len(dfg)} directly-follows edges, starts={start_activities}, ends={end_activities}"
    )
    return variant_rows + dfg_rows


def run_conformance(version: str, formatted: pd.DataFrame) -> tuple[dict[str, object], pd.DataFrame]:
    model = pm4py.read_bpmn(str(MODELS[version]))
    net, initial_marking, final_marking = pm4py.convert_to_petri_net(model)
    diagnostics = pm4py.conformance_diagnostics_alignments(formatted, net, initial_marking, final_marking)
    fitness = pm4py.fitness_alignments(formatted, net, initial_marking, final_marking)
    case_ids = formatted["case:concept:name"].drop_duplicates().tolist()
    if len(case_ids) != len(diagnostics):
        raise RuntimeError(f"PM4Py returned {len(diagnostics)} alignments for {len(case_ids)} {version} cases")

    rows = []
    for case_id, diagnostic in zip(case_ids, diagnostics):
        cost = diagnostic.get("cost")
        rows.append(
            {
                "process_version": version,
                "case_id": case_id,
                "alignment_cost": cost,
                "fitness": diagnostic.get("fitness"),
                "conformant": bool(cost == 0),
            }
        )
    summary = {
        "process_version": version,
        "case_count": len(case_ids),
        "conformant_cases": sum(row["conformant"] for row in rows),
        "nonconformant_cases": sum(not row["conformant"] for row in rows),
        "percent_fitting_traces": fitness.get("percFitTraces"),
        "average_fitness": fitness.get("averageFitness"),
        "reference_model": str(MODELS[version].relative_to(PROJECT_ROOT)),
    }
    return summary, pd.DataFrame(rows)


def write_wait_and_sla_analysis(logs: dict[str, tuple[pd.DataFrame, pd.DataFrame]]) -> None:
    """Measure the explicit client wait and SAV validation/escalation durations."""
    to_be = logs["TO_BE"][0]
    waits = []
    request_activity = "Demander un complément au client"
    received_activity = "Enregistrer le complément reçu"
    timeout_activity = "Notifier la clôture - complément non reçu"

    requests = to_be.loc[to_be["activity"] == request_activity, ["case_id", "end_timestamp"]].rename(
        columns={"end_timestamp": "request_completed_at"}
    )
    for activity, outcome, endpoint in (
        (received_activity, "received", "start_timestamp"),
        (timeout_activity, "timed_out", "start_timestamp"),
    ):
        completions = to_be.loc[to_be["activity"] == activity, ["case_id", endpoint]].rename(
            columns={endpoint: "wait_ended_at"}
        )
        if not completions.empty:
            paired = requests.merge(completions, on="case_id", validate="one_to_one")
            paired["wait_outcome"] = outcome
            paired["wait_hours"] = (paired["wait_ended_at"] - paired["request_completed_at"]).dt.total_seconds() / 3600
            waits.append(paired)

    waits_frame = pd.concat(waits, ignore_index=True) if waits else pd.DataFrame(
        columns=["case_id", "request_completed_at", "wait_ended_at", "wait_outcome", "wait_hours"]
    )
    waits_frame.to_csv(OUTPUT_DIR / "additional_information_waits.csv", index=False)

    validation = to_be.loc[
        to_be["activity"] == "Valider la solution proposée par l'IA",
        ["case_id", "start_timestamp", "end_timestamp", "scenario"],
    ].copy()
    validation["validation_hours"] = (
        validation["end_timestamp"] - validation["start_timestamp"]
    ).dt.total_seconds() / 3600
    escalation_cases = set(
        to_be.loc[
            to_be["activity"] == "Escalader / relancer le superviseur",
            "case_id",
        ]
    )
    validation["escalated"] = validation["case_id"].isin(escalation_cases)
    validation.to_csv(OUTPUT_DIR / "sav_validation_and_escalation.csv", index=False)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    loaded = {version: read_log(version) for version in LOGS}
    write_wait_and_sla_analysis(loaded)

    variant_rows: list[dict[str, object]] = []
    dfg_rows: list[dict[str, object]] = []
    performance_rows: list[dict[str, object]] = []
    conformance_summaries = []
    conformance_case_frames = []

    for version, (raw, formatted) in loaded.items():
        discovery_rows = write_discovery(version, raw, formatted)
        variant_rows.extend(row for row in discovery_rows if "activities" in row)
        dfg_rows.extend(row for row in discovery_rows if "from_activity" in row)

        duration_hours = (raw.groupby("case_id")["end_timestamp"].max() - raw.groupby("case_id")["start_timestamp"].min()).dt.total_seconds() / 3600
        performance_rows.append(
            {
                "process_version": version,
                "case_count": int(raw["case_id"].nunique()),
                "event_count": int(len(raw)),
                "mean_case_duration_hours": float(duration_hours.mean()),
                "median_case_duration_hours": float(duration_hours.median()),
                "p95_case_duration_hours": float(duration_hours.quantile(0.95)),
                "sla_breached_cases": int((raw.groupby("case_id")["sla_breached"].max().str.lower() == "true").sum()),
            }
        )

        conformance_summary, case_diagnostics = run_conformance(version, formatted)
        conformance_summaries.append(conformance_summary)
        conformance_case_frames.append(case_diagnostics)

    pd.DataFrame(variant_rows).sort_values(["process_version", "variant_frequency"], ascending=[True, False]).to_csv(
        OUTPUT_DIR / "variant_frequencies.csv", index=False
    )
    pd.DataFrame(dfg_rows).sort_values(["process_version", "frequency"], ascending=[True, False]).to_csv(
        OUTPUT_DIR / "dfg_edges.csv", index=False
    )
    pd.DataFrame(performance_rows).to_csv(OUTPUT_DIR / "performance_summary.csv", index=False)
    pd.DataFrame(conformance_summaries).to_csv(OUTPUT_DIR / "conformance_summary.csv", index=False)
    conformance_cases = pd.concat(conformance_case_frames, ignore_index=True)
    conformance_cases.to_csv(OUTPUT_DIR / "conformance_by_case.csv", index=False)
    conformance_cases.loc[~conformance_cases["conformant"]].to_csv(OUTPUT_DIR / "nonconformant_cases.csv", index=False)

    case_summary = pd.read_csv(LOG_DIR / "case_summary_synthetic.csv")
    paired = case_summary[case_summary["comparison_group"] == "paired_common"].pivot(
        index="case_id", columns="process_version", values="duration_hours"
    )
    paired["duration_delta_to_be_minus_as_is_hours"] = paired["TO_BE"] - paired["AS_IS"]
    paired["duration_reduction_percent"] = (paired["AS_IS"] - paired["TO_BE"]) / paired["AS_IS"] * 100
    paired.reset_index().to_csv(OUTPUT_DIR / "paired_case_comparison.csv", index=False)
    paired_duration = {
        version: {
            "mean": float(paired[version].mean()),
            "median": float(paired[version].median()),
            "count": int(paired[version].count()),
        }
        for version in ("AS_IS", "TO_BE")
    }

    as_is_fitness = next(row for row in conformance_summaries if row["process_version"] == "AS_IS")
    to_be_fitness = next(row for row in conformance_summaries if row["process_version"] == "TO_BE")
    performance = {row["process_version"]: row for row in performance_rows}
    report = [
        "# Résultats Process Mining — ReturnFlow AI",
        "",
        "Les deux journaux sont synthétiques. Les 200 dossiers `paired_common` ont les mêmes scénarios et issues dans les deux versions; les cas `tobe_extension` couvrent les branches ajoutées par le TO-BE et ne sont pas mélangés à la comparaison appariée.",
        "",
        "| Version | Dossiers dans le log | Événements | Cas appariés | Durée moyenne appariée (h) | Médiane appariée (h) | Cas avec escalade SLA | Traces conformes au BPMN | Fitness moyenne |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for version, fitness in (("AS_IS", as_is_fitness), ("TO_BE", to_be_fitness)):
        stats = performance[version]
        report.append(
            f"| {version} | {stats['case_count']} | {stats['event_count']} | {paired_duration[version]['count']} | "
            f"{paired_duration[version]['mean']:.2f} | {paired_duration[version]['median']:.2f} | {stats['sla_breached_cases']} | "
            f"{fitness['conformant_cases']}/{fitness['case_count']} | {fitness['average_fitness']} |"
        )
    report += [
        "",
        "Les durées de la table comparent exclusivement les 200 cas `paired_common`; le nombre de dossiers et d'événements couvre chaque journal complet. Le compte SLA inclut toutes les traces TO-BE et reste nul dans l'AS-IS, qui ne possède pas de timer automatique de 24 heures.",
        "Les valeurs de durée sont des hypothèses du générateur, pas des mesures d'entreprise. Les attentes de complément et les validations/escalades SAV sont détaillées dans `additional_information_waits.csv` et `sav_validation_and_escalation.csv`.",
        "",
        "Fichiers détaillés : `variant_frequencies.csv`, `dfg_edges.csv`, `activity_durations_*.csv`, `case_durations_*.csv`, `paired_case_comparison.csv`, `additional_information_waits.csv`, `sav_validation_and_escalation.csv`, `conformance_summary.csv` et `conformance_by_case.csv`.",
        "",
    ]
    (OUTPUT_DIR / "analysis_summary.md").write_text("\n".join(report), encoding="utf-8")


if __name__ == "__main__":
    main()
