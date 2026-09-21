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
│   └── tests/
│       └── test_mythodea.py
├── README.md
├── TESTS.md
└── MYTHODEA_SPEC.md
```

Responsabilités :

| Module | Rôle |
| --- | --- |
| `mythodea_v_1_5.py` | point d'entrée et ordre général d'un tour |
| `config.py` | chemins, carte, constantes, légende des ordres |
| `etat.py` | compteurs, positions, fatigue, météo et lecture d'état |
| `generaux.py` | généraux, fiches, ordres, blocs, unités, permissions |
| `mouvements.py` | règles de déplacement et repli |
| `securite.py` | anti-triche et validation des déplacements |
| `combats.py` | résolution des combats |
| `rapports.py` | rapports et tableaux |
| `plateau.py` | structure du plateau et coordination des territoires |
| `victoire.py` | objectifs et victoire |

Les dépendances sont orientées de manière à éviter les imports circulaires.
Importer les modules ne doit jamais lancer un tour. Seul le point d'entrée appelle
`main()`.

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
| `1-1` | `retraite_apres_premiere_manche` | armée | comportement détaillé à finaliser |
| `1-2` | `attaque_frontale` | armée | implémenté |
| `2-1` | `attaque_chirurgicale` | formation | comportement détaillé à finaliser |
| `2-2` | `pluie_de_fleches` | formation | comportement détaillé à finaliser |
| `3-1` | `fuir_avant_la_mort` | intrinsèque | comportement détaillé à finaliser |

Un ordre inconnu, mal écrit ou non applicable est ignoré.

Les règles détaillées des ordres restants doivent être intégrées à partir du
document de design validé par le propriétaire du projet. Ne pas les inventer.

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

---

## 18. Tests

Suite actuelle :

```bash
python3 -B -m unittest discover -s python/tests -v
```

La suite contient 32 tests de régression couvrant notamment :

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

## 20. Prochaines étapes V1.5

Ordre de travail prévu :

1. intégrer et finaliser les ordres des généraux à partir du document de design ;
2. conserver/compléter les tests automatiques pour chaque ordre ;
3. faire une validation réelle sous Linux ;
4. après stabilisation, créer le mode Survie avec le moteur commun.

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
