# Provenance et limites des données

## Données réelles utilisées

- Les champs de référence et certains états d'API sont documentés dans les sources SHEIN Developer répertoriées sous `00_sources/` et `01_api_reference/`.
- Les références de produits et d'avis externes sous `02_public_data/` sont des ressources de contexte facultatives; elles ne sont pas intégrées aux journaux de processus.

## Données synthétiques

- `event_log_as_is_synthetic.csv`
- `event_log_to_be_synthetic.csv`
- `case_summary_synthetic.csv`

Ces fichiers sont générés par `generate_synthetic_logs.py` avec une graine fixe. Les cas, horodatages, motifs, identifiants, ressources et résultats sont fictifs. La cohorte `paired_common` garde les mêmes cas et résultats métier pour comparer les délais; les scénarios propres au TO-BE sont identifiés par `tobe_extension`.

## Interprétation

Les journaux ne sont pas des données internes SHEIN et n'estiment pas sa performance réelle. Les champs de statut publics inspirent le schéma; les variantes, durées et probabilités sont des hypothèses pédagogiques définies par le générateur. Les branches et activités sont construites pour correspondre aux BPMN présents dans ce dépôt.

## Formulation recommandée

« Les journaux opérationnels internes n'étant pas publics, nous avons construit deux journaux synthétiques alignés sur les modèles BPMN académique AS-IS et TO-BE. Une cohorte appariée sert à comparer les durées simulées; des cas supplémentaires exercent les branches spécifiques au TO-BE. Ces résultats décrivent la simulation, pas le fonctionnement de SHEIN. »
