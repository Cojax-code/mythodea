# Vérifier Mythodea V1.5

Depuis la racine du projet, sous Linux :

```bash
python3 -B -m unittest discover -s tests -v
```

Sous Windows, utiliser `python` à la place de `python3` si cet alias ne fonctionne
pas. Aucun `sudo` n'est nécessaire. La suite contient actuellement 32 tests.
`OK` indique que tous les résultats attendus ont été obtenus ; `FAIL` ou `ERROR`
indique le scénario et la ligne à examiner.

## Ce qui est testé

Les scénarios créent de vrais dossiers et fichiers, mais dans un répertoire
temporaire. Ils vérifient les effectifs, les déplacements et suppressions,
les positions sauvegardées et les rapports. Ils n'utilisent pas `/home/game`
sur la machine et ne changent pas les permissions des comptes Linux.

Les dix scénarios ajoutés pour les points 1 et 3 couvrent :

- la sélection par emplacement, même si les noms des généraux sont dans un autre
  ordre, avec exclusion des généraux sans unité et relais après destruction ;
- le passage du frontal au combat rangé lorsque les deux camps ont des survivants ;
- l'absence de combat rangé quand le frontal a déjà éliminé un camp ;
- 24 cas de déplacement, répartis entre j1 et j2 : immobilité, voisin,
  marche forcée, sorties du home et du repli, destinations interdites ;
- un déplacement trop long, sa sanction au repli puis le retour à la base ;
- une marche forcée bloquée par un territoire intermédiaire ennemi ;
- trois tours avec occupation de base, marche forcée puis récupération de fatigue ;
- l'effet réel de la fatigue sur un combat et les rapports correspondants ;
- deux généraux dans le même emplacement, tous deux envoyés au repli ;
- un vrai dépassement de 25 unités ramené à 20, en supprimant d'abord l'arrière,
  puis la gauche, et sans nouvelles pertes au tour suivant.

`tour_sans_generation()` enchaîne la préparation des rapports, l'audit et la
résolution. Il vérifie aussi que les positions enregistrées correspondent aux
dossiers et qu'aucun territoire ne reste contesté. Il ne simule pas l'installation,
la réparation des permissions, l'apparition automatique de renforts ni la victoire.
Ces éléments nécessitent d'autres vérifications, notamment sur Linux.

## Lire manuellement le rapport d'un scénario isolé

Depuis la racine du projet, ouvrir `python3 -B` (ou `python -B` sous Windows),
puis saisir :

```python
import sys
sys.path.insert(0, "tests")
from test_regressions import Regressions

test = Regressions("test_transition_frontal_vers_range_avec_survivants_des_deux_camps")
test.setUp()
test.test_transition_frontal_vers_range_avec_survivants_des_deux_camps()
print((test.m["rapports_territoires_dir"] / "terrain1.txt").read_text(encoding="utf-8"))
print(test.m["rapport_long_path"].read_text(encoding="utf-8"))
```

Résultat attendu :

1. Au frontal, `j1 general1` (5 archers) affronte `j2 general1` (2 piquiers).
   Il reste 4 archers à j1.
2. Au frontal, `j1 general2` (2 piquiers) affronte `j2 general2` (5 archers).
   Il reste 4 archers à j2.
3. En combat rangé, les deux généraux survivants s'affrontent avec 4 archers chacun.
   Ils sont tous deux détruits ; le territoire devient neutre.

Pour voir le chemin des rapports temporaires, saisir `print(test.m["rapport_dir"])`.
Après consultation, nettoyer uniquement le scénario temporaire avec :

```python
test.doCleanups()
```

## Comment les tests chargent le moteur

Le moteur possède maintenant une fonction `main()`, appelée uniquement lorsque
le fichier est lancé directement. Les tests importent donc le fichier complet
avec `importlib`, sans découper son code avec l'AST et sans lancer de tour.
Un module neuf est créé pour chaque test afin d'isoler les variables globales.
`test.m` donne accès au dictionnaire de ce module.

Pendant cet import, `pwd` et `grp` sont remplacés par des modules vides pour
permettre les tests sous Windows. Ces remplacements sont retirés dès la fin de
l'import. Un appel imprévu à leurs fonctions échoue plutôt que de simuler un droit.

`setUp()` prépare un plateau neuf pour chaque test : c'est la **fixture**, ou
préparation commune. Les chemins des homes sont redirigés vers ce plateau.
Certaines fonctions de permissions et d'identification du propriétaire sont
remplacées temporairement : c'est une **simulation**, pas une validation des UID
et droits réels. Les calculs de bataille et les opérations sur les unités restent
ceux du moteur.

Enfin, une graine aléatoire fixe rend les scénarios reproductibles. Elle s'applique
uniquement aux tests et ne rend pas la partie réelle déterministe.
