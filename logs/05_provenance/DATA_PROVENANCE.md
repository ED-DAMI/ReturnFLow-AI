# Provenance et rigueur scientifique

## Ce qui est reel

- Les schemas et champs des APIs proviennent de la documentation publique SHEIN.
- Les mappings de statuts reproduisent la semantique publiee par la plateforme SHEIN Developer.
- Les liens de datasets produits/reviews pointent vers des sources publiques tierces ou academiques.

## Ce qui est synthetique

- `shein_returns_event_log_synthetic_200.csv`
- `case_summary_synthetic_200.csv`

Ces deux fichiers ont ete generes pour ReturnFlow AI. Ils ne contiennent aucune donnee client SHEIN reelle et ne doivent jamais etre presentes comme des logs internes de l'entreprise.

## Formulation recommandee en soutenance

"Les journaux operationnels internes de SHEIN n'etant pas publics, nous avons construit un event log synthetique structure a partir des schemas, statuts et timestamps exposes par les API officielles SHEIN, puis enrichi avec des motifs de retour fashion adaptes a notre cas d'etude."
