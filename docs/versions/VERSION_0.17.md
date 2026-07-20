# Version 0.17

Date : 2026-06-10

Cette version ameliore l'UX de l'interface navigateur :

- ajout dynamique des toitures avec un bouton `+ Toiture`, jusqu'a 8 zones de toiture ;
- ajout dynamique des emplacements onduleurs avec un bouton `+ Onduleur` ;
- conservation des limites reseau : maximum 2 emplacements en mono/biphase, maximum 3 en tri delta/tetra ;
- proposition automatique de l'affectation des strings sur les sorties MPP ;
- modification manuelle possible de l'affectation MPP, string par string, avec recalcul et validations ;
- affichage de l'affectation MPP dans le detail, le CSV et la note de calcul.

Le bouton `+ Onduleur` ajoute un emplacement autorise. Le moteur garde ensuite la logique d'optimisation : il peut choisir le meilleur nombre d'onduleurs jusqu'a cette limite.
