# ReturnFlow AI - Corpus RAG

Ce corpus rassemble les sources de reference publiques, les guides mode, les fiches produits et les regles academiques du projet.

## Provenance et usage

- Les fichiers marques official_user_supplied proviennent des documents fournis par l'utilisateur.
- Les fichiers public_source_normalized sont des syntheses ou des fiches basees sur des pages publiques indiquees dans sources.csv.
- Les fichiers academic_simulated definissent des regles et exemples propres au projet; ne jamais les presenter comme des politiques internes SHEIN ni comme des politiques officielles.
- manifest.csv est la liste de reference des documents a indexer; metadata.json en fournit une representation structuree. Respecter source_type, language, country et use_for_rag.
- Les trois PDF a la racine sont des copies exactes des versions classees dans 01_sources_officielles; ils ne sont pas des entrees distinctes du manifeste et ne doivent pas etre indexes une seconde fois.

## Ingestion par shein-agent

1. Extraire le texte des PDF et conserver les identifiants de source.
2. Decouper par section (environ 500-900 tokens, chevauchement 80-120) sans separer les conditions d'une meme regle.
3. Indexer les passages avec le composant de recherche choisi lors de l'implementation du worker. Le corpus ne prescrit pas de base de donnees ni de moteur de stockage.
4. Conserver les metadonnees du manifeste avec chaque passage et retourner les identifiants de source avec les reponses RAG.
5. Pour les questions sur la politique publique, privilegier les sources officielles ou normalisees et distinguer explicitement toute regle academique du projet.

Dans le BPMN TO-BE, l'operation retrieve-return-policy-rag est une des operations du worker shein-agent. Le worker reste a implementer.
