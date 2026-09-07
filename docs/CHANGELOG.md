# Changelog

Toutes les modifications notables de PV Selector sont tracees ici.

## v0.31 - 2026-09-07

- Remplacement du schema unifilaire horizontal par un rendu plus proche d'un schema electrique RGIE.
- Ajout des symboles panneau/string, sectionneur DC, onduleur DC/AC, protection AC PV, barre TD, depart installation, compteur et terre.
- Affichage direct dans le schema des cables Solar/XVB, sections, distances, polarites/conducteurs, puissances DC/AC, affectation MPP et controles principaux.
- L'export `Dossier RGIE` reprend automatiquement ce nouveau schema.

## v0.30 - 2026-09-07

- Ajout d'un onglet `Plan RGIE` dans l'interface.
- Generation d'un schema unifilaire simplifie `PV - coupure DC - onduleur - protection AC - TD - compteur`.
- Generation d'un plan de position PV base sur le calpinage et l'allocation des toitures retenues.
- Ajout des champs dossier : adresse, EAN, responsable, date, modes de pose DC/AC, protections AC/DC, differentiel, PE structures, verification C10/26 et signalisation DC.
- Ajout d'une checklist dossier avec statuts `OK`, `a verifier` ou `erreur` pour les validations electriques et pieces a joindre.
- Ajout d'un export HTML imprimable du dossier RGIE avec schemas, checklist, signature, versions et informations debug.

## v0.29 - 2026-09-07

- Calpinage en mode `Strings manuel par toiture` calcule toiture par toiture, avec les dimensions brutes propres a chaque toiture.
- Affichage des totaux multi-toitures : panneaux poses, rails, metres lineaires et crochets.
- Clarification des pertes DC : longueur principale et cordons affiches par string puis multiplies par le nombre de strings.
- La chute de tension DC reste exprimee par string, tandis que la perte Joule DC totale additionne les strings paralleles.
- Ajout des longueurs DC par string et totales dans l'export CSV, la note de calcul et les informations debug.

## v0.28 - 2026-09-06

- Ajout d'un mode `Strings manuel par toiture` dans l'interface.
- Possibilite de forcer un plan du type `Toiture 1 = 2 strings de 7 modules` et `Toiture 2 = 1 string de 7 modules`.
- L'optimiseur limite alors la recherche a cette architecture et garde les validations Uoc, startup, Umpp, Isc/MPPT, puissance PV et pertes.
- Le coefficient de production est pondere selon les toitures reellement affectees par le plan manuel.
- Ajout du plan strings dans le detail, l'export CSV, la note de calcul, les rejets et les informations debug.

## v0.27 - 2026-09-01

- Ajout du champ onduleur `startup_input_voltage_v` dans le catalogue CSV/JSON et la base SQLite.
- Extraction datasheet des libelles `startup input voltage`, `start-up voltage` et `starting voltage`.
- Controle de redemarrage ete : `Uoc chaud` de la string doit rester superieur ou egal a la tension de demarrage de l'onduleur quand elle est renseignee.
- Ajout de la colonne `Startup ete` dans le tableau, du controle detaille, des rejets dedies et des valeurs dans les exports CSV/note de calcul.
- Conservation d'un mode non bloquant pour les anciens onduleurs dont la tension de demarrage n'est pas encore renseignee.

## v0.26 - 2026-08-31

- Correction de l'import des datasheets SMA Sunny Boy Smart Energy multi-modeles.
- Extraction de `SBSE3.6-50`, `SBSE4.0-50`, `SBSE5.0-50` et `SBSE6.0-50` depuis une meme fiche.
- Propagation des valeurs communes DC/MPPT/Isc et conservation des puissances AC/PV propres a chaque modele.
- Correction de la detection fabricant SMA pour eviter les collisions avec du texte parasite de sections batterie.
- Detection de phase etendue aux notations `1-phase` et `3-phase`.
- Normalisation plus robuste des champs numeriques optionnels vides ou `None`.

## v0.25 - 2026-08-31

- Ajout d'une base SQLite persistante pour stocker panneaux et onduleurs dans `storage/` ou `/storage` sur Railway.
- Ajout d'un module UI d'upload datasheet PDF/TXT/MD avec formulaire pre-rempli avant insertion.
- Ajout des endpoints backend `/api/datasheets/preview`, `/api/db/insert`, `/api/db/panels`, `/api/db/inverters` et `/api/db/summary`.
- Chargement possible de la base SQLite dans le calcul courant depuis l'onglet Catalogues.
- Ajout des dependances PDF au backend Docker/Railway.

## v0.24 - 2026-07-22

- Correction du calcul `Umpp` chaud/froid : formule additive basee sur `Uoc` et le coefficient `Uoc/Voc`.
- Ajout du coefficient panneau `coef_isc_pct_c` pour les corrections courant.
- Correction du calcul `Impp` chaud/froid : formule additive basee sur `Isc` et le coefficient `Isc` de la datasheet.
- Controle `Isc` MPPT avec correction temperature quand le coefficient Isc est disponible.
- Affichage des temperatures froid/chaud saisies dans les entetes, controles et note de calcul.
- Regeneration du catalogue : les panneaux Trina Vertex portent `coef_isc_pct_c = 0.04`.
## v0.23 - 2026-07-22

- Ajout du module de calpinage toiture dans l'interface.
- Calcul de la toiture nette avec marges 30 cm laterales, 30 cm egout et 10 cm faitage.
- Proposition portrait/paysage avec 2 cm de clame entre panneaux.
- Calcul des rangees, rails, metres lineaires de rails et crochets.
- Choix de l'entraxe chevrons 45 cm ou 60 cm, avec crochets tous les 90 cm ou 1,20 m.
- Ajout du calpinage dans le detail, la metrique, la note de calcul et le debug.

## v0.22 - 2026-07-22

- Ajout des credits Open-Elec, du site https://www.open-elec.be et du copyright 2026 dans l'interface.
- Ajout d'un lien changelog depuis l'UI.
- Ajout du bouton `Reporter un probleme` vers `info@open-elec.be` avec un email pre-rempli.
- Ajout des versions UI/backend/schema, du contexte navigateur, des filtres, des toitures, des rejets et du meilleur choix dans les infos debug.
- Ajout des metadonnees auteur/version/site/copyright dans l'export CSV et la note de calcul.
- Alignement des versions backend, scripts catalogue/import et GUI Python sur `0.22`.

## v0.21 - 2026-07-22

- Ajout de la tension DC nominale `rated input voltage` des onduleurs.
- Ajout de l'ecart signe entre `Umpp STC` string et tension nominale onduleur.
- Affichage de l'indicateur dans le tableau, le detail, l'export CSV et la note de calcul.
- Conservation de cet indicateur comme repere non bloquant.

## v0.20 - 2026-07-22

- Ajout du backend deployable sur Railway.
- Service de l'interface sur `/`, API catalogues et endpoint `/health`.
- Ajout de `Dockerfile`, `railway.toml` et documentation Railway.

## v0.19 - 2026-07-20

- Reorganisation du depot en `ui/`, `code/`, `input/`, `output/`, `docs/` et `backend/`.
- Adaptation des chemins par defaut des scripts.

## v0.18 - 2026-07-20

- Ajout du module d'import local des datasheets PDF/TXT/MD.
- Extraction conservatrice des fiches panneaux et onduleurs.
- Generation de `panneaux.csv`, `onduleurs.csv`, base JSON et rapport d'import.
- Synchronisation possible du catalogue embarque dans l'HTML.

## v0.17 - 2026-06-10

- UX `+ Toiture` et `+ Onduleur`.
- Affectation MPP proposee automatiquement puis modifiable manuellement.
- Recalcul avec affectation MPPT imposee.

## v0.16 - 2026-06-10

- Ajout du multi-toitures avec orientation, pente et surface propres.
- Ajout du multi-onduleurs identiques : jusqu'a 2 en mono/biphase et 3 en tri.
- Allocation des modules en priorite sur la meilleure exposition.

## v0.15 - 2026-06-09

- Ajout de l'export de note de calcul pour le meilleur choix.
- Detail des donnees d'entree, calculs, validations, pertes, production et logique de classement.

## v0.14 - 2026-06-08

- Ajout du module catalogue fabricants.
- Recherche locale, stockage, import/export CSV et base fabricant initiale.

## v0.13 - 2026-06-08

- Interdiction des onduleurs tri sur distribution mono ou biphase.
- Calcul des pourcentages de chute AC par rapport a 230 V reseau.

## v0.12 - 2026-06-08

- Ajout des filtres panneau et onduleur.
- Validation et optimisation avec materiel force si un filtre est selectionne.

## v0.11 - 2026-06-08

- Ajout du schema simple `PV -> onduleur -> TD -> compteur`.
- Affichage des distances, sections, pertes DC/AC et total.

## v0.1 - 2026-06-08

- Prototype initial avec interface graphique locale.
- Selection panneaux/onduleurs, controles RGIE/reseau, consommation client, exposition toiture, pertes DC/AC et export CSV.
