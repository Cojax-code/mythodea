# Préparation des ordres V2 — conception, pas activation

Base de travail : branche `feat/ordres-v2`, issue de `v2.0` après le commit d'audit `eb5c302`.
Les effets des 21 ordres restent **désactivés** tant qu'ils ne sont pas intégrés et testés.
La vérification finale (suite Linux complète, WSL/Raspberry Pi) est confiée à Codex.

## Règles transversales validées

- Les ordres se confrontent par **catégorie et par donneur**. Ne pas fusionner les ordres de généraux différents pour former un cumul.
- Ordre normal contre ordre normal : seuls les ordres du camp gagnant aux PC sont retenus ; en cas d'égalité, ils sont annulés.
- Ordre normal contre contre-ordre : les deux peuvent fonctionner.
- Un contre-ordre fonctionne si ses PC sont inférieurs **ou** s'il n'y a pas d'ordre adverse dans la confrontation concernée.
- Les ordres compatibles **du même général** peuvent se cumuler, mais jamais un ordre normal et un contre-ordre du même donneur.
- Les incompatibilités propres à chaque effet priment sur le cumul par défaut.
- Les effets réservés/non programmés ne doivent pas être activés par simple ajout au catalogue.
- Pour les ordres de duel avec ciblage explicite du QG, le chiffre de cible est une **position** de général, pas son identifiant. Les nouveaux formats spéciaux restent à définir exactement.

## Catalogue de conception (18 ordres du brouillon JSON)

| Ordre | Catégorie | Contre-ordre | Résumé |
|---|---|---|---|
| Charge suicidaire | Individuelle | Non | Fin du duel : chance en % = ⌊pertes d'unités pendant ce duel / 4⌋ de tuer le général adverse. |
| Gros_poisson | Duel | Non | Fusion temporaire des unités homologues de deux généraux ; restitution des survivants à leurs propriétaires. |
| Choca_fuite | Duel | Non | Fuite normale vers le village juste après le choc initial. |
| Retrait_tactique | Globale | Oui | Après un premier combat, le premier général va en dernière position ; récupère 50 % de ses pertes par sélection aléatoire. |
| Hérisson | Individuelle | Non | Piquiers : faiblesse ×3 contre distance, force ×3 contre cavaliers. |
| Discours de la mort | Individuelle | Non | +10 % de moral, cumulable avec les autres bonus sous plafond. |
| Spora-adicte | Globale | Non | +1 à l'effet Spore d'un général Zombie ciblé ; l'émetteur est un général extérieur. |
| Propagafion | Globale | Non | +2 conversions à la Propagation normale. |
| Confinement | Globale | Oui | Neutralise totalement Spore, y compris le bonus Spora-adicte. |
| Pour_l'honneur | Globale | Non | Défenseur OFF/DEF : annule les faiblesses des unités au choc initial ; incompatible avec les autres ordres sauf exception explicite. |
| Ralliement | Globale | Non | Renforts temporaires du QG défenseur : 20 % (arrondi inférieur), par type présent chez le bénéficiaire, des pertes du général allié vaincu. Les piquiers d'un allié ne bénéficient pas à un général sans piquiers. |
| Rafale | Individuelle | Non | Avant le choc initial : ⌊nombre d'archers / 4⌋ tentatives de pertes directes ; tirage aléatoire des unités, sans effet sur cible lourdement blindée ; exige un bloc Arrière d'archers. |
| Cruelle | Duel | Non | Juste avant le combat du général : -1 % de moral adverse par unité cruelle de son armée. |
| Orc_un_jour_orc_toujour | Duel | Non | Donne temporairement l'étiquette Orc aux Sauvageons. |
| Étincellant | Globale | Non | Les Chevaliers clinquants attaquent en premier en manœuvre, sans double attaque durant le même tour. |
| On_melange | Globale | Non | Inverse la séquence des positions des généraux (4, 3, 2, 1). |
| QG_nommade | Globale | Non | Le général QG combat en dernier, avec priorité sur les autres ordres globaux de placement. |
| Chat-man | Duel | Oui | Retarde le combat des Chamans jusqu'à la disparition des autres blocs ; le bloc adverse initialement opposé obtient l'initiative et recherche un bloc contre lequel il est efficace. |

## Trois nouveaux ordres validés en conception

### Muraille humaine — Globale, ordre normal

Les blocs Avant des généraux alliés forment une défense collective temporaire au choc initial.
Ils **ne participent pas à la manœuvre** ; si leur général perd, son bloc Avant est également considéré comme perdu.
Reste à trancher la signification exacte de « perdu » (morts, fuite ou autre état), ainsi que la répartition des pertes pendant le choc collectif.

### Réserve stratégique — Globale, ordre normal

Le QG désigne un général de réserve. Celui-ci vient combattre chaque général adverse qui vient de remporter un combat, donc déjà éprouvé, puis se retire pour que les prochains généraux frais poursuivent le déroulement normal. S'il n'a pas été engagé autrement, il combat normalement lorsqu'arrive sa position finale.
À préciser : s'il reste opérationnel après une interception, peut-il enchaîner sans limite, comment sont gérées ses pertes et la fatigue, et quelle priorité face à QG_nommade.

### Dernière charge — Duel, contre-ordre

Le général précédent est vaincu. Pour le choc initial du général suivant, **les unités vaincues du flanc G ou D du général précédent** se relèvent pour une dernière charge en état de fatigue, à la place du flanc correspondant du général suivant.
À la manœuvre elles disparaissent définitivement du combat, même si elles gagnent le choc initial ; la formation normale du général suivant revient. Les pertes subies durant l'ultime charge restent réelles.
Un seul flanc doit être désigné : `G` ou `D`. Format de jeton exact à fixer avec le parseur existant et la sélection du donneur.

## Questions et garde-fous avant codage des effets

1. **Ne pas interpréter** « perdu » de Muraille humaine comme mort définitive sans validation.
2. Définir les cas limites de Réserve stratégique (répétition, fatigue, positions et QG).
3. Déterminer les priorités exactes entre plusieurs ordres de modification du déroulement et leurs incompatibilités.
4. Gros_poisson : conserver l'identité, le propriétaire, les blessures, l'expérience et la restitution ; clarifier ses 3e et 4e paramètres.
5. Ralliement : vérifier la provenance/identité des renforts, notamment lorsqu'ils sont issus de pertes, et leur restitution éventuelle.
6. Appliquer les arrondis plancher seulement là où ils ont été validés. Charge suicidaire utilise les pertes du **seul duel**.
7. Faire passer tests ciblés puis suite Linux complète et parties déterministes avant activation.
8. Mettre le site, le Bestiaire et le simulateur à niveau **après** stabilisation des règles exécutables.

Cette note est une photographie des décisions prises et des questions ouvertes ; elle ne modifie aucune règle active du moteur.
