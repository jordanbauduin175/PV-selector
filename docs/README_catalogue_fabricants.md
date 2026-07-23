# Module catalogue fabricants v0.24

Ce module sert a rechercher localement, stocker et exporter les caracteristiques fabricants des panneaux et onduleurs. Il peut aussi importer des fiches techniques placees dans `input/datasheets`.

## Version 0.24

Le schema catalogue panneaux ajoute `coef_isc_pct_c`, coefficient de temperature du courant de court-circuit. L'import datasheet extrait ce coefficient quand il est disponible ; les panneaux Trina Vertex importes depuis la fiche fournissent maintenant `0.04 %/C`. Le champ historique `coef_tension_pct_c` reste le coefficient `Uoc/Voc`.
## Version 0.22

Le schema catalogue reste synchronise avec l'application v0.22. Les exports generes peuvent etre associes au changelog et aux informations de support Open-Elec pour faciliter le diagnostic.

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

Les fiches Huawei SUN2000 multi-modeles sont decoupees par colonne : une datasheet `SUN2000-5/6/8/10/12K-MAP0` produit une entree distincte par modele, avec les puissances, plages DC, courants et la tension DC nominale `rated input voltage` repris dans la bonne colonne quand la fiche les fournit.

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

## CI GitHub

Le workflow `.github/workflows/regenerate-catalog.yml` se lance quand une fiche est ajoutee ou modifiee dans `input/datasheets/`. Sur un `push`, il regenere `input/catalogue_fabricants_db.json`, `input/panneaux.csv`, `input/onduleurs.csv` et le catalogue embarque dans `ui/dimensionnement_solaire.html`, puis commit automatiquement les changements si necessaire. Sur une pull request, il verifie que ces fichiers sont deja a jour.

Note : quand une fiche onduleur donne des MPPT asymetriques et que l'application ne sait pas encore modeliser chaque MPPT separement, l'entree stockee utilise la valeur limitante.
