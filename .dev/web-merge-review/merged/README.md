# Mythodea-web

<<<<<<< C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\ours
Le simulateur de bataille exécute le moteur Python officiel **v2.0**, verrouillé par empreintes SHA-256 :
deux camps, quatre généraux maximum par camp, profils et étiquettes, QG/Messagers, étendards,
=======
Le simulateur de bataille exécute le moteur Python officiel **v2.0 / 3391613** :
deux camps, quatre généraux maximum par camp, profils et étiquettes, QG/Messagers,
>>>>>>> C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\web
douze unités, blessures et journal des phases. Aucun calcul de combat n'est
réimplémenté dans son JavaScript. Le comparateur théorique reste un outil séparé.

Les profils et les compositions sont modifiables et peuvent être générés à nouveau.
<<<<<<< C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\ours
OFF/OFF et OFF/DEF utilisent actuellement les mêmes règles. Les cascades,
retraites et la fatigue de déplacement ne sont pas simulées. Les règles sont synchronisées avec le moteur commun du dépôt.
=======
Au niveau 0, aucun PC, moral, étiquette ou évolution n'est attribué à la création.
La progression actuelle et les impasses OFF/OFF et OFF/DEF sont intégrées.
Les retraites physiques, cascades et fatigue de déplacement ne sont pas simulées :
une retraite requise reste explicitement non résolue, avec les survivants présents.
>>>>>>> C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\web

## Lancement sous WSL / Linux

Prérequis : utilisateur **non root**, Python 3.11+, Git, Bubblewrap avec `--size`
et espaces de noms utilisateur autorisés. Lancement vérifié sous WSL Ubuntu,
Python 3.14.4 et Bubblewrap 0.11.1.

Depuis la racine de **Mythodea-web**, dans un terminal **WSL / Linux** :

```bash
bash scripts/run_simulator.sh
```

Ouvrir **http://127.0.0.1:8080/simulateur.html** dans le navigateur Windows ou Linux ;
arrêter avec `Ctrl+C`. Le lanceur utilise `.venv`, ou les dépendances déjà préparées
dans `.runtime/deps`. Il ne sélectionne pas `.venv-linux`.
Le moteur est recherché par défaut dans `.runtime/engine-3391613`.
Si une ancienne variable `MYTHODEA_ENGINE_PATH` est définie, exécuter
`unset MYTHODEA_ENGINE_PATH` pour revenir à ce chemin.

Pour préparer le moteur lors d'une **première installation ou après une mise à jour du verrou** :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
<<<<<<< C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\ours
python3 -B scripts/prepare_engine.py --source ../..
bash scripts/run_simulator.sh
```

Ouvrir **http://127.0.0.1:8080/simulateur.html** ; arrêter avec `Ctrl+C`.
Le verrou courant décrit les sources locales : `--source` est requis. La préparation
vérifie chaque empreinte et refuse une destination existante. Le serveur retrouve
le dossier préparé à partir de l'identifiant `snapshot`. Après une modification du
moteur, exécuter `python3 -B scripts/sync_engine.py --source ../..`, puis préparer
le nouvel instantané et relancer les tests de parité avant publication.
=======
python3 -B scripts/prepare_engine.py --source ../Mythodea_code
```

Les sources sont extraites du commit publié `3391613`, y compris les exclusions
de moral et de soins zombies. Sans `--source`, le script récupère ce commit sur GitHub.
Les **27 modules** sont vérifiés par SHA-256 avant extraction et avant chaque calcul.
Après une mise à jour du verrou, préparer le nouveau dossier moteur avant de relancer
le serveur. Si les dépendances Python sont déjà installées, seule la commande
`python3 -B scripts/prepare_engine.py --source ../Mythodea_code` est nécessaire.
La branche `v2.0` de `Mythodea_code` doit être à jour pour que le commit verrouillé
soit disponible localement (`git fetch origin v2.0`).
Une destination existante est refusée : réutiliser le dossier déjà préparé sans
relancer l'extraction. Un autre emplacement se choisit avec `MYTHODEA_ENGINE_PATH`.
>>>>>>> C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\web
Une page HTML seule ou un hébergement statique ne suffit pas à lancer le backend.

## Vérification

Après une modification qui le justifie, avec l'environnement `.venv` préparé :

```bash
.venv/bin/python -B -m unittest discover -s tests -v
```

Le [dossier du simulateur](docs/simulateur.md) décrit aussi l'API, l'isolation et les
tests navigateur ; le [guide d'hébergement](docs/hebergement-permanent.md) couvre
les prérequis d'une publication permanente.
