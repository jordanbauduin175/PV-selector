# Version 0.20

Date : 2026-07-21

Cette version ajoute une couche backend deployable sur Railway.

- ajout de `backend/server.py` en Python standard, sans dependance externe ;
- ajout de `railway.toml` avec start command et healthcheck ;
- l'interface HTML est servie sur `/` ;
- les catalogues sont exposes via `/api/catalog/panels`, `/api/catalog/inverters` et `/api/catalog/summary` ;
- documentation de connexion Railway dans `docs/RAILWAY_DEPLOY.md`.

Une fois le repo connecte dans Railway sur la branche `main`, les pushes GitHub redeploient automatiquement le service.
