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
| `cycle_linux.py` | gel Linux, capture privée, publication de générations et permissions des phases Survie |
| `survie_admin.py` | diagnostic, dégel de secours et republication explicitement autorisée, sans rejeu métier |
| `crypte.py` | collecteur privé Survie, recette pédagogique, cooldown et attribution différée |
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
Les places déjà occupées ou réservées à l'arrivée restent indisponibles. La réserve
n'entre pas dans ce placement. Un général sans place libre entre son début de
recherche et la capacité d'arrivée (`4` au village, `20` ailleurs)
reste sur son territoire d'origine avec un avertissement, sans suppression ni
repli ; les autres retraites possibles continuent. Les unités, fichiers et fatigue sont
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
/home/game
/home/j1
/home/j2
```

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
/home/game/.systeme/compteur_general_j1.txt
/home/game/.systeme/compteur_general_j2.txt
```

Les compteurs et états moteur sont privés : fichiers `root:root 600`, sous
`.systeme/` (en Survie : `root:mythodea_allies 710`, traversée seule pour joindre
la socket Crypte ; sous-dossiers privés `root:root 700`). Leur remplacement atomique prépare un inode privé
avant publication ; un fichier temporaire n'est jamais exposé aux joueurs.

Les positions actives sont stockées dans :

```text
/home/game/.systeme/positions_generaux.txt
```

Un numéro déjà généré ne doit jamais être réutilisé. Lorsqu'un général est
entièrement détruit, son entrée de position disparaît mais le compteur n'est pas
diminué.

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

Format actuel :

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

### Bloc mixte

Le type majoritaire devient le type du bloc.

- les unités minoritaires sont supprimées ;
- les unités invalides sont supprimées ;
- si plusieurs types sont à égalité en tête, **tout le bloc est supprimé** ;
- le nettoyage est effectué avant le calcul final de la limite de 20 unités.

Cette règle d'égalité est volontaire : une composition équilibrée entre plusieurs
types n'est pas considérée comme une simple erreur d'inattention.

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
/home/game/repli/j1/
/home/game/repli/j2/
```

---

## 9. Déplacements

### Immobile

```text
origine == destination
```

Valide.

### Home

Une anomalie constatée dans le home (propriétaire, identité, duplication ou
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
/home/game/.systeme/fatigue_generaux.txt
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
/home/game/.systeme/controle_territoires.txt
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

Ordres enregistrés :

| ID | Nom interne | Catégorie | État V1.5 |
| --- | --- | --- | --- |
| `1-1` | `retraite_apres_premiere_manche` | armée | réservé à une version ultérieure |
| `1-2` | `attaque_frontale` | armée | implémenté |
| `2-1` | `attaque_chirurgicale` | formation | réservé à une version ultérieure |
| `2-2` | `pluie_de_fleches` | formation | réservé à une version ultérieure |
| `3-1` | `fuir_avant_la_mort` | intrinsèque | réservé à une version ultérieure |

Un ordre inconnu, mal écrit ou non applicable est ignoré.

La V1.5 n'a pas pour objectif de finaliser tout le système d'ordres. Les règles
détaillées des ordres supplémentaires seront définies plus tard à partir de
l'expérience de jeu et d'un document de design validé. Ne pas les inventer.

---

## 15. Rapports

Répertoire :

```text
/home/game/rapport/
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
`village/<joueur>/hotel_de_ville/` : journal passif des vagues 0..2, Courrier sans
traitement de requêtes et copie du rapport court finalisé. Le Clocher commun est
`village/clocher/` ; il reste attaché au cycle vivant et exclu des captures. La
publication du village conserve ses inodes, notamment le journal suivi avec `tail -f`.

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
`/home/game/.systeme/cycle_survie.json`. Ce fichier privé appartient à `root:root`
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
`/home/game/.systeme/verrou_cycle_survie` (`root:root`, `600`), qui contient le PID.
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
- chemins sous `/home/game`, `/home/j1`, `/home/j2` ;
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
