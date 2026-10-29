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
