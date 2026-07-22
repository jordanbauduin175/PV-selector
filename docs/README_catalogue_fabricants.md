# Module catalogue fabricants v0.19

Ce module sert a rechercher localement, stocker et exporter les caracteristiques fabricants des panneaux et onduleurs. Il peut aussi importer des fiches techniques placees dans `input/datasheets`.

## Structure liee au catalogue

- `code/catalogue_fabricants.py` : outil de gestion du catalogue.
- `code/datasheet_importer.py` : module d'import des datasheets PDF/TXT/MD.
- `input/datasheets/` : repertoire de depot des fiches techniques a analyser.
- `input/catalogue_fabricants_db.json` : base locale avec fabricants sources et materiel stocke.
- `input/panneaux.csv` et `input/onduleurs.csv` : catalogues utilises par l'interface.
- `output/` : rapports et exports generes.

## Principe

Le module ne valide pas une fiche technique sans source. Chaque entree peut garder la reference, le fabricant, les valeurs electriques utiles, l'URL ou le fichier source, la date de verification et des notes.

Le module d'import datasheets reste conservateur : il importe seulement les fiches ou tous les champs requis sont retrouves. Les fiches incompletes sont listees dans `output/datasheet_import_report.csv`.

Les fiches Huawei SUN2000 multi-modeles sont decoupees par colonne : une datasheet `SUN2000-5/6/8/10/12K-MAP0` produit une entree distincte par modele, avec les puissances, plages DC et courants repris dans la bonne colonne.

## Commandes utiles

Afficher le resume :

```powershell
python code/catalogue_fabricants.py summary
```

Chercher dans le catalogue local :

```powershell
python code/catalogue_fabricants.py search SMA
python code/catalogue_fabricants.py search 430 --kind panel
```

Exporter vers les CSV attendus par l'application :

```powershell
python code/catalogue_fabricants.py export-app-csv
```

Importer les datasheets d'un repertoire :

```powershell
python code/datasheet_importer.py input/datasheets
python code/catalogue_fabricants.py import-datasheets input/datasheets
```

Analyser sans modifier le catalogue :

```powershell
python code/datasheet_importer.py input/datasheets --dry-run
```

Note : quand une fiche onduleur donne des MPPT asymetriques et que l'application ne sait pas encore modeliser chaque MPPT separement, l'entree stockee utilise la valeur limitante.
