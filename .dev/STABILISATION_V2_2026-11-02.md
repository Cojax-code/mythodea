# Stabilisation Mythodea v2.0 — 2 novembre 2026

Travail effectué sur `v2.0`, depuis `529453b`, avec un arbre Git initialement propre.
`main` n'a pas été modifiée. Aucun commit ni push n'a été créé pendant cette reprise.
Les changements restent dans l'arbre de travail pour relecture.

Les corrections précédentes sont présentes : calculs fractionnaires du moral,
addition des effets, attribution au bon camp, instantané QG pendant les cascades,
contrôles des liens QG et priorité de lecture à l'École. Les règles récentes de
sélection active et de progression zombie étaient déjà implémentées ; elles ont
été vérifiées et complétées par des tests, sans nouvelle refonte du moteur.

**Corrections réalisées**

- Le contrôle de capacité des généraux appelait `caracteristiques_general()` sans
  chemin, provoquant `KeyError: 'chemin'` lors de la lecture des territoires.
  Il consulte maintenant directement le profil privé nécessaire à la capacité.
  Il ne lit ni ne fige la sélection d'un futur renfort. Les capacités normales et
  zombies, ainsi que le traitement existant des surplus, sont conservés.
- La capture Survie contrôlait les liens physiques de `QG.txt`/`qg.txt`, mais
  acceptait ceux de `etiquettes_actives.txt`. Une copie effaçait ensuite la preuve
  du lien. Les trois noms sont maintenant contrôlés avant copie.
- La lecture d'une sélection vérifie le fichier effectivement ouvert : type,
  nombre de liens, identité de l'inode et stabilité des métadonnées pendant la
  lecture. Sous Linux, `O_NOFOLLOW` refuse un lien substitué et `O_NONBLOCK`
  empêche un FIFO substitué de bloquer le moteur. Les parents symboliques sont
  refusés aussi lorsque le fichier de sélection manque.
- Le test historique de progression zombie reçoit maintenant un tirage contrôlé
  de 21, correspondant à l'échec du déblocage de 20 %. Ses assertions restent
  inchangées ; le test vérifie aussi les bornes du tirage.
- Le scénario historique de formation lourde sélectionne explicitement zéro
  étiquette. Il obtenait parfois 16 survivants au lieu des 15 attendus à cause
  d'une étiquette aléatoire du général récompense. Les deux assertions à 15
  survivants sont conservées, ainsi que la vérification des positions des blocs.

**Couverture ajoutée**

Vingt nouveaux tests de développement couvrent la syntaxe, l'absence et le vide,
les doublons, les noms exacts, les limites des quatre natures, les connaissances
privées, les effets non sélectionnés, les liens et objets spéciaux et leur
substitution pendant l'ouverture. Ils exercent le gel entre duels, choc, manœuvre,
frontal, rangé et cascade réelle, dans les deux modes OFF/OFF et OFF/DEF, ainsi
que la nouvelle sélection à la bataille suivante et la restauration après exception.

Le QG transmet seulement sa sélection initiale, avec le bonus initial du Messager,
sans recevoir une seconde copie. Homes, bâtiments, réserve et renforts en attente
sont exclus du calcul initial. Un renfort fige sa sélection à son premier engagement.
Les tests existants vérifient notamment la destruction du QG, l'absence de relève,
les malus chaman/cruelle, les fractions et l'addition des bonus.

Le tirage zombie est contrôlé sur chacun des 100 résultats possibles pour chacune
des quatre natures : exactement 20 succès. Les tests vérifient le rang 1, les deux
places par niveau, l'absence de gains ordinaires, la conservation des étiquettes,
l'absence de nouveau tirage après acquisition, le rechargement, le reçu empêchant
un rejeu et l'emplacement actif supplémentaire.

Deux nouveaux tests Linux couvrent la création d'une sélection par j1, le refus
d'accès de j2, la capture/publication, les droits 600 → 400 → 600 et le refus des
liens physiques, symboliques, FIFO et dossiers avant capture. Les tests existants
couvrent aussi les rapports privés/publics, les états root, les vrais UID/GID,
le gel noyau, les descripteurs ouverts, la republication et la Crypte.

**Validation finale**

Environnement réellement utilisé : WSL2, Ubuntu 26.04.1 LTS, x86_64, Python 3.14.4,
systemd et cgroups v2. Les sources testées sont sur ext4 dans
`/home/cojax/mythodea-v20-20261102-audit`, les plateaux de tests sous `/tmp`.
Les tests de développement tournent sans root ; les tests de permissions et le
test de scanner dédié tournent avec root via `wsl -d Ubuntu -u root`.
Les comptes temporaires ont été retirés. Aucune vraie partie `/game` ni home
`/home/j1` ou `/home/j2` n'a été utilisé.

| Validation | Tests recensés | Réussis | Ignorés | Échecs / erreurs |
| --- | ---: | ---: | ---: | ---: |
| Suite complète `.dev/tests` | 592 | 591 | 1 | 0 |
| Suite complète `python/tests_linux`, root | 31 | 31 | 0 | 0 |
| Scanner ignoré sans root, exécuté séparément avec root | 1 | 1 | 0 | 0 |
| Sélections et zombies, suite ciblée | 20 | 20 | 0 | 0 |
| Défis, suite ciblée | 25 | 25 | 0 | 0 |
| Répétitions du scénario de formation lourde | 20 | 20 | 0 | 0 |

Les lignes ciblées et le scanner répètent des tests de la suite complète : ne pas
additionner ces lignes pour compter des tests distincts. L'unique test ignoré
dans la commande non privilégiée est
`ScannerCrypte.test_17_script_administrateur_non_modifiable` ; il a réussi avec root.
La suite complète de développement finale a duré 73,884 s, la suite Linux 27,708 s.

`python3 -m py_compile` a réussi pour les sept fichiers Python modifiés.
`git diff --check` ne signale aucune erreur. Les empreintes des sources locales
et de la copie WSL testée ont été comparées.

Journaux conservés localement, ignorés par Git :

- [Développement](stabilisation-v20-dev-final.log)
- [Linux réel](stabilisation-v20-linux-final.log)
- [Scanner root](stabilisation-v20-scanner-root.log)
- [Sélections](stabilisation-v20-selections.log)
- [Défis](stabilisation-v20-defis.log)
- [Répétitions](stabilisation-v20-defis-repetitions.log)

Les essais intermédiaires ont révélé les erreurs corrigées ci-dessus. Un premier
essai Linux a aussi démarré avant la fin de la copie des supports de tests ; son
échec d'import Crypte n'est pas un défaut du dépôt. La validation finale utilise
la copie complète sur disque Linux persistant, avec tous les modules découverts.

**Documentation et fichiers**

| Fichier | Modification |
| --- | --- |
| `python/generaux.py` | Lecture privée de la capacité, indépendante de la sélection |
| `python/cycle_linux.py` | Refus des sélections liées ou spéciales avant copie |
| `python/progression.py` | Vérification sécurisée du fichier ouvert |
| `.dev/tests/test_etiquettes_actives.py` | 20 régressions supplémentaires |
| `.dev/tests/test_unites_v2.py` | Tirage zombie explicitement contrôlé |
| `.dev/tests/test_defis_survie.py` | Scénario de formation sans bonus aléatoire |
| `python/tests_linux/test_permissions_reelles.py` | Deux tests Linux supplémentaires |
| `MYTHODEA_SPEC.md` | Références v2.0, retrait des anciens ordres, progression, sélection et QG alignés sur les règles validées |
| `SURVIE_SPEC.md` | Instantané des cascades et tirage zombie de 20 % |
| `REGLES_V2.md` | Contrôles avant capture et autorité privée explicités |
| `TESTS_LINUX_SURVIE.md` | Commandes ciblées et validation du test root |
| `.dev/STABILISATION_V2_2026-11-02.md` | Présent bilan |

Le README, les formats persistants, les chemins de jeu et les politiques de
permissions sont conservés. Aucune configuration de terrain v2.1 ni ancien ordre
n'est introduit. Les scénarios frontaux utilisent seulement l'entrée interne
déjà existante, comme les régressions précédentes.

**Décisions ouvertes et Raspberry Pi**

Les décisions déjà recensées dans `REGLES_V2.md` restent ouvertes : soutien d'un
QG retiré vivant, effets sur la phase spéciale du Bouclier, plancher à 1 % pour
les malus extrêmes, étiquettes instinctives à 0 PC, migration des anciens profils
et mémoires retirées, connaissance préalable pour rédiger une étiquette à l'École.
Aucune nouvelle règle n'a été choisie pour ces cas.

Aucun Raspberry Pi n'était accessible. Sur une installation de test dédiée
sans comptes j1/j2 ni groupe `mythodea_allies` préexistants, depuis le dépôt :

```bash
python3 -B -m unittest discover -s .dev/tests -v
sudo python3 -B -m unittest discover -s python/tests_linux -v
sudo env PYTHONPATH=.dev/tests python3 -B -m unittest \
  test_crypte_scanner.ScannerCrypte.test_17_script_administrateur_non_modifiable -v
```

Les contrôles du serveur cible restent ceux de
[TESTS_LINUX_SURVIE.md](../TESTS_LINUX_SURVIE.md) : partition dédiée et distincte
montée sur `/game`, vraie session SSH de chaque joueur dans sa slice systemd,
annonces sur plusieurs terminaux, gel/reprise, ACTIONS/CONSULTATION, accès aux
rapports et récupération après incident. Vérifications initiales sans écriture :

```bash
findmnt --mountpoint /game
lsblk -f
df -h /game
stat -fc %T /sys/fs/cgroup
```

Dans chaque session SSH joueur :

```bash
id
cat /proc/self/cgroup
```

Ces essais matériels et SSH ne sont pas remplacés par la validation WSL.
