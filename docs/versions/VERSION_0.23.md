# Version 0.23

Cette version ajoute le module de calpinage toiture dans l'interface navigateur.

Changements principaux :

- ajout des champs `Longueur brute toiture`, `Largeur brute rampant`, `Modules a calpiner` et `Entraxe chevrons` ;
- calcul de la toiture nette avec `30 cm` de marge laterale de chaque cote, `30 cm` cote egout et `10 cm` cote faitage ;
- comparaison automatique des poses `Portrait` et `Paysage` selon les dimensions du panneau retenu ;
- prise en compte de `2 cm` de clame entre panneaux ;
- calcul du nombre de rangees, de rails avec `2 rails` par rangee, des metres lineaires de rails et du nombre total de crochets ;
- calcul des crochets avec un pas maximum de `90 cm` pour entraxe chevrons `45 cm`, ou `1,20 m` pour entraxe `60 cm` ;
- ajout du calpinage dans le detail de configuration, la metrique de synthese, l'email de debug et la note de calcul.