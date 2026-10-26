# Reprise du chantier des ordres V2 — état réel

## Lot B — groupes temporaires communs, 26 octobre 2026

**Cette section fait foi ; les sections suivantes sont des archives.**

### Point de départ vérifié

- Reprise sur `feat/ordres-v2`, propre, au commit `82672ee` (« lot b debut »).
  Après `git fetch origin feat/ordres-v2`, HEAD et la référence distante étaient
  identiques (0/0). Aucun changement de branche ni pull nécessaire.
- Le dernier commit ajoutait déjà `GroupeTemporaire`, les références de soldats,
  19 tests et le filtre pur de Muraille dans `ordres_calculs_v2.py`. Les
  publications privées et interruptions avaient déjà leurs scénarios. Le
  précédent journal s'arrêtait au Lot A et ne décrivait pas cette base.
- Périmètre : moteur commun, tests et documentation de ce dépôt. Aucun merge
  vers `v2.0`, aucune modification de Mythodea-web.

### État livré

- Dans `python/soldats.py`, une participation garde les dossiers à leur origine.
  UUID, joueur, général, bloc, inode et UID/GID restent attachés au soldat réel.
  La liste des participants est exposée en lecture seule. Le bilan relit le
  registre privé et refuse les modifications d'origine, d'identité, de type ou
  de propriétaire Linux, ainsi que les disparitions sans décès enregistré.
- `selections_homologues()` fournit un index `(bloc, type) -> UUID vivants`.
  Il ne choisit ni bénéficiaire, ni effectif à prêter, ni type majoritaire.
  `bloc()` reste un instantané utilisable par `combats.combat_bloc()`.
- `appliquer_pertes()` relit et contrôle la sélection avant de déléguer à
  `soldats.pertes()`. Sélection et moral sont explicites ; aucun partage entre
  propriétaires n'est activé par défaut. Les blessures, morts et champs privés
  individuels restent ceux du moteur. Un instantané ancien ne sert pas à
  restaurer les effectifs ou à ressusciter une unité.
- `participer()` inscrit les UUID explicitement engagés au comptage commun de
  bataille complète. Préparer un groupe ne donne pas d'XP ; les soldats non
  prêtés ne sont pas engagés automatiquement, et le général prêteur ne reçoit
  pas de crédit personnel implicite. Les reçus existants évitent les doubles gains.
- Les prêts simultanés du même UUID sont refusés. Sortie normale ou exception
  libèrent les réservations ; les vues fermées ou utilisées dans un autre
  contexte public/privé sont refusées. Fermer ne restaure aucun état.
- Les tests de capture/publication existants utilisent maintenant l'entrée
  contrôlée de pertes. Le protocole commun conserve les résultats privés
  jusqu'à publication et interdit le rejeu d'une résolution interrompue.
- Aucun nouveau format persistant, permission, commande joueur, règle de combat
  ou effet d'ordre actif. Les onze ordres V2 actifs et le frontal restent inchangés.

### Préparation des quatre ordres et blocages

La liste détaillée et les responsabilités de raccordement figurent dans
`docs/ordres-v2-preparation.md`, section « Lot B — préparation et décisions
bloquantes ». Résumé pour la prochaine reprise :

1. **Gros_poisson** : syntaxe/sens des paramètres 3 et 4, participants et
   bénéficiaire, partage des pertes. L'index homogène et la restitution virtuelle
   par origine sont prêts ; les survivants doivent rester chez leurs propriétaires.
2. **Muraille humaine** : résolution des types différents dans la ligne Avant,
   répartition des pertes, statut physique de l'Avant du général vaincu.
   Les exclusions QG_nommade/réserve et les règles de phases déjà confirmées ne
   sont pas à redemander.
3. **Ralliement** : source/identité des soldats récupérés, blessures/XP de ces
   renforts, destination et devenir final quand leur général d'origine est vaincu.
   Le calcul par type `pertes // 5` est prêt et ne crée aucune unité.
4. **Dernière charge** : syntaxe G/D, cas du flanc absent, état physique des
   relevés et devenir après leur retrait définitif du combat. Défaite préalable,
   fatigue et remplacement du flanc au seul choc sont déjà confirmés.
5. **Forces collectives** : préciser moral/fatigue/bonus lorsque les contributeurs
   ont des caractéristiques différentes. Aucune caractéristique d'un prêteur ou
   d'un bénéficiaire n'est choisie implicitement par le socle.

**Les quatre effets restent désactivés.** Le socle ne masque pas les soldats dans
les lectures ordinaires de leur général et ne remplace pas un duel complet.
Le raccordement des phases, des capacités (dont les transferts réels de Spore)
et des rapports de chaque ordre doit suivre les décisions ci-dessus. Il ne faut
pas activer un ordre en ajoutant seulement une entrée au catalogue.

### Validation

- Référence avant modification : **29 tests, 17,801 s, OK**, sous WSL Ubuntu,
  journal `.dev/ordres-v2-lot-b-reference.txt`.
- Compilation des trois fichiers Python modifiés/ajoutés : OK sous Linux,
  caches hors dépôt dans `/tmp`.
- Première passe ciblée : **38 tests, 29,030 s, OK**, journal
  `.dev/ordres-v2-lot-b-cibles.txt`.
- Permissions Linux réelles sous root : **3 tests, 8,161 s, OK**, journal
  `.dev/ordres-v2-lot-b-permissions.txt`. Deux nouveaux tests utilisent seulement
  des dossiers temporaires et les UID/GID numériques 62001/62002, sans créer de
  comptes : accès du seul propriétaire, registre root privé, copies privées,
  conservation des droits après blessures/pertes et détection des changements
  d'UID/GID. Le troisième couvre le contrôle administrateur Crypte ignoré sans root.
- Régressions ciblées élargies : **145 tests, 152,778 s, OK**, journal
  `.dev/ordres-v2-lot-b-regressions.txt` : groupes, calculs d'ordres, effets,
  soldats/formation, générations, formations et pipeline QG.
- Suite complète : **695 tests, 668,733 s, aucun échec, trois ignorés root**,
  journal `.dev/ordres-v2-lot-b-complets.txt`. Les trois contrôles root ci-dessus
  couvrent exactement ces tests ignorés : **695 tests distincts réussis** au
  total, sans recompter les passes ciblées. Cette reprise ajoute 11 tests aux
  684 présents dans `82672ee` ; aucune assertion antérieure n'a été assouplie.
- `git diff --check` : OK. Aucun cache Python suivi. Le commit de reprise est
  local sur `feat/ordres-v2` ; aucun push ni merge effectué.

La validation WSL utilise un vrai noyau Linux pour les permissions. Les scénarios
de génération emploient le gel simulé habituel : ils ne remplacent pas la recette
Raspberry Pi avec sessions SSH et gel cgroup réels.

## Lot A — formations et compatibilités, 26 octobre 2026

Archive du Lot A ; la section Lot B ci-dessus décrit la reprise actuelle.

### Audit et périmètre

- Branche vérifiée : `feat/ordres-v2`, propre avant intervention. Après fetch,
  HEAD et `origin/feat/ordres-v2` étaient tous deux à `80772a7` (0/0) : aucun pull.
- Contrairement au précédent bilan, ce commit contenait déjà la transmission
  QG et Propagafion, Confinement, Étincellant actifs, avec leurs tests. Ils n'ont
  pas été réimplémentés. La destruction QG jusqu'à fin de duel est conservée.
- Travail limité au moteur, aux tests et à la documentation de ce dépôt.
  Aucun merge vers `v2.0`, aucun changement de Mythodea-web.

### Fonctions réellement intégrées

- **On_melange**, ID 1015, jeton `1-6` : séquence du camp `4,3,2,1`.
- **QG_nommade**, ID 1016, jeton `1-7` : QG exclu des duels frontaux et placé en
  dernier au rangé, prioritaire sur On_melange. Aucun déplacement de dossiers,
  aucune recomposition des places vides, aucune perte ou fatigue nouvelle.
- Les deux ordres passent par le QG officiel, l'apprentissage privé, les
  restrictions de nature, les PC globaux et la confrontation commune.
- Matrice des six paires incompatibles et huit compatibles dans
  `commandement.py`. Annulation simultanée de tous les ordres impliqués dans
  une paire interdite du camp ; les autres restent candidats. Chaque paire et
  son motif sont rapportés. Les paires non définies sont distinguées des autorisées.
- L'annulation est réalisée par camp avant la comparaison adverse, y compris
  lorsque `1-2` vient d'un autre général allié. Elle reste mémorisée pendant la
  bataille et ses cascades ; aucun nouveau fichier d'état.
- Migration ciblée validée pendant cette reprise : `1-2` opposé à On_melange
  est confronté aux PC globaux des donneurs QG. Le plus fort impose son schéma ;
  l'égalité annule les deux. Dans ce cas migré, un frontal sans donneur QG
  autorisé ne contourne pas la confrontation. Les autres déclenchements historiques
  restent inchangés. Les rapports distinguent opposition adverse et conflit interne.
- La priorité future Retrait_tactique juste avant le QG est testée comme calcul
  de séquence uniquement ; elle n'active ni récupération de soldats ni retrait.

**Onze ordres V2 actifs**, plus le frontal historique : Hérisson, Discours de la
mort, Orc_un_jour_orc_toujour, Rafale, Cruelle, Choca_fuite (Survie), Propagafion,
Confinement, Étincellant, On_melange et QG_nommade.

### Validation

- Référence intacte `80772a7`, exportée sous `/tmp` : **642 tests en 91,987 s,
  aucun échec, un ignoré root** (`.dev/ordres-v2-lot-a-reference.txt`). L'ancien
  échec d'activation Choca_fuite ne se reproduit pas.
- Compilation des quatre modules Python et trois fichiers de tests modifiés :
  OK, avec `PYTHONPYCACHEPREFIX` hors dépôt.
- Première passe ciblée : 44 tests, trois échecs de scénarios où les bots de test
  recevaient `1-2` par défaut. Leur préparation a été corrigée pour tester le rangé
  demandé, sans modifier les résultats attendus ni le comportement du bot moteur.
  Revalidation : **44 tests en 17,507 s, OK**.
- Après décision de confrontation adverse : **126 tests en 44,470 s, OK**
  (`.dev/ordres-v2-lot-a-cibles.txt`) ; formations, QG, retraites, comparateurs,
  frontal classique, deux camps, rapports privés et interruptions.
- Contrôles Linux avec root et UID temporaires : **4 tests en 10,529 s, OK**
  (`.dev/ordres-v2-lot-a-permissions.txt`), dont le test ignoré de la suite générale.
- Suite complète finale : **665 tests en 280,164 s, aucun échec, un ignoré
  réservé à root**, journal `.dev/ordres-v2-lot-a-complets.txt`. Les quatre
  contrôles root ci-dessus couvrent aussi ce test : **668 tests distincts réussis**,
  sans recompter les passes ciblées. Les 23 nouveaux tests sont dans
  `.dev/tests/test_formations_v2.py`.
- La première tentative de référence sur le répertoire de travail a croisé
  des modifications avec des rechargements de modules : 642 tests, 31 erreurs,
  un ignoré. Son journal `.dev/ordres-v2-lot-a-avant.txt` n'est **pas** une mesure
  du commit initial. La référence isolée ci-dessus remplace cette tentative.

Les listes explicites d'activations et de récompenses des tests existants ont été
étendues uniquement aux deux IDs intégrés ; aucune assertion de combat antérieure
n'a été assouplie. Les validations Linux temporaires ne remplacent pas la recette
Raspberry Pi avec SSH et gel cgroup réels.

### Dix ordres V2 encore désactivés et suite des lots

| Ordre | Travail ou décision restant |
| --- | --- |
| Charge suicidaire | Lot C : groupes de survivants humains, compteurs, sauvegarde, audit et réaffectation manuelle ; retrait définitif des survivants bots. Les règles fournies sont enregistrées, aucun effet persistant encore activé. |
| Gros_poisson | Lot B : syntaxe des paramètres, répartition des pertes et restitution des soldats identifiés. |
| Retrait_tactique | Identité, état et sélection des 50 % récupérés ; placement avant QG validé, mais récupération non définie complètement. |
| Spora-adicte | Syntaxe et validation de la position du Zombie ciblé. La durée QG est résolue. |
| Pour_l'honneur | Non-cumul sans exception confirmé ; traitement de ce non-cumul hors formations et raccordement des modifications du choc à préciser. |
| Ralliement | Provenance et état des soldats récupérés, restitution des renforts temporaires. |
| Chat-man | Départage des cibles efficaces et articulation de l'initiative avec le Bouclier. |
| Muraille humaine | Répartition des pertes collectives et devenir des Avant du général vaincu. Exclusions du QG et de la réserve confirmées. |
| Réserve stratégique | Syntaxe de désignation, coexistence de réserves adverses et issue d'une interception échouée. Rangé uniquement, avant son tour normal, sans fatigue nouvelle ; exclusions QG/Muraille confirmées. |
| Dernière charge | Syntaxe G/D et état physique des soldats relevés après défaite obligatoire du général précédent. |

La paire Attaque frontale + Retrait_tactique reste non définie. La compatibilité
Réserve stratégique + Retrait_tactique ne supprime pas l'interdiction générale
d'ordre normal et contre-ordre chez un même donneur. Aucun contournement ajouté.

Les décisions détaillées de Charge suicidaire, dont les survivants bots sans
village, sont consignées dans `docs/ordres-v2-preparation.md`. Ne pas redemander
ces décisions déjà validées lors de la reprise du lot C.

## Décisions QG et Choca_fuite intégrées — 25 octobre 2026

Archive : cette section remplaçait les états antérieurs ci-dessous. Travail exclusivement
sur `feat/ordres-v2`, depuis `82ba5ca` (qui avait revalidé `a67057d`).
Pas de fusion, pas de modification de `Mythodea-web`.

### Ce qui fonctionne

- **Six ordres exécutables** : Hérisson, Discours de la mort,
  Orc_un_jour_orc_toujour, Rafale, Cruelle, et désormais **Choca_fuite en Survie**
  (ID 1011, jeton `2-5`, apprentissage privé obligatoire). Le `1-2` historique
  reste exécuté par son circuit existant.
- Choca_fuite réserve la retraite immédiatement après le choc initial et
  exclut le survivant des manœuvres et des duels suivants. Les fonctions de
  retraite existantes fixent la destination voisine, les places, la réserve
  du village et la fatigue. Aucun placement ni calcul de pénalité nouveau.
  Au village, la règle existante interdit la retraite automatique : refus
  rapporté, puis poursuite du combat. Même refus si le bot bloque l'arrivée
  ou si aucune place autorisée n'est disponible. Les bots ne reçoivent pas
  d'ordre spécial. Hors Survie, ce jeton n'est pas exécuté.
- **Déclaration et sélection QG opérationnelles**, sans prétendre activer ses
  ordres : lecture sécurisée de `qg.txt`, bloc existant non vide, toutes natures
  admises. Plusieurs déclarations valides dans un camp les annulent toutes,
  même avec des PC différents. La sélection des forces engagées reste figée
  pendant la cascade. Destruction mémorisée dès la perte de la dernière unité
  du bloc, y compris via Spore ou perte du Bouclier ; aucun remplacement ni
  réactivation par repeuplement. Déclaration et destruction figurent aux rapports.
- Sauvegardes et identités conservées : `qg.txt` suit les copies et déplacements
  existants ; aucun nouveau format de registre privé. Les retraites sont
  réservées dans la génération privée puis publiées par le protocole commun.
- **Charge suicidaire reste désactivée**. Seuls ses calculs indépendants sont
  préparés : pertes du seul duel `// 4`, deux tirages indépendants avec RNG
  injectable, réussites simultanées possibles. Aucun général ni soldat n'est
  supprimé par ces fonctions. Aucun dossier de repli arbitraire n'est créé.

### Validation de cette étape

- Compilation Linux des neuf modules Python et quatre fichiers de tests modifiés : OK.
- Nouveaux tests ciblés : **13 tests, 6,234 s, OK**, trace
  `.dev/qg-retraites-nouveaux.txt`. Ils couvrent les deux joueurs, le village,
  l'arrivée bloquée, le frontal suivi du rangé, les UUID/blessures/XP, les rapports
  privés jusqu'à publication, l'interruption après réservation et le refus de
  rejeu d'une génération interrompue.
- Suite complète et contrôles root : résultats à inscrire après leur exécution.
- Premières exécutions ciblées : un import isolé manquait dans le chemin Python,
  puis des fixtures plaçaient un général hors garnison et supposaient sa survie
  après un refus de retraite. Les fixtures ont été corrigées selon les règles
  existantes ; aucun résultat moteur n'a été ajusté pour satisfaire ces tests.
  `.dev/qg-retraites-cibles.txt` conserve le premier échec d'import et les
  70 régressions alors réussies.

### Décisions encore indispensables et effets désactivés

| Ordres désactivés | Point restant |
| --- | --- |
| Charge suicidaire | Destination exacte de `unites_sans_general`, structure des groupes, procédure de réaffectation. Compteurs et distance réutiliseront les règles existantes après définition de la destination. |
| Propagafion, Confinement, Étincellant, On_melange, QG_nommade | Durée des ordres déjà transmis lorsque le QG est détruit : fin du duel ou arrêt immédiat ? Puis raccordement et tests des effets/priorités. |
| Spora-adicte | Même durée QG ; syntaxe du ciblage Zombie par position. |
| Pour_l'honneur | Durée QG, exceptions au non-cumul, interactions des modifications du choc. |
| Ralliement | Durée QG ; provenance, blessures et restitution des renforts. |
| Gros_poisson | Paramètres, transfert temporaire et répartition des pertes/restitution des UUID. |
| Retrait_tactique | Origine et état des 50 % récupérés, interaction avec les placements. |
| Chat-man | Départage des cibles efficaces et priorités face au Bouclier/initiative. |
| Muraille humaine | Répartition des pertes, état du bloc Avant du vaincu ; exclusion de manœuvre ≠ mort. |
| Réserve stratégique | Réserves des deux camps, échec d'interception et priorité de QG_nommade. |
| Dernière charge | Syntaxe G/D et statut physique des soldats relevés ; défaite préalable obligatoire. |

La **transmission de duel par le QG reste désactivée** jusqu'à la réponse sur
la durée d'effet après destruction. Les PC du donneur et la formule globale
existante restent inchangés ; posséder un QG n'accorde aucun ordre non appris.
Les deux questions ont été posées pendant le travail. Aucune réponse implicite
n'est déduite de l'écoulement du temps.

Les contrôles Linux utilisent WSL Ubuntu et des plateaux temporaires ; ils ne
remplacent pas une session SSH réelle avec gel cgroup sur Raspberry Pi.

## État antérieur — reprise de a67057d

Historique antérieur aux décisions QG et Choca_fuite : les règles et résultats
de la section précédente font foi pour la livraison actuelle.

- Branche unique : `feat/ordres-v2`. Reprise du WIP poussé `a67057d`, sans
  modification du moteur depuis cette sauvegarde. La suite d'effets et ses
  journaux étaient encore non suivis : ils sont maintenant enregistrés dans
  **`c8cca1c`**, et non plus seulement présents sur le poste local.
- Ancien audit clôturé dans `AUDIT_V2_STABILISATION.md` : 584 tests avant
  modifications, aucun échec, un test root ignoré puis validé parmi les 4 tests
  Linux isolés. Soit 587 tests distincts réussis avant nouveaux effets.
- Lot intégré : Hérisson (`1006`, `3-2`), Discours de la mort (`1007`, `3-3`),
  Orc_un_jour_orc_toujour (`1008`, `2-3`), Rafale (`1009`, `3-4`),
  Cruelle (`1010`, `2-4`).
  Les effets sont raccordés aux duels réels, avec apprentissages privés,
  confrontation par catégorie, cumul personnel et contexte temporaire.
- Validation finale retrouvée : **618 tests en 268,762 s, aucun échec, un
  ignoré réservé à root**, journal `.dev/ordres-v2-complets.txt`.
- **72 tests ciblés d'ordres réussis en 26,153 s**, dont les **31 tests** du
  nouveau fichier `test_ordres_effets_v2.py`. Également 63 tests de progression,
  niveaux et défis en 22,089 s, sans échec.
- **4 tests Linux root réussis en 7,632 s**, dont le test ignoré dans la suite
  complète : `.dev/ordres-v2-permissions-finales.txt`. Soit **621 tests distincts
  réussis**, sans compter deux fois les vérifications ciblées.
- Cinq parties complètes déterministes, avec reprise entre tours : trois
  scénarios d'audit historiques, plus une défense avec Rafale/Discours et une
  défense coopérative avec ordres. Incluses dans les 618 tests.
- Compilation Python des modules et tests modifiés réussie, caches hors dépôt.
  Nouvelle exécution à la reprise : **618 tests en 250,459 s, aucun échec,
  un ignoré root**, journal `.dev/ordres-v2-reprise-a67057d.txt`.
- Correction du comparateur : un groupe mixte ordre/contre-ordre invalide est
  retiré AVANT comparaison, afin de ne pas neutraliser les ordres adverses.
- Rafale peut éliminer un général avant le choc : terminaison précoce explicite,
  participation des soldats enregistrée avant les tirs.
- La première intégration complète révélait deux défauts : sélection de plusieurs
  ordres à configurer dans la progression, et rupture des arguments positionnels
  de `combat_bloc`. La règle uniforme a été confirmée par le propriétaire et
  intégrée ; les nouveaux paramètres de généraux sont nommés pour conserver
  l'interface historique des blocs. Trace : `.dev/ordres-v2-intermediaire.txt`.
- Les nouvelles récompenses sont accessibles par les voies d'apprentissage
  existantes. Une mémoire en attente ou une fiche publique falsifiée n'autorise
  pas l'exécution. Aucun droit nouveau aux anciens généraux sans profil privé.
- Dernier commit stable du moteur et de sa suite complète : **`c8cca1c`**
  (moteur `a67057d`, tests d'effets et preuves ajoutés). Le commit suivant ne
  change que ce compte rendu et la trace de revalidation. Aucun merge ni push
  effectué par Codex. `Mythodea-web` n'a pas été modifié.

### Décisions confirmées pendant la reprise

- Le QG peut occuper n'importe quel bloc existant choisi par le joueur. Sa
  procédure de déclaration manque encore : aucune commande ni fichier de
  déclaration n'est inventé. Les ordres globaux et la transmission QG restent
  non opérationnels, malgré les calculs et comparateurs testés.
- Rafale précède la priorité de protection du Bouclier vivant. Moral et blessures
  habituels s'appliquent ; les unités lourdement blindées sont immunisées.
  Le Bouclier conserve ensuite ses autres capacités. Les tirs utilisent le
  bloc Arrière de type `archer`, les victimes distinctes sont tirées parmi les
  unités éligibles, y compris les soutiens et le Bouclier (aucune autre immunité).
- Cruelle : réduction multiplicative exacte confirmée, 50 PM et 10 unités cruelles
  donnent 45 PM. Le nombre d'unités est relevé avant les pertes du duel. Le facteur
  se combine à Discours avant le bornage commun des ordres, sans arrondi ajouté.
- Progression : tirage uniforme confirmé parmi les ordres éligibles, avec le
  générateur injectable de progression. Tests d'accès à chaque candidat et de
  reproductibilité à graine identique. Les poids de catégories restent inchangés.

### Travail restant et limites d'intégration

| Ordres encore désactivés | Décision ou raccordement manquant |
| --- | --- |
| Charge suicidaire | Devenir des troupes encore vivantes quand leur général est tué par l'effet, y compris décès simultanés |
| Choca_fuite | Placement au village (plein, village d'origine), accès du bot et articulation avec la file de retraite ; pas de règle de placement inventée |
| Gros_poisson | Paramètres, transfert temporaire et répartition des pertes/restitution des UUID |
| Retrait_tactique | Origine/identité et état des 50 % récupérés, interaction avec les placements globaux |
| Spora-adicte | Déclaration du QG, ciblage Zombie par position et syntaxe |
| Propagafion, Confinement | Déclaration du QG puis raccordement aux capacités ; calculs purs déjà testés |
| Pour_l'honneur | Déclaration du QG, exceptions au non-cumul et interaction avec les autres modifications du choc |
| Ralliement | Déclaration du QG ; provenance, blessures et restitution des renforts |
| Étincellant, On_melange, QG_nommade | Déclaration du QG, puis intégration des priorités au parcours territorial |
| Chat-man | Départage des cibles efficaces et interactions de priorité avec Bouclier/initiative |
| Muraille humaine | Répartition des pertes, état du bloc Avant du général vaincu ; exclusion de manœuvre ≠ mort |
| Réserve stratégique | Déclaration du QG, réserves des deux camps, échec d'interception et priorité de QG_nommade ; répétition autorisée sans nouvelle fatigue |
| Dernière charge | Syntaxe G/D et statut physique des soldats relevés ; défaite préalable obligatoire |

La sauvegarde des soldats et l'arrêt en récupération après interruption sont
ceux du moteur commun. Aucun rejeu automatique d'une génération partiellement
calculée. Le registre `ordres_conception.py` reste documentaire et immuable ;
seul le catalogue explicite active les effets testés. Le comportement de `1-2`
est conservé et comparé avec/sans pipeline dans une bataille territoriale.

Prochaine étape : appliquer les réponses aux trois questions posées à la reprise
pour poursuivre sans invention :
déclaration du QG et calcul de sélection ; troupes du général tué par Charge
suicidaire et tirages simultanés ; destination exacte de Choca_fuite, notamment
au village. Aucune des propositions de syntaxe posées en question n'est validée
ou implémentée à ce stade.

### Statut de livraison

L'ancien audit automatisé est terminé. Les cinq ordres personnels ci-dessus
sont intégrés et testés, y compris les rapports privés et les interruptions.
Le moteur est stable dans ce périmètre de régression. **16 ordres restent
désactivés**, ainsi que la transmission des ordres par le QG ; les fonctions
préparatoires ne sont pas comptées comme effets opérationnels.

Les permissions ont été vérifiées sous Linux avec de vrais UID isolés, sur
dossiers temporaires. La recette Raspberry Pi avec connexions SSH et gel réel
des comptes reste à réaliser sur une machine dédiée. Le chantier complet des
21 ordres n'est pas prêt pour fusion ; aucune fusion vers `v2.0` n'est effectuée.

## Journal historique de préparation (non applicable comme bilan courant)

## Source et branche unique

- **Travailler exclusivement sur `feat/ordres-v2`.**
- Base : `v2.0`, commit `eb5c302` (push d'audit Codex). Aucun changement des 21 ordres ne doit être commité sur `v2.0` avant validation.
- La SPEC des ordres validés et questions ouvertes est `docs/ordres-v2-preparation.md`.
- Le fichier `python/ordres_conception.py` est un **registre documentaire non exécutable**. Il ne doit pas être assimilé au catalogue actif `python/catalogues.py`.
- Le fichier `.dev/tests/test_ordres_conception_v2.py` protège la séparation (21 entrées désactivées, catégories/contre-ordres, absence d'activation).
- `python/commandement.py` contient déjà l'API préparatoire de comparaison des ordres par donneur. `python/generaux.py:lire_ordres_general` ne lit pour le moment que 2 ou 3 nombres et s'appuie sur la légende historique. **Ne pas introduire des formats G/D ou 4 segments à la hâte** : établir le contrat lexical, sécuriser la validation, puis tester.
- **Aucun des 21 nouveaux effets n'est opérationnel pour le moment.** Les nouvelles entrées ne changent pas le comportement d'une partie.

## Audit ciblé de la reprise (sans supposer que tout est raccordé)

1. Examiner les appels depuis le cycle territorial vers `commandement`, `generaux`, `combats` et les effets de l'ordre historique `1-2`.
2. Déterminer où se trouve l'autorité sur la sélection des donneurs ; confronter les ordres sur **les mêmes unités d'engagement et catégories**, jamais par liste agrégée de généraux.
3. Garder séparées : parsing, légalité, conflit d'ordres, ordre des phases, application de l'effet, rapport privé/public.
4. Raccorder l'API sans faire de l'absence d'ordre adverse une autorisation implicite de tous les contre-ordres hors contexte de confrontation.
5. Introduire les 21 effets par lots, avec état des inconnues et tests déterministes pour chaque lot ; **ne pas inventer** d'arrondis, de destinations, de plafonds, de morts ni d'effets annexes non validés.
6. En priorité : les ordres à effet simple dont le contrat est complet ; ensuite ceux qui déplacent les phases et généraux ; puis les fusions, renforts, Zombies et réanimations qui affectent les objets soldats.
7. Aucune nouvelle activation sans tests du déclenchement, des deux camps, de l'échec, du cumul et de la reprise. Vérifier la non-régression de `1-2`.
8. Codex exécutera à la fin les tests Linux complets et les scénarios sur Raspberry Pi / SSH si possible. Ne pas qualifier les tests de réussis sans exécution.

## Décisions toujours manquantes

- **Muraille humaine :** « bloc Avant perdu » à la défaite signifie-t-il mort, fuite ou autre ? Comment répartir les pertes de la ligne collective ?
- **Réserve stratégique :** fatigue et limite d'interventions d'un même général ; interactions avec la priorité de `QG_nommade`.
- **Dernière charge :** format G/D précis dans la grammaire des ordres, statut exact des soldats relevés dans les fichiers et comportement s'il n'existe pas de flanc choisi chez le général précédent.
- **Gros_poisson :** syntaxe troisième/quatrième champ ; répartition et restitution des identités de soldats.
- **Ralliement :** source concrète des soldats « récupérés » après les pertes de l'allié, identité, blessures, mémoire et destination des renforts à la fin.
- Compatibilité des effets globaux entre eux (priorités, exceptions).

Ces questions sont de véritables décisions de gameplay. Un programmeur ne doit pas les déduire arbitrairement d'un ancien algorithme.

## Bilan des commits de préparation

1. `d1165ff` — 21 fiches et règles communes en documentation.
2. `a3d3716` — registre de conception désactivé.
3. `b7dcc35` — tests de contrat et d'absence d'activation.

Statut : modifications GitHub enregistrées, **tests non exécutés dans WSL par cette session**.

## Raccordement initial effectué après la préparation

- `python/ordres_pipeline.py` convertit les jetons connus et **actifs seulement** en IDs internes, sans regrouper plusieurs généraux et sans exécuter d'effet. Le module écarte volontairement les variantes avec paramètre : leur contrat (position/flanc/ordre) doit être défini pour chaque effet.
- `python/combats.py:resoudre_affrontement_actif` collecte au début de la résolution territoriale un instantané des intentions par général, **sans en faire usage** pour l'instant. La logique historique de `1-2` n'a pas été remplacée.
- `.dev/tests/test_ordres_pipeline_v2.py` teste la non-fusion, le filtrage des ordres indisponibles, le rejet des paramètres non validés et les jetons ambigus.
- Ce raccordement est un **jalon d'architecture**, pas l'intégration des nouveaux effets ni de leur opposition PC. Ne pas prétendre que les catégories de duel fonctionnent déjà en jeu.
- Aucune suite de tests exécutée depuis cette session ; Codex devra les lancer sur WSL à son retour.

### Prochaine implémentation

1. Construire une représentation explicite des intentions de chaque camp avec propriétaire, général donneur, catégorie, cibles et origine QG, sans dépendre des champs de texte libres.
2. Confronter les intentions sur une phase réelle avec une identité de donneur stable, puis produire une décision testable. Attention à ne pas sélectionner le QG à partir d'une donnée joueur falsifiable.
3. Tester les conditions d'opposition et d'absence d'ordre, y compris les catégories individuelles sans adversaire explicite.
4. Unifier uniquement ensuite le chemin historique `1-2` avec la sélection nouvelle, en comparant les résultats d'une même bataille avant/après.
5. Ajouter les effets dont les règles sont closes, un par un. Laisser les autres inactifs, sans hypothèse implicite.

## Seconde étape : API de confrontation pure (non exécutée par le combat)

- `python/ordres_pipeline.py:confronter_intentions` reçoit deux donneurs **explicitement choisis**, une catégorie et les PC **calculés ailleurs**. Elle sélectionne les ordres via `commandement.confronter_donneurs`. Elle n'applique aucun effet et ne choisit pas de QG ou d'adversaire.
- La fonction attend dans chaque donneur `{"general": {..., "caracteristiques": fiche_officielle}}`. **Le moteur territorial ne renseigne pas directement cette clé** : il faudra la construire à partir de `progression.caracteristiques_general` au moment du raccordement, sans accepter une fiche falsifiable du joueur.
- Tests nouveaux : égalité de deux ordres normaux, ordre face à contre-ordre, contre-ordre sans ordre adverse, absence des caractéristiques officielles.
- **Aucun appel de confrontation n'a été ajouté au combat réel.** Celui-ci collecte seulement les intentions. Le raccordement du commandement/QG reste une tâche distincte.
- Commits de cette étape : `b819cf0`, `2f45028`, `ce445a7`. Tests non exécutés dans cet environnement.

### Point d'attention sur le sens de « aucun ordre adverse »

Deux ordres ne se neutralisent qu'à l'intérieur d'une **même confrontation et catégorie**. Si le camp adverse n'a aucun ordre dans cette confrontation, les règles validées autorisent le contre-ordre (et aucun affrontement de PC entre deux ordres normaux n'a lieu). Ne pas comparer un ordre global à un ordre de duel pour l'annuler.

## Troisième étape : donneurs liés aux données officielles

- `python/ordres_pipeline.py:donneurs_officiels` récupère pour chaque donneur ses caractéristiques de `progression.caracteristiques_general` (stockage privé), et non la fiche visible du joueur. Un donneur sans fiche privée est refusé.
- Les donneurs restent distingués par camp, position et général ; l'objet initial n'est pas modifié.
- Tests ajoutés dans `.dev/tests/test_ordres_pipeline_v2.py` : source privée authentique, refus en cas de progression manquante.
- **Toujours aucune activation d'ordre nouveau**, ni appel à `confronter_intentions` depuis `combats.py`. Pour la suite, sélectionner le QG officiellement et déterminer le calcul de PC pertinent à chaque confrontation ; ne pas inférer les donneurs depuis leur seule présence dans `ordre.txt`.
- **Exécution des tests restant à faire par Codex** ; ces commits ont été effectués uniquement via GitHub.

## Quatrième étape : calcul PC des duels, sans déclenchement d'effets

- `ordres_pipeline.points_duel_officiels(general)` relit la fiche moteur privée et la composition physique du général puis délègue au calcul existant `commandement.effectif_general` ; la valeur de `fiche.txt` n'entre pas dans le calcul.
- `ordres_pipeline.confronter_duel_officiel(general_1, general_2, donneur_1, donneur_2)` confronte explicitement les ordres de deux donneurs avec les PC des **généraux engagés**. N'applique pas leurs effets et ne choisit pas de donneurs. Ne pas supposer qu'un QG donneur doit utiliser ses propres PC plutôt que ceux de l'engagé sans décision.
- Tests ajoutés : composition officielle, ignorance de la fiche publique, égalité des PC, refus de progression privée absente.
- **Limite impérative :** pas encore de connexion de cette API à `combat_entre_generaux`. Les autres catégories (globale/individuelle), l'autorisation de QG, les cibles de duel et l'exécution des effets ne sont pas réglées.
- Ne pas fusionner le chantier tant que Codex n'a pas validé les tests et le raccordement en Linux.

## Décision confirmée : PC du QG émetteur pour les duels

- Lorsque le **QG émet un ordre de duel à la place du combattant**, comparer les PC du **général possédant le QG**, PAS ceux du combattant.
- La fonction `confronter_duel_officiel` applique désormais ce principe en calculant les PC de chaque **donneur** par `points_duel_officiels` (qui appelle `commandement.effectif_general` et compte les types d'unités présents).
- **Ne pas confondre** ce calcul avec la formule déjà codée pour les **ordres globaux** dans `commandement.global_armee` : `(2 * PC_QG + somme_PC_autres_strateges) // (2 * max(1, nombre_autres_generaux))`. Conserver cette formule tant qu'aucune autre modification n'a été validée.
- Le choix du QG actif reste externe et doit être lié à la sélection officielle `selectionner_qg` et à sa disparition éventuelle. Il n'est PAS encore connecté au combat.
- Le test `test_qg_donneur_duel_utilise_ses_pc_pas_ceux_du_combattant` protège cette décision.
- Aucun effet des 21 ordres encore activé ; tests ajoutés mais pas exécutés sous Linux dans cette session.

## Cinquième étape : premières formules V2 isolées

- `python/ordres_calculs_v2.py` contient seulement deux calculs purs dont la règle est complète : **Charge suicidaire** (`pertes_du_duel // 4`, pourcentage entier) et **Ralliement** (pour chaque type déjà présent chez le bénéficiaire, `pertes_du_type // 5`).
- `.dev/tests/test_ordres_calculs_v2.py` couvre les seuils, les arrondis et des données invalides. Tests **non exécutés sous Linux**.
- Les fonctions n'ont aucune mutation, tirage aléatoire, attribution d'unités ou application d'effet. Elles **ne sont pas appelées par le combat**. Le tirage de Charge suicidaire interviendra à la fin du seul duel lorsque l'ordre sera correctement activé.
- **Ne pas déduire** les effets « +10 % de moral » et « -1 % par unité cruelle » en points de moral bruts sans confirmer s'il s'agit de points de pourcentage ou d'un facteur multiplicatif. Aucun code de ces bonus n'a été conservé.
- Pour Ralliement, la provenance des pertes, les éventuelles identités, les blessures et le devenir des renforts doivent encore être spécifiés avant toute manipulation des soldats.
- Les commits sont exclusivement sur `feat/ordres-v2`; aucun effet supplémentaire n'est activé.

## Sixième étape : calculs préparatoires supplémentaires (non actifs)

Commits supplémentaires sur **la même branche** :
- `220f1c8`, `370de94` : moral `Discours de la mort` = `moral * 11/10`, rendu en Fraction exacte pour ne pas inventer d'arrondi ; préconditions de Réserve stratégique réutilisables sans compteur ni pénalité de fatigue spécifique ; défaite préalable obligatoire de Dernière charge avec un flanc G/D.
- `eadfc97`, `0004ef6` : Rafale = `archers arrière // 4` tentatives (pas de dégâts immédiats), Spore +1 si Spora-adicte et **0 sous Confinement**, Propagation +2 si Propagafion.
- `7323ac2` : documentation des décisions utilisateur exactes sur le moral multiplicatif et les interceptions répétées.

Toutes ces fonctions sont dans `python/ordres_calculs_v2.py` et leurs tests dans `.dev/tests/test_ordres_calculs_v2.py`. **Aucune n'est appelée par le combat réel**. Les calculs ne sont pas une simulation de combat, ne modifient pas les unités et ne valident pas les cibles.

### Points à confirmer avant d'activer les effets

1. **Moral fractionnaire** : arrondi/plafond et séquence de cumul entre plusieurs multiplicateurs, au moment de la résolution (seule la multiplication +10 % est validée).
2. **Réserve stratégique** : ordre précis des interceptions lorsque les deux camps possèdent une réserve, conditions de fin de tour et sortie du duel si la réserve échoue ; aucune règle de fatigue supplémentaire ne doit être inventée.
3. **Muraille humaine** : disparition des blocs Avant **de la manœuvre** ne signifie pas par défaut élimination définitive des soldats ; les unités prêtées retournent à leur propriétaire.
4. **Gros_poisson et Ralliement** : identité des soldats, transferts, provenance et restitution exacts.
5. **Ciblage QG / G-D** : format final des jetons, validation du destinataire, compatibilité avec le parseur qui accepte encore seulement deux ou trois segments numériques.
6. **Ordres globaux et historiques** : la confrontation QG n'est pas encore raccordée à `1-2`; changer ses conditions peut modifier toutes les batailles et exige un test de non-régression comparatif.

### Reprise et exécution des nouveaux tests

Sur une copie de développement de la branche `feat/ordres-v2`, exécuter en environnement Python compatible les tests de :
- `.dev/tests/test_ordres_conception_v2.py`
- `.dev/tests/test_ordres_pipeline_v2.py`
- `.dev/tests/test_ordres_calculs_v2.py`
- `.dev/tests/test_ordres_confrontation_v2.py`

Puis lancer la suite complète et les scénarios Linux, inspecter l'impact du raccordement sur `1-2`, et vérifier la compilation avant tout merge. **Cette session n'a pas exécuté ces tests sur WSL ou Raspberry Pi.**
