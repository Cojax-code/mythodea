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
│   ├── vagues.py
│   └── tests/
│       ├── test_mythodea.py
│       ├── test_modes.py
│       ├── test_village.py
│       ├── test_combats_camps.py
│       ├── test_vagues.py
│       └── test_surnombre.py
├── README.md
├── TESTS.md
└── MYTHODEA_SPEC.md
```

Responsabilités :

| Module | Rôle |
| --- | --- |
| `mythodea_v_1_5.py` | sélection du mode et orchestration du tour classique |
| `config.py` | chemins, carte, constantes, légende des ordres et profils des modes |
| `etat.py` | compteurs, positions, fatigue, météo et lecture d'état |
| `generaux.py` | généraux, fiches, ordres, blocs, unités, permissions |
| `mouvements.py` | règles de déplacement et repli |
| `securite.py` | anti-triche et validation des déplacements |
| `combats.py` | résolution des combats |
| `rapports.py` | rapports et tableaux |
| `plateau.py` | structure du plateau et coordination des territoires |
| `victoire.py` | objectifs et victoire |
| `vagues.py` | compositions des vagues Est, sans accès au disque |
| `survie.py` | inventaire ennemi, progression Est, vagues et orchestration des cascades |

Les dépendances sont orientées de manière à éviter les imports circulaires.
Importer les modules ne doit jamais lancer un tour. Seul le point d'entrée appelle
`main()`.

`config.configuration_mode(mode)` retourne un profil indépendant pour `classique`
ou `survie`, sans écriture sur disque ni remplacement des variables globales
classiques. Le profil distingue les acteurs de jeu, leurs comptes et groupes Linux,
et leurs camps militaires. Les fonctions de préparation du plateau, de découverte
des généraux et d'audit des déplacements acceptent un argument `configuration`
optionnel. Sans cet argument, elles conservent la configuration classique.
Le profil Survie permet de préparer et contrôler les zones militaires des joueurs,
et de résoudre une bataille entre des forces déjà préparées. Il n'est pas encore
raccordé à un cycle de jeu Survie complet.

`generaux.zones_generaux_territoire()` décrit les emplacements et les éventuelles
réserves. `generaux.zones_generaux()` ajoute les homes et le repli. Ces descriptions
communes sont utilisées par la recherche, l'audit et la préparation du plateau ;
elles ne lisent ni ne modifient le disque. Une zone numérotée porte un champ
`emplacement` ; une réserve n'en porte pas et ne participe pas aux collisions ni
à la lecture des forces engagées.

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
anciens ennemis avant de créer la vague demandée. Le numéro est fourni par
l'appelant, une fois par phase ; aucun cycle complet de partie n'est lancé.
Les fonctions communes de création, de lecture des blocs, de permissions,
d'identité et de combat sont réutilisées. L'audit des déplacements des joueurs
préserve les positions des acteurs automatiques gérés par le moteur.

`survie.resoudre_cascade(territoire, configuration, mode_combat)` enchaîne des
appels à `combats.resoudre_combat_range()`, qui continue à résoudre un seul
affrontement et renvoie les renforts promus à son terme. La cascade consulte
ensuite les choix individuels des survivants et relit les forces après les retraites.
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
`mouvements.retraite_surnombre()` conserve le numéro de place, les unités, les
fichiers et la fatigue, et met à jour la position officielle. La cascade applique
ensuite l'audit commun des collisions, limité au territoire d'arrivée, avec envoi
au repli des occupants en collision et mise à jour de leurs positions.

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
les modules dépendant d'Unix. L'exécution Survie est refusée tant que son cycle
n'est pas implémenté. `bash/start.sh` transmet les options au point d'entrée.

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
5 généraux générés maximum par joueur
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
/home/game/systeme/compteur_general_j1.txt
/home/game/systeme/compteur_general_j2.txt
```

Les positions actives sont stockées dans :

```text
/home/game/systeme/positions_generaux.txt
```

Un numéro déjà généré ne doit jamais être réutilisé. Lorsqu'un général est
entièrement détruit, son entrée de position disparaît mais le compteur n'est pas
diminué.

Créer manuellement un dossier portant le nom d'un ancien général ne le ressuscite
pas.

Le bot Survie utilise la même identité `bot:generalN`, le même fichier de positions
et un compteur distinct `systeme/compteur_general_bot.txt`. Il n'est pas soumis
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

Si un même général existe plusieurs fois :

- une seule occurrence est conservée ;
- les autres sont supprimées ;
- le général réel est envoyé au repli comme sanction.

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

Première sortie :

```text
j1 : home -> base1 uniquement
j2 : home -> base2 uniquement
```

### Repli

Retour autorisé uniquement vers sa propre base.

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
/home/game/systeme/fatigue_generaux.txt
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

`conteste` est normalement transitoire pendant la résolution. À la fin d'un tour,
le territoire doit revenir à `j1`, `j2` ou `neutre`.

Contrôle persistant :

```text
/home/game/systeme/controle_territoires.txt
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

## 16. Victoire

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

Le point d'entrée `python/mythodea_v_1_5.py` orchestre ce cycle ; la logique
métier reste dans les modules spécialisés.

`plateau.reparer_structure()` répare uniquement les dossiers et leurs permissions,
selon le profil fourni (classique par défaut). Le point d'entrée classique appelle
ensuite une fois par joueur
`generaux.faire_apparaitre_general_si_possible()`. La génération conserve sa place
avant l'audit : un seul général par joueur et par tour, aucun si le home contient
déjà un général ou si cinq généraux ont déjà été générés. Réparer plusieurs fois
la structure ne provoque aucune génération.

---

## 18. Tests

Suite actuelle :

```bash
python3 -B -m unittest discover -s python/tests -v
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
choix individuels, les retraites et collisions à l'arrivée, les cascades avec
pertes cumulées, l'ordre de la colonne et les conditions d'arrêt.

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

La prochaine étape majeure est la V2.0 :

1. créer le mode Survie sans dupliquer le moteur commun ;
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
