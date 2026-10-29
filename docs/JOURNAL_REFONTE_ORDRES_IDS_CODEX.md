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
