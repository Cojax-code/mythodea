# Mythodea v2.0 — Spécification de référence

Ce document décrit **l'état actuel utile de Mythodea** : règles, formats persistants,
architecture et invariants. Il ne sert pas de journal de modifications.

Les règles détaillées de progression, d'étiquettes et de QG sont définies dans
[REGLES_V2.md](REGLES_V2.md), commun aux modes classique et Survie.

Pour toute modification du moteur :

- lire cette spécification et le code concerné ;
- ne pas modifier une règle de gameplay sans décision explicite ;
- préserver les chemins Linux, formats d'état, permissions et rapports ;
- signaler une incohérence entre code et spécification au lieu de la corriger
  silencieusement.

---

## 1. Concept

Mythodea est un wargame au tour par tour dans lequel Linux fait partie du gameplay.

- les joueurs sont des comptes Linux ;
- les généraux sont des dossiers ;
- les unités sont des sous-dossiers ;
- déplacer un général signifie déplacer physiquement son dossier ;
- le moteur valide ensuite les actions, applique les sanctions éventuelles,
  résout les combats et produit les rapports.

La version classique actuelle oppose :

```text
j1 contre j2
```

La cible principale est Linux / Raspberry Pi OS.

---

## 2. Architecture actuelle

```text
mythodea/
├── bash/
│   ├── instal.sh
│   ├── nettoyage.sh
│   ├── reset_survie.sh
│   ├── stockage.sh
│   └── start.sh
├── python/
│   ├── mythodea_v_1_5.py
│   ├── config.py
│   ├── etat.py
│   ├── generaux.py
│   ├── mouvements.py
│   ├── securite.py
│   ├── combats.py
│   ├── rapports.py
│   ├── plateau.py
│   ├── victoire.py
│   ├── survie.py
│   ├── minuterie.py
│   ├── vagues.py
│   └── tests_linux/
├── .dev/
│   └── tests/
│       ├── test_mythodea.py
│       ├── test_modes.py
│       ├── test_village.py
│       ├── test_combats_camps.py
│       ├── test_vagues.py
│       ├── test_surnombre.py
│       └── test_cycle_survie.py
├── README.md
├── REGLES_V2.md
├── SURVIE_SPEC.md
├── TESTS_LINUX_SURVIE.md
└── MYTHODEA_SPEC.md
```

Responsabilités :

| Module | Rôle |
| --- | --- |
| `mythodea_v_1_5.py` | sélection du mode et orchestration du tour classique |
| `config.py` | chemins, carte, constantes, légende des ordres et profils des modes |
| `etat.py` | compteurs, positions, fatigue, météo, état persistant et verrou du cycle Survie |
| `generaux.py` | généraux, fiches, ordres, blocs, unités, permissions |
| `mouvements.py` | règles de déplacement et repli |
| `securite.py` | anti-triche, audit des déplacements et contrôles territoriaux sans effets secondaires |
| `combats.py` | résolution des combats |
| `rapports.py` | rapports et tableaux |
| `plateau.py` | structure du plateau, accueil passif du village et coordination des territoires |
| `victoire.py` | objectifs et victoire |
| `vagues.py` | compositions des vagues Est, sans accès au disque |
| `survie.py` | cycle Survie Est, progression et rattrapage ennemis, vagues, cascades et retraites différées |
| `minuterie.py` | validation de la durée et attente jusqu'à une échéance, sans logique métier |
| `catalogues.py` | identifiants permanents, types d'unités, recettes, ordres et évolutions |
| `progression.py` | caractéristiques officielles, tirages pondérés et montée de niveau configurable |
| `commandement.py` | effets fractionnaires des étiquettes, instantané QG/Messager et répartition du soutien territorial |
| `soldats.py` | identité individuelle, blessures, sauvetages et batailles survécues |
| `formation.py` | formation en caserne militaire, hôpital, École et Forge, séjours, mémoires et transformations |
| `cycle_linux.py` | gel Linux, capture privée, publication de générations et permissions des phases Survie |
| `survie_admin.py` | diagnostic, dégel de secours et republication explicitement autorisée, sans rejeu métier |
| `crypte.py` | collecteur privé Survie, recette pédagogique, cooldown et attribution différée |
| `defis.py` | lieux des mini-défis, accès par camp, flags via Courrier, état privé, bestiaire et récompense unique |
| `crypte_client.py` | transport non privilégié des observations Bash vers le socket local |
| `crypte_installer.py` | installation administrative des fonctions et hooks Bash officiels |

Les dépendances sont orientées de manière à éviter les imports circulaires.
Importer les modules ne doit jamais lancer un tour. Seul le point d'entrée appelle
`main()`.

`config.configuration_mode(mode)` retourne un profil indépendant pour `classique`
ou `survie`, sans écriture sur disque ni remplacement des variables globales
classiques. Le profil distingue les acteurs de jeu, leurs comptes et groupes Linux,
et leurs camps militaires. Les fonctions de préparation du plateau, de découverte
des généraux et d'audit des déplacements acceptent un argument `configuration`
optionnel. Sans cet argument, elles conservent la configuration classique.
Le profil Survie est utilisé par le cycle jouable du front Est : préparation des
zones militaires, fenêtres d'action, déplacements ennemis, vagues, combats et
retraites. Les fonctions isolées restent appelables séparément.

`generaux.zones_generaux_territoire()` décrit les emplacements et les éventuelles
réserves. `generaux.zones_generaux()` ajoute les homes et le repli. Ces descriptions
communes sont utilisées par la recherche, l'audit et la préparation du plateau ;
elles ne lisent ni ne modifient le disque. Une zone numérotée porte un champ
`emplacement` ; une caserne militaire n'en porte pas. Seules les places actives `1..4`
participent à la lecture des forces engagées. En Survie, les renforts alliés
`territoire/joueur/renforts/5..20`, uniquement hors village, sont découverts et audités comme les autres
généraux, avec leurs propriétaires séparés. Ils restent distincts de la caserne militaire.

En Survie, ces descriptions incluent aussi `territoire/bot/renforts/`, sans
emplacement de combat. L'inventaire de `survie.py` conserve tous les ennemis des
places et des renforts. La lecture des forces engagées reste limitée aux quatre
places et n'effectue pas de déplacement. À la fin d'un affrontement territorial
(frontal puis rangé), `generaux.remonter_renforts_bot()` remplit immédiatement les
places libres avec les premiers renforts vivants, sans lancer un nouvel affrontement.
Les survivants actifs gardent leur emplacement. L'ordre de la colonne est celui des
positions `1` à `4`, puis des renforts dans leur ordre d'arrivée. Toute la colonne
avance ensemble lors de la progression automatique.

Le fichier privé `territoire/bot/renforts/ordre_arrivee.txt` contient un nom
canonique par ligne, dans l'ordre de la file. Il appartient à `root:root`, en `600`.
Les arrivées s'ajoutent à la fin ; les noms absents du disque sont ignorés.
Pour les forces préparées sans ce fichier, les renforts non enregistrés sont
ajoutés par numéro canonique croissant : leur historique d'arrivée n'est pas connu.

`survie.preparer_phase_ennemie(numero_vague, configuration, aleatoire)` avance les
anciens ennemis avant de créer la vague demandée. Le cycle complet appelle
séparément `avancer_ennemis()` puis `creer_vague_est(numero_tour + 1, ...)`, pour
intercaler un contrôle de cohérence. Il n'appelle donc pas en plus ce wrapper,
qui ferait avancer les anciennes forces une deuxième fois.
Les fonctions communes de création, de lecture des blocs, de permissions,
d'identité et de combat sont réutilisées. L'audit des déplacements des joueurs
préserve les positions des acteurs automatiques gérés par le moteur.

`survie.resoudre_cascade(territoire, configuration, mode_combat, en_cours_de_fuite=None)`
enchaîne des appels à `combats.resoudre_combat_range()`, qui continue à résoudre un seul
affrontement et renvoie les renforts promus à son terme. La cascade consulte
ensuite les choix individuels des survivants. Dans le cycle complet, la collection
`en_cours_de_fuite` conserve les destinations et places réservées. Les généraux
acceptés sont exclus des relectures de combat avant leur déplacement physique,
effectué seulement après tous les combats du tour. Sans cette collection, l'API
isolée conserve les retraites immédiates.
Les calculs, pertes, fatigue et priorités restent ceux du moteur commun.
L'absence de nouvelles promotions arrête la cascade, y compris lorsqu'une limite
de sécurité du moteur a laissé le territoire contesté.

En Survie, `generaux.scanner_ordres_surnombre()` crée les fichiers manquants des
généraux joueurs officiels, dans toutes leurs zones. Il est appelé à la fin de
l'audit des déplacements. La cascade complète aussi les participants avant le
premier affrontement. Le fichier `ordre_surnombre.txt` appartient au joueur (`600`),
avec le défaut `1` hors village et `2` au village ; un choix existant suit le dossier.
`ordre.txt` reste indépendant. Les comptes et fichiers classiques sont inchangés.

`mouvements.destination_retraite_surnombre()` cherche l'unique voisin tactique
rapprochant le plus du village ; un départage ambigu est refusé.
`mouvements.preparer_retraites_surnombre()` prépare sans déplacement le placement
des arrivants dans la file alliée `1..20` hors village (`1..4` en garnison),
selon `position_surnombre` puis leur
position d'origine.
À préférence égale, l'origine logique croissante départage les généraux, sans
priorité liée à `j1` ou `j2`. Une préférence vide, invalide ou hors de `1..20`
produit un avertissement et est traitée comme absente, sans réécrire la fiche.
Les places déjà occupées ou réservées à l'arrivée restent indisponibles. Un général
sans place libre entre son début de recherche et la capacité d'arrivée (`4` au
village, `20` ailleurs) rejoint la caserne militaire de son joueur si l'arrivée est le village.
Ailleurs, il reste sur son territoire d'origine avec un avertissement, sans suppression
ni repli ; les autres retraites possibles continuent. Aucun nouveau motif de fuite
n'est ajouté. Les unités, identités, profils, ordres, blessures, statuts, fichiers et fatigue sont
conservés ; les positions officielles sont mises à jour après chaque déplacement.
`mouvements.appliquer_retraites_surnombre()` déplace les dossiers aux places
réservées. La cascade n'applique pas de sanction de collision aux retraites tactiques.
`retraites_surnombre()` conserve l'API immédiate pour un groupe et
`retraite_surnombre()` celle pour un seul général.

En Survie, la priorité des arrivées simultanées est : occupants déjà présents
sur le territoire, puis forces déjà sur la carte arrivant ce tour, puis nouvelles
apparitions. Elle ne dépend pas de l'ordre de lecture des joueurs `j1` et `j2`.

La lecture territoriale conserve les généraux par propriétaire de jeu (`joueur`)
et ajoute leur `camp` en mémoire d'après le profil. Le compte Linux reste une
information distincte du profil (`bot` appartient à `root:root`).
`generaux.regrouper_forces_par_camp()` construit la vue `camp -> emplacement -> général`
en conservant les références aux généraux, sans remplacer leurs identités ni leurs
chemins. `lire_forces_territoire()` relit le disque puis construit cette vue.

Les résolutions frontale, rangée, OFF/OFF et OFF/DEF acceptent un profil optionnel
et utilisent ses deux camps. Le duel conserve les propriétaires réels pour la
fatigue, les pertes et la suppression de l'identité officielle. Le ciblage prend
l'adversaire parmi les deux participants effectifs, sans correspondance fixe de
noms de joueurs. Les calculs et priorités restent communs aux deux modes.

`controle_forces()` calcule le contrôle des forces regroupées ;
`controle_territoire_generaux()` et `plateau.sauvegarder_controle_territoires()`
acceptent le profil pour conserver les camps dans le contrôle. La boucle
`plateau.lancer_bataille_v15()` reste l'orchestration classique.

Le point d'entrée accepte `--mode classique` (valeur par défaut) et `--mode survie`.
L'option `--afficher-configuration` affiche le profil sans lancer de tour ni importer
les modules dépendant d'Unix. `bash bash/start.sh --mode survie` lance le cycle Est.
`--duree-action` configure la durée en secondes (120 par défaut),
`--duree-consultation` la consultation (60), `--duree-gel` le minimum de gel (10),
et `--seuil-capture` le seuil de sécurité (120, provisoire à mesurer sur Raspberry Pi).
Le seuil doit dépasser le minimum de gel. Les trois durées de phase peuvent être
neutralisées avec 0 en test. `--tours` limite les résolutions ; ces options sont
réservées au mode Survie. `bash/start.sh` les transmet au point d'entrée.
La préparation Linux requise est décrite dans `TESTS_LINUX_SURVIE.md`.

---

## 3. Environnement Linux et chemins

Racines utilisées :

```text
/game
/home/j1
/home/j2
```

Le plateau officiel est une **partition dédiée montée directement sur `/game`**,
distincte des systèmes de fichiers de `/` et `/home`. La référence unique est
`config.GAME_PATH_OFFICIEL`, utilisée par `config.game_path`. Les profils des deux
modes en dérivent leurs chemins ; `game_public_path` garde les chemins publiés
pour les journaux et PDF, même pendant une résolution privée.
Les homes joueurs restent `/home/j1` et `/home/j2`, et le dépôt administrateur peut
rester dans `/home/cojax/mythodea`. Aucun symlink entre l'ancien `/home/game` et
`/game`, aucune migration automatique d'une partie existante.

L'administrateur crée et monte la partition manuellement avant le premier lancement.
`config.verifier_partition_plateau()` contrôle, sans écriture, l'existence, l'absence
de lien, le montage exact avec `findmnt --mountpoint`, sa racine de filesystem `/`,
l'accès `rw` et des périphériques distincts de `/` et `/home`.
Le point d'entrée du moteur et l'installation Crypte officielle font ce contrôle ;
`--afficher-configuration` reste consultable sans montage. Les API métier et les
tests conservent leurs chemins temporaires injectables.

`bash/stockage.sh` partage ce contrôle entre les scripts administratifs et refuse
toute cible autre que `/game`, ainsi que les sous-montages avant nettoyage.
`reset_survie.sh` détruit le contenu, fichiers cachés inclus, sans supprimer le
point de montage ni formater la partition. Il refuse moteur actif, verrou ou gel
résiduel, puis conserve son propre verrou exclusif Survie pendant l'opération ;
seuls `general*` sont retirés des homes. Il prépare les racines et
permissions puis installe les hooks Crypte ; le moteur crée le plateau Survie.
`instal.sh` et `nettoyage.sh` restent classiques, avec le même contrôle du stockage.
Aucun script ne crée, ne monte ni ne formate une partition.

Le moteur utilise notamment :

```text
UID / GID
chown
chmod
propriétaires de fichiers
permissions Unix
```

Ces éléments font partie du jeu et ne doivent pas être neutralisés pour éviter
`sudo`.

Lancement normal :

```bash
bash bash/start.sh
```

Le lanceur retrouve la racine du projet depuis son propre emplacement et utilise
`sudo` lorsque nécessaire.

---

## 4. Carte et territoires

Carte classique actuelle :

```text
base1 <-> terrain1 <-> terrain2 <-> terrain3 <-> base2
```

Bases :

```text
j1 -> base1
j2 -> base2
```

Chaque territoire contient, pour chaque joueur, quatre emplacements :

```text
territoire/
├── j1/
│   ├── 1/
│   ├── 2/
│   ├── 3/
│   └── 4/
└── j2/
    ├── 1/
    ├── 2/
    ├── 3/
    └── 4/
```

Un emplacement ne doit contenir qu'un général du joueur concerné.

---

## 5. Génération et structure des généraux

Un général a la forme :

```text
general1/
├── avant/
├── droite/
├── gauche/
├── arriere/
└── fiche.txt
```

Limites actuelles :

```text
20 places de base par général
5 créations normales maximum par joueur
```

Les unités spéciales peuvent occuper plusieurs places. Les généraux zombies
gagnent deux places par niveau après transformation (section 22).
Les choix optionnels `etiquettes_actives.txt` et `QG.txt`/`qg.txt` sont décrits en
section 22 ; `ordre_surnombre.txt` est propre au mode Survie. Un ancien
`ordre.txt` peut subsister mais n'est plus un ordre actif.

Noms valides :

```text
general1
general2
...
```

Le numéro doit être un entier positif en chiffres ASCII, sans zéro initial.
Exemples invalides : `general01`, `general0`, `general١`.

### Identité officielle

Les compteurs sont stockés dans :

```text
/game/.systeme/compteur_general_j1.txt
/game/.systeme/compteur_general_j2.txt
```

Les compteurs et états moteur sont privés : fichiers `root:root 600`, sous
`.systeme/` (en Survie : `root:mythodea_allies 710`, traversée seule pour joindre
la socket Crypte ; sous-dossiers privés `root:root 700`). Leur remplacement atomique prépare un inode privé
avant publication ; un fichier temporaire n'est jamais exposé aux joueurs.

Les positions actives sont stockées dans :

```text
/game/.systeme/positions_generaux.txt
```

Un numéro déjà généré ne doit jamais être réutilisé. Lorsqu'un général est
entièrement détruit, son entrée de position disparaît mais le compteur n'est pas
diminué.

En Survie, une nouvelle partie attribue `general1` à chaque joueur dans son home,
avant la première fenêtre ACTIONS. L'attribution et l'inventaire initial sont
effectués sous gel. Le tour zéro ne réattribue pas un numéro déjà consommé, même
si son dossier a disparu. Un état ACTIONS au tour zéro encore vierge (sans aucune
attribution, position ni génération publiée) termine cette initialisation ; une
reprise ordinaire conserve l'échéance et ne répète pas les créations. Une phase
`preparation` interrompue reste soumise à la récupération administrative commune.

En Survie, les récompenses Crypte sont hors quota normal. Les compteurs privés
`compteur_creation_normale_j1.txt` et `compteur_creation_normale_j2.txt` comptent
uniquement les créations normales. À leur première initialisation, ils reprennent
le compteur technique existant : avant la Crypte, toutes les créations étaient
normales. Ensuite, `compteur_general_<joueur>.txt` augmente pour toute création,
normale ou récompense. Le mode classique conserve son fonctionnement antérieur.

Une récompense est créée dans `village/<joueur>/crypte/recompense/generalN`,
avec la position officielle `village`. Cette zone sans emplacement est découverte
et auditée par le moteur commun, mais exclue du contrôle et du combat. La fiche
porte le `nom_affichage` de la recette (`ame_et_lie_poulin`, `har-chez-moi` ou `pic-nic`) ;
les affichages utilisent ce nom seulement pour une identité réellement attribuée
par cette recette dans l'état privé Crypte. L'identité technique reste
`joueur:generalN`, y compris pour les sanctions, la fatigue et la destruction.

Créer manuellement un dossier portant le nom d'un ancien général ne le ressuscite
pas.

Le bot Survie utilise la même identité `bot:generalN`, le même fichier de positions
et un compteur distinct `.systeme/compteur_general_bot.txt`. Il n'est pas soumis
à la limite de cinq généraux générés des joueurs humains.

### Fiche

La fiche contient `nom` et les caractéristiques actuelles de la section 22 :
`nature`, `orientation_principale`, `trait_inne`, `niveau`, `points_commandement`,
`moral`, `progression_combat`, `progression_formation`, `evolutions_acquises`,
`evolution_apprise` et `etiquettes`.

Les champs historiques `orientation`, `strategie`, `force`, `experience` et
`etiquettes_permanentes` ne sont plus générés. Les anciennes fiches restent
lisibles ; ces clés sont ignorées par les calculs et retirées lors d'une
publication habituelle de la fiche, sans toucher aux autres champs optionnels.
L'affichage territorial utilise désormais nature, niveau, PC et moral.

Une fiche du bot Est ajoute `faction=est`, `vague=<numero>` et
`nom_affichage=general<vague>_<numero_dans_la_vague>`. `nom` reste canonique.
Les rapports utilisent ce libellé ; les données de combat conservent `general_1`
et `general_2` techniques et ajoutent `affichage_1` et `affichage_2` pour le rendu.

---

## 6. Unités et blocs

Les quatre blocs sont toujours :

```text
avant
droite
gauche
arriere
```

Une unité est un dossier contenant son équipement.

Archer :

```text
infanterie1/
└── arc
```

Piquier :

```text
infanterie1/
└── pique
```

Cavalier :

```text
cavalerie1/
└── cheval
```

### Cavalerie lourde de récompense

Le type moteur `cavalerie_lourde` est représenté par un dossier `cavalerie_LN/`,
contenant les cinq fichiers `cheval`, `armure`, `cuirasse`, `bouclier`, `casque`.
La récompense produit exactement ces fichiers dans `cavalerie_L1` à `cavalerie_L20`.
La reconnaissance exige le préfixe `cavalerie_L` et les cinq équipements fichiers.
Un dossier incomplet portant ce préfixe est invalide, sans repli vers le type
cavalier ordinaire. L'ancien format `cavalerie_lourdeN/armure` n'est plus produit
ni reconnu comme cavalerie lourde ; aucune conversion automatique n'est effectuée.
`config.unites_equipements` centralise les représentations reconnues ; ce catalogue
n'autorise pas leur construction. Il s'agit d'un format interne, sans recette
joueur déverrouillée. L'unité est comptée et nettoyée comme les autres unités.

Sa valeur de combat individuelle de base est 5, définie dans `catalogues.UNITES`.
Depuis le bloc `avant`, au moins 15 cavaliers lourds
participant ensemble doublent cette valeur, soit 10 pour cet affrontement. Le seuil
est recalculé avec les survivants avant chaque affrontement, en CHOC comme en
MANŒUVRE ; aucun bonus ne s'applique depuis les autres blocs. L'avantage de type
multiplie ensuite la valeur par 2 contre archer et cavalier : une formation
éligible vaut donc 20 par unité contre ces types. Le piquier bénéficie de son
avantage x2 contre la cavalerie lourde. La règle commune de fatigue entre blocs
du même type s'applique à la valeur contextuelle. Aucun attribut permanent de
force n'est ajouté ; le champ historique `force` de la fiche reste inchangé.

L'audit interdit toute cavalerie lourde construite manuellement, y compris dans
le home et la caserne militaire. Il vérifie l'attribution privée du général récompense et
les unités de la référence publiée `unites_actions.json`, avant les déplacements
de sanction. Une copie ou un nouveau marqueur d'équipement est supprimé ; une
unité ancienne renommée ou déplacée entre blocs est conservée. Le rapprochement
inter-systèmes de fichiers garde la limite des effectifs déjà publiés. La
publication renouvelle la référence après pertes : les morts ne peuvent pas être
réentraînés. Une validation du défi ne déverrouille aucune construction.
Les transformations officielles de Forge sont également admises : le registre privé
du soldat porte leur validation, et la référence publiée authentifie leurs unités.
Un renommage manuel ou une copie ne reçoit pas cette autorisation.

### Bloc mixte

Le type majoritaire devient le type du bloc.

- les unités minoritaires sont supprimées ;
- les unités invalides sont supprimées ;
- si plusieurs types sont à égalité en tête, **tout le bloc est supprimé** ;
- le nettoyage est effectué avant le calcul final de la limite de 20 unités.

Cette règle d'égalité est volontaire : une composition équilibrée entre plusieurs
types n'est pas considérée comme une simple erreur d'inattention.

### Entraînement Survie

Les ajouts d'unités sont permis uniquement dans le home du propriétaire et sa
réserve au village. Garnison, fronts, renforts, repli et récompense Crypte sont
exclus. Un dossier d'unité inachevé ne compte qu'après finalisation de son
équipement. Les règles du mode classique ne changent pas.

L'audit compare la capture à `.systeme/unites_actions.json` (`root:root 600`),
inclus dans `ETATS_METIER`. La référence contient `tour` et `generaux`, indexés
par chemin relatif `game/...` ou `home/<joueur>/generalN`. Chaque entrée conserve
l'identité officielle, la position, l'éligibilité à l'entraînement, le périphérique
et les unités valides : périphérique/inode du dossier, puis de chacun des
équipements dans l'ordre du catalogue, et type en dernier élément. La forme des
entrées ordinaires à un seul équipement reste inchangée ; une entrée de cavalerie
lourde conserve les cinq paires d'identités des équipements.
Un renommage ou changement de bloc conserve ces identités ; une copie, un nouvel
équipement ou une finalisation est un ajout. Aucune date n'autorise une unité.

Deux champs privés complètent cette référence en Survie :

- `premiers_deploiements` : liste des identités `joueur:generalN` effectivement
  retournées par la création moteur avant ACTIONS, au tour zéro comme aux suivants ;
- `rappels_en_attente` : dictionnaire identité → chemin relatif du home, rempli
  uniquement lorsqu'un rappel légal est accepté par l'audit.

L'absence de ces champs équivaut à des collections vides : aucune création
officielle n'est déduite de la seule présence dans le home, d'un renommage, du
compteur ou de la fiche joueur. Le premier déploiement accepté consomme le marqueur
de nouveauté. Les généraux déjà validés au home ont également accès au village,
même avec des ajouts d'unités ; un rappel du tour courant impose toujours son attente.
La publication complète renouvelle la référence sans ces champs et libère les
rappels. Une reprise d'ACTIONS conserve ces informations ; elles
suivent les captures privées et la récupération habituelle du cycle.

Pour un `mv` entre deux systèmes de fichiers, les inodes changent : les unités
équivalentes sont rapprochées par type, dans la limite des effectifs de départ.
Seul le surplus est un renforcement ; remplacer une unité par une autre du même
type pendant cette traversée ne donne aucun effectif supplémentaire. Cette
exception permet de conserver une partition `/game` distincte des homes.

Sous le gel de clôture, les identités vivantes sont relevées dans le champ
`capture` de la copie privée de cet état, avant les copies qui changent les inodes.
L'audit supprime les seuls ajouts interdits et journalise la raison. Si un général
a quitté une zone d'entraînement avec des ajouts, il revient à son chemin exact
d'origine avec toutes ses unités, sans fatigue ni repli. Cela inclut les passages
caserne militaire/garnison. Depuis home, un général nouvellement créé ou déjà enregistré
dans la référence officielle précédente peut créer ses unités puis accéder
immédiatement aux places et bâtiments autorisés du village, sans mouvement
territorial. Le droit vaut aussi pour un général vide. La validation commune
de sortie du home reste obligatoire : aucun saut direct vers un front, ni
exemption des contrôles d'identité ou de collision. Les séjours complets des
bâtiments et l'attente après entraînement en caserne militaire restent applicables.

Un rappel légal vers home peut être suivi d'entraînement à l'arrivée. Tout général
rappelé doit rester au home jusqu'à la prochaine publication, même sans ajout
d'unités. Une tentative de départ pendant cette attente le ramène au home avec
ses unités, sans fatigue ni sanction de repli. La publication suivante renouvelle
la référence : les unités acceptées sont alors anciennes, et le départ au tour
suivant est permis.

La référence est relevée sous gel après installation de la génération, jamais
reconstruite depuis des modifications pendant ACTIONS ou CONSULTATION. À l'ouverture
suivante, seules les nouvelles identités attribuées par le moteur y sont ajoutées.
La capture refuse une référence absente ou d'un autre tour. Une partie ancienne
sans référence exige une récupération administrative, sans validation rétroactive
silencieuse des troupes présentes. Une republication renouvelle la référence sans
rejouer l'audit. L'API d'audit isolée sans état de cycle conserve son usage historique.

Comme les déplacements existants, ces règles utilisent les positions aux bornes
du tour : elles ne reconstituent pas les commandes intermédiaires d'un joueur.

---

## 7. Permissions

Un général appartient réellement au joueur grâce à son propriétaire Linux.

Permissions visées :

```text
dossiers : 700
fichiers : 600
```

Propriétaires :

```text
j1 -> j1:j1
j2 -> j2:j2
```

L'UID est utilisé pour détecter les généraux placés dans l'arborescence du mauvais
joueur.

Les informations privées d'un général ne doivent pas devenir automatiquement
publiques.

---

## 8. Sécurité et anti-triche

Avant les combats, le moteur vérifie notamment :

1. général placé chez le mauvais joueur ;
2. général non autorisé ou identité inexistante ;
3. duplication d'un même général ;
4. plusieurs généraux dans le même emplacement ;
5. déplacement illégal ;
6. unités invalides ;
7. dépassement de la limite de 20 unités.

### Duplication

Hors du home, si un même général existe plusieurs fois :

- une seule occurrence est conservée ;
- les autres sont supprimées ;
- le général réel est envoyé au repli comme sanction.

Le home est un bac à sable : les anomalies qui y sont détectées produisent
uniquement un avertissement dans le rapport. Ses copies restent intactes et ne
déclenchent pas de sanction de duplication sur la carte. La recherche d'un général
privilégie son occurrence hors home afin qu'une copie du bac à sable ne la masque
pas. Une identité non autorisée dans le home n'est pas enregistrée implicitement.
Les règles d'identité et de déplacement restent contrôlées hors home.

### Conflit d'emplacement

Si plusieurs généraux d'un même joueur sont placés dans le même emplacement,
ils sont envoyés au repli.

Zone de repli :

```text
/game/repli/j1/
/game/repli/j2/
```

---

## 9. Déplacements

### Immobile

```text
origine == destination
```

Valide.

### Home

En classique, une anomalie constatée dans le home (propriétaire, identité, duplication ou
déplacement vers le home) produit uniquement un avertissement : aucun envoi au
repli, aucun nouveau délai et aucun calcul de distance de sanction depuis `home`.
Le home n'est pas un emplacement tactique soumis aux collisions de positions.
Un compteur de repli déjà existant est conservé si le général est retrouvé dans
le home ; il n'est ni renouvelé ni décrémenté pour cette anomalie.

Première sortie en mode classique :

```text
j1 : home -> base1 uniquement
j2 : home -> base2 uniquement
```

En mode Survie, les deux joueurs se déploient depuis `home` vers `village`.

Le rappel Survie d'un général officiel depuis une position tactique légale vers
le home de son propriétaire est explicite, instantané par `mv`, sans combat
supplémentaire ni fatigue ajoutée. L'audit vérifie l'UID, l'identité et l'origine
officielle ; la position devient `home` et le rappel en attente est persisté.
Le général reste au home jusqu'à la publication, même sans entraînement.
Au tour suivant, seul `home -> village` est permis ; le départ du village vers le
front attend le tour d'après. Le calcul
normal de fatigue par tour reste applicable, sans dette propre au rappel.

Un rappel depuis `repli` est refusé : le dossier revient au repli et son attente
reste inchangée, sans nouvelle sanction. Un général adverse ou sans origine
officielle légale n'est jamais enregistré dans le home par ce mécanisme. Les
copies du bac à sable restent des copies et ne masquent pas une présence sur carte.

### Repli

Le `repli` est une zone de sanction du moteur commun, notamment pour les cas
d'anti-triche et de déplacement invalide. Une retraite tactique normale d'un mode
de jeu ne doit pas utiliser cette zone sauf règle explicite.

Lorsqu'un général est envoyé au repli comme sanction, il reçoit un délai avant de
pouvoir effectuer une nouvelle action :

```text
tours_attente = ceil(distance_de_retour / 2)
```

`distance_de_retour` est la distance minimale en territoires entre le lieu où la
sanction a été constatée et le point normal de retour depuis le repli du mode
concerné. Dans le mode classique, ce point reste la propre base du joueur.

Exemples :

```text
distance 1 -> 1 tour
distance 2 -> 1 tour
distance 3 -> 2 tours
distance 4 -> 2 tours
distance 5 -> 3 tours
```

Tant que ce compteur est supérieur à zéro, le général ne peut effectuer aucune
action. Le compteur est conservé dans `.systeme/attente_repli.txt`, privé au moteur
(`root:root`, `600`), au format `joueur:generalN=tours_restants`, une ligne par
général. Un fichier absent signifie qu'aucun délai n'est enregistré.

L'audit commun valide une seule phase d'action par appel : il bloque les généraux
dont le délai était positif au début, puis décrémente ces délais en fin d'audit.
Une nouvelle sanction n'est pas décrémentée pendant l'audit qui la prononce.
Un délai de deux tours impose donc deux audits d'attente avant un retour autorisé
au troisième. La réparation du plateau, le scan des ordres et les cascades ne
décrémentent jamais ce compteur. Le cycle Survie appelle cet audit **une seule fois par résolution de tour**, y
compris pour le tour 0. Les contrôles supplémentaires effectués pendant la phase
automatique ne doivent pas réappliquer les sanctions, recalculer la fatigue ni
décrémenter une seconde fois les attentes de repli.

Un général déjà au repli ne reçoit aucune nouvelle sanction ni aucun nouveau
calcul de délai pour une nouvelle anomalie : un avertissement est produit et le
compteur existant est conservé. Le nettoyage des copies illégales hors home reste
applicable. L'audit qui constate cette duplication ou ce placement chez le mauvais
joueur ne décrémente pas son compteur. Sans nouvelle anomalie, la décrémentation
normale du tour reste applicable. Le calcul de distance est réservé aux territoires
tactiques ; il n'est jamais appelé pour sanctionner depuis `home` ou `repli`.

Une fois l'attente terminée, le retour autorisé reste uniquement vers le point de
retour normal du mode (propre base en classique ; règle spécifique du mode dans les
autres profils).

### Mouvement normal

Un territoire adjacent par tour.

En Survie, aucun trajet direct `home → est_1` n'est autorisé, à aucun tour.
Le passage par le village est obligatoire, y compris pour une nouvelle identité.
L'accès depuis home aux places et bâtiments autorisés du village est sans coût
de déplacement territorial ; leur capacité et leurs conditions restent contrôlées.
La marche forcée ne permet jamais de sauter le village. Les restrictions du tour 0,
l'attente après entraînement ou rappel et l'exception de premier entraînement
vers le village restent applicables. Une position officielle au village est
nécessaire avant la validation d'un départ vers le front.

Un général récompensé peut quitter sa zone de récompense dès sa publication pour
un déplacement normal valide, sans tour d'attente. Sa position officielle et ses
unités publiées passent dans l'audit commun ; aucune exemption persistante de
distance, capacité, fatigue ou nombre de déplacements n'est créée.

### Marche forcée

Un général peut parcourir deux territoires lorsqu'un territoire intermédiaire
valide existe.

L'intermédiaire peut être :

```text
allié
neutre
```

mais pas contrôlé par l'ennemi.

Une marche forcée valide rend le général **fatigué pour le tour**.

État de fatigue :

```text
/game/.systeme/fatigue_generaux.txt
```

La fatigue est recalculée à chaque nouveau tour.

---

## 10. Contrôle, ravitaillement et météo

États de contrôle :

```text
j1
j2
neutre
conteste
```

Règle :

```text
j1 > 0 et j2 = 0 -> j1
j2 > 0 et j1 = 0 -> j2
aucune unité       -> neutre
les deux présents  -> conteste
```

`conteste` est normalement transitoire pendant la résolution classique. À la fin
d'un tour classique, le territoire doit revenir à `j1`, `j2` ou `neutre`.
En Survie, un rattrapage bot peut laisser un territoire `conteste` jusqu'au prochain
cycle normal, sans lancer de combat supplémentaire pendant ce rattrapage.

Contrôle persistant :

```text
/game/.systeme/controle_territoires.txt
```

Le code sait également retrouver une chaîne de territoires ravitaillés depuis la
base. Les pénalités complètes de ravitaillement ne sont pas encore définies.

Météos possibles :

```text
clair
pluie
brouillard
vent
orage
neige
```

La météo est commune au tour mais n'a actuellement aucun effet de gameplay.

---

## 11. Combat des unités

Triangle :

```text
archer   > piquier
piquier  > cavalier
cavalier > archer
```

Un type avantagé utilise actuellement un multiplicateur `x2`, sinon `x1`.

### Valeurs individuelles, puissances et pertes

Chaque définition de `catalogues.UNITES` possède `valeur_combat`, un entier
strictement positif, sauf les non-combattants comme le Messager, autorisés à zéro.
Les booléens, flottants, chaînes et valeurs négatives sont refusés.
Les quatre types historiques ont une valeur de 5 : archer, piquier,
cavalier et cavalerie lourde. Ce champ est indépendant de `fabrication`, et
n'est jamais lu dans les fichiers modifiables du général ou des soldats.

Pour un bloc homogène de `n` unités encore présentes, la puissance de base est
`n * valeur_combat`. Dix archers valent donc 50, vingt archers 100. Le moteur
relit les survivants avant chaque affrontement ; un bloc vide a une puissance
nulle et un affrontement avec un bloc vide ne produit aucune perte.

La valeur effective individuelle est calculée ainsi :

```text
vA = valeur_contextuelle_A * formation_A * avantage_A * fatigue_A * etiquettes_A
vB = valeur_contextuelle_B * formation_B * avantage_B * fatigue_B * etiquettes_B
puissance_A = effectif_A * vA
puissance_B = effectif_B * vB
# Pour vA et vB strictement positifs ; cas nuls explicités ci-dessous.
pertes_A = min(effectif_A, puissance_B // vA)
pertes_B = min(effectif_B, puissance_A // vB)
survivants_A = effectif_A - pertes_A
survivants_B = effectif_B - pertes_B
```

La valeur contextuelle inclut l'éventuelle valeur propre au bloc Avant du catalogue.
Le facteur `etiquettes` additionne les pourcentages personnels et globaux compatibles,
avec les malus adverses, selon `REGLES_V2.md`, avec un plancher de **0 %**.
Une valeur effective nulle face à des dégâts positifs provoque la décimation du
bloc, sous réserve des sauvetages existants ; face à zéro dégât, elle ne provoque
aucune perte. Deux blocs à zéro ne subissent donc aucune perte. Ces branches sont
traitées avant division ; pour toute valeur positive, les formules ci-dessus
restent inchangées, même sous 1 %. Aucune perte artificielle ne départage le duel ;
les limites de résolution existantes restent applicables.
Les calculs intermédiaires restent
des `Fraction` ; aucun arrondi supplémentaire n'est appliqué. Le Messager ne cause
aucune perte et le Bouclier vivant conserve sa résolution spéciale documentée dans
`SURVIE_SPEC.md`.

`formation` vaut 2 uniquement pour la cavalerie lourde dans Avant avec au moins
15 survivants, sinon 1. `avantage` garde le triangle et les interactions lourdes
existantes. `fatigue` vaut 2 pour le bloc frais face à un bloc fatigué du même
type, sinon 1 ; la fatigue ne supprime pas les avantages entre types différents.
Chaque facteur est appliqué une seule fois à la valeur effective. Comme dans
le moteur historique, celle-ci sert également de résistance au dénominateur.
Utiliser seulement la valeur brute au dénominateur changerait les pertes
historiques et n'est pas la règle retenue.

Les pertes sont calculées simultanément à partir des deux effectifs initiaux,
arrondies vers le bas par division entière, puis plafonnées à ces effectifs.
Sans facteur particulier, on retrouve `pertes_A = min(nA, (nB * valeur_B) // valeur_A)`
et la formule symétrique. Dix unités de valeur 3 contre dix de valeur 5 donnent
donc zéro et quatre survivants ; pour les valeurs 5 contre 7, zéro et trois.
Ces exemples n'ajoutent aucun type d'unité au jeu.

Le passage uniforme de l'ancienne échelle 1 à 5 multiplie les puissances et
résistances par le même facteur : les pertes historiques restent identiques.
Les sauvetages par le moral et les blessures sont appliqués ensuite par le
traitement existant des pertes, sans nouveau bonus.

Pour définir ultérieurement une unité de puissance différente, attribuer un ID
permanent, renseigner sa définition dans `catalogues.UNITES` avec un entier positif
`valeur_combat`, puis suivre les règles de représentation et de déblocage du moteur.
Les avantages et effets éventuels doivent être définis explicitement : modifier
la valeur ne crée ni avantage, ni recette autorisée, ni effet de terrain ou d'ordre.
`verifier_catalogues` contrôle les valeurs au chargement ; l'accès au combat les
valide également. Aucun nouveau format persistant de soldat n'est nécessaire.

La fatigue n'annule pas les avantages naturels. Pour deux blocs du même type,
un bloc frais obtient l'avantage sur un bloc fatigué.

Les pertes sont appliquées directement en supprimant physiquement les dossiers
des unités.

---

## 12. Combat entre deux généraux

Un engagement comprend :

1. **CHOC INITIAL**
2. **MANŒUVRE**

### Choc initial

Les blocs de même position s'affrontent directement lorsqu'ils existent des deux
côtés :

```text
avant   <-> avant
droite  <-> droite
gauche  <-> gauche
arriere <-> arriere
```

Un général sans aucune unité est supprimé.

### Manœuvre

Les blocs survivants agissent selon une séquence globale aux deux joueurs.

Priorité :

1. **AVANT libre** : avant qui n'avait aucun avant adverse au début du choc ;
2. **ARRIÈRE** ;
3. **FLANCS** ;
4. **AVANT engagé** survivant.

Il n'existe pas de priorité permanente `j1 puis j2`.

Pour les flancs, l'effectif le plus élevé agit d'abord. Une égalité est départagée
aléatoirement.

Choix de cible :

1. cible contre laquelle le type attaquant possède son avantage naturel ;
2. sinon bloc ennemi non vide avec le plus petit effectif.

Les pertes sont immédiates. L'état des blocs est relu avant chaque action ; un bloc
détruit avant son tour n'agit pas.

Limite actuelle :

```text
10 tours de manœuvre maximum par engagement
```

---

## 13. Batailles entre plusieurs généraux

Modes :

### OFF/OFF

Utilisé lorsqu'un territoire sans défenseur propriétaire établi devient contesté.

### OFF/DEF

Utilisé lorsqu'un joueur possédait déjà le territoire et que l'adversaire y entre.
La distinction est conservée pour de futurs effets défensifs.

### Engagement frontal

Lorsque l'attaque frontale est déclenchée, les emplacements correspondants
s'affrontent d'abord :

```text
1 contre 1
2 contre 2
3 contre 3
4 contre 4
```

Les survivants passent ensuite au **COMBAT RANGÉ**.

L'ancien ordre joueur `1-2` est retiré en v2.0. Le point d'entrée frontal conservé
dans le moteur ne lit plus cet ordre. Aucun nouveau terrain ni effet de v2.1
n'est défini ici.

### Combat rangé

Sans autre règle d'ordre applicable, les généraux actifs sont pris par ordre
d'emplacement :

```text
1 -> 2 -> 3 -> 4
```

Le premier général vivant d'un camp affronte le premier général vivant du camp
adverse.

Lorsqu'un général est détruit, le suivant prend sa place. Un survivant continue
donc contre le prochain général adverse.

Limite de sécurité actuelle :

```text
20 engagements de combat rangé maximum
```

Une paire dont tous les blocs ont une valeur effective nulle ne répète pas
inutilement ses manœuvres. En combat rangé, les seules paires entièrement nulles
sont passées, dans l'ordre des emplacements, tant qu'une autre paire peut combattre.
Ce contrôle est recalculé après chaque engagement, notamment après la perte d'un QG.
La phase spéciale du Bouclier vivant conserve sa résolution propre.

Si toutes les paires actives sont nulles, la bataille s'arrête immédiatement,
sans pertes artificielles : en OFF/DEF, le défenseur doit conserver le territoire
et l'attaquant doit battre en retraite ; en OFF/OFF, les deux camps doivent partir.
Le résultat distingue cette décision de sa réalisation physique. Le défenseur
est transmis explicitement par l'appelant ; s'il manque, la décision OFF/DEF est
signalée non résolue. Le bilan facultatif des API de combat expose l'impasse et
les camps devant partir, sans modifier le retour historique des renforts promus.

La cascade Survie réutilise la retraite alliée existante lorsque sa destination
est valide, sans bot actif à l'arrivée, avec ses réservations et déplacements
différés habituels. Le QG est désactivé dès acceptation. Au village, faute de
destination, les survivants restent présents. Les destinations de retraite
classiques et bots ne sont pas définies : ces retraites restent explicitement
non résolues, sans repli de sanction ni suppression. Le contrôle reflète les forces
encore présentes (hors retraites acceptées et réservées dans le cycle différé),
jamais le seul résultat théorique de l'impasse.

---

## 14. Étiquettes et choix de retraite

Les anciens ordres joueur de `ordre.txt` sont retirés en v2.0 ; leurs IDs 1001 à
1005 restent réservés et ne sont jamais réutilisés. Les anciens fichiers ne
confèrent aucun effet ni récompense. Leur texte privé n'est pas publié.
Les anciennes données expérimentales liées aux ordres ne constituent pas une
obligation de migration ; elles ne doivent pas réintroduire d'effet supprimé.

`ordre_surnombre.txt` reste indépendant et conserve ses choix de retraite ou de
poursuite définis dans `SURVIE_SPEC.md`. Les modes OFF/OFF et OFF/DEF restent
disponibles avec le même moteur de combat. Aucun nouvel ordre n'est ajouté.

---

## 15. Rapports

Répertoire :

```text
/game/rapport/
```

Rapports :

```text
rapport_court.txt
rapport_long.txt
territoires/<territoire>.txt
```

### Rapport court

Informations publiques et synthèse du tour.

### Rapport long

Journal technique détaillé utile au développement et au diagnostic.

### Rapport territorial

Rapport lisible de bataille. Terminologie officielle :

```text
ENGAGEMENT FRONTAL
CHOC INITIAL
MANŒUVRE
COMBAT RANGÉ
BILAN
```

Éviter `poursuite` dans le rapport joueur.

Le bilan indique notamment forces initiales/restantes, pertes et généraux engagés.
Un général présent dans la force au début est considéré comme engagé même s'il ne
finit pas par combattre personnellement ; le détail du rapport permet de voir s'il
a réellement subi des pertes.

---

### Rapport d'exploration Survie

`village/<joueur>/hotel_de_ville/rapport_exploration.txt` est une photographie
du plateau, distincte du bilan du tour et des journaux de combat. Elle montre
village, est_1, est_2, est_3 et repli, sans home ni dossiers techniques. Les deux
joueurs disposent de documents séparés et du même niveau d'information.

`generaux.lire_composition_general()` compte les unités avec `identifier_unite()`
sans nettoyage, réparation ni application des limites. Les types reconnus d'un
bloc mixte restent visibles séparément ; les objets non reconnus ne sont pas
comptés et restent intacts. Les lectures utilisées par les combats sont inchangées.
`rapports.lire_etat_exploration()` réutilise les zones du moteur et
`controle_forces()` pour les seules places actives. Réserve, renforts et récompenses
Crypte sont présentés séparément ; le repli reste une zone de sanction hors combat,
sans contrôle territorial inventé. Le surnombre bot est entièrement visible.

`rapports.generer_rapport_exploration(joueur, etat_publie)` produit uniquement du
texte à partir de cette photographie en mémoire. Ce rendu par destinataire
centralise la future personnalisation de la visibilité, sans la filtrer aujourd'hui.
Le rapport n'appelle ni audit, ni combat, ni déplacement.

À la préparation du tour 0, une lecture sous gel bref produit le rapport initial
avant l'ouverture d'ACTIONS. Ensuite, `Generations.publier()` reconstruit les deux
rapports après installation de tous les territoires et états, toujours sous le
gel de publication, avant CONSULTATION et le dégel. Chaque fichier est remplacé
atomiquement, appartient à `root:<groupe_joueur>` en `640` (`440` en CONSULTATION).
L'ouverture d'ACTIONS restaure seulement ses droits, sans recalcul ni réécriture.
Une erreur empêche la validation de publication ; la republication administrative
reconstruit les rapports depuis le résultat réinstallé, sans rejouer le moteur.

## 16. Victoire classique

Chaque base contient un objectif secret :

```text
base1/objectif.txt
base2/objectif.txt
```

Les joueurs peuvent déposer une tentative dans la base adverse :

```text
base2/tentative_j1.txt
base1/tentative_j2.txt
```

Une tentative exacte déclenche la victoire. Une tentative incorrecte est vidée
après vérification.

---

## 17. Cycle d'un tour

Le point d'entrée `python/mythodea_v_1_5.py` orchestre le cycle du mode sélectionné ;
la logique métier reste dans les modules spécialisés.

### Mode classique

Ordre général actuel :

```text
préparer rapports et météo
        ↓
réparer / compléter la structure du plateau
        ↓
faire apparaître un général par joueur si possible
        ↓
vérifier sécurité et déplacements
        ↓
vérifier victoire
        ↓
si pas de victoire : résoudre les batailles
        ↓
sauvegarder le contrôle final
        ↓
afficher le rapport court
```

`plateau.reparer_structure()` répare uniquement les dossiers et leurs permissions,
selon le profil fourni (classique par défaut). Le point d'entrée classique appelle
ensuite une fois par joueur
`generaux.faire_apparaitre_general_si_possible()`. La génération conserve sa place
avant l'audit : un seul général par joueur et par tour, aucun si le home contient
déjà un général ou si cinq généraux ont déjà été générés. Réparer plusieurs fois
la structure ne provoque aucune génération.

### Mode Survie

Le mode Survie sépare la **fenêtre d'action temporisée** de la **résolution d'un
tour**. La fenêtre dure **120 secondes** par défaut, y compris au tour 0. Le champ
`duree_phase_action_secondes` du profil, ou l'option `--duree-action`, permet une
durée finie positive ou nulle. Une durée de 0 supprime l'attente des nouvelles
fenêtres ; elle ne réinitialise pas l'échéance d'une fenêtre déjà ouverte.

Les API du cycle vérifient d'abord l'absence de territoires et de rapports
territoriaux classiques sur le plateau dédié. Un mélange est refusé sans supprimer
de données. `rapports.afficher_fin_de_tour(configuration=None)` reçoit le profil
Survie pour produire son exemple de consultation ; sans profil, le comportement
classique est conservé. Aucun chemin ou exemple classique n'est produit en Survie.

Les anciennes structures visibles sont aussi refusées avant écriture. Le dossier
technique commun est `.systeme/`. L'accueil Survie est publié sous
`village/<joueur>/hotel_de_ville/` : deux journaux passifs des vagues 0..10, Courrier
acceptant `FLAG <flag>`, bestiaire progressif et copie du rapport court finalisé. Le Clocher commun est
`village/clocher/` ; il reste attaché au cycle vivant et exclu des captures. La
publication du village conserve ses inodes, notamment le journal suivi avec `tail -f`.

Les modèles sont conservés dans `python/textes/journal_du_Toonitruand/` et
`python/textes/journal_du_veteran/`. `plateau.preparer_journaux()` utilise la même
publication pour les deux niveaux : elle remplace `{joueur}` et `{game_path}`
(racine publique configurée) et crée uniquement
les fichiers manquants des vagues 0 à la vague atteinte, plafonnée à 10. Les chemins
des commandes restent les chemins Linux publics, même dans une génération privée.
Les fichiers déjà débloqués ne sont ni supprimés ni réécrits. Une reprise complète
les conseils manquants sans rejouer la préparation des généraux ni modifier l'échéance.
En ACTIONS, la vague atteinte est `tour` ; en CONSULTATION ou après défaite, elle
est `tour + 1`, puisque la résolution de ce tour est terminée.
Le message d'accueil propose les deux fichiers `vague_0.txt`, avec les niveaux
« Débutant » (Toonitruand) et « À l'aise avec Linux » (Vétéran).

Les mini-défis sont décrits dans `SURVIE_SPEC.md`. Leur état privé `defis.json`
fait partie de `config.ETATS_METIER`. Le pilote de cycle relève le Courrier
toutes les dix secondes pendant ACTIONS et une dernière fois sous gel de capture.
Une décision est persistée avant sa réponse. La récompense est créée dans la
génération privée via `crypte.attribuer_recompense()`, avec numéro canonique et
sans consommation du quota normal ni du cooldown des recettes. Les deux états
privés sont publiés avec le plateau ; une republication ne rejoue pas l'attribution.

L'accès aux lieux conquis utilise le camp du contrôle publié et
`configuration['groupes_camps']` (camp → groupe Unix). En Survie, `allies` désigne
`mythodea_allies` ; le bot n'a aucun groupe joueur autorisé. Les groupes des
sessions déterminent les lecteurs, sans test sur un nom de joueur individuel.
Neutre et contesté n'autorisent aucun groupe. Les droits de la cabane sont posés
à sa création puis recalculés sous gel après installation complète de la
publication, y compris administrative ; ils restent stables pendant ACTIONS.

Responsabilités des API :

- `minuterie.valider_duree()` valide la durée ;
  `minuterie.attendre_jusqua(echeance, horloge=None, dormir=None, observer=None)` attend une
  échéance absolue, avec `time.time` et `time.sleep` par défaut. Ce module n'importe
  pas le moteur et ne déclenche aucune action de jeu. L'horloge et l'attente sont
  injectables pour les tests ; une échéance déjà atteinte ne provoque aucune attente.
  L'observateur facultatif reçoit le temps restant, sans introduire de règle de jeu.
- `survie.ouvrir_tour_survie(configuration=None, horloge=None)` prépare le plateau,
  fait apparaître un général par joueur si possible selon les limites communes,
  complète les ordres de surnombre et enregistre la fenêtre d'action. Si elle est
  déjà ouverte, il conserve son échéance sans répéter la préparation. Il n'attend pas.
- `survie.resoudre_tour_survie(configuration=None, aleatoire=None, gestion=None)`
  clôture une fenêtre ouverte : capture sous gel, résolution privée par le moteur
  commun, puis publication sous un second gel. Il ouvre la consultation ou constate
  la défaite. Il n'attend pas l'expiration du timer d'action ; les tests l'appellent
  directement avec un contrôleur de gel et des horloges injectés, sans attente réelle.
  Le minimum de gel réel reste appliqué en production. Il n'ouvre pas les actions suivantes.
- `survie.lancer_partie_survie(configuration=None, nombre_tours=None, horloge=None,
  dormir=None)` pilote l'ouverture, l'attente, la résolution, l'affichage du rapport
  et l'ouverture suivante. Il s'arrête à la défaite, à une interruption ou après le
  nombre demandé de résolutions. À cette limite, il laisse la phase `consultation`
  persistée ; le prochain appel attend son échéance puis prépare le tour suivant.

Après clôture par capture, la résolution du tour N travaille exclusivement dans
la génération privée. L'orchestrateur :

1. appelle l'audit commun une seule fois ;
2. prépare et applique les déplacements automatiques des forces ennemies déjà
   présentes ;
3. effectue les contrôles supplémentaires sans rejouer les effets de l'audit ;
4. matérialise entièrement la vague `N + 1` dans l'ordre `est_3 -> est_2 -> est_1`,
   sans déplacement supplémentaire, puis détecte les conflits ;
5. résout les cascades dans l'ordre `village -> est_1 -> est_2 -> est_3`, réserve
   les retraites admissibles et les applique physiquement après tous les combats ;
6. tente un rattrapage pour les seuls survivants bloqués avant combat, si le bot
   contrôle maintenant leur origine ; aucune deuxième avance pour les forces déjà
   déplacées, ni déplacement des nouvelles apparitions, ni combat supplémentaire ;
7. sauvegarde le contrôle final, les rapports et l'éventuelle défaite ;
8. publie de nouveaux inodes puis, en l'absence de défaite, ouvre la consultation
   de 60 secondes et ensuite le tour suivant avec un nouveau timer de 120 secondes.

Le pilote Survie héberge aussi le collecteur Crypte pendant les fenêtres d'action.
Il reçoit des observations Bash, authentifie l'UID par le noyau et conserve les
décisions dans `.systeme/crypte.json`, privé `root:root 600`. Une réussite acceptée
enregistre ensemble son tour, son identifiant et le cooldown, sans créer de général
sur le plateau vivant. À la clôture, les nouvelles demandes sont refusées ; sous
gel, les tentatives inachevées sont invalidées et les ateliers nettoyés avant copie.
Les récompenses acceptées sont matérialisées à la fin de la résolution privée,
puis publiées avec les autres états métier. La récupération administrative republie
les résultats terminés et ne réexécute pas la recette ni son attribution.

`crypte.json` et les deux compteurs de créations normales font partie de
`config.ETATS_METIER`. La configuration `crypte_config.json`, le socket et les
tentatives en mémoire restent attachés au moteur vivant et ne sont pas publiés.
Les règles de recette, permissions et récupération sont définies dans
`SURVIE_SPEC.md`, section « Crypte V0.1 ».

Les déplacements automatiques sont préparés depuis un inventaire initial des
actifs et renforts bots, en tenant compte des départs prévus, puis appliqués.
Une présence alliée active à l'origine bloque le départ de la colonne ; les
identités bloquées sont distinguées des forces ayant déjà avancé. Les arrivants
rejoignent la colonne restée sur place, derrière ses occupants.
Le cycle appelle séparément `avancer_ennemis()` et `creer_vague_est(N + 1, ...)`.
Les contrôles intermédiaires utilisent `securite.controler_coherence_territoires()`
sans rejouer l'audit, la fatigue, les sanctions ou l'attente de repli.

Le tour 0 utilise le même principe : l'audit est exécuté, aucun ancien ennemi ne
se déplace puisqu'il n'en existe pas encore, puis la vague 1 est créée et les
éventuels combats sont résolus.

`survie.preparer_phase_ennemie()` reste une fonction de phase ennemie et non un
cycle complet : elle réalise la progression des anciennes forces puis l'apparition
de la vague demandée. Un appel isolé ne doit pas être précédé d'une progression
automatique des mêmes forces. Cette fonction ne gère ni le timer, ni l'audit joueur,
ni les combats, ni le contrôle final, ni le passage au tour suivant.

### État persistant et reprise du cycle Survie

`etat.charger_cycle_survie()` et `etat.sauvegarder_cycle_survie()` utilisent
`/game/.systeme/cycle_survie.json`. Ce fichier privé appartient à `root:root`
en `600`. L'écriture passe par `cycle_survie.tmp`, également privé, puis remplace
atomiquement le fichier d'état. Celui-ci contient `tour` (entier à partir de 0),
`phase` et, en phase `actions` ou `consultation`, `echeance` (secondes depuis
l'époque Unix). `generation` identifie la clôture en cours ; `generation_active`
identifie la dernière publication validée. `erreur` explique une récupération.
Le numéro de vague est déduit de `tour + 1`, sans compteur supplémentaire.

| Phase | Signification |
| --- | --- |
| `preparation` | Préparation du tour en cours, avant l'ouverture de sa fenêtre. |
| `actions` | Fenêtre ouverte ; son échéance est enregistrée. |
| `capture` | Clôture commencée ; gel et copie des entrées, pas encore de résolution. |
| `resolution` | Moteur commun actif exclusivement dans `travail/`, joueurs dégelés. |
| `publication` | Installation journalisée des nouveaux inodes sous gel court. |
| `consultation` | Publication validée ; lecture pendant 60 secondes, `tour` reste le tour résolu. |
| `a_preparer` | Consultation terminée ; `tour` désigne le prochain tour à préparer. |
| `recuperation` | Incident bloquant ; intervention administrative requise. |
| `defaite` | Partie arrêtée ; `tour` reste celui dont la résolution a provoqué la défaite. |

Sans fichier d'état, l'ouverture commence au tour 0. Après une interruption pendant
un timer, le pilote reprend `actions` ou `consultation` et attend seulement le
temps restant ; si l'échéance est dépassée, il poursuit la transition correspondante.
Le temps écoulé pendant l'arrêt n'est pas ajouté à la fenêtre.

Une phase `preparation`, `capture`, `resolution`, `publication` ou `recuperation`
bloque la reprise automatique. Le journal de gel est aussi bloquant. Une vérification
administrative est nécessaire : aucun retour arrière, audit, vague ou combat n'est
rejoué automatiquement. Les journaux et générations sont conservés pour l'examen.

`etat.verrou_cycle_survie()` crée exclusivement
`/game/.systeme/verrou_cycle_survie` (`root:root`, `600`), qui contient le PID.
Le pilote le garde pendant toute son exécution, y compris l'attente ; les appels
directs d'ouverture et de résolution prennent aussi ce verrou. Sa présence refuse
un second moteur Survie. Il est retiré à la sortie, y compris sur exception ou
`Ctrl+C`. Après un arrêt brutal empêchant ce nettoyage, il faut vérifier l'absence
du processus avant de retirer manuellement le verrou résiduel.

Ce verrou exclut les autres moteurs. La protection contre les écritures joueurs
repose sur `cycle_linux.py` : gel confirmé des slices systemd des deux UID pendant
la capture, copies physiques indépendantes, résolution privée, puis publication
sous un second gel. `chmod` et les ACL seuls ne révoquent pas un descripteur déjà
ouvert ; ils ne suffisent donc pas à clôturer le tour.

`config.racines_generation()` borne les accès métier du moteur commun à la racine
de travail et aux homes capturés, sans modifier les variables globales classiques.
Les états passent par `config.chemin_etat()`/`racine_metier()` ; la découverte des
homes passe par `home_generation()`. Rapports, verrou, Clocher et récupération
restent attachés au moteur vivant. Aucune lecture métier ne revient au plateau public.

Les données capturées gardent leurs UID/GID réels pour l'audit, sous un ancêtre
`root:root 700`. Les métadonnées moteur sont `root:root 600`. Les rapports alliés
et le Clocher utilisent `root:mythodea_allies`, dossiers `750`, fichiers `640` ;
le journal technique reste `root:root 600`. Les homes eux-mêmes restent aux joueurs.
Le format des générations, la publication et la procédure de récupération sont
décrits dans `SURVIE_SPEC.md` et `TESTS_LINUX_SURVIE.md`.

---

## 18. Tests

La suite de développement se lance depuis la racine :

```bash
python3 -B -m unittest discover -s .dev/tests -v
```

Les tests couvrent notamment combats, manœuvres, mouvements, progression,
étiquettes, QG, permissions simulées, cycles Survie, retraites et reprises.
Ils utilisent des plateaux temporaires et ne remplacent pas les contrôles
avec de vrais UID/GID sur Linux.

Les procédures Linux, tests root et préparations sur Raspberry Pi sont
décrits dans [TESTS_LINUX_SURVIE.md](TESTS_LINUX_SURVIE.md).

---

## 19. Réutilisation du moteur commun

Les modes classique et Survie réutilisent les mêmes règles de généraux,
mouvements, combats, étiquettes, commandement et rapports. Le mode Survie
n'ajoute que son cycle, ses vagues, ses bots et ses objectifs propres,
décrits dans [SURVIE_SPEC.md](SURVIE_SPEC.md).

---

## 20. Historique des versions

La V1.5 est l'origine du moteur classique. En v2.0, les anciens ordres
de combat sont remplacés par les étiquettes et le commandement de
[REGLES_V2.md](REGLES_V2.md). `ordre_surnombre.txt` reste une décision
de retraite/poursuite propre au mode Survie.

Les évolutions historiques sont consultables dans l'historique Git.
La validation avec de vrais comptes SSH, UID/GID et permissions sur Raspberry Pi
reste distincte des validations sous WSL.

---

## 21. Invariants à ne pas modifier silencieusement

Sans décision explicite, ne pas changer :

- carte classique ;
- chemins sous `/game`, `/home/j1`, `/home/j2` ;
- structure des généraux et unités ;
- permissions 700/600 ;
- identité officielle des généraux ;
- limites officielles de capacité des unités et de création des généraux ;
- sanctions anti-duplication / emplacement ;
- règles de mouvement et marche forcée ;
- triangle archer/piquier/cavalier ;
- comportement de fatigue ;
- priorités de MANŒUVRE ;
- ordre des généraux en combat rangé ;
- OFF/OFF et OFF/DEF ;
- formats des fichiers d'état ;
- formats et terminologie des rapports ;
- règles de victoire.

Cette spécification décrit le comportement à préserver. Les règles futures
ne deviennent applicables qu'après validation explicite.

---

## 22. Progression commune, blessures et formation

### Identifiants et fabrication

`catalogues.py` est la source des recettes et des identifiants reconnus.
Les identifiants sont universels, permanents et ne doivent jamais être recyclés.

| Type générique | ID unité | ID d'évolution | Référence de fabrication | Valeur de combat |
| --- | --- | --- | --- | --- |
| Archer | 1 | 101 | 5 | 5 |
| Piquier | 2 | 102 | 5 | 5 |
| Cavalier | 3 | 103 | 5 | 5 |
| Cavalerie lourde | 4 | 104 | non définie | 5 |

Le moteur ne possède pas de comptabilité de fabrication. La référence de
fabrication reste une donnée documentaire, sans monnaie, distincte de
`valeur_combat`. Le combat utilise l'échelle individuelle de la section 11,
avec triangle, fatigue et formation lourde conservés. Les recettes et effectifs
ne changent pas. Les étiquettes
multiples ne créent pas de types supplémentaires. Les emplacements de futures
règles de terrain, positionnement ou restrictions ne produisent aucun effet.

Les évolutions 201 et 202 désignent respectivement le gain de +5 à +10 PC et de
+2 à +4 moral. Les unités déblocables portent les IDs 104 à 110 ; la technologie
de Forge 104 autorise une transformation, sans création de soldat. Les IDs
d'ordres 1001 à 1005 sont retirés et restent réservés. Les étiquettes scolaires
portent les IDs 2001 à 2012. Le catalogue complet et les règles d'accès sont
définis dans `catalogues.py` et `REGLES_V2.md`.

### Caractéristiques et niveaux des généraux

La référence unique pour les probabilités de nature, de trait, les gains
naturels, les paliers, la roulette, les étiquettes et la progression zombie
est [REGLES_V2.md](REGLES_V2.md). Les capacités croisées des hybrides,
les rangs scolaires et les plafonds d'activation y sont définis.

La création conserve les natures `stratege`, `instinctif`,
`stratege_hybride` et `instinctif_hybride`. Nature, dominante et trait inné
sont persistants. Les champs `niveau`, `nature`, `orientation_principale`,
`trait_inne`, `points_commandement`, `moral`, `evolutions_acquises`,
`evolution_apprise`, `progression_combat`, `progression_formation` et `etiquettes`
sont visibles dans `fiche.txt`. Le profil privé
`.systeme/progression.json`, indexé par `joueur:generalN`, fait autorité :
modifier la fiche du joueur ne change pas les statistiques officielles.
La liste privée `etiquettes_apprises_ecole` compte les nouvelles acquisitions
scolaires pour le quota, sans verrouiller leurs rangs. Les attributions automatiques
en sont exemptées. À la lecture d'un ancien profil, les anciennes listes et reçus
identifient ces exemptions ; une origine introuvable compte comme scolaire.
Tous les noms et rangs acquis restent conservés, même si le quota est dépassé.
La normalisation est sans écriture à la lecture ; les sauvegardes suivantes
retirent les anciennes clés. Voir les règles de compatibilité dans `REGLES_V2.md`.

Deux jauges indépendantes déclenchent les niveaux :
- **Combat** : un point par bataille territoriale personnellement combattue
  et survécue, cascades comprises. Deux points donnent un niveau.
- **Formation** : un point à chaque clôture où le général est présent dans
  la caserne militaire (dossier `village/<joueur>/caserne_militaire/`), y compris
  lors de son tour d'entrée. Trois points donnent un niveau.

Seule la jauge déclenchée revient à zéro. Les formations sont traitées avant
les combats. `valider_evenement` conserve atomiquement jauges, niveau,
récompenses et reçus privés `progressions_validees` dans `progression.json`.
Les clés de validation incluent `formation:<tour>:<joueur>:<generalN>`
et `combat:survie:<tour>:<territoire>` ; le profil suit ses propres reçus.
Une répétition d'événement ne donne pas une nouvelle récompense et peut
réparer la fiche visible après interruption.

Une mémoire de l'École remplace la prochaine roulette applicable et reste
en attente lors d'un palier garanti. Les tirages automatiques sont séparés
du générateur des combats. La reprise d'un cycle Survie interrompu pendant
la résolution exige une récupération administrative sans rejouer les combats.
Un tour classique interrompu n'a pas de reprise automatique.

### Étiquettes actives, commandement et QG

Les rangs appris restent dans `progression.json`. `etiquettes_actives.txt`, dans
le dossier du général, contient uniquement les noms exacts sélectionnés, séparés
par lignes ou virgules. Un fichier vide désactive tout ; son absence active les
étiquettes connues dans la limite applicable. Doublons, noms non appris et
dépassements des limites trois/un selon l'orientation sont refusés.

`combats._contexte_qg_territorial()` ouvre un instantané de sélection via
`progression.figer_selections_territoriales()` avant les duels. Il couvre choc,
manœuvre, frontal, rangé et toute la cascade Survie. Un renfort fige son choix à
son premier engagement ; une lecture de capacité ne le fige pas. La sortie,
même sur exception, restaure le contexte précédent. La bataille suivante relit
les choix. L'instantané est transitoire et n'introduit aucun format persistant.

`QG.txt` ou `qg.txt` désigne le QG, quelle que soit sa nature ; plusieurs QG du
même camp annulent son soutien. Les PC globaux et les effets des seules étiquettes
actives sont figés depuis les participants initiaux. Un Messager occupe cinq
places, ne combat pas, et ajoute une seule fois `somme(PC des autres alliés) // 10`
aux PC globaux. Réserves, homes, bâtiments et renforts non engagés sont exclus.
Les renforts ultérieurs reçoivent le soutien existant sans nouveau calcul.

Chaque effet vaut `PC × 1/2 × rang` en points de pourcentage. Les bonus et malus
compatibles s'additionnent ; le niveau du général n'est pas un second multiplicateur.
Le QG ne reçoit pas sa propre copie globale ; ses effets personnels utilisent
ses PC personnels. Sa destruction ou l'acceptation de sa retraite de surnombre
retire immédiatement ses bonus et malus globaux pour toute cette bataille,
avant même un déplacement physique différé. Aucun remplaçant n'est désigné et
aucun renfort ni Messager ne réactive ces effets. Les effets personnels des autres
généraux restent actifs ; une retraite refusée conserve le soutien. La cascade
appelle `combats.desactiver_qg_retraite()` pour les seules retraites acceptées.
Les détails, notamment `chaman` et `cruelle`, sont dans `REGLES_V2.md`.

Les choix de combat exigent des fichiers ordinaires sans liens symboliques ou
physiques. `cycle_linux.copier()` les contrôle avant copie, pour ne pas effacer
la preuve du lien. La lecture de sélection contrôle aussi l'inode ouvert et sa
stabilité ; sous Linux, l'ouverture refuse le suivi d'un lien et ne bloque pas
sur un FIFO substitué. Le gel et l'isolement privé du cycle Survie restent applicables.

### Blessures et batailles complètes

Les généraux zombies et les unités zombies ne bénéficient ni du moral ni des
soins. Les anciennes valeurs de moral et de blessures restent enregistrées,
mais ne permettent aucun sauvetage ni restauration des blessures zombies,
y compris à l’Hôpital et par le Chaman. Les PC et les étiquettes compatibles
restent applicables. Spore (conversion), Propagation (création) et la caserne militaire
territoriale du Bouclier vivant conservent leurs règles spécifiques.

Après chaque choc de blocs et chaque manœuvre, les pertes sont sélectionnées
comme auparavant. Un instinctif, instinctif hybride ou stratège hybride disposant
de moral tire `pertes * moral // 100` candidats distincts
parmi ces pertes. Chaque candidat sous sa limite de blessures est conservé et
reçoit une blessure. Une tentative échouée n'est pas réattribuée. Les autres
pertes sont supprimées ; listes, effectifs et rapports sont actualisés avant
l'affrontement suivant. Les blessés combattent sans pénalité supplémentaire.

| Batailles survécues | Statut | Blessures maximales |
| --- | --- | --- |
| 0 à 4 | ordinaire | 1 |
| 5 à 9 | vétéran | 2 |
| 10 et plus | héroïque | 3 |

Une bataille complète correspond à toute la résolution d'un territoire pendant
un tour, frontal, rangé et cascades compris. Les unités des généraux effectivement
engagés sont suivies ; leurs survivantes gagnent une seule bataille, sans condition
de victoire. Les unités de caserne militaire non engagées ne gagnent rien. Le gain est appliqué
en fin de résolution territoriale : le nouveau statut ne change pas rétroactivement
la limite de blessures des affrontements déjà résolus. Les retraites Survie sont
différées jusqu'après ce comptage. L'ID Survie `survie:<tour>:<territoire>` empêche
un double comptage ; le classique crée une identité unique par résolution.

Le suivi est créé au premier sauvetage, comptage ou séjour à l'hôpital. Le dossier
contient `identifiant_soldat.txt` (UUID stable), `batailles_survecues.txt`,
`blessures.txt`, et les marqueurs `veteran` / `heroique` selon les seuils. Un
héroïque conserve aussi son marqueur vétéran. Ces copies restent privées au joueur
en 600 et ne sont jamais l'autorité.

`.systeme/soldats.json` conserve par UUID le type, les compteurs, le chemin logique,
les identités de périphérique/inode, les batailles déjà comptées, la dernière
bataille et, au besoin, la destruction, le dernier soin ou le séjour de Forge
validé (`forge`). Une transformation met à jour le type sans changer l'UUID.
Les inodes vivants
authentifient les soldats avant capture Survie ; les UUID privés sont reliés aux
nouveaux inodes à la publication. Le classique synchronise avant l'audit des
déplacements. Modifier un compteur visible ne soigne pas et ne confère aucun statut.
Une copie ne peut récupérer les droits de l'original présent. Les soldats détruits
restent marqués dans le registre.

Les transferts gardent leurs restrictions : bloc homogène, pas d'écrasement de
nom, droits requis, plafonds d'effectifs et audit d'entraînement. Le suivi n'accorde
aucun droit de renforcement supplémentaire. Un déplacement conservant l'inode
garde l'état ; entre systèmes de fichiers, le marqueur d'identité doit accompagner
le dossier complet. Une récupération ambiguë sans marqueur peut nécessiter une
intervention explicite, sans remise à zéro silencieuse des blessures connues.

### Hôpital, École et Forge du village

Les bâtiments sont actifs dans le village Survie ; le mode classique réutilise
les fonctions sans ajout de lieux à sa carte. L'hôpital conserve les dossiers
`village/<joueur>/hopital/1..20`, avec places logiquement partagées entre alliés.
L'École a exactement six dossiers physiques `village/ecole_officiers/1..6` ; la
Forge un seul, `village/forge/1`. Chaque place commune contient un compartiment
privé `<joueur>/` : un seul général peut occuper la place, tous joueurs confondus.
Les parents communs sont `root:<groupe_allie> 750` ; les compartiments et généraux
restent possédés par leur joueur, en 700 (fichiers 600).
Les 20 places d'hôpital sont configurables par `emplacements_hopital` ; il n'existe
aucun autre quota de soins simultanés. L'École a six places de généraux, distinctes
des trois emplacements de son manuel. Les collisions appliquent la sanction commune
d'emplacement, indépendamment des places de garnison. Les bâtiments sont hors combat.

Les anciens dossiers d'École sont transférés sous gel par renommage, sans
écrasement ni recréation d'identité. Une destination ambiguë interrompt la migration
pour récupération. Un séjour traversant une migration doit recommencer un tour
complet. Capture et publication incluent les deux bâtiments communs ; le Clocher
reste préservé. Les phases de consultation/actions couvrent leurs compartiments privés.

Entrer ou sortir d'un bâtiment est une réorganisation interne au village, sans
déplacement normal. Se déplacer entre le village et un autre territoire conserve
les règles existantes. Les bâtiments n'accordent pas de droit d'entraînement.

Sous gel avant ACTIONS, le moteur enregistre les demandes et les preuves de
présence. Sous gel de clôture, il relève les présences finales. Périphérique,
inode et ctime du général et de sa place doivent rester identiques ; les unités
d'hôpital et de Forge ont aussi leurs propres preuves. À la Forge, les équipements
doivent également être présents et inchangés pendant le tour. Une entrée tardive, sortie/retour ou
substitution invalide le séjour concerné. Modifier une demande pendant ACTIONS
ne remplace pas celle du début. Une reprise ne réinitialise pas le début du séjour.

La formation en caserne militaire utilise les mêmes relevés et validations. Comme plusieurs
généraux partagent ce dossier, sa preuve conserve le périphérique et l'inode du
parent, mais pas son ctime : l'arrivée d'un voisin n'annule pas le séjour.
Le ctime du général lui-même reste contrôlé pour détecter sa sortie et son retour.
Une arrivée pendant ACTIONS ne donne pas de point de formation pour ce tour.

Après l'audit de la génération privée, les soins valides remettent les blessures
à zéro sans toucher aux batailles ni aux statuts. Toutes les unités admissibles
de tous les généraux présents sont traitées. Une validation consommée ne peut
soigner une nouvelle blessure.

Les demandes personnelles sont `ecrire_ses_memoires.txt` (`e 001 201`) et
`lire_les_memoires.txt` (`a 001 201`). Les actions acceptent les majuscules. La
syntaxe historique `001 201` pour écrire et `001` pour lire reste acceptée.
Une lecture non vide prime sur l'écriture, même si cette lecture est invalide.
L'écriture d'une évolution nécessite son acquisition et remplace l'emplacement
choisi. Pour les étiquettes scolaires, toutes les origines sont acceptées et
le contrôle n'exige pas la connaissance préalable ; cette condition reste une décision
ouverte dans `REGLES_V2.md`. Le manuel partagé par camp
a exactement `001`, `002`, `003`, avec `vide` pour un emplacement libre.

Toutes les lectures valides du tour précèdent toutes les écritures. La lecture
vérifie l'emplacement et l'ID demandé, puis mémorise l'ID réel, sans consommer le
manuel. Une écriture ultérieure ne modifie pas cet apprentissage. L'ID remplace
la roulette à la prochaine montée compatible ; s'il devient incompatible, la montée
est refusée sans perte d'état. Deux écritures concurrentes au même emplacement
sont refusées ensemble, sans choisir un gagnant implicite. Le remplacement d'un
apprentissage encore en attente reste refusé tant que sa règle n'est pas définie.
Le résultat individuel est écrit dans `formation_resultat.txt`, jamais dans le
rapport public. Une lecture d'étiquette l'apprend ou améliore directement son rang
à la fin du séjour, selon les plafonds de `REGLES_V2.md`, sans remplacer une mémoire
d'évolution en attente.

`.systeme/formation.json` conserve les manuels par camp, séjours par
`tour:joueur:generalN`, tours ouverts, relevés de clôture et validations consommées.
Le profil conserve les apprentissages validés pour prévenir un double traitement.
Le manuel visible est `village/ecole_officiers/memoire_des_generaux.txt`, publié
`root:<groupe_allie> 640` dans un dossier 750. Aucun `chattr` n'est utilisé.

Les trois nouveaux JSON utilisent l'écriture privée atomique existante, en 600,
et font partie de `ETATS_METIER` : ils accompagnent capture et publication.
Leur absence dans une ancienne sauvegarde signifie absence de suivi, sans
effacement ni attribution rétroactive. Sauvegarder les états privés avec les unités
est indispensable à la conservation de cette autorité. Voir `EVOLUTIONS.md` pour
l'utilisation et les décisions de conception encore ouvertes.

### Transformation à la Forge

Le général doit avoir une orientation principale instinctive et posséder l'évolution
104 dans son profil officiel. Un stratège hybride ne peut pas fabriquer, même
après avoir appris cette évolution. Après un tour complet, les cavaliers légers
existants possédant `cheval`, `cuirasse`, `armure`, `casque`, `bouclier` sont renommés
par le moteur en `cavalerie_LN`. Aucun coût ni ressource supplémentaire n'est ajouté.
L'unité doit figurer dans la référence officiellement publiée au tour précédent
de `unites_actions.json`. Sous gel d'ouverture, les signatures du cavalier et
de son cheval sont rapprochées de cette référence ; les créations du tour courant
sont exclues. Les UUID admissibles sont figés dans `eligibles_forge` du séjour.
Le simple relevé d'entrée, une copie d'UUID ou une recette complète ne valident
pas l'ancienneté. Un renommage ou déplacement conservant les identités physiques
préserve l'éligibilité ; une copie ne la crée pas. Un transfert entre partitions
sans correspondance d'identité attend la prochaine publication officielle.
Un ancien séjour sans liste d'éligibilité ne transforme aucune unité.
Une collision choisit le prochain numéro libre sans écraser l'existant. La recette
doit être constituée de fichiers ordinaires sans liens.

Les fichiers, UUID, batailles, blessures et statuts sont conservés ; seules les
données de type et de localisation changent dans le registre privé. Une recette,
autorisation ou présence invalide ne supprime pas l'unité. Une conversion validée
apparaît dans le rapport court du tour ; le résultat du séjour est aussi individuel.
Les refus par cavalier sont expliqués dans le rapport long ; le résultat individuel
signale un séjour sans transformation. L'audit commun des créations illégales reste
distinct : un refus de Forge n'autorise pas le recrutement dans un bâtiment interdit.
Une unité déjà lourde n'est pas transformée à nouveau. Le combat réutilise les
valeurs de cavalerie lourde déjà définies, sans nouveau multiplicateur. En cas de
conversion partielle d'un bloc, réorganiser ses types avant déploiement : les règles
historiques de nettoyage des blocs de combat homogènes restent applicables.
