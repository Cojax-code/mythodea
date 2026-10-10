# Validation et exploitation Linux du cycle Survie

La suite ordinaire simule les droits. `python/tests_linux/test_permissions_reelles.py`
éprouve réellement les UID/GID, droits Unix, inodes, cgroup v2 et la récupération.
Les tests automatiques s'exécutent dans `/tmp`, jamais sur une partie `/home/game`.
Ils créent puis retirent j1/j2 et le groupe allié ; ils refusent de démarrer si ces
comptes ou ce groupe existent déjà. Utiliser une VM/installation Linux dédiée et
jetable, démarrée avec systemd, avec Python 3, `loginctl`, `ps` et les outils de comptes Unix.

```bash
sudo python3 -B python/tests_linux/test_permissions_reelles.py
sudo python3 -B -m unittest discover -s python/tests_linux -v
python3 -B -m unittest discover -s .dev/tests -v
```

Ne pas lancer `instal.sh`/`nettoyage.sh` pour ces tests : le nettoyage classique
efface les homes entiers. Ces scripts ne servent pas à migrer une partie Survie.

## Préparation du serveur de jeu

Les commandes suivantes concernent le serveur de démonstration, avec un plateau
dédié sans ancienne partie classique ni anciens rapports territoriaux classiques.
Le moteur refuse ce mélange sans le nettoyer : faire archiver séparément l'ancienne
partie par l'administrateur. Garder une session administrateur distincte ouverte.
Une seule session SSH principale par joueur suffit ; toutes les sessions SSH
avec un terminal valide reçoivent les annonces. Le moteur doit
être lancé depuis l'administrateur, jamais depuis un `sudo` dans la session j1/j2.

```bash
id j1 >/dev/null 2>&1 || sudo useradd --create-home --shell /bin/bash j1
id j2 >/dev/null 2>&1 || sudo useradd --create-home --shell /bin/bash j2
id j1
id j2
stat -fc %T /sys/fs/cgroup
systemctl --version
command -v loginctl
command -v ps
sudo groupadd -f mythodea_allies
sudo usermod -aG mythodea_allies j1
sudo usermod -aG mythodea_allies j2
sudo install -d -o root -g root -m 755 /home/game
sudo install -d -o root -g root -m 700 /home/game/systeme
sudo install -d -o root -g root -m 700 /home/.mythodea-publication
sudo python3 python/crypte_installer.py
ls -ld /home /home/game /home/j1 /home/j2
```

Résultat attendu : `cgroup2fs`, UID joueurs distincts et non nuls, homes conservés
en `j1:j1 700` et `j2:j2 700`, parents du plateau non modifiables par les joueurs.
Reconnecter les sessions joueurs après l'ajout au groupe. Ne pas modifier `.ssh`.

Les comptes joueurs ne doivent avoir ni sudo/root, ni accès à Docker/LXD ou à un
service privilégié leur permettant de sortir de leur slice. Ne pas leur attribuer
de tâches cron/at ni de services système hors `user-<UID>.slice` : le gel doit
couvrir tous les producteurs des données. Les services utilisateur systemd, eux,
doivent rester dans cette slice. Vérifier notamment :

```bash
sudo -l -U j1
sudo -l -U j2
sudo crontab -u j1 -l
sudo crontab -u j2 -l
sudo systemd-cgls /user.slice
```

Le moteur contrôle les UID réels/effectifs/sauvegardés et les groupes de processus
dans `/proc`, avant et pendant les gels. Un processus joueur hors confinement
provoque un refus, jamais un faux gel réussi. Cela ne remplace pas la configuration
des services de connexion/PAM du serveur. Dans chaque session SSH joueur :

```bash
id
cat /proc/self/cgroup
```

La ligne cgroup doit être sous `/user.slice/user-<son UID>.slice/`. Vérifier depuis
l'administrateur, à la racine du dépôt, que cette annonce arrive bien dans tous
les terminaux joueurs (ouvrir aussi une seconde session j1 pour ce contrôle) :

```bash
sudo python3 -B -c 'import sys; sys.path.insert(0, "python"); import config, cycle_linux; cycle_linux.Linux(config.configuration_mode("survie")).annoncer("TEST MYTHODEA : annonce avant gel")'
```

Ce contrôle envoie uniquement une annonce, sans geler les slices ni lancer de tour.
Le champ `TTY` de `loginctl` peut être vide : le moteur cherche alors `pts/N` dans
le nom de l'enfant joueur du `Leader` SSH. Il vérifie le propriétaire réel du
terminal avant d'écrire directement dessus en root. `wall` et `mesg y` ne sont
pas nécessaires. Une session sans terminal (SFTP, par exemple) est ignorée.

Le moteur démarre `user@<UID>.service` afin de maintenir les slices même sans SSH.
Il ne tue pas les sessions et n'utilise ni ACL supplémentaire, bind mount ou namespace.
La partition dédiée à `/home/game` reste un exercice manuel ; les homes et leur
staging restent sur le même système de fichiers. Monter la partition sur ce chemin,
sans remplacer le chemin par un symlink, et conserver les propriétaires requis.

## Vérifier une fenêtre ACTIONS

Depuis l'administrateur, lancer normalement :

```bash
bash bash/start.sh --mode survie
```

Pendant ACTIONS, les commandes administratives suivantes doivent réussir. Les
petits `sudo -u` sont des sondes ponctuelles à terminer avant le gel ; pour les
processus longs, utiliser les véritables sessions SSH confinées des joueurs.

```bash
ls -ld /home/game/village /home/game/est_{1,2,3} /home/game/repli
sudo ls -ld /home/game/village/j{1,2}/{garnison,reserve,renforts}
sudo ls -ld /home/game/village/j{1,2}/renforts/{5,20} /home/game/repli/j{1,2}
sudo stat -c '%U:%G %a %n' /home/j{1,2}/general1 /home/j{1,2}/general1/ordre.txt
sudo -u j1 sh -c 'test -w /home/j1/general1/ordre.txt && printf "1-2\n" > /home/j1/general1/ordre.txt'
sudo -u j2 sh -c 'test -w /home/j2/general1/ordre.txt && printf "1-2\n" > /home/j2/general1/ordre.txt'
sudo -u j1 touch /home/game/village/j1/reserve/.sonde
sudo -u j1 rm /home/game/village/j1/reserve/.sonde
sudo -u j2 touch /home/game/village/j2/renforts/5/.sonde
sudo -u j2 rm /home/game/village/j2/renforts/5/.sonde
```

Les sondes suivantes doivent être **refusées**, même en ACTIONS :

```bash
sudo -u j1 cat /home/j2/general1/ordre.txt
sudo -u j1 touch /home/game/village/j2/reserve/.interdit
sudo -u j2 touch /home/game/est_3/bot/.interdit
sudo -u j1 cat /home/game/systeme/cycle_survie.json
sudo -u j2 sh -c 'echo interdit >> /home/game/systeme/compteur_general_j2.txt'
sudo -u j1 cat /home/game/rapport/rapport_long.txt
```

Contrôler les états privés et les informations alliées depuis l'administrateur :

```bash
sudo find /home/game/systeme -maxdepth 1 -type f -exec stat -c '%U:%G %a %n' {} +
sudo stat -c '%U:%G %a %n' /home/game/est_3/bot /home/game/systeme /home/game/systeme/generations
sudo stat -c '%U:%G %a %n' /home/game/rapport /home/game/rapport/rapport_court.txt /home/game/clocher /home/game/clocher/etat_tour.txt
sudo -u j1 cat /home/game/clocher/etat_tour.txt
sudo -u j2 cat /home/game/rapport/rapport_court.txt
```

États privés : `root:root 600`, parents `700`. Informations alliées :
`root:mythodea_allies`, dossiers `750`, fichiers `640`. Jamais `604`.

## Observer clôture, résolution et consultation

Dans une session joueur, suivre le Clocher, puis interrompre seulement `tail` avec
Ctrl+C pour revenir au shell :

```bash
tail -f /home/game/clocher/suivi_tour.log
```

À expiration : l'annonce directe arrive dans chaque terminal SSH avant le gel,
sans attendre le dégel pour apparaître. Le terminal est suspendu au moins
10 secondes, puis reprend pendant la résolution privée. Depuis l'administrateur,
pendant la capture :

```bash
sudo cat /sys/fs/cgroup/user.slice/user-$(id -u j1).slice/cgroup.events
sudo cat /sys/fs/cgroup/user.slice/user-$(id -u j2).slice/cgroup.events
sudo cat /home/game/systeme/gel_survie.json
```

Attendre `frozen 1` ; le gel est effectif, pas simplement un `sleep`. Si la capture
dépasse 10 secondes, le Clocher annonce sa prolongation. Le seuil de 120 secondes
est provisoire et configurable avec `--seuil-capture` : mesurer sur le Raspberry Pi.

Pendant la résolution, les joueurs sont dégelés. Ils ne peuvent pas atteindre
`systeme/generations/.../travail/`, même lorsque les fichiers intérieurs portent
leur UID. Root peut y écrire. Les tests automatisés vérifient réellement cette
séparation et une écriture via un FD ouvert avant capture : elle n'affecte ni la
copie privée ni les nouveaux inodes publiés. Ne pas éditer manuellement `travail/`
pendant une résolution normale.

Après le second gel de publication, dans chaque session joueur :

```bash
cd ~
cat /home/game/clocher/etat_tour.txt
ls -l general1/ordre.txt
test -w general1/ordre.txt
grep 'contrôle final' /home/game/rapport/rapport_court.txt
```

En CONSULTATION, `test -w` échoue et `cat` réussit. Après 60 secondes, ACTIONS
rétablit `700`/`600` et `test -w` réussit. Les homes eux-mêmes restent aux joueurs.
Un propriétaire peut contourner ces modes avec `chmod` ; la copie privée protège
le tour clôturé indépendamment de cette mesure de consultation.

Un FD ou cwd conservé vise encore l'ancien inode. Un éditeur peut aussi réouvrir
un chemin absolu : refermer les anciens éditeurs puis rouvrir les fichiers publiés.
Les rapports restent hors des générations ; `suivi_tour.log` garde son inode.

## Récupération administrative

Un second moteur doit être refusé tant que le premier tient le verrou. Ne jamais
supprimer un verrou simplement parce qu'il paraît ancien. Depuis l'administrateur :

```bash
sudo python3 python/survie_admin.py diagnostic
sudo cat /home/game/systeme/verrou_cycle_survie
```

Contrôler le PID affiché, son propriétaire, sa commande et sa date de démarrage
avec `ps -p <PID> -o pid,user,lstart,args`. Arrêter proprement le moteur s'il tourne.
Un PID encore présent, même réutilisé par un autre processus, bloque l'outil :
ne pas forcer la suppression sans enquête administrative.

Si le moteur est réellement arrêté et des joueurs restent gelés :

```bash
sudo python3 python/survie_admin.py degeler --confirmer
sudo python3 python/survie_admin.py diagnostic
```

Cette commande rend les sessions utilisables, sans valider la partie, sans
restaurer les droits tactiques, sans supprimer le verrou et sans rejouer le moteur.
Elle ne dégèle que les slices consignées. Après un reboot, elles peuvent déjà
avoir disparu ; le journal nécessite quand même un examen.

Examiner `cycle_survie.json`, puis `manifeste.json`, `resultat.json` et
`publication.json` dans la génération indiquée. `preparee`, `ancien_retire` et
`installee` tracent chaque renommage ; un arrêt peut se produire entre l'opération
et l'écriture du marqueur. Comparer les chemins source/destination/ancien au disque.

Après vérification, retirer explicitement le verrou résiduel :

```bash
sudo python3 python/survie_admin.py retirer-verrou --confirmer
```

Si, et seulement si, la résolution est terminée (`resolution_terminee: true`) et
la publication a été interrompue, vérifier la génération avant republication :

```bash
GENERATION=$(sudo python3 -c 'import json; print(json.load(open("/home/game/systeme/cycle_survie.json"))["generation"])')
sudo cat "/home/game/systeme/generations/$GENERATION/resultat.json"
sudo cat "/home/game/systeme/generations/$GENERATION/publication.json"
sudo python3 python/survie_admin.py republier --generation "$GENERATION" --confirmer
```

Les traces précédentes sont archivées et la publication est reconstruite depuis
`travail/`, sans rejouer les combats, puis la consultation reprend. Une capture ou
résolution incomplète ne peut pas être republiée. Conserver ses fichiers, diagnostiquer
et convenir d'une réparation/restauration administrative ; ne pas passer simplement
la phase à `actions`, ce qui risquerait de rejouer des effets déjà appliqués.

`Ctrl+C` pendant ACTIONS/CONSULTATION conserve l'échéance ; relancer le moteur
reprend le temps restant. `SIGKILL` peut laisser les sessions gelées : la session
administrateur distincte et la commande de dégel ci-dessus sont indispensables.

Surveiller l'espace disque : les générations et archives de publication ne sont
pas purgées automatiquement. Sauvegarder avant toute purge, moteur arrêté ; garder
la génération active et celle de toute récupération en cours.

## Crypte V0.1

Python 3.11 ou supérieur est requis pour le nettoyage Unix avec `dir_fd`.
L'installation administrative ci-dessus copie les hooks et le client dans
`/usr/local/lib/mythodea` et crée `/etc/profile.d/mythodea-crypte.sh`. Reconnecter
les sessions joueurs après installation. Elle ne modifie aucun `.bashrc` personnel.
Ne pas sourcer `bash/prototype_crypte_scan.sh` directement dans une partie : ce
fichier seul écrit le journal du prototype, sans collecteur moteur.

Depuis l'administrateur, après préparation du plateau par le lancement Survie :

```bash
ls -ld /home/game/communication /home/game/systeme
ls -ld /home/game/village/j1/crypte/{grimoire,atelier,recompense}
sudo stat -c '%U:%G %a %n' /home/game/systeme/crypte*.json
sudo stat -c '%U:%G %a %n' /home/game/systeme/compteur_creation_normale_*.txt
stat -c '%U:%G %a %n' /usr/local/lib/mythodea/crypte.bash
sudo -u j1 cat /home/game/systeme/crypte.json
sudo -u j2 cat /home/game/systeme/crypte.json
sudo -u j1 test -w /usr/local/lib/mythodea/crypte.bash
```

Les lectures privées et le test d'écriture doivent échouer. Les états sont
`root:root 600` ; le script officiel est `root:root 644` sous dossier `755`.
Le socket, pendant l'exécution du moteur, est `root:mythodea_allies 660`, son
parent `750`. Le moteur obtient l'identité par le noyau, pas par un champ joueur.

Après mise à jour des recettes, réinstaller les hooks avec
`sudo python3 python/crypte_installer.py`, puis reconnecter les joueurs.
Depuis le PC du joueur (remplacer l'adresse), télécharger les PDF :

```bash
scp j1@ADRESSE_DU_PI:/home/game/village/j1/crypte/grimoire/recette1.pdf .
scp j1@ADRESSE_DU_PI:/home/game/village/j1/crypte/grimoire/recette2.pdf .
scp j1@ADRESSE_DU_PI:/home/game/village/j1/crypte/grimoire/recette3.pdf .
```

Dans sa session SSH principale, pendant ACTIONS, après avoir lu le PDF :

```bash
type crypte_commence crypte_fin
cd /home/game/village/j1/crypte/atelier
crypte_commence
mkdir appel
touch appel/cavalerie
cp appel/cavalerie appel/offrande
mv appel/offrande appel/poulin
crypte_fin
```

Résultat attendu : « Réussite enregistrée », atelier vide, aucune récompense avant
publication. Après publication, faire `cd ~`, puis revenir consulter
`/home/game/village/j1/crypte/recompense`. Un seul `generalN` doit apparaître, avec
`nom_affichage=ame_et_lie_poulin` et 20 équipements `cheval`, répartis 10/5/5/0.
Lors des prochaines ACTIONS, déplacer ce dossier avec `mv` vers une place légale
libre de la garnison. Remplacer `generalN` par le nom réellement attribué.

Pour recette2, après récupération et expiration du même cooldown (ou avec j2
dans son propre atelier) :

```bash
crypte_commence
lsblk > a.txt
cat a.txt
cat a.txt | grep "NAME"
grep "NAME" a.txt
crypte_fin
```

Le tableau complet apparaît avec `cat`, puis les lignes contenant `NAME` avec
les deux formes de `grep`. Le pipeline compte pour une étape. Après publication,
la récompense porte `nom_affichage=har-chez-moi`, avec 20 équipements `arc`
dans le seul bloc `arriere` (0/0/0/20), sans consommer de création normale.
Tester aussi `>>`, un motif différent, un troisième composant dans le pipeline
et une commande supplémentaire : toutes ces variantes doivent échouer.

Pour recette3, dans l'atelier et après expiration du même cooldown :

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

Comparer les permissions initiales, puis `-rw-rw----`, puis `-rw-------`.
Les trois affichages doivent être visibles. Après publication, vérifier le nom
`pic-nic` et 20 équipements `pique`, répartis 6/7/7/0. Un `ls -l` absent ou
supplémentaire, un autre mode chmod ou un fichier final différent doit échouer.
Le délai de cinq tours et la récompense unique en attente restent communs aux
trois recettes.

Vérifier séparément, sur une partie de démonstration :

- `ls` après `mkdir appel` invalide la tentative et nettoie l'atelier au retour
  de la commande ; `crypte_fin` annonce l'échec, sans consommation du cooldown ;
- fermer la connexion avant la fin ne produit aucune récompense ; la disparition
  de la session est détectée même sans hook de sortie Bash ;
- laisser une tentative ouverte à l'expiration du timer : aucune attribution,
  atelier propre après publication ;
- j2 utilise sa propre Crypte sans modifier le cooldown de j1 ;
- après une réussite au tour N, les tours N+1 à N+4 sont refusés ; N+5 est accepté
  seulement après récupération de la récompense précédente ;
- un retour dans `recompense/` après récupération constatée par l'audit est refusé
  au prochain audit et utilise le repli commun.

Ces essais matériels restent à effectuer sur Raspberry Pi. Les tests automatisés
de `test_crypte_reelle.py` utilisent des comptes temporaires, de vrais Bash avec PTY,
le socket, les permissions, les cgroups et la republication dans `/tmp`.

En cas d'arrêt brutal, la présence de `communication/crypte.sock` est bloquante.
Après le diagnostic administratif du cycle et **vérification de l'absence du moteur** :

```bash
sudo python3 python/survie_admin.py diagnostic
sudo ss -xlpn | grep '/home/game/communication/crypte.sock'
# Seulement si aucun moteur ni collecteur n'est actif :
sudo rm -- /home/game/communication/crypte.sock
```

Le retrait de cette socket ne retire pas le verrou moteur, ne dégèle pas les
joueurs et ne valide pas une résolution interrompue. Suivre les procédures de
récupération ci-dessus. Une republication terminée conserve la même récompense et
le même numéro ; ne pas remettre manuellement `a_creer` pour demander un rejeu.

## Portée de la validation

Les tests Linux réels couvrent les droits, le gel noyau, les FD, les liens, le refus
des processus hors confinement, les interruptions et la republication administrative.
Leur succès sous WSL2/ext4 ne dispense pas des essais SSH et de mesure du gel sur
le Raspberry Pi cible. En particulier, réception visuelle de l'annonce TTY avant gel, configuration
PAM des sessions et temps d'E/S du stockage sont à vérifier sur cette machine.
