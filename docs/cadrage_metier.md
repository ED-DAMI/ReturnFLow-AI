# ReturnFlow AI — cadrage métier

**Version :** 0.4 — worker `shein-agent` et étude de cas vêtements SHEIN Maroc

**Base de travail :** nouveau BPMN TO-BE académique et README

Ce document résume le cas d’étude académique inspiré des politiques publiques de retour SHEIN Maroc. Il ne reproduit pas le processus interne réel de SHEIN et n’utilise aucune donnée interne. Les fonctions restent à implémenter et à valider.

## 1. Problématique et objectif

Le cas cible porte sur les retours de vêtements et les motifs liés à la taille, la couleur, au tissu, à la coupe, aux défauts, au mauvais article et à la non-conformité à la description. Le processus TO-BE retrouve la commande, vérifie les informations, consulte les politiques via RAG, extrait des faits, applique les règles déterministes, puis conserve la validation humaine.

Le BPMN route les 14 tâches automatisées vers le worker Camunda `shein-agent`; l'en-tête `operation` précise le traitement. Le worker doit assurer la recherche de commande, le RAG, l'analyse, l'évaluation déterministe, les messages, les notifications et les résolutions simulées. L'agent SAV humain garde les validations métier. La proposition avant retour physique est distincte du choix de résolution après inspection.

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

L'AS-IS est le processus manuel de référence et ne comprend ni IA ni automatisation Camunda. Le TO-BE inclut le worker `shein-agent` (à implémenter), le RAG, le LLM, l'analyse manuelle de repli, les règles/DMN, l'escalade SLA et les remboursements simulés. Le BPMN ne modélise pas de base PostgreSQL/pgvector.

## 3. Acteurs

| Acteur | Responsabilité décrite |
|---|---|
| Client | Soumettre la demande, fournir les compléments et retourner le produit. |
| Agent SAV | Valider la proposition après contrôle d'éligibilité et confirmer le traitement après inspection. |
| Agent entrepôt | Confirmer la réception et inspecter le produit. |
| Responsable SAV | Recevoir les escalades, notamment en cas de dépassement du SLA prévu. |
| `shein-agent` (worker) | Exécuter les Service Tasks automatisées selon l'en-tête `operation`; worker planifié, non encore implémenté. |

## 4. Variables métier de référence

Les noms ci-dessous sont des variables de processus prévues pour Camunda et le worker `shein-agent`. Ils ne supposent ni base de données ni API déjà implémentée.

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
| RAG et LLM | `shein-agent` récupère les extraits/sources, puis le LLM classe et extrait les faits; l'éligibilité reste évaluée par les règles/DMN. | Seuil de pertinence RAG, formats de sortie et gestion des faits incertains. |
| Validation humaine | L'agent SAV humain valide la proposition et choisit si un retour physique est requis. | Distinguer les motifs de remboursement sans retour des exceptions. |
| Inspection et résolution | Après réception, un contrôle qualité peut déclencher une réévaluation; le traitement financier est simulé. | Définir les suites exactes en cas de non-conformité. |
| Délais | Un SLA de 24 h déclenche une escalade non interruptive pendant la validation SAV. | Durée et destinataire de l'attente du produit. |

Les règles SHEIN sont traitées comme des règles publiques de référence pour le cas académique, pas comme une reproduction du processus interne. Conserver avec chaque règle les identifiants et extraits de source récupérés par le RAG. Les valeurs distinctes de l'en-tête `operation` sont documentées dans le README.

## 6. Scénarios de démonstration

Le nouveau BPMN route ses tâches automatiques vers `shein-agent` et couvre notamment : retour éligible ou hors règles, commande introuvable avec correction, demande incomplète avec délai de 48 h, indisponibilité IA, contexte RAG insuffisant, dépassement du SLA de 24 h, retour physique requis ou non, inspection conforme ou non conforme, mode de remboursement standard et exception SAV manuelle.

Pour la modélisation AS-IS, les cas principaux à vérifier sont la demande complète, le complément d'information, le refus, la réception et inspection, puis la décision et la clôture. Les cas IA, SLA automatisé, idempotence et échec de service relèvent du TO-BE.

## 7. Écart de modélisation à suivre

Le README prévoit le cas « commande ou article introuvable » dans le TO-BE. Le BPMN AS-IS partagé enchaîne la recherche de commande avec la vérification, sans passerelle dédiée indiquant si la commande existe. Confirmer avec l'équipe si ce cas doit être ajouté au diagramme AS-IS ou rester documenté uniquement comme exception cible.

## 8. Références de travail

- `README.md` — périmètre, processus et scénarios de démonstration.
- `camunda/returnflow_as_is.bpmn` — processus manuel AS-IS.
- `camunda/returnflow_to_be.bpmn` — processus cible TO-BE.
- `camunda/*.form` — formulaires prévus pour les étapes du processus cible.
