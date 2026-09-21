# MYTHODEA_SPEC.md

> **Projet :** Mythodea  
> **Version de travail :** V1.5  
> **Langage principal :** Python 3  
> **Cible principale :** Linux / Raspberry Pi OS  
> **Développement :** VS Code, Raspberry Pi, WSL  
> **Concept :** jeu de stratégie au tour par tour dans lequel le système de fichiers Linux, les utilisateurs, les permissions et SSH font partie du gameplay.

---

# 1. Rôle de ce fichier

Ce document est la spécification de référence destinée à Codex et aux autres agents qui travaillent sur Mythodea.

Avant toute modification importante :

1. lire ce fichier ;
2. inspecter le code actuel ;
3. rechercher les fonctions existantes avant d'en créer de nouvelles ;
4. ne pas modifier une règle de jeu sans demande explicite ;
5. privilégier les changements petits et testables ;
6. signaler une incohérence entre le code et cette spécification au lieu de la corriger silencieusement ;
7. conserver les formats de fichiers, chemins Linux et permissions existants sauf décision explicite contraire.

**Important :** dans Mythodea, les répertoires, fichiers, UID/GID, permissions et déplacements de dossiers ne sont pas de simples détails techniques. Ils représentent directement l'état du jeu et les actions des joueurs.

---

# 2. Vision générale

Mythodea est un wargame Linux joué au tour par tour.

Les joueurs se connectent au serveur et manipulent leurs généraux et leurs unités à travers le système de fichiers.

Principes :

- les joueurs sont des utilisateurs Linux ;
- les généraux sont des dossiers ;
- les unités sont des sous-dossiers ;
- déplacer un général signifie déplacer physiquement son dossier ;
- le moteur compare l'état précédent avec l'état actuel du système de fichiers ;
- les actions invalides sont corrigées ou sanctionnées ;
- les batailles sont ensuite résolues automatiquement ;
- des rapports expliquent le résultat du tour ;
- les permissions Unix empêchent un joueur de lire les informations privées de l'adversaire.

Version classique actuelle :

```text
j1 contre j2
```

---

# 3. Fichiers actuels du dépôt

Le dépôt ressemble actuellement à :

```text
mythodea/
├── bash/
│   ├── start.sh
│   ├── instal.sh
│   └── nettoyage.sh
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

Le point d'entrée est `python/mythodea_v_1_5.py`. Les fonctions métier sont
réparties dans neuf modules, sans dépendance circulaire. Importer les modules
ne lance pas de tour ; seul l'appel de `main()` déclenche la résolution.

Tous les scripts Python sont sous `python/`, tous les scripts Bash sous `bash/`.
La documentation reste à la racine. Les éventuels futurs scripts de préparation
iront dans `python/outils/`.

---

# 4. Environnement d'exécution

## 4.1 Linux

Le projet dépend directement de fonctionnalités Linux :

```text
users
UID / GID
chown
chmod
SSH
/home/...
propriétaires de fichiers
permissions privées
```

La cible principale est Raspberry Pi OS.

WSL peut servir au développement et aux tests, à condition d'utiliser le système de fichiers Linux de WSL plutôt qu'un projet placé sous `/mnt/c/...` lorsque les permissions Unix sont importantes.

## 4.2 Privilèges

Le moteur manipule notamment :

```text
/home/game
/home/j1
/home/j2
```

Il est donc généralement lancé avec :

```bash
sudo python3 python/mythodea_v_1_5.py
```

Ne pas supprimer arbitrairement la logique de permissions afin d'éviter `sudo` : les permissions font partie du jeu.

---

# 5. Racine du jeu

```text
/home/game
```

Structure générale :

```text
/home/game/
├── base1/
├── terrain1/
├── terrain2/
├── terrain3/
├── base2/
├── repli/
├── rapport/
└── systeme/
```

---

# 6. Carte classique V1.5

Carte linéaire actuelle :

```text
base1 <-> terrain1 <-> terrain2 <-> terrain3 <-> base2
```

Modèle :

```python
carte_territoires = {
    "base1": ["terrain1"],
    "terrain1": ["base1", "terrain2"],
    "terrain2": ["terrain1", "terrain3"],
    "terrain3": ["terrain2", "base2"],
    "base2": ["terrain3"],
}
```

Bases :

```text
j1 -> base1
j2 -> base2
```

---

# 7. Structure d'un territoire

Chaque territoire possède une arborescence par joueur puis par emplacement :

```text
/home/game/terrain1/
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

Emplacements valides :

```text
1
2
3
4
```

Exemple :

```text
/home/game/terrain1/j1/2/general3/
```

signifie :

```text
joueur      = j1
territoire  = terrain1
emplacement = 2
général     = general3
```

Un emplacement ne peut contenir qu'un seul général du même joueur.

---

# 8. Modèle d'un général

Un général est un dossier :

```text
general3/
├── avant/
├── droite/
├── gauche/
├── arriere/
├── fiche.txt
└── ordre.txt
```

Les quatre blocs militaires sont toujours :

```text
avant
droite
gauche
arriere
```

Un général valide doit contenir :

- les quatre blocs ;
- `fiche.txt` ;
- `ordre.txt`.

Limites actuelles :

```text
20 unités maximum par général
5 généraux générés maximum par joueur
```

---

# 9. Génération et identité des généraux

Les généraux sont numérotés :

```text
general1
general2
general3
general4
general5
```

Les compteurs officiels se trouvent sous :

```text
/home/game/systeme/compteur_general_j1.txt
/home/game/systeme/compteur_general_j2.txt
```

Exemple :

```text
compteur_general_j1.txt = 3
```

Alors `general4`, `general5`, `general99`, etc. ne sont pas des généraux j1 autorisés tant qu'ils n'ont pas été générés officiellement.

Ne jamais considérer qu'un dossier est légitime uniquement parce que son nom et sa structure semblent valides.

Le nom doit être exactement `general` suivi d'un entier positif écrit avec les
chiffres ASCII, sans zéro initial : `general01`, `general0` et `general١` sont
invalides.

Le compteur prouve qu'un numéro a été généré. L'entrée correspondante dans
`positions_generaux.txt` prouve qu'il est encore officiellement actif. Les deux
conditions sont nécessaires. Lorsqu'un général est détruit au combat, son entrée
est retirée immédiatement, sans diminuer le compteur. Recréer son dossier ne
permet pas de le ressusciter.

La reprise automatique d'une partie sans positions officielles est supprimée.
Une ancienne sauvegarde dépourvue de ce fichier exige une migration administrative
avant de lancer le moteur ; ses dossiers ne sont pas légitimés automatiquement.

---

# 10. `fiche.txt`

Exemple :

```text
nom=general3
orientation=combattant
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

`hybride` est rare.

Les valeurs suivantes existent déjà mais leurs effets ne sont pas encore complètement définis :

```text
strategie
force
experience
```

Ne pas leur inventer de nouveaux effets sans décision de design explicite.

---

# 11. Représentation des unités

Une unité est un **dossier**, pas un simple fichier.

Le type est reconnu à partir du nom du dossier et d'un fichier d'équipement situé dedans.

## Archer

```text
infanterie1/
└── arc
```

Type :

```text
archer
```

## Piquier

```text
infanterie1/
└── pique
```

Type :

```text
piquier
```

## Cavalier

```text
cavalerie1/
└── cheval
```

Type :

```text
cavalier
```

Une unité invalide ou inconnue peut être supprimée par le moteur.

**Important pour les scripts de test :** ne jamais créer des unités comme de simples fichiers `archer1`, `piquier1`, `cavalier1`.

---

# 12. Triangle des types

Règle actuelle :

```text
archer   > piquier
piquier  > cavalier
cavalier > archer
```

Le type avantagé reçoit actuellement :

```text
x2
```

contre sa cible favorable.

Sinon :

```text
x1
```

Ne pas modifier le triangle ou le multiplicateur sans demande explicite.

---

# 13. Blocs d'un général

Chaque bloc est lu comme une structure proche de :

```python
{
    "type": "archer",
    "nombre": 5,
    "unites": [...],
}
```

Bloc vide :

```python
{
    "type": "vide",
    "nombre": 0,
    "unites": [],
}
```

Le moteur de bataille raisonne au niveau **bloc**, même si les pertes sont appliquées physiquement aux dossiers des unités individuelles.

Dans un bloc mixte, le type le plus nombreux donne son identité au bloc. Toutes
les unités d'un autre type sont supprimées avant le calcul des effectifs et la
vérification de la limite de 20 unités du général. Les unités invalides ne
participent pas au décompte.

Si plusieurs types sont à égalité en tête, le bloc est considéré comme invalide :
toutes ses unités sont supprimées, y compris celles des types moins nombreux.
Le bloc devient vide. Ces suppressions sont consignées dans `rapport_long.txt`.
L'ordre de lecture ou d'insertion des unités ne départage pas les égalités.

---

# 14. Permissions et confidentialité

Les généraux doivent rester privés.

Permissions visées :

```text
dossiers : 700
fichiers : 600
```

Propriétaire réel :

```text
j1 -> j1:j1
j2 -> j2:j2
```

Le moteur utilise l'UID Linux pour vérifier l'identité réelle d'un général.

Ne pas relâcher ces permissions sans décision explicite.

---

# 15. Informations cachées

Décision actuelle : les rapports restent lisibles par tous. Le durcissement de
leur confidentialité est reporté au travail sur l'espionnage et la recherche
d'informations. Les permissions privées des généraux restent inchangées.

Les joueurs ne doivent pas automatiquement avoir accès à toutes les informations adverses.

Données susceptibles d'appartenir plus tard à un rapport d'espionnage :

```text
orientation
strategie
force
experience
fatigue
ordres
composition précise des blocs
```

Le rapport de bataille doit expliquer ce qui s'est produit pendant le combat, mais ne doit pas devenir automatiquement un rapport d'espionnage complet.

---

# 16. Zone de repli

```text
/home/game/repli/j1/
/home/game/repli/j2/
```

Exemple :

```text
/home/game/repli/j1/general2
```

Le repli sert notamment à sanctionner/corriger des actions invalides sans forcément détruire le véritable général.

Depuis `repli`, un général ne peut normalement revenir que vers sa propre base.

---

# 17. Positions officielles

Fichier :

```text
/home/game/systeme/positions_generaux.txt
```

Exemple :

```text
j1:general1=terrain1
j1:general2=base1
j2:general1=repli
```

Principe :

```text
état précédent officiel + état actuel du filesystem = validation du mouvement
```

Le joueur propose son action en déplaçant physiquement le dossier.

Le moteur décide ensuite si ce déplacement est légal.

---

# 18. Déplacements

## 18.1 Immobile

```text
origine == destination
```

Valide.

## 18.2 Première sortie du home

```text
home -> propre base uniquement
```

Donc :

```text
j1 : home -> base1
j2 : home -> base2
```

## 18.3 Depuis repli

```text
repli -> propre base uniquement
```

## 18.4 Mouvement normal

Un général peut avancer d'un territoire adjacent.

Exemple :

```text
terrain1 -> terrain2
```

## 18.5 Marche forcée

Un général peut avancer de deux territoires s'il existe un territoire intermédiaire valide.

Exemple :

```text
base1 -> terrain2
```

via :

```text
terrain1
```

Le territoire intermédiaire peut être :

```text
allié
neutre
```

mais pas contrôlé par l'ennemi.

Une marche forcée réussie provoque la fatigue pour le tour.

Le déplacement est évalué à partir du contrôle officiel de fin du tour précédent.
À ce moment, aucun territoire ne doit être `conteste` : les batailles doivent
avoir été résolues avant de rendre la main aux joueurs. Le passage par un
territoire contesté n'est donc pas un cas normal de marche forcée à arbitrer.

---

# 19. Fatigue

Fichier :

```text
/home/game/systeme/fatigue_generaux.txt
```

Exemple :

```text
j1:general3
```

La fatigue est notamment créée par une marche forcée.

Le moteur de combat transmet déjà l'état de fatigue aux calculs de combat des blocs.

Ne pas supprimer cette mécanique.

---

# 20. Ravitaillement

Le code contient une logique permettant d'identifier les territoires reliés à la base du joueur par une chaîne continue de territoires contrôlés par ce joueur.

Concept :

```text
base -> territoire allié -> territoire allié -> ...
```

Le système complet de malus/effets de ravitaillement n'est pas considéré comme finalisé.

Ne pas inventer de nouvelle pénalité sans décision explicite.

---

# 21. Contrôle d'un territoire

États possibles :

```text
j1
j2
neutre
conteste
```

Règle actuelle :

```text
j1 > 0 unité, j2 = 0 -> j1
j2 > 0 unité, j1 = 0 -> j2
j1 = 0, j2 = 0       -> neutre
j1 > 0, j2 > 0        -> conteste
```

`conteste` est un état transitoire de résolution, lorsque les deux camps sont
présents avant ou pendant une bataille. Il ne doit pas subsister à la fin du
tour, lorsque les joueurs peuvent à nouveau agir. Le contrôle final attendu
est uniquement `j1`, `j2` ou `neutre`.

Un territoire encore contesté à ce stade signale une anomalie de résolution à
diagnostiquer, et non une situation de jeu normale.

État persisté dans :

```text
/home/game/systeme/controle_territoires.txt
```

Exemple :

```text
base1=j1
terrain1=neutre
terrain2=j2
```

---

# 22. Modes de bataille

## OFF/OFF

Utilisé lorsqu'un territoire auparavant neutre ou contesté contient maintenant les deux camps.

Dans le déroulement normal, le contrôle précédent est neutre : `conteste` ne
doit pas être conservé entre deux tours. La prise en charge de cet ancien état
par le code reste un comportement de secours, pas une règle autorisant un
territoire contesté pendant la phase de jeu des joueurs.

## OFF/DEF

Utilisé lorsque le territoire appartenait précédemment à un joueur et que l'ennemi y entre.

Exemple :

```text
terrain2 contrôlé par j1
j2 entre sur terrain2
=> OFF/DEF
=> j1 défend
```

Pour l'instant, OFF/OFF et OFF/DEF utilisent presque le même moteur de combat.

**Ne pas supprimer cette distinction.**

Elle est prévue pour permettre plus tard :

```text
bonus défensifs
terrain
fortifications
ravitaillement
avant-postes
brouillard de guerre
```

---

# 23. Terminologie officielle des batailles

Éviter dans les rapports joueur :

```text
poursuite
initiative
attaque d'initiative
```

Terminologie souhaitée :

```text
ENGAGEMENT FRONTAL
CHOC INITIAL
MANŒUVRE
COMBAT RANGÉ
BILAN
```

## Engagement frontal

Première série d'engagements entre généraux, notamment déclenchée par l'ordre d'armée `1-2`.

## Choc initial

Premier affrontement entre blocs lors d'un engagement entre deux généraux.

## Manœuvre

Actions ultérieures des blocs survivants pendant le même engagement.

Le code ancien peut encore employer le mot `initiative` en interne. La migration du vocabulaire doit être progressive afin d'éviter les régressions.

## Combat rangé

Nouvel engagement entre généraux encore actifs après la première série d'engagements.

Ce n'est **pas** une « poursuite ».

---

# 24. Combat entre deux généraux

Le cœur de l'affrontement comprend deux phases.

## 24.1 Choc initial

Les blocs placés face à face se confrontent.

La composition et la fatigue influencent le calcul.

Si un général n'a plus aucune unité après cette phase, il est supprimé du plateau.

## 24.2 Manœuvre

Si les deux généraux survivent au choc initial, les blocs survivants peuvent attaquer d'autres blocs ennemis.

La logique de cible actuelle préfère :

1. une cible contre laquelle le type attaquant possède l'avantage ;
2. sinon le bloc ennemi non vide le plus faible.

La séquence d'actions est **globale aux deux camps**, selon cet ordre :

1. **AVANT libre** : présent au début du choc initial, sans avant adverse en face.
   La détection existante `initiative_avant` est conservée.
2. **ARRIÈRE** survivant.
3. **FLANCS** survivants (`droite` et `gauche`), par effectif décroissant entre
   les deux camps. Les flancs de même effectif sont départagés aléatoirement.
4. **AVANT engagé** : avant ayant participé au choc initial et encore vivant.
   Un avant libre ne reçoit pas de seconde action à ce rang.

Il n'y a pas de priorité permanente `j1` puis `j2`. Par exemple, un arrière de
`j2` agit avant un flanc de `j1`, sauf présence d'un avant libre prioritaire.

Après le choc initial, les survivants n'ont plus de vis-à-vis direct : chaque
confrontation détruit au moins un des deux blocs. Il ne peut donc pas rester
deux arrières ni deux avants engagés opposés. Aucune nouvelle règle de
départage n'est ajoutée pour ces situations impossibles dans un combat valide.

`ordre_attaques_initiative()` reste utilisé pour recenser les blocs de chaque
camp. `ordre_actions_manoeuvre()` les réunit dans une séquence commune construite
au début de chaque tour de manœuvre. Chaque bloc y figure au plus une fois.
Les effectifs sont relus avant chaque action : un bloc détruit depuis la
construction de la séquence est ignoré. La cible est choisie à ce moment avec
la règle existante (cible facile, sinon cible faible), et les pertes sont
appliquées immédiatement. L'ordre prévu des actions restantes n'est pas retrié
après chaque perte ; la séquence est reconstruite au tour de manœuvre suivant.

Le statut d'avant libre dépend uniquement de la situation **au début du choc
initial**. Un avant engagé qui a éliminé son opposant ne devient pas libre.

---

# 25. Ordre frontal `1-2`

```text
1-2 = attaque_frontale
```

C'est l'ordre le mieux développé de la V1.5 actuelle.

Comportement général :

- si au moins un camp actif demande l'ordre frontal, une série d'engagements frontaux est organisée ;
- les généraux peuvent être appariés par emplacement ;
- chaque paire est résolue ;
- les survivants peuvent ensuite participer au combat rangé.

La transition exacte après cette série reste un point de design à finaliser.

---

# 26. Système d'ordres

Fichier par général :

```text
ordre.txt
```

Formats :

```text
type-numero
```

ou :

```text
type-numero-specification
```

Exemples :

```text
1-1
1-2
2-1
2-2
3-1
2-2-1
```

Les ordres mal formés ou inconnus sont ignorés.

Légende actuelle :

```text
1-1 -> retraite_apres_premiere_manche
       catégorie : armee

1-2 -> attaque_frontale
       catégorie : armee

2-1 -> attaque_chirurgicale
       catégorie : formation

2-2 -> pluie_de_fleches
       catégorie : formation

3-1 -> fuir_avant_la_mort
       catégorie : intrinseque
```

**Attention : tous les ordres listés ne sont pas encore complètement implémentés.**

Codex ne doit pas supposer que la présence dans `legende_ordres` signifie « fonctionnalité terminée ».

---

# 27. Sélection des généraux après le frontal

C'est l'un des principaux points restant à finaliser pour la V1.5.

La logique temporaire peut actuellement revenir à :

```text
premier général actif j1
contre
premier général actif j2
```

Ce comportement n'est pas considéré comme la règle tactique définitive.

État de validation au 21 septembre 2026 : la sélection actuelle par emplacement,
le relais après destruction, la poursuite des engagements par un survivant et la
transition frontal → combat rangé sont couverts par des tests isolés réussis.
Ces tests constatent le fonctionnement actuel ; ils ne constituent pas une
validation de design de cette règle provisoire par l'utilisateur.

Il reste à décider :

- quel général combat ensuite ;
- comment son adversaire est choisi ;
- si l'emplacement influence l'ordre ;
- si les ordres influencent l'ordre de passage ;
- si les attributs du général influencent la priorité ;
- comment la retraite interfère avec cette transition ;
- si OFF/DEF doit avoir une transition différente.

Ne pas inventer cette règle sans validation explicite.

---

# 28. Application des pertes

Les pertes sont matérialisées en supprimant physiquement des dossiers d'unités.

Le moteur peut choisir aléatoirement les dossiers individuels supprimés dans un bloc.

Un général dont le nombre total d'unités atteint zéro est supprimé du plateau.

C'est un comportement normal du moteur.

---

# 29. Sécurité / anti-triche

Avant les combats, le moteur audite les actions.

## 29.1 Mauvais joueur

Un dossier réellement propriétaire de `j1` ne doit pas être placé dans l'arborescence de `j2`, et inversement.

L'UID Linux permet d'identifier le vrai propriétaire.

## 29.2 Général non autorisé

Un numéro de général jamais généré est invalide. Un général sans entrée dans les
positions officielles est également invalide, même si son numéro est inférieur
ou égal au compteur. Cela inclut les généraux déjà détruits.

## 29.3 Duplication

Un même général ne doit exister qu'à un seul endroit.

En cas de duplication :

- une occurrence réelle est conservée ;
- les copies supplémentaires sont supprimées ;
- le général réel peut être envoyé au repli comme sanction.

Cette règle doit être prise en compte par les scripts de test.

## 29.4 Conflit d'emplacement

Un même emplacement ne doit pas contenir plusieurs généraux du même joueur.

## 29.5 Unités invalides

Les structures inconnues ou mal formées sont supprimées.

## 29.6 Limite d'unités

Un général ne peut pas dépasser 20 unités.

Le surplus est supprimé selon la logique actuelle du moteur.

---

# 30. Cycle conceptuel d'un tour

Le flux général est :

```text
1. Préparer les rapports et la météo
2. Réparer/créer la structure requise
3. Faire apparaître les nouveaux généraux autorisés
4. Charger l'état précédent
5. Auditer anti-triche / sécurité
6. Vérifier les déplacements
7. Enregistrer la fatigue des marches forcées
8. Lire les généraux présents par territoire
9. Déterminer OFF/OFF ou OFF/DEF
10. Résoudre les batailles
11. Mettre à jour le contrôle territorial
12. Écrire les rapports
13. Persister le nouvel état
```

Ne pas résoudre les combats avant les contrôles de sécurité et de mouvement.

---

# 31. Météo

Valeurs actuelles :

```text
clair
pluie
brouillard
vent
orage
neige
```

Une météo commune au tour est choisie et sauvegardée dans :

```text
/home/game/systeme/meteo.txt
```

À ce stade :

```text
la météo n'a pas encore d'effet gameplay
```

Ne pas inventer de modificateur météo sans décision explicite.

---

# 32. Rapports

Racine :

```text
/home/game/rapport
```

Fichiers importants :

```text
rapport_court.txt
rapport_long.txt
territoires/base1.txt
territoires/terrain1.txt
territoires/terrain2.txt
territoires/terrain3.txt
territoires/base2.txt
```

---

# 33. `rapport_court.txt`

Rôle :

```text
résumé public du tour
```

Contient notamment :

- météo ;
- combats déclenchés ;
- type OFF/OFF ou OFF/DEF ;
- changements de contrôle ;
- contrôle final de la carte.

Ne pas transformer ce fichier en journal debug.

---

# 34. `rapport_long.txt`

Rôle :

```text
journal technique complet
```

Peut contenir :

- audit des déplacements ;
- corrections anti-triche ;
- détails techniques du combat ;
- noms individuels des unités perdues ;
- états des généraux ;
- décisions internes ;
- messages de debug.

Il doit rester utile au développement.

---

# 35. Rapport territorial / rapport de bataille

Exemple :

```text
/home/game/rapport/territoires/terrain1.txt
```

Objectif : être lisible pour le joueur.

Hiérarchie souhaitée :

```text
RAPPORT DE BATAILLE

1. Résumé
2. ENGAGEMENT FRONTAL
3. DÉTAIL DES AFFRONTEMENTS
   - CHOC INITIAL
   - MANŒUVRE
4. COMBAT RANGÉ
5. BILAN
```

---

# 36. Tableau résumé des engagements

Format souhaité :

```text
+------+--------------------------+-----+--------------------------+
| Pos  | j1                       |     | j2                       |
+------+--------------------------+-----+--------------------------+
| 2    | general3 ○ 20 → 12       | <-> | general3 × 20 → 0        |
| 3    | general4 ○ 20 → 12       | <-> | general4 × 20 → 0        |
+------+--------------------------+-----+--------------------------+
```

Symboles :

```text
○ = général survivant
× = général détruit
```

Notation souhaitée :

```text
effectif initial → effectif final
```

Ne pas ajouter automatiquement :

```text
(-8)
```

Le format préféré est simplement :

```text
20 → 12
```

---

# 37. Détail du choc initial

Format souhaité :

```text
+--------+-----------+---------------+-----+-----------+---------------+----------------+
| Moment | Bloc j1   | Unités j1     |     | Bloc j2   | Unités j2     | Résultat       |
+--------+-----------+---------------+-----+-----------+---------------+----------------+
| Choc   | avant     | 5 archers     | <-> | avant     | 5 piquiers    | j1 (3) / j2 (0)|
| Choc   | droite    | 5 piquiers    | <-> | droite    | 5 cavaliers   | j1 (3) / j2 (0)|
+--------+-----------+---------------+-----+-----------+---------------+----------------+
```

La colonne `Résultat` doit montrer les **survivants**.

À éviter :

```text
j1 gagne
j2 perd
```

Préférer :

```text
j1 (3) / j2 (0)
```

---

# 38. Détail des manœuvres

Même style de tableau.

Exemple :

```text
MANŒUVRE

+--------+-----------+---------------+-----+-----------+---------------+----------------+
| Moment | Bloc j1   | Unités j1     |     | Bloc j2   | Unités j2     | Résultat       |
+--------+-----------+---------------+-----+-----------+---------------+----------------+
| M1     | droite    | 3 piquiers    | ->  | gauche    | 2 archers     | j1 (3) / j2 (0)|
| M2     | gauche    | 2 cavaliers   | <-  | avant     | 1 piquier     | j1 (1) / j2 (1)|
+--------+-----------+---------------+-----+-----------+---------------+----------------+
```

Sens des flèches :

```text
-> j1 attaque j2
<- j2 attaque j1
```

S'il n'y a aucune manœuvre :

```text
Aucune manœuvre.
```

---

# 39. Combat rangé dans le rapport

Section :

```text
=================== COMBAT RANGÉ ===================
```

S'il n'y en a aucun :

```text
Aucun combat rangé.
```

Ne pas employer `POURSUITE` dans le rapport joueur.

---

# 40. Bilan final

Format souhaité :

```text
===================== BILAN =====================

+----------------------+--------+--------+
|                      | j1     | j2     |
+----------------------+--------+--------+
| Forces initiales     | 60     | 60     |
| Forces restantes     | 36     | 0      |
| Pertes               | 24     | 60     |
| Généraux engagés     | 3      | 3      |
| Généraux survivants  | 3      | 0      |
| Généraux détruits    | 0      | 3      |
+----------------------+--------+--------+

Contrôle final : j1
```

---

# 41. État actuel du rapport

Une version récente testée a déjà produit correctement :

```text
RAPPORT DE BATAILLE
ENGAGEMENT FRONTAL
tableau résumé
DÉTAIL DES AFFRONTEMENTS
CHOC INITIAL
MANŒUVRE
COMBAT RANGÉ
BILAN
```

Cependant, le test utilisé a détruit tous les généraux adverses pendant le choc initial.

Il reste donc à valider réellement :

- une manœuvre exécutée ;
- plusieurs tours de manœuvre ;
- des survivants des deux côtés ;
- un vrai combat rangé ;
- les tableaux correspondants.

---

# 42. Scripts de test

Ancien script de préparation mentionné dans cette spécification :

```text
preparer_test_4v4.py
```

But : créer rapidement un scénario de bataille 4v4 sur `terrain1`.

Ce fichier n'est pas présent dans le dépôt actuel. S'il est réintroduit, il sera
placé dans `python/outils/`. Les scénarios disponibles sont dans
`python/tests/test_mythodea.py` ; leur utilisation est décrite dans `TESTS.md`.

Les unités créées doivent impérativement respecter leur structure Linux réelle.

---

# 43. Isolation des tests

Les scénarios doivent enregistrer les compteurs et les positions officielles des
généraux qu'ils créent. Un compteur seul ne suffit pas à autoriser un général.

Un script de test doit supprimer ou neutraliser les anciennes occurrences des généraux qu'il va réutiliser.

Zones à vérifier :

```text
/home/j1
/home/j2
/home/game/repli
/home/game/base1
/home/game/terrain1
/home/game/terrain2
/home/game/terrain3
/home/game/base2
```

Sinon le système anti-duplication peut modifier le scénario avant la bataille.

Un test précédent annonçait :

```text
80 vs 80
```

mais le moteur a commencé à :

```text
60 vs 60
```

car un général par joueur avait été éliminé/repositionné pendant la validation.

Toujours distinguer :

```text
problème du setup de test
```

et :

```text
problème du moteur de combat
```

---

# 44. Tests recommandés avant fin V1.5

```text
1v1 simple
1v1 avec survivants après choc initial
4v4 frontal
4v4 avec manœuvre
4v4 avec combat rangé
OFF/OFF
OFF/DEF
mouvement normal
marche forcée
fatigue
déplacement trop long
home -> base
repli -> base
duplication
général chez le mauvais joueur
plusieurs généraux dans un emplacement
général non autorisé
plus de 20 unités
destruction d'un général
mise à jour du contrôle territorial
rapport court
rapport long
rapport territorial
```

---

# 45. Ce qu'il reste pour terminer la V1.5

## Priorité 1 — valider complètement le rapport de bataille

Les scénarios isolés avec manœuvre et combat rangé existent maintenant et leurs
vérifications automatiques passent. La lecture manuelle sur Linux reste à faire.

- créer un scénario qui déclenche vraiment `MANŒUVRE` ;
- créer un scénario qui déclenche vraiment `COMBAT RANGÉ` ;
- vérifier les effectifs et les survivants ;
- corriger les petits problèmes d'alignement éventuels.

## Priorité 2 — finaliser la transition entre généraux

Définir clairement :

- qui combat après l'engagement frontal ;
- contre qui ;
- dans quel ordre ;
- avec quelles priorités.

## Priorité 3 — finaliser les ordres retenus pour V1.5

Ne pas considérer un ordre comme terminé tant que sont définis :

```text
effet
timing
priorité
interaction avec les autres ordres
rapport joueur
tests
```

## Priorité 4 — tests de régression

La suite compte désormais 32 tests réussis, dont des scénarios sur plusieurs tours.
Le détail et les commandes de reproduction se trouvent dans `TESTS.md`.
Les permissions réelles et le lancement complet sur Linux restent à valider.

Tester toute la chaîne sans casser :

```text
mouvement
sécurité
fatigue
combat
contrôle
rapports
```

---

# 46. Architecture modulaire actuelle

Les modules sont dans `python/`. Le découpage déplace les fonctions existantes
et explicite leurs imports, sans modifier les règles ni les formats persistants.

| Module | Responsabilité |
| --- | --- |
| `mythodea_v_1_5.py` | `main()`, ordre des étapes d'un tour et garde d'exécution |
| `config.py` | Chemins, carte, joueurs, emplacements, limites et légende des ordres |
| `etat.py` | Compteurs, positions officielles, lecture du contrôle, fatigue et météo |
| `generaux.py` | Création/destruction, identité, recherche des dossiers, permissions, fiches, ordres, blocs, unités, limites et comptage |
| `mouvements.py` | Adjacence, marche forcée, validation d'un mouvement et envoi au repli |
| `securite.py` | Propriétaire, faux généraux, duplications, conflits et audit complet des déplacements |
| `combats.py` | Calcul des pertes, choc initial, manœuvre, frontal, combat rangé et résolution OFF/OFF ou OFF/DEF |
| `rapports.py` | Journaux, tableaux, affichage et contexte du rapport en cours |
| `plateau.py` | Réparation du plateau, génération de début de tour, coordination territoriale, ravitaillement et sauvegarde du contrôle calculé |
| `victoire.py` | Lecture des objectifs et vérification des tentatives |

`controle_territoire_generaux()` reste auprès des compteurs de forces dans
`generaux.py` : il est utilisé par les combats et la coordination territoriale.
`sauvegarder_controle_territoires()` est dans `plateau.py`, car il relit les
généraux pour calculer le contrôle avant d'écrire. Cela évite les dépendances
circulaires `etat → generaux → etat` et `plateau → combats → plateau`.

Les fonctions qui lisent et corrigent les unités restent regroupées dans
`generaux.py` ; leur séparation fonctionnelle est un travail ultérieur.
`verifier_tous_les_deplacements()` est dans `securite.py`, puisqu'il orchestre
l'audit anti-triche avant d'appliquer les règles de `mouvements.py`.

Dépendances principales, du plus général vers ses dépendances :

```text
mythodea_v_1_5 → plateau, securite, rapports, victoire
plateau       → combats, generaux, etat, rapports, config
combats       → generaux, mouvements, etat, rapports, config
securite      → generaux, mouvements, etat, rapports, config
mouvements    → generaux, rapports, config
generaux      → etat, rapports, config
victoire      → rapports, config
rapports      → etat, config
etat          → config
```

Les constantes sont consultées via `config`. La météo du tour et le contexte
courant des rapports sont dans `rapports`, sans copie d'état entre modules.
Le futur mode PNJ pourra ajouter `bot.py` plus tard ; il ne fait pas partie de ce
refactoring.

---

# 47. Règles de refactorisation

Lors de la séparation en modules :

1. déplacer du code avant de le réécrire ;
2. ne pas changer les règles en même temps que l'architecture ;
3. extraire un domaine à la fois ;
4. tester après chaque extraction ;
5. éviter les imports circulaires ;
6. conserver les chemins et formats de sauvegarde ;
7. ne pas transformer tout le projet en classes uniquement parce que c'est possible ;
8. utiliser des classes seulement si elles simplifient réellement la structure.

Ordre d'extraction conseillé :

```text
config
rapports
generaux
mouvements
combats
securite
```

---

# 48. Futur mode solo / survie / coop

Ce mode est prévu **après la V1.5 classique**.

Principe :

```text
même moteur de base
lanceur différent
carte différente
objectif différent
généraux ennemis préfabriqués
vagues ennemies
difficulté croissante
exploration
bonus
objectifs
solo ou coop
```

Il ne s'agit pas de construire une IA complexe.

Le comportement de base peut être :

```text
générer la vague
faire apparaître les généraux PNJ
les faire avancer vers l'objectif
résoudre les combats avec le moteur normal
augmenter la difficulté
```

---

# 49. Faction PNJ future

Ne pas utiliser `j2` comme ennemi automatique si la coop est prévue.

Préférer une faction distincte :

```text
pnj
```

Concept :

```text
solo : j1 + pnj
coop : j1 + j2 + pnj
```

Attention : beaucoup de code V1.5 suppose actuellement :

```python
joueurs = ["j1", "j2"]
```

Ne pas généraliser cela prématurément pendant la stabilisation de la V1.5.

---

# 50. Carte survie future

Le mode survie pourra utiliser une carte différente, par exemple :

```text
base
village
foret
ruines
porte_nord
porte_est
camp_nord
camp_est
```

Possibilités futures :

```text
bonus d'exploration
renforts
artefacts
réduction de fatigue
révélation de la prochaine vague
PNJ à escorter
territoire à défendre
survivre N vagues
```

Ces éléments ne sont pas des règles V1.5 actuelles.

---

# 51. SQLite futur

SQLite pourra plus tard servir à :

```text
historique des batailles
statistiques
généraux
objectifs
exploration
état du mode survie
vagues
```

Mais le système de fichiers Linux est actuellement un élément central du gameplay.

Ne pas migrer l'état principal vers SQLite sans plan explicite.

---

# 52. Style de code

Préférer :

```text
fonctions explicites
noms lisibles
pathlib.Path
dictionnaires simples
commentaires sur les règles
logique étape par étape
petits changements testables
```

Éviter :

```text
abstractions inutiles
frameworks
métaprogrammation
one-liners opaques
grosses réécritures multi-systèmes
```

La lisibilité est prioritaire.

---

# 53. Aléatoire

Le projet utilise `random`.

L'aléatoire intervient notamment dans :

```text
orientation des généraux
égalité entre flancs
choix des dossiers d'unités supprimés
météo
```

Pour les tests, un `random.seed(...)` peut être utilisé dans un script de test dédié si nécessaire.

Ne pas rendre tout le jeu déterministe sans demande explicite.

---

# 54. Vocabulaire de code futur

Préférer :

```text
engagement_frontal
choc_initial
manoeuvre
combat_range
repli
ravitaillement
```

Éviter de réintroduire comme vocabulaire joueur :

```text
poursuite
```

Les anciens noms internes peuvent être renommés progressivement pour éviter les régressions.

---

# 55. Règles à ne pas modifier silencieusement

Conserver sauf demande explicite :

```text
/home/game comme racine
j1 / j2 pour le mode classique
carte linéaire classique
4 blocs par général
4 emplacements par joueur et territoire
20 unités maximum par général
5 généraux maximum générés par joueur
unités représentées par des dossiers
archer > piquier > cavalier > archer
bonus favorable x2
mouvement normal = 1 territoire
marche forcée = 2 territoires + fatigue
intermédiaire ennemi interdit en marche forcée
home -> propre base uniquement
repli -> propre base uniquement
anti-duplication
anti-faux-général
validation par UID Linux
distinction OFF/OFF et OFF/DEF
modèle de contrôle territorial
```

---

# 56. Règles de travail pour Codex

## Avant de coder

Lire :

```text
MYTHODEA_SPEC.md
fichier Python principal
scripts concernés
```

Chercher une fonction existante avant d'en créer une nouvelle.

## Pendant

Préférer :

```text
petit patch
réutilisation des helpers existants
formats persistants inchangés
permissions préservées
```

Ne pas dupliquer les règles.

Exemple à éviter :

```text
un triangle d'unités dans combats.py
un autre triangle légèrement différent dans bot.py
```

Le bot devra utiliser la même source de règles que le moteur.

## Après

Toujours au minimum :

```bash
python3 -m py_compile <fichiers_python_modifiés>
```

Pour une modification de combat :

1. préparer un scénario dédié ;
2. lancer le moteur ;
3. lire le rapport territorial ;
4. lire `rapport_long.txt` si le résultat paraît incohérent.

---

# 57. Méthode de diagnostic

Lorsqu'un test échoue, déterminer d'abord la couche responsable :

```text
setup de test
permissions
anti-triche
mouvement
persistance
combat
rapport
```

Ne pas corriger immédiatement `combat_bloc()` simplement parce que l'effectif attendu n'apparaît pas.

Exemple :

```text
setup annonce 80 vs 80
rapport commence à 60 vs 60
```

Cela peut provenir du système anti-duplication avant même le combat.

Toujours consulter `rapport_long.txt`.

---

# 58. Ordre de priorité des sources

En cas de conflit :

```text
1. instruction explicite récente de l'utilisateur
2. code actuellement testé
3. MYTHODEA_SPEC.md
4. README / anciens commentaires
5. hypothèses
```

Lorsqu'une nouvelle décision modifie une règle importante, mettre ce fichier à jour.

---

# 59. Objectif immédiat

Objectif actuel :

```text
terminer une V1.5 classique stable et testable
```

Avant d'attaquer fortement :

```text
mode survie
coop PNJ
SQLite
refactorisation massive
espionnage avancé
effets météo
fortifications
statistiques avancées des généraux
```

Priorités de clôture V1.5 :

```text
1. valider MANŒUVRE
2. valider COMBAT RANGÉ
3. finaliser la sélection/transition des généraux
4. finaliser les ordres retenus
5. tests de régression
6. découpage en modules réalisé sur demande ; préserver les tests de régression
```

---

# 60. Résumé rapide pour Codex

```text
Mythodea est un wargame Linux dont le filesystem fait partie du gameplay.

Joueurs classiques : j1 et j2.

Carte :
base1 - terrain1 - terrain2 - terrain3 - base2

Un général :
generalX/
  avant/
  droite/
  gauche/
  arriere/
  fiche.txt
  ordre.txt

Unités :
infanterieX/arc   -> archer
infanterieX/pique -> piquier
cavalerieX/cheval -> cavalier

Triangle :
archer > piquier > cavalier > archer
bonus favorable x2.

Limites :
20 unités / général
5 généraux / joueur
4 emplacements / territoire / joueur

Mouvement :
1 territoire = normal
2 territoires = marche forcée + fatigue
intermédiaire ennemi interdit
home -> propre base
repli -> propre base

Sécurité :
UID Linux important
pas de duplication
pas de général non autorisé
pas de plusieurs généraux dans un emplacement

Batailles :
OFF/OFF
OFF/DEF

Vocabulaire rapport :
ENGAGEMENT FRONTAL
CHOC INITIAL
MANŒUVRE
COMBAT RANGÉ
BILAN

Ne pas employer "poursuite" comme terme joueur.

Rapports :
rapport_court = résumé public
rapport_long = debug complet
rapport territorial = rapport de bataille lisible

V1.5 reste à finaliser :
- vrais tests de manœuvre
- vrais tests de combat rangé
- sélection du prochain général
- ordres retenus
- régression

Architecture actuelle :
modules dans python/, scripts dans bash/, documentation à la racine.

Plus tard :
mode survie/tutoriel/coop avec vagues de généraux PNJ préfabriqués utilisant le même moteur.
```

---

# 61. Maintenance de cette spécification

Quand une règle de gameplay, un format de fichier, une phase de combat, un rapport ou une décision d'architecture change, mettre ce fichier à jour dans le même travail si possible.

Demande confirmée le 21 septembre 2026 : mettre cette spécification à jour au fur
et à mesure du travail, en décrivant les décisions validées dans les sections
concernées et les modifications réalisées dans l'historique daté ci-dessous.
Séparer les modifications terminées, les vérifications et les sujets reportés.

Le but est double :

1. éviter que Codex ait à redécouvrir le projet à chaque session ;
2. éviter qu'une refactorisation automatique modifie accidentellement les règles de Mythodea.

---

# 62. Installation, remise à zéro et lancement

`bash/instal.sh` est destiné à l'installation initiale et appelle le script
`nettoyage.sh` situé dans le même dossier `bash/`.
Le nettoyage complet du plateau et des homes de `j1` et `j2` est volontaire :
une nouvelle partie ne doit conserver aucun résidu de la précédente. Cela inclut
les fichiers cachés, notamment `.ssh` s'il existe.

`bash/start.sh` retrouve la racine du projet à partir de son propre emplacement,
puis lance `python/mythodea_v_1_5.py`, quel que soit le répertoire de l'appelant.
Il utilise `sudo` si l'appelant n'est pas root. Le moteur affiche le rapport court
et les chemins des rapports détaillés. Une erreur du moteur est propagée au lanceur.

Depuis la racine du dépôt :

```bash
sudo bash bash/instal.sh
bash bash/start.sh
python3 -B -m unittest discover -s python/tests -v
```

---

# 63. Historique des modifications

## 2026-09-21 — corrections ciblées après revue

### Demandes et changements réalisés

- **Point 2 — noms des généraux :** validation commune du nom canonique ; rejet
  des zéros initiaux et des chiffres non ASCII. Les dossiers aux noms invalides
  restent traités par le nettoyage anti-triche existant.
- **Point 3 — résurrection :** les positions officielles servent aussi de registre
  des identités actives. Le moteur retire l'identité à la destruction au combat,
  conserve le compteur et refuse les recréations sans identité officielle,
  y compris chez l'adversaire. Aucun nouveau fichier d'état n'est ajouté.
- **Point 6 — lancement :** `start.sh` retrouve le moteur à côté de lui, lance le
  bon fichier Python et utilise l'affichage des rapports déjà fourni par celui-ci.
- **Point 7 — blocs mixtes :** conservation du type le plus nombreux et suppression
  des autres unités. En cas d'égalité en tête, suppression de toutes les unités
  du bloc. L'idée du premier type inséré a été abandonnée après clarification,
  car l'ordre de lecture du système de fichiers ne garantit pas cet ordre.
- Ajout de `tests/test_regressions.py` : scénarios sur un plateau temporaire,
  avec permissions Linux simulées et sans lancer le point d'entrée du vrai jeu.
- L'ajout de l'orientation rare `hybride` effectué par l'utilisateur est conservé.

### Décisions conservées ou reportées

- **Point 4 :** installation initiale unique et nettoyage intégral volontaire,
  y compris les fichiers cachés des homes. Scripts correspondants inchangés.
- **Point 5 :** rapports publics pour le moment ; confidentialité à reprendre
  lors du travail sur l'espionnage et la recherche d'informations.
- **Point 8 :** séparation des lectures et corrections, verrou de tour et reprise
  après interruption reportés.
- Priorité des manœuvres : règle reçue et traitée dans l'entrée suivante.
- Combat rangé : sélection actuelle inchangée, premier général actif dans
  l'ordre des emplacements de chaque camp. Le caractère provisoire mentionné
  lors de la revue venait des sections 25 et 27 de cette spécification.
- Ordres autres que `1-2` : absence d'effet connue, finalisation ultérieure.
- Marche forcée : clarification ultérieure ci-dessous ; aucun territoire ne
  doit rester contesté lorsque les joueurs peuvent agir. Le code du déplacement
  n'est pas modifié dans ce correctif.
- Victoire : règle actuelle conservée.
- Sécurisation générale des liens symboliques et refactorisation en modules :
  non incluses dans ce correctif.

### Vérifications

- Syntaxe Bash de `start.sh` : validée avec `bash -n`.
- Les 14 tests de `python -m unittest discover -s tests -v` réussissent : identités,
  génération, déploiement, duplication, repli, blocs mixtes, égalités, limite de
  20 unités, bataille 4v4 avec manœuvres, combat rangé OFF/DEF et rapports.
- Compilation de `mythodea_v_1_5.py` et `tests/test_regressions.py` : validée avec
  `python -m py_compile`.
- `git diff --check` : aucune erreur d'espacement.
- Les permissions réelles Linux ne sont pas validées par ces tests Windows.

### Clarifications confirmées après les corrections

- **État contesté :** l'utilisateur confirme qu'il s'agit uniquement d'un état
  de passage pendant la résolution. Il ne doit jamais subsister en fin de tour
  lorsque la main est rendue aux joueurs. Les sections 18.5, 21 et 22 précisent
  cette règle ; aucune modification du moteur n'est effectuée pour cette
  clarification documentaire.
- **Anti-résurrection :** l'utilisateur confirme son accord avec le mécanisme
  mis en place au point 3, fondé sur les identités encore présentes dans les
  positions officielles.

## 2026-09-21 — priorité globale des blocs pendant la MANŒUVRE

### Règle validée et modifications

- Remplacement de la boucle successive `j1` puis `j2` par une séquence globale
  d'actions : avant libre, arrière, flancs, avant engagé.
- Conservation de `initiative_avant`, de `ordre_attaques_initiative()` et du
  choix du flanc le plus nombreux. Classement des flancs entre les deux camps
  par effectif décroissant ; hasard uniquement pour départager les flancs égaux.
- Clarification de l'utilisateur : deux blocs en vis-à-vis ne survivent pas
  tous les deux au choc initial. Le cas de deux arrières ou de deux avants
  engagés survivants ne nécessite donc pas une nouvelle règle de départage.
- Relecture des blocs avant chaque action et conservation du choix des cibles,
  du calcul des pertes, de la fatigue et des limites de tours existants.
- Rapport long : affichage de la séquence globale prévue pour chaque tour de
  manœuvre. Les tableaux territoriaux gardent leur format et reflètent l'ordre
  réel des actions et leur sens (`->` ou `<-`).

### Vérifications

- Tests ajoutés pour la priorité de l'arrière de j2, l'avant libre de j2,
  l'avant engagé restant non libre, l'ordre global des flancs, leurs égalités,
  l'absence de double action et l'annulation de l'action d'un bloc détruit.
- Vérification du calcul de blocs sur les types, effectifs de 1 à 20 et états de
  fatigue : au moins un bloc doit être détruit dans chaque confrontation.
- Les **22 tests** passent avec `python -B -m unittest discover -s tests -v`.
  Les scénarios utilisent un plateau temporaire et vérifient aussi les rapports
  territorial et long ; le plateau réel n'est pas utilisé.
- La vérification des confrontations couvre 14 400 combinaisons de types,
  d'effectifs et de fatigue : aucune ne laisse les deux blocs vivants.
- `python3 -m py_compile mythodea_v_1_5.py tests/test_regressions.py` a été tenté,
  mais l'alias `python3` Windows échoue. La compilation réussit avec l'interpréteur
  Python 3 installé via `python -m py_compile` sur ces deux fichiers.
- `git diff --check` ne signale aucune erreur d'espacement. Les permissions
  Linux réelles restent hors du périmètre de ces tests isolés sous Windows.

## 2026-09-21 — tests de la sélection des généraux et de la chaîne de résolution

### Périmètre demandé

L'utilisateur demande les tests des points 1 et 3 de la liste de clôture :
sélection actuelle en combat rangé et compléments de régression. Le contenu des
ordres sera fourni plus tard. Aucune règle de sélection ou d'ordre n'est ajoutée.

### Modifications et résultats

- Ajout de dix tests à `tests/test_regressions.py` ; **32 tests réussissent** au
  total, dont 24 cas de déplacement dans un test paramétré pour les deux joueurs.
- Sélection des généraux par emplacement, exclusion des généraux vides, relais
  après destruction et réutilisation du survivant vérifiés par les engagements
  réellement consignés dans le rapport long.
- Transition frontal → combat rangé testée avec des survivants des deux camps ;
  arrêt sans combat rangé testé lorsqu'un camp disparaît dès le frontal.
- Déplacement trop long et traversée forcée d'un intermédiaire ennemi sanctionnés
  au repli ; conservation des unités et retour à la base vérifiés.
- Marche forcée, fatigue au combat et récupération au tour suivant vérifiées.
- Conflit d'emplacement : tous les généraux concernés rejoignent le repli.
- Dépassement réel de 25 unités : suppression de 3 unités arrière et de 2 unités
  gauche, avec conservation des 20 autres et stabilité au tour suivant.
- Le helper de test `tour_sans_generation()` vérifie aussi les positions
  persistées et l'absence d'état contesté après chaque résolution du scénario.
- Création de `tests/README.md` : commandes, scénarios attendus, consultation
  manuelle d'un rapport temporaire et explication simple de l'AST et des simulations.
- Aucune modification du moteur ni des scripts de jeu pendant ce travail.

### Limites de validation

Les fonctions réelles d'audit et de combat travaillent sur un plateau temporaire.
Les droits Linux sont simulés. Les scénarios de plusieurs tours n'exécutent pas
le point d'entrée complet : ils n'incluent pas l'installation, la réparation des
permissions, la génération automatique à chaque tour ni la victoire. L'absence
d'état contesté est vérifiée dans les scénarios testés, pas démontrée pour toute
partie possible. Le test réel Linux et la définition des ordres restent à faire.

## 2026-09-21 — simplification du chargement des tests

- L'utilisateur a placé le lancement dans `main()`, protégé par
  `if __name__ == "__main__"`. Importer le moteur ne lance plus de tour.
- Les tests importent désormais le fichier complet avec `importlib`, dans un
  module neuf par scénario. Le découpage des déclarations par AST est supprimé.
- Les modules Unix `pwd` et `grp` sont remplacés pendant l'import pour permettre
  les tests Windows. Le plateau temporaire et les simulations restent inchangés.
- `tests/README.md` explique ce chargement. Le moteur et les règles ne sont pas
  modifiés dans ce travail ; le découpage en modules attend la proposition utilisateur.
- Vérifications : 32 tests réussis et compilation du fichier de tests validée.
  La suite a nécessité une exécution hors du bac à sable Windows, qui bloquait
  les dossiers temporaires. Les droits Linux réels restent à valider.

## 2026-09-21 — découpage en modules et séparation Bash/Python

### Architecture

- Déplacement des trois scripts dans `bash/` et du point d'entrée dans `python/`.
- Extraction progressive de `config`, `etat`, `rapports`, `victoire`, `generaux`,
  `mouvements`, `securite`, `combats` et `plateau` ; dépendances sans cycle.
- Conservation des 98 fonctions, de leurs paramètres et de leur logique ; seuls
  les accès aux fonctions et variables déplacées portent les préfixes de modules.
- Tests déplacés dans `python/tests/test_mythodea.py`, avec imports normaux des
  modules et simulations adaptées à leur nouvel emplacement. Aucun résultat
  attendu n'est changé. La documentation des tests est à la racine : `TESTS.md`.
- Lanceur adapté au chemin `python/mythodea_v_1_5.py`. Les deux scripts
  d'installation et de nettoyage sont déplacés sans changement de logique.

### Vérifications du refactoring

- Compilation et 32 tests de régression réussis après chaque grande extraction.
- Comparaison avant/après des 32 scénarios : mêmes arborescences, mêmes contenus
  des fichiers d'état et des rapports (chemin temporaire normalisé).
- Comparaison structurelle des 98 fonctions : signatures et corps identiques
  après normalisation des préfixes de modules.
- Import des dix modules vérifié sans lancement de tour ni accès au plateau.
- Syntaxe des trois scripts Bash validée ; lanceur vérifié depuis un autre
  dossier avec Python et sudo simulés, y compris la propagation des codes 0 et 37.
- Les permissions Linux réelles et une partie complète sur Linux restent hors
  du périmètre des scénarios isolés sous Windows.
