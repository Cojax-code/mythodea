# Validation Codex — Grande Muraille et migration des IDs

**Branche :** `feat/ordres-v2`  
**Dernière mise à jour :** 29 octobre 2026  
**État :** code enregistré ; **compilation, tests et régressions non vérifiés par ChatGPT**.  
**Décision :** geler les refontes supplémentaires jusqu'à la validation de Codex. Aucune modification de gameplay demandée.

## 1. Contrat à préserver

- Le moteur utilise les IDs permanents de `catalogues.ORDRES` pour ses décisions, formations, annulations et effets.
- Les jetons existants (`1-2`, `3-2`...) restent valides dans `ordre.txt` ; les noms restent lisibles dans les rapports et affichages.
- Certaines interfaces publiques de `commandement.py` et `progression.py` acceptent encore des noms pour leurs appelants existants. **Ne pas les supprimer sans inventaire complet.**
- Ne changer ni règles, ni priorités, ni tirages RNG, ni pertes, ni formats persistants. Une incohérence de gameplay exige une décision avant correction.
- La présence de tests dans le dépôt **ne prouve pas leur réussite**. Codex est responsable de la vérification et des corrections.

## 2. Changements à valider

### A. Grande Muraille — travaux du 28 octobre

| Domaine | Modifications enregistrées | Commits de référence |
| --- | --- | --- |
| Autorité du QG | Transmission fondée sur le QG territorial ; arrêt des nouvelles désignations après destruction du QG | `607cd78`, `0052dd6`, `f2ba039` |
| Tirage et victimes | Tirage collectif sans remise, poids ×2 du général engagé, attribution des victimes aux propriétaires, sans second tirage | `f44df7a`, `51da0e9`, `11598aa`, `8080e1c` |
| Engagements territoriaux | Enchaînement des chocs, effectifs initiaux, exclusion des généraux disparus et garde de résolution territoriale | `792a9cf`, `c45da43`, `6b7b636`, `e21cc2f`, `c9bacf1` |
| Suite et rapports | Pas de second choc Avant ; orientation, types, bilan d'élimination et RNG des prévisions | `7d55e46`, `c940c99`, `3aa2327`, `a32e623`, `6cc282a` |
| Compatibilités | Confrontation des PC lorsque deux Murailles sont demandées | `6498d16` |
| Blocs et bonus | Comparaison collective par type engagé, bonus Hérisson par général, fractions exactes, prévisions sans double tirage | `f6a52c8`, `0692c2e`, `cd1f69f`, `04be4c5`, `4f618d1` |
| Moral et participants | Moral individuel ; identité des participants consignée pour les chocs collectifs | `a49c9de`, `15f3e85` |

### B. Passage aux IDs — travaux du 29 octobre

| Fichiers | Modifications | Commits |
| --- | --- | --- |
| `combats.py` | Attaque frontale via jeton du catalogue ; effets et réceptions via IDs ; consommateurs des formations adaptés | `5fbe87f`, `de505cd`, `b6e1251`, `87a45d1` |
| `ordres_pipeline.py` | Formations et effets de duel par IDs ; annulations et filtrage par IDs ; restrictions et sélection par IDs | `9068766`, `693d578`, `1063c4b`, `9ebccd3`, `4acc229`, `02c3dcd`, `10eb53f` |
| `commandement.py` | Autorisations par ID et conversion nom/ID mutualisée dans le diagnostic des formations | `fa1e757`, `ca6d920` |
| `progression.py` | Contrôles des évolutions et permissions par ID ; logique Zombie regroupée, avec compatibilité nominale préservée | `6aacb00`, `e8d1525`, `8bda055` |
| `generaux.py` | Vérification de possession d'ordre par ID, avec jeton externe inchangé | `e19506c` |
| `bouclier_vivant.py`, `soldats.py`, `unites.py` | Confinement 1013, Gros Poisson 1017, Orc un jour orc toujours 1008, Propagafion 1012 | `cdd6d01`, `b98137f`, `237a60b` |

Les commits ci-dessus permettent de retrouver les diffs exacts ; ce document évite de recopier chaque ligne changée. Les corrections d'une éventuelle régression doivent être décrites séparément.

## 3. Checklist de validation Codex

### Priorité 1 — Cohérence des interfaces ID/nom

- [ ] Inventorier les appels à `ordres_pipeline.effet`, `formations_retenues`, `generaux_en_formation`, `qg_hors_formation`, `retirer_ordres_annules` et les accès directs aux contextes `effets` / `annules`.
- [ ] Comparer les attentes des tests existants, notamment `.dev/tests/test_formations_v2.py`, avec les nouvelles valeurs internes (IDs). **Adapter uniquement les assertions dont le contrat a effectivement changé**, sans masquer un bug.
- [ ] Vérifier `compatibilite_formations` et `sequence_formation` pour noms, IDs, entrées mixtes et paires multiples : incompatibilités, ordre des diagnostics et placement identiques à l'existant.
- [ ] Vérifier les annulations durables, notamment Attaque frontale / On_melange, PC égaux ou différents, et disparition du donneur.
- [ ] Vérifier la lecture des anciens jetons `ordre.txt`, les formats persistants et les noms dans les rapports.

### Priorité 2 — Grande Muraille

- [ ] Cas concret : **18 piquiers et 6 archers** dans des blocs distincts. Si seuls les piquiers combattent, les archers ne subissent aucune perte ; tester également le cas inverse.
- [ ] Force collective du seul type engagé, avantages et Hérisson propres aux généraux, fractions exactes et gestion des blocs vides.
- [ ] Tirage sans remise, pondération ×2 lorsque prévue, attribution aux vrais propriétaires et absence de double tirage / double perte.
- [ ] Moral et sauvetages propres à chaque général ; vérifier les pertes après moral.
- [ ] Relecture des Avant à chaque engagement, exclusion des généraux disparus, arrêt des nouvelles désignations quand le QG est détruit ; aucun second choc Avant.
- [ ] Confrontation Muraille/Muraille, PC et incompatibilités ; ne pas supprimer arbitrairement un `NotImplementedError` relatif à une règle non tranchée.
- [ ] Prévisions sans mutation ni consommation du RNG réel, reproductibilité, orientation des camps, participants et effectifs dans les rapports.

### Priorité 3 — Autres ordres, progression et régression

- [ ] Hérisson, Étincellant, Cruelle, Rafale, Discours de la mort, Choca-fuite, Gros Poisson, Confinement, Orc un jour orc toujours et Propagafion : activation, annulation, indisponibilité et conditions d'éligibilité.
- [ ] Restrictions Zombie / non-Zombie : **émission et réception distinctes** ; IDs et anciens noms acceptés aux interfaces prévues ; ordres inconnus.
- [ ] Acquisition, nature (y compris hybrides), évolutions ciblées, possession d'ordres et absence de permissions accidentelles.
- [ ] Aucune différence non voulue de déroulement, pertes, rapports ou tirages RNG par rapport au gameplay spécifié.

## 4. Exécution et restitution attendues

Codex doit :

1. Lire `AGENTS.md`, `MYTHODEA_SPEC.md`, `SURVIE_SPEC.md` selon le périmètre, ainsi que les fichiers et tests pertinents.
2. Compiler les modules Python modifiés, puis exécuter les tests ciblés (formations, ordres, Muraille, progression).
3. Exécuter la suite complète prévue par `AGENTS.md` : `python3 -B -m unittest discover -s .dev/tests -v`.
4. Corriger uniquement les régressions confirmées ; **ne pas modifier le gameplay sans accord explicite**.
5. Renseigner dans ce journal la date, le commit validé, les commandes, le nombre de tests réussis/échoués, les corrections, les cas non couverts et les blocages.

## 5. Pré-vérification isolée ChatGPT — 29 octobre 2026

**Limite cruciale :** le clonage GitHub vers le conteneur Python a échoué (résolution DNS inaccessible). Les fichiers du dépôt **n'ont pas été importés ni exécutés dans leur environnement réel**. La pré-vérification a porté sur une reproduction isolée du diagnostic de `commandement.compatibilite_formations`, avec la matrice d'IDs et les noms lus dans le catalogue. Ce résultat **ne remplace pas** les tests réels de Codex.

- **7 vérifications Python isolées réussies sur 7** : paires interdites et compatibles, paire ouverte, équivalence nom/ID, doublon nom+ID, ordre Pour l'honneur et stabilité face à l'ordre d'entrée.
- **0 échec, 0 erreur** dans cette reproduction.
- Contrôle statique du catalogue : `1008`, `1012`, `1013`, `1017`, `1018`, `1022` ont été retrouvés avec leurs noms attendus.
- **Compilation du dépôt et suite officielle : non exécutées.**
- Aucune correction Python apportée lors de cette pré-vérification.

Attention : les tests du dépôt peuvent encore attendre des noms dans les contextes internes `annules` et `effets` ; cela doit être déterminé par les tests réels, sans assimiler automatiquement une assertion ancienne à une régression.

## 6. Résultats Codex — à compléter après exécution

- **Commit / date de validation :** à renseigner
- **Compilation :** non vérifiée
- **Tests ciblés :** non exécutés ici
- **Suite complète :** non exécutée ici
- **Échecs / régressions :** inconnus avant validation
- **Corrections réalisées par Codex :** aucune consignée
- **Décisions de gameplay en attente :** à préciser si rencontrées
- **Statut final :** EN ATTENTE DE VALIDATION

**Prochaine étape recommandée :** confier ce lot à Codex et stabiliser la V2.0 avant d'envisager d'autres refontes.

## Première campagne exécutée sur ZIP utilisateur — 29 octobre 2026

Source : archive `Mythodea_code.zip` reçue dans la conversation, extraite dans un répertoire isolé ; aucune modification des fichiers Python sur GitHub.

- **Compilation** : `python3 -m compileall -q python .dev/tests` : succès (code retour 0).
- **Suite complète** : `PYTHONPATH=python:.dev/tests python3 -B -m unittest discover -s .dev/tests -v` : interrompue par la limite d'exécution pendant `test_audit_v2`, sans bilan final. Ne pas déclarer la suite réussie.
- **Suite ciblée** : modules `test_formations_v2`, `test_ordres_calculs_v2`, `test_ordres_conception_v2`, `test_ordres_confrontation_v2`, `test_ordres_effets_v2`, `test_ordres_pipeline_v2`, `test_qg_effets_v2`, `test_qg_retraites_v2`, `test_soldats_formation` : interrompue pendant `test_qg_effets_v2`. Parmi **181 résultats affichés**, 21 ont le statut FAIL ou ERROR. Ce décompte n'est pas un résultat final d'une suite complète.
- **Reproduction indépendante de quatre échecs ciblés** : 4 tests exécutés, 4 FAIL, en 0,629 s.

Échecs reproduits :
1. `test_ordres_pipeline_v2.PipelineOrdresTest.test_muraille_territoriale_exclut_qg_reserve_et_zombie` : participants `()` au lieu d'un général attendu.
2. `test_qg_effets_v2.EffetsQG.test_destruction_pendant_duel_preserve_transmis_et_interdit_suivant` : `effet(a, 'orc_un_jour_orc_toujour')` faux au lieu de vrai.
3. `test_qg_effets_v2.EffetsQG.test_global_formule_egalite_normaux_et_contre_ordre` : `effet(a, 'etincellant')` faux au lieu de vrai.
4. `test_qg_effets_v2.EffetsQG.test_propagafion_zombie_toutes_natures_qg_acquisition_et_profil_prive` : `effet(a, 'propagafion')` faux au lieu de vrai.

**Diagnostic provisoire** : plusieurs tests attendent des noms alors que le moteur utilise maintenant des IDs. Cela explique probablement certains FAIL, **mais pas nécessairement les autres erreurs de combat et de formation**. Codex doit examiner les traces complètes et vérifier le contrat avant de corriger. Ne pas faire passer artificiellement les tests en rétablissant des noms dans la logique interne, ni modifier les attentes sans justification. Les échecs sont observés sur le ZIP fourni ; vérifier qu'il correspond exactement au commit GitHub visé.

**Statut : validation incomplète ; anomalies avérées dans l'exécution des tests existants.**

## Mise a jour des tests vers les IDs — 29 octobre 2026

Six fichiers `.dev/tests` ont ete modifies directement sur `feat/ordres-v2` a partir des corrections preparees dans l'archive ZIP. **Aucun fichier du moteur Python n'a ete modifie.**

| Fichier de test | Commit |
| --- | --- |
| `test_formations_v2.py` | `cd7727d` |
| `test_qg_effets_v2.py` | `579a047` |
| `test_restrictions_zombies.py` | `b3a8bef` |
| `test_ordres_effets_v2.py` | `43b06b7` |
| `test_gros_poisson.py` | `603f46e` |
| `test_participations_temporaires.py` | `38f6710` |

Seules les assertions qui interrogeaient les effets par leurs anciens noms, ainsi que le contexte interne `annules` et le jeu d'effets artificiel des tests Zombie, ont ete passes aux IDs du catalogue. Les noms attendus dans les rapports et les appels publics compatibles restent inchanges.

Avant publication, les corrections locales sur ZIP avaient permis de faire passer les quatre cas d'echec reexamines et 13 tests du module QG ; **ces resultats ne sont pas une execution de la suite complete du nouvel etat GitHub**. Codex doit relancer les tests sur la pointe de branche, noter les echecs restants et verifier specialement Grande Muraille. Ne jamais modifier les assertions des regles de combat simplement pour obtenir un test vert.

## Campagne complémentaire réelle sur copie isolée du ZIP — 29 octobre 2026

Méthode : extraction de `Mythodea_code.zip`, superposition des six fichiers issus de `mythodea_tests_ids_corriges.zip`, environnement Python isolé ; aucune modification du moteur ni de la branche pendant l'exécution.

- `python -m compileall -q python .dev/tests` : **OK**.
- Groupe de 11 modules ciblés avec `unittest -q` : **230 tests exécutés**, **3 FAIL et 13 ERROR**, en 67,993 s. Ce groupe n'est pas la suite exhaustive.
- Modules lancés séparément : `test_qg_effets_v2` **13/13 OK** ; `test_gros_poisson` **22/22 OK** ; `test_soldats_formation` **24/24 OK** ; `test_restrictions_zombies` **8/8 OK** ; `test_ordres_conception_v2` **5/5 OK** ; `test_ordres_confrontation_v2` **14/14 OK**.
- `test_ordres_calculs_v2` : 40 tests, 1 ERROR ; mock `Path.is_dir` ne supportant pas l'argument nouvellement passe dans `test_muraille_ne_reselectionne_pas_general_disparu` (trace complète à vérifier).
- `test_ordres_pipeline_v2` : 18 tests, 1 FAIL ; participants Muraille `()` au lieu de `(general3,)`.
- `test_formations_v2` : 23 tests, 1 FAIL et 8 ERROR ; notamment wrappers de `combat_entre_generaux` qui n'acceptent pas les nouveaux arguments nommés `avant_exclus_manoeuvre` et `avant_deja_resolu` (vérifier chaque traceback avant correction), plus une attente liée aux formations.
- `test_participations_temporaires` : 43 tests, 1 FAIL et 1 ERROR ; prévision des survivants avec `KeyError: 'survivants'` et score Muraille `[3, 2]` au lieu de `[4, 0]`.
- `test_ordres_effets_v2` : dépassement de la limite de 17 s lors de son lancement isolé ; **pas de verdict par module**.

Interprétation : plusieurs modules ordres/permissions sont au vert, mais des régressions ou contrats de tests divergents subsistent autour de Grande Muraille, des wrappers et des données de prévision. Ne pas les attribuer systématiquement aux IDs ni modifier arbitrairement le gameplay. **Statut : non validé ; suite exhaustive et tests Linux restant à faire par Codex.**

## Correction des tests sans modification gameplay — 29 octobre 2026

Commit `106ecf2` — `.dev/tests/test_formations_v2.py` seulement.

- Quatre wrappers de `combat_entre_generaux` acceptent et retransmettent `**options` pour préserver les nouveaux arguments de Grande Muraille lors des mocks.
- L'assertion sur `formations['j2']['ordres']` attend désormais `{1016}` au lieu de `{'qg_nommade'}`, car ce contexte interne contient des IDs.
- Vérification sur copie isolée de `Mythodea_code.zip` avec les six tests IDs corrigés : `PYTHONPATH=python:.dev/tests python3 -B -m unittest -q test_formations_v2` : **23 tests, OK**, ~9,8 secondes.
- Avant correction : 23 tests, 1 FAIL + 8 ERROR. Les autres fichiers de la suite et les bugs Muraille non liés à ces deux causes restent à vérifier.
- **Aucun module du moteur ou règle de gameplay modifié.** Ne pas assimiler ces 23 réussites à la validation totale de Mythodea.

### Autre correction de mock — Grande Muraille

Commit `5ce498e` — `.dev/tests/test_ordres_calculs_v2.py` seulement : `patch.object(Path, 'is_dir', autospec=True, side_effect=...)` transmet correctement le chemin au mock, alors que la version précédente causait `TypeError: <lambda>() missing 1 required positional argument: 'p'`. Validation locale : `PYTHONPATH=python:.dev/tests python3 -B -m unittest -q test_ordres_calculs_v2` : **40 tests, OK**. Aucun changement du moteur. Les autres anomalies de Grande Muraille demeurent non validées.

## Diagnostic cible Grande Muraille — 29 octobre 2026

Correction certaine du test (sans changement du moteur) : `7e248a6` modifie `.dev/tests/test_ordres_pipeline_v2.py` : la formation construite directement par le test utilise `{1019, 1016}` plutot que les noms. Verification locale : `PYTHONPATH=python:.dev/tests python3 -B -m unittest -q test_ordres_pipeline_v2` : **18 tests, OK**.

Deux scenarios `test_participations_temporaires` revus individuellement :
- `test_previsions_muraille_blocs_distincts_sans_mutation_ni_classement` : **OK** sur la copie du code ; ne pas attribuer `KeyError: survivants` a ce scenario sans traceback exact.
- `test_muraille_chaque_moral_origine_et_blessures_changent_le_classement` : **FAIL confirme** : scores reels `[3, 2]`, attente `[4, 0]` lorsque deux generaux piquiers sont regroupes avec des moraux distincts. La simulation actuelle calcule le choc par groupe de meme type, puis repartit les victimes et applique le moral individuel. L'attente pourrait predater ce fonctionnement collectif : **ne pas changer la formule ni l'assertion sans trancher explicitement la signification du score par general**.

Attente de decision de gameplay sur la notation des candidats au sein d'un meme groupe de type ; validation des autres anomalies encore ouverte.

## Decision de gameplay confirmée — Grande Muraille (29 octobre 2026)

**Regle tranchee par le concepteur :** les candidats au combat sont des **blocs collectifs reconstitues par type d'unite** (par exemple les piquiers de G1 et G2 forment un seul bloc). On evalue la performance de ce bloc collectif contre le bloc Avant adverse actuel ; on ne classe pas les generaux selon une simulation de duel individuel. **Avant chaque nouvel affrontement**, relire les survivants et les blessures/pertes reelles, reconstruire les blocs collectifs eligibles, et recalculer lequel est le mieux adapte a l'Avant adverse restant. Un type non engage ne subit aucune perte de cet affrontement. La propriete et le moral des soldats restent propres a leurs generaux d'origine.

**Impact sur le code actuel a auditer :** `combats.prochain_avant_muraille()` appelle `simuler_avants_muraille()` puis `choisir_avant_muraille({p['origine']: p['score'] ...})`, ce qui parait encore selectionner une **origine de general** au lieu de classer explicitement des **blocs collectifs par type**. `engager_avant_muraille()` maintient une identite de general engage et un traitement collectif des pertes ; il faut verifier que ce raccordement respecte la selection du meilleur type collectif. Ne pas modifier automatiquement les scores du test `test_muraille_chaque_moral_origine_et_blessures_changent_le_classement` : son classement individuel `[4, 0]` n'est potentiellement plus une attente pertinente. Revoir et renommer ce test pour couvrir la nouvelle regle, et ajouter un scenario de recalcul apres pertes. **Aucune correction du moteur effectuee au titre de cette decision dans cette entree.**

## Correctif selection collective Grande Muraille — 29 octobre 2026

Decision appliquee : les previsions comparables representent chacune **un type de bloc collectif**, et non chaque general qui possede ce type. Avant chaque affrontement, `prochain_avant_muraille()` relit les blocs des generaux actifs et relance les simulations pour les effectifs actuels. Les victimes du seul type engage conservent leur general proprietaire et son moral.

Commits :
- `a552245` — `python/combats.py` : `simuler_avants_muraille` groupe les contributions de meme type une fois, les ordonne de facon stable par emplacement/identite et retient un representant unique par groupe pour l'interface existante du moteur. Pas de modification des formules de degats ni du moral.
- `cbd9e01` — `.dev/tests/test_ordres_calculs_v2.py` : une prevision de piquiers collectifs, une d'archers, au lieu d'une par general.
- `bf6c8cf` — `.dev/tests/test_participations_temporaires.py` : le test remplace l'ancien classement individuel par regroupement, independance de l'ordre d'entree et recalcul apres blessures.

Verification locale sur copie extraite du ZIP avec les memes changements : `PYTHONPATH=python:.dev/tests python3 -B -m unittest -q test_ordres_calculs_v2 test_participations_temporaires.ParticipationsTemporaires.test_muraille_meme_type_forme_un_bloc_et_recalcule_apres_blessures` : **41 tests, OK**. La suite complete et le nouveau commit GitHub ne sont pas verifies par cette execution.

Points de vigilance pour Codex :
- [ ] Le representant d'un type est choisi par la position numerique la plus basse, puis l'identite, afin de transmettre le choc existant. Verifier avec les regles d'autorite QG et de ponderation x2 des victimes.
- [ ] Verifier qu'apres chaque choc les effectifs sont relus et que les autres types restent intacts ; verifier egalement le cas de plusieurs generaux du meme type et la limite d'engagement par choc initial.
- [ ] Examiner les autres tests de previsions qui supposaient un resultat par general, ainsi que l'effet des differentes fatigues, moraux et bonus individuels sur le score collectif.
- [ ] Lancer les tests cibles complets puis la suite generale et consigner tout echec restant.

## Audit complémentaire Muraille — décision nécessaire

Lecture de `combats.enchainer_avants_muraille()` et `engager_avant_muraille()` : le pilote retire de `disponibles` seulement l'identité du général représentant après un choc, alors que le choc a employé les Avant de **tous** les généraux du même type. Ceux-ci peuvent donc rester candidats au choc suivant via un autre représentant. Inversement, un type représenté par un seul général ne peut plus être choisi, même s'il conserve des soldats. Ce comportement n'est pas une application uniforme de la règle de recalcul collectif après chaque choc.

**Décision demandée avant correction :** un bloc collectif de type déjà engagé et survivant peut-il être sélectionné de nouveau au choc initial suivant contre le même Avant adverse, ou chaque bloc collectif n'a-t-il qu'un seul engagement au choc initial ? Selon la réponse, le pilote doit conserver ou retirer l'ensemble des contributeurs du type après un engagement. Vérifier également l'arrêt lors de la disparition du général adverse et les règles des Avant exclus de la manoeuvre. Aucun changement du moteur dans cet audit.

## Clarification sur la fin d'un affrontement Grande Muraille — 29 octobre 2026

**Decision du concepteur (remplace toute interpretation de reengagement continu) :** un affrontement oppose un bloc Avant collectif Muraille (un type, plusieurs generaux possibles) au bloc Avant du general adverse, **jusqu'a ce que l'un des deux blocs soit elimine**. On ne rechoisit pas le bloc Muraille a chaque perte partielle.

- Si le bloc Muraille est elimine et que l'Avant adverse possede encore des soldats, choisir parmi les autres blocs collectifs Avant Muraille **non engages**, a partir des forces actuelles, puis lancer l'affrontement suivant contre les survivants adverses.
- Si le bloc Avant adverse est elimine, il n'existe normalement plus de bloc Avant a affronter pour ce general : **arreter la sequence de Grande Muraille contre cet adversaire**.
- Les blesses ne constituent pas un bloc disponible. Ne pas selectionner une seconde fois un bloc collectif deja engage et survivant.
- Le recalcul du meilleur bloc n'a lieu que lorsqu'un bloc Muraille de remplacement devient necessaire, et non apres chaque perte individuelle au cours du meme affrontement.

**A verifier/corriger dans `combats.enchainer_avants_muraille()` :** retirer des candidats tout le bloc collectif de type deja engage, pas seulement le general representant ; interrompre des que l'Avant adverse a disparu ; conserver la repartition des pertes par origine, les regles de moral et les priorites deja definies. Tests cibles necessaires (relais piquiers -> archers, victoire du premier bloc, absence de second engagement du meme type, morts/blesses). **Aucune modification Python dans cette entree.**

## Correctif : relais des blocs collectifs au choc initial — 29 octobre 2026

**Règle confirmée :** un affrontement oppose le bloc Avant collectif sélectionné au bloc Avant adverse jusqu'à disparition complète d'un des deux. Si l'Avant Muraille est éliminé et que l'Avant adverse survit, seuls les autres types Avant non engagés peuvent prendre le relais. Si l'Avant adverse est éliminé, la séquence s'arrête. Aucun bloc collectif du même type ne peut être sélectionné plusieurs fois sous un autre général représentant.

**Code** : commit `3c524a5` (`python/combats.py`, `enchainer_avants_muraille`). Capture du type de chaque contributeur avant le choc ; retrait de tous les représentants du type engagé ; arrêt immédiat lorsque le résultat indique `final_2 == 0` ou lorsque le dossier adverse disparaît. Conservation du comportement des appels de pilotage simulés sans chemin pour les anciens tests. Aucun changement des formules de dégâts, du moral ou des pertes.

**Tests** : commit `ea28008` (`.dev/tests/test_ordres_calculs_v2.py`). Deux scénarios ajoutés : deux généraux piquiers partagent un engagement puis les archers prennent le relais ; victoire du premier bloc arrête la séquence. Vérification sur copie isolée avec le même correctif et deux tests équivalents : **42/42 OK** (40 anciens tests calculs + 2 tests de relais). Les tests nouvellement publiés sur GitHub et la suite exhaustive doivent encore être exécutés par Codex sur l'état final.

**Attention Codex :** vérifier sur combats réels que `final_2` reflète les survivants du bloc adverse après toutes les pertes, et que des soldats sauvés par le moral ne provoquent pas un second engagement non voulu ; revoir également le cas de plusieurs types et des exclusions QG/réserve, la disparition d'un général et la reproductibilité RNG. Valider les limitations de la gestion du général représentant et les autres interactions Muraille documentées plus haut.

## Audit du choc collectif : exclusions des roles (29 octobre 2026)

**Bug corrige** : la selection de `prochain_avant_muraille` excluait les identites de `qg_nommade` et de `reserve_strategique`, mais l'engagement automatique dans `enchainer_avants_muraille` passait tous les generaux initiaux a `engager_avant_muraille`. Les soldats exclus pouvaient alors etre integres au combat collectif s'ils avaient le type engage.

- `7631356` — `python/combats.py` : l'engagement par defaut applique `ordres_calculs_v2.participants_muraille()` avant de transmettre les membres au combat reel ; les donneurs exclus ne contribuent plus au bloc collectif.
- `94bd064` — `.dev/tests/test_ordres_calculs_v2.py` : test de regression avec un general admissible, un QG nomade et une reserve ; controle des membres effectivement remis a `engager_avant_muraille`.

**Validation attendue de Codex** : executer le nouveau test et l'ensemble des tests de calcul, puis un choc collectif reel avec des blocs de meme type chez QG et reserve pour confirmer que leurs unites ne frappent pas et ne subissent aucune perte. Examiner la selection du general representant et la ponderation x2, ainsi que les cas de blessures, disparition du QG et arret du choc. **Aucun resultat de test n'est revendique pour ces nouveaux commits dans cette entree.**

## Audit du moral collectif Grande Muraille — 29 octobre 2026

Lecture de `combats.engager_avant_muraille`, `combats.simuler_avants_muraille` et `soldats.repartir_victimes_muraille` / `appliquer_victimes_muraille` / `pertes` / `prevoir_pertes` : le calcul numerique est collectif, les victimes sont tirees une seule fois, puis classees par proprietaire. Les moraux sont obtenus individuellement via `moral_des_pertes(bloc, general)` et appliques dans le bloc d'origine. La ponderation x2 concerne les victimes du general representant ; aucune anomalie certaine de double tirage ni d'application globale du moral identifiee dans ces fonctions.

**Question de gameplay a trancher :** les soldats sauves par le moral sont blesses mais restent comptes dans `infos['nombre']` et donc dans `final_1` de `engager_avant_muraille`. Si les pertes numeriques du choc sont totales mais qu'un soldat est sauve, le bloc Avant reste non vide et le relais par un autre type peut ne pas se declencher. Le concepteur avait precise que le relais intervient a l'elimination du bloc « sans compter les blessures » ; clarifier si un blesse sauve par moral reste apte a poursuivre le meme affrontement, ou s'il est ecarte du choc initial et ne bloque pas le relais. Ne pas changer cette logique tant que la distinction n'est pas confirmee. Tests reels croisant moral 0 / 100, blessure et relais a ajouter une fois la regle definie.

## Décision appliquée : moral et relais de Grande Muraille — 29 octobre 2026

**Règle du concepteur :** les soldats sauvés par moral survivent et prennent une blessure, mais sont **hors combat pour le choc initial** ; ils ne doivent pas empêcher le relais du prochain type Avant collectif. Le moral ne ramène pas au combat un bloc entièrement vaincu lors du calcul du choc.

- `df7a8aa` (`python/combats.py`) : dans le rapport structuré du choc Muraille, `final_1` et `final_2` continuent de désigner les effectifs physiquement vivants après les sauvetages ; nouveaux `combattants_1` / `combattants_2` portent les survivants du calcul du choc **avant moral**. L'enchaînement s'arrête si les adversaires sont vaincus (`combattants_2 == 0`), et peut engager un nouveau type si le bloc Muraille a perdu (`combattants_1 == 0`) malgré ses blessés sauvés. Les anciens pilotes simulés sans ces champs gardent la compatibilité antérieure.
- `cebdb24` (`.dev/tests/test_ordres_calculs_v2.py`) : deux tests de régression, relais malgré `final_1 > 0` lorsque `combattants_1 == 0`, et arrêt malgré `final_2 > 0` lorsque `combattants_2 == 0`.

**A vérifier par Codex** : exécuter tests ciblés et suite complète, avec scénarios de combat réel et moral 0/100 ; contrôler aussi l'intégration de ces deux nouveaux champs aux rapports. Aucun test d'exécution sur la branche GitHub n'a été réalisé durant cette modification, et il reste à auditer d'éventuels usages de `final_1` / `final_2` pour déterminer les engagements ailleurs dans le moteur.

## Audit pondération x2 / représentant Muraille — 29 octobre 2026

Le tirage `soldats.repartir_victimes_muraille` privilégie par poids 2 les soldats du général représentant, poids 1 ceux des autres contributeurs de même type ; tirage sans remise, victimes rattachées à leurs vrais propriétaires, et moral traité ensuite séparément. Les tests statistiques préexistants vérifient approximativement le ratio x2. Aucun changement de pondération ni de moral.

**Incohérence corrigée** : les prévisions triaient les membres d'un bloc de même type par emplacement puis identité, mais `engager_avant_muraille` préservait l'ordre d'entrée. Pour un tirage reproductible, `e0812b8` ordonne désormais les contributeurs réels comme ceux des prévisions, avant la création du pool et le tirage. Le général engagé / représentant reste celui transmis par la sélection, sans changement de règle.

**Régression ajoutée** : `4dcae5c` teste que le tirage reçoit les blocs dans l'ordre canonique même si les généraux sont fournis dans l'ordre inverse, et que la priorité x2 reste attachée au représentant engagé. À lancer sous Linux par Codex avec les tests `test_ordres_calculs_v2`, tests de prévision et suite complète. Pas de suite exécutée dans cette intervention ; prudence sur les autres effets aléatoires et rapports de combat.

## Audit Herisson, bonus individuels et commandement — 29 octobre 2026

- `combats.combat_bloc` calcule en Grande Muraille les valeurs par contributeur (`contributions_1`) et la moyenne ponderee par effectif, ce qui evite de donner Herisson aux piquiers d'un autre general ; `simuler_avants_muraille` et `engager_avant_muraille` utilisent tous deux cette fonction. **Pas de modification necessaire identifiee sur ce point.**
- `combats.multiplicateur` donne aussi une faiblesse x3 contre les unites a distance quand le piquier defend sous Herisson. Ce comportement, initialement suspect, est **explicitement couvert** par `test_ordres_effets_v2.test_herisson_faiblesse_distance_egalement_augmente` : ne pas inverser ce bonus sans decision du concepteur.
- La transmission QG est verifiee entre les engagements via `transmission_muraille_active` (pas pendant le choc), et `verifier_qg` intervient apres les pertes. L'usage des effets individuels `ordres_pipeline.effet` depend du contexte du duel : validation sur batailles reelles a demander a Codex.
- Point d'audit encore ouvert : les simulations utilisent un RNG copie alors que certaines suppressions reelles passent par le RNG global ; confirmer la reproductibilite des previsions et l'absence de tirages consommes en double en test d'integration. Ne pas modifier sans reproduction.

Pas de bug certain corrige ni de tests executes pendant cet audit. Les changements eventuels doivent respecter la mecanique intentionnelle d'Herisson contre les archers.

## Audit groupe des 6 controles Muraille / Herisson / QG — 29 octobre 2026

Controle statique du code actuel sur `feat/ordres-v2` (pas une campagne de tests executee) :
1. **Herisson individuel** : `combat_bloc(contributions_1=...)` calcule une contribution et multiplicateur par general ; tests unitaires existants, controle deja fait la veille. **Formule OK**, MAIS activation dans Muraille reel non assuree (voir anomalie).
2. **Calcul collectif** : moyenne ponderee par effectifs des contributeurs de meme type, calcul avec `Fraction`, idem prevision et choc. **Formule OK**.
3. **Faiblesse Herisson contre distance** : branche de `multiplicateur` existante, test de regression `test_herisson_faiblesse_distance_egalement_augmente`. **Comportement conforme au test historique**, sans modification.
4. **Transmission QG** : `transmission_muraille_active` au debut de chaque nouveau choc ; `verifier_qg` apres pertes, ce qui preserve le choc en cours. **Raccordement present**, pas valide en integration.
5. **Aleatoire** : selection reelle des victimes utilise `aleatoire` fourni, mais le cote adverse passe par `supprimer_unites(... random ...)` avec RNG global ; les predictions clonent un autre generateur. **Risque de divergence / reproductibilite non demontrée** ; ne pas inventer d'equivalence statistique. Un scenario de reproduction deterministe en integration est necessaire.
6. **Activation des effets en bataille reelle : BUG D'INTEGRATION CERTAIN.** `combat_entre_generaux` entre dans `with ordres_pipeline.duel(...)` et `with ordres_pipeline.participations_duel(...)`, alors que le parcours `enchainer_avants_muraille -> engager_avant_muraille -> combat_bloc` ne les ouvre pas. `ordres_pipeline.effet(general, id)` renvoie False sans `_duel`, donc Herisson et effets dependants du contexte peuvent etre absents en Grande Muraille, malgre le calcul correct des contributions. `ordres_pipeline.duel` fonctionne sur deux generaux seulement, tandis que Muraille regroupe potentiellement plusieurs contributeurs : **ne pas corriger en ouvrant simplement le contexte du representant**, car cela exclurait les autres generaux et fausserait les droits PC/ordres. Examiner integration collective des effets/commandements et arbitrages des intentions sur plusieurs generaux.

**Statut** : audit et identification, AUCUNE correction de combat apportee dans cette entree. Les six points ne peuvent pas etre marques « valides » sans tests d'integration. Faire resoudre le contexte multi-generaux et la reproductibilite RNG avant de declarer Muraille terminee. Cas necessaires : deux piquiers (un seul avec Herisson), adversaire cavalier et distance, apres perte du QG, ordre des contributeurs inverse, graine identique, previsions sans consommation du RNG reel.

## Passe d'integration groupee Muraille — 29 octobre 2026

**Correctif certain publie** : `e03d788` (`python/combats.py`) permet a `supprimer_unites` de recevoir un RNG optionnel, et fait utiliser le RNG du choc collectif egalement pour les pertes du bloc Avant adverse. Auparavant les pertes Muraille consommaient `aleatoire` et les pertes adverses `random` global, empechant de reproduire la resolution du choc avec une seule graine. Hors Muraille, l'absence de parametre conserve le RNG global historique et la formule de moral est inchangee. Test de regression `6f367fe` (`test_ordres_calculs_v2.py`) controle la transmission de la meme instance RNG aux pertes adverses.

**Audit des six points** : bonus Herisson par contributeur, calcul collectif et faiblesse distance couverts par fonctions et tests existants ; transmission QG entre chocs raccordee ; RNG commun des victimes corrige comme ci-dessus. **Reste un blocage d'integration majeur** : `enchainer_avants_muraille -> engager_avant_muraille` ne cree pas de contexte `ordres_pipeline.duel`, alors que `ordres_pipeline.effet()` ne voit les ordres actifs que dans un tel contexte. La primitive existante `duel(general_1, general_2)` gere deux generals : l'appliquer successivement ou exclusivement au representant risquerait de faire confronter plusieurs fois les ordres adverses, de perdre les bonus des autres contributeurs et de fausser les PC. Ne pas introduire de regle implicite ; concevoir une activation territoriale ou multi-generaux autorisant chaque effet individuel exactement une fois dans son propre contexte, avec arbitrage explicite des ordres adverses, puis faire tester par Codex.

**Tests** : test nouveau publie, **non execute** dans la presente intervention. Validation de la suite complete et d'un choc multi-generaux avec Herisson actif toujours necessaire. Ne pas marquer Grande Muraille terminee a ce stade.

## Blocage precis du raccordement des ordres en Muraille (29 octobre 2026)

L'API existante `ordres_pipeline.duel(g1,g2)` compare un donneur par camp et categorie (globale / duel / individuelle), via `confronter_intentions`, PC officiels puis `commandement.confronter_donneurs`. Elle peuple `_duel` avec les effets retenus uniquement pour ces deux identites. Une formation Grande Muraille peut regrouper G1 et G2 face a un seul adversaire, sans mecanisme defini pour arbitrer les demandes des deux generaux allies face aux memes ordres adverses. Injecter tous les effets sans arbitrage contournerait les PC ; appeler `duel` successivement contre l'adversaire comparerait sa demande plusieurs fois. **Arbitrage de gameplay requis** : comparer individuellement chaque general contributeur contre le meme adversaire (ordres adverses reexamines par contribution) ou definir une confrontation collective de donneurs (choix du PC et regle de repartition des effets). Une fois tranche, implementer un contexte collectif avec `ContextVar` et controle d'identite, tests de deux piquiers dont un seul avec Herisson, et retour au contexte precedent apres choc. Aucune activation fictive ou modification de formule n'a ete publiee a cette etape.

## Rappel de hierarchie du commandement Muraille — 29 octobre 2026

Le concepteur rappelle que les categories **ont deja leurs autorites definies** : (1) ordres globaux confrontes entre generaux en chef / QG avec le calcul de PC qui prend en compte les autres generaux ; (2) ordres de duel confrontes entre generaux dominants des deux camps, **une seule fois**, sans dupliquer le duel adverse pour chaque contributeur ; (3) ordres individuels propres a chaque general, dont Herisson ne concerne que ses propres piquiers. Le general representant du bloc collectif pour le tirage des victimes n'est pas necessairement le donneur des ordres. L'alternative precedente « confrontations 1v1 pour chaque contributeur contre le meme adverse » est invalidee : ne plus demander cet arbitrage. Adapter le contexte d'effets a ces autorites existantes, sans modifier les formules de PC.

## Décision architecture — conserver le calcul dynamique des PC (29 octobre 2026)

Le concepteur confirme explicitement : **ne pas figer les PC au début de la bataille territoriale**. Les recalculer au moment de chaque confrontation est volontaire et préserve les futurs effets susceptibles de modifier le commandement. Limiter l'intervention actuelle à Grande Muraille : réutiliser la confrontation existante des ordres globaux (QG), des ordres de duel (généraux dominants, une seule confrontation), puis appliquer les effets individuels propres à chaque général du bloc collectif. Ne pas réécrire `commandement.py`, ne pas attribuer tous les bonus au représentant des victimes, ne pas confronter plusieurs fois les mêmes ordres adverses. Des tests sur Raspberry Pi seront exécutés par le concepteur ; fournir commandes et scénarios ciblés avant de déclarer l'intégration terminée.

**Point de prudence** : le raccordement Python multi-participants n'est pas encore implémenté ; ne pas considérer la présence de `combat_bloc(contributions_1=...)` comme une preuve que les effets sont actifs (`ordres_pipeline.effet` requiert `_duel`). Préserver le comportement des duels existants lors de l'implémentation.

## Premier raccordement des effets Grande Muraille — 29 octobre 2026

- `1eaaa4c` (`python/ordres_pipeline.py`) ajoute `effets_muraille(dominant, adversaire, contributeurs)` : reutilise une fois `duel(dominant, adversaire)` pour les autorites globales et duel, puis prepare exclusivement les demandes individuelles officielles des contributeurs supplementaires, avec validation des droits de reception et PC au moment du choc. Le contexte temporaire `_duel` est restaure a la sortie.
- `6958266` (`python/combats.py`) transmet le dominant territorial a la resolution de Muraille et active ce contexte pendant la selection et l'engagement ; les appels de test sans dominant explicite gardent la voie historique. Calcul dynamique des PC conserve.

**LIMITES A VERIFIER IMPERATIVEMENT** : les demandes individuelles supplementaires sont evaluees sans nouvel adversaire individuel (`confronter_intentions(demande, None, 'individuelle', pc, 0)`) afin de ne pas arbitrer plusieurs fois les memes ordres adverses. Valider cette interpretation des ordres individuels et les cas d'annulation/counter-ordres ; les effets speciaux (Rafale, Gros Poisson, Cruelle, etc.) ont des hooks de duel hors choc qui ne sont pas encore raccordes par cette seule ouverture du contexte. En cas de divergence ne pas considerer la correction comme terminee. Le nouveau contexte n'a PAS ete execute sur le Raspberry Pi ni teste avec un vrai duel au cours de cette intervention. Tests Raspberry : d'abord `PYTHONPATH=python:.dev/tests python3 -B -m unittest -q test_ordres_calculs_v2 test_ordres_effets_v2` puis tests d'integration d'une Muraille avec un seul piquier Herisson et adversaire cavalier / archers ; effectuer suite exhaustive avant merge.

## Passe speciale Muraille : ordre des effets et rapports (29 octobre 2026)

**Correction certaine publiee** : lors de la conversion d'un choc Grande Muraille vers les colonnes camp1/camp2, le rapport inversait `bloc/type/initial/final` mais oubliait les nouveaux `combattants_1/2` (effectifs aptes avant moral). `bf8a274` ajoute cette orientation, `20c0713` extrait `orienter_choc_muraille(choc, inverser=...)` pour eviter la mutation du choc source, et `b0f5ce6` ajoute un test de regression pour Muraille du camp 2 avec des survivants moraux. Aucun test execute dans cette passe (validation Raspberry Pi reportee a la fin de tous les ordres).

**Audit des effets** (a ne PAS confondre avec une validation de bout en bout) :
- Herisson : calcul `combat_bloc` par general et contexte `effets_muraille` present. Le moral Discours de la mort est lu par `ordres_pipeline.moral`, mais les reductions Cruelle et autres effets qui dependent des sources du duel ne sont pas integres de maniere generale a tous les participants ; controle de vrais combats requis.
- Rafale : `ordres_pipeline.rafales` est appele par `combat_entre_generaux` avant son choc ordinaire. Le chemin collectif Muraille `enchainer_avants_muraille -> engager_avant_muraille` ne l'appelle pas ; si `combat_entre_generaux` suit Muraille, Rafale se declencherait APRES les chocs collectifs, au lieu de la priorite pre-choc normale. **Probleme d'ordonnancement a regler dans le pilote territorial, sans doubler les tirs**.
- Gros Poisson : `ordres_pipeline.participations_duel` realise les prets via une vue temporaire ; cette vue n'est pas ouverte pour `engager_avant_muraille`, donc aucun pret ne peut etre suppose integre au choc collectif. Interactions des exclusions QG/reserve et des groupes a verifier avant de raccorder.
- Choca-fuite : `fuir_apres_choc` s'execute dans `_combat_entre_generaux` mais pas apres chaque choc collectif. Ne pas provoquer de fuite illegale ou double sans verifier la priorite et le declenchement.
- Propagafion : `unites.apres_confrontation` exige `unites.duel` (contexte temporaire distinct), present dans `combat_entre_generaux`, absent du choc collectif. Ce mecanisme est actuellement refuse explicitement par `engager_avant_muraille` pour les blocs speciaux engages ; cela evite une resolution silencieusement fausse, mais ne constitue pas un raccordement.
- Le pilote territorial recolle ensuite le rapport de Muraille au resultat du duel ordinaire ; ses autres effets d'avant-choc peuvent donc intervenir trop tard, ce qui rend un correctif local dans `engager_avant_muraille` insuffisant.

**Pour la suite** : ne pas declarer Grande Muraille terminee ; preparer l'ordonnancement pre-choc unique au niveau territorial (Rafale, Bouclier, autres priorites), ensuite les participations temporaires et les post-effets, en reutilisant les composants existants. Ne pas inventer de nouvelles priorites de gameplay. Ecrire des tests simulant un tour territorial Muraille + Rafale / Gros Poisson et l'ordre d'execution ; execution finale a la campagne Raspberry Pi.

## Suite de Grande Muraille — cycle d'unites (29 octobre 2026)

Commit `fca748b` : `enchainer_avants_muraille` ouvre `unites.duel(choisi, general_adverse)` autour de chaque `engager(choisi)` dans la voie territoriale (`dominant_allie` fourni). L'objectif est que les hooks `unites.apres_confrontation` executes par `engager_avant_muraille` disposent du meme contexte temporaire que dans un duel normal. La voie isolee historique (sans `dominant_allie`, notamment tests injectes) reste inchangee. Cette modification **ne leve pas** le refus des capacites collectives speciales (propagation, bouclier, soutiens) et **ne resout pas encore** la priorite de Rafale ni les prets Gros Poisson. Aucun test execute ; validation finale reservee a la campagne de tous les ordres sur Raspberry Pi. Verifier notamment que l'ouverture de `unites.duel` ne double pas les hooks et que chaque choc suivant dispose d'un contexte neuf.

## Audit d'integration des priorites — limites confirmees

La sequence `combat_entre_generaux` est `duel -> participations_duel -> unites.duel -> rafales -> _combat_entre_generaux`, puis `bouclier_vivant.resoudre_priorite` dans `_combat_entre_generaux`. Le pilote de Muraille execute actuellement `enchainer_avants_muraille` **avant** `combat_entre_generaux` et ne prepare ni `participations_duel` ni `rafales` avant la premiere Muraille. Ne pas deplacer arbitrairement ces priorites sans tenir compte de la vue `soldats.VueParticipants` des prets. La simulation `simuler_avants_muraille` refuse deja les boucliers et la propagation. Le pilote refuse encore deux Murailles (`NotImplementedError`). Aucune regle specifique Muraille contre Muraille n'est attestee dans ce travail : demander la regle au concepteur avant implementation. Aucun test sur Raspberry avant la campagne finale prevue.

## Décision finale : Grande Muraille 1019 archivée et désactivée (29 octobre 2026)

**Statut canonique : ABANDON DE L'INTÉGRATION V2.0. NE PAS RÉACTIVER, NE PAS TERMINER ET NE PAS TESTER COMME FONCTIONNALITÉ ACTIVE.** Les règles documentées et le prototype sont conservés pour une éventuelle reprise future, sans échéance. Les notes précédentes décrivant un travail « à terminer » sur Muraille sont historiques et **ne sont plus des instructions pour Codex**.

- Catalogue `python/catalogues.py` : l'entrée 1019, jeton `1-9`, catégorie `globale`, était **déjà** à `disponible=False`; elle reste réservée avec son identifiant. Ne pas supprimer ni réattribuer cet ID.
- `python/ordres_pipeline.py` : 1019 supprimé de `formations_territoriales` pour empêcher la formation de devenir active dans le processus normal (commit `96bb826`).
- `python/combats.py` : le point d'entrée de la Muraille territoriale vérifie explicitement `catalogues.ORDRES[1019]['disponible']` avant toute préparation (commit `d1c09c7`). Les fonctions expérimentales conservées ne sont donc pas atteintes par le moteur normal.
- Test ajouté `test_muraille_1019_desactivee_et_identifiant_conserve` (`09ea586`) pour vérifier que l'ID, son jeton et sa catégorie restent réservés et désactivés.
- **Codex** : à la campagne finale de régression, vérifier que la présence de jetons historiques `1-9` n'active ni formation, ni bonus, ni simulation et que les autres ordres restent inchangés. Ne pas « corriger » les limites fonctionnelles de Muraille, ne pas inclure ses anciennes recherches dans les objectifs actifs ; traiter une réactivation seulement sur demande explicite du concepteur.
- Les anciens tests du prototype peuvent rester dans `.dev/tests` comme tests de composants isolés ; ils ne valent pas validation d'une fonctionnalité active. Aucun test Raspberry Pi demandé avant la fin de tous les ordres.

**Portée :** suppression des chemins d'activation normale, conservation du code expérimental pour éviter une suppression massive risquée. Aucun changement aux règles des autres ordres ni aux PC dynamiques.

## Spora Adicte 1018 — raccordement ciblé (30 octobre 2026)

- `python/bouclier_vivant.py`, commit `575a57a` : au déclenchement de Spore, applique `ordres_calculs_v2.conversions_spore(1, bonus_spora_adicte=effet(general_zombie,1018), confinement=effet(adversaire,1013))`. Chaque conversion passe par `convertir_spore`, sans duplication de l'algorithme de mutation, avec une preuve d'événement distincte pour la conversion supplémentaire. Les rapports indiquent le nombre réel de conversions, même sans cible supplémentaire.
- `python/catalogues.py`, commit `157d0ed` : 1018 `disponible=True`, catégorie globale et acquisition requise inchangées.
- `.dev/tests/test_ordres_calculs_v2.py`, commit `3c9c922` : test de disponibilité, bonus +1 et neutralisation par Confinement.
- **À valider par Codex à la fin des ordres** : conflit Spora Adicte/Confinement par PC globaux, déclenchement seulement pour un général qui reçoit effectivement l'ordre, victime unique restante, zéro victime restante, conversion double avec identité et preuve distinctes, réexécution/reprise interrompue sans doublon, cohérence du rapport et des registres. Aucun test Raspberry Pi exécuté au cours de cette intégration.
- Grande Muraille 1019 demeure abandonnée, archivée et désactivée ; les anciennes notes de Muraille ne sont pas une liste de tâches active.

## Charge suicidaire 1020 — préparation, pas d'activation (30 octobre 2026)

Calculs déjà présents dans `ordres_calculs_v2.py` : `probabilite_charge_suicidaire(pertes_du_duel)` (1 % par 4 unités perdues dans le duel), `tirages_charges_suicidaires` (tirages indépendants, sans mutation). Tests de bornes et de deux tirages ajoutés (`194c831`). Le catalogue reste `disponible=False`, `progression=False`.

**Blocage d'intégration à traiter avant l'activation** : la formule dit « mort adverse », mais le moteur ordinaire ne fournit pas une primitive spécialisée pour tuer un général encore doté de soldats. `generaux.supprimer_general_si_vide` ne gère que les généraux sans unités ; la détourner serait incorrect. Il faut retrouver la règle officielle définissant l'effet de la mort du général sur les soldats restants, son emplacement, les retraites et le vainqueur, puis réutiliser un mécanisme officiel de suppression (ou créer ce mécanisme à part avec tests). Ne pas détruire arbitrairement le dossier du général ni déclarer l'ordre opérationnel avant ce raccordement. Campagne Raspberry Pi et revue Codex à la fin de tous les ordres.

## Charge suicidaire 1020 — règle confirmée et intégration (30 octobre 2026)

**Décision explicite du concepteur :** si Charge suicidaire réussit, le général adverse **et tous les soldats qui lui appartiennent** sont définitivement éliminés, même si ces soldats ont survécu au duel. Aucun héritage ni transfert à un autre général.

- `python/generaux.py`, `824b1b3` : `detruire_general_et_armee` marque les soldats connus détruits dans le registre, notifie la mort du général pour la morgue, retire son dossier et son identité des positions. Ne modifie pas `supprimer_general_si_vide`.
- `python/combats.py`, `6a0caa0` : relève les activations individuelles dans le contexte officiel, puis applique les tirages existants après restitution des prêts temporaires. Les deux camps tirent indépendamment sur le bilan des pertes de leur duel ; réussites appliquées aux généraux adverses, bilan final recalculé.
- `python/catalogues.py`, `7717693` : 1020 activé avec progression/acquisition requise ; `.dev/tests/test_ordres_calculs_v2.py`, `3646864` : test d'état du catalogue, en complément des tests de formule déjà écrits.
- **Codex** : vérifier impérativement scénario avec général survivant mais armée anéantie par charge, deux charges simultanées, victoire source et source détruite pendant le duel, cible déjà détruite, soldat prêté par Gros Poisson (le prêteur conserve ses soldats), provenance des pertes (duel uniquement), positions, morgue, registres d'UUID, et suivi de bataille. Les tests d'intégration sur le vrai moteur restent non exécutés et sont réservés à la campagne finale de tous les ordres. Si une incompatibilité apparaît, ne pas changer la règle de destruction totale confirmée.
- Grande Muraille 1019 reste désactivée et hors objectif de Codex.

## Retrait tactique 1021 — audit et préparation (30 octobre 2026)

**Règles déjà convenues** : ordre global / contre-ordre ; `Retrait tactique + On mélange` incompatibles ; `Retrait tactique + Réserve stratégique` compatibles, chacun garde son effet ; avec `QG nomade` compatible, le général en retrait passe immédiatement avant le QG. Le retrait concerne le général engagé après la première manche complète des blocs ; le mouvement doit suivre la règle de repli territoriale, pas une suppression du général ni une restauration des soldats.

**État moteur** : `commandement.sequence_formation(...,position_retrait=...)` sait effectuer le placement logique, mais `ordres_pipeline.generaux_en_formation` ne lui transmet pas de `position_retrait`. Aucun branchement officiel et validé du déplacement territorial n'a été identifié dans cette intervention. `1021` reste volontairement `disponible=False` et `progression=False` pour éviter un ordre partiellement actif. Tests ciblés de compatibilité et séquence ajoutés dans `.dev/tests/test_ordres_calculs_v2.py` (`3ed6ea1`), **non exécutés**.

**Avant activation** : raccorder l'identification du général concerné, l'issue et la fin de manche, le mouvement réel vers le territoire de repli selon les règles validées, puis l'actualisation des forces / positions / rapports, et les interactions de succession des combats. Ne pas inventer une destination alternative ni les conditions d'un repli impossible. Codex exécutera les tests en fin de campagne, après achèvement des ordres.

## Retrait tactique 1021 — correction de la règle et raccordement (30 octobre 2026)

**CORRECTION PRIORITAIRE des notes précédentes :** Retrait tactique ne déplace PAS le général vers le territoire spécial `repli`, n'applique AUCUNE sanction ni attente. La règle confirmée dans la conception antérieure est une **rotation logique : après son premier affrontement, le premier général engagé passe à la dernière position de la séquence de combat de son camp**. Le classement existant `commandement.sequence_formation` place ce général juste avant le QG lorsque QG nomade est actif. Toute note précédente demandant de développer un déplacement territorial pour 1021 est **obsolète et erronée**.

- `python/ordres_pipeline.py` commit `2ba1e8e` : contexte de bataille `retraits_tactiques`, `marquer_retrait_tactique`, transmission de `position_retrait` à `sequence_formation`, sans mutation de dossiers ou de positions persistantes.
- `python/combats.py` commit `1979edc` : mémorisation après le combat rangé de chaque camp, une fois seulement, si le général survit. Les rounds suivants relisent la formation. La voie frontale n'est pas modifiée.
- `python/catalogues.py` commit `5f23802` : 1021 activé, contre-ordre global, acquisition requise.
- `.dev/tests/test_ordres_calculs_v2.py` commit `81083f9` : disponibilité et mémorisation unique, en plus des tests de compatibilité et séquence du commit `3ed6ea1`.

**Validation Codex à la fin de tous les ordres :** conflit On mélange, compatibilité QG nomade, PC du contre-ordre, sélection du premier général par camp, général détruit au premier duel, succession de plusieurs affrontements, maintien des positions d'origine et absence de mouvement vers le repli. Vérifier en particulier si l'activation nécessite une confrontation en début de bataille plutôt que de dépendre du recalcul territorial à chaque round. Aucun test Raspberry Pi exécuté.

## Pour l'honneur 1022 — activation cadrée par la fiche originale (30 octobre 2026)

**Source de la règle :** document utilisateur `mythodea-ordres.json` : ordre global avant le combat territorial ; **uniquement le camp DEF en OFF/DEF**, supprime pendant le choc initial les **faiblesses des unités de tous les généraux du clan défenseur**, sans neutraliser leurs forces naturelles. Aucun cumul avec les autres ordres sauf combinaison explicitement autorisée (la matrice `compatibilite_formations` marque actuellement les paires impliquant 1022 incompatibles).

- `ordres_pipeline.py` `08d7faa` : contexte temporaire identifiant le défenseur OFF/DEF et la phase choc initial ; `honneur_protege(general)` vérifie le camp défensif et la réception effective de 1022 dans les décisions du duel officiel.
- `unites.py` `9d6533c` : dans `avantage`, ignore seulement les faiblesses de l'unité défensive protégée ; ne retire pas les forces explicites de l'attaquant, ni les autres règles d'avantage.
- `combats.py` `6fc5367` : entoure le choc initial de son contexte ; `resoudre_combat_off_def` fournit le camp défenseur pendant toute la résolution territoriale. La manœuvre reste non protégée.
- `catalogues.py` `ac6712c` : ordre 1022 activé avec acquisition requise.
- `.dev/tests/test_ordres_calculs_v2.py` `9bf140a`, `675a002` : tests unitaires de neutralisation d'une faiblesse, maintien d'une force naturelle, disponibilité et incompatibilités de formations.

**Vérifications Codex à la campagne finale :** cas OFF/DEF et OFF/OFF, sens d'attaque inversé, plusieurs généraux du camp DEF, QG actif et QG détruit, ordre annulé par opposition de PC globaux, exclusion du malus pendant les manœuvres, interaction avec les autres ordres via la matrice, absence d'impact sur les zombies interdits de réception. Tests publiés non exécutés sur le Raspberry Pi. Ne pas réactiver Muraille 1019.

## Ralliement 1023 — audit de règle et tests préparatoires (30 octobre 2026)

**Ne pas activer avant raccordement complet des identités.** La fiche d'origine `mythodea-ordres.json` décrit un ordre global pour la DEF en OFF/DEF, appliqué au général en chef au QG actif : 20 % de renforts compatibles avec les blocs déjà possédés, potentiellement au-delà de la limite de 20, **temporaires**, seuls les soldats propres subsistant en cas de victoire. Les décisions antérieures précisent aussi : source = soldats morts réanimés, UUID / expérience / blessures conservés, bénéficiaire allié suivant, retour à l'origine si elle existe. Ces points nécessitent une lecture cohérente des phases et une implémentation sans duplication des unités ; ne pas assimiler ces morts réanimés à des soldats créés neufs.

`ordres_calculs_v2.renforts_ralliement` calcule déjà `floor(pertes / 5)` **par type éligible**. Tests ajoutés `f2726d3` : arrondi par type, exclusion des types absents chez le bénéficiaire, pertes nulles. Ces tests n'ont pas été exécutés.

**Blocage concret** : les règles documentaires ne fixent pas encore de manière non ambiguë le moment de prélèvement et de retour des soldats morts en regard du recrutement avant bataille ; elles mêlent QG bénéficiaire et général allié suivant. Ne PAS choisir arbitrairement le propriétaire à chaque étape, ne pas déplacer de dossiers historiques sans procédure de restauration, ne pas renseigner `disponible=True` avant le raccordement. Attendre clarification uniquement si le cas ne peut être résolu en reprenant les décisions antérieures. Ne pas demander de tests Raspberry avant la campagne finale des ordres. Grande Muraille 1019 reste exclue.

## Ralliement 1023 — décision de permanence et régulation (30 octobre 2026)

**Nouvelle décision explicite du concepteur (prioritaire sur les notes antérieures)** : les soldats acquis par Ralliement **restent définitivement** au général en chef / QG. Il n'existe donc plus de disparition automatique des renforts à la fin du combat ni de restitution au propriétaire initial. À la fin du combat territorial, si le général dépasse sa capacité autorisée, retirer l'excédent **aléatoirement en donnant priorité aux soldats sans expérience**. Ne pas déduire du mot « aléatoire » une priorité par bloc.

- `generaux.reguler_surnombre_ralliement(general, aleatoire=None)` ajouté dans `cf785da` : lit la capacité via progression, décompte les places d'unités, détermine l'expérience depuis le registre privé des UUID, tire un ordre aléatoire à priorité égale, marque chaque soldat retiré comme détruit puis supprime son dossier et consigne le résultat. Ne change PAS `verifier_limite_unites_general` utilisée ailleurs, dont la logique historique arrière→avant ne convient pas ici.
- **À raccorder avant activation** : sélection exacte des soldats morts éligibles, attribution définitive au QG et transfert officiel avec préservation UUID, batailles, blessures ; appel de la régulation **une seule fois après la fin du combat territorial** et avant toute vérification normale de capacité qui supprimerait arbitrairement des unités. Garantir absence de double retrait / double expérience sur reprise, ne pas supposer que les soldats transférés sont des soldats neufs.
- `1023` reste désactivé tant que ces transitions ne sont pas intégrées. Codex validera à la fin les cas de capacité, zéro expérience, vétérans, unités à plusieurs places, provenance, morts / survivants et non-duplication.

## Ralliement 1023 — règle finale et raccordement (30 octobre 2026)

**La présente section remplace les passages contradictoires antérieurs sur Ralliement.** Le concepteur a validé **20 % de chance individuellement par soldat mort** (après résolution des blessures/sauvetages), sous réserve que son type corresponde à un bloc du QG défenseur. Le succès signifie transfert **définitif**, UUID/XP/blessures conservés, sans participation au duel ayant causé la mort. Plus de réserve de dossiers et plus de quota déterministe floor(pertes/5) pour l'effet réel. Le général en chef garde les soldats et la fin du territoire applique la régulation, priorité aux soldats sans expérience puis tirage aléatoire.

Raccordements : `ordres_pipeline.py` (`0a50fea`, `96e32d2`, `9816885`) prépare le QG pour OFF/DEF, valide l'activation effective du 1023 par les décisions de duel et réserve/transfère les morts admissibles après le duel ; `soldats.py` (`560a81d`) intercepte les pertes *après* les sauvetages et les exclut du bloc courant ; `combats.py` (`2f9108e`) active le contexte par duel, effectue le transfert après la confrontation, régule à la sortie territoriale ; `catalogues.py` (`865cf83`) active 1023. `generaux.reguler_surnombre_ralliement` (`cf785da`) applique le tri sans expérience / tirage aléatoire et marque les UUID détruits en surnombre.

**Audit Codex impératif en fin de campagne avant déploiement** : ordre global effectivement acquis et gagnant en PC, QG détruit, blocs mixtes, soldat sans UUID, déplacements entre FS de génération privée, reprise et non-duplication, cohérence de la capture et du registre, arrivée sur plusieurs duels, absence de participation au duel mortel, logique de morgue, suppression de capacité après bataille uniquement, interaction avec la disparition du dernier général et `supprimer_general_si_vide`, cas de batailles OFF/OFF, cumul des pertes par bloc et des contre-ordres. Le calcul historique `renforts_ralliement` est désormais **obsolète pour l'effet 1023** et n'est pas appelé. Aucun test de combat / Raspberry Pi exécuté ici.
