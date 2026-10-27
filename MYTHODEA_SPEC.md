# Mythodea V1.5 — Spécification de référence

Ce document décrit **l'état actuel utile de Mythodea** : règles, formats persistants,
architecture et invariants. Il ne sert pas de journal de modifications.

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
├── TESTS.md
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
| `commandement.py` | calculs entiers, sélection des QG et donneurs d'ordres, sans effets tactiques supplémentaires |
| `ordres_pipeline.py` | intentions authentifiées, confrontation et effets temporaires des ordres intégrés dans les duels |
| `ordres_calculs_v2.py` | formules pures des ordres ; un calcul seul ne rend pas un effet disponible |
| `ordres_conception.py` | registre documentaire immuable, sans droit d'apprentissage ou d'exécution |
| `soldats.py` | identité individuelle, blessures, sauvetages, batailles survécues et vues de participation temporaire |
| `formation.py` | formation en réserve, hôpital, École et Forge, séjours, mémoires et transformations |
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
`emplacement` ; une réserve n'en porte pas. Seules les places actives `1..4`
participent à la lecture des forces engagées. En Survie, les renforts alliés
`territoire/joueur/renforts/5..20`, uniquement hors village, sont découverts et audités comme les autres
généraux, avec leurs propriétaires séparés. Ils restent distincts de la réserve.

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
village, `20` ailleurs) rejoint la réserve de son joueur si l'arrivée est le village.
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
├── fiche.txt
└── ordre.txt
```

Limites actuelles :

```text
20 unités maximum par général
5 créations normales maximum par joueur
```

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

Champs historiques conservés :

```text
nom=general1
orientation=stratege
strategie=0
force=0
experience=0
```

Orientations connues :

```text
stratege
combattant
hybride
```

Les effets futurs de `strategie`, `force` et `experience` ne doivent pas être
inventés tant qu'ils ne sont pas définis.

Les nouvelles créations ajoutent les caractéristiques de la section 22.
`orientation` reste un champ historique distinct de `nature`.

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
le home et la réserve. Il vérifie l'attribution privée du général récompense et
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
réserve/garnison. Depuis home, un général nouvellement créé ou déjà enregistré
dans la référence officielle précédente peut créer ses unités puis accéder
immédiatement aux places et bâtiments autorisés du village, sans mouvement
territorial. Le droit vaut aussi pour un général vide. La validation commune
de sortie du home reste obligatoire : aucun saut direct vers un front, ni
exemption des contrôles d'identité ou de collision. Les séjours complets des
bâtiments et l'attente après entraînement en réserve restent applicables.

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
strictement positif. Les booléens, flottants, chaînes, valeurs nulles ou négatives
sont refusés. Les quatre types actuels ont une valeur de 5 : archer, piquier,
cavalier et cavalerie lourde. Ce champ est indépendant de `fabrication`, et
n'est jamais lu dans les fichiers modifiables du général ou des soldats.

Pour un bloc homogène de `n` unités encore présentes, la puissance de base est
`n * valeur_combat`. Dix archers valent donc 50, vingt archers 100. Le moteur
relit les survivants avant chaque affrontement ; un bloc vide a une puissance
nulle et un affrontement avec un bloc vide ne produit aucune perte.

La valeur effective individuelle est calculée ainsi :

```text
vA = valeur_combat_A * formation_A * avantage_A * fatigue_A
vB = valeur_combat_B * formation_B * avantage_B * fatigue_B
puissance_A = effectif_A * vA
puissance_B = effectif_B * vB
pertes_A = min(effectif_A, puissance_B // vA)
pertes_B = min(effectif_B, puissance_A // vB)
survivants_A = effectif_A - pertes_A
survivants_B = effectif_B - pertes_B
```

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

### Ordre frontal `1-2`

Lorsque l'attaque frontale est déclenchée, les emplacements correspondants
s'affrontent d'abord :

```text
1 contre 1
2 contre 2
3 contre 3
4 contre 4
```

Les survivants passent ensuite au **COMBAT RANGÉ**.

L'annulation des formations incompatibles d'un même camp est préalable. Si
`1-2` s'oppose à On_melange dans l'autre camp, les donneurs QG et leurs PC
globaux départagent ces schémas avant le premier duel : victoire du plus fort,
annulation des deux à égalité. Dans ce cas, une demande historique sans donneur
QG autorisé ne peut imposer le frontal. Hors de cette opposition précise,
le déclenchement historique est conservé. QG_nommade exclut son porteur des
couples frontaux, sans déplacer son vis-à-vis ni combler l'emplacement vacant.

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

---

## 14. Ordres des généraux

Format de `ordre.txt` :

```text
type-numero
```

ou :

```text
type-numero-specification
```

La V2 réserve aussi `2-6-position_beneficiaire-position_preteur` pour Gros_poisson.
Les quatre champs sont lus uniquement pour ce jeton, sans activer son effet.

Ordres enregistrés :

| ID | Nom interne | Catégorie | État V1.5 |
| --- | --- | --- | --- |
| `1-1` | `retraite_apres_premiere_manche` | armée | réservé à une version ultérieure |
| `1-2` | `attaque_frontale` | armée | implémenté |
| `2-1` | `attaque_chirurgicale` | formation | réservé à une version ultérieure |
| `2-2` | `pluie_de_fleches` | formation | réservé à une version ultérieure |
| `3-1` | `fuir_avant_la_mort` | intrinsèque | réservé à une version ultérieure |

Un ordre inconnu, mal écrit ou non applicable est ignoré.
Son texte personnel n'est pas recopié dans les rapports, y compris dans les
diagnostics d'erreur. Les effets observables d'un combat restent rapportés.

La V1.5 n'a pas pour objectif de finaliser tout le système d'ordres. Les règles
détaillées des ordres supplémentaires seront définies plus tard à partir de
l'expérience de jeu et d'un document de design validé. Ne pas les inventer.

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

Les rapports sont préparés dans `generation/rapports/`, privé root, avec le
flux chronologique `evenements.jsonl`. Ils ne remplacent les rapports publics
qu'à la publication sous gel. `rapport_long.txt` reste privé root `600` ; les
rapports territoriaux et le journal sont lisibles par le groupe allié en `640`.

Le journal `/game/rapport/suivi_combats.log` conserve son inode pour `tail -f`.
Le plan privé `.systeme/diffusion_rapports.json` contient la génération, l'heure
de début, l'intervalle, la position initiale, le device/inode du journal et les
événements. Il est durable avant le premier append. Pendant CONSULTATION, le
minuteur publie les octets manquants ; le préfixe exact permet de reprendre une
écriture interrompue, même au milieu d'un caractère UTF-8. Une divergence exige
une récupération et n'est jamais effacée automatiquement. La republication
d'une génération ne redémarre pas sa diffusion.

`delai_evenements_combats_secondes` est optionnel (1 seconde par défaut, zéro
pour les tests) ; il est réduit si nécessaire pour finir pendant la consultation.
La défaite termine immédiatement la diffusion. Aucun délai ne ralentit le calcul
privé et les intentions/PC détaillés ne sont pas inclus dans le flux public.

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

Suite actuelle :

```bash
python3 -B -m unittest discover -s .dev/tests -v
```

La suite conserve les 32 tests de régression V1.5 couvrant notamment :

- priorité globale de la manœuvre ;
- avant libre et flancs ;
- transition frontal -> combat rangé ;
- ordre des généraux par emplacement ;
- mouvements des deux joueurs ;
- marche forcée et fatigue ;
- repli ;
- conflits d'emplacement ;
- identité et résurrection interdite ;
- duplication ;
- blocs mixtes ;
- limite de 20 unités ;
- OFF/OFF et OFF/DEF ;
- rapports de bataille.

`test_modes.py` vérifie en complément les profils classique et Survie, la séparation
entre propriétaires Linux et camps, la sélection du mode, le cycle classique et la
réparation du plateau sans génération.

`test_village.py` couvre les zones Survie, les réserves, les positions logiques,
les déplacements, l'identité et les collisions entre joueurs alliés. Les suites
V1.5 et de sélection du mode sont conservées sans modification.

`test_combats_camps.py` couvre les duels contre le bot, les forces coopératives,
l'ordre des positions, les identités, la fatigue, les ordres, le contrôle par camp
et la compatibilité classique. Les forces sont préparées dans un plateau temporaire,
sans génération de vagues.

`test_vagues.py` couvre les compositions Est, leur matérialisation, la progression,
les noms d'affichage, les identités, les droits Unix simulés, la conservation des
forces excédentaires et leur exclusion des quatre places de combat.
Il vérifie aussi la remontée après affrontement, l'ordre d'arrivée persistant et
le déplacement de la colonne entière jusqu'au village.

`test_surnombre.py` vérifie le scan, les fichiers privés et leurs défauts, les
choix individuels, les retraites et placements `1..20` à l'arrivée, les cascades avec
pertes cumulées, l'ordre de la colonne et les conditions d'arrêt.

`test_repli.py` couvre les distances de sanction, les délais persistants privés,
l'interdiction de sortir pendant l'attente et le retour après son expiration.

`test_cycle_survie.py` couvre la relation tour/vague, les déplacements planifiés,
les ordres d'apparition et de combat, l'audit unique, les retraites réservées puis
différées, le contrôle final, la défaite, le timer simulé, l'état persistant, la
reprise et l'exclusion des moteurs concurrents.

Les tests utilisent un plateau temporaire et peuvent simuler les dépendances Unix.
Ils ne remplacent pas un test réel sur Linux avec vrais UID/GID, `chown`, `chmod`
et comptes `j1` / `j2`.

Voir `TESTS.md` pour les détails.

---

## 19. Mode classique, Survie et futur multijoueur

Le moteur commun doit rester indépendant du mode de jeu autant que possible.

Objectif architectural :

```text
                 moteur Mythodea
                /               \
       mode classique          mode Survie
          /   \
        j1     j2
```

Le mode Survie ne doit pas réimplémenter les combats, mouvements, généraux,
ordres ou rapports fondamentaux.

Il doit surtout définir :

- comment les ennemis apparaissent ;
- comment ils choisissent leurs actions ;
- les vagues et la progression ;
- les objectifs et conditions propres au mode.

Le multijoueur et le mode Survie doivent réutiliser au maximum les mêmes modules.

Une future faction PNJ distincte pourra permettre du solo ou du coop sans détourner
la logique de `j2`.

---

## 20. Clôture de la V1.5 et passage à la V2.0

La V1.5 est considérée comme la base de référence du moteur classique actuel.

La finalisation complète des ordres n'est pas une condition de clôture de la V1.5.
Les ordres supplémentaires seront conçus et introduits progressivement lorsque
l'expérience de jeu permettra de valider leur utilité et leur équilibre.

La validation réelle sur Raspberry Pi reste nécessaire pour les comportements liés
aux vrais comptes Linux, UID/GID, propriétaires et permissions. Elle pourra se
poursuivre pendant le développement du mode Survie, qui réutilise le même moteur.

La V2.0 dispose du cycle jouable Survie Est et poursuit les objectifs suivants :

1. développer le mode Survie sans dupliquer le moteur commun ;
2. utiliser ce mode comme environnement d'intégration et de jeu pour éprouver le moteur ;
3. introduire progressivement les mécaniques propres au Survie ;
4. intégrer dans ce mode les petits objectifs Linux aléatoires de type Bandit débutant.

---

## 21. Invariants à ne pas modifier silencieusement

Sans décision explicite, ne pas changer :

- carte classique ;
- chemins sous `/game`, `/home/j1`, `/home/j2` ;
- structure des généraux et unités ;
- permissions 700/600 ;
- identité officielle des généraux ;
- limite de 20 unités et 5 généraux ;
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

Cette spécification décrit le comportement à préserver. Les nouvelles règles
d'ordres et les futurs modes doivent être ajoutés explicitement lorsqu'ils sont
validés.

---

## 22. Progression commune, blessures et formation

### Identifiants et fabrication

`catalogues.py` est la source des recettes reconnues et de la légende des ordres.
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

Les évolutions 201 et 202 désignent respectivement une récompense de commandement
et de moral, dont le gain dépend du niveau. Les IDs 1001 à 1005 correspondent aux
jetons historiques `1-1`, `1-2`, `2-1`, `2-2`, `3-1` ; `ordre.txt` garde son format.
Les catégories préparées sont globale (armée), duel (formation) et individuelle
(intrinsèque). La technologie de Forge 104 est disponible comme évolution d'unité
pour l'orientation instinctive ; elle autorise une transformation, sans créer de
soldats. Les unités ordinaires gardent leurs accès existants. Les apprentissages
d'unités disponibles sont définis dans le catalogue ; l'attaque frontale 1002 et
les ordres personnels intégrés ci-dessous disposent d'IDs d'apprentissage propres.

### Caractéristiques et niveaux des généraux

Une création officielle apparaît au niveau 0 : `stratege` 45 %, `instinctif` 45 %,
`stratege_hybride` 5 %, `instinctif_hybride` 5 %. Nature, orientation principale et
trait inné sont permanents. L'orientation d'un hybride est celle de son préfixe ;
elle détermine ses traits et ses récompenses ordinaires, avec les mêmes poids.
Cet aléatoire est indépendant de celui des combats existants.

| Nature | Charismatique | Leader | Inventeur |
| --- | --- | --- | --- |
| Stratège | 50 % | 35 % | 15 % |
| Instinctif | 50 % | 15 % | 35 % |

Champs ajoutés à `fiche.txt` : `niveau`, `nature`, `orientation_principale`, `trait_inne`,
`points_commandement`, `moral`, `evolutions_acquises`, `evolution_apprise`,
`progression_combat`, `progression_formation`.
Les listes d'IDs sont séparées par des virgules ; l'absence d'évolution apprise
est une valeur vide. Les anciens champs sont conservés. L'autorité est
`.systeme/progression.json`, indexée par `joueur:generalN`. Modifier la fiche
possédée par le joueur ne change pas les caractéristiques officielles.

| Nature / trait | Commandement ou moral | Ordre | Unité |
| --- | --- | --- | --- |
| Stratège charismatique | 60 % commandement | 30 % | 10 % |
| Stratège leader | 20 % commandement | 70 % | 10 % |
| Stratège inventeur | 20 % commandement | 20 % | 60 % |
| Instinctif charismatique | 60 % moral | 15 % | 25 % |
| Instinctif leader | 20 % moral | 60 % | 20 % |
| Instinctif inventeur | 20 % moral | 10 % | 70 % |

Les récompenses indisponibles, incompatibles ou entièrement acquises sont exclues.
Les poids restants sont redistribués proportionnellement par un tirage entier.
Un stratège peut recevoir du commandement, un instinctif du moral jusqu'au
plafond ; les unités et ordres doivent être disponibles, compatibles avec sa
nature et encore non acquis.
Si aucun choix n'est possible, la montée
n'accorde pas de récompense. Dans les catégories unités et ordres, le choix
par défaut est uniforme parmi les IDs éligibles, avec le générateur aléatoire
de progression injecté (donc reproductible avec une graine). Les poids des
catégories, les restrictions de nature et la priorité d'une mémoire restent
inchangés. Un choix explicite fourni par l'appelant doit rester éligible.

Un stratège commence avec 11 à 20 points. Une récompense au niveau `n` utilise
`tranche = 10 * (n // 5 + 1)` puis ajoute `tranche + randint(1, tranche)`.
Un instinctif commence avec un moral nul ; une récompense au niveau `n` ajoute
`1 + randint(0, n)`, plafonné à 100. Ces gains dépendent de la récompense obtenue,
jamais du seul passage de niveau.

À l'École, les hybrides peuvent mémoriser une évolution disponible de l'autre
orientation. Une mémoire 201 ou 202 donne le même gain au prochain niveau,
sans changer nature ni trait. Moral et commandement peuvent coexister. Ces
capacités croisées ne deviennent jamais des récompenses aléatoires ordinaires.
Les non-hybrides restent soumis aux restrictions de nature. Aucune capacité
croisée n'est accordée automatiquement. Les profils antérieurs gardent leur nature ;
leur orientation se déduit de celle-ci sans nouveau tirage.

Les deux jauges indépendantes commencent à zéro :

- Combat : un point si le général a personnellement participé à au moins un
  affrontement de blocs adverses et possède encore des unités à la fin de toute
  la résolution territoriale. Choc, manœuvres, duels et cascades ne comptent
  ensemble qu'une fois. Défaite survécue et fuite après combat comptent ; fuite
  sans engagement, bloc vide ou destruction avant la fin ne comptent pas.
  Deux points donnent un niveau et remettent seulement cette jauge à zéro.
- Formation : un point par tour complet validé dans la caserne militaire, dont
  le dossier technique reste `village/<joueur>/reserve/`. Trois points donnent
  un niveau et remettent seulement cette jauge à zéro.

Le pilote traite les formations avant les combats, dans un ordre déterministe.
Chaque niveau réutilise `monter_niveau` et les récompenses ci-dessus ; la mémoire
apprise remplace le tirage du premier niveau concerné. Les tirages automatiques
utilisent un générateur indépendant de celui des combats.

`valider_evenement` persiste ensemble jauges, niveau, récompense et reçu privé
`progressions_validees` dans `progression.json`, par écriture atomique. Les clés
sont `formation:<tour>:<joueur>:<generalN>` et
`combat:survie:<tour>:<territoire>` ; chaque profil a ses propres reçus.
Représenter une même clé répare la copie de fiche sans redonner de point ou
de récompense. Les reçus ne sont pas publiés dans `fiche.txt` et accompagnent
les captures et sauvegardes. Le cycle Survie interrompu pendant la résolution
reste bloqué pour récupération ; la republication ne rejoue pas les combats.
En classique, chaque résolution appelée reçoit un UUID distinct : il n'existe
pas de reprise automatique d'un tour classique interrompu.

`progression_due` reste une API de condition administrative ; des observations
brutes ne valident aucun événement. `attribuer_niveau` conserve son rôle d'appel
explicite. Les profils existants commencent les jauges manquantes à zéro lors
de leur première validation, sans reconstituer d'expérience antérieure.
Un ancien général sans profil officiel reste inchangé, avec un moral effectif
nul ; sa montée de niveau exige une migration explicitement définie.

### Commandement, ordres personnels et QG

Le commandement effectif vaut `points // max(1, nombre_types_generiques_distincts)`.
Le global utilise le calcul entier exact
`(2 * points_QG + somme_points_autres_strateges) // (2 * max(1, nombre_non_strateges))`.
Les fonctions reçoivent les caractéristiques officielles. Le QG fourni au calcul
est l'objet général sélectionné dans la liste de l'armée. Les points ne limitent
pas le nombre d'ordres ; aucun bonus de messager n'est défini.

Le joueur déclare un QG en créant `qg.txt` dans son général, contenant uniquement
`avant`, `droite`, `gauche` ou `arriere` (espaces périphériques et fin de ligne
tolérés). Ce bloc doit exister et contenir au moins une unité. Sans fichier,
aucun QG n'est déclaré. Tous les généraux, y compris les Instinctifs, peuvent
porter un QG ; cela ne leur accorde aucun ordre ni droit lié à une autre nature.
Les ordres restent dans `ordre.txt`, indépendamment du bloc désigné.

`QuartierGeneral` sélectionne une seule fois parmi les déclarations valides des
forces engagées : exactement une déclaration par camp donne le QG officiel ;
plusieurs déclarations annulent tous les QG de ce camp, quels que soient leurs PC.
La sélection est conservée pendant toute la cascade territoriale. Le QG n'ajoute
aucune troupe. Si son bloc devient vide, sa destruction est mémorisée avant une
éventuelle conversion ou propagation : aucune relève dans cette bataille,
même si ce bloc reçoit ensuite des unités. La déclaration suit le général
dans les sauvegardes et les déplacements, sans nouvelle donnée privée persistante.

Les ordres sont confrontés par catégorie, entre deux donneurs distincts. Deux
ordres normaux opposés sont départagés par leurs PC ; une égalité annule les
deux groupes. Un ordre et un contre-ordre peuvent fonctionner ensemble, même
si le contre-ordre a moins de PC. Sans ordre adverse dans cette catégorie,
l'ordre ou contre-ordre reste applicable. Un même donneur peut cumuler des
ordres compatibles, jamais un ordre normal avec un contre-ordre. Un groupe
mixte interdit est écarté avant de comparer l'adversaire.

Les ordres personnels intégrés utilisent les PC effectifs de leur donneur.
La transmission d'un ordre de duel par le QG utilise les PC effectifs du
général QG, distincts de la formule globale d'armée. Les ordres personnels de
duel priment sur le QG ; les listes de généraux différents ne sont pas agrégées.

Le stratège hybride garde l'accès natif aux trois catégories. L'instinctif hybride
ne peut utiliser un ordre global que si son ID figure parmi ses évolutions
effectivement acquises ; une mémoire encore en attente ne suffit pas. La formule
globale continue de distinguer les orientations principales ; les points du QG,
y compris instinctif hybride, sont comptés intégralement.

La confrontation de `1-2` avec On_melange utilise désormais les donneurs QG et
les PC globaux. Les autres déclenchements historiques restent conservés.
La déclaration, la sélection du QG et ses
transmissions sont exécutées et rapportées. Les décisions globales et de duel
sont prises avant les effets de chaque duel. Les ordres transmis restent valables
jusqu'à sa fin, même si le QG est détruit entre-temps ; aucune transmission n'est
possible aux duels suivants. Un QG ayant réservé sa retraite ne transmet plus
aux combats suivants. Une fiche publique ne remplace pas `qg.txt` et ne donne
aucune connaissance d'ordre. Les ordres individuels ne sont jamais transmis.

#### Ordres V2 exécutables

| ID d'apprentissage | Jeton `ordre.txt` | Ordre | Catégorie |
| --- | --- | --- | --- |
| 1006 | `3-2` | Hérisson | individuelle |
| 1007 | `3-3` | Discours de la mort | individuelle |
| 1008 | `2-3` | Orc_un_jour_orc_toujour | duel |
| 1009 | `3-4` | Rafale | individuelle |
| 1010 | `2-4` | Cruelle | duel |
| 1011 | `2-5` | Choca_fuite (Survie) | duel |
| 1012 | `1-3` | Propagafion | globale |
| 1013 | `1-4` | Confinement | globale, contre-ordre |
| 1014 | `1-5` | Étincellant | globale |
| 1015 | `1-6` | On_melange | globale |
| 1016 | `1-7` | QG_nommade | globale |

Ces IDs s'ajoutent aux cinq historiques, sans les renuméroter. Ils sont
apprenables par les voies communes. Chaque ordre doit figurer dans les
évolutions personnellement acquises du général, dans `progression.json` privé.
Une mémoire en attente, le savoir d'un autre général et `fiche.txt` ne donnent
aucun droit. Les généraux Zombies ne donnent ou reçoivent que leurs ordres
spécifiques ; Propagafion est exécutable, Spora-adicte reste désactivé.
Les généraux ordinaires peuvent bénéficier d'un effet collectif allié sans
acquérir le droit de l'apprendre ou de l'émettre. Ces onze jetons
sont sans paramètre : une troisième valeur est refusée pour leur exécution.

Les décisions sont arrêtées avant les effets du duel. Elles ne modifient ni
les caractéristiques persistantes, ni le type, l'UUID ou la recette des soldats.
Le contexte est libéré même après exception. Les effets retenus apparaissent
dans le rapport territorial ; les PC et intentions détaillées restent root.

- Hérisson porte à ×3 l'avantage des piquiers contre la cavalerie et leur
  faiblesse face à la distance, au choc comme en manœuvre.
- Choca_fuite utilise exclusivement la retraite Survie existante, immédiatement
  après le choc initial si le général survit. Une réservation acceptée l'exclut
  des combats restants ; ses soldats ne participent pas à la manœuvre de ce duel.
  Les déplacements physiques sont appliqués avec les autres retraites du tour.
  Destination, places, réserve du village, fatigue et régénération des Sauvageons
  suivent les règles de retraite communes. Au village, avec un bot actif sur
  l'arrivée ou sans place autorisée, la retraite est refusée et le combat continue.
  Aucun bot ne reçoit cet ordre ; hors du pilote Survie, il n'est pas exécuté.
- Propagafion ajoute deux conversions à chaque Propagation normalement
  déclenchée chez un bénéficiaire allié. Les préconditions restent identiques :
  pertes adverses réelles, bloc propagateur survivant, adversaire non mort-vivant.
  La régulation des effectifs reste à la fin de la bataille territoriale.
- Confinement neutralise la conversion par Spore contre les bénéficiaires du
  camp, sans supprimer la résistance ni la priorité du Bouclier vivant.
- Étincellant place les actions des Chevaliers clinquants avant les autres
  actions de manœuvre. L'ordre relatif existant est conservé au sein des deux
  groupes ; chaque bloc garde son unique action prévue pour ce tour.
- On_melange inverse la séquence des généraux du camp : `4, 3, 2, 1`.
  Les positions absentes restent absentes ; aucun dossier n'est déplacé.
- QG_nommade retire le général QG de la séquence initiale et le place en dernier,
  après les autres généraux de sa formation. Avec On_melange et un QG en 3,
  la séquence est `4, 2, 1, 3`. Il est aussi exclu du frontal historique.
- Discours multiplie le moral courant par `11/10`, après les bonus d'unités
  existants, sous le plafond commun de 100. Les fractions restent exactes
  jusqu'au plancher collectif des sauvetages, sans arrondi intermédiaire ajouté.
- Cruelle multiplie le moral adverse par `(100 - nombre_unites_cruelles) / 100`.
  Le nombre est celui de l'armée du donneur au début du duel ; les pertes
  ultérieures ne réécrivent pas ce facteur. Discours et Cruelle se composent
  exactement avant le bornage commun `0..100` des ordres, sans arrondi ajouté.
- Orc_un_jour_orc_toujour donne l'étiquette Orc aux Sauvageons pendant ce duel.
  Leur type reste Sauvageon. Le décompte racial de moral et les interactions
  avec les Chamans tiennent compte de cette étiquette temporaire.
- Rafale utilise `archers du bloc Arrière // 4` tirs avant le choc, y compris
  avant la priorité du Bouclier vivant. Les victimes distinctes sont choisies
  aléatoirement parmi les unités éligibles ; l'étiquette `lourde` immunise la
  cavalerie lourde. Aucune immunité supplémentaire n'est ajoutée. Le sauvetage
  habituel par le moral s'applique collectivement aux victimes de chaque bloc.
  Les plans des deux camps précèdent les pertes. La participation à la bataille
  est enregistrée avant les tirs, même si ceux-ci éliminent le camp adverse.

Les autres ordres du registre de conception restent désactivés. Leur formule
isolée, lorsqu'elle existe, n'est pas une preuve de fonctionnement en partie.

#### Compatibilité des formations

Le contrôle est commun aux propriétaires alliés d'un camp, avant les effets et
la confrontation adverse. Tous les ordres impliqués dans une paire interdite
s'annulent mutuellement, simultanément, sans départage interne par PC. Les autres
ordres valides restent candidats selon leurs règles de donneur et de catégorie.
Le rapport territorial nomme chaque paire annulée et son motif. Les annulations
restent mémorisées dans le contexte de bataille, cascades comprises ; la disparition
d'un donneur ne réactive pas un ordre annulé. Aucun nouvel état disque n'est créé.

| Paire | Compatibilité |
| --- | --- |
| On_melange + Attaque frontale | Interdite |
| On_melange + Réserve stratégique | Interdite |
| On_melange + Retrait_tactique | Interdite |
| Attaque frontale + Réserve stratégique | Interdite |
| Attaque frontale + Muraille humaine | Interdite |
| Muraille humaine + Retrait_tactique | Interdite |
| Muraille humaine + On_melange | Compatible |
| Muraille humaine + Réserve stratégique | Compatible |
| Muraille humaine + QG_nommade | Compatible |
| Retrait_tactique + Réserve stratégique | Compatible |
| QG_nommade + Retrait_tactique | Compatible |
| QG_nommade + Réserve stratégique | Compatible |
| QG_nommade + On_melange | Compatible |
| QG_nommade + Attaque frontale | Compatible |

Les paires non définies ne sont pas implicitement autorisées ; Attaque frontale
+ Retrait_tactique reste ouverte. Pour_l'honneur reste non cumulable avec tout
autre ordre, sans exception actuellement validée. Cette matrice n'active aucun
ordre réservé et ne lève pas l'interdiction de mêler ordre et contre-ordre chez
un même donneur.

`commandement.compatibilite_formations()` fournit les annulations et les paires
non définies. `sequence_formation()` calcule les positions sans mutation.
`ordres_pipeline` authentifie les donneurs, applique les annulations et confronte
les PC ; `combats` utilise les séquences retenues. L'opposition spécifique entre
`1-2` et On_melange est tranchée avant le premier duel : le schéma perdant ne
revient pas après les pertes. Les autres transmissions restent décidées par duel,
avec la destruction irréversible du QG déjà décrite.

Pour les effets encore désactivés, les priorités validées sont : QG exclu des
contributions de Muraille humaine et des interceptions de Réserve stratégique ;
général en Retrait_tactique juste avant le QG ; général de réserve exclu de
Muraille humaine, sans contribution de son Avant. La réserve intercepte seulement
au rangé, avant son tour normal, puis combat normalement à ce tour. Aucun malus
de fatigue nouveau n'est défini. Les identités, pertes et retours de ces effets
ne sont pas déduits de la seule compatibilité et restent à intégrer après leurs
décisions manquantes.

### Groupes temporaires — infrastructure préparatoire

Contrats validés du lot B, encore non activés : Gros_poisson réunit uniquement
les mêmes blocs et types, sous le commandement du bénéficiaire désigné par le
QG ; pertes aléatoires dans la formation engagée, propriétaires et états
individuels conservés, retour des survivants à leurs origines après le duel.
Son jeton réservé est `2-6-position_beneficiaire-position_preteur` (ID 1017).
Le parseur conserve les deux positions dans un tuple `specification` ; cette
lecture ne rend l'ordre ni apprenable ni exécutable. Le QG peut occuper un rôle.
Les blocs absents ou sans type commun sont ignorés ; les autres prêts demeurent
possibles. Sans homologue, aucun effet, avec motif destiné au rapport. Aucun
soldat ni bloc n'est créé ; les non-prêtés gardent leur commandement d'origine.
Les généraux Zombies et les unités interdites aux ordres classiques ne bénéficient
d'aucune exception. La fatigue hétérogène n'est pas remplacée par une valeur commune.
Muraille humaine conserve au contraire chaque Avant distinct, avec les bonus
de son général d'origine, et prévoit des engagements successifs après simulation
contre l'Avant adverse, sans mutation. Le score est `ennemis éliminés - alliés
perdus`, après les protections habituelles. La meilleure valeur prime, puis la
position d'origine selon l'ordre numérique commun ; une égalité restante est
tirée au hasard reproductible. Recalcul après chaque engagement réel contre les
survivants, jusqu'à victoire ou défaite de la muraille. Les Avant participants
sont exclus de la manœuvre. QG sous QG_nommade et réserve stratégique sont exclus.
Les soldats d'un général vaincu restent engagés tant que la muraille existe.
Les survivants sans général rentrent au village d'origine après le territoire,
même perdu ; le stockage `unites_sans_general` est encore à réaliser au lot C.
À la disparition du QG, l'effet transmis finit avec le duel, puis la muraille
se dissout et les survivants reprennent leur circuit normal, sans nouveau QG.
Les morts de Ralliement et Dernière charge nécessitent une réanimation explicite
dont la sélection et l'état physique restent à définir. Les fonctions de groupes
vivants ci-dessous ne constituent pas une procédure de résurrection.

`combats.previsions_avant_muraille()` prépare seulement des résultats numériques
indépendants contre un bloc adverse fourni explicitement, via `combat_bloc`.
`simuler_avants_muraille()` ajoute les pertes après moral et limites de blessures,
avec les statistiques d'origine et les effets du contexte fourni. La sélection
des victimes et l'éligibilité au sauvetage sont communes avec `soldats.pertes()`.
Chaque candidat emploie une copie du générateur ; aucun tirage réel, fichier,
blessure, expérience, sauvegarde ou rapport n'est modifié.
`prochain_avant_muraille()` relit les survivants et recalcule scores et choix,
avec exclusions des rôles fournis. `lire_blocs_general(lecture_seule=True)`
ne recrée aucun dossier, ne nettoie rien et refuse les blocs invalides ou mixtes.
Ces API restent préparatoires : transmissions par confrontation, Bouclier,
Spore/Propagation et soutiens ne sont pas encore simulés intégralement. Les
capacités non prises en charge sont refusées explicitement, y compris un
Bouclier situé hors Avant ; elles ne reçoivent pas un score incomplet.

`soldats.participation_temporaire()` reçoit des contributions explicites
`(général, bloc, chemins des soldats)` déjà authentifiées sous gel ou dans la
génération privée. Elle ne déplace ni ne copie les dossiers. Chaque référence
conserve UUID, joueur, général, bloc, chemin, inode et UID/GID. Les blessures et
l'expérience sont relues dans le registre commun, sans copie d'état à restaurer.
Un UUID ne peut appartenir à deux groupes temporaires simultanés du même contexte.

`GroupeTemporaire.selections_homologues()` indexe les vivants par bloc d'origine
et type, sans éliminer une minorité ni choisir les soldats à prêter. `bloc()`
produit un instantané homogène accepté par `combats.combat_bloc()` ; une sélection
mixte doit être explicitement séparée. L'instantané doit être relu après pertes.
`appliquer_pertes()` exige une sélection d'UUID et un moral explicites, contrôle
les survivants demandés, puis appelle `soldats.pertes()` : tirages, blessures et
morts restent ceux du moteur commun. Cette API ne choisit aucun partage des
pertes, moral collectif, bonus, fatigue ou traitement de soutien.
`selections_gros_poisson()` extrait les homologues des deux alliés, sans retirer
les autres soldats ; profils privés et restriction raciale restent obligatoires.
Cette sélection ne remplace pas les contrôles du donneur QG, de son acquisition
et de la confrontation. `fatigues_origine()` associe à chaque UUID vivant la
fatigue officielle de son général d'origine, sans calculer une moyenne ni
définir les dégâts/résistances d'un bloc mélangé.

`participer()` inscrit seulement les soldats explicitement engagés dans une
`bataille_complete()` existante. Le comptage commun crédite les survivants une
seule fois par bataille. Préparer une vue ne donne aucune expérience ; un prêt
ne crédite pas automatiquement son général d'un affrontement personnel.
`bilan()` retourne les survivants et morts réels par propriétaire, général et
bloc d'origine. Un changement d'origine, d'identité, de type ou d'UID/GID, une
disparition sans mort enregistrée ou un objet lié provoque une erreur.

À la sortie du contexte, même après exception, les réservations sont libérées
et la vue est fermée. Les pertes et blessures ne sont jamais annulées. Les
méthodes refusent une vue fermée ou utilisée hors de sa racine et de son mode
public/privé. Aucun nouveau format persistant ni protocole de publication n'est
introduit ; une résolution privée interrompue suit la récupération commune.

Ce socle n'active pas Gros_poisson, Muraille humaine, Ralliement ou Dernière
charge. Les règles de sélection, phases et effets doivent encore être raccordées
après les décisions de `docs/ordres-v2-preparation.md`. En particulier, une vue
ne retire pas automatiquement ses soldats des autres lectures de leur général,
ne ressuscite pas les morts et ne remplace pas un duel complet avec ses capacités.

### Restriction des ordres des généraux Zombies

Les généraux identifiés Zombies dans leur profil privé ne peuvent apprendre,
donner ou recevoir que Spora-adicte et Propagafion, sous réserve des contrôles
habituels de disponibilité et d'acquisition. Leur nature initiale reste intacte :
la politique logique Zombie est dérivée du seul `etat_zombie` existant.
Toutes les natures Zombies peuvent apprendre les deux ordres. Propagafion peut
être émis même par un instinctif, avec les règles QG et de confrontation communes.
Spora-adicte (ID 1018, jeton réservé `1-8`) est apprenable et mémorisable, mais
son exécution est désactivée jusqu'à définition du ciblage. Un non-Zombie ne
peut apprendre ou émettre ces deux ordres. Les anciens acquis ne
permettent pas d'exécuter un autre ordre après zombification. Les transmissions
interdites sont filtrées avant la confrontation des ordres du duel. Cette règle
ne prive pas les soldats Zombies de leurs capacités raciales ni des effets
collectifs alliés par défaut.

À chaque niveau Zombie, premier tirage : 85 % pour +2 places, 15 % pour un ordre ;
si ordre, second tirage uniforme entre Spora-adicte et Propagafion. Un doublon
recommence l'ensemble du processus. Avec un seul ordre inconnu, la distribution
conditionnelle exacte utilise les poids 170 pour la capacité et 15 pour cet ordre.
Les deux connus donnent automatiquement +2 places, sans tirage.
`niveaux_zombie` compte les niveaux après transformation ; `gains_capacite_zombie`
compte uniquement les récompenses de capacité. La capacité est `20 + 2 * gains`.
Pour une ancienne fiche sans ce nouveau compteur, les gains déjà accordés sont
lus depuis `niveaux_zombie`, puis conservés à la prochaine montée de niveau.
Aucun nouveau bonus automatique, retrait d'ancien bonus ou tirage rétroactif.
La progression et son reçu atomique restent dans `progression.json`, sans registre
Zombie concurrent. La mémoire scolaire reste conservée par la branche Zombie
actuelle ; sa priorité éventuelle sur le tirage 85/15 reste à décider explicitement.

### Blessures et batailles complètes

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
de victoire. Les unités de réserve non engagées ne gagnent rien. Le gain est appliqué
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

La formation en réserve utilise les mêmes relevés et validations. Comme plusieurs
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
Une seule demande non vide est traitée par général. L'écriture nécessite une
évolution acquise et remplace l'emplacement choisi. Le manuel partagé par camp
a exactement `001`, `002`, `003`, avec `vide` pour un emplacement libre.

Toutes les lectures valides du tour précèdent toutes les écritures. La lecture
vérifie l'emplacement et l'ID demandé, puis mémorise l'ID réel, sans consommer le
manuel. Une écriture ultérieure ne modifie pas cet apprentissage. L'ID remplace
le tirage à la prochaine montée compatible ; s'il devient incompatible, la montée
est refusée sans perte d'état. Deux écritures concurrentes au même emplacement
sont refusées ensemble, sans choisir un gagnant implicite. Le remplacement d'un
apprentissage encore en attente reste refusé tant que sa règle n'est pas définie.
Le résultat individuel est écrit dans `formation_resultat.txt`, jamais dans le
rapport public.

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
