# Module catalogue fabricants v0.18

Ce module sert a rechercher localement, stocker et exporter les caracteristiques fabricants des panneaux et onduleurs. Il peut maintenant importer des fiches techniques placees dans un repertoire local.

Fichiers :

- `catalogue_fabricants.py` : outil de gestion du catalogue.
- `datasheet_importer.py` : module d'import des datasheets PDF/TXT.
- `datasheets/` : repertoire de depot des fiches techniques a analyser.
- `catalogue_fabricants_db.json` : base locale avec fabricants sources et materiel stocke.
- `panneaux_catalogue_export.csv` et `onduleurs_catalogue_export.csv` : exports possibles pour l'application de dimensionnement.

La base contient un premier noyau de fiches verifiees depuis sources officielles : Trina Solar, Jinko Solar, LONGi, SMA, Huawei FusionSolar et Fronius. Les autres fabricants sont presents comme sources a alimenter progressivement.

## Principe

Le module ne valide pas une fiche technique sans source. Chaque entree peut garder :

- la reference ;
- le fabricant ;
- les valeurs electriques utiles au dimensionnement ;
- l'URL de la fiche technique ou page officielle ;
- la date de verification ;
- des notes.

## Commandes utiles

Afficher le resume :

```powershell
python catalogue_fabricants.py summary
```

Chercher dans le catalogue local :

```powershell
python catalogue_fabricants.py search SMA
python catalogue_fabricants.py search 430 --kind panel
```

Lister les fabricants sources :

```powershell
python catalogue_fabricants.py list-sources
python catalogue_fabricants.py list-sources --kind inverter
```

Generer des liens de recherche web pour une fiche technique :

```powershell
python catalogue_fabricants.py search-queries --manufacturer SMA --product "Sunny Boy 5.0" --domain sma.de
```

Exporter vers les CSV attendus par l'application :

```powershell
python catalogue_fabricants.py export-app-csv
```

Importer les datasheets d'un repertoire :

```powershell
python datasheet_importer.py datasheets
python catalogue_fabricants.py import-datasheets datasheets
```

Analyser sans modifier le catalogue :

```powershell
python datasheet_importer.py datasheets --dry-run
```

Ajouter une fiche panneau verifiee :

```powershell
python catalogue_fabricants.py add-panel --reference "ABC-450" --fabricant "Fabricant" --puissance-w 450 --largeur-m 1.134 --hauteur-m 1.762 --uoc-v 41.2 --isc-a 14.0 --umpp-v 34.5 --impp-a 13.2 --coef-tension-pct-c -0.28 --source-url "https://..." --source-type official_pdf
```

Ajouter une fiche onduleur verifiee :

```powershell
python catalogue_fabricants.py add-inverter --reference "INV-5K" --fabricant "Fabricant" --puissance-ac-w 5000 --puissance-pv-max-w 7500 --tension-dc-max-v 600 --mppt-min-v 120 --mppt-max-v 550 --courant-max-mppt-a 16 --isc-max-mppt-a 20 --nombre-mppt 2 --strings-max-par-mppt 1 --phase mono --source-url "https://..." --source-type official_pdf
```

## Workflow recommande

1. Chercher la fiche technique officielle du fabricant.
2. Relever les donnees utiles : puissance, dimensions, `Uoc`, `Isc`, `Umpp`, `Impp`, coefficient tension pour les panneaux ; limites DC/MPPT/courants pour les onduleurs.
3. Ajouter l'entree avec `add-panel` ou `add-inverter`.
4. Exporter les CSV.
5. Coller/importer les CSV dans l'application de dimensionnement.

Le scraping automatique complet n'est pas active par defaut : les sites fabricants changent souvent, les PDF bougent, et une mauvaise valeur de fiche technique peut fausser le dimensionnement.

Le module d'import datasheets reste conservateur : il importe seulement les fiches ou tous les champs requis sont retrouves. Les fiches incompletes sont listees dans `datasheet_import_report.csv` avec les champs manquants.

Note : quand une fiche onduleur donne des MPPT asymetriques et que l'application ne sait pas encore modeliser chaque MPPT separement, l'entree stockee utilise la valeur limitante.

