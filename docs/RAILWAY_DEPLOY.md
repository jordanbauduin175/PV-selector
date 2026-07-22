# Deploiement Railway

Ce projet est pret pour Railway avec `railway.toml` a la racine.

## Fonctionnement

- Railway lance `python backend/server.py`.
- Le backend ecoute le port fourni par la variable `PORT`.
- `/health` repond `200` pour les healthchecks Railway.
- `/` sert l'interface `ui/dimensionnement_solaire.html`.
- Les catalogues sont aussi exposes en API :
  - `/api/catalog/panels`
  - `/api/catalog/inverters`
  - `/api/catalog/summary`

## Mise en place automatique

1. Dans Railway, creer un nouveau projet.
2. Choisir `Deploy from GitHub repo`.
3. Selectionner `jordanbauduin175/PV-selector`.
4. Garder la branche `main`.
5. Verifier que le service utilise le fichier `railway.toml` a la racine.
6. Activer le domaine public Railway si necessaire.

Une fois le service Railway lie au repo GitHub, chaque `git push` sur `main` redeploie automatiquement le backend.

## Test local

Depuis la racine du repo :

```powershell
$env:PORT=8000
python backend/server.py
```

Puis ouvrir :

```text
http://127.0.0.1:8000
```
