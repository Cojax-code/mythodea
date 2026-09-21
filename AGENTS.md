# AGENTS.md

Ce fichier définit les règles de travail pour les agents qui modifient Mythodea.

## Avant toute modification

1. Lire `MYTHODEA_SPEC.md`.
2. Inspecter les fichiers réellement concernés avant de proposer une modification.
3. Vérifier les tests existants liés à la zone modifiée.
4. Ne jamais supposer une règle de gameplay qui n'est pas documentée ou explicitement demandée.

## Règle principale

Ne pas modifier le gameplay sans accord explicite.

Un refactoring doit conserver exactement le comportement existant.

Ne pas modifier silencieusement :

- les règles de combat ;
- les priorités de MANŒUVRE ;
- les déplacements ;
- la marche forcée et la fatigue ;
- les ordres ;
- les sanctions anti-triche ;
- les permissions Linux ;
- les chemins sous `/home/game`, `/home/j1`, `/home/j2` ;
- les formats des fichiers d'état ;
- les rapports ;
- les conditions de victoire.

Si une incohérence ou un bug potentiel est découvert, le signaler avant de le corriger.

## Architecture

Le code Python se trouve dans `python/`.

Les scripts Bash se trouvent dans `bash/`.

Le point d'entrée est :

```text
python/mythodea_v_1_5.py
```

Il doit rester léger et appeler les modules spécialisés.

Éviter les dépendances circulaires entre modules.

Ne pas multiplier les petits modules sans raison claire.

Le mode classique, le futur mode Survie et le futur multijoueur doivent réutiliser
au maximum le même moteur : généraux, mouvements, combats, ordres, sécurité et rapports.

## Tests

Conserver tous les tests de régression existants.

Commande principale :

```bash
python3 -B -m unittest discover -s python/tests -v
```

Après une modification Python :

1. lancer `python3 -m py_compile` sur les fichiers concernés ;
2. lancer les tests pertinents ;
3. lancer la suite complète lorsque la modification touche le moteur ;
4. ne jamais modifier un résultat attendu uniquement pour faire passer un test.

Les tests temporaires doivent utiliser un environnement isolé et ne jamais altérer
une vraie partie sous `/home/game`.

Les caches Python (`__pycache__`, `*.pyc`) ne doivent jamais être commités.

## Linux

Mythodea cible Linux / Raspberry Pi OS.

Les UID/GID, propriétaires, `chmod`, `chown` et permissions font partie du jeu.

Les tests sous Windows ou dans un environnement simulé ne remplacent pas une validation
réelle sous Linux lorsqu'une modification touche ces aspects.

## Documentation

`README.md` est destiné aux humains et doit rester court et accessible.

`MYTHODEA_SPEC.md` est la référence technique et gameplay actuelle.

Ne pas utiliser la SPEC comme journal de modifications.

Mettre à jour la SPEC uniquement lorsqu'une modification validée change :

- une règle ;
- un format persistant ;
- l'architecture ;
- la responsabilité d'un module ;
- une étape importante du cycle du jeu.

Mettre à jour le README seulement si l'installation, le lancement ou la présentation
générale du projet change.

## Communication

Après une tâche importante, expliquer en français :

1. ce qui a été modifié ;
2. quels fichiers ont été touchés ;
3. pourquoi ;
4. comment la modification a été testée ;
5. les éventuels risques ou points restant à vérifier.

Le propriétaire du projet apprend Python et Linux pendant le développement :
privilégier une explication compréhensible plutôt qu'un compte rendu opaque.

## Changements complexes

Avant d'introduire une technique avancée ou inhabituelle (AST, métaprogrammation,
monkey patching complexe, architecture supplémentaire, abstraction importante),
expliquer pourquoi elle est nécessaire.

Préférer la solution la plus simple qui conserve correctement les règles et les tests.
