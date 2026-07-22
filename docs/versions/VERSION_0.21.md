# Version 0.21

Cette version ajoute un indicateur de proximite entre la tension de fonctionnement DC des strings et la tension nominale d'entree de l'onduleur.

Changements principaux :

- ajout du champ `tension_dc_nominale_v` dans le catalogue onduleurs CSV/JSON ;
- extraction automatique de `Rated input voltage` dans les datasheets onduleurs, notamment Huawei SUN2000 MAP0 ;
- affichage d'une colonne `Ecart rated` dans le tableau des configurations valides ;
- ajout de `Umpp STC`, tension nominale onduleur et ecart signe dans l'export CSV et la note de calcul ;
- conservation du comportement de validation : cet ecart est un repere qualitatif, pas une condition de rejet.
