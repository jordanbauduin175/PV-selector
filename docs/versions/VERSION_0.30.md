# Version 0.30

Date : 2026-09-07

## Ajouts

- Onglet `Plan RGIE` dans l'interface navigateur.
- Schema unifilaire simplifie avec modules PV, coupure/protection DC, onduleur, protection AC, TD et compteur.
- Plan de position PV base sur le calpinage retenu et, si disponible, sur chaque toiture affectee.
- Champs dossier : adresse, EAN, responsable, date, mode de pose DC, mode de pose AC, protection AC, differentiel, coupure DC, section PE, C10/26 et signalisation DC.
- Checklist dossier avec statuts `OK`, `a verifier` et `erreur`.
- Export HTML imprimable du dossier RGIE avec schemas, checklist, signature, versions et debug.

## Notes RGIE

Le module genere un dossier de travail, pas une validation finale par organisme de controle. Il aide a verifier et documenter :

- schema unifilaire et plan de position ;
- limites Uoc froid, tension DC max onduleur, startup ete et plage MPPT ;
- courants Impp/Isc par MPPT ;
- pertes Joule AC/DC ;
- distribution et limite de puissance AC ;
- presence des informations administratives et pieces constructeur a joindre.

Les protections exactes, differentiels, parafoudres, sections definitives et exigences GRD doivent rester verifiees sur chantier et avec les notices fabricant.
