# Dimensionnement solaire - prototype GUI v0.21

Ce dossier contient la version `v0.21` du programme :

- `ui/dimensionnement_solaire.html` : interface graphique locale a ouvrir dans un navigateur.
- `code/solar_optimizer_gui.py` : interface graphique Python et moteur de selection.
- `input/panneaux.csv` : catalogue panneaux d'exemple.
- `input/onduleurs.csv` : catalogue onduleurs d'exemple.
- `code/catalogue_fabricants.py` : module de recherche locale, stockage et export des fiches fabricant.
- `code/datasheet_importer.py` : module d'import local de datasheets PDF/TXT.
- `input/catalogue_fabricants_db.json` : base locale des fabricants, panneaux et onduleurs.

## Version 0.21

Cette version ajoute la tension DC nominale `rated input voltage` des onduleurs dans le catalogue. L'interface affiche l'ecart signe entre `Umpp STC` de la string et cette tension nominale, dans le tableau, le detail, l'export CSV et la note de calcul. Cet indicateur sert de repere qualitatif et ne bloque pas une configuration valide.

## Version 0.20

Cette version ajoute un backend deployable sur Railway. Le serveur `backend/server.py` sert l'interface sur `/`, expose les catalogues via API et fournit `/health` pour les healthchecks Railway. Le fichier `railway.toml` configure le lancement automatique du service.

## Version 0.19

Cette version reorganise le depot : ui/ pour l'interface, code/ pour les scripts, input/ pour les donnees, output/ pour les exports generes et docs/ pour la documentation. Les chemins par defaut des scripts ont ete adaptes a cette nouvelle structure.

## Version 0.18

Cette version ajoute un module d'import local des datasheets fabricants. Il lit un repertoire de fiches techniques PDF/TXT/MD, detecte autant que possible panneau ou onduleur, extrait les caracteristiques necessaires au dimensionnement, importe uniquement les fiches completes dans le catalogue, exporte `panneaux.csv` et `onduleurs.csv`, puis peut synchroniser le catalogue embarque dans l'interface HTML. Les fiches incompletes sont listees dans `datasheet_import_report.csv`.
## Version 0.17

Cette version ameliore l'UX de l'interface navigateur. Les toitures sont ajoutees avec un bouton `+ Toiture` jusqu'a 8 zones, les emplacements onduleurs avec un bouton `+ Onduleur`, et les limites restent appliquees : 2 emplacements maximum en mono/biphase, 3 en tri delta ou tetra. L'affectation MPPT est proposee automatiquement, puis peut etre modifiee manuellement string par string. Le moteur recalcule alors les configurations valides avec cette affectation imposee.

## Version 0.16

Cette version ajoute le dimensionnement multi-toitures dans l'interface navigateur : jusqu'a 3 toitures peuvent etre renseignees avec surface, orientation et pente propres. Les modules sont alloues en priorite sur la toiture au meilleur coefficient d'exposition, puis sur les autres si la surface manque. Elle ajoute aussi le calcul avec plusieurs onduleurs identiques : jusqu'a 2 en mono/biphase et jusqu'a 3 en tri delta ou tetra, en conservant la limite unitaire de 5 kVA ou 10 kVA selon la distribution.

## Version 0.15

Cette version ajoute un export de note de calcul pour le meilleur choix classe. Le fichier exporte detaille les donnees d'entree, le materiel retenu, les calculs de strings, les validations Uoc/Isc/Umpp/MPPT, les pertes DC/AC, la production estimee et la logique de classement. Le critere actuel reste la production annuelle par rapport a la consommation client ; la structure prepare l'ajout futur d'un facteur prix.

## Version 0.14

Cette version ajoute un module catalogue fabricants. Il permet de lister les grands fabricants, chercher dans la base locale, stocker des panneaux/onduleurs avec URL source, date de verification et notes, importer les CSV de l'application, puis exporter des CSV compatibles avec l'interface de dimensionnement. Le catalogue embarque aussi un premier noyau de fiches verifiees : Trina Solar, Jinko Solar, LONGi, SMA, Huawei FusionSolar et Fronius.

## Version 0.13

Cette version interdit les onduleurs `tri` quand la distribution selectionnee est `Mono` ou `Biphase`. Ces onduleurs ne sont plus proposes dans le filtre onduleur et le moteur les rejette aussi par securite. Elle calcule aussi les pourcentages de chute de tension AC par rapport a une reference fixe de `230 V` reseau.

## Version 0.12

Cette version ajoute deux filtres de materiel : panneau force et onduleur force. Par defaut, les deux filtres restent sur `Tous`. Si un panneau, un onduleur ou les deux sont selectionnes, toutes les validations et optimisations sont faites uniquement avec ce materiel force.

## Version 0.11

Cette version ajoute un schema simple `PV -> onduleur -> TD -> compteur` dans le detail de configuration. Le schema affiche les distances, sections, pertes Joule et chutes de tension pour la partie DC, la liaison AC onduleur-TD, la liaison AC TD-compteur et le total de l'installation.

## Version 0.1

Cette version fige le prototype avec interface graphique locale, selection panneaux/onduleurs, contraintes RGIE et reseau, consommation client, exposition toiture, pertes DC/AC et export CSV.

## Regles verifiees

Pour chaque combinaison panneau / onduleur / nombre de modules / nombre de strings, le programme verifie :

- surface totale des panneaux inferieure a la surface utile ;
- `Uoc` froid du string inferieur ou egal a `750 V DC` pour la limite RGIE ;
- `Uoc` du string a temperature minimale inferieur a la tension DC max de l'onduleur ;
- `Umpp` du string a temperature module haute superieur au MPPT min ;
- `Umpp` du string a temperature minimale inferieur au MPPT max ;
- `Impp` par MPPT inferieur au courant max MPPT ;
- `Isc` par MPPT inferieur au courant de court-circuit max MPPT ;
- puissance PV DC inferieure a la puissance PV max acceptee par l'onduleur.
- onduleur `tri` interdit sur distribution mono ou biphase.
- limite de puissance AC unitaire selon le type de distribution : `5 kVA` en mono/biphase, `10 kVA` en tri delta ou tetra.
- nombre d'onduleurs : jusqu'a `2` en mono/biphase et jusqu'a `3` en tri delta ou tetra, selon les emplacements ajoutes dans l'interface.
- affectation MPP automatique ou manuelle, avec controle du nombre de strings par MPP et des courants MPPT/Isc.
- pertes Joule totales DC + AC inferieures ou egales a `2 %` de la puissance DC installee.
- production annuelle estimee a partir de la consommation client et du coefficient orientation/pente de chaque toiture.

## Hypotheses du prototype

- La temperature minimale est appliquee au calcul de tension ouverte `Uoc`.
- La temperature module maximale est appliquee au controle `Umpp` bas.
- Le coefficient de temperature tension du panneau est reutilise pour approximer `Umpp`.
- Le coefficient d'exposition combine l'orientation de toiture et la pente, avec une orientation sud et une pente de 35 degres comme reference favorable.
- En multi-toitures, les modules sont places en priorite sur la toiture au meilleur coefficient d'exposition. Le coefficient de production est ensuite pondere selon le nombre de modules places sur chaque toiture.
- La production annuelle estimee utilise : `puissance kWc x gisement reference x coefficient exposition`.
- Si une consommation client est renseignee, le classement privilegie la configuration dont la production annuelle estimee est la plus proche de cette consommation.
- Si la consommation client vaut 0, le classement privilegie la puissance DC installee, puis l'utilisation de surface.
- Les pertes cables sont calculees avec une resistivite cuivre de `0,0175 ohm.mm2/m`.
- Cote DC, le programme prend une distance onduleur-panneaux par string, ajoute l'aller-retour, ajoute un retour de string proportionnel au nombre de panneaux, puis ajoute les cordons panneaux en section fixe `4 mm2`.
- Cote AC, le programme calcule deux troncons : onduleur vers TD, puis TD vers compteur. La section TD-compteur est `10 mm2` par defaut et peut etre passee a `6` ou `16 mm2`.
- En multi-onduleurs, le troncon onduleur-TD est compte par onduleur et le troncon TD-compteur porte le courant total.
- Le bouton `+ Onduleur` ajoute un emplacement autorise. Le moteur peut choisir le meilleur nombre d'onduleurs jusqu'a cette limite.
- En mode MPPT manuel, le nombre d'affectations renseigne doit correspondre au nombre de strings de la configuration retenue.
- Les pourcentages de chute de tension AC sont calcules par rapport a `230 V` reseau. En tetra, la chute affichee est la chute phase-neutre utilisee pour ce pourcentage.
- La production annuelle affichee est nette des pertes cables ; la production brute avant pertes reste visible dans le detail de configuration.
- Les lignes `Exemple` des CSV sont fictives ; les lignes Trina Solar, Jinko Solar, LONGi, SMA, Huawei FusionSolar et Fronius proviennent de fiches fabricant verifiees.
- Certaines fiches onduleur ont des MPPT asymetriques. Quand le modele actuel ne permet pas de distinguer MPPT 1 et MPPT 2, la valeur limitante est utilisee pour rester conservateur.

## Lancement

Option recommandee pour une demo rapide :

```text
ouvrir ui/dimensionnement_solaire.html dans un navigateur
```

Option Python :

```powershell
python code/solar_optimizer_gui.py
```

Si Python n'est pas disponible sur le poste, installer Python 3.10+ puis relancer la commande.

Export de note de calcul :

```text
cliquer sur Exporter calcul dans l'interface apres le calcul
```

Module catalogue fabricants :

```powershell
python code/catalogue_fabricants.py summary
python code/catalogue_fabricants.py search SMA
python code/catalogue_fabricants.py export-app-csv
python code/datasheet_importer.py input/datasheets --dry-run
python code/datasheet_importer.py input/datasheets
```
