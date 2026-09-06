# Version 0.28

Date : 2026-09-06

## Objectif

Permettre de forcer manuellement le nombre de strings et le nombre de modules par string sur chaque toiture.

## Changements

- Ajout du mode `Manuel par toiture` dans la section Toitures.
- Ajout des champs `Strings` et `Modules/string` sur chaque toiture quand ce mode est actif.
- Validation du plan manuel avant optimisation.
- Recherche limitee a l'architecture imposee quand un plan manuel est actif.
- Allocation toiture forcee par le plan manuel, avec coefficient de production pondere sur les toitures affectees.
- Ajout du plan strings dans le detail, l'export CSV, la note de calcul et les informations debug.

## Exemple

- Toiture 1 : `2` strings de `7` modules.
- Toiture 2 : `1` string de `7` modules.
- Architecture forcee : `3 strings x 7 modules/string = 21 modules`.

## Notes

Cette version conserve le comportement automatique par defaut. En mode manuel, toutes les strings doivent avoir le meme nombre de modules afin de rester compatible avec les controles electriques et les calculs de pertes existants.
