# Version 0.31

Date : 2026-09-07

## Changement principal

Le schema unifilaire du module `Plan RGIE` adopte un rendu plus proche d'un schema electrique de dossier de controle.

## Ajouts

- Champ PV represente verticalement avec nombre de modules par string, nombre de strings, puissance et Uoc froid.
- Liaison DC avec designation cable Solar, section, PE, distance par string et pertes DC.
- Symbole onduleur DC/AC avec marque, type, puissance PV max, puissance AC et affectation MPP.
- Depart AC PV vers barre TD avec protection A, designation cable XVB, conducteurs et distance.
- Barre TD avec depart installation B, differentiel, compteur kWh, terre et liaison TD-compteur.
- Bloc de controles calcules : Uoc froid, startup ete, Umpp chaud/froid, Impp/Isc MPPT et pertes totales.

## Note

Le dessin reste un schema de travail genere automatiquement. Les calibres, symboles definitifs et libelles doivent rester ajustables selon le chantier, la notice fabricant, le GRD et l'organisme de controle.
