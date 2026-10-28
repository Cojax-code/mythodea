# Reprise du chantier des ordres V2 — état réel

Branche unique : `feat/ordres-v2`. Reprise du 28 octobre 2026 depuis `da52467`,
propre et synchronisé avec origin après fetch. Aucun changement de branche,
merge vers `v2.0` ou modification de Mythodea-web.

Références : `MYTHODEA_SPEC.md`, `SURVIE_SPEC.md`, [contrats courants](ordres-v2-preparation.md),
[fatigue individuelle](ordres-v2-fatigue-individuelle.md). L'[audit du 27 octobre](ordres-v2-audit-architecture.md)
reste historique ; ses anciennes questions Gros_poisson ne décrivent plus l'état courant.

## Gros_poisson actif

- ID 1017, ordre Duel `2-6-position_beneficiaire-position_preteur`, apprenable.
  QG, profil privé, acquisition, positions actives du camp, réception et
  confrontation sont validés avant le prêt. Priorité personnelle et PC conservés.
  Deux Gros_poisson adverses à PC égaux s'annulent comme les autres ordres normaux.
- Plusieurs prêteurs sont réunis avant le duel dans une seule `VueParticipants`.
  Seuls les couples bloc/type homologues sont prêtés. Répétitions et UUID natifs
  dédupliqués ; auto-désignation ignorée avant confrontation, sans groupe ni
  annulation adverse. Un conflit de prêteur entre bénéficiaires simultanés est
  détecté avant réservation, sans priorité inventée.
- Réutilisation de `participation_temporaire`, `selections_gros_poisson`,
  `VueParticipants`, `combat_bloc`, `soldats.pertes` et du comptage territorial
  d'XP. Aucun dossier déplacé par le prêt ; UUID, blessures, XP, fatigue et
  propriétaires conservés. Les survivants restent à l'origine, le prêteur garde son tour.
- Composition effective après fusion, bonus collectifs puis fatigue individuelle.
  10 + 5 cavaliers lourds activent le seuil Avant de 15, relu après pertes.
  Chamans et Cruelle tiennent compte de la composition effective. Aucun soin
  anticipé. Aucun bonus de messager n'étant actif, le prêt n'en crée ni n'en transfère.
- Bouclier/Spore lisent la vue commune. Une conversion officielle conserve UUID/XP
  et reconnaît le changement de propriétaire sans retour à l'ancienne origine.
  Contrôles inode, type et UID/GID conservés.
- Spore et Propagation partagent `bloc_destination_zombies` chez leur général
  source : plus grand effectif mort-vivant, hasard entre maxima, Arrière sans
  zombie. Les messagers ne comptent pas. Quantités et déclencheurs conservés.
- Choca_fuite utilise la réservation commune ; prêts libérés avant déplacement.
  Sans survivants propres, le bénéficiaire ne réserve pas une retraite vers un
  général qui serait supprimé au retour des prêts.

## Restrictions Zombies

- `progression` centralise profil Zombie, droit d'ordre et droit de possession.
  Seuls les généraux Zombies peuvent posséder Zombies et Trop gros zombie.
  Un soldat authentique chez un général ordinaire fait refuser l'audit/publication,
  sans suppression ou transfert inventé. Les créations sans origine officielle
  restent traitées par l'audit préexistant.
- Seuls Spora-adicte et Propagafion sont autorisés. Spora-adicte reste mémorisable
  mais son effet demeure désactivé ; aucun nouveau ciblage n'est introduit.
- Frontal classique et Muraille préparatoire excluent les participants Zombies.
  On_melange et QG_nommade ne réordonnent que les généraux éligibles ; les Zombies
  gardent leurs rangs dans la séquence normale. Combat et capacités automatiques
  restent actifs. Apprentissage, nature et progression Zombie restent inchangés.

## Autres chantiers

La fatigue intégrée par `da52467` ne change pas : paires fatigué/fatigué,
frais/fatigué, frais/frais, puis bonus proportionnel des seuls frais libres.
Fractions exactes jusqu'au plancher collectif ; règles homogènes conservées.
Muraille, Ralliement et Dernière charge restent inactifs. La mémoire Zombie et
les autres chantiers antérieurs restent hors de cette intervention.

## Validation Linux

WSL Ubuntu / Python 3.14.4, copies et plateaux temporaires exclusivement ; aucun
accès au vrai `/game`. Les scripts compilent tous les fichiers Python concernés.

- Compilation : OK ; chiffres définitifs à reporter après validation des restrictions Zombies.
- Root du raccordement Gros_poisson : **5 tests, 4,291 s, OK**, dont conversion
  d'un prêté par Spore avec vrais UID/GID 62001, 62002 et 62003, sans créer de comptes.
- Comparaison avant restrictions Zombies à `980a3d7` : **27/30 scénarios strictement
  identiques**. Les trois Bouclier ont les mêmes résultats, fichiers, UUID et
  permissions ; seul l'état RNG diffère car un maximum unique ne consomme plus
  de tirage de placement. Le comparateur strict signale ces trois écarts et
  détaille les scénarios/champs concernés.
- Les attentes de statut désactivé ont été adaptées à l'activation demandée.
  Les premiers essais ont corrigé le maintien des sélections explicites de la
  vue, une valeur de test lourd (10, pas 15) et une hypothèse de test erronée sur
  la coexistence d'ordres normaux adverses à PC égaux.
- Les tests de cycle gardent leur gel simulé habituel ; une validation réelle
  Raspberry Pi/SSH/cgroup reste distincte.
