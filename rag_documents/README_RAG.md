# ReturnFlow AI — corpus RAG

Ce corpus rassemble des sources publiques de référence, des guides de mode, des fiches produits et des règles académiques utilisées pour cadrer le projet.

## Provenance et usage

- Les fichiers `official_user_supplied` sont issus des documents fournis pour le projet.
- Les fichiers `public_source_normalized` résument ou structurent les pages publiques référencées dans `sources.csv`.
- Les fichiers `academic_simulated` définissent des règles et exemples propres au cas académique; ils ne doivent pas être présentés comme des politiques SHEIN officielles ou internes.
- `manifest.csv` est la liste de référence des documents destinés à l’indexation. `metadata.json` en fournit une représentation structurée. Préserver `source_type`, `language`, `country` et `use_for_rag`.
- Les trois PDF à la racine sont des copies des versions classées sous `01_sources_officielles`; ils ne sont pas des entrées distinctes du manifeste et ne doivent pas être indexés deux fois.

## Ingestion prévue

1. Extraire le texte des PDF et conserver les identifiants de source.
2. Découper le texte par section (environ 500 à 900 tokens, chevauchement de 80 à 120) sans séparer les conditions d’une même règle.
3. Indexer les passages avec le moteur choisi lors de l’implémentation du worker. Le manifeste ne prescrit ni base de données ni moteur de stockage.
4. Conserver les métadonnées du manifeste avec chaque passage et retourner les identifiants de source avec les réponses RAG.
5. Pour les questions sur les politiques publiques, privilégier les sources officielles ou normalisées et distinguer clairement les règles académiques.

Le BPMN TO-BE prévoit l’opération `retrieve-return-policy-rag` pour le worker `shein-agent`. Le prototype FastAPI actuel ne traite pas les jobs Zeebe et n’ingère pas encore ce manifeste. Le worker, l’ingestion du corpus et le contrat de retour des références restent à implémenter.
