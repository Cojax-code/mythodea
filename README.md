# Mythodea

Mythodea est un jeu de stratégie au tour par tour construit autour de Linux.

Ici, le système de fichiers fait partie du jeu : les joueurs sont des comptes Linux,
les généraux sont des dossiers, les unités sont des sous-dossiers et déplacer un
général revient réellement à déplacer son dossier sur le serveur.

Le projet sert à la fois de jeu et de terrain d'apprentissage pour Linux, SSH,
permissions Unix et Python.

## État actuel

La branche V1.5 contient le moteur classique `j1 contre j2`, désormais découpé en
modules. Le gameplay reste basé sur le même moteur de déplacement, de sécurité et
de combat.

La V1.5 est considérée comme la base stable du moteur classique. Le système complet
d'ordres n'est volontairement pas bloquant pour clôturer cette version : seuls les
comportements déjà validés sont conservés, et les autres ordres seront affinés plus
tard à partir de l'expérience de jeu.

La V2.0 propose un prototype Survie Est jouable qui réutilise le moteur commun.
La validation réelle sous Linux / Raspberry Pi se poursuit pendant son développement.

## Lancer le jeu

Mythodea est prévu pour Linux / Raspberry Pi OS.

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

Chaque fenêtre d'action dure 120 secondes, y compris le tour 0. Une annonce directe sur les terminaux SSH
précède un gel d'au moins 10 secondes pour capturer les actions. Les sessions
reprennent pendant la résolution privée : anciennes forces, vague suivante,
combats. La vague 1 apparaît à la résolution du tour 0. Un second gel court publie
le résultat, puis une consultation de 60 secondes précède les nouvelles actions.
Après publication, faire `cd ~` puis revenir sur la carte.

Le temps est lisible avec `cat /home/game/village/clocher/etat_tour.txt` ou
`tail -f /home/game/village/clocher/suivi_tour.log`.

Commencez par `village/<joueur>/hotel_de_ville/journal_du_Toonitruand/vague_0.txt`.
L’Hôtel de Ville contient aussi le bilan `rapport.txt` et le `courrier/` (prototype
sans traitement de requêtes). Les états techniques se trouvent sous `.systeme/`.
Les anciennes structures sont refusées ; archiver la partie et réinstaller les
hooks Crypte avant une nouvelle partie.

La Crypte V0.1 propose trois recettes Linux, documentées dans les PDF
`recette1.pdf`, `recette2.pdf` et `recette3.pdf` sous
`village/<joueur>/crypte/grimoire/` (SCP/SFTP).
L'administrateur installe ou met à jour les hooks Bash officiels, puis les joueurs se
reconnectent :

```bash
sudo python3 python/crypte_installer.py
```

Une réussite pendant ACTIONS prépare un général bonus de 20 cavaliers, archers ou piquiers, publié
après la résolution dans `crypte/recompense/`. Il reste à récupérer avec `mv`.
Une réussite tous les cinq tours, partagée entre toutes les recettes, est permise par joueur, hors quota normal des
cinq créations. Voir [les vérifications Linux de la Crypte](TESTS_LINUX_SURVIE.md#crypte-v01).

Pour un essai borné sans attendre :

```bash
bash bash/start.sh --mode survie --duree-action 0 --duree-gel 0 --duree-consultation 0 --tours 1
```

`Ctrl+C` pendant l'attente conserve l'échéance pour la reprise. Une capture,
résolution ou publication interrompue exige une récupération administrative ; les
[commandes de diagnostic et de dégel](TESTS_LINUX_SURVIE.md#récupération-administrative)
ne rejouent aucun audit ou combat. Ne pas alterner classique et Survie sur une même
partie : les identités et fichiers d'état sont communs. L'installation et le
nettoyage restent classiques.

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

- `MYTHODEA_SPEC.md` : référence des règles actuelles et de l'architecture.
- `SURVIE_SPEC.md` : règles et décisions de conception propres au mode Survie V2.0.

Mythodea est encore en développement : la V1.5 stabilise le moteur commun, et la
V2.0 propose le cycle Survie du front Est. Les ordres supplémentaires seront
introduits progressivement lorsqu'ils apporteront une vraie valeur au gameplay.
