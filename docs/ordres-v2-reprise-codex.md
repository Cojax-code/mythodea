# Reprise du chantier des ordres V2 — état réel

## Source et branche unique

- **Travailler exclusivement sur `feat/ordres-v2`.**
- Base : `v2.0`, commit `eb5c302` (push d'audit Codex). Aucun changement des 21 ordres ne doit être commité sur `v2.0` avant validation.
- La SPEC des ordres validés et questions ouvertes est `docs/ordres-v2-preparation.md`.
- Le fichier `python/ordres_conception.py` est un **registre documentaire non exécutable**. Il ne doit pas être assimilé au catalogue actif `python/catalogues.py`.
- Le fichier `.dev/tests/test_ordres_conception_v2.py` protège la séparation (21 entrées désactivées, catégories/contre-ordres, absence d'activation).
- `python/commandement.py` contient déjà l'API préparatoire de comparaison des ordres par donneur. `python/generaux.py:lire_ordres_general` ne lit pour le moment que 2 ou 3 nombres et s'appuie sur la légende historique. **Ne pas introduire des formats G/D ou 4 segments à la hâte** : établir le contrat lexical, sécuriser la validation, puis tester.
- **Aucun des 21 nouveaux effets n'est opérationnel pour le moment.** Les nouvelles entrées ne changent pas le comportement d'une partie.

## Audit ciblé de la reprise (sans supposer que tout est raccordé)

1. Examiner les appels depuis le cycle territorial vers `commandement`, `generaux`, `combats` et les effets de l'ordre historique `1-2`.
2. Déterminer où se trouve l'autorité sur la sélection des donneurs ; confronter les ordres sur **les mêmes unités d'engagement et catégories**, jamais par liste agrégée de généraux.
3. Garder séparées : parsing, légalité, conflit d'ordres, ordre des phases, application de l'effet, rapport privé/public.
4. Raccorder l'API sans faire de l'absence d'ordre adverse une autorisation implicite de tous les contre-ordres hors contexte de confrontation.
5. Introduire les 21 effets par lots, avec état des inconnues et tests déterministes pour chaque lot ; **ne pas inventer** d'arrondis, de destinations, de plafonds, de morts ni d'effets annexes non validés.
6. En priorité : les ordres à effet simple dont le contrat est complet ; ensuite ceux qui déplacent les phases et généraux ; puis les fusions, renforts, Zombies et réanimations qui affectent les objets soldats.
7. Aucune nouvelle activation sans tests du déclenchement, des deux camps, de l'échec, du cumul et de la reprise. Vérifier la non-régression de `1-2`.
8. Codex exécutera à la fin les tests Linux complets et les scénarios sur Raspberry Pi / SSH si possible. Ne pas qualifier les tests de réussis sans exécution.

## Décisions toujours manquantes

- **Muraille humaine :** « bloc Avant perdu » à la défaite signifie-t-il mort, fuite ou autre ? Comment répartir les pertes de la ligne collective ?
- **Réserve stratégique :** fatigue et limite d'interventions d'un même général ; interactions avec la priorité de `QG_nommade`.
- **Dernière charge :** format G/D précis dans la grammaire des ordres, statut exact des soldats relevés dans les fichiers et comportement s'il n'existe pas de flanc choisi chez le général précédent.
- **Gros_poisson :** syntaxe troisième/quatrième champ ; répartition et restitution des identités de soldats.
- **Ralliement :** source concrète des soldats « récupérés » après les pertes de l'allié, identité, blessures, mémoire et destination des renforts à la fin.
- Compatibilité des effets globaux entre eux (priorités, exceptions).

Ces questions sont de véritables décisions de gameplay. Un programmeur ne doit pas les déduire arbitrairement d'un ancien algorithme.

## Bilan des commits de préparation

1. `d1165ff` — 21 fiches et règles communes en documentation.
2. `a3d3716` — registre de conception désactivé.
3. `b7dcc35` — tests de contrat et d'absence d'activation.

Statut : modifications GitHub enregistrées, **tests non exécutés dans WSL par cette session**.

## Raccordement initial effectué après la préparation

- `python/ordres_pipeline.py` convertit les jetons connus et **actifs seulement** en IDs internes, sans regrouper plusieurs généraux et sans exécuter d'effet. Le module écarte volontairement les variantes avec paramètre : leur contrat (position/flanc/ordre) doit être défini pour chaque effet.
- `python/combats.py:resoudre_affrontement_actif` collecte au début de la résolution territoriale un instantané des intentions par général, **sans en faire usage** pour l'instant. La logique historique de `1-2` n'a pas été remplacée.
- `.dev/tests/test_ordres_pipeline_v2.py` teste la non-fusion, le filtrage des ordres indisponibles, le rejet des paramètres non validés et les jetons ambigus.
- Ce raccordement est un **jalon d'architecture**, pas l'intégration des nouveaux effets ni de leur opposition PC. Ne pas prétendre que les catégories de duel fonctionnent déjà en jeu.
- Aucune suite de tests exécutée depuis cette session ; Codex devra les lancer sur WSL à son retour.

### Prochaine implémentation

1. Construire une représentation explicite des intentions de chaque camp avec propriétaire, général donneur, catégorie, cibles et origine QG, sans dépendre des champs de texte libres.
2. Confronter les intentions sur une phase réelle avec une identité de donneur stable, puis produire une décision testable. Attention à ne pas sélectionner le QG à partir d'une donnée joueur falsifiable.
3. Tester les conditions d'opposition et d'absence d'ordre, y compris les catégories individuelles sans adversaire explicite.
4. Unifier uniquement ensuite le chemin historique `1-2` avec la sélection nouvelle, en comparant les résultats d'une même bataille avant/après.
5. Ajouter les effets dont les règles sont closes, un par un. Laisser les autres inactifs, sans hypothèse implicite.

## Seconde étape : API de confrontation pure (non exécutée par le combat)

- `python/ordres_pipeline.py:confronter_intentions` reçoit deux donneurs **explicitement choisis**, une catégorie et les PC **calculés ailleurs**. Elle sélectionne les ordres via `commandement.confronter_donneurs`. Elle n'applique aucun effet et ne choisit pas de QG ou d'adversaire.
- La fonction attend dans chaque donneur `{"general": {..., "caracteristiques": fiche_officielle}}`. **Le moteur territorial ne renseigne pas directement cette clé** : il faudra la construire à partir de `progression.caracteristiques_general` au moment du raccordement, sans accepter une fiche falsifiable du joueur.
- Tests nouveaux : égalité de deux ordres normaux, ordre face à contre-ordre, contre-ordre sans ordre adverse, absence des caractéristiques officielles.
- **Aucun appel de confrontation n'a été ajouté au combat réel.** Celui-ci collecte seulement les intentions. Le raccordement du commandement/QG reste une tâche distincte.
- Commits de cette étape : `b819cf0`, `2f45028`, `ce445a7`. Tests non exécutés dans cet environnement.

### Point d'attention sur le sens de « aucun ordre adverse »

Deux ordres ne se neutralisent qu'à l'intérieur d'une **même confrontation et catégorie**. Si le camp adverse n'a aucun ordre dans cette confrontation, les règles validées autorisent le contre-ordre (et aucun affrontement de PC entre deux ordres normaux n'a lieu). Ne pas comparer un ordre global à un ordre de duel pour l'annuler.
