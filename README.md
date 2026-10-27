# ReturnFlow AI

**Service après-vente : retour d'un produit**
BPMN · Process Mining · Workflow AI

Projet du module *BPMN, Process Mining & Workflow AI* (IDSI 3)
Binôme : Israe Yaaya & Mohamed · Encadrement : Mme N. AIT MANSOUR · Remise : jeudi 5 novembre 2026

---

## 1. Présentation

ReturnFlow AI est un mini-système SAV intelligent pour la gestion des retours de produits :

- **BPMN** : le processus (AS-IS puis TO-BE) est modélisé et exécuté sur **Camunda 8**.
- **Process Mining** : un event log simulé est analysé avec **PM4Py** (variantes, goulots, conformité).
- **Workflow AI** : un LLM (**LangChain + OpenRouter**) intervient dans des tâches ciblées : classification du motif, résumé, suggestion et rédaction de la réponse client.

> **Principe directeur** : Camunda garde le contrôle du chemin et des règles. L'IA comprend, résume, propose et rédige. La décision finale reste à l'agent SAV (human-in-the-loop).

## 2. Architecture

```
Camunda 8 (BPMN, Forms, Tasklist, Operate)
        │  REST Connector
        ▼
   FastAPI (API REST, validation Pydantic)
        │                     │
        ▼                     ▼
 LangChain → OpenRouter     SQLite / JSON
     (LLM)                (commandes, règles)

Event log (CSV) ──► PM4Py (discovery, performance, conformance)
```

Schéma détaillé : `docs/architecture.png`

## 3. Processus TO-BE (12 étapes)

| # | Étape | Type |
|---|-------|------|
| 1 | Demande de retour reçue | Start Event |
| 2 | Saisir la demande de retour | User Task + Form |
| 3 | Récupérer la commande | REST Service Task |
| 4 | Commande trouvée ? | Gateway XOR |
| 5 | Analyser la demande avec IA | REST Service Task |
| 6 | Vérifier l'éligibilité | Service Task (ou DMN) |
| 7 | Retour éligible ? | Gateway XOR |
| 8 | Valider la solution proposée | User Task (human-in-the-loop) |
| 9 | Timer SLA 24 h | Boundary Timer |
| 10 | Organiser le retour | Service / User Task |
| 11 | Générer la réponse client | REST + LLM |
| 12 | Notifier le client | Service / Send Task |

## 4. Structure du dépôt

```
ReturnFlow-AI/
├── camunda/
│   ├── returnflow_as_is.bpmn
│   ├── returnflow_to_be.bpmn
│   ├── form-demande-retour.form
│   ├── form-validation-sav.form
│   └── regles-retour.dmn          (optionnel / bonus)
├── backend/
│   ├── app.py                     API FastAPI
│   ├── ai_service.py              LangChain + OpenRouter
│   ├── schemas.py                 Modèles Pydantic
│   ├── database.py                Accès SQLite
│   ├── policies.json              Règles de retour
│   ├── orders.db                  Commandes simulées
│   └── .env                       Secrets (jamais versionné)
├── process_mining/
│   ├── generate_log.py            Génération de l'event log simulé
│   ├── process_mining.py          Analyses PM4Py
│   ├── event_log.csv
│   └── outputs/                   Graphiques et résultats
├── docs/
│   ├── architecture.png
│   ├── demo_scenarios.md
│   └── presentation.pdf
├── requirements.txt
└── README.md
```

## 5. Prérequis

- Camunda Desktop Modeler 5.52.x
- Camunda 8.10 / c8run
- Python 3.11
- Git
- Une clé API [OpenRouter](https://openrouter.ai)

## 6. Installation

```powershell
git clone https://github.com/<utilisateur>/ReturnFlow-AI.git
cd ReturnFlow-AI

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Dépendances principales : `fastapi`, `uvicorn`, `langchain`, `langchain-openrouter`, `pydantic`, `python-dotenv`, `requests`, `pm4py`, `pandas`, `matplotlib`.

### Configuration des secrets

Créer le fichier `backend/.env` (**ne jamais l'envoyer sur GitHub**) :

```env
OPENROUTER_API_KEY=votre_cle_api
OPENROUTER_MODEL=nom_du_modele
```

## 7. Lancement

**1. Démarrer Camunda 8 (c8run)**

```powershell
.\c8run.exe start
```

Operate et Tasklist sont ensuite accessibles en local (voir la documentation c8run pour les URL et identifiants par défaut).

**2. Démarrer l'API FastAPI**

```powershell
cd backend
uvicorn app:app --reload
```

- API : http://localhost:8000
- Documentation Swagger : http://localhost:8000/docs

**3. Déployer le processus**

Dans Camunda Modeler, ouvrir `camunda/returnflow_to_be.bpmn`, puis déployer le BPMN et les formulaires (`.form`) sur l'instance locale.

**4. Démarrer une instance**

Lancer une instance du processus, puis remplir le formulaire dans Tasklist.

## 8. Endpoints de l'API

| Méthode | Route | Rôle |
|---------|-------|------|
| GET | `/health` | Vérifier que l'API répond |
| GET | `/orders/{order_id}` | Récupérer une commande |
| POST | `/eligibility` | Appliquer les règles de retour |
| POST | `/ai/analyze` | Catégorie, résumé, sentiment, urgence, suggestion |
| POST | `/ai/generate-response` | Rédiger la réponse client |

La sortie de l'IA est un **JSON structuré** (validé par Pydantic). En cas d'échec d'OpenRouter, un **fallback** renvoie la demande vers une analyse manuelle par l'agent SAV.

## 9. Scénarios de test

| # | Scénario | Résultat attendu |
|---|----------|------------------|
| 1 | Retour accepté | Produit éligible, l'agent confirme |
| 2 | Retour refusé | Hors délai ou non conforme aux règles |
| 3 | Produit défectueux | Recommandation échange / réparation |
| 4 | Informations manquantes | Boucle vers complément d'information |
| 5 | OpenRouter indisponible | Fallback vers analyse manuelle |
| 6 | SLA dépassé | Déclenchement du timer et escalade |

Détails : `docs/demo_scenarios.md`

## 10. Process Mining

Les données sont **simulées** : 60 à 100 dossiers, générés de façon reproductible.

```powershell
python process_mining/generate_log.py
python process_mining/process_mining.py
```

Colonnes de `event_log.csv` :

| Colonne | Exemple |
|---------|---------|
| `case_id` | RMA-001 |
| `activity` | Analyser demande |
| `timestamp` | 2026-11-01 10:42:15 |
| `resource` | Agent01 / AI / System |
| `result` | eligible / refused / exchange |

Analyses produites (dans `process_mining/outputs/`) :

1. Variantes de processus
2. Découverte du processus réel (DFG ou Inductive Miner)
3. Temps moyen et temps d'attente par activité
4. Détection du goulot d'étranglement
5. Conformance checking
6. Comparaison AS-IS vs TO-BE sur quelques KPI

## 11. Captures principales

<!-- Ajouter les captures dans docs/ puis les référencer ici -->

- BPMN AS-IS : `docs/captures/as_is.png`
- BPMN TO-BE : `docs/captures/to_be.png`
- Tasklist et formulaire de validation : `docs/captures/tasklist.png`
- Variables IA dans Operate : `docs/captures/operate_ai.png`
- Résultats PM4Py : `docs/captures/process_mining.png`

## 12. Démonstration

1. Montrer l'AS-IS : pourquoi le processus actuel est lent / manuel
2. Montrer le Process Mining : variantes, délais, goulot, non-conformités
3. Montrer le TO-BE dans Camunda
4. Démarrer une instance et remplir le formulaire
5. Montrer les variables produites par l'IA (catégorie, résumé, suggestion)
6. Human-in-the-loop : l'agent SAV valide ou modifie la proposition
7. Fin du workflow : réponse personnalisée, instance terminée
8. Conclusion : BPMN orchestre, Process Mining mesure, IA enrichit

## 13. Règles de l'équipe

- Tout fichier important est versionné dans Git.
- Chacun travaille sur une branche courte, puis fusionne dans `main` après test.
- Le fichier `.env` n'est jamais envoyé sur GitHub.
- Chaque membre doit pouvoir expliquer l'ensemble du système.

## 14. Équipe

| Membre | Rôle |
|--------|------|
| Israe Yaaya | Modélisation BPMN, Camunda Forms, Process Mining, documentation métier |
| Mohamed | Backend FastAPI, LangChain + OpenRouter, base de données, gestion des erreurs et fallback |

Travail commun : architecture, intégration Camunda ↔ API, tests, scénarios de démonstration et présentation.

---

*Les données utilisées dans ce projet sont entièrement simulées.*
