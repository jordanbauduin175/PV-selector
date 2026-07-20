# Version 0.15

Date de tag : 2026-06-09

Base : version 0.14

Ajout principal :

- passage des interfaces `dimensionnement_solaire.html` et `solar_optimizer_gui.py` en badge `v0.15` ;
- ajout du bouton `Exporter calcul` dans l'interface navigateur ;
- ajout du bouton `Exporter calcul` dans l'interface Python ;
- generation d'une note de calcul Markdown pour la meilleure configuration classee ;
- detail des entrees, choix materiel, calculs de strings, controles electriques, pertes DC/AC et production ;
- explication de la suite logique de decision : ecart conso/production, surproduction, puissance DC, surface utile et ratio DC/AC ;
- structure preparee pour integrer plus tard un facteur prix dans le classement ;
- correction du declenchement de telechargement dans le navigateur integre : le lien d'export est maintenant attache temporairement a la page et un message de confirmation apparait.
