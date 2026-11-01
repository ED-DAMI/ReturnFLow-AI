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

Le BPMN TO-BE et ses formulaires décrivent le flux cible. Les scripts de génération et d’analyse Process Mining sont disponibles. Le code FastAPI/LangGraph est un prototype de question-réponse RAG; **il n’est pas encore le worker de jobs Zeebe** et ne réalise pas les 14 opérations du BPMN. Tant que l’adaptateur/worker Zeebe n’est pas développé et déployé, les jobs `shein-agent` du diagramme ne sont pas exécutés par cette API. Les opérations financières du diagramme restent simulées.

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

Un worker Camunda/Zeebe devra consommer le type `shein-agent`, traiter l’opération demandée, écrire les variables de processus attendues et compléter le job. Le prototype actuel ne fournit pas encore cette capacité. Les échecs techniques épuisant les retries Camunda doivent être traités comme incidents d’exécution par un opérateur; ils ne sont pas assimilés à une décision métier ni à un échec de paiement.

## 3. Prototype RAG et configuration

Le prototype [backend/shein-agent.py](backend/shein-agent.py) expose une API FastAPI qui récupère des extraits depuis PostgreSQL avec pgvector puis génère une réponse avec LangGraph et `ChatOpenAI`. PostgreSQL/pgvector est un détail d’implémentation, pas un acteur ni une tâche du BPMN. [docker-compose.yaml](docker-compose.yaml) démarre uniquement PostgreSQL avec l’extension pgvector; l’API et Zeebe ne sont pas inclus.

Copier `.env.example` vers `.env`, définir un mot de passe local de base de données et configurer le fournisseur LLM compatible avec l’API OpenAI :

~~~dotenv
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
~~~

Ces variables configurent directement une clé et une URL de fournisseur compatible; le dépôt ne fixe aucun fournisseur par défaut. Ne jamais ajouter de vraie clé au dépôt. Sans ces paramètres, la génération LLM renvoie une erreur de configuration explicite.

Pour lancer les composants actuellement présents, depuis la racine du dépôt :

~~~powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Renseigner DB_PASSWORD et les variables LLM dans .env
docker compose up -d postgres
uv sync
uv run python backend/shein-agent.py
~~~

L’API écoute sur `http://localhost:8000`; sa route de démonstration est `POST /process-return`. Elle ne consomme pas les jobs Zeebe. Le schéma vectoriel et le chargement des documents doivent être initialisés séparément avant les requêtes sur un corpus RAG.

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
- `backend/` — prototype API RAG, pas encore le worker Zeebe.
- `rag_documents/` — corpus documentaire pour cadrer les règles métier.
- `embeddings/` — artefacts d’embeddings du prototype.
- `logs/` — schéma, génération, protocole et provenance.
- `process_mining/outputs/` — rapports produits par le script d’analyse.
- `docs/cadrage_metier.md` — périmètre et décisions de modélisation.
