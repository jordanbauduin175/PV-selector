# Datasheets a importer

Deposer ici les fiches techniques fabricants a importer dans l'outil.

Formats acceptes par le module :

- PDF avec texte extractible ;
- TXT / MD contenant le texte de la fiche.

Commande recommandee depuis la racine du projet :

```powershell
python code/datasheet_importer.py input/datasheets
```

Pour tester sans modifier le catalogue :

```powershell
python code/datasheet_importer.py input/datasheets --dry-run
```

Le module importe uniquement les fiches completes. Les fiches incompletes sont listees dans `output/datasheet_import_report.csv`.
