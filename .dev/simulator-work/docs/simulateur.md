# Simulateur de bataille v2.0

## Référence et audit

Le simulateur utilise un instantané des sources locales de la branche `v2.0`,
identifié par `snapshot` et les empreintes SHA-256 de `backend/engine.lock.json`.
Le champ `commit` indique le commit de base, pas un commit contenant les changements
locaux. `scripts/sync_engine.py --source ../..` exporte le catalogue officiel et
renouvelle le verrou ; `scripts/prepare_engine.py --source ../..` prépare une copie
vérifiée. Chaque worker contrôle les empreintes avant exécution dans Bubblewrap.
Aucun calcul de combat n'est dupliqué dans le navigateur.

Trois orientations, progression classique et spécifique, places actives débloquées,
étendards individuels et exceptions zombies proviennent du moteur commun.

## Bataille exécutée

Chaque camp dispose de 1 à 4 généraux sur des positions distinctes de 1 à 4.
La file est résolue par `combats.resoudre_combat_v15` ou
`combats.resoudre_combat_off_def`. Les survivants peuvent affronter les généraux
suivants. Chaque duel utilise le choc initial, les manœuvres et les capacités
spéciales officielles. OFF/DEF ajoute les rôles au rapport, sans bonus défensif.
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

Le QG n'est jamais choisi automatiquement par ses PC. Une double déclaration
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
niveau demandé. Elle utilise les probabilités du moteur verrouillé.
Le bouton est réutilisable ; son résultat remplace le profil, pas les soldats.
Le remplissage des unités est un tirage de composition local, sans résolution
de combat, qui respecte les natures et exclut les soutiens du tirage automatique.
Les Messagers et le Gros zombie se placent explicitement dans les blocs.

Les PC peuvent être augmentés ou diminués ; changer le niveau manuellement ne
recalcule pas le parcours. Les connaissances et rangs sont des données synthétiques,
sans supposer une origine scolaire : une étiquette peut aussi provenir de la roulette.
Les champs `active_slots` et `banner_level` représentent les capacités débloquées.
L'adaptateur vérifie les parcours possibles en appelant les étapes spécifiques du
moteur ; l'activation passe par `selection_etiquettes`. `banner_block` choisit un bloc
ou vaut `null` ; son fichier est contrôlé par `etendards.declaration`.
L'ancien champ facultatif `permanent` est accepté comme métadonnée sans effet.

Bornes du service, sans modification du jeu : niveaux 0–50, PC 0–1000, moral
0–100, au plus huit généraux. Capacité ordinaire de 20 places ; capacité zombie
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

## API

`GET /api/simulator/catalog` fournit unités et définitions officielles, blocs,
natures, traits, étiquettes, rang maximal par niveau, limites et commit.

`POST /api/simulator/generate` reçoit `{"level":10,"seed":42}`. `seed:null`
demande une nouvelle graine, renvoyée avec `profile` et `unlocked_evolutions`.
La génération utilise le même bac à sable et le même verrou de concurrence.

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

Suivre le [README](../README.md) pour préparer WSL et le moteur. Sous WSL :

```bash
export MYTHODEA_ENGINE_PATH="$PWD/.runtime/engine-b31b842"
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

Aucune publication, aucun commit ni push n'est effectué par cette mise à niveau.
