# Version 0.25

Cette version ajoute le stockage SQLite et un flux de validation avant import.

Changements principaux :

- creation d'une base `pv_selector.sqlite3` dans `storage/` ou `/storage` sur Railway ;
- initialisation automatique depuis les CSV existants si la base est vide ;
- upload de datasheets PDF/TXT/MD depuis l'interface ;
- extraction en previsualisation, sans insertion immediate ;
- formulaire editable pour verifier les champs panneau ou onduleur ;
- insertion validee dans SQLite puis rechargement possible dans le calcul ;
- endpoints backend dedies au catalogue SQLite et a l'analyse des datasheets ;
- installation des dependances PDF dans le backend Railway.
