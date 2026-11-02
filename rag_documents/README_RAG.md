# ReturnFlow AI — corpus RAG

Ce dossier conserve les sources publiques, guides, fiches et règles académiques du projet. Le RAG actif est volontairement limité à un seul document : `Synthese_Politique_de_Retour_SHEIN_Maroc.pdf` à la racine de ce dossier.

## Provenance et usage

- Les fichiers `official_user_supplied` sont issus des documents fournis pour le projet.
- Les fichiers `public_source_normalized` résument ou structurent les pages publiques référencées dans `sources.csv`.
- Les fichiers `academic_simulated` définissent des règles et exemples propres au cas académique; ils ne doivent pas être présentés comme des politiques SHEIN officielles ou internes.
- `manifest.csv` et `metadata.json` décrivent le corpus et l’activation RAG. Un seul fichier doit avoir `use_for_rag=true` : la synthèse indiquée ci-dessus.
- Les autres PDF présents dans ce dossier sont conservés comme références du projet, mais ils ne sont pas indexés ni utilisés par l’agent.

## Ingestion et récupération RAG

Le script [`../embeddings/ingest_rag_documents.py`](../embeddings/ingest_rag_documents.py) n’accepte que `Synthese_Politique_de_Retour_SHEIN_Maroc.pdf`, seul fichier marqué `use_for_rag=true` dans le manifeste. Il extrait le texte et les numéros de page, puis indexe des passages de 420 tokens avec un chevauchement de 60 tokens dans PostgreSQL/pgvector. Chaque ligne vectorielle associe le chunk et son embedding à un identifiant de chunk, l’empreinte SHA-256 du PDF source, la page, l’ordinal du chunk, les offsets de début et de fin dans le texte extrait de la page, et les empreintes du texte de page et du chunk. Les résultats de recherche exposent ces références pour retrouver le passage dans la version exacte du PDF. Le service filtre aussi sur l’identifiant exact de la source.

Le chevauchement de 60 tokens est une valeur de départ configurable, pas un optimum mesuré. Il limite les portions de texte répétées tout en conservant du contexte entre les chunks. Une valeur de 100 peut aider si une règle est souvent coupée à une limite, mais répète davantage de texte et peut augmenter le nombre de passages. Comparez les résultats sur des questions représentatives avant d’arrêter votre choix.

Les embeddings multilingues `intfloat/multilingual-e5-small` sont calculés localement; le préfixe `passage:` est utilisé à l’indexation et `query:` à la recherche. La génération des réponses utilise séparément le chat Groq. L’API renvoie les références de source et les pages retenues avec la réponse.

Pour préparer l’index, lancer PostgreSQL, installer les dépendances du projet puis exécuter depuis la racine `uv run python embeddings/ingest_rag_documents.py`. Voir [`../embeddings/README.md`](../embeddings/README.md) et le README principal pour la configuration Groq et le lancement de l’API.

L’opération BPMN `retrieve-return-policy-rag` est exécutée par `backend/zeebe_worker.py` via les services partagés de `backend/returnflow_core.py`; l’API FastAPI conserve une route séparée pour tester le même RAG à source unique.
