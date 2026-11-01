# Process Mining — protocole d'analyse

## Périmètre

- `event_log_as_is_synthetic.csv` contient les traces du processus manuel de référence.
- `event_log_to_be_synthetic.csv` contient la cohorte appariée et les variantes propres au processus cible.
- Les 200 cas `paired_common` ont le même scénario et le même résultat dans les deux journaux. Ils servent à comparer les durées sans changer le mélange de cas.
- Les cas `tobe_extension` couvrent les branches ajoutées par le TO-BE. Ils sont analysés séparément et ne participent pas à la comparaison appariée.
- Chaque activité du journal porte le nom de la tâche BPMN correspondante. Les événements de début, de fin, passerelles et timers ne sont pas des activités de travail et ne sont donc pas enregistrés comme telles.

## Analyses

1. Fréquence des variantes et activités de début/fin.
2. DFG et découverte de réseau de Petri par Inductive Miner.
3. Durée par dossier et par activité, avec comparaison des 200 cas appariés.
4. Délais de réponse et branche d'escalade SLA de 24 heures dans le TO-BE.
5. Conformance checking par alignement contre chaque BPMN correspondant.
6. Analyse séparée des variantes TO-BE de correction de commande, compléments, fallback IA/RAG, retour sans réception physique, contrôle qualité et résolution manuelle.

Le délai de 48 h concerne uniquement l'attente d'un complément client. Aucune durée de retour physique n'est imposée par le corpus public; les dossiers TO-BE attendent la confirmation de réception. Les durées du générateur sont des paramètres pédagogiques, pas des règles de SHEIN ni des mesures d'entreprise.

## Exécution

Depuis la racine du dépôt :

```powershell
python -m pip install -r logs/requirements.txt
python logs/03_synthetic_event_logs/generate_synthetic_logs.py
python logs/04_process_mining/run_analysis.py
```

Les résultats sont écrits dans `process_mining/outputs/`. Le contrôle de conformité utilise `camunda/returnflow_as_is.bpmn` pour le journal AS-IS et `camunda/returnflow_to_be.bpmn` pour le TO-BE.

## Limites d'interprétation

- Les deux journaux sont synthétiques et construits à partir des flux BPMN; ils ne sont pas des journaux opérationnels SHEIN.
- L'AS-IS ne comporte ni tâche IA, ni timers automatiques, ni retour sans réception physique. Les traces de ces branches ne sont présentes que dans le journal TO-BE.
- Le KPI de dépassement du SLA automatique s'applique au TO-BE. La comparaison globale des durées est faite uniquement sur la cohorte appariée.
- La conformance vérifie la séquence d'activités contre le modèle de référence. Elle n'évalue ni la justesse des décisions métier, ni les règles publiques elles-mêmes.
