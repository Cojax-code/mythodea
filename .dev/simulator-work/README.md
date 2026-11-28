# Copie de travail du simulateur

Le simulateur maintenu et sa documentation canonique sont dans
[Mythodea-web](https://github.com/Cojax-code/Mythodea-web).
Cette copie permet les essais d’intégration avec le moteur voisin. Elle utilise
le même backend, les mêmes tests, JavaScript et verrou de sources. Les anciennes
pages annexes de cette copie ne doivent pas remplacer celles du site maintenu.

## Préparer et tester sous Linux / WSL

Depuis ce dossier, sous un utilisateur non root, avec Python 3.11+, Git,
Bubblewrap avec `--size` et les espaces de noms utilisateur autorisés :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
python3 -B scripts/prepare_engine.py --source ../.. --working-tree
bash scripts/run_simulator.sh
```

Ouvrir `http://127.0.0.1:8080/simulateur.html` ; arrêter avec Ctrl+C.
Le runtime `.runtime/engine-<revision>` est extrait des sources locales identifiées dans `backend/engine.lock.json`,
base Git `645fada`, puis vérifié intégralement par SHA-256.
Ce verrou temporaire exige `--working-tree` ; il ne représente pas un commit publié. Une destination existante
est refusée ; la copie déjà préparée peut être réutilisée.

```bash
.venv/bin/python -B -m unittest discover -s tests -v
```

Sur un checkout Windows monté dans WSL, `python3 -B scripts/validate_linux.py`
teste une copie Linux temporaire. `--serve` la sert pour les cinq parcours de
`scripts/test_browsers.py` (Playwright et Chrome requis). Les résultats restent
dans `test-results/`, hors Git. Ne jamais désactiver Bubblewrap pour les tests.

## Synchronisation

Après validation explicite d’un nouveau commit moteur :

```bash
python3 -B scripts/sync_engine.py --source ../.. --commit COMMIT_VALIDE
python3 -B scripts/prepare_engine.py --source ../..
```

Le [guide technique web](https://github.com/Cojax-code/Mythodea-web/blob/main/docs/simulateur.md)
décrit API, limites, isolation et parité. Le
[guide d’hébergement](https://github.com/Cojax-code/Mythodea-web/blob/main/docs/hebergement-permanent.md)
conserve les exigences d’un service permanent ; aucune publication n’est automatique.
Comparer les deux verrous et les fichiers partagés avant intégration. Les métadonnées
des généraux synthétiques restent dans `info/` ; les clés privées de progression
et le contrat API ne sont pas renommés avec les champs publics de fiche.
