# ReturnFlow AI - cadrage métier

**Version :** 0.1 - document de travail
**Périmètre actuel :** J1, cadrage métier et processus AS-IS

Les règles ci-dessous sont des hypothèses de simulation. Elles doivent être confirmées par l'équipe avant d'être considérées comme la politique métier du projet.

## 1. Problématique

Le traitement d'une demande de retour peut varier selon l'agent et prendre du temps. L'agent doit retrouver la commande, comprendre le motif, vérifier les conditions applicables, choisir une solution et informer le client.

Le projet modélise d'abord le traitement manuel actuel (AS-IS), puis pourra comparer ce fonctionnement à un processus cible (TO-BE) assisté par workflow, analyse de processus et IA.

## 2. Périmètre J1

Le processus commence à la réception d'une demande de retour. Il couvre l'enregistrement du dossier, la vérification des informations et de la commande, l'examen manuel de l'éligibilité, le choix et la validation d'une solution, puis l'information du client.

Le BPMN AS-IS décrit les tâches manuelles. Il n'intègre ni classification IA, ni recommandation automatique, ni intégration technique à Camunda ou au backend.

## 3. Acteurs

| Acteur | Rôle dans le processus |
|---|---|
| Client | Soumet la demande, fournit les informations manquantes et reçoit la réponse. |
| Agent SAV | Enregistre et vérifie le dossier, applique la politique, choisit et valide la solution. |
| Système de commandes | Source consultée par l'agent pour retrouver la commande. Dans l'AS-IS, la consultation est manuelle. |
| Camunda, backend et service IA | Composants envisagés pour le TO-BE; ils ne sont pas représentés comme acteurs exécutants dans l'AS-IS. |

## 4. Données du dossier

| Donnée | Usage |
|---|---|
| `returnId` | Identifiant du dossier et futur identifiant de cas Process Mining. |
| `orderId` | Recherche de la commande. |
| `clientName` | Identification dans les échanges; utiliser une valeur fictive dans les exemples. |
| `productName` | Produit concerné par le retour. |
| `purchaseDate` | Vérification de la période de retour proposée. |
| `reason` | Motif communiqué par le client. |
| `productCondition` | État déclaré du produit. |
| `desiredSolution` | Solution souhaitée par le client. |
| `warrantyActive` | Indicateur à confirmer pour les cas de produit défectueux. |
| `eligibility` | Résultat de la vérification manuelle. |
| `agentDecision` | Décision validée par l'agent. |
| `finalResponse` | Réponse communiquée au client. |

Pour un futur journal Process Mining, prévoir au minimum un identifiant de cas, l'activité, les dates/horaires de début et de fin, la ressource (ou un identifiant pseudonymisé) et le résultat. N'utiliser que des données synthétiques ou anonymisées.

Les champs `category`, `sentiment`, `urgency` et `aiRecommendation` sont des pistes TO-BE et ne sont pas requis pour l'AS-IS.

## 5. Règles métier proposées

| ID | Règle de travail | Effet dans l'AS-IS |
|---|---|---|
| R1 | Le dossier doit contenir au minimum `orderId`, `reason`, `productCondition` et `desiredSolution`. | Si une donnée manque, l'agent demande un complément et reprend l'examen après réception. |
| R2 | La commande doit exister dans le système de commandes. | Sinon, l'agent informe le client et clôt le dossier. |
| R3 | Proposition à confirmer : un retour classique est éligible si la demande intervient au plus 30 jours calendaires après l'achat. | L'agent vérifie manuellement la date. |
| R4 | Proposition à confirmer : un produit défectueux avec garantie active peut être orienté vers une réparation ou un échange, même hors du délai classique. | L'agent vérifie le défaut et la garantie; il choisit ensuite la solution autorisée. |
| R5 | L'agent SAV prend et valide la décision finale. | La décision est humaine dans l'AS-IS; dans le TO-BE, l'IA pourra seulement recommander ou rédiger. |
| R6 | Les résultats possibles sont remboursement, échange, réparation ou refus. | L'agent informe le client de la décision et de la suite à donner. |

Les durées, les justificatifs requis et les conditions exactes de remboursement, d'échange ou de réparation restent à confirmer. Les passerelles du BPMN portent donc des questions métier génériques plutôt que des expressions exécutables.

## 6. Scénarios à couvrir

1. **Retour classique accepté :** commande trouvée, dossier complet, critères satisfaits, solution validée par l'agent.
2. **Produit défectueux sous garantie :** l'agent vérifie le défaut et la garantie, puis examine une réparation ou un échange.
3. **Retour hors délai classique :** l'agent refuse selon la règle de délai proposée, sauf exception confirmée.
4. **Commande introuvable :** le client est informé et le dossier est clôturé.
5. **Informations manquantes :** l'agent sollicite le client, reçoit son complément et poursuit l'analyse.
6. **Traitement agent en retard :** le dossier reste en attente; le délai est à mesurer dans les données. Le BPMN AS-IS ne déclenche pas d'escalade automatique.

**Cas TO-BE distinct :** indisponibilité du service IA. Le processus cible devra prévoir un retour au traitement manuel; ce cas n'apparaît pas dans le BPMN AS-IS.

## 7. Points à valider avec l'équipe

- Le délai classique est-il bien de 30 jours, et se calcule-t-il depuis l'achat, la livraison ou la réception du produit ?
- Quelles preuves déterminent qu'un produit est défectueux et que sa garantie est active ?
- Un dossier incomplet reste-t-il ouvert sans limite, ou expire-t-il après une durée définie ?
- Quelles solutions sont autorisées pour chaque catégorie de produit et de motif ?
- À quel événement le processus se termine-t-il : décision, expédition du produit retourné ou réception du remboursement/de l'échange ?
- Quel délai agent/SLA veut-on mesurer et quelle règle d'escalade sera définie pour le TO-BE ?
