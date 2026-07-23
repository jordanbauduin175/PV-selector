# Changelog

Toutes les modifications notables de PV Selector sont tracees ici.

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
