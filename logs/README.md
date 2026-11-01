# Journaux et Process Mining — ReturnFlow AI

Ce dossier regroupe le schéma de journal, les journaux synthétiques reproductibles, leur protocole d’analyse et les informations de provenance.

## Fichiers

- `03_synthetic_event_logs/generate_synthetic_logs.py` génère les deux versions avec la graine fixe `42`.
- `03_synthetic_event_logs/event_log_as_is_synthetic.csv` contient le processus manuel AS-IS.
- `03_synthetic_event_logs/event_log_to_be_synthetic.csv` contient la cohorte appariée et les extensions TO-BE.
- `03_synthetic_event_logs/case_summary_synthetic.csv` contient une ligne par cas et par version, avec groupe de comparaison et durée.
- `03_synthetic_event_logs/synthetic_dataset_summary.md` résume les volumes et scénarios générés.
- `04_process_mining/event_log_schema.csv` décrit les colonnes des journaux.
- `04_process_mining/process_mining_plan.md` définit la méthode et les limites.
- `04_process_mining/run_analysis.py` calcule variantes, DFG, Inductive Miner, durées, KPI et alignements BPMN.
- `05_provenance/DATA_PROVENANCE.md` décrit les sources de contexte et la provenance synthétique.

## Reproduction

Depuis la racine du dépôt :

~~~powershell
uv run --no-project --with pandas --with pm4py python logs/03_synthetic_event_logs/generate_synthetic_logs.py
uv run --no-project --with pandas --with pm4py python logs/04_process_mining/run_analysis.py
~~~

Les résultats sont enregistrés dans `process_mining/outputs/`. Le fichier `additional_information_waits.csv` détaille les attentes de compléments reçus ou expirés; `sav_validation_and_escalation.csv` détaille la durée de validation et les cas escaladés. `paired_case_comparison.csv` ne contient que les 200 cas communs aux deux modèles.

## Cohortes et interprétation

Les 200 cas `paired_common` partagent le même scénario et la même issue métier dans les deux versions. Ils forment la seule cohorte utilisée pour comparer les durées. Les 180 cas `tobe_extension` exercent neuf scénarios propres au TO-BE et sont présentés séparément.

Les activités de journal reprennent les noms de tâches BPMN. `timestamp` est l’heure de fin de l’activité; les horodatages de début et fin conservent sa durée. Les attentes entre activités se mesurent par les intervalles. Les événements début/fin, passerelles et timers ne sont pas ajoutés comme activités de travail.

Tous les cas, identifiants, horodatages, ressources, décisions et durées sont synthétiques. Ils ne constituent ni des données client ni des journaux opérationnels SHEIN; les résultats caractérisent uniquement les hypothèses du générateur.
