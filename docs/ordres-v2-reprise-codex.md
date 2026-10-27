# Reprise du chantier des ordres V2 — état réel

Branche unique : `feat/ordres-v2`. Reprise du 27 octobre 2026 depuis `f4bdad6`,
propre et synchronisé avec `origin` après fetch. Aucun changement de branche,
merge vers `v2.0` ou modification de Mythodea-web.

Références : [contrats courants](ordres-v2-preparation.md), [fatigue et obstacles
Gros_poisson](ordres-v2-fatigue-individuelle.md), [audit de départ](ordres-v2-audit-architecture.md)
et `MYTHODEA_SPEC.md`. Les anciens bilans restent dans l'historique Git.

## Fatigue individuelle intégrée

- La décision officielle remplace l'ancien appariement maximal : paires
  fatigué/fatigué, frais/fatigué, frais/frais, puis bonus proportionnel pour les
  seuls frais libres, selon le taux initial de fatigue adverse.
- `combats.bonus_fatigue()` calcule les équivalents de bonus par effectifs,
  sans ordre d'UUID ni hasard. `combat_bloc()` réutilise la base, les bonus
  collectifs et les pertes simultanées existantes ; `Fraction` évite tout
  arrondi avant le plancher final. Les types différents restent inchangés.
- `VueParticipants.fatigue()` conserve le booléen historique si homogène et
  transmet sinon `fatigues_individuelles()`. Le groupe relie les chemins aux
  UUID et à `fatigues_origine()`. Aucun registre ni écriture de fatigue ajouté.
- Choc et manœuvre utilisent les vrais participants, relus après Rafale et pertes.
  Seuls les mélanges ajoutent une mention de fatigue partielle au rapport.
  Moral, blessures, XP, propriétés Linux et publication restent communs.
- Cas A, B, C : survivants **5/0, 5/0, 1/0**. Cas D : **1/0** pour 3 frais +
  2 fatigués contre 2 frais + 3 fatigués ; **0/0** pour deux blocs 3 frais +
  2 fatigués. Les puissances D sont maintenant 30/25 et 25/25, par priorité T/T.

## Gros_poisson : raccordement préparatoire

- `GroupeTemporaire.vue_gros_poisson()` assemble `selections_gros_poisson()`
  et `VueParticipants`, avec motif sans homologue. Pas de nouveau système de prêt.
- Fusion partielle, fatigue mélangée, pertes chez les origines, restitution
  virtuelle et duel suivant du prêteur sont testés dans le moteur commun.
  Les restrictions Zombies et les refus de capacités non définies restent actifs.
- **L'ordre 1017 / `2-6` reste indisponible.** Il reste à raccorder QG, acquisition,
  positions, confrontation et rapport du motif dans le pipeline réel.
- Décisions bloquantes : composition de référence des bonus ; seuil lourd sur
  le bloc fusionné ou les origines (exemple 10 + 5) ; rattachement/destruction des
  soutiens ; sort d'un prêté converti par Spore adverse ; auto-désignation des rôles.
  Le cycle du prêt avec Choca_fuite reste également à raccorder.
- Aucun travail nouveau sur Muraille, Ralliement ou Dernière charge.

## Validation finale

WSL Ubuntu / Python 3.14.4, copies et plateaux temporaires isolés exclusivement :

- Compilation Python du lanceur, dont les cinq fichiers Python modifiés : **OK**.
- `.dev/validation-vue.sh cibles` : **126 tests, 24,831 s, OK** (vue, valeurs,
  participations temporaires, effets des ordres et effets QG).
- `.dev/validation-vue.sh complet` : **756 tests, 99,037 s, OK, 4 réservés root**.
- `.dev/validation-vue.sh root` sous Linux root : **4 tests, 3,208 s, OK**, avec
  vrais UID/GID. Le chemin de fatigue est lui aussi injecté dans la racine temporaire.
  Soit **756 tests distincts réussis**, sans additionner les passes ciblées.
- `.dev/comparer-vue.sh` : **30 scénarios strictement identiques à `980a3d7`**,
  états, UUID, rapports, UID/GID, permissions et tirages inclus ; seuls
  inodes/devices et racines temporaires sont normalisés.
- Oracle historique : **774 400 confrontations homogènes**, plus comparaison de
  **1 936 profils individuels homogènes** aux booléens. Nouveaux mélanges validés
  séparément : résultats numériques, fractions, priorités, permutations, capacités,
  pertes, blessures, XP, relecture après Rafale et interruption sans duplication.
- Première passe de développement : une erreur de calcul manuel dans un nouveau
  test de seuil lourd, corrigée avec la fraction exacte 1/14 ; aucun résultat
  historique attendu n'a été changé. Les relances finales ci-dessus passent.
- Les scénarios de cycle gardent leur gel simulé habituel ; la validation réelle
  Raspberry Pi/SSH/cgroup reste distincte. Aucun essai dans le véritable `/game`.
