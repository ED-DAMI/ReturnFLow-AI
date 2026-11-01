# ReturnFlow AI

**Gestion des retours de vêtements — cas d’étude académique inspiré des politiques publiques de SHEIN Maroc**
BPMN · Process Mining · Workflow AI

Projet du module *BPMN, Process Mining & Workflow AI* — IDSI 3

- **Binôme :** Israe Yaaya & Mohamed
- **Encadrement :** Mme N. AIT MANSOUR
- **Remise :** jeudi 5 novembre 2026

> Ce projet décrit un cas académique. Il ne reproduit pas le processus interne de SHEIN et n’utilise aucun journal opérationnel interne. Les cas, délais et remboursements de démonstration sont simulés; aucun paiement réel n’est exécuté.

## 1. Objectif et état du projet

Le projet compare un processus manuel de référence (**AS-IS**) à un processus cible assisté par automatisation (**TO-BE**). Le TO-BE centralise les tâches automatisées sous le type de job Camunda `shein-agent`, conserve les validations humaines et sépare la décision d’éligibilité du choix de résolution après inspection.

Le BPMN TO-BE et ses formulaires décrivent le flux cible. Un worker Python Camunda 8 consomme maintenant les jobs `shein-agent` et implémente les 14 opérations déclarées dans les en-têtes `operation`. Le prototype FastAPI reste disponible pour tester le parcours RAG séparément. Les connexions SHEIN, notifications externes et opérations financières ne sont pas intégrées; les commandes, notifications et remboursements de démonstration restent simulés. Les décisions d’éligibilité sont déterministes et soumises à la validation du SAV dans le BPMN.

## 2. Processus modélisés

### AS-IS — référence manuelle

Le modèle [AS-IS](camunda/returnflow_as_is.bpmn) décrit la lecture de la demande, la recherche manuelle de commande, la vérification des informations et règles, l’échange éventuel de compléments, la décision d’autorisation, puis la réception, l’inspection, la résolution, la notification et la clôture. Il ne comporte ni IA ni automatisation. Les exceptions non représentées, comme une commande introuvable, sont hors du périmètre AS-IS.

### TO-BE — processus cible

Le modèle [TO-BE](camunda/returnflow_to_be.bpmn) suit ces étapes :

1. Le client soumet une demande; `shein-agent` retrouve la commande, l’article et la fiche produit. Si les références sont introuvables, un agent SAV peut les corriger; sans correction, le client est notifié et le dossier est fermé.
2. `shein-agent` vérifie la complétude. Il demande les informations manquantes, puis le dossier attend le complément. Après **48 heures sans réponse**, le client est informé de la clôture. Le timer est attaché à l’étape d’attente, pas à l’envoi du message.
3. `shein-agent` analyse le motif, récupère les règles via le RAG et extrait les faits sourcés. Si le LLM est indisponible ou si le contexte RAG est insuffisant, l’agent SAV fait l’analyse manuellement. L’éligibilité est ensuite évaluée par des règles déterministes; le LLM ne prend pas seul cette décision.
4. Un refus est expliqué, sourcé, notifié et clôturé. Pour une demande éligible, l’agent SAV valide les faits et l’éligibilité, puis confirme si un retour physique est requis. Le timer non interruptif de **24 heures** déclenche une escalade au superviseur pendant la validation.
5. Si un retour physique est requis, `shein-agent` envoie les instructions; l’entrepôt enregistre la réception et inspecte l’article. En cas d’écart au contrôle qualité, l’agent SAV réévalue le dossier. Le modèle n’impose pas de délai de réception produit: l’attente reste ouverte jusqu’à la confirmation de l’entrepôt.
6. L’agent SAV confirme le mode de résolution. Le flux distingue portefeuille SHEIN, moyen de paiement initial, remboursement sans retour physique et exception manuelle (qui peut couvrir un remplacement ou un traitement SAV spécifique). Le chemin sans retour n’est valide que lorsque `returnRequired = false`; une combinaison incohérente aboutit au traitement manuel par défaut. Les remboursements sont simulés.
7. `shein-agent` prépare la réponse finale et notifie le client; l’agent SAV clôture le dossier.

Les formulaires rattachés aux tâches sont dans [camunda/](camunda/) : demande, correction des références, complément, analyse manuelle, validation SAV, escalade, réception, inspection, réévaluation, résolution, exception et clôture. Les formulaires de validation et de résolution séparent le choix de retour physique du mode de remboursement.

### Tâches automatisées du BPMN TO-BE

Le diagramme contient 17 occurrences de Service Tasks correspondant à 14 opérations distinctes. Les opérations sont identifiées par l’en-tête `operation`; `notify-client` est réutilisée à plusieurs étapes.

| Opération | Rôle dans le flux |
|---|---|
| `fetch-fashion-order-item` | Récupérer commande, article et fiche produit |
| `validate-return-data` | Vérifier les informations minimales |
| `request-additional-information` | Demander un complément au client |
| `classify-fashion-return` | Analyser le motif de retour |
| `retrieve-return-policy-rag` | Récupérer les passages de politique pertinents |
| `extract-grounded-return-facts` | Extraire les faits et leurs références |
| `evaluate-return-eligibility` | Appliquer les règles déterministes |
| `generate-grounded-refusal-response` | Préparer un refus motivé par les règles |
| `notify-client` | Envoyer les notifications de dossier |
| `send-return-instructions` | Envoyer les instructions de retour |
| `refund-shein-wallet` | Enregistrer un remboursement portefeuille simulé |
| `refund-original-payment` | Enregistrer un remboursement sur le moyen initial simulé |
| `refund-without-return` | Enregistrer un remboursement sans retour physique simulé |
| `generate-grounded-final-response` | Rédiger la réponse finale à partir des faits établis |

Le worker [backend/zeebe_worker.py](backend/zeebe_worker.py) consomme le type `shein-agent` par l’API REST Orchestration Cluster Camunda 8. Il lit l’en-tête `operation`, exécute le gestionnaire correspondant dans [backend/returnflow_core.py](backend/returnflow_core.py), écrit les variables de sortie et complète le job. Les tâches qui dépendent d’une intégration indisponible (commande, notification, paiement) utilisent un résultat simulé ou les données fournies par un adaptateur amont. Les échecs techniques utilisent les retries définis dans le BPMN; un job sans retry crée un incident d’exécution à traiter par un opérateur. Le worker ne déploie pas automatiquement le BPMN : déployer le BPMN TO-BE et ses formulaires dans le cluster Camunda avant de démarrer une instance.

## 3. Prototype RAG et configuration

Le module partagé [backend/returnflow_core.py](backend/returnflow_core.py) récupère les extraits pertinents dans PostgreSQL/pgvector et appelle le chat Groq via l’API compatible OpenAI. Les embeddings sont calculés localement avec `intfloat/multilingual-e5-small`; ils ne passent pas par Groq et ne nécessitent pas de clé d’embeddings. Pour générer une réponse, le texte de la demande et les passages RAG retenus sont transmis à Groq; n’indexez et ne traitez ainsi que des documents autorisés pour ce service cloud. L’API FastAPI [backend/shein-agent.py](backend/shein-agent.py) expose une route de démonstration RAG; [backend/zeebe_worker.py](backend/zeebe_worker.py) réutilise les mêmes services pour les jobs BPMN. L’ingestion de `rag_documents/manifest.csv` est réalisée par [embeddings/ingest_rag_documents.py](embeddings/ingest_rag_documents.py). PostgreSQL/pgvector et le RAG restent des détails d’implémentation, pas des acteurs ni des tâches BPMN. [docker-compose.yaml](docker-compose.yaml) démarre uniquement PostgreSQL; Camunda 8 doit être fourni séparément (cluster SaaS ou installation locale).

Créer `.env` depuis `.env.example`, choisir un mot de passe local de base de données et renseigner une clé Groq obtenue dans votre compte :

~~~dotenv
GROQ_API_KEY=
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=openai/gpt-oss-20b
~~~

Le modèle configuré par défaut doit être disponible dans la liste de modèles de votre compte Groq; modifiez `GROQ_MODEL` si nécessaire. Les quotas gratuits conviennent aux essais et démonstrations, mais ne constituent pas une capacité de production garantie. Garder la clé uniquement dans `.env` et ne jamais la committer. Les détails sont dans la [documentation de compatibilité OpenAI Groq](https://console.groq.com/docs/openai), la [liste des modèles](https://console.groq.com/docs/models) et les [limites de débit](https://console.groq.com/docs/rate-limits).

Pour Camunda, renseigner `CAMUNDA_REST_URL` pour une installation locale. Avec Camunda 8 Run, l’URL locale est `http://localhost:8080/v2`; l’installation de développement utilise `demo` / `demo` par défaut, à configurer dans `CAMUNDA_BASIC_USERNAME` et `CAMUNDA_BASIC_PASSWORD`. Pour Camunda SaaS, renseigner `CAMUNDA_REGION`, `CAMUNDA_CLUSTER_ID`, `CAMUNDA_CLIENT_ID`, `CAMUNDA_CLIENT_SECRET` et l’audience fournie avec les identifiants API. Ces paramètres restent dans le `.env` ignoré par Git. Le worker utilise `POST /v2/jobs/activation`, puis les routes de complétion ou d’échec de job de l’API REST Camunda.

### Camunda Modeler et Camunda 8 Run en local

Ouvrir `camunda/returnflow_to_be.bpmn` dans Camunda Modeler. Depuis le dossier d’installation de Camunda 8 Run, démarrer le moteur local avec :

~~~powershell
$env:JAVA_OPTS = "-Xms256m -Xmx768m -XX:MaxMetaspaceSize=256m -XX:MaxDirectMemorySize=256m"
.\c8run.exe start --no-browser --disable-connectors
Remove-Item Env:JAVA_OPTS
~~~

Les connecteurs Camunda intégrés sont désactivés ici car le worker Python traite les jobs `shein-agent`. Déployer le BPMN TO-BE et les formulaires depuis Modeler après une modification, puis lancer le worker. Pour arrêter le moteur, exécuter `.\c8run.exe stop` depuis son dossier d’installation.

Le projet requiert Python 3.14 ou une version ultérieure. Si le port local 5432 est déjà utilisé, choisir `DB_PORT=5433` dans `.env`; cette valeur sert au port publié par Docker Compose et à la connexion de l’API.

Pour lancer les composants actuellement présents, depuis la racine du dépôt :

~~~powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Renseigner DB_PASSWORD, GROQ_API_KEY et les paramètres du cluster Camunda dans .env
docker compose up -d postgres
uv sync
uv run python embeddings/ingest_rag_documents.py
# Camunda 8 Run doit être démarré et le BPMN TO-BE déployé avant ce terminal
# Terminal 1: API de démonstration facultative
uv run python backend/shein-agent.py
# Terminal 2: worker du BPMN TO-BE
uv run python backend/zeebe_worker.py
~~~

Lors de la première ingestion ou recherche, Sentence Transformers télécharge le modèle d’embeddings dans `.model-cache/` (ignoré par Git). L’indexeur crée la table pgvector si nécessaire et indexe les PDF signalés dans le manifeste; relancez-le après une mise à jour du corpus. L’API écoute sur `http://localhost:8000`; sa route `POST /process-return` renvoie les sources et pages retenues. Le worker démarre seulement si l’API REST du cluster Camunda est joignable et si le BPMN est déployé. Pour un test sans système de commandes, `DEMO_ORDER_LOOKUP=true` active une commande fictive (`DEMO-ORDER-001` / `DEMO-ITEM-001`); aucun connecteur SHEIN n’est appelé. Les notifications et remboursements sont consignés comme simulés, sans message externe ni paiement. Les détails d’indexation sont dans [embeddings/README.md](embeddings/README.md). Voir la [spécification Camunda d’activation de jobs](https://docs.camunda.io/docs/apis-tools/orchestration-cluster-api-rest/specifications/activate-jobs/) et les [mécanismes d’authentification REST](https://docs.camunda.io/docs/apis-tools/orchestration-cluster-api-rest/orchestration-cluster-api-rest-authentication/).

## 4. Process Mining

Les journaux sont générés par [generate_synthetic_logs.py](logs/03_synthetic_event_logs/generate_synthetic_logs.py) avec une graine fixe. Ils comprennent 200 cas `paired_common` présents dans les deux versions et 180 cas `tobe_extension` couvrant neuf scénarios propres au TO-BE. Les cas appariés gardent le même scénario et la même issue métier; eux seuls servent à comparer les durées. Les extensions sont analysées à part.

Le script [run_analysis.py](logs/04_process_mining/run_analysis.py) calcule les variantes, le graphe directement-follows, une découverte Inductive Miner, les durées d’activités et de dossiers, la comparaison appariée et les alignements de conformité contre chaque BPMN. Les résultats sont écrits dans `process_mining/outputs/`.

~~~powershell
uv run --with pandas --with pm4py python logs/03_synthetic_event_logs/generate_synthetic_logs.py
uv run --with pandas --with pm4py python logs/04_process_mining/run_analysis.py
~~~

Le schéma est documenté dans [event_log_schema.csv](logs/04_process_mining/event_log_schema.csv), le protocole dans [process_mining_plan.md](logs/04_process_mining/process_mining_plan.md), et les limites de provenance dans [DATA_PROVENANCE.md](logs/05_provenance/DATA_PROVENANCE.md). Toutes les durées, ressources, décisions et identifiants sont synthétiques. Les résultats mesurent le comportement du générateur, pas la performance réelle de SHEIN.

## 5. Structure du dépôt

- `camunda/` — BPMN AS-IS/TO-BE et formulaires Camunda.
- `backend/` — services RAG partagés, API de démonstration et worker Zeebe.
- `rag_documents/` — corpus documentaire pour cadrer les règles métier.
- `embeddings/` — indexeur du corpus RAG et notes sur les embeddings locaux.
- `logs/` — schéma, génération, protocole et provenance.
- `process_mining/outputs/` — rapports produits par le script d’analyse.
- `docs/cadrage_metier.md` — périmètre et décisions de modélisation.
