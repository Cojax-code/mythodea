# Journal de refonte des ordres par identifiants — suivi Codex

Date de mise à jour : 2026-10-29  
Branche : `feat/ordres-v2`  
État : **modifications enregistrées, non testées**. Les tests, corrections de régression et leur validation sont réservés à Codex.

## Objectif et limites

Utiliser les identifiants permanents de `catalogues.ORDRES` dans les calculs et comparaisons internes. Conserver les noms pour les messages et rapports, les jetons historiques (`1-2`, `3-2`, etc.) pour `ordre.txt`. **Aucun changement intentionnel de gameplay.** Avant de retirer une compatibilité historique, rechercher tous ses appelants (y compris tests). Ne pas modifier les valeurs attendues d'un test simplement pour le faire réussir.

## Modifications enregistrées, dans l'ordre

| Commit | Fichier | Modification précise |
| --- | --- | --- |
| `5fbe87f` | `python/combats.py` | Deux lectures de l'attaque frontale emploient `catalogues.ORDRES[1002]['jeton']` au lieu du jeton `"1-2"` écrit en dur. |
| `9068766` | `python/ordres_pipeline.py` | `formations_retenues()` retourne `ordres` comme ensemble d'IDs plutôt que noms ; comparaisons Muraille `1019` et QG nomade `1016` adaptées. |
| `de505cd` | `python/combats.py` | Consommateurs des formations adaptées pour `1019` et `1016`. |
| `693d578` | `python/ordres_pipeline.py` | Le contexte des effets de duel mémorise les IDs retenus, non leurs noms. `effet(general, identifiant)` et ses appels internes utilisent les IDs : `1011` Choca-fuite, `1007` Discours de la mort, `1009` Rafale ; Cruelle vérifié avec `1010`. |
| `b6e1251` | `python/combats.py` | Effets consultés par IDs : `1014` Étincellant et `1006` Hérisson. |
| `1063c4b` | `python/ordres_pipeline.py` | Contrôles `progression.general_recoit_ordre` sur Muraille et QG nomade convertis en `1019` et `1016`. |
| `87a45d1` | `python/combats.py` | Contrôles de réception Attaque frontale `1002`, Muraille `1019` convertis en IDs (quatre occurrences au total). |

## Vérifications obligatoires de Codex

- **Avant exécution** : vérifier que toutes les modifications précédentes sont cohérentes avec l'état de la branche ; rechercher tous les appels à `ordres_pipeline.effet`, `formations_retenues`, `generaux_en_formation`, `qg_hors_formation`, `participants_muraille_territoire` et les usages de `formation['ordres']`. Rechercher aussi les accès directs au dictionnaire `['effets']`. Les tests et autres consommateurs peuvent attendre des noms.
- **Attention à `commandement.compatibilite_formations`** : le diagnostic `annules` reste actuellement nominal dans `preparer_compatibilites` et dans la confrontation frontale. Ne pas convertir une moitié de cette chaîne indépendamment : `frontal_autorise`, `retirer_ordres_annules`, les rapports et les confrontations doivent rester synchronisés. Cette partie **n'a pas encore été migrée**.
- Vérifier la politique Zombie / réception d'ordres dans `progression.py` : un nom et son ID doivent donner la même permission, notamment pour Attaque frontale, Muraille et QG nomade. Ne pas changer la règle.
- Vérifier l'ordre des généraux, les exclusions QG, la Muraille, les annulations internes et les oppositions Attaque frontale / On_melange ; conserver les séquences, les pertes, les tirages RNG et les rapports à comportement égal.
- Vérifier le fonctionnement de Hérisson, Étincellant, Cruelle, Rafale, Discours de la mort et Choca-fuite avec des demandes valides, annulées, indisponibles et des donneurs non autorisés.
- Vérifier la lecture des jetons historiques de `ordre.txt`, les éventuels consommateurs d'API externes et les formats persistants.
- **Tests confiés à Codex** : compilation Python des fichiers modifiés ; tests ciblés des ordres/formations/combats ; suite complète `python3 -B -m unittest discover -s .dev/tests -v` selon `AGENTS.md`. Fournir les résultats exacts (nombre de tests, échecs, corrections effectuées), puis seulement marquer ce journal « validé ».

## Points restant à migrer ou à décider

1. `preparer_compatibilites` manipule toujours des noms, par compatibilité avec les diagnostics et les rapports ; migration concertée nécessaire.
2. `commandement.compatibilite_formations` et `sequence_formation` acceptent encore les noms historiques et les IDs. Ne supprimer la compatibilité qu'après inventaire des appels.
3. Les textes de rapports et affichages doivent rester lisibles avec les noms du catalogue.
4. À cette étape, **aucune validation runtime, compilation ni test effectué** par ChatGPT.

## Consigne pour la reprise

Lire ce journal **et les diffs des commits**, puis comparer au code courant avant toute nouvelle refonte. Ce document décrit ce qui a effectivement été édité ; il ne garantit pas l'absence de régression.

## Grande Muraille : suivi des changements du 28 octobre 2026

Ces points sont a verifier par Codex ; aucun resultat de tests n'est confirme dans ce journal.

- QG territorial et fin des nouvelles selections apres destruction du QG.
- Tirage collectif sans remise, avec ponderation x2 pour le general engage.
- Victimes retirees uniquement du type de bloc engage et attribuees a leur general d'origine.
- Exemple : si 18 piquiers combattent et 6 archers restent inactifs, les archers ne perdent aucun soldat.
- Multiplicateurs et bonus Herisson calcules pour chaque general, avec fractions exactes.
- Moral propre a chaque general, sans double application des pertes.
- Enchainement des chocs, exclusion des generaux disparus et aucun second choc Avant.
- Rapports coherents, orientation des camps, effectifs et victimes, previsions sans mutation et RNG inchange.
- Confrontation de deux Murailles et regles de PC.

Commits reperes : 607cd78, f44df7a, 11598aa, 8080e1c, 792a9cf, c45da43, 6b7b636, 7d55e46, c940c99, 6cc282a, f6a52c8, 0692c2e, cd1f69f, 04be4c5, 4f618d1, a49c9de, 15f3e85.

Codex doit verifier les tests deja ecrits, executer les tests cibles et la suite complete prevue par AGENTS.md, puis documenter les resultats reels.

## Reprise du 29 octobre : annulations des formations

Commit : 9ebccd3.

Fichier modifie : python/ordres_pipeline.py.

- preparer_compatibilites construit une collection d'identifiants d'ordres ; Attaque frontale y entre par l'ID 1002 et le jeton du catalogue.
- Les incompatibilites continuent a passer par commandement.compatibilite_formations, qui sait deja recevoir des IDs.
- Le contexte interne des annulations conserve des IDs ; confronter_frontal_melange y ajoute directement les identifiants annules.
- frontal_autorise verifie l'ID 1002.
- Le rapport convertit les IDs des deux formations en noms du catalogue pour rester lisible.

Verifications reservees a Codex :

- [ ] Conflits de formations au sein d'un camp : deux ordres incompatibles sont annules, pas leurs voisins.
- [ ] Confrontation Attaque frontale / On_melange avec PC differents ou egaux et annulations successives.
- [ ] Aucun ordre annule n'est reactive apres disparition d'un donneur.
- [ ] Rapports de conflits : noms des ordres, et non IDs, toujours affiches.
- [ ] Rechercher les autres lecteurs de contexte['annules'] qui attendent potentiellement des noms.
- [ ] Verifier avec les cas Grande Muraille puis executer les tests conformement a AGENTS.md.

Statut : modification enregistree, aucun test execute dans cette session.

## Suite : filtrage des annulations par identifiant

Commit `4acc229` — `python/ordres_pipeline.py`.

- `retirer_ordres_annules()` ne parcourt plus le catalogue pour convertir des noms : il retire directement les IDs demandes.
- Le seul appel local encore nominal (`gros_poisson`) utilise desormais l'ID `1017`.
- Les appels depuis les annulations de formations et les restrictions de reception fournissent deja des IDs. Aucun changement de regle intentionnel.

**Attention pour Codex :** les tests dans `.dev/tests/test_formations_v2.py` utilisent encore des noms pour `commandement.compatibilite_formations()` et `sequence_formation()`, et attendent des noms dans certains resultats. Ils appellent aussi `ordres_pipeline.effet()` avec des noms et attendent des noms dans le contexte `annules`. La migration des effets et annulations du moteur vers les IDs rend ces attentes potentiellement obsoletes : Codex doit verifier la logique reellement voulue, adapter les tests si necessaire sans masquer une regression, puis lancer les validations.

- [ ] Verifier tous les appels de `retirer_ordres_annules` sur la branche, y compris dans les tests, et confirmer qu'ils fournissent des IDs.
- [ ] Verifier le cas `gros_poisson` sans cible : l'effet ID 1017 doit etre annule.
- [ ] Verifier cumul et persistance des annulations, attaque frontale / On_melange et effets sur zombies.
- [ ] Conserver temporairement l'interface nom/ID de `commandement.py` tant que les consommateurs et tests ne sont pas migrés.

Statut : code et notes enregistres ; tests non executes.

## Inventaire des dependances aux noms — 29 octobre 2026

Commit `02c3dcd` : dans `python/ordres_pipeline.py`, `ordres_du_general()` transmet desormais l'ID de l'ordre a `progression.ordre_autorise()` plutot que son nom. Cette fonction accepte deja les IDs, notamment pour les restrictions Zombie.

Inventaire actuel : les noms restent necessaires dans `commandement.compatibilite_formations()` et `sequence_formation()` pour des tests et interfaces existants, dans `progression.py` pour les politiques qui prennent des noms, ainsi que pour les rapports. Les jetons de `ordre.txt` sont conserves. La suppression globale de cette compatibilite n'est donc pas realisee.

Tests pour Codex :
- [ ] Verifier le filtrage `ordres_du_general()` pour profils Zombie et non-Zombie, ordres valides et interdits.
- [ ] Rechercher les appels de fonctions acceptant des noms avant toute suppression de compatibilite.
- [ ] Verifier les attentes des tests de formations et du pipeline qui utilisent encore les noms.
- [ ] Tester les annulations de formations et la Grande Muraille apres cette migration.

Statut : code et journal enregistres ; aucun test execute par ChatGPT.
