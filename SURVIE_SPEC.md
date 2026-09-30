# Mythodea V2.0 — Mode Survie

Ce document prépare le développement du mode Survie.

Il complète `MYTHODEA_SPEC.md`, qui reste la référence du moteur commun hérité de
la V1.5. Les règles non définies ici ne doivent pas être inventées.

---

## 1. Objectif de la V2.0

La V2.0 introduit le **mode Survie**.

Le mode Survie doit réutiliser au maximum le moteur commun de la V1.5 :

- généraux ;
- unités et blocs ;
- mouvements ;
- combats ;
- sécurité ;
- fatigue ;
- rapports ;
- règles Linux communes.

Le but n'est pas de créer un deuxième moteur séparé.

---

## 2. Rôle du mode Survie dans le développement

Le mode Survie servira aussi d'environnement d'intégration et de jeu pour éprouver
le moteur commun.

Les tests Python de régression du moteur commun restent conservés. Le document
`TESTS.md` de la V1.5 n'est pas repris comme documentation de la V2.0 ; une nouvelle
documentation de tests pourra être créée plus tard lorsque les scénarios Survie
seront suffisamment définis.

Les validations réelles liées aux comptes Linux, UID/GID, propriétaires, `chmod`
et `chown` seront effectuées sur Raspberry Pi lorsque l'environnement sera
disponible.

Un bug découvert en Survie dans une règle commune doit être corrigé dans le moteur
commun lorsque cela est approprié, et non contourné uniquement dans le mode Survie.

---

## 3. Boucle initiale du mode Survie

Une nouvelle partie commence par un **tour 0 à blanc** servant de préparation.

À terme, un tutoriel guidé sera proposé avant ou pendant cette préparation. Le
joueur pourra le passer.

Après le tour de préparation, les ennemis apparaissent sur des territoires éloignés
du village.

Règle de déplacement de base du bot :

- une force ennemie avance d'un territoire vers le village à chaque tour ;
- si elle rencontre une force joueuse, le moteur commun résout le combat ;
- les survivants ennemis reprennent leur progression au tour suivant.

Le village est le centre et l'objectif défensif de la partie.

Condition de défaite :

```text
controle(village) == bot
        ↓
      défaite
```

L'entrée d'un ennemi dans le village ne suffit donc pas à elle seule : le combat et
la résolution du contrôle ont lieu normalement. La partie est perdue lorsque le
contrôle final du village revient au bot.

---

## 4. Carte Survie

Les noms de dossiers utilisent des minuscules, sans espace ni accent.

Topologie actuellement décidée :

```text
                         nord_4
                            |
                         nord_3
                            |
                         nord_2
                            |
                         nord_1
                            |
ouest_... ---- ouest_1 -- village -- est_1 -- est_2 -- est_3
                            |
                          sud_1
                            |
                          sud_2
                            |
                          sud_3
                         /     \
              branche gauche   branche droite
                 2 territoires  1 territoire
                                 entrée grotte
```

### Nord

```text
village -- nord_1 -- nord_2 -- nord_3 -- nord_4
```

### Est

```text
village -- est_1 -- est_2 -- est_3
```

### Sud

```text
village -- sud_1 -- sud_2 -- sud_3
                               / \
                    2 territoires  1 territoire
                                   entrée d'une grotte
```

Les noms définitifs des territoires des deux branches après `sud_3` restent à
choisir.

### Ouest

```text
village -- ouest_1 -- ouest_2 -- ouest_3
                                  /       \
                             ouest_4     ouest_10
                                |           |
                             ouest_5     ouest_9
                                |           |
                             ouest_6 -- ouest_7 -- ouest_8
```

La contrainte de graphe est :

```text
village - ouest_1 - ouest_2 - ouest_3
ouest_3 - ouest_4 - ouest_5 - ouest_6 - ouest_7
ouest_7 - ouest_8 - ouest_9 - ouest_10 - ouest_3
```

Ainsi, `ouest_3` à `ouest_10` forment une boucle reliée au village par
`ouest_2` puis `ouest_1`.

Le choix exact du chemin automatique du bot à l'intérieur de cette boucle reste à
définir ; il ne doit pas être inventé avant décision de gameplay.

---

## 5. Village

Le village contient des lieux de gameplay propres à chaque joueur.

Structure de principe :

```text
village/
├── j1/
│   ├── garnison/
│   │   ├── 1/
│   │   ├── 2/
│   │   ├── 3/
│   │   └── 4/
│   ├── forum/
│   ├── poste/
│   └── clocher/
└── j2/
    ├── garnison/
    │   ├── 1/
    │   ├── 2/
    │   ├── 3/
    │   └── 4/
    ├── forum/
    ├── poste/
    └── clocher/
```

La garnison est la zone militaire du village. Les quatre emplacements `1` à `4`
conservent l'organisation connue du moteur classique. Les généraux conservent leurs
blocs `avant`, `droite`, `gauche` et `arriere`.

### Forum

Le forum reçoit les informations générales de la partie, notamment :

- nombre de tours survécus ;
- rapports et informations générales utiles au joueur.

### Poste

La poste sert de canal de communication joueur -> jeu.

Un fichier dédié sera scanné périodiquement. Le joueur pourra y répondre à une
proposition du jeu, par exemple `OUI` ou `NON`. Lors du scan, le moteur lit la
réponse, applique l'action correspondante si elle est valide, puis nettoie le
fichier.

Exemple futur : accepter ou refuser une dépense de 100 PO contre un bonus. Cet
exemple ne signifie pas que le système complet d'argent est déjà défini en V2.0.

### Clocher

Le clocher permet de consulter le temps restant avant les prochaines vagues.

Le fichier associé doit pouvoir être observé depuis le terminal pendant qu'il
s'actualise, notamment avec :

```bash
tail -f <fichier_du_clocher>
```

Le format exact du fichier et la fréquence d'actualisation restent à définir.

---

## 6. Organisation militaire des territoires

Les territoires conservent l'organisation militaire du moteur classique avec les
emplacements `1`, `2`, `3`, `4` et, dans chaque général, les blocs
`avant`, `droite`, `gauche`, `arriere`.

Le bot dispose lui aussi de cette structure afin de réutiliser le moteur commun au
lieu d'introduire un système de combat séparé.


---

## 7. Objectifs Linux aléatoires

Le mode Survie introduira de petits objectifs Linux inspirés d'un niveau débutant
de Bandit.

Principes déjà décidés :

- plusieurs patterns simples seront disponibles ;
- un pattern pourra être choisi aléatoirement pour une partie ;
- les défis doivent apprendre ou faire pratiquer de vraies commandes Linux ;
- ils doivent rester courts et accessibles ;
- la réussite donne une récompense ou permet une progression dans le jeu ;
- ils ne doivent pas demander de contourner la sécurité réelle du serveur.

Exemples de familles envisagées :

- fichier caché ;
- recherche avec `find` ;
- recherche de contenu avec `grep` ;
- encodage simple comme Base64.

Les détails exacts, récompenses et conditions de déclenchement restent à définir.

---

## 8. Ordres

La V2.0 ne suppose pas que tous les ordres imaginés soient déjà finalisés.

Les ordres supplémentaires seront introduits progressivement après observation du
gameplay réel.

Point de design important à résoudre :

- plusieurs ordres alliés et adverses doivent pouvoir coexister lorsqu'ils ne se
  contredisent pas ;
- une simple priorité globale fondée sur une statistique ne doit pas être imposée
  sans validation de gameplay ;
- les règles de chevauchement, contradiction et résolution devront être définies
  avant implémentation.

---

## 9. Hors périmètre actuel

Les éléments suivants ne doivent pas être ajoutés automatiquement à la V2.0 sans
nouvelle décision de design :

- nouvelle carte multijoueur V3 ;
- tailles de carte 1v1, 2v2 et 3v3 ;
- nouvelle victoire par maintien de la base adverse ;
- événements neutres liés à la future carte V3 ;
- système complet d'argent ;
- bâtiments ;
- nouvelles statistiques avancées ;
- moral complet ;
- nouvelles unités avancées.

Ces éléments appartiennent à des étapes ultérieures sauf décision explicite contraire.

---

## 10. Questions restant à définir

Les points suivants restent volontairement ouverts :

1. règles précises d'apparition et de composition des vagues ;
2. chemin choisi par le bot dans la boucle ouest ;
3. noms des branches situées après `sud_3` ;
4. ressources initiales du joueur ;
5. création et remplacement des unités ;
6. place exacte des objectifs Linux dans la progression ;
7. récompenses des objectifs Linux ;
8. format et fréquence de scan de la poste ;
9. format et fréquence d'actualisation du clocher ;
10. condition éventuelle de victoire ou fin d'une partie Survie.

Ces décisions doivent être prises avant de figer l'architecture spécifique du mode.
