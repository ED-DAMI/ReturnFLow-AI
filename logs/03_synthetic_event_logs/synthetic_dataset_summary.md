# Synthèse du jeu synthétique

Les journaux de processus sont générés par `generate_synthetic_logs.py` avec la graine fixe `42`.

- **Cohorte appariée :** 200 cas communs à l’AS-IS et au TO-BE, avec les mêmes scénarios et issues métier.
- **Extensions TO-BE :** 180 cas couvrant neuf scénarios propres au modèle cible.
- **Provenance :** cas, identifiants, activités, ressources, décisions et horodatages simulés; aucune donnée client ou opérationnelle interne de SHEIN.
- **Interprétation :** les durées sont des hypothèses pédagogiques et ne mesurent pas la performance réelle de SHEIN.

À chaque génération, le script remplace cette synthèse par les volumes d’événements et les durées observées dans les fichiers produits. Pour la méthode et les commandes, voir [logs/README.md](../README.md).
