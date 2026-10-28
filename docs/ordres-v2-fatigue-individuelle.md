# Fatigue individuelle et suite de Gros_poisson

Règle officielle du 27 octobre 2026, intégrée dans le moteur commun. Elle remplace
l'ancien appariement maximal : priorité aux paires fatigué/fatigué et complément
proportionnel pour les seuls frais sans adversaire direct. Aucun nouvel état
persistant ni tirage pour former les paires.

## Calcul commun exact

La base dépend du type et de la position. `valeur_base_bloc()` et
`multiplicateur()` appliquent les facteurs collectifs existants avant la fatigue :
formation lourde, avantages naturels et Hérisson gardent leurs priorités.
Les types différents ne reçoivent aucun facteur de fatigue.

Pour un même type, avec effectifs `nA`, `nB`, fatigués `tA`, `tB` et frais
`fA = nA - tA`, `fB = nB - tB`, `bonus_fatigue()` calcule :

```text
paires_fatiguees = min(tA, tB)
direct_A = min(fA, tB - paires_fatiguees)
direct_B = min(fB, tA - paires_fatiguees)
paires_fraiches = min(fA - direct_A, fB - direct_B)
frais_libres_A = fA - direct_A - paires_fraiches
frais_libres_B = fB - direct_B - paires_fraiches
bonus_A = direct_A + frais_libres_A * tB / nB
bonus_B = direct_B + frais_libres_B * tA / nA
puissance_A = valeur_collective_A * (nA + bonus_A)
puissance_B = valeur_collective_B * (nB + bonus_B)
resistance_A = puissance_A / nA
resistance_B = puissance_B / nB
pertes_A = min(nA, floor(puissance_B / resistance_A))
pertes_B = min(nB, floor(puissance_A / resistance_B))
```

Les taux adverses utilisent les effectifs initiaux de cet affrontement. Les
fatigués libres contribuent à la puissance sans bonus. Aucun adversaire n'est
réutilisé dans les paires directes. Les UUID n'interviennent pas dans les paires.
`Fraction` conserve exactement les quantités jusqu'au plancher final de chaque
camp. Les pertes sont simultanées ; pas de sous-duels ni d'arrondis par groupe.

`combat_bloc()` garde ses retours pour blocs vides, soutiens et unités sans dégâts.
Les sauvetages par moral et limites de blessures restent ensuite dans
`supprimer_unites()` et `soldats.pertes()` ; aucun nouveau bonus de puissance
lié au moral. Les victimes sont tirées dans l'ensemble des participants selon
la règle commune, sans quota de fatigue ni d'origine.

## Exemples de référence avant moral

Valeur individuelle 5, même type, aucun autre bonus. Chaque résultat porte sur
un seul affrontement. F = frais, T = fatigué. Les fractions ne sont pas arrondies.

| Cas | Bloc A | Bloc B | Bonus A / B | Puissances A / B | Résistances A / B | Pertes A / B | Survivants A / B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 6 F | 3 T | 6 / 0 | 60 / 15 | 10 / 5 | 1 / 3 | **5 / 0** |
| B | 8 F | 3 F + 1 T | 2 / 0 | 50 / 20 | 25/4 / 5 | 3 / 4 | **5 / 0** |
| C | 5 F | 4 F + 1 T | 1 / 0 | 30 / 25 | 6 / 5 | 4 / 5 | **1 / 0** |
| D1 | 3 F + 2 T | 2 F + 3 T | 1 / 0 | 30 / 25 | 6 / 5 | 4 / 5 | **1 / 0** |
| D2 | 3 F + 2 T | 3 F + 2 T | 0 / 0 | 25 / 25 | 5 / 5 | 5 / 5 | **0 / 0** |
| E | 6 F + 2 T | 3 F + 1 T | 1 / 1 | 45 / 25 | 45/8 / 25/4 | 4 / 4 | **4 / 0** |
| F | 5 F + 2 T | 2 F + 1 T | 4/3 / 1 | 125/3 / 20 | 125/21 / 20/3 | 3 / 3 | **4 / 0** |
| G | 8 T | 2 F + 1 T | 0 / 2 | 40 / 25 | 5 / 25/3 | 5 / 3 | **3 / 0** |

Dans D1, deux paires T/T passent d'abord, puis une paire F/T et deux paires F/F.
Un seul frais A est avantagé : les anciennes puissances 40/35 ne s'appliquent plus.
Dans D2, les deux paires T/T puis les trois paires F/F ne donnent aucun bonus.
Dans B, un bonus direct plus `4 × 1/4` pour les frais libres donnent exactement 2.

## Conservation des cas homogènes

Frais/frais et fatigués/fatigués donnent zéro bonus. Pour un bloc frais contre un
bloc entièrement fatigué, les frais appariés ont ×2 ; tous les frais libres ont
également ×2 puisque le taux adverse est 100 %. Le bonus équivalent est donc
exactement l'effectif frais, même en surnombre. Aucune exception spécifique aux
blocs homogènes n'est nécessaire. Les valeurs collectives et positions peuvent
différer sans casser cette équivalence.

L'oracle historique couvre 774 400 combinaisons de types, positions, effectifs
et fatigues homogènes. Les profils individuels homogènes sont aussi comparés
aux booléens historiques. Les 30 scénarios de `.dev/comparer-vue.sh` restent
comparables à `980a3d7` ; leurs états, droits, rapports et tirages doivent être
identiques. Les mélanges nouvellement admis sont validés par leurs résultats
numériques et leurs duels réels, pas par une ancienne formule inexistante.

## Raccordement de Gros_poisson

`VueParticipants.fatigues_individuelles()` fournit un booléen par chemin de la
sélection vivante, dans le même ordre que `infos['unites']`. Le groupe résout
l'origine via l'UUID et `GroupeTemporaire.fatigues_origine()`. Après une perte,
le lecteur relit le bloc ; les morts quittent le relevé. `fatigue()` fournit un
booléen pour un bloc homogène et le tuple individuel sinon. Choc et manœuvre
passent ce résultat à `combat_bloc()` ; le relevé suit aussi les pertes de Rafale.
Seuls les mélanges ajoutent une mention de fatigue partielle au rapport ; les
textes et formats historiques homogènes sont conservés. Pas de nouveau registre, dossier
de fatigue ou mutation de `fatigue_generaux.txt` due au prêt.

`GroupeTemporaire.vue_gros_poisson()` assemble les `selections_gros_poisson()`
existantes en `VueParticipants` et renvoie le motif éventuel sans homologue.
Les blocs non fusionnés restent à leur commandant. Ce raccordement est testé
dans le duel commun, avec pertes réelles puis fermeture et combat du prêteur.
La vue seule n'autorise pas l'ordre : le pipeline valide maintenant acquisition,
QG, positions alliées actives et confrontation avant d'ouvrir le groupe réel.

| Interaction | Fonctions réutilisées | Règle appliquée |
| --- | --- | --- |
| Fusions partielles et retour | `selections_gros_poisson`, `vue_gros_poisson`, `VueParticipants`, `bilan` | QG, positions, confrontation et motifs raccordés. Plusieurs prêteurs réunis avant le duel, UUID natifs dédupliqués. |
| Bonus de composition | `moral_des_pertes`, `unites.moral_bloc`, `caracteristiques_armee` | Composition effective du bénéficiaire, puis fatigue individuelle. |
| Cavalerie lourde | `valeur_base_bloc` | 10 + 5 activent le seuil Avant de 15 ; recalcul commun après pertes. |
| Effets d'ordres | `ordres_pipeline.duel`, `multiplicateur`, `rafales` | Donneur et priorités conservés. Cruelle est recalculée après fusion, sur la composition effective de son donneur. |
| Soutiens | `generaux.infos_bloc_valide`, `soldats.pertes`, `rafales` | Homologues prêtés, chamans dans la composition effective, messagers dans les pertes communes. Aucun bonus non combattant transféré ; aucun soin anticipé. |
| Spore adverse | `choisir_spore`, `bloc_destination_zombies`, `convertir_spore` | Conversion officielle reconnue : UUID/XP conservés, nouveau propriétaire zombie, aucun retour à l'ancienne origine. Même placement pour Propagation. |

La restriction commune Zombie reste applicable aux deux rôles. Elle n'empêche
pas un adversaire d'utiliser Spore contre un prêté admissible. L'auto-désignation
est sans effet et les lignes identiques sont ignorées. Choca_fuite réserve sa
retraite normalement ; les prêts sont libérés avant les déplacements différés.

Gros_poisson est activé. Les validations Linux et root sont consignées dans le
[bilan de reprise](ordres-v2-reprise-codex.md). Muraille, Ralliement et Dernière
charge restent hors de ce chantier.
