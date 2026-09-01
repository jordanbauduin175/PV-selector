# Version 0.27

Date : 2026-09-01

## Objet

Ajouter la tension de demarrage DC des onduleurs et verifier que les strings peuvent redemarrer en ete apres une coupure reseau.

## Changements

- Ajout du champ catalogue onduleur `startup_input_voltage_v`.
- Migration SQLite automatique avec colonne `startup_input_voltage_v`.
- Extraction datasheet des libelles `startup input voltage`, `start-up voltage`, `starting voltage` et `start voltage`.
- Controle bloquant : `Uoc chaud` de la string doit etre superieur ou egal au `startup input voltage` quand il est renseigne.
- Ajout de la colonne UI `Startup ete`, des rejets `Startup`, du detail de validation, de l'export CSV et de la note de calcul.

## Regle de calcul

`Uoc chaud = Uoc STC string x (1 + coef Uoc %/C / 100 x (temperature chaude - 25))`

La validation de demarrage utilise `Uoc chaud`, pas `Umpp chaud`, car apres coupure reseau l'onduleur est arrete et la chaine PV est a vide.
