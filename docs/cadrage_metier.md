# ReturnFlow AI — cadrage métier

**Version :** 0.2 — document de travail J1  
**Base de travail :** README et modèles BPMN partagés sur `main` au 31 octobre 2026

Ce document résume le périmètre métier retenu pour le démarrage. Les règles qui ne figurent pas dans les documents partagés sont signalées comme hypothèses à valider. Le README décrit un périmètre cible prévu : les fonctions restent à implémenter et à valider.

## 1. Problématique et objectif

Le traitement d'un retour nécessite de retrouver la commande, vérifier les informations et les règles applicables, communiquer avec le client, puis décider et exécuter une résolution. Le projet part du processus manuel AS-IS et prévoit un processus cible TO-BE orchestré par Camunda, complété par l'analyse Process Mining et une assistance IA.

Le principe métier retenu est que les règles déterminent l'éligibilité, l'IA peut analyser et recommander, et l'agent SAV valide les décisions. L'autorisation d'expédier un retour est distincte de la décision finale prise après réception et inspection du produit.

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

L'AS-IS ne comprend pas de classification ou recommandation IA ni d'automatisation Camunda. Le README décrit le TO-BE prévu, dont le contrôle d'éligibilité, l'assistance IA avec repli manuel, le RMA, l'escalade SAV et l'exécution simulée d'un remboursement, échange ou réparation.

## 3. Acteurs

| Acteur | Responsabilité décrite |
|---|---|
| Client | Soumettre la demande, fournir les compléments et retourner le produit. |
| Agent SAV | Autoriser ou refuser le retour et valider la résolution finale. |
| Agent entrepôt | Confirmer la réception et inspecter le produit. |
| Responsable SAV | Recevoir les escalades, notamment en cas de dépassement du SLA prévu. |
| Système | Appliquer les règles, enregistrer les opérations et notifier dans le TO-BE. |
| Assistant IA | Analyser, résumer, proposer et rédiger dans le TO-BE; l'agent garde la décision métier. |

## 4. Données métier de référence

Les noms ci-dessous reprennent le modèle de données prévu dans le README. Ils ne signifient pas que la base ou les API sont déjà implémentées.

| Entité | Champs principaux |
|---|---|
| Commande et article | `order_id`, `order_item_id`, `product_id`, `product_name`, `ordered_quantity`, `purchase_date`, `delivery_date`, `unit_price` |
| Dossier de retour | `return_id`, `order_id`, `order_item_id`, `return_quantity`, `return_reason`, `requested_resolution`, `eligibility_status`, `authorization_status`, `ai_status`, `ai_suggestion`, `agent_decision`, `received_at`, `inspection_result`, `final_resolution`, `resolution_status`, `closed_at` |

Les exemples et journaux de démonstration doivent utiliser des données synthétiques ou anonymisées. Pour Process Mining, chaque événement doit pouvoir être rattaché à un `return_id` et comporter au minimum une activité, un horodatage et un résultat.

## 5. Règles et décisions à valider

| Sujet | Ce qui est établi dans le README partagé | À confirmer |
|---|---|---|
| Complétude | Une demande incomplète peut suivre une boucle de demande de complément. | Champs obligatoires et durée maximale d'attente. |
| Recherche de commande | La commande et l'article doivent être recherchés; le TO-BE prévoit un cas introuvable. | Correction/réessai ou clôture, et représentation de cette décision dans l'AS-IS. |
| Éligibilité | Un contrôle d'éligibilité est prévu avant l'autorisation SAV. | Critères et délais commerciaux précis. |
| Autorisation | L'agent SAV autorise ou refuse le retour avant expédition. | Motifs et règles exactes d'autorisation/refus. |
| Résolution finale | Après réception et inspection, l'agent valide la résolution; les options simulées sont remboursement, échange ou réparation. | Conditions par motif, produit et résultat d'inspection. |
| IA et décision | L'IA assiste; l'agent valide les décisions métier. Un fallback manuel est prévu si l'IA est indisponible. | Contenu des recommandations et contrôles de sortie. |
| Délais | Un SLA de 24 heures avec relance non interruptive et information du responsable SAV est prévu pour la validation. | Délai d'attente du produit et durée utilisée pour les démonstrations. |

La règle « retour classique dans les 30 jours » et l'exception liée à une garantie active figuraient dans une première ébauche locale, mais ne sont pas confirmées par le README ou les BPMN partagés. Elles restent donc des propositions à valider et ne doivent pas être codées comme règles acquises.

## 6. Scénarios de démonstration

Le README partagé recense 12 scénarios TO-BE : retour accepté, retour hors règles, produit défectueux, informations manquantes, commande introuvable, IA indisponible, JSON IA invalide, SLA dépassé, produit non reçu, produit reçu non conforme, échec de résolution simulée et appel d'exécution répété sans double remboursement.

Pour la modélisation AS-IS, les cas principaux à vérifier sont la demande complète, le complément d'information, le refus, la réception et inspection, puis la décision et la clôture. Les cas IA, SLA automatisé, idempotence et échec de service relèvent du TO-BE.

## 7. Écart de modélisation à suivre

Le README prévoit le cas « commande ou article introuvable » dans le TO-BE. Le BPMN AS-IS partagé enchaîne la recherche de commande avec la vérification, sans passerelle dédiée indiquant si la commande existe. Confirmer avec l'équipe si ce cas doit être ajouté au diagramme AS-IS ou rester documenté uniquement comme exception cible.

## 8. Références de travail

- `README.md` — périmètre, processus et scénarios de démonstration.
- `camunda/returnflow_as_is.bpmn` — processus manuel AS-IS.
- `camunda/returnflow_to_be.bpmn` — processus cible TO-BE.
- `camunda/*.form` — formulaires prévus pour les étapes du processus cible.
