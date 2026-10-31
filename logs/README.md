# ReturnFlow AI - dossier logs

Ce dossier rassemble tout ce qui concerne les logs et donnees de contexte du projet ReturnFlow AI.

## Contenu

- `00_sources/`: sources officielles SHEIN et datasets publics reperes.
- `01_api_reference/`: champs et mappings de statuts issus de la documentation SHEIN.
- `02_public_data/`: liens et instructions pour datasets publics produits/reviews.
- `03_synthetic_event_logs/`: event log academique de 200 dossiers + generateur reproductible.
- `04_process_mining/`: schema PM4Py et plan d'analyse.
- `05_provenance/`: distinction entre donnees reelles, publiques et synthetiques.

## Point essentiel

Aucun vrai journal interne client SHEIN n'a ete trouve en acces public. Le CSV de retours du projet est donc synthetique, mais sa structure est inspiree des APIs officielles SHEIN et de la machine d'etats apres-vente publique.

## Sources de reference

Voir `00_sources/sources.csv` et `00_sources/official_shein_api_sources.md`.

## Test rapide PM4Py

```powershell
pip install -r requirements.txt
python 04_process_mining/pm4py_quickstart.py
```

Le script d'analyse est fourni mais PM4Py doit etre installe dans votre environnement local avant execution.
