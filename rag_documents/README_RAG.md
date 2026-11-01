# ReturnFlow AI — corpus RAG

Ce corpus rassemble des sources publiques de référence, des guides de mode, des fiches produits et des règles académiques utilisées pour cadrer le projet.

## Provenance et usage

- Les fichiers `official_user_supplied` sont issus des documents fournis pour le projet.
- Les fichiers `public_source_normalized` résument ou structurent les pages publiques référencées dans `sources.csv`.
- Les fichiers `academic_simulated` définissent des règles et exemples propres au cas académique; ils ne doivent pas être présentés comme des politiques SHEIN officielles ou internes.
- `manifest.csv` est la liste de référence des documents destinés à l’indexation. `metadata.json` en fournit une représentation structurée. Préserver `source_type`, `language`, `country` et `use_for_rag`.
- Les trois PDF à la racine sont des copies des versions classées sous `01_sources_officielles`; ils ne sont pas des entrées distinctes du manifeste et ne doivent pas être indexés deux fois.

## Ingestion et récupération RAG

Le script [`../embeddings/ingest_rag_documents.py`](../embeddings/ingest_rag_documents.py) lit les entrées `use_for_rag=true` du manifeste, extrait le texte et les numéros de page des PDF, puis indexe des passages de 420 tokens avec un chevauchement de 60 tokens dans PostgreSQL/pgvector. Chaque passage conserve son identifiant de source, son type, sa langue, son pays et sa page.

Les embeddings multilingues `intfloat/multilingual-e5-small` sont calculés localement; le préfixe `passage:` est utilisé à l’indexation et `query:` à la recherche. La génération des réponses utilise séparément le chat Groq. L’API renvoie les références de source et les pages retenues avec la réponse.

Pour préparer l’index, lancer PostgreSQL, installer les dépendances du projet puis exécuter depuis la racine `uv run python embeddings/ingest_rag_documents.py`. Voir [`../embeddings/README.md`](../embeddings/README.md) et le README principal pour la configuration Groq et le lancement de l’API.

Pour les questions sur les politiques publiques, privilégier les sources officielles ou normalisées et distinguer clairement les règles académiques. Le BPMN TO-BE prévoit l’opération `retrieve-return-policy-rag` pour le worker `shein-agent`; le prototype FastAPI enrichi par ce pipeline reste distinct d’un worker Zeebe et ne traite pas encore les jobs Camunda.
