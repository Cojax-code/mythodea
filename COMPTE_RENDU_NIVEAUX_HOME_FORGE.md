# Progression automatique, accès depuis Home et ancienneté à la Forge

## Fonctionnalités implémentées

- Un point de combat par résolution territoriale complète, uniquement après un
  affrontement réel de blocs et si le général survit. Deux points donnent un niveau.
  Les duels et cascades ne multiplient pas les points. Une fuite après engagement
  compte ; une fuite sans engagement ou une destruction en fin de territoire ne compte pas.
- Un point de formation par tour complet validé en `reserve/`, nom technique
  conservé pour la caserne militaire. Trois points donnent un niveau. L'arrivée
  d'un autre général en réserve n'annule pas le séjour du premier.
- Les deux jauges restent indépendantes. La formation précède les combats ;
  chaque niveau réutilise les récompenses existantes, dont l'apprentissage garanti.
- Les reçus privés sont enregistrés atomiquement avec les jauges et les récompenses.
  Une répétition du même événement ne donne aucun gain supplémentaire et peut
  réparer la fiche visible après une interruption.
- Un général déjà validé dans Home bénéficie des mêmes accès au village qu'une
  nouvelle création, même après ajout d'unités. Les restrictions du tour zéro,
  le passage obligatoire par le village, l'attente après rappel et les séjours
  complets des bâtiments sont conservés.
- La Forge vérifie l'ancienneté dans la référence officielle précédente. La simple
  présence à l'ouverture du séjour ou la copie d'un UUID ne suffit pas. Les refus
  conservent les dossiers et sont expliqués ; les transformations conservent les
  identités, blessures, batailles et statuts des soldats.

## Fonctions existantes réutilisées

Le calcul des récompenses reste dans `monter_niveau` : nature, trait, hybrides,
tranches de commandement, moral, apprentissage et catégories indisponibles.
La résolution territoriale commune fournit la frontière de comptage. Les scans
de séjour, le registre des soldats, `unites_actions.json`, les captures privées
et les publications officielles apportent les preuves et la persistance.
Les calculs de combat et le raccordement tactique des QG ne sont pas modifiés.

## Fichiers concernés

| Fichier | Rôle du changement |
| --- | --- |
| `python/progression.py` | Jauges, validation atomique et reçus empêchant les doubles gains |
| `python/soldats.py` | Participation des généraux et survie en fin de territoire |
| `python/combats.py` | Signalement des affrontements de blocs effectivement réalisés |
| `python/survie.py` | Transmission de la configuration pour retrouver un général ayant fui |
| `python/formation.py` | Formation en réserve et preuve d'ancienneté des cavaliers |
| `python/securite.py` | Accès depuis un Home officiellement validé avec de nouvelles unités |
| `.dev/tests/test_niveaux_home_forge.py` | 21 nouveaux tests, y compris interruptions et captures/publications |
| `.dev/tests/test_entrainement_rappel_survie.py` | Adaptation des scénarios à la nouvelle règle Home explicitement demandée |
| `MYTHODEA_SPEC.md`, `SURVIE_SPEC.md`, `EVOLUTIONS.md` | Règles, formats persistants et guide d'utilisation cohérents |

## Vérifications

La compilation des huit fichiers Python modifiés a réussi sous Linux WSL.
Les 121 tests ciblés ont réussi sans échec ni test ignoré. Deux tests de permissions
Linux réelles ont également réussi sous root, ainsi que le test de protection du
script administrateur réservé à root. Tous utilisent des dossiers temporaires.

Résultats finaux sous Ubuntu WSL :

| Exécution | Réussis | Échoués / erreurs | Ignorés |
| --- | ---: | ---: | ---: |
| Tests ciblés (121 tests, 114,167 s) | 121 | 0 | 0 |
| Suite complète (465 tests, 399,858 s) | 464 | 0 | 1 |
| Test administrateur réservé à root | 1 | 0 | 0 |
| Tests de permissions Linux réelles | 2 | 0 | 0 |

Le test ignoré dans la suite normale est
`test_crypte_scanner.ScannerCrypte.test_17_script_administrateur_non_modifiable` ;
il a été exécuté avec succès séparément sous root. Les 121 tests ciblés sont
inclus dans la suite complète : ne pas additionner ces deux lignes. En comptant
les deux tests de permissions supplémentaires et le test réservé à root,
**467 tests distincts ont réussi**, sans échec ni test restant non exécuté.

Commandes de test, depuis la racine du dépôt sous Linux :

```bash
PYTHONPATH=.dev/tests python3 -B -m unittest test_niveaux_home_forge test_entrainement_rappel_survie test_complements_moteur test_progression test_soldats_formation -v
python3 -B -m unittest discover -s .dev/tests -v
# Les deux commandes suivantes nécessitent root :
PYTHONPATH=.dev/tests python3 -B -m unittest test_crypte_scanner.ScannerCrypte.test_17_script_administrateur_non_modifiable -v
python3 -B -m unittest discover -s python/tests_linux -p test_progression_isolee.py -v
```

`git diff --check` réussit. Les caches de compilation ont été placés sous
`/tmp/mythodea-pycache`, hors du dépôt.

Les tests de reprise couvrent un point de combat déjà compté, l'expérience du
soldat, une interruption après persistance du niveau avant publication de la
fiche, et une interruption après le niveau avant clôture du séjour. Ils vérifient
l'absence de double gain. Le cycle complet teste aussi capture, résolution et publication.

Deux anomalies découvertes pendant la validation ont été corrigées : recherche
d'un Home inexistant pour un bot détruit, et attente Home encore imposée par un
ancien test. La recherche d'un général ayant fui vérifie sa position officielle
afin qu'une copie Home ne fasse pas passer un général détruit pour un survivant.

## Limites et risques restants

- Validation réalisée sous Ubuntu WSL ; le comportement sur Raspberry Pi OS et
  son système de fichiers reste à vérifier sur la machine cible.
- Une interruption en résolution Survie conserve la procédure de récupération
  existante. La republication ne rejoue pas les combats. Le mode classique n'a
  pas de reprise automatique de tour interrompu : un nouvel appel crée une
  nouvelle identité de bataille, et ne doit pas servir à rejouer un ancien tour.
- Les anciens généraux sans profil officiel ne reçoivent aucun tirage rétroactif.
  Les profils existants commencent leurs jauges manquantes à zéro.
- Après un transfert entre partitions sans correspondance d'identité physique,
  la Forge attend une nouvelle publication officielle. Un séjour ancien sans
  preuve d'éligibilité ne transforme aucune unité.
- Un refus de Forge conserve les unités, mais ne désactive pas l'audit commun
  des créations illégales hors Home/réserve. Les blocs partiellement transformés
  doivent toujours être réorganisés avant combat selon les règles existantes.
- Les reçus de progression sont conservés dans le registre privé ; leur volume
  augmente avec le nombre d'événements validés.

Aucun commit ni push n'a été effectué.
