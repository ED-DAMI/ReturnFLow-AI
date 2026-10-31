# ReturnFlow AI — cadrage métier

**Version :** 0.3 — étude de cas vêtements SHEIN Maroc  
**Base de travail :** nouveau BPMN TO-BE académique et README

Ce document résume le cas d’étude académique inspiré des politiques publiques de retour SHEIN Maroc. Il ne reproduit pas le processus interne réel de SHEIN et n’utilise aucune donnée interne. Les fonctions restent à implémenter et à valider.

## 1. Problématique et objectif

Le cas cible porte sur les retours de vêtements et les motifs liés à la taille, la couleur, au tissu, à la coupe, aux défauts, au mauvais article et à la non-conformité à la description. Le processus TO-BE retrouve la commande, vérifie les informations, consulte les politiques via RAG, extrait des faits, applique les règles déterministes, puis conserve la validation humaine.

Le principe retenu est : le RAG retrouve les sources, le LLM comprend et extrait des faits, les règles/DMN évaluent l'éligibilité, l'agent SAV valide la suite et Camunda orchestre. La proposition avant retour physique est distincte du choix de remboursement après inspection.

## 2. Périmètre du processus AS-IS

Le BPMN AS-IS partagé couvre le traitement manuel suivant :

1. Recevoir et lire la demande.
2. Rechercher la commande.
3. Vérifier les informations et les règles.
4. Demander un complément au client et reprendre la vérification si nécessaire.
5. Autoriser ou refuser le retour; enregistrer et notifier un refus.
6. Envoyer les instructions, recevoir le produit et l'inspecter.
7. Décider puis exécuter la résolution finale.
8. Notifier le client et clôturer le dossier.

L'AS-IS est le processus manuel de référence et ne comprend ni IA ni automatisation Camunda. Le TO-BE de l'étude inclut LLM, RAG PostgreSQL/pgvector, analyse manuelle de repli, règles/DMN, escalade SLA et remboursements simulés.

## 3. Acteurs

| Acteur | Responsabilité décrite |
|---|---|
| Client | Soumettre la demande, fournir les compléments et retourner le produit. |
| Agent SAV | Valider la proposition après contrôle d'éligibilité et confirmer le traitement après inspection. |
| Agent entrepôt | Confirmer la réception et inspecter le produit. |
| Responsable SAV | Recevoir les escalades, notamment en cas de dépassement du SLA prévu. |
| Système | Appliquer les règles, enregistrer les opérations et notifier dans le TO-BE. |
| Assistant IA | Classifier, résumer, proposer et rédiger dans le TO-BE; l'agent garde la décision métier. |

## 4. Données métier de référence

Les noms ci-dessous reprennent le modèle de données prévu dans le README. Ils ne signifient pas que la base ou les API sont déjà implémentées.

| Entité | Champs principaux |
|---|---|
| Commande et article | `order_id`, `order_item_id`, `product_id`, `product_name`, `ordered_quantity`, `purchase_date`, `delivery_date`, `unit_price` |
| Dossier de retour | `return_id`, `order_id`, `order_item_id`, `return_quantity`, `return_reason`, `requested_resolution`, `eligibility_status`, `authorization_status`, `ai_status`, `ai_suggestion`, `agent_decision`, `received_at`, `inspection_result`, `final_resolution`, `resolution_status`, `closed_at` |

Les exemples et journaux de démonstration doivent utiliser des données synthétiques ou anonymisées. Pour Process Mining, chaque événement doit pouvoir être rattaché à un `return_id` et comporter au minimum une activité, un horodatage et un résultat.

## 5. Règles et décisions à valider

| Sujet | Règle de travail du nouveau BPMN | À confirmer |
|---|---|---|
| Complétude | Demander un complément; fermer le dossier après 48 h sans réponse. | Le délai est un paramètre de démonstration à confirmer. |
| Éligibilité vêtements | Le modèle s'appuie sur une fenêtre publique de 30 jours après réception et sur l'état neuf, non porté, non lavé, non endommagé, non modifié et les étiquettes d'origine. | Vérifier les exceptions et la version de la politique publique avant de figer les règles. |
| Catégories | Certaines catégories sont exclues; les articles signalés défectueux ou endommagés suivent un chemin SAV. | Maintenir la liste des catégories exclues et des délais propres aux défauts avec leurs sources. |
| RAG et LLM | Le RAG fournit les extraits/sources; le LLM classe et extrait les faits; le LLM ne décide pas l'éligibilité. | Seuil de pertinence RAG, formats de sortie et gestion des faits incertains. |
| Validation humaine | L'agent valide la proposition et choisit si un retour physique est requis. | Distinguer les motifs de remboursement sans retour des exceptions. |
| Inspection et résolution | Après réception, un contrôle qualité peut déclencher une réévaluation; le traitement financier est simulé. | Définir les suites exactes en cas de non-conformité. |
| Délais | Un SLA de 24 h déclenche une escalade non interruptive pendant la validation SAV. | Durée et destinataire de l'attente du produit. |

Les règles SHEIN sont traitées comme des règles publiques de référence pour le cas académique, pas comme une reproduction du processus interne. Conserver avec chaque règle les identifiants et extraits de source récupérés par le RAG.

## 6. Scénarios de démonstration

Le nouveau BPMN couvre notamment : retour éligible ou hors règles, commande introuvable avec correction, demande incomplète avec délai de 48 h, indisponibilité IA, contexte RAG insuffisant, dépassement du SLA de 24 h, retour physique requis ou non, inspection conforme ou non conforme, mode de remboursement standard et exception SAV manuelle.

Pour la modélisation AS-IS, les cas principaux à vérifier sont la demande complète, le complément d'information, le refus, la réception et inspection, puis la décision et la clôture. Les cas IA, SLA automatisé, idempotence et échec de service relèvent du TO-BE.

## 7. Écart de modélisation à suivre

Le README prévoit le cas « commande ou article introuvable » dans le TO-BE. Le BPMN AS-IS partagé enchaîne la recherche de commande avec la vérification, sans passerelle dédiée indiquant si la commande existe. Confirmer avec l'équipe si ce cas doit être ajouté au diagramme AS-IS ou rester documenté uniquement comme exception cible.

## 8. Références de travail

- `README.md` — périmètre, processus et scénarios de démonstration.
- `camunda/returnflow_as_is.bpmn` — processus manuel AS-IS.
- `camunda/returnflow_to_be.bpmn` — processus cible TO-BE.
- `camunda/*.form` — formulaires prévus pour les étapes du processus cible.
