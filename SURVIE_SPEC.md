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
│   ├── reserve/
│   ├── forum/
│   ├── poste/
│   └── clocher/
└── j2/
    ├── garnison/
    │   ├── 1/
    │   ├── 2/
    │   ├── 3/
    │   └── 4/
    ├── reserve/
    ├── forum/
    ├── poste/
    └── clocher/
```

La garnison est la zone militaire active du village. Les quatre emplacements `1` à
`4` conservent l'organisation connue du moteur classique. Les généraux conservent
leurs blocs `avant`, `droite`, `gauche` et `arriere`.

La `reserve/` permet de stocker des généraux présents au village mais non engagés.
Les généraux y restent complets avec leurs blocs et fichiers. Un passage
`reserve <-> garnison` est une réorganisation interne au village et **ne compte pas
comme un mouvement**. Un général peut donc être placé depuis la réserve dans la
garnison puis effectuer son déplacement normal hors du village pendant le même tour,
si les autres règles de déplacement l'autorisent.

### Prise en charge des zones militaires

`plateau.reparer_structure(configuration)` crée ou répare la garnison, la réserve
et les renforts tactiques `renforts/5..20` de chaque joueur avec son propriétaire
Linux et des permissions `700`, ainsi que
les emplacements extérieurs et les espaces de repli séparés. La réparation ne crée
aucun général et ne touche pas à sa composition. Les fonctions du Forum, de la Poste
et du Clocher restent pour les étapes suivantes.

La découverte et la sécurité utilisent les mêmes descriptions de zones dans
`generaux.py`. La réserve est inspectée pour l'identité officielle, les propriétaires
et les duplications, mais elle ne figure pas parmi les forces engagées.

Les positions persistantes conservent le format `joueur:generalN=territoire`.
Un général en réserve comme en garnison a la position logique `village` ; son
chemin réel permet de retrouver sa zone. Ainsi, la réorganisation interne ne crée
ni mouvement supplémentaire ni fatigue. Les restrictions communes de déploiement,
de retour du repli et de distance restent applicables au déplacement territorial.

Les appels utilisent explicitement le profil retourné par
`config.configuration_mode("survie")`, sans remplacer la configuration globale
classique. Par exemple, `securite.verifier_tous_les_deplacements(configuration)`
audite les joueurs du profil et enregistre positions et fatigue dans les fichiers
communs sous `/home/game/systeme`. Cet audit correspond à la validation des actions
d'un tour ; il ne constitue pas encore un cycle Survie ni un scan périodique.

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

1. futurs fronts Nord, Sud et Ouest ;
2. chemin choisi par le bot dans la boucle ouest ;
3. noms des branches situées après `sud_3` ;
4. ressources initiales du joueur et future économie ;
5. création, remplacement et recrutement futurs des unités ;
6. place exacte des objectifs Linux dans la progression ;
7. récompenses des objectifs Linux ;
8. format et fréquence de scan de la poste ;
9. format et fréquence d'actualisation du clocher ;
10. condition éventuelle de victoire ou fin d'une partie Survie ;
11. ordres spécifiques au combat en surnombre.

Ces décisions restent ouvertes tant qu'elles ne sont pas nécessaires à l'étape
d'implémentation en cours.


---

## 11. Premier prototype jouable : front Est

La première implémentation jouable du mode Survie est volontairement limitée au front Est :

```text
repli <-> village <-> est_1 <-> est_2 <-> est_3
```

Le tour 0 est un tour de préparation. Pendant ce tour, les joueurs peuvent créer
leurs généraux selon les règles classiques : un général créé par tour, cinq généraux
générés au maximum par joueur. Pendant ce tour 0, un général ne peut se déplacer que
de son home vers le village.

La zone spéciale `repli` fait partie du graphe Survie et est directement reliée au
`village`. Elle conserve des espaces séparés pour les joueurs. Ce n'est pas un
territoire tactique accessible par déplacement volontaire : elle sert aux sanctions
du moteur. Une retraite tactique de surnombre reste sur les territoires tactiques.

### Configuration et propriétaires Linux

Le profil `survie` de `config.configuration_mode()` décrit uniquement le front Est.
Il conserve les racines Linux existantes et distingue :

| Acteur de jeu | Propriétaire et groupe Linux | Camp militaire |
| --- | --- | --- |
| `j1` | `j1:j1` | `allies` |
| `j2` | `j2:j2` | `allies` |
| `bot` | `root:root` | `bot` |

`allies` est un identifiant technique de camp, pas un nouveau compte Linux.
Les joueurs humains restent `j1` et `j2` ; le bot n'est pas ajouté à leur liste de
génération classique. Ses forces sont possédées par `root`, avec des dossiers en
`700` et des fichiers en `600`. Les joueurs ne doivent pas pouvoir modifier les
forces ennemies ; seul le moteur privilégié les crée et les modifie.

Le profil distingue les territoires tactiques (`village`, `est_1`, `est_2`, `est_3`)
des zones spéciales (`home`, `repli`). Le lien `repli <-> village` reste présent
dans le graphe sans autoriser un mouvement volontaire vers le repli.

À ce stade, `--mode survie --afficher-configuration` permet de consulter ce profil
sans modifier le plateau. `--mode survie` seul refuse toujours l'exécution : les
fonctions de préparation et d'audit des zones militaires et les vagues sont
appelables séparément. Le cycle Survie reste à implémenter. Des batailles
coopératives isolées peuvent être résolues avec le moteur commun sur des forces
déjà préparées.

Pour ce premier prototype, les ennemis de l'Est utilisent uniquement les généraux,
unités, blocs et règles de combat classiques. Aucun comportement tactique ou ordre
spécial de bot n'est ajouté. Des ordres propres aux bots pourront être étudiés dans
une version ultérieure.

### Cycle d'un tour

La phase d'action dure actuellement **2 minutes**.

À la fin de la phase d'action :

1. les forces ennemies déjà présentes avancent d'un territoire vers le village ;
2. la nouvelle vague est créée sur les territoires prévus par son pattern ;
3. les mouvements, présences et combats sont résolus ;
4. les renforts en surnombre peuvent provoquer des affrontements successifs ;
5. le contrôle final des territoires est calculé ;
6. si le bot contrôle le village, la partie est perdue ;
7. les rapports sont finalisés et le tour suivant commence.

Une nouvelle vague n'effectue pas immédiatement un deuxième déplacement après son
apparition. Il n'y a pas de résolution intermédiaire entre le déplacement des anciens
ennemis et l'apparition de la nouvelle vague.

### Identité des ennemis

Les noms canoniques des dossiers des généraux joueurs restent inchangés :
`general1`, `general2`, etc.

Pour les rapports, un général ennemi reçoit un **nom d'affichage** de la forme :

```text
general<vague>_<numero_dans_la_vague>
```

Exemples :

```text
general1_1
general1_2
general13_1
```

Ce nom d'affichage ne doit pas casser les fonctions communes qui valident actuellement
les noms canoniques `generalN`. L'implémentation doit donc séparer l'identité
technique du général de son nom affiché dans les rapports si nécessaire.

La `fiche.txt` d'un général ennemi contient en plus :

```text
faction=est
vague=<numero>
nom_affichage=general<vague>_<numero_dans_la_vague>
```

Les généraux des joueurs ne possèdent pas ces champs.

`nom` dans la fiche et le nom du dossier restent `generalN`. Le compteur commun
`systeme/compteur_general_bot.txt` réserve des numéros techniques jamais réutilisés.
Les positions gardent le format `bot:generalN=territoire`. Le rang d'affichage est
unique dans toute la vague, tous territoires confondus, et reste conservé après
déplacement ou destruction d'autres généraux de cette vague.

### Fonctions disponibles pour la phase ennemie

`vagues.composer_vague_est(numero, aleatoire)` décrit une vague par une liste de
généraux : territoire d'apparition, numéro de vague, nom d'affichage et composition
des quatre blocs (`nombre`, `type`). Cette fonction ne touche pas au plateau.
La source aléatoire peut être fournie pour rendre les tests reproductibles.

`survie.preparer_phase_ennemie(numero_vague, configuration, aleatoire)` réalise
uniquement la progression puis l'apparition. L'appelant fournit le numéro et doit
l'appeler une seule fois pour cette phase. Elle ne gère pas encore le tour 0,
le chronomètre, les combats, le contrôle final, la défaite ou le tour suivant.
`avancer_ennemis()` et `creer_vague_est()` sont également appelables séparément.
Les ennemis déjà au village y restent ; les autres avancent d'une seule case,
y compris ceux conservés parmi les renforts.

`survie.inventorier_ennemis()` lit toutes les présences dans les zones communes du
bot, sans nettoyage ni suppression. Les quatre places sont remplies dans l'ordre
à l'arrivée ; les ennemis supplémentaires vont dans `territoire/bot/renforts/`.
Cette zone reste privée (`root:root`, dossiers `700`, fichiers `600`) et fait partie
de la recherche des identités. Elle contient la suite mobile de la colonne ennemie.
Après l'affrontement territorial (frontal puis rangé), les premiers renforts vivants
remplissent immédiatement les places libres, avant le choix de retraite.
Cette remontée ne lance pas elle-même un nouvel affrontement.
`survie.resoudre_cascade()` enchaîne les affrontements communs selon les choix
individuels des alliés, sans lancer de cycle de partie.
L'audit des joueurs conserve les positions officielles du bot.

Le fichier privé `bot/renforts/ordre_arrivee.txt` conserve l'ordre d'arrivée des
renforts, un nom technique `generalN` par ligne. Un général arrivé plus tard rejoint
la fin, même si son numéro technique est plus petit. En l'absence d'historique
(anciennes forces préparées sans ce fichier), les noms non enregistrés sont repris
par numéro technique croissant. Ce fichier n'est pas un ordre de joueur.

---

## 12. Progression des vagues Est

La vague 1 sert d'échauffement : un général de 5 unités apparaît sur chacun des trois
territoires `est_1`, `est_2` et `est_3`.

Pour chaque général aléatoire, le nombre d'unités est réparti aléatoirement entre
`avant`, `droite`, `gauche` et `arriere`. Chaque bloc non vide reçoit un seul type
d'unité aléatoire, commun à toutes ses unités. Les blocs sont donc valides dès la
création et les effectifs annoncés sont conservés, sans nettoyage de blocs mixtes.
Les compositions imposées (mono-type ou cavalerie à l'avant) restent respectées.

Ensuite :

- vague 2 : 1 général de 10 unités aléatoires, au fond du front Est ;
- vague 3 : 1 général de 15 unités aléatoires ;
- vague 4 : 2 généraux de 10 unités ;
- vague 5 : vague Boss ;
- vague 6 : base + 1 général de 20 archers, répartition aléatoire ;
- vague 7 : base + 1 général de 20 piquiers, répartition aléatoire ;
- vague 8 : base + 1 général de 20 unités d'un même type choisi aléatoirement,
  répartition aléatoire ;
- vague 9 : même principe mono-type, avec apparition au territoire du fond et au
  territoire du milieu ;
- vague 10 : vague Boss, base + 1 général complet aléatoire.

À partir de la vague 6, la **base** est d'abord constituée d'un général complet
aléatoire.

Les vagues suivantes reprennent le pattern 6 à 10 par groupes de cinq :

- vagues 11 à 15 : base = 2 généraux complets aléatoires ;
- vagues 16 à 20 : base = 3 généraux complets aléatoires ;
- vagues 21 à 25 : base = 4 généraux complets aléatoires.

Ainsi, par exemple, la vague 13 correspond au pattern de la vague 8 :
deux généraux complets aléatoires de base + un général mono-type complet.

À partir de la vague 26, chaque nouvelle vague fait apparaître quatre généraux
complets aléatoires sur **chacun** des territoires `est_1`, `est_2` et `est_3`,
soit douze généraux par vague, jusqu'à la fin du prototype Est. Ce régime s'applique
également aux numéros divisibles par cinq à partir de cette étape.

Toute vague Boss, c'est-à-dire une vague dont le numéro est divisible par 5, apparaît
sur tous les territoires Est prévus pour le front à ce stade. La présence d'ennemis
plus anciens sur ces territoires n'annule pas l'apparition de la vague.

La composition d'une vague Boss est **répétée intégralement sur chaque territoire
concerné**, et non répartie entre eux.

Ainsi, pour la vague 5 :

```text
est_1 : 1 général complet aléatoire + 1 général avec 20 cavaliers à l'avant
est_2 : 1 général complet aléatoire + 1 général avec 20 cavaliers à l'avant
est_3 : 1 général complet aléatoire + 1 général avec 20 cavaliers à l'avant
```

La vague 5 fait donc apparaître six généraux au total.

---

## 13. Surnombre et renforts

Le mode Survie accepte qu'un territoire contienne temporairement plus de généraux
ennemis que le moteur classique n'en engage simultanément. Ce surnombre est une
difficulté normale du mode contre l'ordinateur, pas une erreur à corriger en
supprimant des troupes.

Un affrontement utilise d'abord au maximum le nombre de généraux actifs autorisé par
le territoire. Lorsque cet affrontement est terminé, les ennemis encore présents sur
le territoire peuvent entrer comme renforts.

La priorité générale lors d'événements simultanés est :

1. forces déjà présentes sur le territoire ;
2. forces déjà présentes sur la carte et arrivant ce tour ;
3. nouvelles apparitions / nouveaux spawns.

Cette priorité ne dépend jamais de l'ordre de lecture `j1` / `j2`. Les occupants
déjà présents gardent leur position. Les renforts ennemis présents remontent dans
les places libres avant les nouveaux arrivants. Les
généraux qui ne peuvent pas être engagés immédiatement restent **physiquement présents
sur le territoire** comme renforts. La limite de quatre concerne donc l'engagement
simultané, pas la présence totale sur le territoire. Aucune troupe n'est supprimée
pour résoudre le surnombre.

`bot/renforts/` représente la suite de la colonne présente sur le même territoire.
Son ordre logique est : positions actives `1 -> 2 -> 3 -> 4`, puis renforts dans
leur ordre d'arrivée. Quand des places sont libérées après un affrontement, les
premiers renforts encore vivants y remontent immédiatement dans l'ordre des places
libres. Les survivants actifs conservent leurs emplacements.

Exemple : quatre actifs et six renforts ; les quatre actifs sont détruits, puis le
joueur fuit. Les quatre premiers renforts deviennent actifs et les deux derniers
restent dans `renforts/`. Au tour suivant, les six généraux avancent ensemble.
Aucun renfort n'est laissé sur le territoire précédent. Une colonne non réduite
peut ainsi atteindre le village avec de nombreux renforts ; les affrontements
successifs sont pris en charge par la résolution en cascade.

Le joueur doit pouvoir choisir à l'avance s'il reste pour affronter ces renforts.

Chaque général joueur possède donc un fichier séparé des ordres classiques :

```text
ordre_surnombre.txt
```

Valeurs :

```text
1 = battre en retraite avant un nouvel affrontement contre les renforts
2 = continuer le combat
```

Règle par défaut :

- hors du village : `1` ;
- au village : `2`.

Hors du village, un général qui fuit rejoint le territoire adjacent valide qui le
rapproche le plus du village. Pour le front Est :

```text
est_3 -> est_2
est_2 -> est_1
est_1 -> village
```

Au village, il n'y a pas de retraite automatique. Le départage entre plusieurs
routes équivalentes sur une future carte reste à définir.

Le fichier appartient au général. Son choix est conservé lorsque le général se
déplace. S'il est supprimé, le moteur le recrée au scan suivant avec la valeur par
défaut appropriée à sa situation de création.

Le scan utilise la **position actuelle** au moment de recréer le fichier : `2`
dans la réserve ou la garnison du village, `1` dans toute autre zone (home et repli
compris). Il ne remplace pas un choix existant. Une valeur vide ou invalide est
signalée dans le rapport long et utilise le défaut du lieu, sans réécrire le fichier.
Le fichier appartient au joueur, en `600`, et ne modifie jamais `ordre.txt`.

La retraite tactique de surnombre ne doit pas devenir une téléportation punitive
vers `repli`. Elle recule d'abord d'un territoire vers le village, puis réorganise
les généraux alliés sur le territoire d'arrivée.

Pour cette réorganisation, la colonne alliée utilise des positions logiques :

```text
1..4   = positions actives
5      = renfort 1
6      = renfort 2
...
20     = renfort 16
```

Physiquement, les positions actives restent dans les emplacements habituels. Les
positions `5..20` sont stockées dans une zone `renforts/` propre à chaque joueur,
par exemple `territoire/j1/renforts/5/`. Au village, cette zone reste distincte de
`reserve/` : la réserve est une organisation interne volontaire du village, tandis
que `renforts/` représente un débordement tactique après une retraite.

La fiche d'un général joueur peut contenir le champ optionnel :

```text
position_surnombre=<1..20>
```

Ce champ n'est consulté que lorsqu'une réorganisation de surnombre/retraite est
nécessaire.

Une valeur vide, invalide ou hors de `1..20` produit un avertissement dans le
rapport et est traitée comme une absence de préférence. La fiche n'est pas
réécrite et cette valeur ne provoque pas de `ValueError`.

Ordre de placement :

1. traiter d'abord les généraux qui possèdent `position_surnombre`, par valeur
   valide demandée croissante ; à valeur égale, les départager par leur position
   logique d'origine croissante ;
2. pour chacun, essayer la position demandée ; si elle est occupée, essayer
   successivement les positions supérieures jusqu'à trouver la première place libre ;
3. traiter ensuite les généraux sans `position_surnombre`, dans l'ordre numérique
   de leur position d'origine avant la retraite ;
4. chacun de ces généraux cherche la première place libre en testant
   `1 -> 2 -> 3 -> 4 -> 5 -> ... -> 20`.

Exemple : un général sans préférence provenant de la position 1 est traité avant
un général sans préférence provenant de la position 4. Un général peut aussi
indiquer `position_surnombre=1` s'il souhaite être prioritaire pour une place active
lorsqu'une retraite arrive sur un territoire peu occupé.

Si deux préférences se chevauchent, le premier général traité prend la place ; le
suivant continue vers la première position supérieure libre. Les positions actives
`1..4` restent partagées logiquement entre `j1` et `j2`.

Par exemple, deux généraux venant de `1` et `3` demandent `5` : celui venant de `1`
essaie `5` en premier ; celui venant de `3` essaie ensuite `5`, puis `6`, `7`, etc.
Une égalité de préférence n'est pas une ambiguïté bloquante.

La retraite n'ajoute pas de fatigue et ne réinitialise pas celle du général.
Les positions officielles doivent rester cohérentes avec le territoire réel. Les
détails de départage qui ne seraient pas couverts par ces règles ne doivent pas être
inventés silencieusement.

L'implémentation prépare le placement de tous les arrivants avant de les déplacer.
Elle considère les places des occupants déjà présents comme occupées et ne déplace
pas ces occupants. Si un général ne trouve aucune place libre entre son point de
départ de recherche et `20`, il reste sur son territoire d'origine avec un
avertissement dans le rapport, sans suppression ni repli. Les autres généraux
dont le placement est possible continuent leur retraite : le groupe n'est pas
annulé. Il n'y a pas de reprise de la recherche en dessous du point de départ.
La remontée automatique des renforts **alliés** vers `1..4` n'est pas définie ici
et n'est pas déclenchée implicitement par la lecture des forces ou la cascade.

### Séquence d'une cascade

1. Résoudre l'affrontement initial avec le moteur commun, sans consulter le choix
   de surnombre pour interrompre cet affrontement.
2. Remonter les premiers renforts vivants dans les places libres, dans leur ordre.
3. Relire les forces ; s'il reste des alliés et des ennemis, et que des renforts
   viennent de remonter, lire le fichier de chaque général allié survivant.
4. Hors village, déplacer ceux qui ont choisi `1` vers le voisin rapprochant le
   plus du village. Sur le territoire d'arrivée, appliquer la réorganisation
   `1..20` décrite ci-dessus au lieu d'envoyer automatiquement un général au
   `repli` parce qu'une place active est occupée. Ceux qui ont choisi `2` restent.
   Au village, aucun général ne part automatiquement, même si son fichier contient `1`.
5. Relire les alliés réellement présents, puis relancer le même moteur si les
   deux camps sont encore présents. Les pertes précédentes restent sur disque.
6. Répéter la remontée et la consultation avant chaque nouvel affrontement.

La cascade s'arrête si les ennemis ou les alliés sont éliminés, si tous les alliés
survivants ont quitté le territoire, ou si aucun renfort n'a été promu pour un
affrontement supplémentaire. Elle ne contourne pas les limites de sécurité du
moteur commun. Les identités techniques, vagues, noms d'affichage et ordre de
colonne sont conservés. Le départage de routes équivalentes reste non défini et
provoque un refus explicite au lieu d'un choix arbitraire.

L'API est `survie.resoudre_cascade(territoire, configuration, mode_combat="OFF/OFF")`.
Elle accepte aussi `OFF/DEF`, renvoie le nombre d'affrontements, les retraites et
le contrôle local final. Elle n'avance aucun bot, ne génère aucune vague et ne
sauvegarde pas le contrôle global d'une partie. Les fonctions communes de combat
restent appelables pour un affrontement isolé.

Si la valeur `2` est choisie, des ordres spécifiques au combat en surnombre pourront
être ajoutés ultérieurement. Ils ne font pas partie du premier prototype.

Plusieurs affrontements successifs peuvent donc se produire sur le même territoire
pendant une seule phase de résolution.

Les généraux ennemis conservent leur numéro de vague dans leur fiche et leur nom
d'affichage afin que les rapports puissent distinguer les survivants d'anciennes
vagues des nouveaux renforts.

Certains territoires pourront plus tard limiter le nombre de généraux engagés
simultanément, par exemple à un seul général. Cette capacité de combat est distincte
du nombre total de forces ennemies physiquement présentes sur le territoire.

### Repli comme sanction

La zone globale `repli` n'est pas la destination normale d'une retraite tactique de
surnombre. Elle reste une **sanction** pour les anomalies et infractions du moteur
commun (duplication, déplacement illégal, collision interdite, placement chez le
mauvais joueur, etc.).

Pour éviter qu'une sanction de repli ne devienne un raccourci avantageux en Survie,
un général envoyé au repli reçoit un temps d'attente avant de pouvoir effectuer une
nouvelle action. La règle commune est :

```text
tours_attente = ceil(distance_de_retour / 2)
```

où `distance_de_retour` est le nombre minimal de territoires entre le lieu où la
sanction a été constatée et le point normal de retour depuis le repli. Pour le
prototype Survie Est, ce point est le village. Le moteur commun doit conserver cette
règle de façon réutilisable pour le mode classique/JcJ.

Exemples :

```text
distance 1 -> 1 tour d'attente
distance 2 -> 1 tour
distance 3 -> 2 tours
distance 4 -> 2 tours
distance 5 -> 3 tours
```

Pendant cette attente, le général ne peut effectuer aucune action. Le détail du
stockage et de la décrémentation est défini dans `MYTHODEA_SPEC.md` : le fichier
privé `systeme/attente_repli.txt` conserve les tours restants par identité.

Le home est un bac à sable. Une anomalie qui y est détectée produit uniquement
un avertissement dans le rapport, sans suppression, envoi au repli, nouveau délai
ni calcul de distance de sanction depuis `home`. Ses copies ne masquent pas les
occurrences présentes sur la carte et ne les sanctionnent pas. La sortie du home
reste soumise aux règles communes de déploiement et d'identité.

Pour un général déjà au repli, une nouvelle anomalie produit un avertissement,
sans nouvelle sanction ni nouveau calcul de délai ; son compteur existant est
conservé. Les copies illégales hors home restent nettoyées selon le moteur commun.
La décrémentation normale reste applicable aux tours sans nouvelle anomalie.

---

## 14. Rythme visible des combats

En mode Survie, les combats ne doivent pas être affichés comme une résolution
instantanée. Le joueur doit pouvoir suivre les étapes de la bataille et le développeur
doit pouvoir repérer plus facilement un comportement anormal.

Les délais d'affichage doivent être configurables et désactivables pour les tests
automatiques.

Le Forum doit pouvoir proposer un journal de combat actualisé progressivement,
consultable notamment avec `tail -f`.

Le ralentissement concerne la présentation et l'enchaînement des étapes ; il ne doit
pas modifier les règles mathématiques du moteur de combat.

---

## 15. Coopération j1 / j2

Les dossiers Linux de `j1` et `j2` restent séparés pour préserver les permissions,
mais les positions militaires numérotées `1` à `4` sont **partagées logiquement
entre les deux joueurs alliés**.

Cette règle s'applique aux territoires extérieurs et à la garnison du village.

Exemple valide :

```text
j1/1/general1
j2/2/general1
j1/3/general2
j2/4/general2
```

Exemple invalide :

```text
j1/1/general1
j2/1/general1
```

Deux généraux alliés ne peuvent donc pas occuper simultanément le même numéro
d'emplacement, même s'ils se trouvent dans des dossiers joueurs différents.

En cas de collision entre `j1` et `j2` sur le même numéro, **les deux généraux sont
envoyés au territoire `repli`**.

Les joueurs doivent donc communiquer pour répartir leurs généraux entre les quatre
positions communes.

Au village, `j1` et `j2` possèdent chacun une `reserve/` séparée. La réserve
n'est pas une position de combat et n'entre pas dans la règle des quatre emplacements
partagés.

### Forces communes et combat

`generaux.lire_generaux_territoire(territoire, configuration)` conserve une lecture
par propriétaire de jeu (`j1`, `j2`, `bot`). Chaque général garde son champ `joueur`,
son nom technique, son chemin réel, son emplacement, sa fiche, ses ordres et ses blocs.
Son champ `camp`, ajouté uniquement en mémoire, vient du profil.

`regrouper_forces_par_camp()` puis `lire_forces_territoire()` fournissent une vue
commune des quatre positions alliées, indépendante du propriétaire. Un emplacement
déjà occupé n'est jamais écrasé pendant ce regroupement : une collision encore
présente signale que l'audit préalable n'a pas été réalisé.

Pour les batailles préparées à cette étape, les emplacements ennemis sont lus dans
`territoire/bot/1` à `territoire/bot/4`, y compris au village. Les garnisons et
réserves spécifiques aux joueurs restent sous leurs dossiers séparés. Aucune
génération de bot n'est effectuée par ces appels. La résolution territoriale remonte
les renforts après l'affrontement, sans les engager dans un combat supplémentaire.
Les forces ennemies préparées doivent conserver leur propriétaire Linux `root`.

Les fonctions communes `resoudre_attaque_frontale()`, `resoudre_combat_range()`,
`resoudre_combat_v15()` (OFF/OFF) et `resoudre_combat_off_def()` acceptent le profil
Survie. Elles choisissent les généraux dans l'ordre des positions, relisent les
forces après les pertes et transmettent les généraux réels au même moteur de duel.
La fatigue et la destruction restent rattachées à `joueur:generalN`, jamais à
`allies:generalN`. Les données de résultat conservent propriétaires et camps ; les
libellés des rapports identifient les propriétaires réels des généraux alliés.

Le contrôle territorial est calculé selon les unités des forces engagées :

| Présence | Contrôle |
| --- | --- |
| Alliés seuls | `allies` |
| Bot seul | `bot` |
| Aucune unité | `neutre` |
| Alliés et bot | `conteste` |

La réserve reste exclue de ces forces. La sauvegarde conserve le format
`territoire=controle`. Ces fonctions ne déclenchent ni défaite globale, ni nouvelle
vague, ni nouveau tour ; le cycle complet reste une étape ultérieure.
