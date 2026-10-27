# Préparation des ordres V2 — conception, pas activation

Base de travail : branche `feat/ordres-v2`, issue de `v2.0` après le commit d'audit `eb5c302`.
Un ordre reste **désactivé** tant qu'il n'est pas intégré et testé. Le bilan actuel
des activations est dans `ordres-v2-reprise-codex.md` ; le présent document conserve
les décisions de conception, y compris celles des effets encore réservés.
La vérification finale (suite Linux complète, WSL/Raspberry Pi) est confiée à Codex.

## Contrats courants du lot B — 27 octobre 2026

Cette section et les SPEC à jour priment sur les hypothèses historiques ci-dessous.

- **Gros_poisson** : Duel, ID réservé 1017, `2-6-position_beneficiaire-position_preteur`.
  Le QG choisit les positions et peut être l'un des participants. Fusion partielle
  des seuls couples bloc/type communs ; blocs absents et types différents ignorés,
  sans annuler les autres prêts. Aucune unité ni bloc créé. Sans homologue : aucun
  effet, avec indication au rapport. Les non-prêtés gardent leur commandement.
  Les engagés utilisent temporairement celui du bénéficiaire, conservent UUID,
  propriétaire, XP, blessures et fatigue ; victimes aléatoires sans quota par
  propriétaire, puis retour des survivants à leurs origines. Le prêteur conserve
  son tour normal. Aucun contournement de la politique des généraux Zombies,
  de la restriction raciale des unités, de l'apprentissage ou des permissions.
- **Muraille** : blocs Avant distincts, avec leurs statistiques d'origine,
  contre l'Avant adverse. Score après protections et moral : ennemis effectivement
  éliminés moins alliés effectivement perdus. Meilleur score, puis position
  d'origine selon l'ordre commun, puis hasard reproductible en cas d'égalité
  restante. Recalcul après chaque engagement contre les forces restantes.
  Aucun fichier, XP, blessure, sauvegarde ou tirage réel modifié par les simulations.
  Victimes tirées dans le seul bloc engagé. Exclusion des Avant participants de
  la manœuvre, du QG sous QG_nommade et du général de Réserve stratégique.
  Les Avant vivants d'un général vaincu continuent tant que l'effet existe.
  Après le territoire, retour des survivants sans général au village d'origine,
  même si leur camp a perdu ; `unites_sans_general` demeure à construire au lot C.
  Disparition du QG : fin des transmissions après le duel en cours, dissolution,
  circuit normal des survivants, aucune nouvelle désignation. Matrice du lot A
  conservée, dont les incompatibilités Attaque frontale et Retrait_tactique.
- **Général Zombie** : politique issue du seul état privé existant, nature
  initiale conservée. Seuls Spora-adicte et Propagafion sont apprenables, quelle
  que soit cette nature ; aucun de ces deux ordres pour un non-Zombie. Propagafion
  appris est exécutable même par un instinctif sous les conditions QG communes.
  Spora-adicte est mémorisable mais son ciblage et son exécution restent désactivés.
  Récompense : 85 % capacité +2, 15 % ordre puis 50/50 ; doublon = reprise du
  processus entier. Poids conditionnels 170:15 avec un ordre connu, capacité
  automatique avec les deux. Les anciennes places acquises sont conservées,
  sans tirage rétroactif et sans cumul de deux systèmes de progression.
- **Ralliement** : morts réanimés, UUID/blessures/XP conservés, bénéficiaire =
  allié suivant ; quotas `pertes_du_type // 5` seulement pour ses types présents.
  Retour à l'origine si le général existe ; aucune résurrection activée.
- **Dernière charge** : précédent général obligatoirement vaincu, flanc G/g ou
  D/d, flanc absent sans effet. Morts relevés et fatigués au choc seulement,
  exclus de la manœuvre, survivants définitivement morts après leur charge.

### Travail préparatoire disponible

`GroupeTemporaire.selections_gros_poisson()` sélectionne les homologues partiels
avec contrôles des profils privés et des unités sans cerveau ; le motif sans
effet est prêt pour le futur rapport. `fatigues_origine()` conserve une valeur
par UUID vivant. Le parseur lit les quatre champs réservés ; le catalogue et le
pipeline maintiennent l'ordre désactivé. Ces fonctions ne remplacent pas les
contrôles du donneur QG, des positions effectivement actives et de la confrontation.

La simulation Muraille couvre le calcul commun, le moral d'origine et les
limites individuelles de blessures/XP. Les tirages et tests de sauvetage sont
partagés avec le combat réel. La sélection suivante relit et recalcule les
scores ; elle ne programme pas toute la succession des duels. Les contextes
d'ordres par candidat et les capacités Bouclier/Spore/Propagation/soutiens
restent à raccorder ; les cas non simulés sont refusés explicitement. Il faut
aussi réaliser le circuit du lot C avant toute activation de Muraille.

### Questions de gameplay encore indispensables

1. **Gros_poisson, fatigue hétérogène** : la résistance et les dégâts partagent
   actuellement la même valeur effective. Les valeurs de fatigue peuvent être
   conservées par UUID, mais la règle de résistance d'un mélange frais/fatigués
   contre un même type reste à fixer. Ni moyenne ni sous-duels arbitraires.
2. **Gros_poisson, capacités** : formation de référence pour le seuil de cavalerie
   lourde et les bonus de composition/raciaux ; traitement des soutiens admis.
   Conversion d'un soldat prêté par Spore adverse : origine/bloc après conversion
   à définir avant de permettre ce transfert dans la vue temporaire.
   Les Zombies/Boucliers sont exclus du prêt par les restrictions confirmées, pas prêtés
   par une exception de Spore. Même bénéficiaire et prêteur : aucune fusion
   exécutée tant que cette désignation n'est pas définie.
3. **Mémoire Zombie** : la réponse reçue précisait les restrictions de Gros_poisson,
   sans trancher la priorité d'une mémoire scolaire sur le tirage 85/15. La base
   conserve cette mémoire et applique le tirage ; aucune nouvelle priorité ajoutée.
4. **Ralliement** : éligibilité et sélection des morts, état physique au seuil
   de blessure mortelle, bloc d'accueil si plusieurs conviennent, durée du prêt,
   destination si le général d'origine n'existe plus.
5. **Dernière charge** : sélection des morts et blessures à la relève.

Les modalités de stockage et l'orchestration des phases sont des travaux
techniques restant à faire, pas des nouvelles questions de gameplay.

## Règles transversales validées

- Les ordres se confrontent par **catégorie et par donneur**. Ne pas fusionner les ordres de généraux différents pour former un cumul.
- Ordre normal contre ordre normal : seuls les ordres du camp gagnant aux PC sont retenus ; en cas d'égalité, ils sont annulés.
- Ordre normal contre contre-ordre : les deux peuvent fonctionner.
- Un contre-ordre fonctionne si ses PC sont inférieurs **ou** s'il n'y a pas d'ordre adverse dans la confrontation concernée.
- Les ordres compatibles **du même général** peuvent se cumuler, mais jamais un ordre normal et un contre-ordre du même donneur.
- Les incompatibilités propres à chaque effet priment sur le cumul par défaut.
- Les effets réservés/non programmés ne doivent pas être activés par simple ajout au catalogue.
- Pour les ordres de duel avec ciblage explicite du QG, le chiffre de cible est une **position** de général, pas son identifiant. Les nouveaux formats spéciaux restent à définir exactement.

## Décisions définitives de reprise — 26 octobre 2026

Ces décisions remplacent les anciennes hypothèses contradictoires ci-dessous.
La matrice complète est dans `MYTHODEA_SPEC.md`, section « Compatibilité des
formations ». Les six paires interdites s'annulent mutuellement au sein du camp,
sans PC internes, en conservant les autres ordres valides. Toutes les paires
conflictuelles sont relevées avant toute annulation ; chaque motif apparaît au
rapport. Les huit paires compatibles n'autorisent pas les autres par défaut.

Entre camps, `1-2` opposé à On_melange utilise les donneurs QG et la formule
globale existante : le plus fort impose son schéma, l'égalité annule les deux.
L'annulation interne précède cette confrontation. La migration du frontal est
limitée à cette opposition ; aucun départage nouveau n'est étendu aux autres cas.

QG_nommade a la priorité de placement : son général est retiré des autres schémas,
du frontal, de Muraille humaine (contributions comprises) et de Réserve stratégique
(interceptions comprises), puis combat en dernier. Les places libres ne sont pas
réorganisées. Avec Retrait_tactique, le général en retrait vient juste avant lui.
La réserve stratégique ne contribue pas à Muraille humaine ; elle intercepte
seulement au combat rangé avant son tour normal, puis combat normalement à ce tour.
Réserve stratégique et Retrait_tactique conservent chacun leur effet, sans fatigue
supplémentaire. La compatibilité ne lève pas les restrictions de donneur,
catégorie, apprentissage et mélange ordre/contre-ordre. Pour_l'honneur reste
non cumulable avec les autres ordres, sans exception validée.

Charge suicidaire : les survivants humains rejoindront `unites_sans_general`,
dans un groupe distinct par événement et avec leur propre compteur, à destination
de la réserve du village d'origine. Délai commun de repli/distance, conservation
des identités, blessures et expériences. À zéro, réaffectation manuelle des
dossiers vers les blocs d'un général présent dans sa réserve, sous les restrictions
ordinaires de capacité, type et permissions. Pour le bot, les survivants quittent
définitivement la bataille : aucun village ni réserve de bot n'est créé. Le calcul
reste `pertes_du_duel // 4` %, avec deux tirages indépendants et mort simultanée
possible. Ces règles sont validées ; leur persistance et leur audit relèvent du lot C,
pas d'une activation par les seules fonctions de calcul.

La destruction du QG laisse les ordres transmis actifs jusqu'à la fin du duel.
Aucune transmission ultérieure, aucun remplacement, aucune réactivation si le
bloc est repeuplé. Le mécanisme existant `qg.txt` est conservé.

## Lot B — préparation et décisions bloquantes, 26 octobre 2026

Le socle `soldats.participation_temporaire()` représente les soldats réels par
références, sans déplacement physique. Il fournit les sélections par bloc/type,
les bilans par origine, les pertes communes avec moral explicite et l'inscription
explicite au comptage territorial. La fermeture ne restaure ni mort ni blessure.
Les UUID absents ou détruits ne deviennent jamais des renforts par cette API.

Les quatre ordres ci-dessous restent hors catalogue exécutable. Aucun jeton ni
paramètre supplémentaire n'est attribué. Les tests techniques de groupes ne
valident pas implicitement une politique de pertes pour un ordre.

| Ordre | Préparation disponible | Décisions encore bloquantes |
| --- | --- | --- |
| Gros_poisson | Index par même bloc/type, vue homogène, pertes communes et bilan par origine ; test du commandement bénéficiaire. | Catégorie/jeton, blocs non concordants, capacités spéciales et fatigue hétérogène (détails ci-dessous). |
| Muraille humaine | Filtre des exclusions par identité ; `combats.previsions_avant_muraille()` réutilise le calcul numérique commun, sans mutation ni classement. | Cibles simulées, critère/égalité, recalcul, survivants après défaite territoriale ou fin anticipée de la muraille. |
| Ralliement | Quantités conservées : `pertes_du_type // 5`, uniquement pour les types du bénéficiaire. | Sélection des morts, état physique de réanimation, blocs d'accueil et survivants sans général d'origine. |
| Dernière charge | Défaite préalable, G/g ou D/d ; effectif éligible nul => aucun effet. | Sélection des morts et blessures à la relève ; attribution des jetons avant extension du parseur. |

### Contrats reçus après acaba3e — décisions faisant foi

Ces décisions remplacent les descriptions antérieures contradictoires, notamment
la fusion des Avant de Muraille et l'ambiguïté sur la provenance des réanimés.

- **Gros_poisson** : le QG désigne deux alliés, bénéficiaire (champ 3) et prêteur
  (champ 4), par leurs positions. Il peut lui-même occuper un de ces rôles.
  Forme demandée `1-x-position_beneficiaire-position_preteur`. Seuls même bloc
  et même type sont regroupés. Statistiques et bonus de commandement du
  bénéficiaire remplacent ceux du prêteur pendant l'engagement ; blessures,
  fatigue individuelle, états persistants, UUID, XP et propriétaire restent.
  Pertes aléatoires parmi les engagés, sans quotas par propriétaire. Après le
  duel, survivants à leur général et bloc exacts d'origine ; prêteur encore
  autorisé à combattre à son tour normal. Aucun mort restauré.
- **Muraille** : succession des blocs Avant originaux, chacun avec son général,
  ses statistiques et bonus. Aucun mélange des types ni fusion des Avant.
  Simuler les confrontations sans effet permanent, puis engager les blocs
  selon leur efficacité jusqu'à victoire ou défaite de tous. La formule
  d'efficacité et le départage restent ouverts. Seul le bloc actuellement
  engagé subit les pertes, avec victimes aléatoires en son sein. Le général
  vaincu ne tue pas ses soldats Avant survivants : ils restent dans la muraille
  tant qu'elle existe. À la victoire territoriale, ceux sans général suivent
  le retour `unites_sans_general` déjà défini (infrastructure du lot C à réaliser).
  À la disparition du QG, les effets s'arrêtent après le duel en cours, sans
  remplacement. Phases, restitution et exclusions QG_nommade/réserve conservées.
  Compatible avec On_melange, QG_nommade et Réserve stratégique ; incompatible
  avec Attaque frontale et Retrait_tactique, avec annulation mutuelle du camp.
- **Ralliement** : morts réanimés avec leurs UUID, blessures et XP conservés.
  Bénéficiaire temporaire = général allié suivant. Les survivants retournent
  au général d'origine s'il existe. Aucune réanimation réelle avant définition
  de l'état physique, de la sélection et des destinations manquantes.
- **Dernière charge** : morts du flanc restaurés, fatigués, à la place du flanc
  correspondant du général suivant au seul choc. Flanc absent/sans éligible :
  aucun effet, jamais de bascule. G/g et D/d admis, formes personnelle et QG
  proposées acceptées sous réserve de la grammaire/du jeton final. Tous les
  survivants de cette charge meurent définitivement après le choc ; aucun ne
  participe à la manœuvre. Défaite préalable obligatoire conservée.
- **Généraux Zombies** : seuls Spora-adicte et Propagafion sont recevables ;
  aucun autre ordre V2 ne peut être appris ou exécuté. Le profil privé fait foi.
  Cette restriction ne retire ni capacité raciale ni soldat Zombie d'un effet
  collectif allié par défaut. La progression sans récompense de niveau reste
  inchangée. L'éventuelle voie d'apprentissage des deux exceptions doit rester
  distincte de l'autorisation de les recevoir d'un QG extérieur.

### Questionnaire restant — propositions, pas règles acquises

**Gros_poisson**

1. Le catalogue exécutable n'a **aucun jeton attribué** à Gros_poisson. La
   conception le classe Duel (`2-…`), tandis que la forme demandée commence
   par `1-…` (Globale). Confirmer la catégorie et le jeton : cela détermine aussi
   la confrontation des PC. Aucun identifiant n'est inventé dans cette étape.
2. Bloc absent ou type différent : laisser ce bloc hors du prêt, ou invalider
   l'ordre entier ? La première proposition permet une fusion partielle ; la
   seconde refuse toute formation non concordante. Même bénéficiaire/prêteur :
   confirmer le rejet de cette désignation, sans duplication.
3. Capacités spéciales : lors d'une conversion Spore, qui récupère le soldat
   et dans quel bloc ? Comment compter une formation lourde, les bonus liés à
   la composition et un Bouclier vivant prêté ? Garder les mécanismes communs
   exige de préciser leur formation de référence, pas de les désactiver.
4. Le moteur applique actuellement la fatigue par général/bloc. Confirmer la
   contribution séparée des soldats frais/fatigués dans une même formation
   prêtée, avec le commandement du bénéficiaire. Ne pas imposer une fatigue
   commune qui effacerait l'état des prêteurs.

**Muraille humaine**

1. Quelles forces adverses simuler (Avant opposé seulement, ou autres blocs) ?
   Quel critère exact, puis quel départage ? Propositions : priorité aux pertes
   infligées, aux survivants conservés, ou ordre explicite du créateur ; aucune
   formule ni pondération retenue. Préciser si le classement est recalculé
   après chaque engagement réel ou fixé avant la première confrontation.
2. En cas de défaite territoriale, où vont les Avant survivants sans général ?
   Décès, capture ou repli seraient des règles différentes : aucune n'est choisie.
3. Si le QG disparaît et que la muraille cesse après le duel, quelle destination
   immédiate pour les survivants dont le général a déjà disparu ? La durée de
   l'ordre est fixée ; le stockage et la disponibilité de ces soldats restent
   nécessaires pour éviter disparition ou prolongation implicite de la muraille.

**Ralliement**

1. Quels morts sont éligibles et comment choisir les individus jusqu'au quota
   de chaque type : tirage, priorité d'XP ou autre critère explicite ?
2. Quel état physique autorise la réanimation en conservant les blessures,
   notamment si leur seuil mortel est atteint ? Ne pas guérir implicitement.
3. Quel bloc d'accueil si plusieurs blocs du bénéficiaire ont le même type ?
   Préciser la durée du prêt et le moment du retour.
4. Où vont les survivants si le général d'origine n'existe plus ? Aucun retour
   vers un dossier disparu ni transfert définitif ne sera déduit du seul quota.

**Dernière charge**

1. Quels morts du flanc sont éligibles et comment les sélectionner ?
2. Quelles blessures ont-ils à la relève, particulièrement au seuil mortel ?
   UUID et état ne doivent pas être reconstruits arbitrairement.

Les prévisions numériques préparées ne sont pas encore une simulation complète :
elles donnent les effectifs avant moral et capacités hors `combat_bloc`, avec
les bonus présents dans le contexte fourni. Elles ne choisissent pas de cible,
ne classent pas les blocs, ne tirent pas de victimes et n'émettent aucun rapport.
Le contexte de chaque commandement d'origine et les capacités doivent encore
être intégrés après définition du contrat de simulation.

### Raccordement technique après décisions

Les responsabilités ci-dessous sont des travaux d'intégration, pas de nouvelles
règles à demander :

- Le pipeline existant doit authentifier le donneur, ses apprentissages, son
  camp, les paramètres et la confrontation avant d'ouvrir un groupe.
- Le pilote de combat doit fournir les sélections et exclure toute double
  utilisation des mêmes soldats dans les vues de la phase. Les dossiers
  d'origine restant présents, une simple relecture du général ne suffit pas.
- Les effets définissent la durée du prêt et les phases concernées. Muraille
  retire les Avant de la manœuvre ; Dernière charge rend au général suivant son
  flanc normal pour la manœuvre. La fermeture technique d'une vue ne joue aucune
  de ces règles à elle seule.
- Le calcul de blocs, les permissions, les pertes, les capacités d'unités, les
  rapports et la publication doivent continuer à utiliser le moteur commun.
  La vue actuelle refuse les changements d'origine/type : l'intégration devra
  prendre explicitement en charge les transferts réels déjà prévus par Spore,
  sans les confondre avec la restitution d'un prêt.
- L'expérience des soldats engagés utilise les reçus territoriaux existants ;
  le crédit d'affrontement personnel d'un général reste distinct. Les scénarios
  complets de chacun des quatre ordres devront précéder son activation.

## Catalogue de conception (18 ordres du brouillon JSON)

Archive de conception : pour les quatre ordres du lot B, les contrats reçus
après `acaba3e` ci-dessus priment sur les descriptions et questions ci-dessous.

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
| Rafale | Individuelle | Non | Avant le choc initial et la priorité du Bouclier : ⌊archers Arrière / 4⌋ tirs ; cibles aléatoires, armure lourde immunisée, sauvetage habituel par le moral. |
| Cruelle | Duel | Non | Juste avant le combat : moral adverse × (100 − unités cruelles de l'armée du donneur) / 100, sans arrondi intermédiaire. |
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
Il peut intercepter de nouveau tant qu'il lui reste des unités, sans pénalité
de fatigue supplémentaire propre à l'ordre. Restent à préciser la coexistence
de réserves adverses, l'échec d'une interception et la priorité face à QG_nommade.

### Dernière charge — Duel, contre-ordre

Le général précédent est vaincu. Pour le choc initial du général suivant, **les unités vaincues du flanc G ou D du général précédent** se relèvent pour une dernière charge en état de fatigue, à la place du flanc correspondant du général suivant.
À la manœuvre elles disparaissent définitivement du combat, même si elles gagnent le choc initial ; la formation normale du général suivant revient. Les pertes subies durant l'ultime charge restent réelles.
Un seul flanc doit être désigné : `G` ou `D`. Format de jeton exact à fixer avec le parseur existant et la sélection du donneur.

## Questions et garde-fous avant codage des effets

1. **Ne pas interpréter** « perdu » de Muraille humaine comme mort définitive sans validation.
2. Définir les cas limites de Réserve stratégique (réserves des deux camps, échec d'interception, positions et QG).
3. Déterminer les priorités exactes entre plusieurs ordres de modification du déroulement et leurs incompatibilités.
4. Gros_poisson : conserver l'identité, le propriétaire, les blessures, l'expérience et la restitution ; clarifier ses 3e et 4e paramètres.
5. Ralliement : vérifier la provenance/identité des renforts, notamment lorsqu'ils sont issus de pertes, et leur restitution éventuelle.
6. Appliquer les arrondis plancher seulement là où ils ont été validés. Charge suicidaire utilise les pertes du **seul duel**.
7. Faire passer tests ciblés puis suite Linux complète et parties déterministes avant activation.
8. Mettre le site, le Bestiaire et le simulateur à niveau **après** stabilisation des règles exécutables.

Cette note est une photographie des décisions prises et des questions ouvertes ; elle ne modifie aucune règle active du moteur.

## Contrats validés pendant l'intégration

- QG : `qg.txt` créé par le joueur dans son général, contenant un nom de bloc
  existant et non vide (`avant`, `droite`, `gauche`, `arriere`). Tous les généraux
  peuvent en porter, y compris les Instinctifs. Une seule déclaration valide par
  camp devient officielle ; plusieurs déclarations annulent tous les QG du camp.
  Aucun départage par PC : cette décision remplace l'ancienne sélection du plus
  puissant. Aucun remplacement du QG détruit pendant la bataille. Les ordres
  restent dans `ordre.txt`, soumis à leur apprentissage et à la nature du donneur.
  Le duel utilise les PC du donneur QG ; le global conserve `global_armee`.
  Après destruction du QG pendant un duel, les ordres déjà transmis restent
  actifs jusqu'à la fin de ce duel ; aucun nouvel ordre n'est ensuite transmis.
- Rafale : tirs juste avant le choc initial, `archers_arriere // 4`, cibles
  aléatoires éligibles, immunité des unités lourdement blindées. Le moral
  habituel protège les victimes. Rafale ignore la priorité de protection du
  Bouclier vivant, sans désactiver les autres règles défensives.
- Cruelle : réduction multiplicative exacte, `PM * (100 - nombre_cruelles) / 100`.
  Exemple confirmé : 50 PM et 10 unités cruelles donnent 45 PM, pas 40.
- Progression : tirage uniforme parmi les ordres éligibles lorsque la catégorie
  ordre est choisie. Pas de pondération interne ; générateur injectable avec seed.
- Charge suicidaire : deux tirages indépendants si les deux généraux possèdent
  l'ordre, décès simultanés possibles. Les soldats survivants ne sont pas tués.
  Leur repli `unites_sans_general` doit conserver toutes leurs données dans un
  groupe distinct par événement, vers la réserve de leur village d'origine,
  avec le délai de distance existant et un compteur indépendant par groupe.
  Au compteur nul, la réaffectation est manuelle, sans nouvelle commande ni
  affectation automatique. Les survivants du bot sont retirés définitivement de
  la bataille, sans base créée. L'inventaire et l'audit des groupes humains hors
  général restent à implémenter au lot C selon la décision définitive ci-dessus.
- Choca_fuite : utiliser la retraite Survie existante immédiatement après le
  choc initial. Les règles existantes excluent la retraite automatique au village.
  Ne pas donner de nouveaux ordres spéciaux aux bots.

## Clarifications ultérieures validées

- **Muraille humaine :** les unités de blocs d'autres généraux engagées temporairement dans la formation collective **retournent à leur général d'origine** après l'intervention. Les pertes éventuelles ne sont pas annulées. Cela ne résout pas à lui seul l'état exact des unités du général vaincu ni la répartition des pertes collectives : ne pas les inventer.
- **Dernière charge :** déclenchement interdit si le général précédent **n'a pas perdu** son duel. La défaite de ce général est une condition nécessaire, pas seulement une condition de disponibilité du flanc. La règle de retour des unités de Muraille humaine ne s'applique pas automatiquement à Dernière charge.

### Muraille humaine — précision sur les phases (25 octobre 2026)

- L'ordre vise à favoriser le **choc initial**, puis à faire se dérouler **la manœuvre sans les blocs Avant des deux camps**.
- Les unités d'autres généraux engagées temporairement pour constituer la ligne commune retournent à leur général d'origine après leur intervention, sans effacer les pertes subies.
- Les unités des blocs Avant engagés dans le choc initial « disparaissent » pour la suite de cet affrontement : **elles n'interviennent plus en manœuvre**, même si elles ont gagné le choc initial. Ne pas inventer une participation ultérieure dans ce duel.
- La disparition du combat n'est pas automatiquement une mort permanente ou une destruction des fichiers des soldats : cette conséquence n'a pas encore été explicitement fixée.
- La répartition exacte des pertes dans la ligne collective et le traitement des unités qui reviennent à leur général restent à tester/définir sans hypothèse implicite.

## Décisions additionnelles validées (25 octobre 2026)

- **Discours de la mort** : bonus de **10 % du moral actuel**, **multiplicatif** et cumulable avec les autres bonus futurs. Ex. 30 PM devient 33 PM ; ce n'est **pas** +10 points de moral. Aucun arrondi intermédiaire ne doit être inventé (31 PM devient provisoirement 34,1 avant règle générale d'arrondi).
- **Réserve stratégique** : le général désigné peut réintervenir **autant de fois que nécessaire**, tant qu'il dispose encore d'unités. Son intervention vise à finir le général adverse qui vient de gagner contre son vis-à-vis ; il se retire ensuite pour laisser les deux généraux suivants se confronter normalement. Ne **pas** imposer une nouvelle règle de fatigue à cet ordre : le joueur ne l'a pas demandée. Les effets de fatigue déjà inhérents au combat, s'ils sont applicables, restent du ressort des règles générales et ne doivent pas être supposés nouveaux.
- **Dernière charge** : il est obligatoire que le général allié précédent ait perdu ; sinon pas de déclenchement. Une seule option de flanc, G ou D.
