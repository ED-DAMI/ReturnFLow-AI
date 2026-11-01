"""Generate paired synthetic AS-IS and TO-BE event logs for ReturnFlow AI."""

from __future__ import annotations

import csv
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SEED = 42
N_PAIRED_CASES = 200
N_TOBE_EXTENSION_CASES_PER_SCENARIO = 20
BASE_TIME = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
OUT_DIR = Path(__file__).resolve().parent

AS_IS_LOG = OUT_DIR / "event_log_as_is_synthetic.csv"
TO_BE_LOG = OUT_DIR / "event_log_to_be_synthetic.csv"
CASE_SUMMARY = OUT_DIR / "case_summary_synthetic.csv"
DATASET_SUMMARY = OUT_DIR / "synthetic_dataset_summary.md"

EVENT_FIELDS = [
    "case_id",
    "process_version",
    "activity",
    "start_timestamp",
    "end_timestamp",
    "timestamp",
    "resource",
    "result",
    "scenario",
    "comparison_group",
    "return_id",
    "order_id",
    "product_id",
    "return_reason",
    "eligibility",
    "return_required",
    "resolution",
    "sla_breached",
    "is_synthetic",
]
SUMMARY_FIELDS = [
    "case_id",
    "process_version",
    "scenario",
    "comparison_group",
    "return_reason",
    "eligibility",
    "return_required",
    "resolution",
    "sla_breached",
    "start_timestamp",
    "end_timestamp",
    "duration_hours",
    "is_synthetic",
]

REASONS = [
    "SIZE_FIT",
    "COLOR_MISMATCH",
    "FABRIC_QUALITY",
    "SHAPE_CUT",
    "DEFECTIVE",
    "WRONG_ITEM",
    "NOT_AS_DESCRIBED",
]
COMMON_SCENARIOS = [
    ("standard_accepted", 0.55),
    ("standard_refused", 0.25),
    ("missing_information", 0.20),
]
TOBE_ONLY_SCENARIOS = [
    "order_correction",
    "order_not_found",
    "information_timeout",
    "ai_fallback_manual",
    "rag_fallback_manual",
    "sla_escalation",
    "refund_without_return",
    "qc_exception",
    "manual_resolution",
]


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def minutes(rng: random.Random, lower: int, upper: int) -> timedelta:
    return timedelta(minutes=rng.randint(lower, upper))


def hours(rng: random.Random, lower: float, upper: float) -> timedelta:
    return timedelta(seconds=rng.randint(int(lower * 3600), int(upper * 3600)))


def days(rng: random.Random, lower: float, upper: float) -> timedelta:
    return timedelta(seconds=rng.randint(int(lower * 86400), int(upper * 86400)))


def add_activity(
    events: list[dict[str, Any]],
    case: dict[str, Any],
    version: str,
    activity: str,
    resource: str,
    now: datetime,
    duration: timedelta,
    result: str,
    *,
    sla_breached: bool = False,
) -> datetime:
    """Append one completed BPMN activity and return its completion time."""
    end = now + duration
    events.append(
        {
            "case_id": case["case_id"],
            "process_version": version,
            "activity": activity,
            "start_timestamp": stamp(now),
            "end_timestamp": stamp(end),
            # PM4Py uses the completion timestamp for event ordering.
            "timestamp": stamp(end),
            "resource": resource,
            "result": result,
            "scenario": case["scenario"],
            "comparison_group": case["comparison_group"],
            "return_id": case["return_id"],
            "order_id": case["order_id"],
            "product_id": case["product_id"],
            "return_reason": case["return_reason"],
            "eligibility": case["eligibility"],
            "return_required": str(case["return_required"]).lower(),
            "resolution": case["resolution"],
            "sla_breached": str(sla_breached).lower(),
            "is_synthetic": "true",
        }
    )
    return end


def new_case(
    rng: random.Random,
    case_id: str,
    scenario: str,
    comparison_group: str,
    *,
    eligibility: str | None = None,
    return_required: bool = True,
    resolution: str | None = None,
) -> dict[str, Any]:
    if eligibility is None:
        eligibility = "refused" if scenario == "standard_refused" else "eligible"
    if resolution is None:
        resolution = rng.choice(["shein_wallet", "original_payment"]) if eligibility == "eligible" else "none"
    return {
        "case_id": case_id,
        "return_id": f"RET-{case_id}",
        "order_id": f"ORD-{rng.randint(100000, 999999)}",
        "product_id": f"PRD-{rng.randint(10000, 99999)}",
        "return_reason": rng.choice(REASONS),
        "scenario": scenario,
        "comparison_group": comparison_group,
        "eligibility": eligibility,
        "return_required": return_required,
        "resolution": resolution,
    }


def case_start(rng: random.Random) -> datetime:
    return BASE_TIME + timedelta(
        days=rng.randint(0, 59),
        hours=rng.randint(0, 10),
        minutes=rng.randint(0, 59),
    )


def record_case_summary(
    summaries: list[dict[str, Any]], case: dict[str, Any], version: str, start: datetime, end: datetime, sla: bool
) -> None:
    summaries.append(
        {
            "case_id": case["case_id"],
            "process_version": version,
            "scenario": case["scenario"],
            "comparison_group": case["comparison_group"],
            "return_reason": case["return_reason"],
            "eligibility": case["eligibility"],
            "return_required": str(case["return_required"]).lower(),
            "resolution": case["resolution"],
            "sla_breached": str(sla).lower(),
            "start_timestamp": stamp(start),
            "end_timestamp": stamp(end),
            "duration_hours": f"{(end - start).total_seconds() / 3600:.2f}",
            "is_synthetic": "true",
        }
    )


def generate_as_is_case(
    rng: random.Random, case: dict[str, Any], events: list[dict[str, Any]], summaries: list[dict[str, Any]]
) -> None:
    version = "AS_IS"
    start = case_start(rng)
    now = start
    now = add_activity(events, case, version, "Lire la demande", "Agent-SAV", now, minutes(rng, 5, 20), "reviewed")
    now += minutes(rng, 2, 12)
    now = add_activity(events, case, version, "Rechercher la commande", "Agent-SAV", now, minutes(rng, 8, 35), "found")
    now += minutes(rng, 1, 15)
    now = add_activity(
        events, case, version, "Vérifier les informations et les règles", "Agent-SAV", now, minutes(rng, 15, 55), "checked"
    )

    if case["scenario"] == "missing_information":
        now += hours(rng, 0.2, 4)
        now = add_activity(events, case, version, "Échanger avec le client", "Agent-SAV", now, hours(rng, 1, 12), "information_received")
        now += minutes(rng, 3, 20)
        now = add_activity(
            events, case, version, "Vérifier les informations et les règles", "Agent-SAV", now, minutes(rng, 12, 45), "complete"
        )

    now += minutes(rng, 4, 25)
    outcome = "authorized" if case["eligibility"] == "eligible" else "refused"
    now = add_activity(events, case, version, "Autoriser ou refuser le retour", "Agent-SAV", now, hours(rng, 0.2, 8), outcome)
    if outcome == "refused":
        now += minutes(rng, 1, 10)
        now = add_activity(events, case, version, "Enregistrer le refus", "Agent-SAV", now, minutes(rng, 3, 15), "refused")
    else:
        now += minutes(rng, 2, 15)
        now = add_activity(events, case, version, "Envoyer les instructions de retour", "Agent-SAV", now, minutes(rng, 5, 25), "sent")
        now += days(rng, 0.5, 5)
        now = add_activity(events, case, version, "Réceptionner le produit", "Entrepôt", now, minutes(rng, 5, 25), "received")
        now += minutes(rng, 2, 30)
        now = add_activity(events, case, version, "Inspecter le produit", "Entrepôt", now, minutes(rng, 15, 60), "quality_passed")
        now += minutes(rng, 5, 30)
        now = add_activity(events, case, version, "Décider de la résolution finale", "Agent-SAV", now, hours(rng, 0.2, 5), case["resolution"])
        now += minutes(rng, 3, 20)
        now = add_activity(events, case, version, "Exécuter la résolution", "Service-Remboursement", now, hours(rng, 0.2, 24), "completed")

    now += minutes(rng, 1, 15)
    now = add_activity(events, case, version, "Notifier le client", "Agent-SAV", now, minutes(rng, 2, 12), "sent")
    now += minutes(rng, 1, 8)
    now = add_activity(events, case, version, "Clôturer le dossier", "Agent-SAV", now, minutes(rng, 2, 10), "closed")
    record_case_summary(summaries, case, version, start, now, False)


def add_tobe_evaluation(
    rng: random.Random, case: dict[str, Any], events: list[dict[str, Any]], now: datetime, mode: str
) -> datetime:
    now = add_activity(
        events,
        case,
        "TO_BE",
        "Analyser le motif du retour avec le LLM",
        "shein-agent",
        now,
        minutes(rng, 1, 3),
        "unavailable" if mode == "ai_fallback_manual" else "available",
    )
    if mode == "ai_fallback_manual":
        now += minutes(rng, 1, 5)
        now = add_activity(events, case, "TO_BE", "Analyse manuelle des faits / règles", "Agent-SAV", now, minutes(rng, 15, 60), "reviewed")
    else:
        now += minutes(rng, 1, 4)
        rag_result = "insufficient" if mode == "rag_fallback_manual" else "sufficient"
        now = add_activity(
            events,
            case,
            "TO_BE",
            "Rechercher les politiques via le RAG de shein-agent",
            "shein-agent",
            now,
            minutes(rng, 1, 3),
            rag_result,
        )
        if rag_result == "insufficient":
            now += minutes(rng, 1, 5)
            now = add_activity(events, case, "TO_BE", "Analyse manuelle des faits / règles", "Agent-SAV", now, minutes(rng, 15, 60), "reviewed")
        else:
            now += minutes(rng, 1, 4)
            now = add_activity(events, case, "TO_BE", "Extraire les faits + preuves citées", "shein-agent", now, minutes(rng, 1, 3), "grounded")

    now += minutes(rng, 1, 4)
    now = add_activity(
        events,
        case,
        "TO_BE",
        "Évaluer l'éligibilité (règles déterministes / DMN)",
        "shein-agent",
        now,
        minutes(rng, 1, 3),
        case["eligibility"],
    )
    return now


def generate_to_be_case(
    rng: random.Random, case: dict[str, Any], events: list[dict[str, Any]], summaries: list[dict[str, Any]]
) -> None:
    version = "TO_BE"
    start = case_start(rng)
    now = start
    now = add_activity(events, case, version, "Saisir la demande de retour", "Client", now, minutes(rng, 2, 8), "submitted")
    now += minutes(rng, 1, 3)
    fetch_result = "not_found" if case["scenario"] in {"order_correction", "order_not_found"} else "found"
    now = add_activity(events, case, version, "Récupérer la commande, l'article et la fiche produit", "shein-agent", now, minutes(rng, 1, 3), fetch_result)

    if case["scenario"] in {"order_correction", "order_not_found"}:
        now += minutes(rng, 2, 20)
        correction = "provided" if case["scenario"] == "order_correction" else "not_provided"
        now = add_activity(events, case, version, "Demander correction des références", "Agent-SAV", now, hours(rng, 0.2, 2), correction)
        if correction == "not_provided":
            now += minutes(rng, 1, 4)
            now = add_activity(events, case, version, "Notifier la clôture - références introuvables", "shein-agent", now, minutes(rng, 1, 3), "sent")
            record_case_summary(summaries, case, version, start, now, False)
            return
        now += minutes(rng, 1, 3)
        now = add_activity(events, case, version, "Récupérer la commande, l'article et la fiche produit", "shein-agent", now, minutes(rng, 1, 3), "found_after_correction")

    now += minutes(rng, 1, 4)
    now = add_activity(events, case, version, "Valider les informations minimales", "shein-agent", now, minutes(rng, 1, 2), "incomplete" if case["scenario"] in {"missing_information", "information_timeout"} else "complete")
    if case["scenario"] in {"missing_information", "information_timeout"}:
        now += minutes(rng, 1, 4)
        now = add_activity(events, case, version, "Demander un complément au client", "shein-agent", now, minutes(rng, 1, 3), "request_sent")
        if case["scenario"] == "information_timeout":
            now += timedelta(hours=48)
            now = add_activity(events, case, version, "Notifier la clôture - complément non reçu", "shein-agent", now, minutes(rng, 1, 3), "sent")
            record_case_summary(summaries, case, version, start, now, False)
            return
        now += hours(rng, 2, 18)
        now = add_activity(events, case, version, "Enregistrer le complément reçu", "Client", now, minutes(rng, 2, 8), "received")
        now += minutes(rng, 1, 4)
        now = add_activity(events, case, version, "Valider les informations minimales", "shein-agent", now, minutes(rng, 1, 2), "complete")

    mode = case["scenario"]
    now = add_tobe_evaluation(rng, case, events, now + minutes(rng, 1, 4), mode)
    if case["eligibility"] == "refused":
        now += minutes(rng, 1, 4)
        now = add_activity(events, case, version, "Générer un refus expliqué et sourcé", "shein-agent", now, minutes(rng, 1, 3), "refusal_generated")
        now += minutes(rng, 1, 4)
        now = add_activity(events, case, version, "Notifier le client du refus", "shein-agent", now, minutes(rng, 1, 3), "sent")
        record_case_summary(summaries, case, version, start, now, False)
        return

    case["return_required"] = case["scenario"] != "refund_without_return"
    if case["scenario"] == "refund_without_return":
        case["resolution"] = "returnless"

    # The service task stays active while the non-interrupting 24-hour timer
    # creates a parallel supervisor follow-up branch.
    validation_duration = hours(rng, 26, 32) if mode == "sla_escalation" else hours(rng, 0.2, 5)
    validation_start = now + minutes(rng, 2, 10)
    validation_end = validation_start + validation_duration
    if mode == "sla_escalation":
        escalation_start = validation_start + timedelta(hours=24)
        escalation_end = add_activity(
            events,
            case,
            version,
            "Escalader / relancer le superviseur",
            "Responsable-SAV",
            escalation_start,
            minutes(rng, 5, 30),
            "escalated",
            sla_breached=True,
        )
        del escalation_end  # The escalation is a concurrent timer branch.
        now = add_activity(
            events,
            case,
            version,
            "Valider la solution proposée par l'IA",
            "Agent-SAV",
            validation_start,
            validation_duration,
            "validated",
            sla_breached=True,
        )
    else:
        now = add_activity(
            events,
            case,
            version,
            "Valider la solution proposée par l'IA",
            "Agent-SAV",
            validation_start,
            validation_duration,
            "validated",
        )

    if case["return_required"]:
        now += minutes(rng, 1, 5)
        now = add_activity(events, case, version, "Envoyer les instructions de retour", "shein-agent", now, minutes(rng, 1, 3), "sent")
        now += days(rng, 0.5, 4)
        now = add_activity(events, case, version, "Confirmer la réception du vêtement", "Entrepôt", now, minutes(rng, 1, 5), "received")
        now += minutes(rng, 1, 5)
        qc_result = "non_conforming" if case["scenario"] == "qc_exception" else "conforming"
        now = add_activity(events, case, version, "Inspecter l'état, les étiquettes et la conformité", "Entrepôt", now, minutes(rng, 5, 25), qc_result)
        if qc_result == "non_conforming":
            now += minutes(rng, 1, 5)
            now = add_activity(events, case, version, "Réévaluer le dossier après inspection", "Agent-SAV", now, hours(rng, 0.2, 3), "reevaluated")

    now += minutes(rng, 1, 5)
    now = add_activity(events, case, version, "Confirmer le mode de remboursement / traitement", "Agent-SAV", now, hours(rng, 0.1, 2), case["resolution"])
    if case["resolution"] == "shein_wallet":
        resolution_activity = "Rembourser sur portefeuille SHEIN"
        operation_result = "wallet_refund_recorded"
    elif case["resolution"] == "original_payment":
        resolution_activity = "Enregistrer le remboursement sur le moyen initial"
        operation_result = "original_payment_refund_recorded"
    elif case["resolution"] == "returnless":
        resolution_activity = "Enregistrer le remboursement sans retour physique"
        operation_result = "returnless_refund_recorded"
    else:
        resolution_activity = "Traiter une exception SAV manuellement"
        operation_result = "manual_resolution_recorded"

    now += minutes(rng, 1, 4)
    now = add_activity(events, case, version, resolution_activity, "shein-agent" if case["resolution"] != "manual" else "Agent-SAV", now, minutes(rng, 1, 5), operation_result)
    now += minutes(rng, 1, 5)
    now = add_activity(events, case, version, "Générer la réponse finale personnalisée (LLM)", "shein-agent", now, minutes(rng, 1, 3), "generated")
    now += minutes(rng, 1, 5)
    now = add_activity(events, case, version, "Notifier le client", "shein-agent", now, minutes(rng, 1, 3), "sent")
    now += minutes(rng, 1, 5)
    now = add_activity(events, case, version, "Clôturer le dossier", "Agent-SAV", now, minutes(rng, 1, 4), "closed")
    record_case_summary(summaries, case, version, start, now, mode == "sla_escalation")


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rng = random.Random(SEED)
    as_is_events: list[dict[str, Any]] = []
    to_be_events: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    # Paired common cases use identical business scenarios and outcomes so
    # the AS-IS / TO-BE duration comparison is not distorted by case mix.
    for index in range(1, N_PAIRED_CASES + 1):
        scenario = rng.choices([name for name, _ in COMMON_SCENARIOS], weights=[weight for _, weight in COMMON_SCENARIOS], k=1)[0]
        if scenario == "standard_refused":
            eligible, resolution = "refused", "none"
        else:
            eligible = "eligible" if rng.random() < 0.78 else "refused"
            resolution = rng.choice(["shein_wallet", "original_payment"]) if eligible == "eligible" else "none"
        case = new_case(
            rng,
            f"RMA-COMMON-{index:04d}",
            scenario,
            comparison_group="paired_common",
            eligibility=eligible,
            resolution=resolution,
        )
        generate_as_is_case(rng, case.copy(), as_is_events, summaries)
        generate_to_be_case(rng, case.copy(), to_be_events, summaries)

    # TO-BE-only cases exercise automation and exception paths absent from
    # the manual AS-IS reference process.
    next_index = 1
    for scenario in TOBE_ONLY_SCENARIOS:
        for _ in range(N_TOBE_EXTENSION_CASES_PER_SCENARIO):
            eligibility = "pending" if scenario in {"order_not_found", "information_timeout"} else "eligible"
            if scenario == "manual_resolution":
                resolution = "manual"
            elif scenario == "refund_without_return":
                resolution = "returnless"
            elif scenario in {"order_not_found", "information_timeout"}:
                resolution = "none"
            else:
                resolution = rng.choice(["shein_wallet", "original_payment"])
            case = new_case(
                rng,
                f"RMA-TOBE-{next_index:04d}",
                scenario,
                comparison_group="tobe_extension",
                eligibility=eligibility,
                return_required=scenario != "refund_without_return",
                resolution=resolution,
            )
            generate_to_be_case(rng, case, to_be_events, summaries)
            next_index += 1

    as_is_events.sort(key=lambda row: (row["case_id"], row["timestamp"], row["activity"]))
    to_be_events.sort(key=lambda row: (row["case_id"], row["timestamp"], row["activity"]))
    summaries.sort(key=lambda row: (row["case_id"], row["process_version"]))
    write_csv(AS_IS_LOG, EVENT_FIELDS, as_is_events)
    write_csv(TO_BE_LOG, EVENT_FIELDS, to_be_events)
    write_csv(CASE_SUMMARY, SUMMARY_FIELDS, summaries)

    scenario_counts = Counter(row["scenario"] for row in summaries if row["process_version"] == "TO_BE")
    mean_duration = {}
    for version in ("AS_IS", "TO_BE"):
        rows = [row for row in summaries if row["process_version"] == version and row["comparison_group"] == "paired_common"]
        mean_duration[version] = sum(float(row["duration_hours"]) for row in rows) / len(rows)
    DATASET_SUMMARY.write_text(
        "\n".join(
            [
                "# Synthèse des journaux synthétiques",
                "",
                f"- Graine fixe : `{SEED}`.",
                f"- Cohorte appariée : {N_PAIRED_CASES} cas communs AS-IS / TO-BE.",
                f"- Cas TO-BE supplémentaires : {N_TOBE_EXTENSION_CASES_PER_SCENARIO * len(TOBE_ONLY_SCENARIOS)} pour exercer les branches propres au modèle cible.",
                f"- Événements AS-IS : {len(as_is_events)}.",
                f"- Événements TO-BE : {len(to_be_events)}.",
                f"- Durée moyenne de la cohorte appariée AS-IS : {mean_duration['AS_IS']:.2f} h.",
                f"- Durée moyenne de la cohorte appariée TO-BE : {mean_duration['TO_BE']:.2f} h.",
                "",
                "## Scénarios TO-BE",
                "",
                *[f"- `{name}` : {count}" for name, count in sorted(scenario_counts.items())],
                "",
                "Les horodatages, ressources, décisions et cas sont simulés. Aucun journal interne, client ou transaction SHEIN n'est utilisé. Les durées sont des hypothèses pédagogiques; les résultats ne mesurent pas la performance réelle de SHEIN.",
                "",
                "Les lignes de log sont des activités terminées. `timestamp` reprend `end_timestamp` pour l'ordre PM4Py; `start_timestamp` et `end_timestamp` permettent d'analyser la durée propre de chaque activité.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Generated {len(as_is_events)} AS-IS events and {len(to_be_events)} TO-BE events")
    print(AS_IS_LOG)
    print(TO_BE_LOG)
    print(CASE_SUMMARY)


if __name__ == "__main__":
    main()
