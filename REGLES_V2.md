# Mythodea v2.0 — Progression, étiquettes et QG

Référence des règles validées de la refonte, commune au JcJ et à Survie.
[MYTHODEA_SPEC.md](MYTHODEA_SPEC.md) décrit les autres règles et la persistance ;
[SURVIE_SPEC.md](SURVIE_SPEC.md) décrit le cycle Est ;
[EVOLUTIONS.md](EVOLUTIONS.md) donne les commandes joueur des bâtiments.
Les décisions remplacées restent consultables dans
[l'historique](HISTORIQUE_REGLES.md), sans être des règles actives.

## Progression

Les natures à la création sont stratège (45 %), instinctif (45 %), stratège hybride
(5 %) et instinctif hybride (5 %). L'orientation principale d'un hybride est celle
de son préfixe ; les apprentissages croisés ne changent ni sa nature ni son trait.

| Règle | Stratège, y compris hybride | Instinctif, y compris hybride |
| --- | --- | --- |
| PC initiaux | 11 à 20 | 0 |
| Moral initial | 0 | 0 |
| Gain naturel | +2 à +4 PC à chaque niveau | +1 moral aux niveaux pairs |
| Récompense statistique native | Maîtrise du commandement : +5 à +10 PC | Force de caractère : +2 à +4 moral |
| Étiquettes permanentes | Création, niveau 5, niveau 10, si place libre | Niveau 5, si place libre |
| Maximum total d'étiquettes | 3 | 1 |

Le moral est plafonné à 100. Les étiquettes de palier sont de niveau 1 et ne sont
pas modifiables à l'École. Si la limite est déjà atteinte, le palier utilise la
roulette normale. Le stratège utilise donc la roulette aux niveaux 15, 20, etc.,
l'instinctif à tous les niveaux sauf son éventuelle attribution au niveau 5.

Les traits natifs suivent les poids 50/35/15 (charismatique/leader/inventeur)
chez le stratège et 50/15/35 chez l'instinctif. Les **poids** de la roulette sont :

| Orientation / trait | Statistique native | Unité |
| --- | ---: | ---: |
| Stratège charismatique | 60 | 10 |
| Stratège leader | 20 | 10 |
| Stratège inventeur | 20 | 60 |
| Instinctif charismatique | 60 | 25 |
| Instinctif leader | 20 | 20 |
| Instinctif inventeur | 20 | 70 |

Ces poids sont normalisés sur les catégories encore accessibles ; ce ne sont pas
des pourcentages sur 100. Les anciens poids d'ordres sont supprimés. Par exemple,
60/10 donne une probabilité de 6/7 pour les PC et de 1/7 pour une unité.
Une évolution d'unité déjà acquise est exclue. Le moral à 100 est exclu.
Si toutes les catégories accessibles sont épuisées, +5 à +10 PC restent le dernier
recours répétable, même pour un instinctif.

Une évolution mémorisée à l'École remplace la roulette du prochain niveau
applicable. Elle est conservée lorsqu'un palier attribue une étiquette permanente.
Pour un hybride, une mémoire de moral donne +2 à +4 moral et une mémoire de PC
+5 à +10 PC, indépendamment de sa nature ; son gain naturel reste celui de son
orientation principale. Une mémoire devenue incompatible bloque l'attribution
sans perte d'état ; aucun remplacement silencieux n'est effectué.

Deux batailles territoriales personnellement combattues et survécues donnent un
niveau ; trois séjours complets en réserve donnent un niveau par une jauge distincte.
Seule la jauge déclenchée revient à zéro. Les généraux zombies suivent leur règle
spécifique de capacité, sans ces récompenses ordinaires.

## Étiquettes

### Sélection active

Dans son dossier, le joueur peut créer `etiquettes_actives.txt` et inscrire
les noms des étiquettes apprises, une par ligne ou séparés par des virgules.
Seules celles choisies contribuent au combat, y compris aux effets du QG.
Une sélection vide désactive tous les effets d'étiquettes.
Le stratège (et son hybride) peut activer au plus trois étiquettes,
l'instinctif (et son hybride) une seule. Le moteur refuse les noms inconnus,
les doublons, les dépassements de capacité et les fichiers liés.
En l'absence de fichier de sélection, les étiquettes connues sont
automatiquement activées dans la limite applicable, pour compatibilité.
La sélection est figée au début de chaque bataille territoriale, comme le QG.
Toute modification du fichier pendant les affrontements reste sans effet sur
cette bataille. Un renfort engagé plus tard fige sa sélection à son premier
engagement, sans recalculer le soutien global initial.

À chaque niveau gagné après zombification, le général zombie conserve son
gain habituel de deux places et, tant qu'il ne connaît pas `mort_vivant`,
dispose d'un tirage indépendant de 20 % pour l'apprendre au niveau 1.
Cette étiquette spéciale offre un emplacement actif supplémentaire au zombie
et ne retire pas ses étiquettes ordinaires.

```text
bonus en points de pourcentage = PC × 1/2 × niveau de l'étiquette
valeur finale = valeur contextuelle × (1 + somme des bonus et malus / 100)
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

Le code conserve son plancher préexistant de 1 % pour la valeur après malus,
afin d'éviter une division par zéro. Le choix d'équilibrage à 100 % de malus ou
au-delà reste à confirmer ; l'audit ne le modifie pas.

## École des officiers

Six places communes : `village/ecole_officiers/1..6/<joueur>/`.
Le manuel partagé a trois emplacements distincts : `001`, `002`, `003`.
Lecture et écriture exigent chacune un séjour complet, selon les preuves du moteur.

- Une demande de lecture non vide prime sur l'écriture : une seule action par séjour.
  Si cette lecture est invalide, il n'y a pas de repli vers l'écriture.
- Toutes les lectures valides du tour précèdent les écritures. Deux écritures
  concurrentes sur la même mémoire sont refusées ensemble.
- Une étiquette scolaire s'apprend au niveau 1, puis s'améliore d'un niveau par séjour,
  au maximum `1 + niveau_general // 5`. Les permanentes sont verrouillées.
- Les limites totales sont trois étiquettes pour le stratège et une pour l'instinctif.
  Aucune première étiquette scolaire instinctive avant le niveau 5.
  La capacité scolaire suit aussi `1 + niveau_general // 5`, hors permanentes.
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
L'écriture d'une étiquette non permanente est actuellement permise sans exiger
qu'elle soit déjà connue du rédacteur ; cette condition préexistante n'a pas été
changée pendant l'audit et mérite une décision de conception.

## QG et Messager

Le joueur crée `QG.txt` ou `qg.txt` dans le dossier du général choisi. Leur contenu
est indifférent. Les deux graphies sur le même général comptent une seule fois.
Toute nature peut être désignée ; aucune comparaison de PC ne choisit le QG.
Aucun QG signifie aucun effet global. Plusieurs QG du même camp annulent tous
les effets globaux de ce camp pour cette bataille, même si l'un disparaît ensuite.

Seuls les généraux **effectivement engagés** sont inclus : positions actives au
début, y compris les renforts déjà promus. Renforts encore en attente, réserve,
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

La destruction complète du QG retire irréversiblement les bonus et malus de son
camp pour cette bataille. Les bonus personnels alliés et le QG adverse restent
actifs. Il n'y a aucune relève. Les chemins du QG détruit ne sont pas réutilisés.

La désignation exige un fichier ordinaire sans lien symbolique ou physique ;
les deux graphies sont contrôlées. La capture Survie refuse le lien **avant** la
copie, qui ferait sinon perdre la preuve de son existence.

## Compatibilité et décisions ouvertes

Les états privés existants restent l'autorité. Aucun nouveau format ni migration
de profils n'est introduit par cette stabilisation. Un général sans profil reste
sans récompense ; une montée explicite ou une désignation QG sans caractéristiques
officielles réclame une migration définie. Les anciens profils ne reçoivent pas
de compensation rétroactive pour les paliers déjà passés.

À décider explicitement :

- À 0 PC, l'étiquette instinctive produit un bonus nul. Les PC de dernier recours
  ou un apprentissage croisé d'hybride peuvent l'activer plus tard ; aucun PC initial
  supplémentaire n'a été accordé.
- Migration d'une mémoire d'ordre retiré encore en attente, de profils dépassant
  les nouveaux plafonds ou dépourvus de provenance des étiquettes permanentes.
- Effets sur la résistance spéciale du Bouclier vivant et sur sa phase prioritaire :
  cette phase utilise encore sa formule dédiée, distincte des duels ordinaires.
- Sort des effets d'un QG qui se retire vivant entre deux affrontements : la règle
  validée ici définit la destruction, pas une nouvelle règle de retraite du QG.

La validation réelle Raspberry Pi/SSH reste décrite dans
[TESTS_LINUX_SURVIE.md](TESTS_LINUX_SURVIE.md). Une suite WSL réussie ne la remplace pas.
