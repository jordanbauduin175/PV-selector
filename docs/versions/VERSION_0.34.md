# Version 0.34

Date : 2026-09-07

## Changement principal

Correction du mode strings manuel pour permettre correctement un troisieme string quand les contraintes electriques le permettent.

## Correction

- Synchronisation immediate des champs toiture pendant la saisie.
- Relecture des champs toiture visibles juste avant chaque calcul.
- Correction du cas ou `3 strings x 7 modules` pouvait rester lu comme `0 string` dans l'etat interne.

## Verification

Cas teste dans l'interface : mode strings manuel, toiture `3 x 7`, surface suffisante, deux emplacements onduleur mono autorises. Le moteur retourne des configurations valides et propose une repartition MPPT compatible.
