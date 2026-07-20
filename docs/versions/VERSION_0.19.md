# Version 0.19

Date : 2026-07-20

Cette version reorganise le depot en structure projet.

- `ui/` contient l'interface HTML ;
- `code/` contient les scripts Python ;
- `input/` contient les catalogues, la base fabricants et les datasheets ;
- `output/` est reserve aux rapports et exports generes ;
- `docs/` contient les README detailles et les notes de version.

Les chemins par defaut des scripts ont ete adaptes : les donnees sont lues dans `input/`, les rapports sont ecrits dans `output/`, et la synchronisation catalogue met a jour `ui/dimensionnement_solaire.html`.
