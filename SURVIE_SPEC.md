# Mythodea V2.0 — Mode Survie

Ce document décrit le prototype jouable Survie Est et les règles de conception
du mode Survie. Les fonctionnalités prévues au-delà de ce prototype restent
distinctes du cycle actuellement implémenté.

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

Une nouvelle partie commence par un **tour 0 de préparation**. Ce tour est une
fenêtre d'action normale : les joueurs disposent de la même durée que pendant les
tours suivants, mais aucune force ennemie ancienne n'est encore présente à déplacer.

À terme, un tutoriel guidé sera proposé avant ou pendant cette préparation. Le
joueur pourra le passer.

À l'expiration du tour 0, la résolution normale a lieu : audit unique des actions
joueurs, absence de déplacement ennemi ancien, apparition de la vague 1, combats et
retraites éventuels, calcul du contrôle, rapports et défaite éventuelle. Le tour 1
commence seulement après cette résolution.

La relation entre tour et vague est volontairement décalée : à la résolution du
tour N, les forces ennemies déjà présentes avancent d'abord, puis la vague N+1
apparaît. Une vague nouvellement apparue ne se déplace jamais pendant la résolution
où elle est créée.

Règle de déplacement de base du bot :

- une force ennemie déjà présente avance d'un territoire vers le village à chaque
  résolution de tour ;
- les ennemis déjà au village y restent ;
- si une force ennemie rencontre une force joueuse, le moteur commun résout le
  combat ;
- les survivants ennemis reprennent leur progression à la résolution suivante.

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
aucun général et ne touche pas à sa composition. Le Forum et la Poste restent pour
les étapes suivantes ; le Clocher expose seulement l'état et le temps du cycle.

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
communs sous `/home/game/systeme`. Le cycle Survie appelle cet audit une seule fois
après la fenêtre d'action ; les contrôles suivants n'en rejouent pas les effets.
L'audit seul ne lance ni cycle de partie ni scan périodique.

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

Le clocher permet de consulter le temps restant de la fenêtre d'action du tour
courant. Le timer clôt cette fenêtre ; le clocher ne contient pas lui-même la
logique de résolution du tour.

Deux fichiers sous `/home/game/clocher/` sont lisibles par le groupe allié :

- `etat_tour.txt` : photographie courante remplacée atomiquement, pour `cat` ;
- `suivi_tour.log` : inode stable alimenté par append, pour `tail -f`.

Ils indiquent `TOUR`, `PHASE` et `TEMPS RESTANT` pendant les fenêtres temporisées,
avec une actualisation par seconde. Pendant la capture, ils annoncent
`FIN DU TOUR`, `RESOLUTION EN COURS`, `JOUEURS GELES`, `PAUSE : 10 secondes`, puis
`PROLONGATION TECHNIQUE` si nécessaire. Le log n'est pas remplacé entre les tours.

```bash
cat /home/game/clocher/etat_tour.txt
tail -f /home/game/clocher/suivi_tour.log
```

Le Clocher complète l'annonce `wall` envoyée avant le gel. Une seule session SSH
principale par joueur suffit ; aucune autre fonctionnalité de bâtiment n'est requise.

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

`--mode survie --afficher-configuration` permet de consulter ce profil sans
modifier le plateau. Le cycle Survie Est est lançable sur un plateau dédié avec
les comptes Linux `j1` et `j2` préparés par l'installation :

```bash
bash bash/start.sh --mode survie
```

`--duree-action` configure la fenêtre en secondes (120 par défaut, 0 pour supprimer
l'attente des nouvelles fenêtres). `--tours` limite le nombre de résolutions de
cet appel. Le groupe `mythodea_allies`, systemd et cgroup v2 sont requis ; la
préparation et les vérifications Linux figurent dans `TESTS_LINUX_SURVIE.md`.
Les fonctions de préparation, d'audit, de vague et de combat restent
appelables séparément. Les identités et fichiers d'état étant communs aux deux
modes, ne pas alterner classique et Survie sur une même partie.

L'ouverture, la résolution directe et le pilote refusent un plateau contenant
encore des territoires ou rapports territoriaux classiques, sans supprimer ces
données. La préparation Survie utilise un plateau dédié, hors des scripts
d'installation/nettoyage classiques. Les chemins, rapports, messages et exemples
produits par le cycle utilisent uniquement les zones du profil Survie ; l'exemple
de consultation en fin de tour pointe vers le rapport du village.

Pour ce premier prototype, les ennemis de l'Est utilisent uniquement les généraux,
unités, blocs et règles de combat classiques. Aucun comportement tactique ou ordre
spécial de bot n'est ajouté. Des ordres propres aux bots pourront être étudiés dans
une version ultérieure.

### Cycle d'un tour

La phase d'action dure **120 secondes (2 minutes) par défaut**, y compris au tour 0.

Un tour comprend une fenêtre d'action joueurs puis sa résolution automatique.
À son expiration : `wall`, annonce au Clocher, gel réel confirmé de j1/j2,
capture cohérente, puis dégel. Le gel dure **au moins 10 secondes**, même si la
copie finit avant. Une capture plus longue prolonge le gel et l'annonce au Clocher.
Le seuil de sécurité est configurable (`--seuil-capture`), avec une valeur
**provisoire de 120 secondes**, à mesurer sur Raspberry Pi avant validation définitive.
Son dépassement abandonne la capture et exige une récupération administrative.
Le seuil est contrôlé entre les opérations d'E/S ; il ne peut interrompre un appel
noyau bloqué. Les joueurs restent dégelés pendant la résolution privée.

Dans la copie privée, la résolution du tour N suit l'ordre suivant :

1. effectuer l'audit complet des actions joueurs **une seule fois** ;
2. préparer les déplacements des forces ennemies déjà présentes à partir d'un état
   initial, puis appliquer ces déplacements sans qu'une unité puisse avancer deux
   fois à cause de l'ordre du parcours ;
3. effectuer les contrôles de cohérence nécessaires sans nouvelle sanction, fatigue
   ou décrémentation d'attente ;
4. créer entièrement la vague N+1 ; pour le front Est, lorsqu'une vague concerne
   plusieurs territoires, sa matérialisation suit `est_3 -> est_2 -> est_1` sans
   modifier les compositions ni les noms d'affichage produits par `vagues.py` ;
5. identifier les territoires en conflit ;
6. résoudre les combats dans l'ordre
   `village -> est_1 -> est_2 -> est_3` ;
7. pendant ces cascades, préparer et réserver les retraites tactiques admissibles ;
8. après tous les combats, appliquer physiquement les retraites exactement aux
   places réservées ;
9. calculer et sauvegarder le contrôle final, finaliser les rapports et vérifier la
   défaite ;
10. publier les nouveaux inodes sous un second gel court ; en l'absence de défaite,
    ouvrir **CONSULTATION 60 secondes**, puis le tour N+1 avec **ACTIONS 120 secondes**.

Au tour 0, l'étape 2 ne déplace personne parce qu'aucune force ennemie ancienne
n'existe encore ; la vague 1 apparaît néanmoins à l'étape 4.

Une nouvelle vague ne se déplace jamais pendant la résolution où elle apparaît.
Les priorités d'arrivée restent : occupants déjà présents, anciennes forces arrivant
ce tour, puis nouvelles apparitions.

Le timer et la résolution sont deux responsabilités séparées : `minuterie.py`
valide la durée et attend une échéance, sans logique métier. Le pilote appelle la
résolution après cette attente. La durée est configurable par le champ
`duree_phase_action_secondes` du profil ou par `--duree-action`. Les tests peuvent
la neutraliser avec 0 et injecter une horloge ainsi qu'une attente simulées.
`--duree-consultation`/`duree_consultation_secondes` et
`--duree-gel`/`duree_gel_secondes` configurent les deux autres durées, neutralisables
en test. `seuil_capture_secondes` doit rester supérieur au minimum de gel.

### API du cycle, état et reprise

- `survie.ouvrir_tour_survie()` prépare le plateau et les généraux selon les règles
  communes, puis enregistre la fenêtre d'action et son échéance. Un nouvel appel
  sur une fenêtre déjà ouverte conserve cette échéance sans répéter la préparation.
- `survie.resoudre_tour_survie()` capture, résout et publie directement une fenêtre
  ouverte, sans exiger l'expiration du timer d'action. Le gel reste effectif en
  production ; un gestionnaire et des horloges injectés rendent les tests sans
  attente. Il ouvre la consultation, mais pas la prochaine fenêtre d'action.
- `survie.lancer_partie_survie()` pilote les ouvertures, l'attente via
  `minuterie.attendre_jusqua()`, les résolutions et l'affichage des rapports jusqu'à
  la défaite, une interruption ou la limite optionnelle `nombre_tours`. Hors défaite,
  il attend la consultation puis ouvre la fenêtre suivante. À la limite de
  résolutions, la consultation reste persistée pour le prochain appel.

L'état privé `systeme/cycle_survie.json` contient `tour`, `phase` et, en phase
`actions` ou `consultation`, une `echeance` absolue. Les phases sont `preparation`,
`actions`, `capture`, `resolution`, `publication`, `consultation`, `recuperation`,
`a_preparer` et `defaite`. `generation` identifie la clôture en cours et
`generation_active` la dernière publication validée. Le fichier appartient à `root:root` en
`600` et est remplacé atomiquement. Le format et les transitions sont détaillés
dans `MYTHODEA_SPEC.md`, section 17.

Le verrou privé `systeme/verrou_cycle_survie` contient le PID et empêche deux
moteurs Survie concurrents, pendant l'attente comme pendant la résolution. Les
API directes d'ouverture et de résolution sont également protégées. Ce verrou
ne remplace pas le gel ni l'isolation par générations.

Une interruption pendant le timer conserve l'échéance : la reprise attend
seulement le temps restant en `actions` ou `consultation`, puis poursuit la
transition prévue. Changer la durée ne réinitialise pas une échéance enregistrée.
Les autres phases interrompues exigent une vérification administrative. Le verrou
est libéré normalement, y compris sur `Ctrl+C` ; après un arrêt brutal, sa présence
reste bloquante jusqu'à vérification et retrait explicite.

### Clôture Linux et générations privées

`cycle_linux.py` contrôle les slices `user-<UID>.slice` de j1/j2 sous `user.slice`
avec le freezer cgroup v2. Il démarre leurs gestionnaires systemd utilisateur afin
que ces slices existent aussi sans session ouverte, vérifie le confinement des
processus et attend `frozen 1` avant copie. Le moteur root doit être lancé depuis
un administrateur distinct, hors de ces slices. Un processus joueur hors de sa
slice, un gel extérieur ou un journal de gel résiduel fait refuser la clôture.
Les comptes joueurs ne doivent pas avoir de privilèges ni de services autorisés
à créer des producteurs hors de ces slices ; voir les prérequis Linux.

Le gel seul bloquerait inutilement les terminaux durant les combats. Les modes
Unix ou ACL seuls laisseraient les anciens descripteurs écrire. Le gel bref permet
la capture cohérente ; les copies indépendantes assurent ensuite la séparation.
Aucun montage, namespace, ACL supplémentaire ou partitionnement automatique n'est utilisé.

```text
/home/game/systeme/generations/g<tour>-<identifiant>/
  manifeste.json              capture validée, tour, liste blanche des états
  capture/game/               territoires, repli et états métier
  capture/homes/j1/           entrées general* du home uniquement
  capture/homes/j2/
  travail/                    copie indépendante, modifiée par le moteur commun
  resultat.json               présent seulement après résolution complète
  publication/game/           nouveaux inodes prêts à installer
  publication/anciens/        anciennes entrées retirées du plateau
  publication.json            journal durable de chaque remplacement
/home/.mythodea-publication/g<tour>-<identifiant>/
  nouveaux/j1/ et nouveaux/j2/
  anciens/j1/ et anciens/j2/
```

Ces parents sont `root:root 700`. Les dossiers/fichiers tactiques copiés conservent
leurs UID/GID réels et leurs modes ; l'audit détecte donc encore un mauvais
propriétaire. La copie est physique, vérifiée par SHA-256 et synchronisée sur disque.
Aucun hardlink ni symlink n'est créé ; un symlink ou objet spécial source est refusé.
Un hardlink source est copié comme un fichier indépendant.

La liste blanche `config.ETATS_METIER` est : `compteur_general_j1.txt`,
`compteur_general_j2.txt`, `compteur_general_bot.txt`, `positions_generaux.txt`,
`fatigue_generaux.txt`, `controle_territoires.txt`, `attente_repli.txt`, `meteo.txt`,
`crypte.json`, `compteur_creation_normale_j1.txt`, `compteur_creation_normale_j2.txt`.
Le cycle vivant, les verrous, générations, journaux de récupération, rapports et
Clocher sont exclus. Le marqueur local du résolveur dans `travail/systeme/` n'est
jamais publié. Le moteur commun utilise le contexte privé `config.racines_generation()`.

La publication prépare les copies avant le second gel, journalise chaque retrait
et installation, puis valide `generation_active` seulement après toutes les
opérations. Elle n'est pas une transaction atomique couvrant plusieurs dossiers :
le gel empêche les joueurs d'observer les remplacements partiels, et une panne
laisse un journal à examiner. Chaque renommage reste sur un même système de
fichiers ; le staging des homes est séparé pour permettre une partition dédiée
montée sur `/home/game`, sans automatiser sa création.

Les homes `/home/j1` et `/home/j2` eux-mêmes restent aux joueurs. Seules les
entrées réservées au jeu `general*` sont remplacées ; `.ssh`, les fichiers personnels,
le shell et l'historique ne sont pas touchés. Un ancien FD ou cwd continue de viser
les anciens inodes, sans effet sur la capture ou la nouvelle génération.
Après publication : **faire `cd ~`, puis revenir sur la carte**. Un éditeur qui
réouvre un chemin absolu vise, lui, la nouvelle génération : consultation n'est
pas une frontière anti-triche absolue.

Pendant consultation, les bits d'écriture des entrées tactiques alliées sont retirés.
À l'ouverture des actions, les modes normaux `700`/`600` sont restaurés sans changer
les propriétaires constatés. Les homes eux-mêmes restent inchangés. Les joueurs
propriétaires peuvent rétablir leurs modes : cette mesure facilite la lecture seule,
mais la protection du tour clôturé repose sur la copie privée.

Rapports alliés et Clocher : dossiers `root:mythodea_allies 750`, fichiers `640`.
Le journal technique reste `root:root 600`, comme compteurs, cycle, manifestes,
résultats, verrous et journaux de publication. Les rapports restent hors des
arborescences remplacées, lisibles avec `cat`, `tail -f` et `grep`.

### Récupération administrative

Les sorties interceptables dégèlent les joueurs dans un `finally`. Après `SIGKILL`
ou une panne, `systeme/gel_survie.json` indique le PID et les slices concernées.
`survie_admin.py diagnostic` affiche les marqueurs. Après vérification de l'arrêt
du processus, `degeler --confirmer` libère les sessions sans valider le jeu,
sans rétablir les permissions tactiques et sans supprimer le verrou. Le retrait
du verrou est une autre commande explicite ; un PID encore présent bloque ces opérations.

Une publication interrompue peut être reprise par `republier --generation ...
--confirmer` après examen du résultat terminé et du journal. L'outil accepte
uniquement la génération interrompue, conserve les traces précédentes et recrée
la publication depuis `travail/`, sans audit, vague ou combat supplémentaire.
Une capture ou résolution incomplète n'a pas ce chemin de reprise : conserver les
preuves, réparer/restaurer explicitement avec l'administrateur, sans modifier
aveuglément la phase pour forcer une relance. Aucun merge des écritures tardives.
Les commandes et contrôles exacts sont dans `TESTS_LINUX_SURVIE.md`.

Les générations sont conservées pour diagnostic ; leur purge est administrative,
moteur arrêté, après sauvegarde. Aucun nettoyage automatique ni partitionnement
n'est déclenché par le cycle.

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
uniquement la progression des anciennes forces puis l'apparition de la vague
demandée, sans déplacer la vague qu'elle vient de créer. Elle ne gère pas le timer,
les combats, le contrôle final, la défaite ou le passage au tour suivant.
Le cycle complet appelle séparément `avancer_ennemis()` puis
`creer_vague_est(numero_tour + 1, ...)`, après l'audit unique, pour intercaler un
contrôle de cohérence. Il n'appelle pas en plus `preparer_phase_ennemie()`, afin
de ne pas déplacer deux fois les anciennes forces.
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

Pendant la résolution complète d'un tour, une retraite tactique admissible est
**réservée puis appliquée plus tard**. Au moment du choix, le moteur vérifie la
destination, l'absence de bot actif restant sur ce territoire déjà résolu et la
première place disponible selon la règle `1..20`. Les réservations déjà acceptées
comptent comme des places occupées.

Si aucune destination ou place valide n'existe, le général reste engagé normalement.
Si la retraite est acceptée, le général est considéré comme en cours de fuite et
doit être exclu de toutes les relectures de combat suivantes, même si son dossier
physique n'a pas encore été déplacé. Après la résolution de tous les territoires,
les retraites acceptées sont appliquées exactement aux places réservées, sans refaire
un placement différent.

Une retraite finale ne doit jamais recréer un territoire contesté ni déclencher un
second combat. La remontée automatique des renforts **alliés** vers `1..4` n'est
pas définie ici et n'est pas déclenchée implicitement par la lecture des forces ou
la cascade.

### Séquence d'une cascade

1. Résoudre l'affrontement initial avec le moteur commun, sans consulter le choix
   de surnombre pour interrompre cet affrontement.
2. Remonter les premiers renforts vivants dans les places libres, dans leur ordre.
3. Relire les forces ; s'il reste des alliés et des ennemis, et que des renforts
   viennent de remonter, lire le fichier de chaque général allié survivant.
4. Hors village, pour ceux qui ont choisi `1`, préparer la retraite vers le voisin
   rapprochant le plus du village. Le territoire de destination a déjà été résolu
   grâce à l'ordre `village -> est_1 -> est_2 -> est_3`. La retraite n'est acceptée
   que si aucun bot actif n'y reste et si une place `1..20` peut être réservée.
   Ceux qui ont choisi `2` restent. Au village, aucun général ne part
   automatiquement, même si son fichier contient `1`.
5. Exclure les retraites acceptées des relectures de combat suivantes, sans encore
   les déplacer physiquement ; relancer le moteur si les deux camps ont encore des
   combattants non exclus. Les pertes précédentes restent sur disque.
6. Répéter la remontée et la consultation avant chaque nouvel affrontement.
7. Après la résolution de tous les territoires du tour, appliquer physiquement les
   retraites réservées aux destinations et places déjà décidées.

La cascade s'arrête si les ennemis ou les alliés non exclus sont éliminés, si tous
les alliés survivants ont une retraite acceptée, ou si aucun renfort n'a été promu
pour un affrontement supplémentaire. Elle ne contourne pas les limites de sécurité
du moteur commun. Les identités techniques, vagues, noms d'affichage et ordre de
colonne sont conservés. Le départage de routes équivalentes reste non défini et
provoque un refus explicite au lieu d'un choix arbitraire.

L'API est `survie.resoudre_cascade(territoire, configuration, mode_combat="OFF/OFF",
en_cours_de_fuite=None)`. Le cycle complet lui transmet une collection commune de
réservations ; les généraux acceptés sont exclus des relectures suivantes. Les
fonctions communes `mouvements.preparer_retraites_surnombre()` et
`mouvements.appliquer_retraites_surnombre()` séparent réservation et déplacement.
Sans collection, l'appel isolé de cascade conserve les retraites immédiates ; le
cycle complet utilise toujours les retraites différées. Les calculs de combat
restent ceux du moteur commun.

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
vague, ni nouveau tour : ces responsabilités appartiennent au cycle de `survie.py`.

---

## 16. Crypte V0.1

La Crypte est une mécanique pédagogique Linux du mode Survie, avec trois recettes :
`ame_et_lie_poulin` et `har-chez-moi` (quatre lignes), puis `pic-nic` (six lignes).
Elle ne dépend pas des futurs dieux ou manuscrits.
Chaque joueur dispose de :

```text
village/<joueur>/crypte/
├── grimoire/
│   ├── recette1.pdf
│   ├── recette2.pdf
│   └── recette3.pdf
├── atelier/
└── recompense/
```

Le grimoire contient trois PDF téléchargeables par SCP/SFTP, à lire sur l'ordinateur
du joueur. L'atelier est entièrement jetable : aucun document personnel ne doit
y être conservé. `recompense/` est une zone de récupération inactive, distincte
de la garnison, de la réserve et des renforts tactiques.

### Recette et observation

Dans son Bash normal, pendant ACTIONS, le joueur exécute une commande par ligne :

```bash
cd /home/game/village/j1/crypte/atelier
crypte_commence
mkdir appel
touch appel/cavalerie
cp appel/cavalerie appel/offrande
mv appel/offrande appel/poulin
crypte_fin
```

La seconde recette exerce la lecture, la redirection, le pipe et le filtrage :

```bash
crypte_commence
lsblk > a.txt
cat a.txt
cat a.txt | grep "NAME"
grep "NAME" a.txt
crypte_fin
```

La troisième recette met en évidence l'évolution des permissions :

```bash
crypte_commence
touch rempart
ls -l rempart
chmod 660 rempart
ls -l rempart
chmod 600 rempart
ls -l rempart
crypte_fin
```

Les trois `ls -l` sont trois étapes distinctes, avec leurs sorties visibles dans
le terminal. Les permissions initiales dépendent de l'umask ; après `chmod 660`,
elles sont `-rw-rw----`, puis `-rw-------` après `chmod 600`. Le collecteur exige
le nombre d'étapes de la recette choisie, sans limite fixe de quatre étapes.

Pour j2, le chemin d'atelier contient `j2`. La première ligne sélectionne la
recette, sans commande de sélection supplémentaire. Les commandes sont réellement
exécutées par le shell ; les sorties de `cat` et de `grep` restent visibles.
Chaque ligne doit correspondre exactement à la recette, guillemets, arguments,
redirection et ordre compris. Le seul pipeline autorisé est celui de recette2.
Aucune commande supplémentaire entre les marqueurs n'est admise :
`ls`, `clear`, `cd`, autre pipeline, liste avec `;` ou sous-shell invalident la tentative.
Un alias ou une fonction remplaçant une commande attendue est refusé. Chaque
étape requiert la ligne attendue et un code retour nul. La fin prématurée, Ctrl+C
et une erreur de syntaxe ne donnent aucune récompense.

Le contrôle final de recette1 exige uniquement `appel/`, contenant les deux
fichiers ordinaires vides sans lien `cavalerie` et `poulin`. Aucun mode `600`
n'est imposé à ces fichiers d'exercice : la recette ne contient plus `chmod`.
Pour recette2, l'atelier contient uniquement le fichier ordinaire sans lien
`a.txt`, avec le motif `NAME`. Le tableau de `lsblk` dépend de la machine et
n'est pas comparé à un inventaire figé.
Pour recette3, l'atelier contient uniquement le fichier ordinaire vide sans lien
`rempart`, dont les permissions finales doivent être exactement `600`.

Le scanner officiel utilise `DEBUG`, la ligne complète de l'historique Bash en
mémoire et `PROMPT_COMMAND`. Ce dernier relève aussi les erreurs de syntaxe qui
ne déclenchent pas `DEBUG`. Les filtres d'historique sont neutralisés temporairement
et restaurés à la fin ; un historique personnel grand ou illimité n'est pas réduit.
Une ligne produit un événement `before`, puis éventuellement `component` pour
les autres commandes internes, et un seul `after`. Le collecteur vérifie les
deux composants exacts du pipeline sans avancer de deux étapes. `after.status`
contient `$?` et `after.command` contient les codes de `PIPESTATUS`, capturés
dès le retour à l'invite. Le pipeline exige les deux codes `0 0`, même si le
dernier composant a réussi. Les anciens hooks doivent être réinstallés.
La configuration privée `systeme/crypte_config.json` contient `debut` et `fin`, par
défaut `crypte_commence` et `crypte_fin`. Ces noms doivent être distincts et respecter
`crypte_[a-zA-Z0-9_]+`. Ils ne viennent pas de l'environnement du joueur. Après une
modification administrative, réinstaller les hooks et reconnecter les joueurs ;
le grimoire est actualisé par la préparation du cycle.

`crypte_installer.py` fournit les hooks et le client depuis
`/usr/local/lib/mythodea/` (`root:root`, dossiers `755`, fichiers `644`) et leur
chargement depuis `/etc/profile.d/mythodea-crypte.sh`. Le `.bashrc` joueur n'est
pas la source officielle. Les fonctions sont chargées dans le shell existant,
sans mini-shell ni interprétation de commandes par le moteur.

Le scanner est volontairement contournable par modification du shell ou du PATH.
Il n'est pas une frontière anti-triche. Une observation envoyée au moteur ne
permet jamais de choisir un numéro de général, d'écrire son cooldown ou de rejouer
une attribution. Les fichiers et variables du joueur ne déclarent pas une réussite
officielle : seul le collecteur valide et persiste cette décision.

### Collecteur et persistance

Le pilote `lancer_partie_survie()` héberge un collecteur local en parallèle de
l'attente. Le timer reste indépendant de la logique métier. Les tests peuvent
désactiver uniquement le service socket avec `collecteur_crypte=False` et appeler
directement le collecteur ou la résolution sans attendre.

Le socket est `/home/game/communication/crypte.sock` : dossier
`root:mythodea_allies 750`, socket `root:mythodea_allies 660`. Il reçoit des messages
JSON bornés en taille ; il n'exécute jamais leur texte. L'UID est obtenu par
`SO_PEERCRED`. Le collecteur vérifie aussi l'ascendance du client, l'UID de sa session,
son PID et son instant de démarrage dans `/proc`, ainsi que son répertoire réel.
Une tentative est liée au joueur, à cette session et au tour. Son identifiant
aléatoire et le numéro croissant de chaque événement empêchent le rejeu.

La progression reste en mémoire du moteur ; aucune tentative ouverte n'est reprise
après redémarrage. Une nouvelle tentative remplace l'ancienne sans pouvoir la
continuer. La disparition du processus de session est observée sans dépendre des
hooks EXIT/HUP de Bash. Elle invalide la tentative et nettoie l'atelier.

`systeme/crypte.json` est un état atomique privé `root:root 600`, avec une entrée
par joueur :

- `dernier_tour` : tour de la dernière réussite acceptée, ou `null` ;
- `a_creer` : identifiant, tour et `recette` (`recette1`, `recette2` ou `recette3`) d'une
  réussite attendant sa matérialisation ;
- `en_attente` : identité technique de la récompense non encore récupérée ;
- `attributions` : historique des identifiants, tours, recettes et généraux attribués.

Les anciennes entrées sans champ `recette` désignent recette1 ; une récompense
historique reste donc une récompense de cavalerie.

Au début et à la validation finale, le moteur contrôle ACTIONS et son échéance,
le cooldown et l'absence de récompense en attente. La condition est
`dernier_tour is None` ou `tour >= dernier_tour + 5`, indépendamment pour j1 et j2.
Ce délai est global à la Crypte pour un joueur, partagé entre toutes les recettes.
Erreur, refus, abandon et déconnexion ne consomment pas ce délai. Le cooldown est
enregistré atomiquement avec la réussite acceptée, pas avec une déclaration locale.
Une seule récompense, déjà publiée ou encore `a_creer`, est autorisée par joueur.

### Récompense et cycle sécurisé

Après acceptation pendant ACTIONS : fermeture des demandes, gel, invalidation des
tentatives inachevées, nettoyage, capture privée, résolution, matérialisation privée,
puis publication. Le nettoyage utilise des descripteurs de dossiers et ne suit
pas les symlinks vers l'extérieur. Il ne parcourt jamais grimoire ou recompense.
Après une commande erronée, le nettoyage attend son retour avant de vider l'atelier.
Une anomalie empêchant un nettoyage sûr bloque la clôture pour vérification.

La récompense est `generalN`, avec le nom et la composition de la recette :

- recette1 : `nom_affichage=ame_et_lie_poulin`, 20 cavaliers (10/5/5/0) ;
- recette2 : `nom_affichage=har-chez-moi`, 20 archers (0/0/0/20) ;
- recette3 : `nom_affichage=pic-nic`, 20 piquiers (6/7/7/0).

L'ordre des blocs est avant/droite/gauche/arrière. Elle est créée uniquement
dans la génération privée à `village/<joueur>/crypte/recompense/generalN`, puis
publiée. Elle ne participe ni au contrôle ni au combat tant qu'elle attend là.
Elle ne consomme aucune des cinq créations normales ; le compteur technique
commun continue à croître et ne réutilise jamais un numéro.

Pendant ACTIONS, le joueur choisit une destination légale et utilise un vrai `mv` :

```bash
mv /home/game/village/j1/crypte/recompense/general7 /home/game/village/j1/garnison/1/
```

La position logique d'origine est le village. Les limites, identités, collisions,
déplacements, fatigue, combats et destructions utilisent le moteur commun.
L'audit unique constate la récupération et ferme la zone à ce général. Un retour
ultérieur dans `recompense/` est une infraction, sanctionnée par le repli commun.
Comme les autres déplacements de dossiers, cette règle s'applique aux positions
constatées lors de l'audit ; les allers-retours entre deux observations ne constituent
pas un historique de mouvements enregistré par le moteur.

Grimoire : dossier `root:<groupe_joueur> 750`, PDF `640`. Atelier, zone de récupération
et généraux sont privés au joueur (`700`/`600`), avec le retrait d'écriture prévu
pendant CONSULTATION. Les états, compteurs et configuration restent privés root.

Une interruption pendant capture/résolution/publication conserve les règles de
récupération du cycle. Une republication administrative utilise le résultat terminé
sans réexécuter ni audit, ni recette, ni création de récompense. Une socket résiduelle
reste bloquante : son retrait est une décision administrative explicite après
vérification de l'arrêt du moteur. Les commandes sont dans `TESTS_LINUX_SURVIE.md`.
