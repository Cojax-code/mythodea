# Ordres V2 — audit d’architecture et plan de programmation

Date : 27 octobre 2026. **Analyse uniquement ; aucune activation ni modification du moteur.**

## 1. Base examinée et conclusion

L’audit porte sur `feat/ordres-v2`, au commit
`9d16a5f2230e5ed200818f2c77e5cfb732eac64d`. Le répertoire de travail était propre au
début de l’analyse. `HEAD` et la référence locale `origin/feat/ordres-v2` désignaient
ce commit. Cette observation ne constitue pas une nouvelle interrogation du serveur
GitHub ; aucun fetch, pull, changement de branche ou merge n’a été effectué.

Derniers commits examinés dans l’historique :

| Commit | Objet |
| --- | --- |
| `9d16a5f` | Valide la progression Zombie et prépare les sélections du lot B |
| `d32fdeb` | en cours de route |
| `44250f2` | Prépare les contrats du lot B et restreint les ordres des généraux Zombies |
| `acaba3e` | Consolide les groupes temporaires du lot B et leurs validations Linux |
| `82672ee` | lot b début |

Références confrontées au code et aux assertions des tests :
[règles de travail](../AGENTS.md), [moteur commun](../MYTHODEA_SPEC.md),
[Survie](../SURVIE_SPEC.md), [reprise](ordres-v2-reprise-codex.md),
[contrats de préparation](ordres-v2-preparation.md), ainsi que les décisions
explicites du propriétaire sur les restrictions Zombies et les fusions partielles.
Les sections courantes des documents priment sur leurs questionnaires archivés.
La demande d’audit remplace la poursuite de l’intégration demandée auparavant.

**Le moteur dispose déjà du calcul des combats, du traitement des pertes et de
l’identité des soldats. Le principal manque est une façon commune de présenter
les soldats effectivement engagés à tous les consommateurs du duel.** Les groupes
temporaires ne modifient pas cette présentation : les phases continuent à relire
les dossiers des généraux. Brancher seulement `GroupeTemporaire.bloc()` sur
`combat_bloc()` laisserait donc une partie du combat ignorer le prêt.

La cible recommandée conserve les modules existants et ajoute trois capacités
limitées : une vue explicite des participants par phase, un résultat de pertes
identifiable par UUID, puis un cycle authentifié pour les réanimations et les
survivants sans général. Les calculs communs restent uniques. Aucun framework,
registre Zombie concurrent ou module « moteur Lot B » n’est justifié.

Les quatre ordres restent inactifs. Gros_poisson possède une réservation de jeton,
des sélections testées et une conservation des origines, **pas un duel intégré**.
Muraille possède une prévision partielle, **pas une orchestration complète**.
Ralliement et Dernière charge disposent de calculs/préconditions, **pas d’une
réanimation opérationnelle**.

## 2. Chemin d’exécution réellement utilisé

Le chemin Survie est le suivant ; les noms sont ceux du code actuel :

```text
survie.resoudre_tour_survie
  → survie._clore_tour_survie
    → cycle_linux.Generations.capturer
    → config.racines_generation + rapports.preparation_privee
      → survie._resoudre_tour_capture
        → audit / formation.resoudre_tour / préparation des conflits
        → soldats.bataille_complete, par territoire
          → survie.resoudre_cascade
            → ordres_pipeline.bataille + retraites_apres_choc
            → survie._resoudre_cascade
              → combats.resoudre_combat_range
                → combats.resoudre_affrontement_actif
                  → combats._resoudre_affrontement_actif
                    → combats.combat_entre_generaux
                      → ordres_pipeline.duel + unites.duel
                      → soldats.participer
                      → ordres_pipeline.rafales
                      → combats._combat_entre_generaux
                        → bouclier_vivant.resoudre_priorite, si nécessaire
                        → combats.phase_engagement_initial
                        → ordres_pipeline.fuir_apres_choc
                        → manœuvres / combats.attaque_ciblee
                    → rapports.ecrire_detail_engagement
          → unites.terminer_territoire
        → clôture XP, retraites, soins, contrôle et rapports
    → Generations.preparer_publication / Generations.publier
```

Le pilote classique `plateau.lancer_bataille_v15()` ouvre lui aussi
`soldats.bataille_complete()` et appelle `combats.resoudre_combat_v15()` ou
`combats.resoudre_combat_off_def()`. Ces enveloppes rejoignent le moteur commun.
La transaction par génération privée appartient au pilote Survie : elle ne doit
pas être supposée présente autour de tout appel classique ou unitaire.

`survie.resoudre_cascade()` garde un même contexte QG pendant la cascade et fournit
la fonction de retraite. `ordres_pipeline.bataille()` réutilise le contexte si le
territoire est le même. Ajouter un nouveau contexte QG par prêt réélirait
incorrectement le donneur ; il faut conserver cette durée de vie.

## 3. Cartographie fonctionnelle ciblée

Les chemins ci-dessous sont relatifs à la racine du dépôt. « Lecture » signifie
absence de mutation persistante seulement lorsqu’elle est explicitement indiquée.
Les principaux appels sont indiqués, sans inventaire des utilitaires.

### 3.1 Combat, formations et déplacements

| Module et fonctions exactes | Responsabilité ; appelants → appels principaux | Effets de bord et données | Réutilisation Lot B |
| --- | --- | --- | --- |
| `python/combats.py` : `resoudre_affrontement_actif`, `_resoudre_affrontement_actif`, `resoudre_attaque_frontale` | Pilotes classique/Survie → sélection des adversaires, frontal puis rangé, `ordres_pipeline.formations_retenues`, `combat_entre_generaux`. | Relisent les forces, déclenchent combats et rapports ; limite de sécurité du rangé. | Garder l’ordonnancement commun. Lui ajouter les participants spéciaux et l’identité du précédent vaincu, pas une boucle de bataille parallèle. |
| `python/combats.py` : `combat_entre_generaux`, `_combat_entre_generaux` | Frontal/rangé → validation des camps, contextes d’ordres/capacités, participation, Rafale, Bouclier, choc, fuite, manœuvres. | Pertes réelles, progression indirecte, suppression des généraux, résultat structuré et rapports. Relit les dossiers à plusieurs étapes. | Point d’intégration du prêt complet. Tous ses lecteurs doivent voir la même sélection effective. |
| `python/combats.py` : `phase_engagement_initial`, `confrontation_directe`, `attaque_ciblee` | Duel et priorité Zombie → choc de blocs homologues ou attaque entre deux blocs désignés → `combat_bloc`, `supprimer_unites`, `unites.apres_confrontation`. | Blessures, morts, Propagation, vérification du QG, traces et résultat de phase. | Conserver les politiques de phase ; partager leur résolution élémentaire et accepter des blocs explicitement engagés. |
| `python/combats.py` : `ordre_actions_manoeuvre`, `ordre_attaques_initiative`, `choisir_cible`, `trouver_cible_facile`, `trouver_cible_faible` | Boucle de manœuvre → ordre des actions, priorité naturelle puis cible faible. | Choix aléatoires possibles ; pas de nouvelle règle de dégâts. | Réutiliser avec un filtre de présence par phase : Avant de Muraille et morts de Dernière charge absents de la manœuvre. Conserver les priorités existantes. |
| `python/generaux.py` : `lire_forces_territoire`, `regrouper_forces_par_camp`, `generaux_actifs_joueur` | Pilotes et pipeline → `lire_generaux_territoire`, regroupement par camp et positions. | Observation du plateau ; les lecteurs appelés peuvent valider/nettoyer. Les positions d’origine ne sont pas des numéros d’identité. | Réutiliser pour authentifier les cibles actives, y compris deux propriétaires alliés ; ne pas reconstruire les camps dans chaque ordre. |
| `python/generaux.py` : `lire_composition_general`, `lire_blocs_general` | Combat, PC, moral, capacités → représentation des dossiers par bloc/type ou bloc homogène avec chemins, soutiens et boucliers. | `lire_blocs_general()` peut créer un bloc manquant et supprimer des unités invalides/minoritaires. Avec `lecture_seule=True`, ne nettoie ni ne crée ; refuse les blocs invalides/mixtes. | Garder les lecteurs physiques comme source d’observation. Les prêts doivent produire une vue dérivée, sans passer une fusion virtuelle au nettoyage physique. |
| `python/commandement.py` : `compatibilite_formations`, `sequence_formation` ; `python/ordres_pipeline.py` : `preparer_compatibilites`, `formations_retenues`, `confronter_frontal_melange` | Pipeline → matrice du Lot A, positions des formations, confrontation spéciale frontal/On_melange. | Calculs purs dans `commandement` ; décisions et rapports dans le pipeline. | Muraille doit utiliser ces décisions, notamment les exclusions QG_nommade/réserve, sans compacter les places ni réimplémenter la matrice. |
| `python/mouvements.py` : `verifier_deplacement_general`, `preparer_retraites_surnombre`, `appliquer_retraites_surnombre`, `envoyer_general_au_repli`, `delai_sanction_repli` | Audit ou cascade → validation et planification, puis déplacement réel de dossiers. | Positions officielles, chemins, attente de sanction ; modifications physiques selon l’opération. | Aucun déplacement requis pour un prêt vivant. Les retours d’orphelins doivent réutiliser les primitives pertinentes après définition de leur cycle, sans transformer le retour en sanction. |

**Formation ne veut pas toujours dire formation de combat.** `python/formation.py`,
`resoudre_tour()`, `valider_sejour()` et `forger()` gèrent les séjours, apprentissages,
soins et transformations autorisés (`formation.json`, progression, soldats et
copies). `survie._resoudre_tour_capture()` les appelle avant les conflits. Ce n’est
pas un moteur de regroupement tactique à réutiliser pour fusionner des blocs.

### 3.2 Dégâts, fatigue, moral et capacités

| Module et fonctions exactes | Responsabilité ; appelants → appels principaux | Effets de bord et données | Réutilisation Lot B |
| --- | --- | --- | --- |
| `python/combats.py` : `combat_bloc`, `valeur_base_bloc`, `multiplicateur` | Choc, manœuvre et prévisions → `catalogues.valeur_combat`, `unites.definition`, `unites.avantage`, effets d’ordres. Valeur, formation lourde, avantage, fatigue, dégâts et pertes simultanées. | Calcul sans écriture ; dépend des définitions et du contexte d’ordres en lecture. Retourne des nombres de survivants avant moral. | Unique source des calculs ordinaires. Adapter l’entrée de fatigue seulement après validation de la règle hétérogène. |
| `python/etat.py` : `charger_generaux_fatigues`, `general_est_fatigue`, `sauvegarder_generaux_fatigues` | Audit/déplacements alimentent l’état ; combat le consulte. | `fatigue_generaux.txt`, par `joueur:generalN`, recalculé au tour. | Conserver cette autorité ; dériver la fatigue de chaque participant par son origine. |
| `python/combats.py` : `moral_des_pertes`, `supprimer_unites` | Résolutions et simulations → profil privé, composition, `unites.moral_bloc`, `ordres_pipeline.moral`, puis `soldats.pertes` et `verifier_qg`. | `moral_des_pertes` lit ; `supprimer_unites` détruit/sauve et peut constater la destruction irréversible du QG. | Le commandant effectif et la composition de référence doivent être explicites. Garder un seul traitement du moral et des pertes. |
| `python/soldats.py` : `selectionner_victimes`, `sauvetage_possible`, `prevoir_pertes`, `pertes` | Combat, Rafale, groupe temporaire ou simulation → même tirage collectif et même limite individuelle via `unites.blessures_max`. | Les deux premières sont pures. `prevoir_pertes` lit le registre. `pertes` modifie blessures/`detruit`, supprime les dossiers, publie les copies et retire les soutiens si leur bloc disparaît sans bouclier. | Réutiliser la sélection et le sauvetage. Compléter le résultat réel par les UUID/causes/origines nécessaires aux ordres de réanimation. |
| `python/unites.py` : `definition`, `etiquette`, `avantage`, `caracteristiques_armee`, `moral_bloc`, `blessures_max`, `ordres_classiques` | Combat, commandement, formation, prêts → catalogue et effets temporaires du pipeline. | Calcul/lecture. Étiquettes temporaires, bonus raciaux et restrictions `sans_cerveau` ne réécrivent pas la race persistante. | Garder ces fonctions centrales ; fournir le bon général et la bonne composition, pas des copies de leurs règles dans chaque ordre. |
| `python/unites.py` : `duel`, `memoriser_sauvageons`, `apres_confrontation`, `propager`, `regenerer_fuite`, `terminer_territoire`, `soigner_victoire_territoriale` | Duel → souvenirs de Sauvageons ; confrontation → Propagation ; retraite → régénération ; pilote Survie → régulation territoriale et soins. | `capacites_unites.json`, `soldats.json`, dossiers créés/supprimés, blessures. Événements de capacité et protections contre le rejeu. | Adapter les listes effectivement engagées. Réutiliser les mécanismes d’événement ; ni Propagation ni régénération des Sauvageons ne définissent la réanimation du Lot B. |
| `python/bouclier_vivant.py` : `resoudre_priorite`, `resistance_apres_choc`, `convertir_spore`, `retirer_bouclier` | Duel → séquence prioritaire, résistance, conversions ; attaques Zombies → `combats.attaque_ciblee`. | Résistance et reçus dans `capacites_unites.json` ; Spore change type, chemin, inode/propriétaire de destination et remet les blessures à zéro en conservant UUID/XP. Destructions et contrôle QG. | Conserver les règles propres du Bouclier ; adapter les sources de participants et isoler les décisions calculables pour les simulations. |

La valeur effective de `combat_bloc()` sert **à la fois** aux dégâts et à la
résistance au dénominateur. Pour deux types identiques, le côté frais face au côté
fatigué reçoit le facteur 2. Il n’existe pas de résistance individuelle déjà
calculée permettant de résoudre immédiatement un mélange frais/fatigués.

Les PC de `commandement.effectif_general()` servent à la confrontation des ordres.
`combat_bloc()` ne multiplie pas les dégâts par les PC du général. « Bonus du
bénéficiaire » doit donc reprendre les effets existants — moral, ordres, contexte
racial et composition selon la règle validée — sans inventer un bonus de dégâts.

### 3.3 Ordres, identités, morts et publication

| Module et fonctions exactes | Responsabilité ; appelants → appels principaux | Effets de bord et données | Réutilisation Lot B |
| --- | --- | --- | --- |
| `python/generaux.py` : `lire_ordres_general`, `lire_declaration_qg` ; `python/ordres_pipeline.py` : `ordres_du_general`, `intention_personnelle`, `intention` | Lecture des demandes → sélection des ordres disponibles/acquis, choix donneur personnel ou QG. Le parseur conserve les deux positions de Gros_poisson. | Lecture de fichiers et profils ; la syntaxe ne confère aucun droit. `ordres_du_general` écarte encore les spécifications non exécutables. | Adapter précisément le ciblage validé ; conserver tous les filtres avant la confrontation. |
| `python/progression.py` : `caracteristiques_general`, `ordre_autorise`, `reception_ordre_autorisee`, `nature_autorise_ordre`, `evolutions_eligibles` | Pipeline, commandement et formation → autorité du profil privé, apprentissage, émission, réception distincts. | Lecture/calcul ; `progression.json` fait foi, pas la fiche publique. | Réutiliser sans exception Zombie pour Gros_poisson. Ne pas remplacer réception par apprentissage : un effet collectif n’exige pas toujours l’acquisition du destinataire. |
| `python/ordres_pipeline.py` : `bataille`, `verifier_qg`, `qg_du_general` ; `python/commandement.py` : `QuartierGeneral.actif`, `selectionner_qg` | Pilote → QG choisi une fois ; pertes/Spore → contrôle avant repeuplement du bloc. | Contexte territorial, destruction mémorisée, rapports ; aucun remplacement. | Étendre le contrôle à la mort logique du commandant si ses soldats persistent. Garder les transmissions du duel courant jusqu’à sa fin. |
| `python/ordres_pipeline.py` : `points_duel_officiels`, `points_globaux_officiels`, `confronter_intentions`, `duel`, `effet`, `moral` ; `python/commandement.py` : `effectif_general`, `global_armee`, `confronter_donneurs` | Duel → donneurs autorisés, réception filtrée avant comparaison, PC et effets par identité. `duel` fige le facteur Cruelle avant les pertes. | Lectures privées/physiques, contexte temporaire ; les appels de préparation peuvent vérifier le QG et produire des traces. Aucun bonus inscrit dans les fiches. | Préparer les décisions depuis des observations explicites pour pouvoir simuler un candidat sans effets de bord. Ne pas copier les formules PC. |
| `python/soldats.py` : `SoldatParticipant`, `participation_temporaire`, `GroupeTemporaire.bilan`, `.bloc`, `.selections_homologues`, `.selections_gros_poisson`, `.fatigues_origine`, `.appliquer_pertes`, `.participer` | API préparatoire et tests → références des vivants authentifiés, regroupement, pertes communes, XP explicite. Aucun ordre actif ne raccorde ce groupe au duel complet. | Réservations temporaires d’UUID ; pas de déplacement. Pertes réelles uniquement sur demande. Contrôles origine, inode, UID/GID, type et génération. | Base du prêt vivant ; conserver ces contrôles, ajouter la présentation des unités engagées aux phases. Ne pas en faire une API qui accepte arbitrairement des morts. |
| `python/soldats.py` : `synchroniser`, `retrouver`, `enregistrer`, `sauvegarder`, `publier` | Audit/créations officielles → registre d’identité, rapprochement inode ou marqueur de génération privée, copies publiques. | `soldats.json` : UUID, type, chemin, inode/device, blessures, batailles, état détruit ; dossiers et copies lisibles. | Autorité unique des états des soldats. Préserver la distinction entre nouvelle unité et réanimation du même UUID. |
| `python/soldats.py` : `bataille_complete`, `participer`, `affrontement`, `terminer_bataille` ; `python/progression.py` : `valider_evenement`, `attribuer_niveau`, `monter_niveau` | Pilote territorial → participants survivants crédités une fois ; confrontations effectives → progression personnelle des généraux. | `soldats.json`, `progression.json`, copies ; pas de clôture XP en cas d’exception. Le suivi courant des soldats utilise des chemins. | Inscrire les prêtés réellement engagés ; ne pas créditer automatiquement le prêteur d’un duel personnel. Fiabiliser le suivi si une unité change de chemin ou reste sans général. |
| `python/generaux.py` : `supprimer_general_si_vide` ; `python/soldats.py` : `mort_general` ; `python/morgue.py` : `enregistrer_mort`, `materialiser` | Combat → général sans troupes, ou seulement Bouclier → notification de mort, suppression du dossier et de sa position ; pilote Survie → Morgue. | Positions, dossiers, `morgue.json`, puis état/profil Zombie lors du cycle prévu. | Séparer la mort d’un général de la destruction de soldats détachés vivants. La Morgue concerne les généraux et leurs rituels, pas les morts de Ralliement. |
| `python/securite.py` : `inventorier_unites_actions`, `memoriser_unites_actions`, `auditer_unites_speciales`, `verifier_tous_les_deplacements` | Cycle et audit → authenticité des mouvements, créations et capacités avant résolution. | `unites_actions.json`, inventaires, positions/fatigue et sanctions selon le contrôle. | Conserver l’audit pour prêts, retours et réanimations autorisées ; ne pas rendre un mort recréable par copie de son marqueur. |
| `python/etat.py` : `ecrire_prive` ; `python/config.py` : `racines_generation`, `ETATS_METIER` ; `python/cycle_linux.py` : `Generations.capturer`, `.preparer_publication`, `.publier`, `.erreur` | Sauvegardes et pilote Survie → copie privée, résolution, publication/reprise contrôlée. | États métier, générations et dossiers des joueurs ; écritures privées atomiques et permissions réelles. | Utiliser la transaction existante. Tout nouvel état persistant devra être capturé/publié avec elle, jamais dans un registre parallèle oublié. |
| `python/rapports.py` : `preparation_privee`, `afficher_et_ecrire`, `ecrire_detail_engagement`, `ecrire_details_engagements`, `ecrire_rapport_long`, `ecrire_rapport_court` | Résolutions et pilotes → détails des chocs/manœuvres, ordres retenus, synthèses. | Rapports longs, courts et territoriaux ; redirection dans la génération privée pendant le calcul Survie. | Étendre le résultat du duel avec origines, prêts, morts/retours et motifs sans effet. Les simulations ne doivent rien publier. |

## 4. Doublons et risques de complexité

### 4.1 Réorganisations justifiées

| Constat vérifiable dans le code | Qualification | Recommandation et bénéfice concret |
| --- | --- | --- |
| `combats.confrontation_directe()` et `combats.attaque_ciblee()` répètent fatigue → calcul → participation → pertes des deux côtés → capacités → effectifs finaux. | Vrai doublon d’orchestration, mais calcul des dégâts déjà partagé dans `combat_bloc`. Les formats de rapport et les phases diffèrent légitimement. | Extraire une résolution de deux blocs dans `combats.py`. Deux chemins de mutation deviennent un seul ; un prêt ou une correction de pertes n’a plus deux intégrations à maintenir. Préserver l’ordre des appels et les branches blocs vides. |
| `GroupeTemporaire.selections_homologues()` et `.selections_gros_poisson()` reconstruisent un index bloc/type ; le second ajoute origine, profil et restriction raciale. | Duplication partielle ; les décisions ne sont pas identiques. | Partager éventuellement la construction de l’index dans `soldats.py`, en gardant le contrôle des deux origines et de leur intersection. Faible priorité ; aucune justification pour un module de sélection. |
| `soldats.limite_blessures()` reproduit les seuils d’ancienneté, mais ignore le type ; `unites.blessures_max()` est la règle complète utilisée par `sauvetage_possible`. | Ancien calcul partiel, appelé par un test, pas par le chemin réel de pertes repéré. | Ne pas le réutiliser pour les réanimés. Éventuelle délégation/dépréciation séparée après vérification des usages ; pas de remplacement silencieux des limites raciales par 1/2/3. |
| `unites.terminer_duel()` régule d’anciennes créations après un duel ; `terminer_territoire()` réalise la régulation territoriale active en Survie. | Deux API à temporalités différentes. La première n’a que des appels de tests repérés dans le dépôt. | Ne pas reconnecter `terminer_duel` au Lot B. Cela changerait le surnombre et les survivants avant la fin du territoire. Clarifier son statut lors d’un nettoyage distinct. |
| `combats.cible_facile()` contient l’ancien triangle ; `trouver_cible_facile()` utilise `multiplicateur`, donc le catalogue et les effets courants. | Fonction ancienne sans appel repéré dans `python/` ou les tests. | Utiliser la seconde ; ne pas réanimer le triangle codé en dur pour les prévisions. Suppression éventuelle non nécessaire à l’intégration. |
| `ordres_pipeline.donneurs_officiels()` et `confronter_duel_officiel()` ont des appels de tests, alors que le duel réel passe par `intention`, `points_*_officiels`, `confronter_intentions`. | API préparatoires distinctes du chemin actif ; risque de tester une façade sans tester l’intégration. | Étendre la préparation commune utilisée par le duel réel et les simulations. Ne pas construire un troisième pipeline Lot B autour de ces seules façades. |

### 4.2 Séparations à conserver

- `soldats.prevoir_pertes()` et `soldats.pertes()` ne sont pas deux règles de moral
  concurrentes : elles partagent `selectionner_victimes()` et
  `sauvetage_possible()`. La première observe, la seconde mutile/supprime et publie.
  Leur rapprochement ne doit jamais faire exécuter puis « annuler » de vraies pertes
  pour obtenir une prévision.
- `combats.combat_bloc()` donne les pertes avant sauvetage ; `soldats.pertes()`
  décide quels individus meurent réellement. Cette séparation est nécessaire aux
  blessures individuelles et au score de Muraille après moral.
- `bouclier_vivant.resistance_apres_choc()` applique une règle spéciale de réserve
  de résistance, différente d’un combat ordinaire. `_puissance_bloc_adverse()`
  réutilise déjà `combats.valeur_base_bloc()` et `multiplicateur()`.
  `_cible_zombie()` exprime aussi une priorité propre aux Zombies : la remplacer
  par `choisir_cible()` au nom de la déduplication changerait le gameplay.
- Les validations du pipeline et de `commandement._ordres_eligibles()` protègent
  deux entrées différentes. Les règles communes sont déjà centralisées dans
  `progression`. Conserver ces frontières, en testant leur cohérence.
- `ordres_conception.ORDRES_EN_CONCEPTION` décrit des intentions ;
  `catalogues.ORDRES` attribue les droits exécutables. Ce ne sont pas deux sources
  interchangeables d’autorisation.
- Les contextes `_participants`, `_generaux_engages`, `_bataille` et `_prets` de
  `soldats.py` suivent respectivement XP des soldats, progression des commandants,
  événement territorial et réservations. Ne pas les fusionner en un registre
  universel ; un prêt n’est pas un affrontement personnel du prêteur.

### 4.3 Divergences possibles à prévenir

1. **Lecture physique contre présence au combat.** `phase_engagement_initial`,
   la manœuvre, `rafales`, `moral_des_pertes`, `unites.apres_confrontation` et
   `bouclier_vivant.convertir_spore` retrouvent les unités à partir des chemins
   des généraux. Une seule de ces lectures oubliée suffit à reprendre une unité
   exclue, ignorer un prêt ou employer une composition incorrecte.
2. **Lecture qui répare.** Le mode historique de `lire_blocs_general()` recrée les
   blocs absents. La sélection de Gros_poisson et les simulations doivent éviter
   cette mutation. Pour respecter le contrat jusque dans le duel, ne pas compter
   sur un lecteur avec nettoyage après une sélection sans création.
3. **Référence immuable contre conversion.** `GroupeTemporaire.bilan()` refuse un
   changement d’origine/type/inode. Spore effectue précisément ces changements.
   Retirer les contrôles pour « accepter Spore » ouvrirait aussi la voie aux copies
   falsifiées. Une conversion autorisée doit produire un événement reconnu,
   seulement après décision sur la destination du prêté converti.
4. **Général vivant confondu avec dossier non vide.** Les tests d’existence et
   `supprimer_general_si_vide()` ne représentent pas un général vaincu dont l’Avant
   survit ailleurs. Le QG est également contrôlé par le contenu de son bloc.
   Muraille exige un état de cycle explicite ; ce n’est pas un changement de nature
   du général ni une nouvelle exception Zombie.
5. **Totaux physiques contre pertes du duel.** Les champs `initial_*`/`final_*` de
   `combat_entre_generaux()` sont issus des généraux physiques. Un prêt exige des
   totaux engagés et un bilan d’origine distincts, sinon le rapport attribue mal
   les pertes ou double les survivants.
6. **Morts historiques contre morts éligibles.** `soldats.json` conserve `detruit`,
   mais `pertes()` renvoie surtout des libellés et ne fournit pas un journal des
   décès de chaque duel/flanc. Filtrer tous les `detruit=True` ressusciterait des
   soldats étrangers à l’événement.
7. **Défenseur connu puis perdu.** `resoudre_combat_off_def()` connaît le défenseur,
   mais transmet essentiellement le mode à la résolution commune. Le contexte
   d’ordres du duel n’expose pas explicitement ce rôle. Ralliement doit recevoir
   le camp défenseur authentifié du pilote, jamais le déduire de `j1` ou `j2`.
8. **Nombreuses relectures.** Les méthodes de `GroupeTemporaire` repassent par
   `bilan()` et le registre pour vérifier les références. C’est utile à la sûreté,
   mais multiplier les conversions UUID → chemins → blocs → compositions à chaque
   phase peut coûter cher. Mesurer avant de mettre en cache ; une observation
   bornée à une confrontation est préférable à un second état mutable permanent.

Ces points sont des limites ou des risques d’intégration signalés par l’audit.
Ils n’ont donné lieu à aucune correction fonctionnelle dans cette livraison.

## 5. Gros_poisson — analyse et intégration prioritaire

### 5.1 Ce qui fonctionne déjà

`soldats.participation_temporaire()` authentifie des vivants sans déplacer leurs
dossiers. `GroupeTemporaire.selections_gros_poisson()` ne retient que les couples
bloc/type présents chez les deux alliés. Les blocs manquants ou incompatibles sont
ignorés sans annuler les autres sélections ; aucun homologue donne un motif sans
effet. Les profils privés et `unites.ordres_classiques()` interdisent le
contournement des restrictions Zombies. Le QG, l’acquisition, les positions actives
et la confrontation restent à vérifier par le pipeline réel.

`GroupeTemporaire.appliquer_pertes()` délègue aux pertes communes, avec sélection
explicite et moral fourni. Les victimes sont tirées dans l’ensemble de cette
sélection, sans quota par propriétaire. `bilan()` distingue morts et survivants à
leur origine. Une fermeture ne ressuscite rien et ne restaure aucune blessure.

### 5.2 Fatigue individuelle : représentation possible, règle manquante

`fatigues_origine()` fournit une valeur pour chaque UUID vivant, mais la dérive de
la fatigue de son général d’origine. Il n’existe pas aujourd’hui de champ autonome
de fatigue par soldat dans `soldats.json`.

Cette représentation dérivée suffit à **préserver** deux provenances différemment
fatiguées pendant un duel. Elle ne suffit pas à **calculer** les pertes d’un bloc
mélangé : `combat_bloc()` reçoit deux booléens, et la valeur modifiée sert aussi de
résistance. Ni une moyenne, ni « tout le bloc fatigué », ni deux sous-duels
successifs ne sont équivalents à une règle déjà validée. Les sous-duels changeraient
notamment les planchers de pertes et la simultanéité.

Recommandation : conserver l’état par général et transmettre le relevé par UUID
dans la vue de participants. Après validation de la formule, adapter le calcul
commun pour les profils hétérogènes en conservant exactement les cas homogènes.
Ne pas persister une seconde fatigue pour le seul besoin du prêt.

### 5.3 Commandement et capacités

Le propriétaire d’un dossier, le commandant du duel et le donneur d’un ordre sont
trois rôles différents. Gros_poisson ne doit changer que le commandement effectif
des soldats engagés, et seulement pendant le prêt.

`moral_des_pertes(infos, beneficiaire)` sait déjà prendre le profil du bénéficiaire,
mais relit sa composition physique. `valeur_base_bloc()` prend le nombre du bloc
fourni pour le seuil de cavalerie lourde. Sans règle explicite, ces deux fonctions
pourraient donc appliquer deux références différentes : armée physique pour le
moral, bloc fusionné pour la formation. Il faut choisir la référence validée puis
la fournir à ces fonctions communes. Les non-prêtés conservent le contexte de
leur général et ne deviennent pas implicitement des bénéficiaires.

Les effets Orc/Hérisson/Cruelle/Discours restent ceux du pipeline. Cruelle dépend
actuellement de l’armée du donneur figée au début du duel : ne pas substituer
automatiquement l’effectif fusionné à cette source. Rafale doit viser les soldats
effectivement présents, avec l’immunité lourde existante. Les soutiens doivent
garder leur lien avec le bloc dont la destruction les entraîne.

Un Zombie ou un Bouclier interdit au prêt ne devient pas prêtable. En revanche,
un **adversaire** avec Spore peut viser un humain prêté : c’est cette interaction
qui exige une règle de destination/conservation de l’origine. Les restrictions
Zombies ne suppriment pas les capacités de l’adversaire.

### 5.4 Tableau d’intégration

| Besoin technique | Fonction existante | Décision |
| --- | --- | --- |
| Lire les deux positions, authentifier QG/acquisition/camps/destinataires, comparer les ordres | `generaux.lire_ordres_general` ; `ordres_pipeline.intention`, `duel`, `confronter_intentions` ; contrôles `progression` | **Adapter** le ciblage réservé 1017 sans contourner les contrôles ni fusionner les droits de plusieurs donneurs. |
| Choisir les homologues, refuser unités interdites, expliquer l’absence d’effet | `soldats.GroupeTemporaire.selections_gros_poisson` | **Réutiliser** ; raccorder le motif au résultat du duel. |
| Présenter prêtés et non-prêtés aux phases et empêcher leur double engagement | `participation_temporaire`, `GroupeTemporaire.bloc` ; lecteurs de `combats` | **Adapter**, avec une petite fonction commune de construction/lecture de la vue effective. Le groupe actuel ne modifie aucun lecteur du duel. |
| Préserver fatigue et appliquer les bonus autorisés | `GroupeTemporaire.fatigues_origine`, `combats.combat_bloc`, `moral_des_pertes`, `unites.moral_bloc` | **Adapter** après décision sur résistance hétérogène et composition. Aucune nouvelle formule propre à Gros_poisson. |
| Appliquer blessures, victimes et décès | `soldats.pertes`, `selectionner_victimes`, `sauvetage_possible`, `combats.supprimer_unites` | **Réutiliser/adapter** le résultat identifiable ; conserver le contrôle du QG après pertes, absent d’un simple appel isolé au groupe. |
| Capacités, préphase et manœuvre | `ordres_pipeline.rafales`, `bouclier_vivant.resoudre_priorite`, `unites.apres_confrontation`, `combats.attaque_ciblee` | **Adapter** les entrées de participants, pas réimplémenter les effets. |
| Retour des survivants, XP et rapport | `GroupeTemporaire.bilan`, `.participer`, `soldats.terminer_bataille`, `rapports.ecrire_detail_engagement` | **Réutiliser** la restitution virtuelle ; **adapter** les totaux et le suivi de participation. Aucun déplacement physique pour le prêt ordinaire. |

### 5.5 Chemin envisagé jusqu’à la publication

1. Le pilote ouvre la bataille et son QG unique. Le pipeline lit le jeton réservé,
   authentifie le donneur acquis et ses permissions, résout les positions dans le
   camp, contrôle chaque profil et confronte les ordres selon la catégorie Duel.
2. Sur une décision retenue, observer les unités autorisées sans créer les blocs
   absents. Ouvrir `participation_temporaire`, sélectionner les homologues et
   construire la vue du bénéficiaire ; les autres soldats gardent leurs rôles.
   Sans homologue, conserver le duel normal et ajouter le motif au rapport.
3. Préparer les effets avec les références validées de commandement/composition.
   Relever la fatigue par origine. Les UUID réservés ne peuvent figurer deux fois
   dans la même phase ; le prêteur ne perd pas son futur tour normal.
4. Faire passer **Rafale, Bouclier/Spore, choc et manœuvres** par les mêmes lecteurs
   de participants. Les règles de dégâts restent dans `combats`, les mutations
   dans `soldats`/`unites`/`bouclier_vivant`. Réévaluer les effectifs après mutation.
5. Enregistrer les pertes par UUID/origine et les participants réels. Vérifier le
   QG immédiatement après les destructions, avant une éventuelle recréation par
   capacité. Les effets déjà transmis restent valides jusqu’au terme du duel.
6. À la sortie, vérifier `bilan()`, fermer la vue et rendre les survivants disponibles
   à leur origine. Leurs dossiers n’ayant pas bougé, il n’y a aucune copie inverse
   ni restauration d’état. Une conversion autorisée devra suivre son événement
   explicite ; elle ne peut être assimilée à ce retour ordinaire.
7. Produire un résultat de duel distinguant effectifs engagés, pertes par origine
   et survivants restitués. `rapports.ecrire_detail_engagement()` en dérive les
   détails ; la clôture territoriale applique l’XP commune une seule fois.
8. En Survie, ces opérations restent dans la génération privée. La publication
   commune expose ensemble état final et rapports. En cas d’interruption, libérer
   les vues mais ne pas rejouer ni annuler artisanalement les mutations privées.

La réponse à la question d’architecture est donc **oui, une adaptation générale
est préférable** : elle porte sur les participants et le contexte du combat.
Elle ne résout cependant pas par elle-même les choix de gameplay sur la fatigue
et la composition.

## 6. Muraille humaine

Les Avant restent des blocs distincts, sous leur commandement d’origine. Le score,
son départage, le recalcul et le retour des orphelins même après défaite sont déjà
validés ; il n’est pas nécessaire de redemander ces décisions.

| Besoin technique | Fonction existante | Décision |
| --- | --- | --- |
| Appliquer la matrice et exclure QG_nommade/réserve | `commandement.compatibilite_formations`, `sequence_formation` ; `ordres_calculs_v2.participants_muraille` | **Réutiliser** les rôles effectivement retenus ; ne pas confondre propriétaire, camp et identité. |
| Conserver les Avant séparés | `soldats.participation_temporaire`, `GroupeTemporaire.bloc` | **Adapter** la vue de phase commune, sans fusion d’Avant ni attribution de bonus du voisin. |
| Calculer, sauver par moral, classer | `combats.previsions_avant_muraille`, `simuler_avants_muraille`, `prochain_avant_muraille` ; `soldats.prevoir_pertes` ; `ordres_calculs_v2.choisir_avant_muraille` | **Réutiliser/adapter**. Calcul et sélection existent ; contextes QG de chaque candidat et capacités restent incomplets. |
| Simuler Bouclier, Spore, Propagation et soutiens | `bouclier_vivant.resistance_apres_choc`, `choisir_spore`, `bloc_destination_spore` ; `unites.apres_confrontation`, `propager` | **Adapter**, en séparant les décisions calculables de leurs écritures. **Créer** seulement les fonctions pures manquantes dans ces modules ; la simulation doit appeler les mêmes règles que le réel. |
| Enchaîner les engagements et recalculer après chaque résultat | `combats._resoudre_affrontement_actif`, `phase_engagement_initial`, `confrontation_directe` | **Adapter** l’orchestration ; la fonction `prochain_avant_muraille` choisit, elle n’exécute aucune succession de duels. |
| Retirer les Avant de la manœuvre, préserver la durée de transmission | `combats.ordre_actions_manoeuvre`, `ordres_pipeline.duel`, `verifier_qg` | **Adapter** le filtre de phase et le contrôle du général vaincu ; conserver les effets jusqu’à fin du duel, sans nouvelle désignation QG. |
| Garder vivants les soldats d’un général vaincu, les retourner au village | `generaux.supprimer_general_si_vide`, `soldats.mort_general`, primitives de `mouvements` | **Créer** le cycle manquant des soldats sans général dans les modules existants, puis **adapter** la suppression. Les déplacements de généraux et la Morgue ne remplacent pas `unites_sans_general`. |
| Comptabiliser et rapporter les survivants détachés | `soldats.bataille_complete`, `terminer_bataille`, `rapports.ecrire_detail_engagement` | **Adapter** l’identité de participation et les résultats ; aucun gain d’XP pour une simple simulation. |

La prévision actuelle copie le générateur aléatoire fourni pour chaque candidat ;
les tests vérifient l’absence de consommation du hasard réel. Elle refuse
explicitement les capacités non simulées, y compris un Bouclier hors Avant.
Ce refus est un garde-fou préparatoire, pas une restriction de gameplay à conserver
dans un ordre activé.

Ne pas entrer dans le vrai `ordres_pipeline.duel()` pour « essayer » un candidat :
ses dépendances peuvent constater une destruction QG et écrire un rapport. Préparer
les mêmes décisions à partir d’une observation figée, puis utiliser un contexte
isolé de calcul. Même principe pour `unites.duel()`, qui mémorise les Sauvageons
dans l’état privé. Aucune exécution de combat réel suivie d’une restauration de
dossiers, aucun monkey patch du système de fichiers n’est recommandé.

**Dépendance obligatoire :** le circuit des survivants sans général du Lot C doit
exister avant l’activation de Muraille. L’extraction de son seul sous-ensemble
nécessaire peut être proposée séparément ; il ne faut ni prétendre ce circuit déjà
disponible, ni étendre automatiquement le chantier à tout le Lot C.

## 7. Ralliement

Le contrat de conception prévoit les renforts du QG défenseur à partir des pertes
d’un allié vaincu, au profit de l’allié suivant. Les décisions récentes précisent
qu’il s’agit de **morts réanimés**, avec UUID, blessures et XP conservés. La formule
est `pertes_du_type // 5`, uniquement pour les types présents chez le bénéficiaire.

| Besoin technique | Fonction existante | Décision |
| --- | --- | --- |
| Authentifier le QG défenseur et le bénéficiaire suivant | `combats.resoudre_combat_off_def`, `_resoudre_affrontement_actif` ; `ordres_pipeline.bataille`, `intention`, `duel` | **Adapter** le contexte territorial avec le camp défenseur et l’historique des engagements, en conservant l’ordre des formations retenues. |
| Calculer les quotas | `ordres_calculs_v2.renforts_ralliement` | **Réutiliser** ; aucun arrondi global ni transfert vers un type absent. |
| Identifier les morts de l’événement et sélectionner les UUID | `soldats.pertes`, `generaux.supprimer_general_si_vide` | **Adapter** pour conserver un résultat de décès exploitable ; **créer** la sélection après validation de l’éligibilité, car les libellés et `detruit` seuls sont insuffisants. |
| Réanimer les mêmes individus sans ouvrir une fabrication libre | `soldats.retrouver`, `creer_dossier_unite`, `ecrire_copie`, `publier` ; précédent `unites.regenerer_fuite` | **Créer** une opération authentifiée de réanimation dans `soldats.py`, utilisant ces primitives. La régénération des Sauvageons est limitée à son type/événement et ne définit pas la règle de Ralliement. |
| Intégrer provisoirement les vivants restaurés au combat | `participation_temporaire`, vue de phase proposée, `combats.combat_bloc`, `soldats.pertes` | **Réutiliser/adapter** après réanimation autorisée ; ne jamais admettre un UUID mort dans le groupe vivant pour contourner cette étape. |
| Restituer, conserver les états, traiter une origine disparue | `GroupeTemporaire.bilan`, `soldats.bataille_complete`, futur cycle sans général | **Adapter/créer** selon les décisions encore ouvertes de bloc, durée et destination. Ne pas appliquer automatiquement la destination de Muraille à Ralliement. |

La réanimation n’est pas `enregistrer()` : cette fonction crée une nouvelle
identité. Elle n’est pas non plus `unites.propager()`, qui crée de nouveaux Zombies,
ni `morgue.materialiser()`, qui traite les généraux. Il faut un acte limité à des
UUID morts autorisés par un événement, avec preuve d’origine, contrôle de la
destination et absence de double consommation. Les recettes/dossiers nécessaires
ne doivent pas être reconstruits depuis une copie publique falsifiable.

## 8. Dernière charge

Contre-ordre de Duel : le général allié précédent doit être vaincu. Les morts du
flanc G/g ou D/d prennent la place du flanc correspondant du suivant au choc
seulement, fatigués. Flanc absent ou sans éligible : aucun effet, aucune bascule.
Les survivants de la charge meurent définitivement ; le flanc normal du suivant
revient pour la manœuvre.

| Besoin technique | Fonction existante | Décision |
| --- | --- | --- |
| Vérifier la défaite précédente et le flanc | `ordres_calculs_v2.derniere_charge_possible` ; `combats._resoudre_affrontement_actif` | **Réutiliser** la condition ; **adapter** le pilote pour fournir le précédent réel et ses morts, sans déduire la défaite d’un simple dossier absent. |
| Parser/confronter le contre-ordre personnel ou QG | `generaux.lire_ordres_general`, `ordres_pipeline.intention`, `confronter_intentions` ; `commandement.confronter_donneurs` | **Adapter** après fixation du jeton/format final. Réutiliser les règles de contre-ordre, acquisition et réception. |
| Sélectionner et relever les morts du flanc | Résultat identifiable de `soldats.pertes` et opération de réanimation proposée pour Ralliement | **Réutiliser** ce mécanisme commun ; **créer** seulement la sélection propre à la règle validée de Dernière charge. |
| Remplacer temporairement le flanc et imposer la fatigue au choc | `combats.phase_engagement_initial`, `combat_bloc`, vue de phase commune | **Adapter** par sélection/substitution explicite et fatigue de participation. Ne pas écrire la fatigue de tout le général suivant. |
| Exclure la manœuvre et tuer définitivement les relevés survivants | `combats.ordre_actions_manoeuvre`, `soldats.pertes`, `generaux.supprimer_general_si_vide` | **Adapter** la transition de phase et **créer** la finalisation obligatoire de l’événement. Une fermeture de groupe ne tue rien ; une perte soumise au moral ordinaire pourrait sauver à tort les relevés. |
| XP, preuves de décès et rapports | `soldats.terminer_bataille`, `rapports.ecrire_detail_engagement` | **Adapter** pour ne pas créditer des survivants inexistants en fin de bataille, ni compter deux fois les mêmes individus. |

Ralliement et Dernière charge partagent l’authentification et la matérialisation
des mêmes UUID. Leurs durées, sélections, destinations et règles de fin restent
distinctes. Une classe d’ordre avec des dizaines de paramètres ne simplifierait
pas cette différence ; quelques fonctions explicites dans les modules actuels
suffisent.

## 9. Architecture cible minimale

### 9.1 Autorités et représentations

| Donnée | Autorité conservée | Vue temporaire autorisée |
| --- | --- | --- |
| UUID, type, XP, blessures, destruction | `soldats.json`, géré par `soldats.py` | Référence à l’UUID ; observation de calcul sans restauration de l’état ancien. |
| Identité/profil/nature/état Zombie/ordres appris du général | `progression.json`, géré par `progression.py` | Profil du commandant ou du donneur au moment défini par l’effet. |
| Propriété et présence physique | Dossiers authentifiés, UID/GID, registre privé, inventaire d’actions | Origine attachée au participant ; le prêt ordinaire ne déplace pas le dossier. |
| Fatigue normale | `fatigue_generaux.txt` | Valeur dérivée par UUID d’origine ; éventuel état « fatigué pour cette charge » borné à la phase, sans modifier le général. |
| QG, ordres transmis, phases | Contextes existants `ordres_pipeline.bataille`/`duel` | Décisions calculées depuis des observations ; aucune seconde élection ou copie persistante de droits. |
| Résistance, Propagation, Spore, régénération | `capacites_unites.json` et opérations existantes | Plans de calcul isolés pour la simulation, reçus d’événement lors de l’application réelle. |
| Réanimation et soldats sans général | Cycle encore manquant ; à concevoir autour des identités de `soldats.py` | Métadonnées de provenance/événement/destination, sans dupliquer XP/blessures/type dans un deuxième registre d’autorité. |

Pour un prêt vivant, la vue a seulement besoin de savoir **qui participe**, **qui
commande**, **d’où vient sa fatigue** et **à quelles phases il participe**. Les
origines sont déjà dans `SoldatParticipant`. Les listes de chemins et nombres
compatibles avec `combat_bloc()` restent des projections calculées à la demande,
pas une seconde armée mutable à synchroniser manuellement.

La vue doit être consommée par les phases, les capacités, le moral, les rapports
et le suivi XP. Les calculs PC du donneur gardent leur référence documentée : ne
pas remplacer aveuglément toute lecture physique par un effectif fusionné.

### 9.2 Fonctions à adapter, sans nouveau module

- **`soldats.py`** : étendre le groupe vivant et le résultat des pertes ; suivre
  les identités engagées lorsque les chemins peuvent changer ; accueillir le
  cycle authentifié de réanimation et les métadonnées de soldats sans général.
- **`combats.py`** : partager la résolution de deux blocs entre choc/manœuvre ;
  fournir la vue effective et le contexte de phase ; porter les séquences de
  Muraille et l’historique utile du précédent combat. Garder `combat_bloc()` comme
  calcul commun, avec extension conditionnée par la règle de fatigue validée.
- **`ordres_pipeline.py`** : préparer les décisions de donneur/cible depuis une
  observation explicite, appliquer ensuite le contexte et les traces du réel ;
  raccorder les paramètres validés sans nouvelle couche de permissions.
- **`unites.py` et `bouclier_vivant.py`** : accepter les participants effectifs et
  séparer les décisions de capacité de leurs écritures là où la simulation
  l’exige. Les politiques raciales restent dans ces modules.
- **`generaux.py`** : tenir compte des soldats détachés avant destruction physique
  du dossier ; distinguer mort du commandant et sort des soldats, sans changer
  les sanctions ni la règle ordinaire du général vide.
- **`survie.py`, `plateau.py`, `rapports.py`** : transmettre le contexte territorial
  manquant, finaliser les événements et présenter les résultats. Pas de calcul
  de combat supplémentaire dans un pilote de mode.

### 9.3 Fonctions réellement manquantes

Les intitulés suivants décrivent des responsabilités proposées, **pas des API
déjà présentes ni des signatures imposées** :

1. **Construire/lire la participation effective d’une phase**, dans `soldats.py`
   avec les choix de phase dans `combats.py`. Le groupe actuel ne soustrait pas
   ses soldats aux lectures ordinaires ; aucune adaptation du seul calcul
   numérique ne peut résoudre cette absence.
2. **Préparer un résultat de confrontation réutilisable par réel et prévision**,
   par extraction dans `combats.py` et dans les modules de capacités. Il doit
   préserver les tirages et l’ordre des mutations, sans nécessiter une exécution
   fictive du cycle Linux. Commencer par les parties réellement communes.
3. **Produire les décès et transitions identifiés de l’événement**, en adaptant
   `soldats.pertes` et les destructions/conversions hors de cette fonction.
   Un événement doit distinguer mort, conversion et retrait : un simple écart de
   compteurs ne permet pas de sélectionner les morts d’un flanc.
4. **Réanimer une sélection autorisée puis finaliser son usage**, dans
   `soldats.py`, avec le pilote de phase. Nécessaire car le groupe vivant refuse
   justement les morts et que les créations officielles fabriquent de nouveaux
   UUID. Ralliement et Dernière charge utilisent la même opération autorisée.
5. **Conserver et acheminer des survivants sans général**, avec `soldats.py`,
   `generaux.py` et les primitives de mouvement. Ce cycle manque réellement ;
   appeler `supprimer_general_si_vide()` ou déplacer un général ne le remplace pas.

La persistance de ces deux derniers mécanismes devra être spécifiée avant leur
codage. Il n’est pas décidé ici d’un nouveau format de fichier. Réutiliser le
registre des soldats pour leurs états et les événements existants lorsque leur
responsabilité correspond ; toute extension doit entrer dans la capture et la
publication communes. Aucun état de prêt vivant n’a besoin de survivre à un duel
ou de traverser une publication.

## 10. Ordre de réalisation recommandé

Toutes les étapes ci-dessous sont **proposées**, soumises à validation préalable.
Chaque livraison conserve les ordres incomplets désactivés.

| Étape | Travail et dépendances | Critère de sortie |
| --- | --- | --- |
| 1. Arrêter les contrats manquants | Répondre aux questions de la section 12 pour l’ordre que l’on veut activer. Définir le contexte territorial et les événements nécessaires, sans réouvrir les règles déjà validées. | Aucun calcul implicite de fatigue, de réanimation ou de destination. |
| 2. Unifier l’accès aux participants | Extraire la résolution commune choc/manœuvre et intégrer la vue effective dans le duel ordinaire, initialement avec les participants historiques. | Même résultat, mêmes victimes/blessures, mêmes tirages, capacités et rapports pour les scénarios sans Lot B. Aucun nouveau module. |
| 3. Intégrer Gros_poisson | Réutiliser les sélections, raccorder QG/ciblage, effets/composition/fatigue validés, capacités, XP, restitution et motifs au rapport. | Duels complets, prêteur à son tour normal, fusions partielles et restrictions testés ; pas seulement appel direct à `combat_bloc`. |
| 4. Établir les événements de pertes et le cycle sans général | Résultat par UUID, distinction mort/conversion/retrait, notification unique du général vaincu, retour des orphelins selon les règles déjà validées de Muraille. | Pas de destruction d’un Avant survivant ; identité, propriétaire, délai et publication conservés après victoire, défaite ou arrêt du QG. |
| 5. Compléter la prévision et intégrer Muraille | Préparation sans écriture des ordres de chaque candidat, capacités partagées, classement/recalcul, exclusion de manœuvre. Dépend de 2 et 4. | Prévision et réel cohérents pour les capacités prises en charge ; aucun hasard réel consommé par le classement ; cycle complet des orphelins. |
| 6. Réanimation commune puis Ralliement | Dépend de 2 et 4 et des réponses spécifiques : origine des morts, quotas, bénéficiaire défenseur suivant, bloc/durée/destination. | Mêmes UUID et états, sélection bornée à l’événement, aucune copie falsifiée ni double consommation. |
| 7. Dernière charge | Réutiliser la réanimation de 6 ; ajouter remplacement du flanc au choc, fatigue temporaire et mort définitive après charge. | Flanc normal rétabli pour la manœuvre, aucun relevé survivant crédité ou restitué par erreur. |
| 8. Activation vérifiée | Après recette propre à chaque ordre, rendre seulement cet ordre disponible et documenter la règle/architecture validée. | Suite moteur et contrôles Linux réussis, rapport lisible, aucune activation indirecte d’un autre ordre. |

L’étape 4 peut être préparée avant la fin de Gros_poisson si ses règles restent
en attente ; la préparation pure de Muraille peut avancer sans activer l’effet.
En revanche, ni une formule pure ni un test de groupe ne suffisent à passer
directement à l’étape 8. Aucun merge vers `v2.0` n’est inclus dans ce plan.

## 11. Tests existants, limites et non-régression à prévoir

### 11.1 Éléments de preuve déjà présents

Les assertions ont été lues ; **aucune suite n’a été relancée pour cet audit
documentaire**. Le journal de reprise rapporte 726 tests Linux distincts réussis,
dont trois contrôles root exécutés séparément après les trois skips de la suite.
C’est le bilan historique de la livraison examinée, pas un nouveau résultat de
validation. La recette Raspberry Pi/SSH/cgroup demeure distincte des tests WSL.

| Fichier de tests | Preuve utile et limite |
| --- | --- |
| `.dev/tests/test_valeurs_combat.py` | `test_equivalence_historique_tous_types_fatigues_positions_et_effectifs`, `test_fatigue_meme_type_sans_annuler_avantage_naturel`, seuil lourd après pertes. Base de comparaison du calcul commun ; ne définit pas une fatigue mélangée. |
| `.dev/tests/test_participations_temporaires.py` | `test_gros_poisson_fusion_partielle_blocs_absents_types_distincts`, `test_gros_poisson_sans_homologue_ne_cree_rien_et_explique_absence_effet`, rejet Zombie/profil falsifié, `test_gros_poisson_fatigue_par_uuid_conservee_apres_pertes_et_retour`. Valident le socle, pas un ordre actif dans `combat_entre_generaux`. |
| Même fichier | `test_simulation_muraille_moral_blessures_identique_aux_pertes_reelles`, classement recalculé, moral/blessures d’origine, lecture sans nettoyage, refus explicite Bouclier/Propagation. Équivalence sur les cas couverts, pas simulation complète de toutes les capacités. |
| Même fichier | Double réservation, liens/copies, racine privée, interruptions, XP explicite unique, pertes sans restauration. Les tests `test_publication_conserve_pertes_blessures_origines_et_rapport` et `test_interruption_privee_plateau_intact_reprise_sans_rejeu` injectent une intervention technique autour de la résolution : ils prouvent la publication du groupe, pas le duel Gros_poisson intégré. |
| `.dev/tests/test_participations_permissions.py` | `test_copie_privee_pertes_et_blessures_gardent_droits_reels`, `test_changement_uid_ou_gid_detecte_avant_toute_perte` : vrais contrôles Linux root, non remplaçables par Windows. |
| `.dev/tests/test_ordres_pipeline_v2.py`, `test_ordres_confrontation_v2.py`, `test_ordres_effets_v2.py` | Acquisition, PC du donneur, contre-ordres, profils privés, destinataires, effets réels, Rafale avant Bouclier, interruption, rapports privés. Certains tests portent sur des façades préparatoires : ajouter des scénarios via le duel et le tour réel. |
| `.dev/tests/test_qg_effets_v2.py`, `test_formations_v2.py`, `test_bouclier_vivant.py` | Transmission jusqu’à fin du duel malgré destruction du QG, réception Zombie filtrée avant comparaison, Cruelle calculée sur le donneur, matrice et positions non compactées, résistance et choix de Spore. Garde-fous essentiels lors du passage aux participants temporaires. |
| `.dev/tests/test_ordres_calculs_v2.py`, `test_ordres_conception_v2.py` | Quotas Ralliement, condition/flanc de Dernière charge, exclusions/sélection de Muraille, absence d’activation. Ne prouvent ni réanimation ni orchestration. |
| `.dev/tests/test_soldats_formation.py`, `test_progression.py`, `test_unites_v2.py`, `test_cycle_survie.py`, `test_combats_camps.py` | Identités/blessures/XP, apprentissage et progression, capacités, capture/publication et camps. À conserver lors de l’intégration transversale. |

### 11.2 Scénarios nécessaires pour les futurs changements

1. **Moteur inchangé sans ordre nouveau** : mêmes résultats de blocs et victimes,
   mêmes blessures/XP, consommation du RNG, ordre de manœuvre, effets raciaux et
   rapports. Préserver les cas vides, mortalité simultanée, fatigue identique ou
   différente, formation lourde au seuil et perte de QG avant repeuplement.
2. **Gros_poisson complet** : QG bénéficiaire ou prêteur, positions actives/camps,
   acquisition/nature/réception, profil privé absent ou falsifié, unités interdites,
   blocs physiquement absents, types différents, fusion partielle et aucun
   homologue. Vérifier le motif final et l’absence de dossier créé par les phases
   ultérieures. Non-prêtés inchangés, pas de quotas de pertes par propriétaire,
   prêteur combattant ensuite avec ses seuls survivants et ses propres bonus.
3. **État individuel et capacités** : fatigue hétérogène selon la formule validée,
   blessures/XP différents dans le même bloc, moral du bénéficiaire, seuil lourd,
   effets Orc/Cruelle/Discours/Hérisson, Rafale et immunité lourde, soutiens,
   Bouclier et conversion adverse selon le contrat validé. Bilan exact par UUID.
4. **Muraille** : même état et mêmes tirages d’entrée entre prévision et résolution
   élémentaire réelle ; aucun octet, blessure, XP, QG ou RNG réel modifié par une
   simulation. Tester capacités, QG hors Avant, contextes différents par candidat,
   égalités de positions alliées, ordre d’entrée inversé et recalcul après pertes.
   Tester exclusions et absence d’Avant en manœuvre, mort du général, disparition
   du QG, dissolution, retours après victoire et défaite du camp.
5. **Ralliement** : seuls les morts de l’événement admissible, quotas 0/4/5/9/10 par
   type, type absent, bloc d’accueil validé, allié suivant et défenseur exacts,
   mêmes UUID/XP/blessures, destination selon existence du général d’origine,
   pas de réanimation double ni réutilisation d’une copie publique.
6. **Dernière charge** : général précédent vivant/vaincu, chaque casse G/g/D/d,
   flanc absent ou vide, remplaçant normal préservé pendant le choc puis retrouvé,
   fatigue limitée aux relevés, mort finale même si moral élevé, aucune manœuvre
   des relevés. Pas de recréation d’un autre flanc ni attribution d’XP fictive.
7. **Transactions et Linux** : interrompre après pertes, réanimation, conversion
   et préparation des rapports ; aucun état partiel public ni rejeu automatique.
   Vérifier les UUID après changement d’inode dû à la publication, UID/GID/modes,
   liens interdits, changement de propriétaire détecté, retours et accès aux
   dossiers. Utiliser exclusivement des parties temporaires isolées.

Après chaque modification Python future : compilation des fichiers concernés,
tests ciblés, puis suite complète pour toute modification du moteur :

```bash
python3 -B -m unittest discover -s .dev/tests -v
```

Les caches de compilation seront isolés et jamais commités. Les contrôles exigeant
root seront exécutés séparément sous Linux et comptés une seule fois. L’activation
ne doit pas reposer sur un résultat Windows ou sur des permissions simulées.

## 12. Questions de gameplay encore bloquantes

| Question encore ouverte | Pourquoi elle bloque | Travaux possibles sans la trancher |
| --- | --- | --- |
| Gros_poisson : comment calculer dégâts et résistance pour des soldats frais et fatigués du même type dans le même bloc ? | Le calcul actuel utilise une valeur commune pour attaque et résistance ; aucune moyenne ou succession de sous-duels n’est validée. | Vue par UUID, tests de conservation et refactoring équivalent des cas homogènes. Pas d’activation. |
| Gros_poisson : quelle formation/composition sert au seuil lourd et aux bonus raciaux, et comment participent les soutiens ? | Les lecteurs actuels n’utilisent pas tous la même référence ; choisir silencieusement changerait les bonus et le sort des soutiens. | Rendre les entrées explicites et recenser leurs usages. |
| Gros_poisson : sort d’un prêté converti par Spore adverse ? | Type, propriétaire et destination changent dans la conversion actuelle, contrairement au retour ordinaire du prêt. | Garder l’authentification stricte ; préparer l’événement de conversion sans décider d’une restitution. |
| Gros_poisson : même général désigné dans les deux rôles ? | Cas non défini, aujourd’hui refusé explicitement par la sélection. | Conserver ce refus ; aucune duplication ou auto-fusion implicite. |
| Ralliement : quels morts sélectionner, et quel état physique autorise leur réanimation avec blessures conservées ? | `detruit` n’est pas une autorisation de ressusciter ; la limite de blessures ne définit pas leur nouveau statut physique. | Journal de pertes et opération technique à droits bornés, sans exécuter de réanimation. |
| Ralliement : bloc d’accueil si plusieurs conviennent, durée du prêt et destination si l’origine a disparu ? | Ces choix déterminent présence, bonus et retour. Le contrat de Muraille ne vaut pas automatiquement pour Ralliement. | Quotas et identification du suivant ; pas de placement définitif inventé. |
| Dernière charge : quels morts du flanc sont éligibles et quelles blessures ont-ils à la relève ? | Nécessaire avant matérialisation et avant application du moral pendant leur charge. | Précondition, substitution de phase et finalisation technique préparatoires. |

La priorité d’une mémoire scolaire Zombie sur les tirages 85/15 reste également
ouverte, mais **ne bloque pas la préparation architecturale des quatre ordres**.
La base conserve la mémoire et applique le tirage existant ; cet audit ne propose
pas de modifier cette progression.

L’attribution des jetons encore absents, la représentation des événements, la
transmission du camp défenseur et l’acheminement des orphelins sont des travaux de
conception technique à faire valider, pas des prétextes pour rouvrir les décisions
acquises. Le score de Muraille, les fusions partielles, les restrictions Zombies,
les UUID conservés et la mort finale de Dernière charge sont déjà fixés.

**Suite recommandée après accord :** préparer d’abord la vue commune des
participants et la résolution de blocs partagée, puis intégrer Gros_poisson une
fois ses règles restantes tranchées. Construire ensuite le cycle des morts et
des survivants détachés pour Muraille, Ralliement et Dernière charge. Aucun travail
fonctionnel n’est commencé par le présent document.
