# Version 0.24

Cette version corrige les calculs temperature des panneaux.

Changements principaux :

- `coef_tension_pct_c` est traite comme coefficient `Uoc/Voc`.
- `Umpp(T)` utilise `Umpp STC + Uoc STC x coef Uoc x (T - 25)`.
- ajout de `coef_isc_pct_c` au catalogue panneaux et aux imports datasheets.
- `Impp(T)` utilise `Impp STC + Isc STC x coef Isc x (T - 25)`.
- `Isc` MPPT est corrige par le coefficient Isc quand il est disponible.
- les entetes et validations affichent les temperatures froid/chaud réellement saisies.
- le catalogue a ete regenere ; les panneaux Trina Vertex importes ont `coef_isc_pct_c = 0.04`.