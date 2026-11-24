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
et espaces de noms utilisateur autorisés. Validation réalisée sous WSL Ubuntu,
Python 3.14.4 et Bubblewrap 0.11.1. Depuis ce dépôt dans un terminal WSL :

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

## Vérification

```bash
.venv/bin/python -B -m unittest discover -s tests -v
```

Les tests Linux exécutent réellement Bubblewrap, sans solution de repli non isolée.
Le [dossier du simulateur](docs/simulateur.md) décrit le contrat API, les tests
navigateur, les limites, l'audit et les vérifications avant publication.
