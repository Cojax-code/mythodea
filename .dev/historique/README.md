# Tests des règles retirées

Ces copies conservent les tests de progression et de confrontation d'ordres tels
qu'ils existaient avant l'audit final du 2 novembre 2026, au commit `04e2120`.
Elles documentent l'ancien contrat et ne font pas partie de la découverte sous
`.dev/tests`. Elles ne doivent pas servir à réactiver les ordres supprimés.

Les tests actifs conservent les régressions compatibles et vérifient la refonte
décrite dans [REGLES_V2.md](../../REGLES_V2.md), notamment l'absence des anciennes
API d'ordres. Les pertes des scénarios historiques restent vérifiées ; les scénarios
frontaux passent par le paramètre interne déjà existant, sans développement de terrain.
