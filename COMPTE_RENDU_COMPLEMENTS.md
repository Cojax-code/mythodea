# Compléments du moteur — compte rendu du 19 octobre 2026

Les modifications sont locales, sans commit ni push. Aucun test n'a utilisé une
partie réelle : plateaux temporaires, processus de test et copies isolées uniquement.

## Fonctionnalités opérationnelles

- Depuis `home`, passage obligatoire par le village à tous les tours. Les nouveaux
  généraux peuvent rejoindre ses emplacements et bâtiments autorisés sans coût
  territorial. Aucun accès direct à `est_1`, même par marche forcée. Les restrictions
  du tour 0 et les délais d'entraînement/rappel sont conservés.
- Les généraux récompensés peuvent effectuer un déplacement normal dès publication.
  Le mécanisme existant satisfaisait cette règle : des tests le couvrent sans
  ajouter d'exemption permanente à l'audit commun.
- Une retraite admissible vers le village utilise la garnison disponible, puis
  `reserve` si aucune place ne convient. Identité, profil, ordres, fatigue et états
  des soldats sont conservés. Les conditions de fuite ne changent pas.
- Création des quatre natures selon 45/45/5/5, orientation principale permanente,
  traits et poids de récompenses conservés. Les hybrides peuvent apprendre des
  évolutions croisées ; leurs récompenses ordinaires suivent leur orientation.
  Le moral du stratège hybride intervient dans le sauvetage réel des soldats.
- Hôpital : soins simultanés après un tour complet, sans effacer l'expérience ou
  les statuts. Supprimer le fichier visible des blessures ne guérit pas le soldat.
- École : six places physiques communes avec compartiments privés, manuel de
  trois emplacements, demandes `a/A` et `e/E`, contrôles des IDs et du séjour.
  Toutes les lectures précèdent les écritures ; les mémoires personnelles gardent
  l'ID réellement appris. Les apprentissages croisés utilisent le même catalogue.
- Forge : une place commune, un tour complet, orientation instinctive et technologie
  104 obligatoires. Les cavaliers existants avec la recette complète deviennent
  `cavalerie_LN`, sans collision ni perte d'identité, blessures ou statuts. Les
  recettes refusées conservent les unités. Les transformations sont rapportées et
  reconnues par les scans suivants ; les copies ne sont pas autorisées.
- Les règles de combat de la cavalerie lourde restent celles déjà présentes.

## Fonctionnalités préparées et décisions ouvertes

Les fonctions de sélection de QG et de commandement acceptent les hybrides.
L'instinctif hybride n'obtient un ordre global dans ces fonctions qu'après acquisition
effective de son ID. Le raccordement tactique des QG reste inactif : matérialisation
sur le plateau, commandement pertinent selon le contexte et transition des ordres
historiques doivent encore être définis. La résolution historique n'est pas remplacée.

Les évolutions disponibles sont 201 (commandement), 202 (moral), 104 (technologie
de Forge) et 1002 (attaque frontale existante), selon leur compatibilité. Aucun
barème ne déclenche automatiquement une montée de niveau ; l'API moteur permet
une attribution explicite. Les autres déblocages restent réservés.

Les écritures concurrentes du même emplacement sont toujours refusées ensemble ;
leur départage et le remplacement d'un apprentissage personnel en attente restent
à définir. Les généraux historiques sans profil ne reçoivent pas de tirage rétroactif.
Le nom technique `reserve` est conservé.

## Permissions et sauvegardes

L'École utilise `village/ecole_officiers/1..6/<joueur>/`, la Forge
`village/forge/1/<joueur>/`. Les parents communs appartiennent à
`root:<groupe_allie>` en 750 ; les compartiments restent privés à leur joueur en
700, leurs fichiers en 600. Le manuel reste administrateur en 640. Aucun `chattr`.

Capture, publication et permissions de consultation/actions incluent les nouveaux
compartiments. Les anciens emplacements d'École sont migrés sous gel par renommage,
sans écrasement. Les états privés existants restent l'autorité ; le registre des
soldats enregistre la transformation de Forge sans remplacer leur UUID.

## Validation

- Compilation `py_compile` des onze modules modifiés et du test Linux : réussie.
- `python3 -B -m unittest discover -s .dev/tests -v` sous Ubuntu WSL :
  **444 tests, aucun échec, un test réservé à root ignoré**, en 138,265 secondes.
- Ce test réservé à root, `ScannerCrypte.test_17_script_administrateur_non_modifiable`,
  a ensuite réussi séparément dans son environnement temporaire.
- Les deux tests de `python/tests_linux/test_progression_isolee.py` ont réussi
  sous root avec de vrais UID de processus : protection des états et du manuel,
  capacité physique et confidentialité entre compartiments joueurs.
- 21 nouveaux scénarios couvrent les compléments du moteur. Les tests existants
  du village, des combats, des soins, des mémoires et des générations sont conservés.
- Deux échecs historiques ont été reproduits sur une copie intacte de HEAD :
  les attentes des tests ne tenaient pas compte de l'espacement des journaux et de
  l'annonce finale de consultation déjà intégrés. Leurs vérifications ont été
  adaptées à ces comportements, sans changer les journaux ni les notifications.
- `git diff --check` : aucun défaut d'espacement.

## Points de vigilance

- La validation des permissions a été faite sous Linux WSL ; l'exécution complète
  sur Raspberry Pi, notamment les sessions SSH et le gel réel, reste à vérifier.
- Une migration d'École avec destination déjà existante s'arrête pour récupération.
  Un séjour qui traverse une migration doit recommencer un tour complet.
- Après une conversion partielle à la Forge, les blocs doivent être réorganisés
  avant engagement : la règle historique de suppression des types minoritaires
  dans un bloc de combat reste applicable. La Forge elle-même ne les supprime pas.
- Les sauvegardes doivent conserver ensemble unités et états privés. Les fichiers
  visibles de blessures, de profils ou de mémoires ne remplacent pas cette autorité.

## Fichiers modifiés ou créés

| Fichiers | Rôle du changement |
| --- | --- |
| `python/catalogues.py` | Évolutions disponibles 104 et 1002, IDs existants conservés |
| `python/progression.py` | Quatre natures, orientation, apprentissages croisés et tirages ordinaires |
| `python/commandement.py` | Éligibilité des hybrides au QG et contrôle des ordres appris |
| `python/combats.py` | Sauvetage par le moral des hybrides |
| `python/generaux.py` | Description commune des places d'École et de Forge |
| `python/mouvements.py` | Accueil des fuyards en réserve et exclusion des bâtiments du placement tactique |
| `python/formation.py` | Emplacements, migration, séjour de Forge et transformation conservant le soldat |
| `python/securite.py` | Reconnaissance des cavaleries lourdes forgées officiellement |
| `python/plateau.py` | Préparation des bâtiments et de leurs permissions |
| `python/cycle_linux.py` | Migration sous gel, publication des bâtiments et permissions des phases |
| `python/rapports.py` | Reconnaissance de la Forge dans l'exploration |
| `.dev/tests/test_complements_moteur.py` (nouveau) | 21 scénarios des nouvelles règles et de leurs protections |
| `.dev/tests/test_progression.py` | Probabilités des quatre natures et exclusion des récompenses déjà acquises |
| `.dev/tests/test_soldats_formation.py` | Chemin physique commun de l'École |
| `.dev/tests/test_surnombre.py` | Accueil en réserve et conservation des données |
| `.dev/tests/test_village.py` | Groupe commun ajouté au simulateur de permissions |
| `.dev/tests/test_accueil_survie.py` | Retraite en réserve et introduction malgré l'espacement existant |
| `.dev/tests/test_notifications_survie.py` | Vérification de l'annonce de consultation déjà existante |
| `python/tests_linux/test_progression_isolee.py` | Confidentialité réelle des compartiments partagés |
| `MYTHODEA_SPEC.md` | Règles, formats persistants, architecture et limites |
| `SURVIE_SPEC.md` | Intégration Survie des bâtiments, retraites et déplacements |
| `EVOLUTIONS.md` | Guide pratique des nouveaux chemins et de la Forge |
| `COMPTE_RENDU_COMPLEMENTS.md` (nouveau) | Présent bilan de réalisation et de validation |
