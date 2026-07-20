# Datasheets a importer

Deposer ici les fiches techniques fabricants a importer dans l'outil.

Formats acceptes par le module :

- PDF avec texte extractible ;
- TXT / MD contenant le texte de la fiche.

Commande recommandee depuis le dossier `outputs` :

```powershell
python datasheet_importer.py datasheets
```

Pour tester sans modifier le catalogue :

```powershell
python datasheet_importer.py datasheets --dry-run
```

Le module importe uniquement les fiches completes. Les fiches incompletes sont listees dans `datasheet_import_report.csv`.
