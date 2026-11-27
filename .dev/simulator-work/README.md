# Mythodea-web

Le simulateur de bataille exécute le moteur Python officiel **v2.0**, verrouillé par empreintes SHA-256 :
deux camps, quatre généraux maximum par camp, profils et étiquettes, QG/Messagers, étendards,
douze unités, blessures et journal des phases. Aucun calcul de combat n'est
réimplémenté dans son JavaScript. Le comparateur théorique reste un outil séparé.

Les profils et les compositions sont modifiables et peuvent être générés à nouveau.
OFF/OFF et OFF/DEF utilisent actuellement les mêmes règles. Les cascades,
retraites et la fatigue de déplacement ne sont pas simulées. Les règles sont synchronisées avec le moteur commun du dépôt.

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
Le moteur est recherché dans `.runtime/engine-<snapshot abrégé>` selon `backend/engine.lock.json`.
Si une ancienne variable `MYTHODEA_ENGINE_PATH` est définie, exécuter
`unset MYTHODEA_ENGINE_PATH` pour revenir à ce chemin.

Pour préparer le moteur lors d'une **première installation ou après une mise à jour du verrou** :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
python3 -B scripts/prepare_engine.py --source ../..
bash scripts/run_simulator.sh
```

Ouvrir **http://127.0.0.1:8080/simulateur.html** ; arrêter avec `Ctrl+C`.
Le verrou courant décrit les sources locales : `--source` est requis. La préparation
vérifie chaque empreinte et refuse une destination existante. Le serveur retrouve
le dossier préparé à partir de l'identifiant `snapshot`. Après une modification du
moteur, exécuter `python3 -B scripts/sync_engine.py --source ../..`, puis préparer
le nouvel instantané et relancer les tests de parité avant publication.
Une page HTML seule ou un hébergement statique ne suffit pas à lancer le backend.

Les informations des généraux synthétiques sont créées sous `info/`, comme dans
le moteur. Les nouveaux noms de `fiche.txt` ne changent ni le contrat JSON du
simulateur ni les clés privées de progression. Le verrou courant reste un
instantané local non publié.

## Vérification

Après une modification qui le justifie, avec l'environnement `.venv` préparé :

```bash
.venv/bin/python -B -m unittest discover -s tests -v
```

Le [dossier du simulateur](docs/simulateur.md) décrit aussi l'API, l'isolation et les
tests navigateur ; le [guide d'hébergement](docs/hebergement-permanent.md) couvre
les prérequis d'une publication permanente.
