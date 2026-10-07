# Prototype du scanner Bash de la Crypte

Ce prototype évalue l'observation d'un Bash interactif normal. Il n'est pas
branché au jeu : aucun cooldown, compteur, général ou fichier de partie n'est
modifié. Les marqueurs ont leurs noms provisoires fixes ; la configuration
privée des marqueurs et le collecteur moteur restent à intégrer.

Le script est `bash/prototype_crypte_scan.sh`. Les tests sont dans
`python/tests/test_crypte_scanner.py`. Ils utilisent de vrais pseudo-terminaux
Linux, des répertoires temporaires et de vraies commandes, sans dépendance Python
supplémentaire. La vérification de la séquence est effectuée par un oracle de
test, séparé de l'observateur. Il ne s'agit pas encore d'un atelier proposant
les messages de réussite/échec et le nettoyage immédiat au joueur.

## Mécanisme observé

`crypte_commence` active l'enregistrement. Pendant la tentative, les filtres
`HISTCONTROL` et `HISTIGNORE` sont neutralisés et l'historique en mémoire est
activé. L'expansion `!` est désactivée. Les valeurs précédentes sont restaurées
par `crypte_fin`. Un historique grand ou illimité n'est pas réduit.

`DEBUG` enregistre une fois chaque nouvelle entrée d'historique, avant exécution.
Le texte de l'entrée est comparé à la commande attendue. Il est distinct de
`BASH_COMMAND`, qui peut déjà contenir l'expansion d'un alias et ne représente
pas nécessairement la ligne complète. Les séparateurs et pipelines sont donc
détectés dans le texte complet, même si la première commande est correcte.

`PROMPT_COMMAND` récupère le code retour dès le retour à l'invite. Il détecte
aussi une nouvelle entrée non vue par `DEBUG`, notamment une erreur de syntaxe.
Une étape n'est admissible qu'après un code retour nul. Les erreurs ne sont pas
effacées par les commandes correctes suivantes.

Le journal contient huit champs séparés par NUL : événement, ligne complète,
`BASH_COMMAND`, statut, répertoire physique, numéro/disponibilité de l'historique,
nature de la commande et PID Bash. Pour `start`, deux champs portent le numéro
local de tentative et l'UID annoncé par Bash. **Cet UID annoncé n'est pas une
authentification** : le futur collecteur doit obtenir l'UID depuis le noyau.
Le journal du prototype, écrit par le shell sur le descripteur 9, est lui-même
modifiable par le joueur et ne doit jamais autoriser une récompense.

## Observations Linux

Essais sur WSL Ubuntu, GNU Bash 5.3.9, Python 3.14.4. Les tests lancés par root
exécutent le Bash joueur sous UID/GID 65534 (`nobody`), sans créer de compte.
Le dossier administrateur temporaire appartient à root, en `755`, ses scripts
sont en `444`. Aucun profil système ou `.bashrc` personnel n'est modifié.

| Cas | Ce qui est réellement observé | Décision de l'oracle |
| --- | --- | --- |
| 1. Séquence normale | Les quatre lignes exactes, chacune suivie de `after: 0`, puis `crypte_fin` et `end`. L'offrande existe réellement en `600`. | Succès pédagogique |
| 2. `ls` supplémentaire | `before` contient `ls`, même si son retour est `0`. | Échec : ligne inattendue |
| 3. Mauvaise commande | `mkdir autre` est enregistré et s'exécute réellement. | Échec : ligne inattendue |
| 4. Bonne commande échouée | `mkdir appel` sur un dossier préexistant : ligne correcte, retour `1`. | Échec : code retour |
| 5. Deux commandes avec `;` | Ligne complète `mkdir appel; touch appel/cavalerie`, distincte du premier `BASH_COMMAND` égal à `mkdir appel`. | Échec dès la ligne complète |
| 6. Pipeline | Ligne complète `mkdir appel \| cat`, même si le pipeline retourne `0`. | Échec : ligne inattendue |
| 7. Alias ou fonction | Alias : ligne `mkdir appel`, commande développée `mkdir -v appel`, nature `alias`. Fonction : même texte mais nature `function`. | Échec : commande remplacée |
| 8. Ctrl+C pendant une commande | La commande au premier plan retourne `130`. Le trap INT du Bash parent n'est pas nécessairement appelé. | Échec : code retour 130 |
| 9. Ctrl+C à l'invite | Événement `interrupt: 130` ; le texte interrompu n'est pas une ligne exécutée. Dans cet environnement, trap INT et retour à l'invite peuvent signaler deux fois la même interruption. | Échec définitif |
| 10. Fermeture avant la fin | Fermeture réelle du maître du PTY : les dernières entrées restent, sans `end`. Aucun événement `close` n'a été reçu lors de ces essais. | Tentative inachevée, jamais succès |
| 11. Sous-shell Bash | Le parent observe `bash --noprofile --norc`. L'intérieur du sous-shell n'est pas scanné ; la tentative est déjà invalide. | Échec : ligne inattendue |
| 12. Changement de répertoire | `cd ..` est observé ; le répertoire physique suivant change réellement. | Échec : ligne inattendue, puis hors atelier |
| 13. Historique modifié | `set +o history`, `history -c` et `HISTCONTROL=ignorespace` sont observés avant leur effet. Ensuite, le journal signale les lignes indisponibles ou le changement de numérotation. | Échec dès la modification |
| 14. Fin prématurée | `crypte_fin` puis `end` après une seule étape. | Échec : quatre étapes absentes |

Le test 8 utilise un exécutable temporaire nommé `mkdir` placé dans le PATH :
il attend réellement et reçoit Ctrl+C. Cela permet d'interrompre une commande
dont le texte reste exactement celui de la recette, sans introduire un `sleep`
supplémentaire qui aurait déjà invalidé la tentative. Ce montage est réservé au test.

Les six tests supplémentaires vérifient :

- l'erreur de syntaxe `)` : événement `unobserved`, texte `)`, statut `2` ;
- l'historique désactivé avant le début : activation temporaire, réussite puis
  restauration des réglages initiaux ;
- le refus réel de `chmod`, d'écriture et de suppression du script root par nobody ;
- la conservation de `HISTSIZE` grand, illimité ou initialement nul ;
- Ctrl+C après les quatre étapes, avant la fin : toujours échec ;
- la déconnexion après les quatre étapes : toujours inachevée sans `crypte_fin`.

## Portée et limites

Le prototype est concluant pour ces scénarios pédagogiques sur cette version de
Bash. Il ne constitue pas encore une validation de l'intégration Crypte au moteur.
Les points suivants doivent accompagner cette intégration :

- fournir le script officiel depuis un répertoire administrateur non modifiable,
  par exemple `/etc/mythodea/`, et le charger dans le Bash de connexion ; ne pas
  prendre le `.bashrc` joueur comme source officielle des fonctions ;
- conserver les noms de marqueurs dans la configuration moteur privée, sans
  interpréter des noms fournis par l'environnement joueur ;
- faire vérifier UID, atelier, échéance ACTIONS, cooldown et récompense en attente
  par le collecteur, et non par les variables ou le journal du shell ;
- attribuer et consommer les identifiants de tentative côté moteur, avec une seule
  décision d'attribution persistante ; un `end` reçu n'est pas une réussite ;
- détecter aussi la disparition de la session côté collecteur : les traps
  HUP/EXIT seuls ne suffisent pas, notamment après un arrêt brutal ;
- annuler les tentatives inachevées avant capture et réinitialiser l'atelier
  jetable dans le cycle prévu, sans toucher au grimoire ou à la récompense ;
- tester l'installation dans la vraie session SSH principale sur Raspberry Pi,
  avec sa version de Bash et ses éventuels hooks de présentation existants.

Un script officiel en lecture seule ne rend pas les fonctions chargées en mémoire
immuables. Le joueur peut modifier ses hooks, falsifier les événements ou placer
un autre exécutable dans son PATH. Ce contournement pédagogique est accepté ;
aucun événement reçu ne doit permettre de choisir un numéro de général, de
modifier directement le cooldown ou de faire rejouer une attribution.

Le prototype remplace les hooks dans **son Bash de test dédié**. Ne pas le sourcer
dans une session de partie : il n'est ni un installateur ni le collecteur final.
Les répertoires sont détruits par le banc de test à sa sortie ; le nettoyage
automatique de l'atelier en cours de partie n'est pas implémenté ici.

## Reproduction

Depuis la racine du dépôt sous Linux :

```bash
# 19 réussites, un test de propriété root ignoré si lancé sans root.
python3 -B -m unittest discover -s python/tests -p test_crypte_scanner.py -v

# Les 20 tests, avec de vrais refus de permissions sous UID nobody.
sudo python3 -B -m unittest discover -s python/tests -p test_crypte_scanner.py -v

# Export facultatif des événements (un objet JSON par scénario/sous-cas).
sudo env CRYPTE_TEST_REPORT=/tmp/crypte-observations.jsonl \
  python3 -B -m unittest discover -s python/tests -p test_crypte_scanner.py -v

sudo python3 -B -m unittest discover -s python/tests -v
python3 -m py_compile python/tests/test_crypte_scanner.py
bash -n bash/prototype_crypte_scan.sh
git diff --check
```

Validation effectuée : 205 tests de la suite Linux réussis, dont 20 tests du
prototype. Les sous-cas alias/fonction et historique sont inclus dans ce nombre,
pas comptés comme des tests unitaires supplémentaires. Aucun test SSH Raspberry Pi
réel n'a encore été exécuté pour ce scanner.
