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

## Troisième étape : donneurs liés aux données officielles

- `python/ordres_pipeline.py:donneurs_officiels` récupère pour chaque donneur ses caractéristiques de `progression.caracteristiques_general` (stockage privé), et non la fiche visible du joueur. Un donneur sans fiche privée est refusé.
- Les donneurs restent distingués par camp, position et général ; l'objet initial n'est pas modifié.
- Tests ajoutés dans `.dev/tests/test_ordres_pipeline_v2.py` : source privée authentique, refus en cas de progression manquante.
- **Toujours aucune activation d'ordre nouveau**, ni appel à `confronter_intentions` depuis `combats.py`. Pour la suite, sélectionner le QG officiellement et déterminer le calcul de PC pertinent à chaque confrontation ; ne pas inférer les donneurs depuis leur seule présence dans `ordre.txt`.
- **Exécution des tests restant à faire par Codex** ; ces commits ont été effectués uniquement via GitHub.

## Quatrième étape : calcul PC des duels, sans déclenchement d'effets

- `ordres_pipeline.points_duel_officiels(general)` relit la fiche moteur privée et la composition physique du général puis délègue au calcul existant `commandement.effectif_general` ; la valeur de `fiche.txt` n'entre pas dans le calcul.
- `ordres_pipeline.confronter_duel_officiel(general_1, general_2, donneur_1, donneur_2)` confronte explicitement les ordres de deux donneurs avec les PC des **généraux engagés**. N'applique pas leurs effets et ne choisit pas de donneurs. Ne pas supposer qu'un QG donneur doit utiliser ses propres PC plutôt que ceux de l'engagé sans décision.
- Tests ajoutés : composition officielle, ignorance de la fiche publique, égalité des PC, refus de progression privée absente.
- **Limite impérative :** pas encore de connexion de cette API à `combat_entre_generaux`. Les autres catégories (globale/individuelle), l'autorisation de QG, les cibles de duel et l'exécution des effets ne sont pas réglées.
- Ne pas fusionner le chantier tant que Codex n'a pas validé les tests et le raccordement en Linux.

## Décision confirmée : PC du QG émetteur pour les duels

- Lorsque le **QG émet un ordre de duel à la place du combattant**, comparer les PC du **général possédant le QG**, PAS ceux du combattant.
- La fonction `confronter_duel_officiel` applique désormais ce principe en calculant les PC de chaque **donneur** par `points_duel_officiels` (qui appelle `commandement.effectif_general` et compte les types d'unités présents).
- **Ne pas confondre** ce calcul avec la formule déjà codée pour les **ordres globaux** dans `commandement.global_armee` : `(2 * PC_QG + somme_PC_autres_strateges) // (2 * max(1, nombre_autres_generaux))`. Conserver cette formule tant qu'aucune autre modification n'a été validée.
- Le choix du QG actif reste externe et doit être lié à la sélection officielle `selectionner_qg` et à sa disparition éventuelle. Il n'est PAS encore connecté au combat.
- Le test `test_qg_donneur_duel_utilise_ses_pc_pas_ceux_du_combattant` protège cette décision.
- Aucun effet des 21 ordres encore activé ; tests ajoutés mais pas exécutés sous Linux dans cette session.

## Cinquième étape : premières formules V2 isolées

- `python/ordres_calculs_v2.py` contient seulement deux calculs purs dont la règle est complète : **Charge suicidaire** (`pertes_du_duel // 4`, pourcentage entier) et **Ralliement** (pour chaque type déjà présent chez le bénéficiaire, `pertes_du_type // 5`).
- `.dev/tests/test_ordres_calculs_v2.py` couvre les seuils, les arrondis et des données invalides. Tests **non exécutés sous Linux**.
- Les fonctions n'ont aucune mutation, tirage aléatoire, attribution d'unités ou application d'effet. Elles **ne sont pas appelées par le combat**. Le tirage de Charge suicidaire interviendra à la fin du seul duel lorsque l'ordre sera correctement activé.
- **Ne pas déduire** les effets « +10 % de moral » et « -1 % par unité cruelle » en points de moral bruts sans confirmer s'il s'agit de points de pourcentage ou d'un facteur multiplicatif. Aucun code de ces bonus n'a été conservé.
- Pour Ralliement, la provenance des pertes, les éventuelles identités, les blessures et le devenir des renforts doivent encore être spécifiés avant toute manipulation des soldats.
- Les commits sont exclusivement sur `feat/ordres-v2`; aucun effet supplémentaire n'est activé.
