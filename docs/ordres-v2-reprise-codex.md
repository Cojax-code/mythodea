# Reprise du chantier des ordres V2 — état réel

**Entrée de reprise courte.** État fonctionnel ci-dessous ; [audit d'architecture](ordres-v2-audit-architecture.md) pour les dépendances et fonctions réutilisables ; [contrats en vigueur](ordres-v2-preparation.md) et SPEC pour les règles. Les anciens bilans du Lot A et des étapes précédentes restent consultables dans l'historique Git (avant l'élagage documentaire du 27 octobre 2026).

## Lot B — reprise depuis d32fdeb, 27 octobre 2026

**Cette section fait foi ; toutes les sections suivantes sont des archives.**

### État de départ et périmètre

- Branche propre `feat/ordres-v2`, HEAD et `git ls-remote origin
  refs/heads/feat/ordres-v2` identiques à
  `d32fdebcd752fdb90f6b52a3645054e731e71a01`. Aucun pull nécessaire.
- Ce commit contenait déjà la politique Zombie, les tirages 85/15 puis 50/50,
  le compteur de gains de capacité, les réservations 1017/1018 et le sélecteur
  de Muraille. Ils ont été vérifiés et complétés, pas réimplémentés.
- Les documents précédents et plusieurs tests décrivaient encore l'ancien
  apprentissage/progression Zombie. Les attentes concernées ont été adaptées
  aux nouvelles décisions explicites ; les régressions étrangères sont conservées.
- Aucun merge vers `v2.0`, aucune modification de Mythodea-web. Livraison par
  commit local sur `feat/ordres-v2`, sans push demandé dans cette reprise.

### Fonctionnalités réellement actives

- **Politique Général Zombie** : seul `etat_zombie` privé fait foi, nature et
  caractéristiques d'origine conservées. Spora-adicte/Propagafion apprenables
  dans les quatre natures ; non-Zombies exclus de leur apprentissage/émission.
  Propagafion appris fonctionne aussi depuis un QG instinctif Zombie, en
  conservant acquisition, déclaration QG, calcul PC et confrontation.
- **Réception distincte de l'émission** : le contrôle du destinataire conserve
  l'interdiction des ordres non-Zombies pour un général Zombie. Un général
  ordinaire peut toujours recevoir un effet collectif sans pouvoir l'apprendre.
  Cette distinction corrige l'utilisation du contrôle d'apprentissage comme
  contrôle de réception dans la base. Les profils publics ne font jamais foi.
- **Récompenses Zombie** : distribution exacte testée aux frontières ; rejet
  complet des doublons via poids conditionnels 170:15, capacité automatique si
  les deux ordres sont connus. `gains_capacite_zombie` empêche le double bonus.
  Les anciennes places sont conservées ; aucun tirage rétroactif. Le reçu de
  progression empêche un nouveau tirage après interruption de publication.
- **Spora-adicte** est apprenable et mémorisable à l'École, mais son effet reste
  désactivé. Une mémoire seule ne donne jamais un droit d'exécution.

### Fonctions préparatoires, sans activation des quatre ordres

- **Gros_poisson** : lecture de `2-6-bénéficiaire-prêteur`, dans cet ordre,
  avec deux positions numériques dans `specification`. Seul ce jeton accepte
  quatre champs ; il demeure indisponible à l'apprentissage et à l'exécution.
- `GroupeTemporaire.selections_gros_poisson()` sélectionne les couples bloc/type
  communs des deux alliés. Les autres restent intacts. Sans homologue : résultat
  vide et motif prêt pour le rapport, sans publication d'un effet inexistant.
  Profils privés et restriction commune des unités sans cerveau sont vérifiés.
  Les règles Zombie s'appliquent au bénéficiaire comme au prêteur.
- `fatigues_origine()` conserve une valeur par UUID vivant, issue de son
  général d'origine, même après pertes. Ce relevé ne définit pas les dégâts et
  résistances d'un mélange frais/fatigués. Aucun raccordement au duel réel tant
  que ce calcul et les cas de capacités restent ouverts.
- **Muraille** : `simuler_avants_muraille()` simule Avant contre Avant, après
  moral, limites de blessures et XP, avec statistiques d'origine et contexte
  d'ordres fourni. Les fonctions de sélection des victimes et de sauvetage sont
  partagées avec les pertes réelles, sans changer leur comportement.
- `prochain_avant_muraille()` relit les survivants, recalcule les scores
  `ennemis éliminés - alliés perdus` et choisit selon score, position d'origine,
  puis hasard reproductible. Exclusions QG_nommade et Réserve stratégique.
  Les simulations copient le générateur et ne consomment pas les tirages réels.
- `lire_blocs_general(lecture_seule=True)` évite les nettoyages et créations de
  dossiers de la lecture historique : un bloc invalide ou mixte est refusé.
  Cette option sert aux prévisions ; le comportement du combat réel est conservé.
- La simulation complète des capacités Bouclier/Spore/Propagation/soutiens et
  les contextes QG par candidat restent à raccorder. Les capacités non simulées
  provoquent un refus explicite, même pour un Bouclier situé hors Avant.
- **Ralliement et Dernière charge** : formules et préconditions antérieures
  conservées ; aucune résurrection, sélection de morts ou destination inventée.
- Les retours sans général, y compris après défaite territoriale, sont désormais
  définis vers le village d'origine. Leur persistance `unites_sans_general`
  relève toujours du lot C ; aucune API opérationnelle de retour n'est annoncée.

### Fichiers et limites de la livraison

- Moteur : `progression.py`, `ordres_pipeline.py`, `soldats.py`, `combats.py`,
  `generaux.py`. Pas de nouveau module, registre Zombie ou changement de droits.
- Tests : progression, unités V2, effets QG, soldats/formation, participations
  temporaires. Couverture des tirages exacts, mémoires, profils falsifiés,
  interruptions, UUID/XP/blessures, fusions partielles, fatigue, prévisions,
  exclusions, classements et absence de mutation.
- Documentation : les deux SPEC, la préparation et le présent bilan.
  Les nouvelles décisions et les questions indispensables sont au début de
  `docs/ordres-v2-preparation.md` ; les anciens questionnaires sont des archives.
- Questions restantes : résistance/dégâts avec fatigue hétérogène, référence des
  bonus de composition et formation lourde de Gros_poisson, conversion d'un prêté
  par Spore adverse, auto-désignation des
  deux rôles ; priorité d'une mémoire scolaire Zombie ; sélection/état physique
  des réanimés et placement/durée/destination de Ralliement.
- La réponse sur la mémoire Zombie précisait Gros_poisson sans trancher cette
  question : comportement de `d32fdeb` conservé (mémoire intacte, tirage 85/15).
- La recette Raspberry Pi/SSH/cgroup réelle reste distincte des tests sous WSL.

### Validation

- Compilation Linux des **10 fichiers Python modifiés : OK**, caches isolés
  dans `/tmp`, aucun cache suivi par Git.
- Ciblés : **171 tests, 20,521 s, OK**, journal
  `.dev/lot-b-reprise-cibles-finaux.log`. La première passe de développement
  (143 tests) avait relevé une fixture QG restée instinctive après changement
  d'état ; le profil de ce scénario non-Zombie a été rétabli en stratège.
- Suite complète finale : **726 tests, 156,788 s, OK (3 ignorés root)**,
  journal `.dev/lot-b-reprise-complets.log`. Les 17 tests ajoutés s'ajoutent aux
  709 présents dans `d32fdeb` (le bilan de 704 précédait ce dernier commit).
- Contrôles Linux root séparés : **3 tests, 1,186 s, OK**, journal
  `.dev/lot-b-reprise-root.log`. Les deux scénarios de permissions des groupes
  et le script administrateur Crypte utilisent des dossiers temporaires et de
  vrais UID isolés, sans modifier une partie `/game`.
- Les trois contrôles root couvrent exactement les trois tests ignorés :
  **726 tests distincts réussis**, sans additionner les passes ciblées.
- Renforcement final du scénario de fusion partielle : dossiers de blocs
  physiquement absents, pas seulement vides. Test recompilé et réexécuté :
  **1 test, 0,179 s, OK**, `.dev/lot-b-reprise-blocs-absents.log`.
- Une première passe complète de 725 tests avait réussi avant le dernier
  garde-fou Bouclier et le test supplémentaire de classement par blessures.
  Son script enveloppe a ensuite échoué à sa fermeture après modification
  pendant l'exécution ; la passe finale ci-dessus a bien terminé avec code 0.
- Exécution WSL Ubuntu/Python 3.14.4, sur copies temporaires Linux des fichiers
  suivis avec leurs modifications de travail, pour éviter la lenteur du montage
  Windows. Pas de simulation des UID dans les trois contrôles root. Les tests
  de cycle conservent leur gel simulé habituel, sans validation Raspberry/SSH.
- `git diff --check` : OK ; aucun `.pyc` ni `__pycache__` suivi. Scripts de
  lancement temporaires retirés ; journaux locaux non livrés.
