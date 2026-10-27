# Fatigue individuelle et suite de Gros_poisson

Analyse du 27 octobre 2026, après la réponse du propriétaire : priorité souhaitée
à l'appariement maximal sans réutiliser un adversaire fatigué, somme des valeurs
individuelles puis résistance moyenne. **Non implémenté : cette méthode contredit
la conservation demandée de tous les cas homogènes.** Le moteur refuse encore un
bloc temporaire de fatigue hétérogène avant pertes, rapports et tirages du duel.

## Principes acquis et calcul historique

La base dépend du type et de la position. Les facteurs collectifs existants de
valeur (formation, avantages naturels, Hérisson et dépendances d'ordres) sont
calculés avant l'avantage individuel de fatigue. À type égal, le frais reçoit
×2 contre le fatigué, jamais l'inverse. À types différents, les avantages naturels
restent inchangés. Les capacités spéciales gardent leurs règles.

`valeur_base_bloc()` et `multiplicateur()` fournissent les valeurs `cA`, `cB`
avant fatigue. `combat_bloc()` utilise ensuite la même valeur effective pour
la puissance et la résistance : pertes simultanées, division entière unique,
plafond à l'effectif initial. Les sauvetages par moral et limites de blessures
restent traités ensuite par `supprimer_unites()` et `soldats.pertes()` ; le moral
ne devient pas un nouveau multiplicateur de puissance.

## Méthode demandée et calcul exact

Notations : `nA`, `nB` sont les effectifs ; `tA`, `tB` les nombres de fatigués ;
`fA = nA - tA`, `fB = nB - tB` les frais. Les blocs vides gardent leur retour
historique sans division. Pour des types différents, aucun bonus de fatigue.

À type égal, le nombre de frais avantagés dans chaque camp est le minimum entre
ses frais et les fatigués adverses. Un fatigué ne donne aucun bonus à son camp :

```text
bA = min(fA, tB)                 bB = min(fB, tA)
vA = cA * (nA + bA) / nA         vB = cB * (nB + bB) / nB
puissance_A = nA * vA             puissance_B = nB * vB
pertes_A = min(nA, floor(puissance_B / vA))
pertes_B = min(nB, floor(puissance_A / vB))
```

La résistance est la moyenne des valeurs individuelles après bonus. Ces calculs
ont été exécutés avec `Fraction`, sans arrondi intermédiaire ni tirage. Le plancher
s'applique une seule fois par total de pertes, puis le plafond d'effectif.
La sélection réelle des victimes resterait la sélection commune par UUID.

## Exemples avant moral

Même type, valeur de base 5, mêmes bonus collectifs. Chaque résultat indique les
**survivants A / B d'un seul affrontement**, pas ceux du duel complet.

| Effectifs A / B | Fatigués A / B | Puissances A / B | Résistances A / B | Survivants A / B |
| --- | --- | --- | --- | --- |
| 3 / 3 | 0 / 0 | 15 / 15 | 5 / 5 | 0 / 0 |
| 3 / 3 | 3 / 3 | 15 / 15 | 5 / 5 | 0 / 0 |
| 3 / 3 | 0 / 3 | 30 / 15 | 10 / 5 | 2 / 0 |
| 3 / 3 | 0 / 1 | 20 / 15 | 20/3 / 5 | 1 / 0 |
| 3 / 3 | 1 / 2 | 25 / 20 | 25/3 / 20/3 | 1 / 0 |
| 5 / 5 | 0 / 1 | 30 / 25 | 6 / 5 | 1 / 0 |
| 5 / 5 | 0 / 3 | 40 / 25 | 8 / 5 | 2 / 0 |
| 5 / 5 | 2 / 3 | 40 / 35 | 8 / 7 | 1 / 0 |
| 5 / 5 | 2 / 2 | 35 / 35 | 7 / 7 | 0 / 0 |
| 6 / 3 | 0 / 3 | 45 / 15 | 15/2 / 5 | 4 / 0 |

**5 frais contre 4 frais + 1 fatigué :** un seul frais A reçoit ×2. Puissances
`4×5 + 1×10 = 30` et `5×5 = 25`. Résistances 6 et 5. Pertes A :
`floor(25/6) = 4` ; pertes B : `min(5, floor(30/5)) = 5`. Résultat **1 / 0**.

**3 frais + 2 fatigués contre 2 frais + 3 fatigués :** trois frais A et deux frais
B reçoivent ×2. Puissances `3×10 + 2×5 = 40` et `2×10 + 3×5 = 35`. Résistances
8 et 7. Pertes `floor(35/8) = 4` et `floor(40/7) = 5`. Résultat **1 / 0**.
Avec 3 frais + 2 fatigués de chaque côté : deux frais avantagés par camp,
puissances 35 et résistances 7 ; cinq pertes de chaque côté, donc **0 / 0**.

## Incompatibilité avec les blocs homogènes

La méthode conserve frais/frais, fatigués/fatigués et frais/fatigués de même
effectif. Elle conserve les avantages naturels en laissant les types différents
sur le chemin historique. Elle échoue cependant sur certains effectifs inégaux.

Sur la dernière ligne, seuls trois des six frais reçoivent ×2 : `vA = 7,5`,
`vB = 5`, donc deux pertes A et **4 / 0** survivants. L'appel réel à
`combat_bloc()` donne `vA = 10` pour les six frais, une perte A et **5 / 0**.
Une exception pour les blocs homogènes constituerait un mécanisme supplémentaire,
non autorisé par la réponse. Aucun correctif ni activation n'est donc ajouté.
Mythodea-web n'a été ni inspecté ni modifié.

**Décision encore requise :** laquelle des deux contraintes doit primer,
l'appariement maximal sans réutilisation ou l'équivalence historique de tous
les blocs homogènes ? Leur maintien simultané est impossible avec cette formule.

## Préparation technique et obstacles de Gros_poisson

`VueParticipants.fatigues_individuelles()` fournit un booléen par chemin de la
sélection vivante, dans le même ordre que `infos['unites']`. Le groupe résout
l'origine via l'UUID et `GroupeTemporaire.fatigues_origine()`. Après une perte,
le lecteur relit le bloc ; les morts quittent le relevé. `fatigue()` réutilise
ce lecteur mais continue à refuser le mélange. Pas de nouveau registre, dossier
de fatigue ou mutation de `fatigue_generaux.txt` due au prêt.

| Interaction | Fonctions à réutiliser | Décision ou adaptation restante |
| --- | --- | --- |
| Fusions partielles et retour | `selections_gros_poisson`, `VueParticipants`, `bilan` | Raccorder QG, positions, confrontation, motif sans homologue et fin du prêt ; aucune nouvelle fusion à inventer. |
| Bonus de composition | `moral_des_pertes`, `unites.moral_bloc`, `caracteristiques_armee` | Armée physique du bénéficiaire ou sélection effectivement engagée ? Les Orcs et chevaliers modifient le moral ; les deux références peuvent différer. |
| Cavalerie lourde | `valeur_base_bloc` | Le seuil Avant de 15 se mesure-t-il dans le bloc fusionné ou à l'origine ? Par exemple 10 + 5 déclenchent le bonus uniquement dans le premier cas. Recalcul commun après chaque perte. |
| Effets d'ordres | `ordres_pipeline.duel`, `multiplicateur`, `rafales` | Conserver donneur et priorités. Cruelle utilise l'armée du donneur figée au début du duel, pas automatiquement l'effectif fusionné. |
| Soutiens | `generaux.lire_blocs_general`, `soldats.pertes`, `rafales` | Fixer s'ils suivent le bloc prêté et quelle destruction emporte le soutien : bloc physique d'origine ou bloc engagé. La lecture seule distingue déjà combattants, soutiens et boucliers. |
| Spore adverse | `choisir_spore`, `bloc_destination_spore`, `convertir_spore` | Spore change normalement type, propriétaire et destination, conserve UUID/XP et remet les blessures à zéro. Préciser le sort du prêté converti par rapport au retour à l'origine ; adapter ensuite le suivi à cet événement officiel sans affaiblir l'authentification. |

La restriction commune Zombie reste applicable aux deux rôles. Elle n'empêche
pas un adversaire d'utiliser Spore contre un prêté admissible. Les mêmes rôles
désignés deux fois restent refusés. `verifier_duel()` maintient ses garde-fous
pour capacités/compositions non définies ; `combat_entre_generaux()` refuse aussi
Choca_fuite avec groupe temporaire tant que le cycle du prêt et de la retraite
n'est pas raccordé. Ces limitations sont explicites, pas des effets disponibles.

L'activation reste conditionnée aux décisions ci-dessus, au raccordement et aux
tests des capacités, aux identités/permissions/publication et à la non-régression
du combat ordinaire. Aucun chantier Muraille, Ralliement ou Dernière charge n'est
engagé par cette préparation.
