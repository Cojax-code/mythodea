# Mythodea

Mythodea est un jeu de stratégie au tour par tour construit autour de Linux.

Ici, le système de fichiers fait partie du jeu : les joueurs sont des comptes Linux,
les généraux sont des dossiers, les unités sont des sous-dossiers et déplacer un
général revient réellement à déplacer son dossier sur le serveur.

Le projet sert à la fois de jeu et de terrain d'apprentissage pour Linux, SSH,
permissions Unix et Python.

## État actuel

La branche `v2.0` rassemble le moteur commun du mode classique (`j1` contre
`j2`) et le cycle jouable du mode Survie Est. Les combats et la progression
utilisent les **étiquettes**, les PC et le soutien du QG, à la place des
anciens ordres de combat. `info/ordre_surnombre.txt` reste réservé aux décisions
de retraite et de poursuite du mode Survie.

Les premiers essais Raspberry Pi avec joueurs SSH ont validé la montée de niveau,
les gains et la récompense de commandement (Stratège à 13 PC). Les corrections
d’arborescence et d’accueil demandent encore leur essai sur cette machine ;
les procédures distinguent ces contrôles des tests automatisés Linux/WSL.
Les règles applicables sont décrites dans [REGLES_V2.md](REGLES_V2.md),
[MYTHODEA_SPEC.md](MYTHODEA_SPEC.md) et [SURVIE_SPEC.md](SURVIE_SPEC.md).

## Lancer le jeu

Mythodea est prévu pour Linux / Raspberry Pi OS.

Avant le premier lancement, l'administrateur doit créer et monter manuellement une
partition dédiée sur `/game`. Le jeu ne partitionne ni ne formate les disques.
Les homes `/home/j1`, `/home/j2` et le dépôt (par exemple `/home/cojax/mythodea`)
restent séparés. Voir [la préparation Raspberry](TESTS_LINUX_SURVIE.md#partition-dédiée-sur-le-raspberry).

Pour installer et lancer le **mode classique**, depuis la racine du dépôt :

```bash
sudo bash bash/instal.sh
bash bash/start.sh
```

Pour remettre complètement le plateau à zéro :

```bash
sudo bash bash/nettoyage.sh
```

Le moteur peut aussi être lancé directement :

```bash
sudo python3 python/mythodea_v_1_5.py
```

Sans option, le lancement conserve le mode classique. Il peut aussi être explicite :

```bash
bash bash/start.sh --mode classique
```

La configuration du prototype Survie Est est consultable sans modifier le plateau :

```bash
python3 -B python/mythodea_v_1_5.py --mode survie --afficher-configuration
```

Le prototype Survie Est est jouable sur un plateau dédié, avec les comptes Linux
`j1` et `j2`. Préparer aussi le groupe allié et vérifier systemd/cgroup v2 selon
[la procédure Linux](TESTS_LINUX_SURVIE.md), puis lancer depuis le compte administrateur :

```bash
bash bash/start.sh --mode survie
```

Pour Survie, ne pas utiliser les scripts d'installation/nettoyage classiques :
ils créent une autre carte. Le moteur crée les zones Survie sur un plateau dédié
et refuse de démarrer si des territoires ou rapports territoriaux classiques
subsistent. Une ancienne partie doit être archivée séparément par l'administrateur.

Pour détruire la partie Survie actuelle et repartir de zéro, moteur arrêté :

```bash
sudo bash bash/reset_survie.sh
bash bash/start.sh --mode survie
```

Le reset vide `/game` sans retirer son montage et ne supprime que `general*` dans
les homes ; `.ssh` et les fichiers personnels sont conservés.

Chaque fenêtre d'action dure 120 secondes, y compris le tour 0. Une annonce directe sur les terminaux SSH
précède un gel d'au moins 10 secondes pour capturer les actions. Les sessions
reprennent pendant la résolution privée : anciennes forces, vague suivante,
combats. La vague 1 apparaît à la résolution du tour 0. Un second gel court publie
le résultat, puis une consultation de 60 secondes précède les nouvelles actions.
Après publication, faire `cd ~` puis revenir sur la carte.

Le temps est lisible avec `cat /game/village/clocher/etat_tour.txt` ou
`tail -f /game/village/clocher/suivi_tour.log`.

Commencez par `village/<joueur>/hotel_de_ville/journal_du_Toonitruand/vague_0.txt`.
L’Hôtel de Ville contient aussi le bilan `rapport.txt` et le `courrier/`, qui accepte
`FLAG <flag>` pour les mini-défis. Les états techniques sont sous `.systeme/`.
Les anciens plateaux incompatibles sont refusés ; les informations des généraux
encore à leur racine sont en revanche migrées sous gel vers `info/`, sans écrasement.
Voir [compatibilité et migration](MYTHODEA_SPEC.md#5-généraux).

La Crypte propose trois recettes Linux dans son grimoire PDF et des récompenses
hors quota normal. Installation des hooks, tests bornés, sauvegardes et récupération
après interruption : [procédure Linux](TESTS_LINUX_SURVIE.md).
Une résolution interrompue ne doit jamais être relancée en modifiant sa phase :
la récupération administrative ne rejoue ni audit ni combat.

## Organisation

```text
bash/                 scripts d'installation, lancement et nettoyage
python/               moteur du jeu
.dev/tests/           tests automatiques (développement)
MYTHODEA_SPEC.md      règles et architecture de référence
SURVIE_SPEC.md        conception du mode Survie V2.0
```

Le point d'entrée Python est volontairement léger ; les règles sont réparties entre
les modules de généraux, mouvements, sécurité, combats, rapports, état et plateau.

## Tests

Depuis la racine du dépôt :

```bash
python3 -B -m unittest discover -s .dev/tests -v
```

Le dossier `.dev/` est versionné dans Git. Sous Linux, `ls` le masque et `ls -a`
l'affiche. Les validations Linux spécifiques restent dans `python/tests_linux/` ;
leur procédure est décrite dans [TESTS_LINUX_SURVIE.md](TESTS_LINUX_SURVIE.md).

Les tests utilisent un plateau temporaire. Ils ne remplacent pas la validation des
vrais comptes, UID/GID et permissions sur Linux.

## Documentation

- [REGLES_V2.md](REGLES_V2.md) : progression, étiquettes, QG et Messager.
- [MYTHODEA_SPEC.md](MYTHODEA_SPEC.md) : moteur commun, formats et invariants.
- [SURVIE_SPEC.md](SURVIE_SPEC.md) : cycle et règles du mode Survie Est.
- [EVOLUTIONS.md](EVOLUTIONS.md) : bâtiments, formation et évolutions.
- [TESTS_LINUX_SURVIE.md](TESTS_LINUX_SURVIE.md) : tests Linux et préparation Raspberry Pi.
- [AGENTS.md](AGENTS.md) : instructions de travail pour les agents de développement.

Mythodea v2.0 reste en développement. Les décisions futures de la v2.1
(notamment la fuite volontaire et les terrains) ne sont pas des règles actives.
