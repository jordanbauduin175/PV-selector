# Version 0.18

Date : 2026-07-20

Cette version ajoute un module d'import local des datasheets fabricants.

- lecture recursive d'un repertoire de fiches techniques PDF, TXT ou MD ;
- detection automatique panneau / onduleur quand c'est possible ;
- extraction des champs utiles au dimensionnement : puissance, tensions, courants, dimensions, coefficient de temperature, MPPT, phase et limites DC/AC ;
- import uniquement des fiches completes dans `catalogue_fabricants_db.json` ;
- export automatique vers `panneaux.csv` et `onduleurs.csv` ;
- synchronisation possible du catalogue embarque dans `dimensionnement_solaire.html` ;
- generation de `datasheet_import_report.csv` avec les fiches importees, incompletes ou illisibles.

Commandes principales :

```powershell
python datasheet_importer.py datasheets --dry-run
python datasheet_importer.py datasheets
python catalogue_fabricants.py import-datasheets datasheets
```

Le module reste volontairement conservateur : si une valeur critique manque ou n'est pas lisible, la fiche est envoyee au rapport de verification au lieu d'etre importee.
