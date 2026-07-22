# PV Selector

Prototype local de dimensionnement photovoltaique.

## Structure du projet

- `backend/` : serveur web deployable sur Railway.
- `ui/` : interface navigateur HTML.
- `code/` : scripts Python et modules d'import.
- `input/` : catalogues CSV, base fabricant et datasheets sources.
- `output/` : rapports et exports generes localement.
- `docs/` : documentation et notes de version.

## Lancement rapide

Ouvrir dans un navigateur :

```text
ui/dimensionnement_solaire.html
```

## Commandes utiles

```powershell
python code/catalogue_fabricants.py summary
python code/datasheet_importer.py input/datasheets
python backend/server.py --dry-run
python code/datasheet_importer.py input/datasheets
python backend/server.py
```

## Fonctions principales

- selection panneaux / onduleurs ;
- controles Uoc froid RGIE 750 V DC, Isc, Umpp et plages MPPT ;
- toitures multiples avec orientation et pente ;
- limites mono, biphase, tri delta et tetra ;
- pertes DC/AC et chute de tension ;
- affectation MPP automatique ou manuelle ;
- export CSV et note de calcul ;
- import local de datasheets fabricants.

Deploiement Railway : `docs/RAILWAY_DEPLOY.md`.

Les notes detaillees sont dans `docs/README_dimensionnement_solaire.md`.
