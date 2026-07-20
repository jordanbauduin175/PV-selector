# Version 0.13

Date de tag : 2026-06-08

Base : version 0.12

Ajouts principaux :

- interdiction des onduleurs `tri` sur distribution `Mono` ou `Biphase` ;
- filtre onduleur adapte automatiquement au type de distribution ;
- rejet de securite cote moteur si un onduleur tri arrive quand meme avec une distribution mono/biphase ;
- calcul des pourcentages de chute de tension AC sur une reference fixe de `230 V` reseau, avec chute phase-neutre affichee en tetra ;
- export CSV enrichi avec la reference `230 V` utilisee pour le pourcentage de chute AC.
