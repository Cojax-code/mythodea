# Valeurs de combat individuelles

## Résultat

Le catalogue définit désormais `valeur_combat`, entier strictement positif,
indépendant de la référence de fabrication. Archer, piquier, cavalier et
cavalerie lourde ont une valeur de base de 5. Aucune nouvelle unité n'est créée.
Les valeurs 3 et 7 sont simulées uniquement dans les tests.

La cavalerie lourde conserve son doublement dans Avant à partir de 15 unités
présentes : sa valeur contextuelle passe de 5 à 10, puis à 20 contre un archer
ou cavalier grâce à l'avantage naturel existant. Le seuil est réévalué après
chaque affrontement avec les survivants réels.

## Formules utilisées

La puissance de base d'un bloc homogène est `effectif × valeur_combat`.
Pour chaque camp, la valeur effective `v` applique exactement une fois les
facteurs déjà présents : formation lourde, avantage naturel, et avantage du
bloc frais face à un bloc fatigué du même type.

```text
puissance_A = effectif_A * vA
puissance_B = effectif_B * vB
pertes_A = min(effectif_A, puissance_B // vA)
pertes_B = min(effectif_B, puissance_A // vB)
survivants_A = effectif_A - pertes_A
survivants_B = effectif_B - pertes_B
```

Les deux pertes sont calculées simultanément, avant suppression des unités,
avec arrondi entier vers le bas. Un bloc vide ne produit aucune perte et ne
déclenche aucune division. Le moral et les blessures sont traités ensuite par
les fonctions existantes.

Point de compatibilité : dans le moteur historique, la valeur effective sert
aussi de résistance au dénominateur. Cette règle est conservée. Employer seulement
la valeur brute au dénominateur modifierait les pertes lorsque des avantages
s'appliquent. Le facteur uniforme 5 se simplifie donc dans les rapports de
puissances et résistances : les survivants historiques restent identiques.

## Fichiers modifiés

| Fichier | Modification |
| --- | --- |
| `python/catalogues.py` | Valeur individuelle centrale, accès et validation stricte |
| `python/combats.py` | Utilisation de la valeur, gestion des blocs vides et plafonnement explicite des pertes |
| `python/defis.py` | Texte du bestiaire décrivant le doublement sans ancienne échelle chiffrée |
| `.dev/exemples/bestiaire_cavalerie_lourde.txt` | Exemple conforme au bestiaire publié |
| `.dev/tests/test_defis_survie.py` | Attentes numériques des valeurs multipliées par cinq ; survivants attendus conservés |
| `.dev/tests/test_valeurs_combat.py` | Dix nouveaux tests de valeurs, compatibilité historique et pertes sur disque |
| `MYTHODEA_SPEC.md` | Propriété, calculs, interactions et procédure d'ajout futur d'une valeur |
| `SURVIE_SPEC.md` | Référence au calcul commun utilisé par joueurs et bots |
| `EVOLUTIONS.md` | Présentation de l'échelle de combat, distincte de la fabrication |
| `COMPTE_RENDU_VALEURS_COMBAT.md` | Livraison et résultats de vérification |

## Vérifications

Compilation réussie des cinq fichiers Python modifiés sous Ubuntu WSL, avec
les caches dans `/tmp/mythodea-pycache`, hors du dépôt.

Les 188 tests ciblés ont réussi, sans échec ni test ignoré. Ils couvrent les
valeurs de combat, le moteur historique, les défis et la cavalerie lourde,
les soldats et la formation, la progression, Home et la Forge.

| Exécution | Réussis | Échoués / erreurs | Ignorés |
| --- | ---: | ---: | ---: |
| Tests ciblés (188 tests, 121,242 s) | 188 | 0 | 0 |
| Suite complète (475 tests, 145,797 s) | 474 | 0 | 1 |
| Test réservé à root, exécuté séparément | 1 | 0 | 0 |

Le test ignoré par l'exécution ordinaire est
`test_crypte_scanner.ScannerCrypte.test_17_script_administrateur_non_modifiable`.
Il a réussi sous root dans son environnement temporaire : **475 tests distincts
validés au total**, sans échec ni test restant non exécuté. Les tests ciblés sont
inclus dans la suite complète et ne s'ajoutent pas à ce total.
`git diff --check` réussit également. Les résultats attendus des combats
historiques n'ont pas été modifiés : seules les assertions des valeurs numériques
de base de la cavalerie lourde ont été adaptées à la nouvelle échelle demandée.

Un test compare **774 400 confrontations** à un oracle figé de l'ancienne échelle :
quatre types, quatre combinaisons de fatigue, quatre positions plus absence de
position, et effectifs de 0 à 20 ainsi que 25. Les dix nouveaux tests vérifient
aussi les valeurs 3/5 et 5/7 sans avantage, les avantages naturels, le passage
sous le seuil lourd, les blocs vides, les pertes simultanées, la conservation des
identités et les blessures puis destructions dans des dossiers temporaires.

Commandes principales, depuis la racine du dépôt sous Linux :

```bash
PYTHONPATH=.dev/tests python3 -B -m unittest test_valeurs_combat test_mythodea test_defis_survie test_soldats_formation test_niveaux_home_forge test_complements_moteur test_progression test_entrainement_rappel_survie -v
python3 -B -m unittest discover -s .dev/tests -v
```

## Compatibilité et limites

Aucun nouveau format persistant ni aucune migration des soldats n'est introduit.
Les identifiants, blessures, expérience, niveaux, accès Home, validation de Forge
et procédures de récupération continuent d'utiliser le moteur existant.
La validation interdit les valeurs nulles, négatives, booléennes, flottantes et
textuelles. Toute future unité nécessite encore une définition explicite de sa
représentation et de ses autorisations ; sa valeur seule ne crée aucun avantage.

La validation est effectuée sous Ubuntu WSL, pas sur un Raspberry Pi physique.
La reprise automatique d'un tour classique interrompu reste hors du périmètre ;
les protections de récupération Survie existantes sont conservées.

Travail sur la branche courante `v2.0`. Aucune branche créée, aucun commit ni push.
Le site Mythodea-web et son comparateur n'ont pas été modifiés.
