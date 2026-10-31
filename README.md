# ReturnFlow AI

**Service après-vente : gestion d’un retour produit de la demande à la résolution**  
BPMN · Process Mining · Workflow AI

Projet du module *BPMN, Process Mining & Workflow AI* — IDSI 3

- **Binôme :** Israe Yaaya & Mohamed
- **Encadrement :** Mme N. AIT MANSOUR
- **Remise :** jeudi 5 novembre 2026

> **Statut :** ce document décrit le périmètre cible du projet. Les fonctionnalités sont à considérer comme prévues jusqu’à leur implémentation et leur validation.
>
> Les données, transports, remboursements, échanges et réparations sont simulés. Aucun paiement réel n’est effectué.

---

## 1. Présentation

ReturnFlow AI est un mini-système SAV intelligent permettant de gérer un retour produit depuis la demande du client jusqu’à la résolution et la clôture du dossier.

Le projet combine :

- **BPMN** : modélisation AS-IS et TO-BE, puis exécution du processus TO-BE sur Camunda 8.
- **Process Mining** : analyse d’event logs simulés avec PM4Py.
- **Workflow AI** : analyse et rédaction assistées par un LLM via LangChain et OpenRouter.

### Principe directeur

> Camunda orchestre le processus. Les règles métier déterminent l’éligibilité. L’IA analyse, résume, propose et rédige. L’agent SAV valide les décisions métier.

Deux décisions sont distinguées :

1. **Autoriser le retour**, avant l’expédition du produit.
2. **Confirmer la résolution finale**, après réception et inspection.

L’autorisation de retour ne constitue donc pas une validation automatique du remboursement.

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
- Vérification des informations.
- Demande de complément.
- Contrôle d’éligibilité.
- Analyse IA ou analyse manuelle.
- Autorisation ou refus par l’agent SAV.
- Création d’un identifiant de retour RMA.
- Envoi des instructions de retour.
- Réception simulée du produit.
- Inspection du produit.
- Validation de la résolution finale.
- Remboursement, échange ou réparation simulé.
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

> Les règles et délais sont des hypothèses pédagogiques. Ils ne constituent pas une politique commerciale réelle ni une interprétation juridique.

---

## 4. Architecture

```text
Camunda 8
BPMN · Forms · Tasklist · Operate
              │
              │ REST Connector
              ▼
         API FastAPI
Validation · Règles · Gestion des erreurs
              │
              ├──► SQLite
              │    Commandes · Articles · Retours
              │
              ├──► policies.json
              │    Règles pédagogiques
              │
              └──► LangChain → OpenRouter
                   Analyse et rédaction IA

Event logs simulés AS-IS / TO-BE
              │
              ▼
             PM4Py
Variantes · Performance · Découverte · Conformité
```

Schéma détaillé prévu : `docs/architecture.png`.

---

## 5. Acteurs

| Acteur | Responsabilité |
|--------|----------------|
| Client | Soumettre la demande, fournir les compléments et retourner le produit |
| Agent SAV | Autoriser le retour et valider la résolution finale |
| Agent entrepôt | Confirmer la réception et inspecter le produit |
| Responsable SAV | Recevoir les escalades |
| Système | Appliquer les règles, enregistrer les opérations et notifier |
| Assistant IA | Analyser, résumer, proposer et rédiger |

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
| 1 | Demande de retour reçue | Start Event |
| 2 | Saisir la demande | User Task + Form |
| 3 | Récupérer la commande et l’article | REST Service Task |
| 4 | Commande et article trouvés ? | XOR Gateway |
| 5 | Vérifier les informations | Service Task |
| 6 | Demande complète ? | XOR Gateway |
| 7 | Vérifier l’éligibilité | Service Task ou DMN |
| 8 | Analyser la demande avec IA | REST Service Task |
| 9 | Autoriser ou refuser le retour | User Task + Form |
| 10 | Retour autorisé ? | XOR Gateway |
| 11 | Créer le dossier RMA | REST Service Task |
| 12 | Envoyer les instructions | Service Task |
| 13 | Confirmer la réception du produit | User Task + Form |
| 14 | Inspecter le produit | User Task + Form |
| 15 | Valider la résolution finale | User Task + Form |
| 16 | Exécuter la résolution | Sous-processus simulé |
| 17 | Générer la réponse finale | REST Service Task + LLM |
| 18 | Notifier le client | Service Task |
| 19 | Clôturer le dossier | REST Service Task |
| 20 | Dossier terminé | End Event |

### Vue simplifiée

```text
Demande reçue
    ↓
Saisie et recherche de commande
    ↓
Vérification des informations
    ├── Incomplètes → Demander un complément → Vérifier à nouveau
    └── Complètes
          ↓
Contrôle d’éligibilité
          ↓
Analyse IA ou analyse manuelle
          ↓
Validation SAV
    ├── Refus → Notification → Clôture
    └── Autorisation
          ↓
Création RMA et instructions
          ↓
Réception du produit
          ↓
Inspection
          ↓
Validation de la résolution
          ↓
Remboursement / Échange / Réparation / Refus motivé
          ↓
Exécution et vérification du résultat
          ↓
Notification finale
          ↓
Clôture
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

Un délai configurable peut être ajouté pendant l’attente du produit :

- relance du client ;
- examen manuel du dossier ;
- éventuelle clôture motivée.

Pour une démonstration rapide, les durées peuvent être réduites dans une version de test du BPMN.

---

## 9. Réception, inspection et résolution

### Réception

L’agent entrepôt enregistre :

- l’identifiant RMA ;
- la date de réception ;
- la quantité reçue ;
- un commentaire éventuel.

### Inspection

L’agent vérifie :

- la référence du produit ;
- la quantité ;
- l’état constaté ;
- la présence des accessoires ;
- le défaut déclaré ;
- les éventuelles différences avec la demande.

### Résolutions possibles

| Résolution | Traitement simulé |
|------------|-------------------|
| Remboursement | Enregistrement du montant et d’une référence fictive |
| Échange | Création d’une référence de remplacement fictive |
| Réparation | Création d’un dossier de réparation fictif |
| Refus motivé | Enregistrement de la justification et du traitement prévu |

La clôture intervient uniquement après l’enregistrement de la résolution et de la notification finale.

Si l’exécution échoue, le dossier reste ouvert et passe en traitement manuel.

---

## 10. Intelligence artificielle

### Analyse de la demande

Sortie structurée attendue :

```json
{
  "category": "defective_product",
  "summary": "Le client signale un produit qui ne fonctionne plus.",
  "sentiment": "negative",
  "urgency": "normal",
  "missing_information": [],
  "suggested_resolution": "exchange",
  "requires_manual_review": false
}
```

Cette sortie est illustrative et doit correspondre aux schémas réellement implémentés.

### Utilisations prévues

- Classification du motif.
- Résumé de la demande.
- Suggestion de traitement.
- Aide à la rédaction d’un complément.
- Rédaction des instructions.
- Rédaction de la réponse finale.

### Garde-fous

- Validation des sorties avec Pydantic.
- Séparation entre `ai_suggestion` et `agent_decision`.
- Aucune exécution de remboursement sur la seule proposition du LLM.
- Aucun secret transmis au modèle.
- Données de démonstration fictives.
- Fallback manuel en cas d’erreur.
- Message prédéfini si la génération de réponse échoue.

Les recommandations de l’IA restent consultatives.

---

## 11. Formulaires

| Fichier | Utilisation |
|---------|-------------|
| `form-demande-retour.form` | Commande, article, quantité, motif, description |
| `form-complement-information.form` | Corrections et informations manquantes |
| `form-autorisation-sav.form` | Éligibilité, analyse IA, autorisation ou refus |
| `form-reception-produit.form` | Réception et quantité reçue |
| `form-inspection-produit.form` | État, référence, accessoires, défaut |
| `form-resolution-sav.form` | Résolution finale et justification |

Une pièce justificative peut être représentée par une référence fictive. Le stockage réel de fichiers n’est pas nécessaire au périmètre minimal.

---

## 12. Modèle de données

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
├── camunda/
│   ├── returnflow_as_is.bpmn
│   ├── returnflow_to_be.bpmn
│   ├── form-demande-retour.form
│   ├── form-complement-information.form
│   ├── form-autorisation-sav.form
│   ├── form-reception-produit.form
│   ├── form-inspection-produit.form
│   ├── form-resolution-sav.form
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
├── requirements.txt
└── README.md
```

La base SQLite et le fichier `.env` sont créés localement.

---

## 14. Prérequis

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
| 1 | Retour accepté | Autorisation, réception, inspection, résolution et clôture |
| 2 | Retour hors des règles | Refus motivé validé par le SAV |
| 3 | Produit défectueux | Inspection puis échange ou réparation validé |
| 4 | Informations manquantes | Boucle de complément |
| 5 | Commande introuvable | Correction ou traitement manuel |
| 6 | IA indisponible | Analyse manuelle sans blocage définitif |
| 7 | JSON IA invalide | Rejet de la sortie et fallback |
| 8 | SLA dépassé | Relance sans suppression de la tâche |
| 9 | Produit non reçu | Relance puis traitement manuel |
| 10 | Produit reçu non conforme | Inspection et décision motivée |
| 11 | Résolution simulée en échec | Dossier maintenu ouvert |
| 12 | Appel d’exécution répété | Pas de double remboursement simulé |

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
7. Valider l’autorisation dans Tasklist.
8. Simuler la réception.
9. Compléter l’inspection.
10. Valider et exécuter la résolution simulée.
11. Montrer la notification et la clôture.
12. Illustrer un fallback ou une escalade.

### Message de conclusion

> BPMN orchestre, les règles encadrent, l’IA assiste, l’humain décide et le Process Mining mesure.

---

## 22. Plan de réalisation

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
- [ ] Répéter la démonstration.

---

## 23. Répartition du travail

| Membre | Responsabilités principales |
|--------|-----------------------------|
| Israe Yaaya | BPMN, formulaires, Process Mining, documentation métier |
| Mohamed | FastAPI, LLM, SQLite, règles, gestion des erreurs |

### Travail commun

- Architecture.
- Contrats API.
- Intégration Camunda ↔ FastAPI.
- Variables et mappings.
- Tests.
- Scénarios de démonstration.
- Présentation finale.

Chaque membre doit pouvoir expliquer le fonctionnement global du système.

---

## 24. Sécurité et Git

- Ne jamais versionner les secrets.
- Versionner `.env.example`, sans clé réelle.
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
