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

La prochaine étape majeure est la V2.0 : construire le mode Survie en réutilisant le
même moteur que le mode multijoueur. La validation réelle sous Linux / Raspberry Pi
continuera au fur et à mesure de ce développement.

## Lancer le jeu

Mythodea est prévu pour Linux / Raspberry Pi OS.

Depuis la racine du dépôt :

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

## Organisation

```text
bash/                 scripts d'installation, lancement et nettoyage
python/               moteur du jeu
python/tests/         tests automatiques
MYTHODEA_SPEC.md      règles et architecture de référence
TESTS.md              détails sur les tests
```

Le point d'entrée Python est volontairement léger ; les règles sont réparties entre
les modules de généraux, mouvements, sécurité, combats, rapports, état et plateau.

## Tests

```bash
python3 -B -m unittest discover -s python/tests -v
```

Les tests utilisent un plateau temporaire. Ils ne remplacent pas la validation des
vrais comptes, UID/GID et permissions sur Linux.

## Documentation

- `MYTHODEA_SPEC.md` : référence des règles actuelles et de l'architecture.
- `TESTS.md` : scénarios de test et commandes utiles.

Mythodea est encore en développement : la V1.5 stabilise le moteur commun, et la
V2.0 ouvre le développement du mode Survie. Les ordres supplémentaires seront
introduits progressivement lorsqu'ils apporteront une vraie valeur au gameplay.
