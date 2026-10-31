# ReturnFlow AI

**Gestion des retours de vêtements — cas d’étude académique inspiré des politiques publiques de SHEIN Maroc**  
BPMN · Process Mining · Workflow AI

Projet du module *BPMN, Process Mining & Workflow AI* — IDSI 3

- **Binôme :** Israe Yaaya & Mohamed
- **Encadrement :** Mme N. AIT MANSOUR
- **Remise :** jeudi 5 novembre 2026

> **Statut :** ce document décrit le périmètre cible du projet. Les fonctionnalités sont à considérer comme prévues jusqu’à leur implémentation et leur validation.
>
> Le processus interne de SHEIN n’est pas reproduit et aucune donnée interne n’est utilisée. Les données, transports et opérations de remboursement sont simulés; aucun paiement réel n’est effectué.

---

## 1. Présentation

ReturnFlow AI est un cas d’étude académique de gestion des retours de vêtements, inspiré des politiques publiques de SHEIN Maroc. Il ne décrit pas le processus interne réel de SHEIN.

Le projet combine :

- **BPMN** : processus manuel de référence AS-IS et processus cible TO-BE sur Camunda 8.10.
- **Process Mining** : analyse d’event logs simulés avec PM4Py.
<<<<<<< HEAD
- **Workflow AI** : RAG sur PostgreSQL + pgvector pour retrouver les politiques; LLM via LangChain/OpenRouter pour classifier et extraire les faits; règles déterministes/DMN pour décider.

### Principe directeur

> Camunda orchestre. Le RAG retrouve les sources. Le LLM comprend la demande et extrait des faits. Les règles déterministes évaluent l’éligibilité. L’agent SAV valide la suite.
=======
- **Workflow AI** : un worker Camunda nommé `shein-agent` exécute les 14 tâches automatisées du BPMN. L’en-tête `operation` distingue leurs traitements : recherche RAG, analyse LLM, évaluation déterministe, notifications et résolutions simulées.

### Principe directeur

> Camunda orchestre. Le worker `shein-agent` exécute les tâches automatisées et reçoit le nom de l’opération dans l’en-tête `operation`. Le LLM analyse et extrait les faits; les règles déterministes évaluent l’éligibilité; l’agent SAV humain valide la suite.
>>>>>>> israe

Deux décisions sont distinguées :

1. **Valider la proposition et le besoin d’un retour physique**, après l’évaluation des règles.
2. **Confirmer le mode de traitement**, après réception et inspection si un retour physique est requis.

La recommandation du LLM ne décide jamais seule de l’éligibilité.

---

## 2. Objectifs

- Modéliser un processus SAV complet.
- Automatiser les contrôles répétitifs.
- Conserver une validation humaine.
- Gérer les informations manquantes.
- Prévoir un fallback en cas d’indisponibilité de l’IA.
- Tracer les décisions et les opérations.
- Mesurer les délais et les goulots d’étranglement.
- Comparer les processus AS-IS et TO-BE sur des données simulées.

---

## 3. Périmètre

### Fonctionnalités prévues

- Saisie de la demande de retour.
- Recherche de la commande et de l’article concerné.
- Vérification des informations et correction des références.
- Demande de complément.
- Classification du motif et recherche de politiques via RAG.
- Extraction de faits avec leurs sources, ou analyse manuelle de repli.
- Contrôle déterministe de l’éligibilité et validation humaine.
- Envoi des instructions de retour.
- Réception simulée du produit.
- Inspection du vêtement, des étiquettes et de la conformité.
- Remboursement simulé selon le mode validé, ou traitement manuel d’une exception.
- Notification finale.
- Clôture du dossier.
- Analyse Process Mining.

### Hors périmètre

- Paiement bancaire réel.
- Intégration à un transporteur réel.
- Gestion complète des stocks.
- Réparation physique.
- Portail client complet.
- Données personnelles réelles.

> Les règles du cas d’étude reprennent des politiques publiques citées; elles ne décrivent pas de processus interne SHEIN ni une interprétation juridique.

---

## 4. Architecture

```text
Camunda 8.10
BPMN · Forms · Tasklist · Operate
<<<<<<< HEAD
              │
              │ REST Connector
              ▼
         API FastAPI
Validation · Règles · Gestion des erreurs
              │
              ├──► PostgreSQL
              │    Commandes · Articles · Retours
              │
              ├──► pgvector
              │    Politiques · FAQ · Guides · Fiches produit
              │
              └──► LangChain → OpenRouter
                   Classification · Extraction · Réponse

Éligibilité déterministe / DMN

Event logs simulés AS-IS / TO-BE
              │
              ▼
             PM4Py
Variantes · Performance · Découverte · Conformité
```

Schéma détaillé prévu : `docs/architecture.png`.
=======
              │ jobs, type = `shein-agent`
              ▼
       Worker `shein-agent`
       dispatch via `operation`
              │
     ┌────────┼─────────┐
     ▼        ▼         ▼
Commandes   RAG + LLM   Règles/DMN
et contrôles sources    déterministes
              │
              ▼
 Réponses · notifications · résolutions simulées

Tâches humaines : validations SAV, réception et inspection
Process Mining : journaux TO-BE / AS-IS → PM4Py
```

Dans le BPMN TO-BE, les 14 tâches de service partagent le type de job `shein-agent`. Leur en-tête `operation` indique le traitement attendu. Le worker et ses intégrations restent à implémenter; aucun stockage PostgreSQL/pgvector n’est modélisé.
>>>>>>> israe

---

## 5. Acteurs

| Acteur | Responsabilité |
|--------|----------------|
| Client | Soumettre la demande, fournir les compléments et retourner le produit |
| Agent SAV | Valider la proposition après contrôle d’éligibilité et confirmer le traitement après inspection |
| Agent entrepôt | Confirmer la réception et inspecter le produit |
| Responsable SAV | Recevoir les escalades |
<<<<<<< HEAD
| Système | Appliquer les règles, enregistrer les opérations et notifier |
| Assistant IA | Classifier, résumer, proposer et rédiger avec des sources RAG |
=======
| `shein-agent` (worker) | Exécuter les 14 tâches automatisées selon l’en-tête `operation` : recherche, RAG, analyse, règles, messages, notifications et résolution simulée |
>>>>>>> israe

Pour la démonstration, certaines actions du client et de l’entrepôt sont représentées par des formulaires.

---

## 6. Processus AS-IS

Le processus AS-IS représente un traitement principalement manuel.

```text
Demande reçue
    ↓
Lecture par l’agent SAV
    ↓
Recherche de la commande
    ↓
Vérification des informations et des règles
    ↓
Échanges avec le client si nécessaire
    ↓
Autorisation ou refus
    ↓
Envoi des instructions
    ↓
Réception et inspection
    ↓
Décision finale
    ↓
Exécution de la résolution
    ↓
Notification et clôture
```

### Problèmes étudiés

- Attente avant validation.
- Informations incomplètes.
- Échanges répétés.
- Vérifications manuelles.
- Manque de visibilité sur l’état du dossier.
- Écarts par rapport au processus attendu.

Ces problèmes sont représentés dans les données simulées.

---

## 7. Processus TO-BE

### Flux principal

| # | Étape | Type BPMN prévu |
|---|-------|-----------------|
| 1 | Saisir la demande et récupérer commande/article/fiche produit | User Task + Service Task |
| 2 | Corriger les références si la commande est introuvable | User Task + XOR Gateway |
| 3 | Vérifier la complétude et demander un complément si nécessaire | Service Task + User Task + Timer 48 h |
| 4 | Classifier le motif avec le LLM, puis vérifier sa disponibilité | Service Task + XOR Gateway |
<<<<<<< HEAD
| 5 | Rechercher la politique avec RAG dans PostgreSQL/pgvector | Service Task + XOR Gateway |
=======
| 5 | Rechercher les politiques avec le RAG de `shein-agent` | Service Task (`operation=retrieve-return-policy-rag`) + XOR Gateway |
>>>>>>> israe
| 6 | Extraire les faits et les sources, ou effectuer une analyse manuelle | Service Task / User Task |
| 7 | Évaluer l’éligibilité par règles déterministes/DMN | Service Task + XOR Gateway |
| 8 | Valider la proposition et le besoin d’un retour physique | User Task + SLA 24 h |
| 9 | Si requis, recevoir et inspecter le vêtement | User Tasks + contrôle qualité |
| 10 | Confirmer le mode de remboursement ou traiter une exception | User Task + sous-processus simulé |
| 11 | Générer la réponse, notifier le client et clôturer | Service Tasks + User Task |

<<<<<<< HEAD
=======
Les 14 Service Tasks du BPMN sont routées vers le même worker `shein-agent`; l’en-tête `operation` sélectionne l’action. Les User Tasks restent assignées aux personnes concernées et conservent leurs formulaires Camunda.

>>>>>>> israe
### Vue simplifiée

```text
Demande → commande et article
    ↓
Complétude ? → correction / complément si nécessaire
    ↓
LLM → RAG + sources → extraction des faits
    └── IA/RAG indisponible → analyse manuelle
    ↓
Règles déterministes / DMN → éligibilité ?
    ├── Non → refus sourcé → notification → fin
    └── Oui → validation humaine + SLA 24 h
              ↓
       Retour physique requis ?
       ├── Non ─────────────────────┐
       └── Oui → réception → inspection → contrôle qualité
                                      ↓
                     choix du traitement simulé / exception
                                      ↓
                         réponse → notification → clôture
```

### Branches alternatives

#### Commande ou article introuvable

- Demander une correction.
- Recevoir les nouvelles informations.
- Relancer la recherche.
- Prévoir une clôture motivée si le dossier ne peut pas être identifié.

#### Demande incomplète

- Identifier les champs manquants.
- Envoyer une demande de complément.
- Saisir ou recevoir la réponse.
- Reprendre la vérification.

#### Retour refusé

- Enregistrer la décision et sa justification.
- Générer une réponse adaptée.
- Notifier le client.
- Clôturer le dossier.

#### IA indisponible

- Positionner `ai_status` à `fallback`.
- Diriger le dossier vers une analyse manuelle.
- Poursuivre la validation SAV.

Un échec de l’IA ne provoque pas automatiquement un refus.

---

## 8. Délais et escalades

### SLA de validation SAV

Un Boundary Timer non interruptif de **24 heures** est prévu sur la tâche de validation SAV.

Lorsqu’il se déclenche :

- la tâche reste active ;
- une relance est enregistrée ;
- le responsable SAV est informé.

> Le timer est attaché à la tâche concernée. Il n’est pas une étape séquentielle du processus.

### Produit non reçu

Le BPMN courant ne modélise pas de timer distinct après l’envoi des instructions de retour. Le délai de non-réception reste à décider avant d’ajouter cette branche.

---

## 9. Réception, inspection et résolution

### Réception

L’agent entrepôt enregistre :

- la date de réception ;
- la quantité reçue ;
- un commentaire éventuel.

### Inspection

L’agent vérifie :

- la référence du produit ;
- la quantité ;
- l’état constaté ;
- la présence des étiquettes d’origine ;
- le défaut déclaré ;
- les éventuelles différences avec la demande.

### Modes de traitement prévus par le BPMN

| Mode | Traitement simulé |
|------|-------------------|
| Portefeuille SHEIN | Enregistrement d’un remboursement fictif sur portefeuille |
| Moyen de paiement initial | Enregistrement d’un remboursement fictif sur le moyen initial |
| Sans retour physique | Enregistrement d’un remboursement fictif sans retour |
| Exception SAV | Prise en charge et justification manuelles |

La clôture intervient uniquement après l’enregistrement de la résolution et de la notification finale.

Le BPMN courant n’a pas encore de branche explicite d’erreur après l’échec d’une exécution simulée; ce comportement reste à modéliser.

---

## 10. Intelligence artificielle

### Analyse de la demande

Sortie structurée attendue :

```json
{
  "category": "SIZE_FIT",
  "summary": "La taille semble trop petite; les étiquettes sont encore attachées.",
  "sentiment": "negative",
  "urgency": "normal",
  "days_since_receipt": 8,
  "item_worn": false,
  "item_washed": false,
  "original_tags_attached": true,
  "policy_source_ids": ["POLICY_CLOTHING_01", "POLICY_RETURN_WINDOW_01"],
  "recommendation": "review_eligibility"
}
```

Cette sortie est illustrative et doit correspondre aux schémas réellement implémentés.

### Utilisations prévues

- Recherche de politiques publiques pertinentes avec RAG et références de sources.
- Classification du motif et extraction de faits structurés.
- Résumé de la demande.
- Suggestion de traitement.
- Aide à la rédaction d’un complément.
- Rédaction des instructions.
- Rédaction de la réponse finale.

### Garde-fous

<<<<<<< HEAD
- Validation des sorties avec Pydantic.
- Séparation entre `ai_suggestion` et `agent_decision`.
- Le LLM ne décide pas l’éligibilité et ne déclenche aucun remboursement.
=======
- Prévoir la validation des sorties structurées avec Pydantic lors de l’implémentation du worker.
- Séparation entre `ai_suggestion` et `agent_decision`.
- Le LLM de `shein-agent` ne décide pas l’éligibilité; les règles/DMN évaluent le dossier et les validations SAV restent humaines. Les opérations de résolution sont simulées.
>>>>>>> israe
- Aucun secret transmis au modèle.
- Données de démonstration fictives.
- Fallback manuel en cas d’erreur.
- Message prédéfini si la génération de réponse échoue.

Les recommandations de l’IA restent consultatives.

---

## 11. Formulaires

| Fichier | Utilisation |
|---------|-------------|
| `form-demande-retour.form` | Références, motif, solution souhaitée, description et état déclaré du vêtement |
| `form-correction-references.form` | Correction de commande/article introuvable |
| `form-complement-information.form` | Réponse du client aux informations manquantes |
| `form-analyse-manuelle.form` | Repli humain quand le LLM/RAG n’est pas disponible |
| `form-validation-sav.form` | Sources RAG, résultat des règles et validation de l’agent |
| `form-escalade-sav.form` | Relance et suivi du SLA par le responsable SAV |
| `form-reception-produit.form` | Réception simulée du vêtement retourné |
| `form-inspection-produit.form` | État, étiquettes, défaut et contrôle qualité |
| `form-reanalyse-apres-inspection.form` | Réévaluation après constat d’un écart |
| `form-resolution-sav.form` | Mode de remboursement simulé et justification |
| `form-resolution-exception.form` | Traitement manuel d’une exception |
| `form-cloture-dossier.form` | Statut de notification et clôture du dossier |

Une pièce justificative peut être représentée par une référence fictive. Le stockage réel de fichiers n’est pas nécessaire au périmètre minimal.

---

<<<<<<< HEAD
## 12. Modèle de données
=======
## 12. Variables métier du processus
>>>>>>> israe

### Commandes et articles

```text
order_id
order_item_id
product_id
product_name
ordered_quantity
purchase_date
delivery_date
unit_price
```

### Dossiers de retour

```text
return_id
order_id
order_item_id
return_quantity
return_reason
requested_resolution
eligibility_status
authorization_status
ai_status
ai_suggestion
agent_decision
received_at
inspection_result
final_resolution
resolution_status
closed_at
```

### États du dossier

```text
submitted
awaiting_information
under_review
refused
authorized
awaiting_product
received
inspected
resolution_in_progress
resolved
closed
```

Chaque retour identifie une ligne de commande et une quantité précise.

---

## 13. Structure du dépôt

```text
ReturnFlow-AI/
├── backend/
│   └── .gitkeep                 # emplacement réservé au worker `shein-agent`
├── camunda/
│   ├── returnflow_as_is.bpmn
│   ├── returnflow_to_be.bpmn
<<<<<<< HEAD
│   ├── form-demande-retour.form
│   ├── form-correction-references.form
│   ├── form-complement-information.form
│   ├── form-analyse-manuelle.form
│   ├── form-validation-sav.form
│   ├── form-escalade-sav.form
│   ├── form-reception-produit.form
│   ├── form-inspection-produit.form
│   ├── form-reanalyse-apres-inspection.form
│   ├── form-resolution-sav.form
│   ├── form-resolution-exception.form
│   ├── form-cloture-dossier.form
│   └── regles-retour.dmn
├── backend/
│   ├── app.py
│   ├── ai_service.py
│   ├── schemas.py
│   ├── database.py
│   ├── seed_database.py
│   ├── policies.json
│   ├── .env.example
│   └── tests/
├── process_mining/
│   ├── generate_log.py
│   ├── process_mining.py
│   ├── event_log_as_is.csv
│   ├── event_log_to_be.csv
│   └── outputs/
├── docs/
│   ├── cadrage_metier.md
│   ├── architecture.png
│   ├── demo_scenarios.md
│   ├── captures/
│   └── presentation.pdf
├── .gitignore
=======
│   └── *.form                   # formulaires du processus TO-BE
├── docs/
│   └── cadrage_metier.md
├── process_mining/
│   ├── .gitkeep
│   └── outputs/.gitkeep
├── src/returnflow_ai/
│   └── __init__.py
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
>>>>>>> israe
├── requirements.txt
├── uv.lock
└── README.md
```

<<<<<<< HEAD
La configuration PostgreSQL/pgvector et le fichier `.env` sont gérés localement; aucun secret ne doit être versionné.
=======
Le dépôt contient le BPMN, les formulaires et le premier socle de dépendances pour le RAG et l’agent. Le worker `shein-agent` reste à implémenter. Aucune base PostgreSQL/pgvector n’est requise par le BPMN.
>>>>>>> israe

---

## 14. Prérequis

<<<<<<< HEAD
- Python 3.11.
- Git.
- Camunda 8 avec un environnement local fonctionnel.
- Camunda Desktop Modeler compatible avec l’environnement retenu.
- Une clé API OpenRouter.

Les versions exactes des outils et bibliothèques sont à fixer après validation de l’intégration.

### Dépendances principales

```text
fastapi
uvicorn
pydantic
python-dotenv
langchain
langchain-openrouter
requests
pm4py
pandas
matplotlib
```

---

## 15. Installation

Les commandes suivantes supposent que les fichiers correspondants ont été implémentés.

### Créer l’environnement Python

Depuis la racine du dépôt :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Configurer les secrets

```powershell
Copy-Item backend/.env.example backend/.env
```

Modifier `backend/.env` :

```env
OPENROUTER_API_KEY=votre_cle_api
OPENROUTER_MODEL=modele_a_configurer
```

Le backend doit charger explicitement ce fichier depuis son emplacement.

### Initialiser les données

```powershell
cd backend
python seed_database.py
```

Le script doit créer la base et les commandes fictives nécessaires à la démonstration.

---

## 16. Lancement

### 1. Démarrer Camunda

Démarrer l’environnement Camunda local selon la distribution et la version installées.

Les URL, identifiants et paramètres de connexion sont à documenter après validation de l’environnement.

### 2. Démarrer FastAPI

Depuis le dossier `backend` :

```powershell
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

- API : `http://localhost:8000`
- Swagger : `http://localhost:8000/docs`

### 3. Configurer les REST Connectors

Configurer l’adresse du backend dans les tâches concernées.

> Si Camunda ou les Connectors s’exécutent dans un conteneur, `localhost` désigne ce conteneur, pas nécessairement la machine hôte. L’adresse du backend doit être adaptée à l’environnement.

### 4. Déployer le processus

- Ouvrir `camunda/returnflow_to_be.bpmn`.
- Vérifier les expressions et mappings.
- Déployer les formulaires.
- Déployer le BPMN sur l’instance locale.

### 5. Démarrer un dossier

- Démarrer une instance.
- Compléter le formulaire de demande.
- Effectuer les validations dans Tasklist.
- Suivre les variables et l’exécution dans Operate.

---

## 17. Contrat API cible

Les routes suivantes décrivent l’API prévue.

| Méthode | Route | Rôle |
|---------|-------|------|
| GET | `/health` | Vérifier la disponibilité |
| GET | `/orders/{order_id}` | Récupérer une commande et ses articles |
| POST | `/eligibility` | Appliquer les règles métier |
| POST | `/ai/analyze` | Produire l’analyse structurée |
| POST | `/ai/generate-response` | Rédiger un message |
| POST | `/returns` | Créer un dossier RMA |
| GET | `/returns/{return_id}` | Consulter le dossier |
| POST | `/returns/{return_id}/authorization` | Enregistrer l’autorisation ou le refus |
| POST | `/returns/{return_id}/receive` | Enregistrer la réception |
| POST | `/returns/{return_id}/inspection` | Enregistrer l’inspection |
| POST | `/returns/{return_id}/resolution` | Enregistrer la décision finale |
| POST | `/returns/{return_id}/execute-resolution` | Exécuter la résolution simulée |
| POST | `/returns/{return_id}/notify` | Simuler la notification |
| POST | `/returns/{return_id}/close` | Clôturer le dossier |

### Gestion des erreurs

- Validation des entrées avec Pydantic.
- Réponse métier exploitable pour une commande introuvable.
- Distinction entre erreur technique et décision métier.
- Fallback si le LLM est indisponible.
- Prévention des doublons lors de la création ou de l’exécution d’une résolution.
- Journalisation sans secrets.

Les réponses doivent être mappées vers les variables du processus Camunda.

---

## 18. Process Mining

### Données

Les logs sont entièrement simulés et générés avec une graine fixe.

Objectif : **60 à 100 dossiers par version de processus**.

Deux fichiers sont prévus :

- `event_log_as_is.csv`
- `event_log_to_be.csv`

### Structure du log

| Colonne | Description |
|---------|-------------|
| `case_id` | Identifiant du dossier |
| `activity` | Nom de l’activité |
| `start_timestamp` | Début de l’activité |
| `end_timestamp` | Fin de l’activité |
| `resource` | Acteur ou système |
| `result` | Résultat de l’activité |
| `process_version` | `AS_IS` ou `TO_BE` |

Exemple :

```csv
case_id,activity,start_timestamp,end_timestamp,resource,result,process_version
RMA-001,Verifier eligibilite,2026-11-01T10:00:00,2026-11-01T10:00:02,System,eligible,TO_BE
RMA-001,Autoriser retour,2026-11-01T10:30:00,2026-11-01T10:35:00,Agent01,authorized,TO_BE
```

Les dates de l’exemple sont fictives.

### Exécution

=======
- Git et Python selon la version indiquée dans pyproject.toml.
- `uv` pour installer les dépendances verrouillées (`uv sync`).
- Camunda 8.10 et Camunda Desktop Modeler compatible.
- Une clé API OpenRouter pour les opérations LLM.
- Une clé Tavily si la recherche Web est utilisée par l’agent.
- Un client Camunda/Zeebe à sélectionner pour l’implémentation du worker.

Les dépendances initiales couvrent LangChain/LangGraph, l’accès à un modèle compatible OpenAI, ChromaDB pour l’index RAG, le traitement PDF et Tavily. Le client Camunda/Zeebe et le contrat d’exécution du worker restent à choisir.

Pour installer l’environnement Python :

```powershell
uv sync
```

---

## 15. Configuration prévue

Copier `.env.example` vers `.env`, puis renseigner les clés nécessaires dans l’environnement local :

```env
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=
TAVILY_API_KEY=
```

`TAVILY_API_KEY` est facultative si l’agent n’utilise pas la recherche Web. Ne pas versionner de clé réelle. Le BPMN ne requiert ni configuration PostgreSQL ni initialisation de base.

---

## 16. Déploiement et exécution

1. Ouvrir `camunda/returnflow_to_be.bpmn` dans Camunda Modeler.
2. Vérifier les formulaires et expressions, puis déployer le BPMN et les formulaires sur Camunda.
3. Implémenter et démarrer un worker qui s’abonne au type de job `shein-agent`.
4. Dans ce worker, lire l’en-tête `operation`, exécuter le traitement correspondant et compléter le job avec les variables attendues.
5. Démarrer une instance, remplir le formulaire de demande, puis suivre les validations humaines dans Tasklist et l’exécution dans Operate.

**État actuel :** le BPMN déclare ce routage, mais le worker n’est pas encore présent; les Service Tasks ne peuvent donc pas être exécutées avant son implémentation.

---

## 17. Contrat du worker `shein-agent`

Chaque Service Task crée un job de type `shein-agent`. L’en-tête Camunda `operation` permet au worker unique de distinguer les traitements :

| Valeur de `operation` | Traitement |
|---------------------|------------|
| `fetch-fashion-order-item` | Récupérer la commande, l’article et la fiche produit |
| `validate-return-data` | Vérifier les informations minimales |
| `classify-fashion-return` | Classifier le motif du retour |
| `retrieve-return-policy-rag` | Rechercher les sources de politique avec le RAG |
| `extract-grounded-return-facts` | Extraire les faits et preuves sourcées |
| `evaluate-return-eligibility` | Appliquer les règles déterministes/DMN |
| `generate-grounded-refusal-response` | Rédiger un refus expliqué et sourcé |
| `notify-client` | Simuler une notification client |
| `send-return-instructions` | Générer/envoyer les instructions de retour |
| `refund-shein-wallet` | Enregistrer le remboursement simulé sur portefeuille |
| `refund-original-payment` | Enregistrer le remboursement simulé sur le moyen initial |
| `refund-without-return` | Enregistrer la résolution simulée sans retour |
| `generate-grounded-final-response` | Rédiger la réponse finale sourcée |

Les entrées et sorties précises de chaque opération doivent être définies avec les variables du BPMN avant l’implémentation. Les User Tasks et leurs formulaires restent traités par les utilisateurs humains.

---

## 18. Process Mining

### Données

Les logs sont entièrement simulés et générés avec une graine fixe.

Objectif : **60 à 100 dossiers par version de processus**.

Deux fichiers sont prévus :

- `event_log_as_is.csv`
- `event_log_to_be.csv`

### Structure du log

| Colonne | Description |
|---------|-------------|
| `case_id` | Identifiant du dossier |
| `activity` | Nom de l’activité |
| `start_timestamp` | Début de l’activité |
| `end_timestamp` | Fin de l’activité |
| `resource` | Acteur, worker ou système |
| `result` | Résultat de l’activité |
| `process_version` | `AS_IS` ou `TO_BE` |

Exemple :

```csv
case_id,activity,start_timestamp,end_timestamp,resource,result,process_version
RMA-001,Verifier eligibilite,2026-11-01T10:00:00,2026-11-01T10:00:02,shein-agent,eligible,TO_BE
RMA-001,Autoriser retour,2026-11-01T10:30:00,2026-11-01T10:35:00,Agent01,authorized,TO_BE
```

Les dates de l’exemple sont fictives.

### Exécution

>>>>>>> israe
Depuis la racine du dépôt :

```powershell
python process_mining/generate_log.py
python process_mining/process_mining.py
```

### Analyses prévues

1. Variantes de processus.
2. Découverte par DFG ou Inductive Miner.
3. Durées de traitement par activité.
4. Temps entre activités.
5. Détection des goulots.
6. Conformance checking.
7. Comparaison AS-IS / TO-BE.

La conformité doit être évaluée par rapport à un modèle de référence explicite. La découverte seule ne constitue pas un contrôle de conformité.

### KPI

- Délai demande → autorisation.
- Délai autorisation → réception.
- Délai réception → résolution.
- Durée totale d’un dossier.
- Taux de demandes de complément.
- Taux de refus.
- Taux de fallback IA.
- Proportion de propositions IA modifiées par l’agent.
- Nombre de dépassements du SLA.

> Les gains AS-IS / TO-BE sont des résultats de simulation, pas des améliorations mesurées en entreprise.

---

## 19. Scénarios de test

| # | Scénario | Résultat attendu |
|---|----------|------------------|
| 1 | Demande éligible | Extraction sourcée, règles déterministes, validation agent |
| 2 | Demande hors règles | Refus expliqué et notification |
| 3 | Commande introuvable | Correction des références ou clôture |
| 4 | Informations manquantes | Complément puis nouvelle vérification; clôture après 48 h |
| 5 | IA indisponible | Analyse manuelle des faits et des règles |
| 6 | Contexte RAG insuffisant | Revue manuelle sans décision LLM autonome |
| 7 | SLA de validation dépassé | Escalade au responsable SAV après 24 h |
| 8 | Retour physique non requis | Résolution simulée sans étape de réception |
| 9 | Contrôle qualité conforme | Poursuite vers le mode de traitement choisi |
| 10 | Contrôle qualité non conforme | Réévaluation humaine après inspection |
| 11 | Mode de remboursement standard | Portefeuille ou moyen de paiement initial simulé |
| 12 | Exception de traitement | Prise en charge manuelle et traçable |

Détails prévus : `docs/demo_scenarios.md`.

---

## 20. Captures attendues

À ajouter après implémentation :

- `docs/captures/as_is.png`
- `docs/captures/to_be.png`
- `docs/captures/tasklist_demande.png`
- `docs/captures/tasklist_inspection.png`
- `docs/captures/operate_ai.png`
- `docs/captures/process_mining.png`

---

## 21. Démonstration

1. Présenter le problème métier.
2. Montrer le processus AS-IS.
3. Présenter les résultats Process Mining.
4. Montrer le TO-BE dans Camunda.
5. Soumettre une demande.
6. Montrer les règles d’éligibilité et l’analyse IA.
7. Examiner les sources et la décision des règles, puis valider la proposition dans Tasklist.
8. Simuler la réception.
9. Compléter l’inspection.
10. Valider et exécuter la résolution simulée.
11. Montrer la notification et la clôture.
12. Illustrer un fallback ou une escalade.

### Message de conclusion

<<<<<<< HEAD
> BPMN orchestre, les règles encadrent, l’IA assiste, l’humain décide et le Process Mining mesure.
=======
> Camunda orchestre, `shein-agent` exécute les tâches automatisées, les règles encadrent l’éligibilité, l’agent SAV humain valide les décisions métier et le Process Mining mesure.
>>>>>>> israe

---

## 22. Plan de réalisation

<<<<<<< HEAD
### Phase 1 — Socle

- [ ] Créer le dépôt.
- [ ] Définir les règles pédagogiques.
- [ ] Modéliser l’AS-IS.
- [ ] Modéliser le TO-BE.
- [ ] Créer les commandes fictives.
- [ ] Implémenter FastAPI.

### Phase 2 — Traitement de la demande

- [ ] Créer le formulaire de demande.
- [ ] Récupérer la commande et l’article.
- [ ] Vérifier les informations.
- [ ] Ajouter la boucle de complément.
- [ ] Implémenter l’éligibilité.
- [ ] Intégrer l’analyse IA.
- [ ] Ajouter le fallback.
- [ ] Créer la validation SAV.

### Phase 3 — Retour et résolution

- [ ] Créer le dossier RMA.
- [ ] Générer les instructions.
- [ ] Ajouter la réception.
- [ ] Ajouter l’inspection.
- [ ] Ajouter la décision finale.
- [ ] Simuler remboursement, échange ou réparation.
- [ ] Ajouter la notification et la clôture.
- [ ] Ajouter le timer SLA.

### Phase 4 — Analyse et livraison

- [ ] Générer les logs AS-IS et TO-BE.
- [ ] Produire les analyses PM4Py.
- [ ] Tester les scénarios.
- [ ] Ajouter les captures.
- [ ] Finaliser le README.
- [ ] Préparer la présentation.
=======
### Phase 1 — Modèle et contrat du worker

- [x] Modéliser l’AS-IS et le TO-BE.
- [x] Créer les formulaires humains du TO-BE.
- [x] Router les tâches automatisées vers `shein-agent`.
- [ ] Définir les variables d’entrée/sortie par valeur de l’en-tête `operation`.
- [ ] Choisir le client Camunda/Zeebe et la configuration d’exécution.

### Phase 2 — Implémentation de `shein-agent`

- [ ] Implémenter le worker abonné au type de job `shein-agent`.
- [ ] Ajouter la récupération des données de commande et les contrôles.
- [ ] Intégrer RAG et LLM avec sources et sorties structurées.
- [ ] Implémenter les règles déterministes/DMN.
- [ ] Ajouter réponses, notifications et résolutions simulées.
- [ ] Gérer indisponibilités, erreurs, reprises et idempotence.
- [ ] Préserver les validations SAV et les autres User Tasks.

### Phase 3 — Process Mining et livraison

- [ ] Générer les journaux AS-IS et TO-BE.
- [ ] Produire les analyses PM4Py.
- [ ] Vérifier les scénarios de démonstration dans Camunda.
- [ ] Ajouter les captures et finaliser la présentation.
>>>>>>> israe
- [ ] Répéter la démonstration.

---

## 23. Répartition du travail

| Membre | Responsabilités principales |
|--------|-----------------------------|
| Israe Yaaya | BPMN, formulaires, Process Mining, documentation métier |
<<<<<<< HEAD
| Mohamed | FastAPI, LLM, PostgreSQL/pgvector, règles et gestion des erreurs |

### Travail commun

- Architecture.
- Contrats API.
- Intégration Camunda ↔ FastAPI.
- Variables et mappings.
- Tests.
- Scénarios de démonstration.
=======
| Mohamed | Worker `shein-agent`, intégration LLM/RAG, règles et gestion des erreurs |

### Travail commun

- Contrat des variables Camunda et des opérations du worker.
- Intégration du worker au processus Camunda.
- Journaux et scénarios de démonstration.
>>>>>>> israe
- Présentation finale.

Chaque membre doit pouvoir expliquer le fonctionnement global du système.

---

## 24. Sécurité et Git

- Ne jamais versionner les secrets.
<<<<<<< HEAD
- Versionner `.env.example`, sans clé réelle.
=======
- Si un fichier `.env.example` est ajouté, n’y inclure aucune clé réelle.
>>>>>>> israe
- Utiliser uniquement des données fictives.
- Ne pas afficher la clé API dans les captures.
- Tester avant fusion dans `main`.
- Utiliser des branches courtes.
- Conserver les données nécessaires à la reproduction des analyses.

### Exemple de `.gitignore`

```gitignore
# Secrets
.env
.env.*
!.env.example

# Python
.venv/
__pycache__/
*.py[cod]
.pytest_cache/

# Bases locales
*.db
*.db-shm
*.db-wal
*.sqlite
*.sqlite3

# Journaux
*.log

# Éditeurs et système
.vscode/
.idea/
.DS_Store
Thumbs.db
```

---

## 25. Critères de réussite

Le projet est considéré comme démontrable lorsque :

- une demande peut parcourir le processus complet ;
- les branches de refus et de complément fonctionnent ;
- l’échec de l’IA permet un traitement manuel ;
- l’agent valide les décisions métier ;
- la réception et l’inspection sont tracées ;
- la résolution simulée possède un résultat enregistré ;
- le dossier est clôturé après notification ;
- les analyses Process Mining sont reproductibles ;
- aucune donnée sensible n’est présente dans le dépôt.

---

*ReturnFlow AI est un projet pédagogique utilisant exclusivement des données et opérations simulées.*
