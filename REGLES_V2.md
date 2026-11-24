# Mythodea v2.0 — Progression, étiquettes et QG

Référence des règles validées de la refonte, commune au JcJ et à Survie.
[MYTHODEA_SPEC.md](MYTHODEA_SPEC.md) décrit les autres règles et la persistance ;
[SURVIE_SPEC.md](SURVIE_SPEC.md) décrit le cycle Est ;
[EVOLUTIONS.md](EVOLUTIONS.md) donne les commandes joueur des bâtiments.
Les règles remplacées ne sont pas applicables : pour retracer les décisions
anciennes, consulter l'historique Git du dépôt plutôt qu'un document de règles actif.

## Progression

Trois orientations existent : Stratège (45 %), Instinctif (45 %) et Hybride (10 %).
L'Hybride est indépendant, sans dominante. Au niveau 0, seuls l'orientation et
le trait sont déterminés : 0 PC, 0 moral, aucune étiquette ni évolution.

| Orientation | PC naturels par niveau | Moral naturel aux niveaux pairs | Places actives initiales / maximum |
| --- | --- | --- | --- |
| Stratège | +2 à +4 | Aucun | 1 / 3 |
| Instinctif | Aucun | +1 | 1 / 1 |
| Hybride | +2 à +4 | +1 | 1 / 3 |

Les gains naturels sont indépendants des récompenses. Le moral est plafonné à 100.
Les traits charismatique/leader/inventeur suivent les poids 50/35/15, 50/15/35
et 50/25/25, respectivement pour ces trois orientations.

Chaque niveau non zombie attribue ses gains naturels et sa récompense classique
(roulette ou mémoire de l'École). Chaque multiple de cinq donne **en plus** une
récompense spécifique, puis une seconde roulette lorsque les capacités sont complètes.
Aucune étiquette n'est garantie aux niveaux 5 et 10.

| Palier | Stratège | Instinctif | Hybride |
| --- | --- | --- | --- |
| 5 | Deuxième place active | Étendard normal | Tirage spécifique 50/50 |
| 10 | Troisième place active | Étendard royal | Tirage spécifique 50/50 |
| 15 et 20 | Roulette supplémentaire | Roulette supplémentaire | Tirage spécifique 50/50 |
| 25 et chaque multiple de 5 suivant | Roulette supplémentaire | Roulette supplémentaire | Roulette supplémentaire si toutes les capacités sont débloquées |

Le tirage hybride choisit Stratège ou Instinctif à 50/50. Chaque branche avance
indépendamment : deuxième puis troisième place ; étendard normal puis royal.
Une branche terminée bascule automatiquement vers l'autre, sans perdre la récompense.
La première récompense instinctive donne toujours le normal, même tardivement.
Un parcours complet termine les quatre étapes à 20. Une capacité exceptionnellement
manquante est traitée au prochain palier avant conversion en roulette.
Une place active ne donne aucune connaissance ni amélioration de rang.
Les connaissances ne sont pas plafonnées par les places actives.

Les probabilités de roulette sont inchangées :

| Nature / trait | PC | Moral | Unité | Étiquette |
| --- | ---: | ---: | ---: | ---: |
| Stratège charismatique | 40 % | 10 % | 15 % | 35 % |
| Stratège leader | 35 % | 10 % | 15 % | 40 % |
| Stratège inventeur | 15 % | 10 % | 40 % | 35 % |
| Instinctif charismatique | 10 % | 55 % | 20 % | 15 % |
| Instinctif leader | 10 % | 50 % | 20 % | 20 % |
| Instinctif inventeur | 10 % | 35 % | 40 % | 15 % |
| Hybride charismatique | 30 % | 30 % | 15 % | 25 % |
| Hybride leader | 25 % | 30 % | 15 % | 30 % |
| Hybride inventeur | 20 % | 20 % | 35 % | 25 % |

Chaque ligne totalise 100 %. L'Hybride utilise sa propre ligne.
La récompense PC donne +5 à +10, y compris à l'instinctif ; le moral donne +2 à +4,
plafonné à 100. Aucun plafond de PC n'est prévu par le moteur.
L'unité est choisie parmi les évolutions compatibles et encore inconnues.
L'Hybride accède aux deux orientations par roulette comme à l'École, ainsi qu'à
la Forge avec la technologie 104 et les autres conditions habituelles.
L'étiquette est choisie parmi les entrées inconnues de `ETIQUETTES_COMBAT`,
actuellement toutes compatibles avec les trois orientations, au rang 1.

Une catégorie indisponible est retirée et ses probabilités sont redistribuées
proportionnellement entre les catégories restantes de poids positif. Le moral
à 100, les unités acquises et les étiquettes connues sont exclus. Exemple : chez
l'instinctif charismatique, moral et étiquettes épuisés donnent PC/unité = 10/20,
soit 1/3 et 2/3. Les tirages entiers restent reproductibles à graine fixe.
Si toutes les catégories accessibles sont épuisées, +5 à +10 PC restent le dernier
recours répétable, même pour un instinctif.

Une évolution mémorisée à l'École remplace la roulette du prochain niveau
applicable, y compris aux multiples de cinq ; elle ne remplace jamais le supplément.
Pour un hybride, une mémoire de moral donne +2 à +4 moral et une mémoire de PC
+5 à +10 PC, indépendamment de sa nature ; ses deux gains naturels restent
applicables. Une mémoire devenue incompatible bloque l'attribution
sans perte d'état ; aucun remplacement silencieux n'est effectué.

Deux batailles territoriales personnellement combattues et survécues donnent un
niveau ; trois clôtures de tour avec présence en caserne militaire donnent un niveau par une jauge distincte (entrée du tour incluse).
Seule la jauge déclenchée revient à zéro. Les généraux zombies suivent leur règle
spécifique de capacité, sans ces récompenses ordinaires.

Les généraux zombies et les unités zombies ne bénéficient ni du moral ni des
soins. Les anciennes valeurs de moral et de blessures restent enregistrées,
mais ne permettent aucun sauvetage ni restauration des blessures zombies,
y compris à l’Hôpital et par le Chaman. Les PC et les étiquettes compatibles
restent applicables. Spore (conversion), Propagation (création) et la caserne militaire
territoriale du Bouclier vivant conservent leurs règles spécifiques.

## Étiquettes

### Sélection active

Les **étiquettes connues** et leurs rangs sont conservés dans le profil officiel.
La roulette apprend une nouvelle étiquette sans plafond total de connaissances,
y compris avant le niveau 5 chez l'instinctif. Elle ne l'active pas d'office si
un fichier de sélection existe. Aucune étiquette n'est verrouillée selon son origine.
**Comportement provisoire :** la roulette n'améliore jamais un rang connu ;
l'amélioration par roulette reste une décision ouverte. Lorsque toutes les
étiquettes sont connues, cette catégorie est retirée du tirage. L'amélioration
des rangs reste assurée par l'École selon ses règles existantes.

Dans son dossier, le joueur peut créer `etiquettes_actives.txt` et inscrire
les noms des étiquettes apprises, une par ligne ou séparés par des virgules.
Seules celles choisies contribuent au combat, y compris aux effets du QG.
Une sélection vide désactive tous les effets d'étiquettes.
Le nombre actif est limité aux places effectivement débloquées dans le profil privé :
une au départ, au plus trois pour Stratège et Hybride, une pour Instinctif.
Le moteur refuse les noms inconnus,
les doublons, les dépassements de capacité et les fichiers liés ou non ordinaires.
La capture Survie vérifie ces fichiers avant copie, car une copie physique ferait
perdre la preuve d'un lien physique. Les connaissances et leurs rangs restent
exclusivement ceux du profil officiel privé.
En l'absence de fichier de sélection, les étiquettes connues sont
automatiquement activées dans la limite applicable, pour compatibilité.
La sélection est figée au début de chaque bataille territoriale, comme le QG.
Toute modification du fichier pendant les affrontements reste sans effet sur
cette bataille. Un renfort engagé plus tard fige sa sélection à son premier
engagement, sans recalculer le soutien global initial.

À chaque niveau gagné après zombification, le général zombie conserve son
gain habituel de deux places et, tant qu'il ne connaît pas `mort_vivant`,
dispose d'un tirage indépendant de 20 % pour l'apprendre au niveau 1.
Cette étiquette spéciale dispose d'un emplacement actif supplémentaire au zombie,
**exclusivement réservé à `mort_vivant`**. Sans acquisition ou sans sélection de
`mort_vivant`, aucune étiquette ordinaire supplémentaire n'est autorisée.
Sans fichier de sélection, les premières étiquettes ordinaires connues dans la limite débloquée
sont actives, ainsi que `mort_vivant` si connue, quel que soit son ordre d'acquisition.
Le zombie garde ses deux places de capacité par niveau et n'a aucune roulette ordinaire.

```text
bonus en points de pourcentage = PC × 1/2 × niveau de l'étiquette
valeur finale = valeur contextuelle × max(0, 1 + somme des bonus et malus / 100)
```

Le coefficient 1/2 est fixe, sans multiplicateur lié au niveau du général.
Les calculs emploient `Fraction`, y compris le moral réduit par `cruelle`.
Les pertes et les candidats au sauvetage sont arrondis à l'inférieur à leur étape
habituelle ; les bonus intermédiaires ne sont pas arrondis.
Exemple : base 20, bonus personnel 10 %, soutien 30 % donnent **28**, par addition.

Les bonus de valeur ciblent les étiquettes **réellement présentes** dans
`catalogues.UNITES`, sans déduire une race ou une famille du nom de l'unité.
Les dix cibles sont `infanterie`, `distance`, `cavalerie`, `humain`, `melee`, `orc`,
`mort_vivant`, `noble`, `armure_legere` et `lourde`.
Une unité portant plusieurs cibles bénéficie de la somme des bonus applicables.
`chaman` diminue la valeur des unités Orcs adverses ; `cruelle` diminue le moral
adverse utilisé pour les sauvetages, sans changer le profil permanent.
L'ancienne synergie de moral entre unités cruelles et chamans est retirée.

Le facteur final est borné à **0 %**, jamais négatif, après addition des bonus
et malus. Une valeur positive, même inférieure à 1 %, reste exacte.
Dans les combats ordinaires, la valeur effective sert aussi de résistance :

- valeur nulle et dégâts reçus strictement positifs : décimation du bloc,
  sous réserve des sauvetages existants ;
- valeur nulle et dégâts reçus nuls : aucune perte ;
- deux blocs de valeur nulle : aucune perte des deux côtés ;
- valeur positive : calcul habituel des pertes, sans changement.

Le moteur traite le zéro avant toute division. Les pertes restent simultanées,
sans perte artificielle pour départager un duel. Les limites de résolution et les
sauvetages, blessures et exceptions raciales existants restent applicables.
Cette règle ne redéfinit pas la phase spéciale du Bouclier vivant.

## École des officiers

Six places communes : `village/ecole_officiers/1..6/<joueur>/`.
Le manuel partagé a trois emplacements distincts : `001`, `002`, `003`.
Lecture et écriture exigent chacune un séjour complet, selon les preuves du moteur.

- Une demande de lecture non vide prime sur l'écriture : une seule action par séjour.
  Si cette lecture est invalide, il n'y a pas de repli vers l'écriture.
- Toutes les lectures valides du tour précèdent les écritures. Deux écritures
  concurrentes sur la même mémoire sont refusées ensemble.
- Une étiquette scolaire s'apprend au niveau 1, puis s'améliore d'un niveau par séjour,
  au maximum `1 + niveau_general // 5`. Toutes les étiquettes connues peuvent être
  améliorées, y compris celles attribuées à la création, aux paliers ou par roulette.
- Les limites trois/une portent sur l'activation, sans plafond total de connaissances.
  L'apprentissage scolaire d'une nouvelle étiquette instinctive reste inaccessible
  avant le niveau 5. La capacité d'acquisition scolaire conserve
  `1 + niveau_general // 5`, en comptant uniquement les nouvelles étiquettes
  apprises à l'École. Les attributions automatiques (création, paliers, roulette
  et acquisition zombie) sont exemptées. Une amélioration ne consomme aucune place.
  Atteindre ou dépasser cette capacité n'empêche ni une attribution automatique,
  ni l'École d'améliorer un rang connu admissible ; aucune connaissance n'est retirée.
- Une mémoire d'évolution est gardée jusqu'à son niveau applicable ; une leçon
  d'étiquette est appliquée à la fin du séjour et ne remplace pas cette mémoire.
- Les reçus privés empêchent de traiter deux fois le même séjour.

Les identifiants scolaires sont explicites et permanents :

| ID | Étiquette | ID | Étiquette |
| --- | --- | --- | --- |
| 2001 | infanterie | 2007 | mort_vivant |
| 2002 | distance | 2008 | noble |
| 2003 | cavalerie | 2009 | armure_legere |
| 2004 | humain | 2010 | lourde |
| 2005 | melee | 2011 | chaman |
| 2006 | orc | 2012 | cruelle |

Les évolutions d'unités actives sont 104 à 110 ; 201 désigne les PC et 202 le moral.
Les IDs retirés 1001 à 1005 ne sont jamais réutilisés.
L'écriture d'une étiquette est actuellement permise sans exiger
qu'elle soit déjà connue du rédacteur ; cette condition préexistante n'a pas été
changée pendant l'audit et mérite une décision de conception.

## QG et Messager

Le joueur crée `QG.txt` ou `qg.txt` dans le dossier du général choisi. Leur contenu
est indifférent. Les deux graphies sur le même général comptent une seule fois.
Seuls les Stratèges et les Hybrides non zombies peuvent
être désignés ; une déclaration incompatible est refusée. Aucune comparaison
de PC ne choisit le QG.
Aucun QG signifie aucun effet global. Plusieurs QG du même camp annulent tous
les effets globaux de ce camp pour cette bataille, même si l'un disparaît ensuite.

Seuls les généraux **effectivement engagés** sont inclus : positions actives au
début, y compris les renforts déjà promus. Renforts encore en attente, caserne militaire,
bâtiments et home sont exclus. L'instantané reste le même pendant toute la
bataille territoriale, y compris les cascades Survie. Les renforts engagés plus
tard reçoivent les effets encore actifs ; leurs PC, Messagers ou déclarations QG
ne changent pas l'instantané initial.

Un Messager occupe **cinq places**, vaut **zéro au combat** et ajoute aux seuls PC
globaux du QG `somme(PC des autres alliés engagés au début) // 10`.
Il peut appartenir à n'importe quel général allié engagé. Plusieurs Messagers ne
cumulent pas leur effet ; chaque général contribue une fois. Le QG est exclu de
la somme. Aucun PC permanent n'est modifié.

Le QG bénéficie seulement de ses étiquettes personnelles avec ses PC personnels.
Chaque autre général allié ajoute les soutiens du QG à ses bonus personnels,
sans division entre bénéficiaires. Les malus globaux ciblent le camp adverse.
Quand le QG combat lui-même, ses malus personnels s'appliquent une fois, sans
addition de son propre malus global ni amplification par le Messager.

La destruction complète du QG ou l'acceptation de sa retraite de surnombre retire
immédiatement et irréversiblement les bonus et malus globaux de son camp pour
cette bataille territoriale. La retraite désactive les effets dès son acceptation,
avant le déplacement physique, même différé. Une retraite refusée ne les retire pas.
Les effets personnels des autres généraux et le QG adverse restent actifs.
Il n'y a aucune relève, ni réactivation par un Messager ou un renfort ultérieur.
Les chemins du QG détruit ne sont pas réutilisés. Le prochain territoire dispose
de son propre instantané. `ordre_surnombre.txt` conserve son fonctionnement :
aucune fuite volontaire avant ou pendant un affrontement n'est ajoutée en v2.0.

La désignation exige un fichier ordinaire sans lien symbolique ou physique ;
les deux graphies sont contrôlées. La capture Survie refuse le lien **avant** la
copie, qui ferait sinon perdre la preuve de son existence.

## Étendards

Un seul fichier ordinaire `etendard.txt`, sans lien symbolique ou physique, est
placé dans l'un des quatre blocs du général. Son contenu ne choisit pas son type :
le profil officiel autorise le normal (1) ou le royal (2). Un double placement ou
une capacité absente est refusé. La capture contrôle les liens avant copie.
L'Hybride peut conserver son QG : `QG.txt` reste au niveau du général, avec sa portée
et sa destruction historiques ; l'étendard reste propre à son bloc.

Après sélection habituelle des pertes, le moteur tente d'abord les sauvetages par
le moral et respecte les limites de blessures (vétéran, héroïque et bonus d'unité).
Si le moral échoue, l'étendard absorbe la perte : une fois par unité pour le normal,
deux pour le royal, jamais trois. Un sauvetage par le moral ne consomme rien.
L'absorption n'ajoute ni ne soigne de blessure permanente.

La protection est figée pour toute la guerre territoriale : choc, manœuvres,
frontal, rangé et cascades. Un renfort la fige à son arrivée au combat.
Le compteur individuel ne se partage ni avec une autre unité, ni un autre bloc,
ni un autre général. Modifier ou reconstruire le marqueur en cours de guerre
ne recharge rien. La guerre suivante renouvelle les protections sans soigner.
Un bloc ne subit que les pertes des combats auxquels il participe.

L'anéantissement du bloc détruit immédiatement le marqueur. La capacité reste
acquise ; le joueur peut recréer gratuitement le fichier pendant une préparation
ultérieure. Une capacité royale reconstruit directement un étendard royal.
Les généraux et unités zombies, ainsi que le Bouclier vivant, conservent leurs
mécanismes particuliers et ne reçoivent pas cette protection. Les généraux zombies
ne reçoivent aucune nouvelle récompense spécifique ou supplémentaire.

## Compatibilité et décisions ouvertes

Les états privés existants restent l'autorité. Un général sans profil reste
sans récompense ; une montée explicite ou une désignation QG sans caractéristiques
officielles réclame une migration définie. Les profils existants sont migrés une
seule fois : `stratege_hybride` et `instinctif_hybride` deviennent `hybride`, sans
dominante. Statistiques, unités, traits, connaissances, rangs et apprentissages
sont conservés. Les capacités spécifiques des paliers atteints sont rattrapées ;
les Hybrides tirent chaque étape avec basculement. Aucun gain naturel, aucune
roulette classique ou supplémentaire historique n'est rejoué. Les zombies gardent
leur ancienne capacité active sans recevoir les nouveaux déblocages.
Les champs privés `emplacements_etiquettes_actives`, `niveau_etendard` (0/1/2),
`version_progression=3` et le reçu `migration_orientations` empêchent un nouveau
tirage. La première lecture d'un registre ancien sauvegarde atomiquement la migration
avant utilisation ; les suivantes sont sans écriture.

Les nouvelles connaissances utilisent le dictionnaire `etiquettes` existant ;
une récompense d'étiquette par roulette est renvoyée sous la forme `('etiquette', nom)` et
enregistrée comme les autres récompenses dans les reçus privés existants.
La liste interne `etiquettes_apprises_ecole` conserve uniquement les acquisitions
scolaires pour calculer le quota ; elle n'est pas publiée dans `fiche.txt` et
ne verrouille aucun rang. Les anciennes `etiquettes_permanentes` sont supprimées
du profil normalisé. Leurs noms et les reçus d'attribution automatique permettent
de retrouver les exemptions ; les anciennes récompenses `etiquette_permanente`
restent lisibles dans les reçus, sans être réécrites ni rejouées.
Sans origine retrouvable, une connaissance est comptée comme scolaire. Les noms
et les rangs existants sont conservés, même au-delà des plafonds actuels : seules
les futures acquisitions scolaires et améliorations sont contrôlées.
Hors migration versionnée ci-dessus, le nettoyage reste en mémoire jusqu'à la
prochaine sauvegarde ou publication. `dernier_niveau` et le `bilan` du reçu privé
distinguent gains naturels, récompense classique, supplément et basculement.
Le retour historique de `monter_niveau` conserve la seule récompense classique.
Les anciennes sélections zombies utilisant la place spéciale pour une étiquette
ordinaire supplémentaire sont désormais refusées et doivent être corrigées par
le joueur. Les connaissances restent intactes. Une même graine reproduit les
tirages du nouveau moteur, sans garantir ceux de l'ancienne table de roulette.

À 0 PC, l'étiquette instinctive produit un bonus nul. La roulette peut désormais
lui donner des PC ; aucun PC initial supplémentaire n'est accordé.

À décider explicitement :

- Migration d'une mémoire d'ordre retiré encore en attente.
- Effets sur la résistance spéciale du Bouclier vivant et sur sa phase prioritaire :
  cette phase utilise encore sa formule dédiée, distincte des duels ordinaires.
- Amélioration directe des rangs par roulette : non activée en attendant décision.
- Éventuelles exceptions de moral supplémentaires : aucune n'est ajoutée au cas
  de valeur nulle ; plafonds, fractions de `cruelle`, sauvetages et restrictions
  raciales existants sont conservés.

La validation réelle Raspberry Pi/SSH reste décrite dans
[TESTS_LINUX_SURVIE.md](TESTS_LINUX_SURVIE.md). Une suite WSL réussie ne la remplace pas.
