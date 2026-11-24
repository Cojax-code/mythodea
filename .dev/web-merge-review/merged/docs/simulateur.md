# Simulateur de bataille v2.0

## Référence et audit

<<<<<<< C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\ours
Le simulateur utilise un instantané des sources locales de la branche `v2.0`,
identifié par `snapshot` et les empreintes SHA-256 de `backend/engine.lock.json`.
Le champ `commit` indique le commit de base, pas un commit contenant les changements
locaux. `scripts/sync_engine.py --source ../..` exporte le catalogue officiel et
renouvelle le verrou ; `scripts/prepare_engine.py --source ../..` prépare une copie
vérifiée. Chaque worker contrôle les empreintes avant exécution dans Bubblewrap.
Aucun calcul de combat n'est dupliqué dans le navigateur.

Trois orientations, progression classique et spécifique, places actives débloquées,
étendards individuels et exceptions zombies proviennent du moteur commun.
=======
Le moteur est verrouillé sur `Cojax-code/mythodea`, branche `v2.0`, commit
`3391613a4dcd81798b947754a69dd6b745e89d50`, qui inclut les exclusions de moral et de soins zombies.
La révision `3391613` est identifiée par les SHA-256 des 27 modules.
`prepare_engine.py --source ../Mythodea_code` extrait les blobs de ce commit et
vérifie chaque source ; sans `--source`, le script récupère le dépôt sur GitHub.
Le worker vérifie ensuite exactement les sources montées. Aucun calcul ne lit
directement le dépôt moteur.

| Zone | Ancien simulateur (`6326a607`) | Version mise à niveau |
| --- | --- | --- |
| Sources Python | 19 modules | 27 modules, SHA-256 dans `backend/engine.lock.json` |
| Camps | Profil Survie j1 contre bot | Profil classique j1 contre j2, territoire jetable `terrain1` |
| Unités | Quatre types historiques | Douze types officiels, capacités et compatibilité de nature |
| Généraux | Fiche neutre ; orientation seulement visuelle | Niveau, nature, trait, PC, moral, état zombie et sélection privée |
| Étiquettes | Absentes du contrat de bataille | Sélection et rang ; conversion interne vers le profil officiel |
| QG / Messager | Absents | QG explicite par camp, Messagers dans les blocs, instantané territorial |
| Ordres | Ancien `1-2` | Refusé par l'API et retiré de l'interface |
| Pertes | Différence d'effectifs | Bilan net, destructions, créations, conversions reçues, blessures avant/après soins |
| Génération | Composition aléatoire seulement | Progression officielle jusqu'au niveau choisi et composition compatible |
| Isolation | Bubblewrap, quotas et graine | Garanties conservées, vérification de fichiers renforcée, flux Spore initialisé |
>>>>>>> C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\web

## Bataille exécutée

Chaque camp dispose de 1 à 4 généraux sur des positions distinctes de 1 à 4.
La file est résolue par `combats.resoudre_combat_v15` ou
`combats.resoudre_combat_off_def`. Les survivants peuvent affronter les généraux
suivants. Chaque duel utilise le choc initial, les manœuvres et les capacités
spéciales officielles. OFF/DEF distingue le défenseur dans la décision d’impasse, sans bonus défensif.
La configuration future d'engagement frontal par terrain n'est pas exposée.

L'adaptateur crée les dossiers et les soldats via `generaux.creer_general` et
`unites.creer_officielle`, enregistre les profils dans `progression.json`, écrit
`etiquettes_actives.txt` et la déclaration `QG.txt`, puis utilise les points
d'entrée de combat. Aucun chemin, fichier arbitraire ou commande client n'est accepté.
Les recettes et permissions du Messager sont matérialisées dans le plateau privé.

Le cycle territorial inclut `soldats.bataille_complete`, la régulation des
propagations par `unites.terminer_territoire` et les soins de victoire du Chaman.
Les soldats démarrent sans blessures ni batailles passées ; le résultat distingue
les blessures avant les soins de fin de bataille et celles restant après soins.
La progression de campagne, l'hôpital et les résurrections ne sont pas simulés.

Le QG est réservé aux Stratèges non zombies, hybrides à dominante Stratège inclus.
Il n'est jamais choisi automatiquement par ses PC. Une double déclaration
est refusée. Ses effets sont figés avec les généraux présents ; ils cessent à sa
destruction, sans remplaçant. Le Messager ajoute une seule fois les PC calculés
par le moteur ; son amplification ne s'applique pas aux bonus personnels du QG.
Le journal et `calculations` montrent les bonus personnels + QG et les malus
de valeur réellement lus pendant le combat. `morale_observations` enregistre
le moral transmis par le moteur au calcul des pertes, sans formule locale.

L'observateur enveloppe temporairement les fonctions déjà utilisées par le moteur,
appelle chacune une seule fois et ne consomme aucun tirage aléatoire. Il restaure
les fonctions à la sortie, y compris en cas d'erreur. Les tests comparent le
rapport intégral et les survivants à un worker indépendant sans cet observateur.

## Profils synthétiques et limites

La génération appelle `nouvelles_caracteristiques` puis `monter_niveau` pour chaque
<<<<<<< C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\ours
niveau demandé. Elle utilise les probabilités du moteur verrouillé.
Le bouton est réutilisable ; son résultat remplace le profil, pas les soldats.
=======
niveau demandé. Elle utilise les probabilités actuelles du moteur, selon la nature et le trait.
Les hybrides gagnent naturellement PC et moral ; les instinctifs peuvent gagner
des PC par roulette. Les Stratèges disposent de 10 % de moral dans chaque table
de trait, avant redistribution des catégories indisponibles. Les connaissances
de rang 1 ne sont pas bornées par le quota scolaire. La sélection suit le plafond
de nature (trois/une) ; la place zombie supplémentaire est réservée
à mort_vivant. Une nature demandée conditionne le tirage de création officiel.
Les niveaux après zombification utilisent la progression zombie, sans gains ordinaires.
Le formulaire conserve les récompenses par niveau. Chaque bouton « Aléatoire »
appelle `monter_niveau` sur les acquis précédents et tire la récompense complète,
catégorie et valeur, avec les poids du moteur. Les paliers garantis restent prioritaires.
Les choix manuels d'unités de roulette respectent la dominante ; les acquisitions
croisées de l'École restent distinctes.
« Tirer les gains naturels » appelle `appliquer_gains_naturels` dans le worker
isolé, puis ajoute une seule fois les récompenses statistiques sélectionnées.
Les relances ne modifient ni récompenses, ni acquisitions, ni activations.
Avant zombification les gains vivants restent acquis ; après, aucun gain naturel
ordinaire n'est ajouté. Une réponse devenue obsolète après changement de profil est ignorée.
>>>>>>> C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\web
Le remplissage des unités est un tirage de composition local, sans résolution
de combat, qui respecte les natures et exclut les soutiens du tirage automatique.
Les Messagers et le Gros zombie se placent explicitement dans les blocs.

Les PC peuvent être augmentés ou diminués ; changer le niveau manuellement ne
<<<<<<< C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\ours
recalcule pas le parcours. Les connaissances et rangs sont des données synthétiques,
sans supposer une origine scolaire : une étiquette peut aussi provenir de la roulette.
Les champs `active_slots` et `banner_level` représentent les capacités débloquées.
L'adaptateur vérifie les parcours possibles en appelant les étapes spécifiques du
moteur ; l'activation passe par `selection_etiquettes`. `banner_block` choisit un bloc
ou vaut `null` ; son fichier est contrôlé par `etendards.declaration`.
L'ancien champ facultatif `permanent` est accepté comme métadonnée sans effet.

Bornes du service, sans modification du jeu : niveaux 0–50, PC 0–1000, moral
0–100, au plus huit généraux. Capacité ordinaire de 20 places ; capacité zombie
=======
recalcule pas le parcours. Dans le formulaire, toutes les étiquettes sélectionnées
sont modifiables jusqu’au rang maximal du niveau. Le contrat API historique accepte
encore le champ historique `permanent`, sans verrouiller les rangs. Les connaissances sont des
acquis synthétiques de roulette ; les améliorations utilisent `apprendre_etiquette`
et l’activation `selection_etiquettes`. Aucun parcours de carrière n’est inventé.
Les profils manuels servent aux expériences : leur carrière et l'acquisition
historique de chaque unité ne sont pas reconstituées. Le serveur exige cependant
un déblocage compatible pour toute unité évoluée, Messager compris. L'évolution
104 autorise la Cavalerie lourde ; `quest_heavy_cavalry` déclare son acquisition
par quête, indépendamment de la roulette. La Forge transforme des unités déjà
débloquées ; elle n'est jamais une source de déblocage. Le serveur ne vérifie pas
les preuves d'une campagne réelle. Un changement d'orientation réinitialise les
acquis, statistiques, unités et QG dans le formulaire. Une étiquette désactivée
reste connue, et l'étape des étiquettes est masquée quand aucune n'est acquise.

Bornes du service, sans modification du jeu : niveaux 0–50, moral 0–100,
au plus huit généraux. Les PC sont des entiers positifs ou nuls sans plafond de jeu. Capacité ordinaire de 20 places ; capacité zombie
>>>>>>> C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\web
calculée par le moteur. Un Messager prend cinq places et un Gros zombie dix.
Un seul Gros zombie est autorisé, accompagné de Zombies ordinaires. Chaque bloc
a un type de combattant, avec des soutiens distincts. Les scénarios très coûteux
restent soumis aux quotas : un dépassement produit une erreur, jamais un résultat
de bataille partiel présenté comme réussi.

Non pris en charge : fatigue acquise par déplacement, renforts en cascade,
retraites de surnombre, fuite volontaire, carte et directions d'attaque, terrains,
météo, formation, carrières antérieures des soldats, campagne et ressources.
Ajouter la cascade demanderait ses files de renforts, ses destinations et son
cycle de décisions officiel ; aucune de ces fonctions n'est affichée comme active.
Le comparateur théorique dans l'autre onglet conserve ses limites affichées et
ne constitue pas le moteur du simulateur de bataille.

<<<<<<< C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\ours
## Limites conservées

Les règles communes sont celles de `REGLES_V2.md` : le plancher de valeur est 0 %,
les capacités hybrides et les étendards sont actifs. Les règles encore ouvertes du
Bouclier vivant restent ouvertes ; sa résistance spéciale ne reçoit pas l'étendard.

Point de revue, sans correction locale : `bouclier_vivant._puissance_bloc_adverse`
emploie valeur de base et avantage de type pour les chocs contre le bouclier,
sans les fonctions de bonus/malus d'étiquettes de `combat_bloc`. Ce comportement
est reproduit et comparé au moteur ; sa conformité au gameplay souhaité devra
être confirmée côté moteur. Le moral saisi d'un stratège pur est également traité
selon le code officiel, qui le ramène à zéro avant les effets de composition.
=======
## Limites restantes

Le moteur détecte une impasse seulement lorsque toutes les paires actives sont
nulles. Une paire nulle n'empêche pas les autres blocs ou généraux de combattre.
En OFF/DEF, l'attaquant doit partir ; en OFF/OFF, les deux camps doivent partir.
Le simulateur n'a ni carte ni destination : `battle_resolution` expose la décision,
mais `outcome` reste `contested` tant que les deux camps sont présents. Aucune
retraite physique ni victoire défensive fictive n'est annoncée. Le QG détruit
perd son soutien ; la retraite acceptée du QG est testée dans la cascade moteur,
qui seule dispose des réservations nécessaires. Le simulateur ne la fabrique pas.

La phase spéciale du Bouclier vivant conserve sa formule officielle dédiée.
L'amélioration des rangs par roulette et les destinations de retraite classiques
et bots restent des décisions moteur ouvertes. Le passage Raspberry Pi conserve
la procédure existante du dépôt moteur, `TESTS_LINUX_SURVIE.md`.

## Configuration progressive

Le formulaire suit **Type → Niveau → Génération des statistiques → PC/Moral
→ Étiquettes → QG et bloc → Unités → Combat**. Le type inclut directement
Général zombie, sans case séparée. La nature d’origine reste dans les données
internes du profil zombie. Le moral est masqué pour le stratège et le zombie ;
les PC restent disponibles, y compris pour les instinctifs qui peuvent en gagner.
Le tirage est réutilisable, respecte le type et le niveau choisis et utilise
les API officielles. Les statistiques manuelles ne changent pas avec le niveau.

Chaque étiquette sélectionnée est connue et active dans le profil synthétique,
sans statut permanent exposé. Son rang peut monter ou descendre jusqu’au maximum
du niveau. Le simulateur autorise une étiquette ordinaire avant N5, puis deux
à N5 et trois à N10 chez le stratège et son hybride ; l’instinctif et son hybride
restent à une. Le zombie conserve le plafond de sa nature d’origine et une place
réservée exclusivement à `mort_vivant`. Ces limites expérimentales ne changent
ni l’apprentissage ni l’activation officielle du jeu réel.

Toutes les unités compatibles sont sélectionnables indépendamment du niveau
et des acquisitions de carrière. Messager et Gros zombie restent des unités
placées dans les blocs. Le Gros zombie exige un cadavre déclaré, dix places,
des Zombies ordinaires et l’absence d’un second Gros zombie. Les ressources
et le rituel de campagne ne sont pas exécutés. Le moral et les soins zombies
sont neutralisés par le moteur, sans suppression des anciennes valeurs.
Spore, Propagation et la réserve du Bouclier vivant restent inchangés.

Un seul QG peut être choisi par camp. Son bloc (`qg_block`) est une donnée de
placement conservée dans la configuration ; le rôle et ses effets officiels
restent au niveau du général, sans bonus de bloc ajouté.

Les saisies devenues incompatibles et les effectifs excédentaires sont conservés.
Le clic sur Lancer le combat affiche ensemble les erreurs en rouge immédiatement
sous le bouton, avec camp, général et bloc si applicable. Aucun appel de combat
n’est envoyé tant que ces erreurs subsistent ; elles disparaissent à la correction.
Les rangs trop élevés sont ramenés au plafond lors d’une baisse de niveau.
Les contrôles serveur et l’isolation Bubblewrap restent obligatoires.
>>>>>>> C:\Users\marti\1.cree_manuel\perso\OTW\linux\Mythodea\Mythodea_code\.dev\web-merge-review\web

## API

`GET /api/simulator/catalog` fournit unités et définitions officielles, blocs,
natures, traits, étiquettes, rang maximal par niveau, limites et commit.

`POST /api/simulator/options` reçoit un objet vide et fournit les évolutions
admissibles et compatibilités obtenues par les API officielles, les capacités
zombies par niveau et les limites de sélection du formulaire par niveau et nature.
L’appel utilise le même worker isolé et le même verrou de concurrence.

Le champ `unlocked_evolutions` déclare les acquisitions et ses IDs sont validés.
Son absence ne débloque aucune unité évoluée. `quest_heavy_cavalry` est un booléen
facultatif pour la Cavalerie lourde obtenue par quête. `corpse_available` déclare la condition
spéciale du Gros zombie. Les restrictions de nature et d’état zombie sont contrôlées
pour tous les profils, même sans ces champs.

`POST /api/simulator/generate` reçoit `{"level":10,"seed":42}` ou ajoute
`nature`, `zombie` et `zombie_levels` pour conserver le type choisi.
`seed:null` demande une nouvelle graine, renvoyée avec le profil.
La génération utilise le même bac à sable et le même verrou de concurrence.

`POST /api/simulator/natural` accepte le même contrat que `generate` et renvoie
uniquement `pc`, `morale`, `seed` et `engine_commit`. Les statistiques partent de
zéro ; les récompenses sont ajoutées par le formulaire sans changer leurs choix.
`POST /api/simulator/reward` reçoit `{"profile": <profil avant le niveau>, "seed": null}`.
Il appelle `monter_niveau` et renvoie seulement `reward`, `seed` et `engine_commit`.
Le bouton par niveau transmet les acquis des niveaux précédents ; la récompense
tirée suit le trait, la dominante, les exclusions, les paliers et la règle zombie
du moteur. Les deux routes utilisent le même worker Bubblewrap et les mêmes quotas.

`POST /api/simulator/run` reçoit :

```json
{
  "seed": 42,
  "mode": "OFF/DEF",
  "defender": "B",
  "armies": {
    "A": {"generals": [{
      "position": 1, "qg": true,
      "profile": {
        "level": 10, "nature": "stratege", "trait": "leader",
        "pc": 40, "morale": 0, "zombie": false, "zombie_levels": 0,
        "labels": {"infanterie": 2}, "active_slots": 3, "banner_level": 0, "active": ["infanterie"]
      },
      "blocks": {
        "avant": {"unit": "archer", "count": 15, "messengers": 1, "shield": false},
        "droite": {"unit": "archer", "count": 0},
        "gauche": {"unit": "archer", "count": 0},
        "arriere": {"unit": "archer", "count": 0}
      }
    }]},
    "B": {"blocks": {
      "avant": {"unit": "piquier", "count": 20},
      "droite": {"unit": "archer", "count": 0},
      "gauche": {"unit": "archer", "count": 0},
      "arriere": {"unit": "archer", "count": 0}
    }}
  }
}
```

Le contrat historique à un bloc par position reste accepté avec profil neutre.
`profile` et `qg` sont optionnels ; l'ancien champ `order` n'accepte que `""`.
Sans `mode`/`defender`, le mode est OFF/OFF ; s'ils sont fournis, les deux sont
requis (`defender:null` en OFF/OFF). Aucune autre clé n'est acceptée.

La réponse inclut commit, version Python, graine, configuration exacte, résultat,
avant/après par général/bloc, engagements, annotations, QG initial, blessures et
journal intégral. `losses` conserve sa compatibilité comme **bilan net**
avant − après : une valeur négative peut provenir de propagation/conversion.
Les destructions et les conversions ne doivent pas être déduites de ce seul champ.
Les fractions officielles restent exactes durant le combat ; seule la réponse JSON
convertit les fractions non entières en nombres pour l'affichage.

Erreurs : 400 configuration invalide (y compris règles vérifiées dans le worker),
403 requête intersite, 413 corps > 8 Kio, 429 service occupé, 503 moteur/isolation
indisponible, 504 délai dépassé. Aucun de ces codes ne désigne un vainqueur.

## Isolation et reproductibilité

Le serveur non root lance Bubblewrap avec espaces utilisateur, PID et réseau
séparés, environnement vidé et aucune capacité. `/game` (16 Mio) et `/tmp`
(8 Mio) sont des tmpfs jetables ; `/engine`, le code backend et le système
nécessaire sont montés en lecture seule. Ni vraie partie ni home de joueur n'est monté.
Le worker vérifie ses montages avant tout accès métier. Quotas conservés :
256 Mio d'espace d'adressage, 5 s CPU, 10 s murales, fichier/rapport 1 Mio,
64 descripteurs, 16 processus. Le timeout tue tout le groupe de processus.

Avant lancement, le runner refuse source modifiée, lien symbolique, lien physique,
FIFO ou fichier supplémentaire ; il ouvre les sources sans suivre les liens,
contrôle l'inode et monte une copie vérifiée. Les répertoires parents liés sont
également refusés. La validation n'accepte aucun chemin fourni par l'utilisateur.

La graine initialise des flux distincts dans le worker : combat et généraux
(`seed`), soldats (`seed ^ 0x501D`), bouclier/Spore (`seed ^ 0xB0C1`), progression
(`seed ^ 0x1234`) et identités techniques (`seed ^ 0x1D3`). Ces dernières sont
déterministes uniquement dans le processus jetable pour reproduire aussi les
journaux et la régulation des Zombies ; ce ne sont pas des identités de production.
Comparer à version moteur, version Python et configuration identiques. Aucun état
ni fonction modifiée du worker ne survit à sa destruction.

## Tests et lancement

La synchronisation a été vérifiée sous WSL avec 52 tests Python réussis
(20 ciblés, 31 autres régressions, puis un contrôle de préparation locale).
Les deux parcours Chrome existants ont réussi, y compris les nouvelles vérifications
des impasses et de la place zombie. Les tests de parité comparent directement
le journal et les survivants avec le moteur Python sans adaptateur ni observateur.
La dernière modification Survie ne change pas les fonctions utilisées par le
simulateur classique ; les 27 empreintes ont été revérifiées après son intégration.

Suivre le [README](../README.md) pour préparer WSL et le moteur. Sous WSL :

```bash
export MYTHODEA_ENGINE_PATH="$PWD/.runtime/engine-3391613"
.venv/bin/python -B -m unittest discover -s tests -v
```

`tests/reference_worker.py` construit indépendamment le plateau et appelle le
moteur sans l'adaptateur ni l'observateur du simulateur. Les tests vérifient
rapports et survivants identiques, replays, 1v2 à 4v4, modes, PC/rangs/activation,
QG/Messager, destruction du QG, malus extrêmes, les douze unités, blessures,
Zombies et attaques sur les fichiers. Les tests de réseau, ressources, fichiers
hôtes, moteur en lecture seule, concurrence et timeout sont exécutés sous Linux.

Pour les parcours navigateur, avec le serveur lancé dans un autre terminal et
Chrome installé sur le système qui exécute Playwright :

```bash
.venv/bin/python -m pip install playwright
.venv/bin/python -B tests/browser_smoke.py --channel chrome
.venv/bin/python -B tests/browser_modes.py --channel chrome
.venv/bin/python -B tests/browser_configuration.py
.venv/bin/python -B tests/browser_progression_audit.py
```

Playwright peut aussi tourner sous Windows contre le serveur WSL sur localhost.
Les captures vont dans `test-results/` (ignoré par Git). Les parcours couvrent
profils, étiquettes, génération répétée, PC modifiables, QG et Messagers,
permutation des positions, quatre généraux, affichage mobile, clavier/tactile,
préservation des saisies, journal fidèle, modes et erreurs du serveur.

## Avant publication publique

- Relancer la suite sur le Linux cible avec son véritable Bubblewrap ; aucun
  contournement des espaces de noms et aucun lancement du serveur en root.
- Installer les dépendances verrouillées, vérifier le commit/SHA-256 et conserver
  un environnement Python cohérent pour le rejeu. Conserver les runtimes hors Git.
- Le service écoute uniquement localhost et refuse les Host étrangers. Configurer
  explicitement le domaine de confiance et un reverse proxy HTTPS avant exposition.
- Définir une limitation de débit et d'accès adaptée : une seule requête de moteur
  simultanée est admise par processus. Plusieurs processus multiplient ce quota.
- Vérifier les limites, journaux serveur, erreurs 429/503/504 et absence d'exposition
  des fichiers backend. Les tests ne remplacent pas un audit du déploiement cible.
- Confirmer les décisions de gameplay dans le moteur, mettre à jour ses références
  et régressions, puis préparer un nouveau verrou du simulateur. Ne jamais modifier
  les formules web pour anticiper une règle encore absente du moteur.
