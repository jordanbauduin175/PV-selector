# Version 0.26

Cette version renforce l'import des datasheets onduleurs multi-modeles.

Changements principaux :

- ajout d'un extracteur SMA Sunny Boy Smart Energy multi-colonnes ;
- extraction separee de `SBSE3.6-50`, `SBSE4.0-50`, `SBSE5.0-50` et `SBSE6.0-50` depuis une seule fiche ;
- reprise des puissances AC/PV par modele ;
- propagation des valeurs communes : tension DC max, plage MPPT, courants MPPT/Isc, nombre MPPT et strings par MPPT ;
- detection fabricant SMA prioritaire sur les textes Sunny Boy / Sunny Tripower ;
- detection phase compatible `1-phase` et `3-phase` ;
- champs numeriques optionnels plus tolerants quand la datasheet ne donne pas de tension DC nominale.
