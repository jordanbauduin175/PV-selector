# Version 0.16

Date de tag : 2026-06-10

Base : version 0.15

Ajout principal :

- passage de l'interface navigateur `dimensionnement_solaire.html` en badge `v0.16` ;
- ajout de 3 blocs toiture avec surface, orientation et pente propres ;
- allocation des modules par toiture en priorite sur le meilleur coefficient d'exposition ;
- coefficient de production pondere selon les modules poses sur chaque toiture ;
- ajout du choix `Onduleurs max` ;
- exploration de 1 a 2 onduleurs en mono/biphase et de 1 a 3 onduleurs en tri delta/tetra ;
- conservation des limites unitaires : `5 kVA` par onduleur mono/biphase et `10 kVA` par onduleur tri/tetra ;
- adaptation des pertes AC : cables onduleur-TD comptes par onduleur, TD-compteur calcule avec le courant total ;
- export CSV et note de calcul enrichis avec nombre d'onduleurs, puissance AC totale et allocation toiture.
