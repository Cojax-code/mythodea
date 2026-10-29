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

## 5. Résultats Codex — à compléter après exécution

- **Commit / date de validation :** à renseigner
- **Compilation :** non vérifiée
- **Tests ciblés :** non exécutés ici
- **Suite complète :** non exécutée ici
- **Échecs / régressions :** inconnus avant validation
- **Corrections réalisées par Codex :** aucune consignée
- **Décisions de gameplay en attente :** à préciser si rencontrées
- **Statut final :** EN ATTENTE DE VALIDATION

**Prochaine étape recommandée :** confier ce lot à Codex et stabiliser la V2.0 avant d'envisager d'autres refontes.
