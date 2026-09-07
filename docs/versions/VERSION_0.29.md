# Version 0.29

Date : 2026-09-07

## Ajouts

- Calpinage toiture par toiture quand le mode `Manuel par toiture` est actif.
- Champs de longueur et largeur brutes propres a chaque toiture dans les controles manuels.
- Totaux multi-toitures pour panneaux calpines, rails, metres lineaires et crochets.
- Affichage explicite des pertes DC par string et du total multiplie par le nombre de strings.
- Colonnes CSV dediees aux longueurs DC par string et totales.

## Regle confirmee

En DC, la resistance et la chute de tension sont calculees pour une string. La perte Joule en watts est ensuite additionnee pour toutes les strings identiques :

```text
perte DC totale = perte DC/string x nombre de strings
```

La chute de tension DC affichee reste donc une chute par string, car les strings sont en parallele et ne s'additionnent pas en tension.

## Exemple

Pour un plan manuel `2 x 7` sur la toiture 1 et `1 x 7` sur la toiture 2, le calpinage presente deux blocs :

- toiture 1 : 14 panneaux a calpiner ;
- toiture 2 : 7 panneaux a calpiner ;
- total : 21 panneaux, avec rails et crochets additionnes.
