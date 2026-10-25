# Audit et stabilisation V2 — 25 octobre 2026

Branche `v2.0`, départ `84802b1`. Arbre Git initial propre. Aucun nouveau
ordre ne doit être ajouté ni activé. Les règles ouvertes restent ouvertes.

## Avancement

- Spécifications commune et Survie, architecture et comptes rendus précédents lus.
- Historique examiné : les derniers changements Orcs/ordres/Bouclier avaient
  été intégrés sans validation complète (compte rendu du 20 octobre).
- Suite initiale Windows : 529 tests, 2 échecs, 896 erreurs (certaines en
  nettoyage), 38 ignorés. Environnement incompatible avec les dépendances Unix ;
  ce résultat ne mesure pas la stabilité Linux du moteur.
- Suite initiale Ubuntu WSL lancée, journal `/tmp/mythodea-audit-initial-linux.txt`.
- Lecture des rapports : écritures publiques pendant le calcul privé confirmées.
  Publication groupée et diffusion pendant CONSULTATION à terminer.
- Lecture des combats : un bouclier isolé dans son bloc reste une cible ordinaire
  lorsque deux boucliers adverses sont présents. Régression à couvrir.
- Tests Orcs/commandement/progression à confronter aux décisions nouvelles.

## Plan de validation

1. Conserver le bilan initial Linux et reproduire les anomalies.
2. Corriger les unités et la sélection des ordres sans activer de nouveaux effets.
3. Isoler les rapports privés ; publier sous gel ; diffuser sans ralentir le
   calcul et sans processus permanent, avec reprise du même fichier.
4. Compléter les régressions, parties complètes déterministes et interruptions.
5. Compiler, exécuter toute la suite et les tests Linux isolés possibles.
6. Actualiser ce rapport avec résultats exacts et décisions encore nécessaires.

## Limites connues à qualifier

- Le QG/commandement V2 est une API préparatoire, distincte de l'attaque frontale
  historique. Matérialisation et transition tactique restent à décider.
- Le journal technique long est privé root selon la SPEC ; les rapports
  territoriaux détaillés sont les rapports longs accessibles aux alliés.
- La Survie n'a pas de victoire finale définie, seulement une défaite par
  contrôle final du village par le bot.
- WSL n'est pas une validation Raspberry Pi/SSH réel. Les tests ne doivent
  jamais utiliser une vraie partie sous `/game`.
