# Mythodea-web

Le simulateur de bataille exécute le moteur Python officiel **v2.0 / b31b842** :
deux camps, quatre généraux maximum par camp, profils et étiquettes, QG/Messagers,
douze unités, blessures et journal des phases. Aucun calcul de combat n'est
réimplémenté dans son JavaScript. Le comparateur théorique reste un outil séparé.

Les profils et les compositions sont modifiables et peuvent être générés à nouveau.
OFF/OFF et OFF/DEF utilisent actuellement les mêmes règles. Les cascades,
retraites et la fatigue de déplacement ne sont pas simulées. Les décisions de
gameplay postérieures à `b31b842` attendent leur intégration dans le moteur.

## Lancement sous WSL / Linux

Prérequis : utilisateur **non root**, Python 3.11+, Git, Bubblewrap avec `--size`
et espaces de noms utilisateur autorisés. Validation réalisée sous WSL Ubuntu,
Python 3.14.4 et Bubblewrap 0.11.1. Depuis ce dépôt dans un terminal WSL :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
python3 -B scripts/prepare_engine.py --source ../Mythodea_code --destination .runtime/engine-b31b842
export MYTHODEA_ENGINE_PATH="$PWD/.runtime/engine-b31b842"
bash scripts/run_simulator.sh
```

Ouvrir **http://127.0.0.1:8080/simulateur.html** ; arrêter avec `Ctrl+C`.
Sans dépôt moteur local, omettre `--source` pour le récupérer depuis GitHub.
La préparation extrait les **27 modules** du commit exact et vérifie leurs SHA-256.
Une destination existante est refusée : réutiliser le dossier préparé en passant
directement au `export`. L'ancien moteur peut rester archivé dans `.runtime/engine`.
Une page HTML seule ou un hébergement statique ne suffit pas à lancer le backend.

## Vérification

```bash
export MYTHODEA_ENGINE_PATH="$PWD/.runtime/engine-b31b842"
.venv/bin/python -B -m unittest discover -s tests -v
```

Les tests Linux exécutent réellement Bubblewrap, sans solution de repli non isolée.
Le [dossier du simulateur](docs/simulateur.md) décrit le contrat API, les tests
navigateur, les limites, l'audit et les vérifications avant publication.
