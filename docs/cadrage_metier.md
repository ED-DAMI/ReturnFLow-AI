# ReturnFlow AI — cadrage métier

**Version :** 1.0 — retours de vêtements, cas académique SHEIN Maroc
**Références :** [BPMN AS-IS](../camunda/returnflow_as_is.bpmn), [BPMN TO-BE](../camunda/returnflow_to_be.bpmn), [README](../README.md)

## 1. Finalité et limites

ReturnFlow AI compare un processus manuel de référence avec un processus cible assisté par un worker automatisé, un RAG et un LLM. Le cas est inspiré des politiques publiques de retour SHEIN Maroc. Il ne représente pas le processus interne de SHEIN et n’utilise aucune donnée opérationnelle interne. Les cas, décisions, identifiants, délais et remboursements de démonstration sont simulés.

Le BPMN TO-BE décrit le comportement visé. Les Service Tasks portent le type de job `shein-agent` et un en-tête `operation`. Le worker Python `backend/zeebe_worker.py` consomme ces jobs et délègue les 14 opérations à `backend/returnflow_core.py`. Les systèmes de commandes, notifications externes et paiement ne sont pas reliés; ces actions restent simulées ou nécessitent des données fournies par un adaptateur amont.

## 2. Processus AS-IS et TO-BE

### AS-IS

Le processus de référence comprend la lecture de la demande, la recherche manuelle de commande, la vérification des données et des règles, l’échange éventuel avec le client, la décision d’autorisation, l’envoi des instructions, la réception et l’inspection du produit, la résolution, la notification et la clôture. Il ne comporte aucune tâche IA ni automatisation. Les exceptions non représentées ne sont pas ajoutées artificiellement au journal AS-IS.

### TO-BE

Le client soumet une demande. `shein-agent` retrouve commande et article, vérifie la complétude puis demande un complément si nécessaire. Un timer interruptif de 48 heures est attaché à la tâche qui attend ce complément; à expiration, le client est notifié de la clôture.

Pour une demande complète, `shein-agent` analyse le motif, récupère les règles via le RAG et extrait les faits utiles. Une indisponibilité du LLM ou un contexte RAG insuffisant dirige le dossier vers l’analyse humaine de repli. Les règles déterministes évaluent l’éligibilité; le LLM ne prend pas cette décision seul. Un refus est expliqué et notifié.

Pour un dossier éligible, l’agent SAV vérifie les faits et confirme l’éligibilité, puis décide si le produit doit être retourné physiquement. Un timer non interruptif de 24 heures crée une tâche d’escalade vers le superviseur sans interrompre la validation. Si un retour est requis, le dossier attend la confirmation de réception de l’entrepôt, puis l’article est inspecté. Une inspection non conforme mène à une réévaluation humaine. Le modèle ne fixe pas de délai de réception du produit.

La résolution intervient après la validation et l’inspection éventuelle. Elle choisit le portefeuille SHEIN, le moyen de paiement initial, le remboursement sans retour physique si `returnRequired = false`, ou le traitement manuel en cas d’exception. Les opérations financières sont simulées. Le client est ensuite notifié et le dossier clôturé.

## 3. Acteurs et responsabilités

| Acteur | Responsabilité dans le modèle |
|---|---|
| Client | Soumettre la demande et fournir les compléments requis. |
| `shein-agent` | Worker Camunda 8 qui exécute les opérations automatisées du BPMN et conserve les validations humaines. |
| Agent SAV | Analyse humaine de repli, validation des faits et de l’éligibilité, choix du besoin de retour, traitement des exceptions et confirmation de la résolution. |
| Entrepôt | Enregistrer la réception et inspecter l’article retourné. |
| Responsable SAV | Traiter l’escalade créée après le délai de validation de 24 heures. |

Le worker RAG utilise uniquement le PDF `rag_documents/Synthese_Politique_de_Retour_SHEIN_Maroc.pdf`. `intfloat/multilingual-e5-small` calcule localement les embeddings des passages et des questions; PostgreSQL/pgvector stocke les passages et leurs vecteurs. Le chat Groq classe les demandes et rédige les réponses; il ne décide pas seul de l’éligibilité. Ces composants sont des détails d’implémentation, ni des tâches ni des acteurs BPMN. L’ingestion et le filtrage à source unique sont décrits dans [`embeddings/README.md`](../embeddings/README.md).

## 4. Variables et décisions

Le worker lit les variables visibles du processus et écrit les résultats attendus par le modèle. Il conserve les références et scores des extraits RAG avec la décision. L’adaptateur de commande reste externe: sans `orderFound` et données d’une intégration amont, le worker ne prétend pas consulter les systèmes SHEIN.

| Domaine | Variables représentatives |
|---|---|
| Commande et article | `order_id`, `order_item_id`, `product_id`, `product_name`, `ordered_quantity`, `purchase_date`, `delivery_date`, `unit_price` |
| Demande | `return_id`, `return_quantity`, `return_reason`, `description`, `requested_resolution` |
| Analyse et règles | `category`, `aiAvailable`, `policyChunks`, `sourceIds`, `ragContextFound`, `eligibility`, `eligibility_reason`, `agent_decision` |
| Retour physique | `returnRequired`, `received_at`, `inspection_result`, `inspection_differences` |
| Résolution | `refundMethod`, `resolution_status`, `closed_at` |

| Décision | Comportement retenu |
|---|---|
| Commande/article introuvable | Demander une correction; sans correction, notifier et clôturer. |
| Informations incomplètes | Demander un complément; clôturer après 48 h sans réponse. |
| LLM indisponible ou RAG insuffisant | Passer par une analyse humaine avant l’application des règles. |
| Éligibilité | Appliquer des règles déterministes aux faits et politiques, en conservant les sources. |
| Validation SAV | Confirmer l’éligibilité et le besoin de retour physique; choisir le remboursement séparément. |
| SLA SAV | Après 24 h, créer le suivi du superviseur sans interrompre la validation. |
| Réception produit | Attendre la confirmation de l’entrepôt; aucun délai de livraison n’est imposé. |
| Inspection non conforme | Faire réévaluer le dossier par l’agent SAV avant la résolution. |
| Résolution | Portefeuille, moyen initial, retourless si aucun retour physique n’est requis, ou exception manuelle. Aucun transfert d’argent n’est exécuté. |
| Incident technique Camunda | Après épuisement des retries, reprendre l’incident comme problème d’exécution; ne pas le confondre avec une décision métier. |

Toute règle citée dans le rapport doit rester liée à une source identifiable et à la version consultée dans le corpus documentaire.

## 5. Formulaires et cohérence du flux

Chaque formulaire est rattaché à une tâche par son `formId`. Les formulaires de validation SAV et de résolution sont distincts : le premier confirme l’éligibilité et le besoin de retour physique; le second choisit le moyen de remboursement ou l’exception après inspection éventuelle. Le chemin `returnless` exige `returnRequired = false`; les choix incompatibles aboutissent au traitement manuel par défaut.

Les activités des journaux utilisent les noms exacts des tâches du BPMN correspondant. Les événements de passerelle, début, fin et timers ne sont pas enregistrés comme activités terminées. Les traces expirant sur le timer de complément se terminent par « Demander un complément au client » puis « Notifier la clôture - complément non reçu »; elles ne déclarent pas le complément comme reçu.

## 6. Scénarios de démonstration

Les traces couvrent des cas acceptés ou refusés, complément reçu, correction de références, références introuvables, complément expiré, fallback LLM, fallback RAG, escalade après 24 heures, remboursement sans retour physique, inspection non conforme et résolution manuelle. Les 200 cas communs AS-IS/TO-BE forment la cohorte appariée. Les 180 cas additionnels n’existent que dans le TO-BE et exercent ses branches particulières; ils restent exclus de la comparaison des durées.

La méthode et ses limites sont détaillées dans [logs/README.md](../logs/README.md) et [process_mining_plan.md](../logs/04_process_mining/process_mining_plan.md).
