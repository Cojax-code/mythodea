# Simulateur Mythodea — rendre le service disponible 24 h/24

## Version locale vérifiée le 3 novembre 2026

Le lancement local est vérifié ; aucun déploiement public permanent n'est validé
par cette vérification. Le site HTML peut
être hébergé statiquement, mais son bouton « Lancer le combat » appelle
`POST /api/simulator/run`, exécuté par le serveur Python Flask/Waitress.
`backend/app.py` écoute **uniquement sur 127.0.0.1:8080** et sa liste
`TRUSTED_HOSTS` n'accepte que localhost. Lancer la page sur GitHub Pages
ne suffit pas : GitHub Pages ne fait pas tourner Python ni Bubblewrap.

Le simulateur utilise les 27 modules du moteur **87d36a5 + corrections locales**,
verrouillés par SHA-256 dans `backend/engine.lock.json`. La progression actuelle,
les étiquettes, QG/Messagers et les impasses sont synchronisés. La révision exacte
et les limites figurent dans la [documentation du simulateur](simulateur.md).
Les corrections restent sans commit : leur préparation exige le dépôt moteur
local et `--working-tree`. Avant une installation depuis GitHub, créer le commit
sur instruction explicite puis actualiser le verrou pour utiliser ses blobs Git.
Les changements du moteur ne sont jamais intégrés automatiquement.

## Solution recommandée : hôte Linux permanent, HTTPS, proxy inverse

Un petit serveur Linux (VPS) ou un hébergement applicatif acceptant **Python,
Bubblewrap et les espaces de noms utilisateur** est nécessaire.

1. Choisir un hôte sous Linux disposant d'une connexion permanente et d'une
   adresse joignable depuis Internet. Les offres qui interdisent Bubblewrap ou
   les espaces de noms utilisateur ne sont pas compatibles avec ce moteur
   sécurisé. Ne jamais désactiver l'isolation pour contourner ce problème.
2. Installer Python 3.11+, Git, Bubblewrap avec `--size` et un environnement virtuel
   pour l'application, sous un compte Linux dédié non privilégié. Préparer
   l'environnement selon `README.md`.
3. Préparer et vérifier l'empreinte du **moteur verrouillé**. Exécuter sur
   l'hôte la suite `tests/` et vérifier que le lancement du moteur isolé
   fonctionne avant toute exposition publique.
4. Conserver Waitress sur **127.0.0.1:8080**, derrière un proxy inverse
   Nginx ou Caddy qui fournit HTTPS, le certificat TLS et la connexion
   publique sur le port 443. Ne pas ouvrir directement 8080.
5. Ajuster après audit la politique `TRUSTED_HOSTS` dans `backend/app.py`
   pour accepter uniquement le véritable domaine public configuré, en plus
   de localhost si nécessaire. Garder les protections de taille de requête,
   la validation de schéma, le sandbox et les limites de ressources.
6. Protéger toutes les routes `/api/simulator/` (run, generate, natural, reward, options) par **limitation du débit**, quotas
   et éventuellement authentification : chaque requête lance un vrai calcul.
   Surveiller CPU, mémoire, espace disque et logs ; prévoir la mise à jour
   et la reprise en cas d'arrêt.
7. Lancer Waitress par un service supervisé (systemd, ou mécanisme natif de
   l'hébergeur) afin qu'il redémarre après une panne et au démarrage de
   l'hôte. Configurer une vérification de disponibilité externe.
8. Utiliser le même domaine pour les pages du simulateur et les routes
   `/api/simulator/*` : le JavaScript existant appelle ces chemins relatifs.
   Ainsi, aucun CORS public n'est nécessaire.

**Attention :** « accessible en permanence » signifie un hôte actif avec
redémarrage et supervision, pas une garantie de 100 % de disponibilité.

## Raspberry Pi ou VPS ?

- **Raspberry Pi allumé à domicile :** techniquement envisageable après tests
  de Bubblewrap sur son système ARM64. Il faut un accès réseau stable, un
  adressage externe adapté (le partage de connexion mobile et le CGNAT peuvent
  empêcher un serveur entrant), un tunnel/proxy HTTPS de confiance, et une
  gestion des limites de ressources. Laisser le Pi allumé ne le rend pas
  automatiquement accessible.
- **VPS Linux :** souvent plus simple pour un service public permanent,
  avec réseau stable, domaine, TLS, supervision et sauvegardes. Vérifier
  spécifiquement le support de Bubblewrap avant choix.
- **Hébergement statique seul / GitHub Pages :** adapté au site et aux fiches
  techniques, mais **pas** aux simulations calculées par le moteur Python.

## Mise à jour du moteur du simulateur

**Ne pas remplacer seulement le hash verrouillé** : `engine.lock.json`, la
préparation des modules et les schémas d'unités/profils/étiquettes doivent être adaptés
ensemble. Une nouvelle version du moteur nécessite une nouvelle campagne de
tests et de comparaisons. Jusqu'à ce travail, afficher le simulateur comme une
version de référence limitée, non comme une simulation complète de toutes les
capacités de la V2.

## Guide des étiquettes

La page `etiquettes.html` présente les étiquettes. Les anciens ordres ne sont
plus proposés dans le simulateur ; l'API refuse un champ `order` non vide.
`fiches-ordres.html` n'est pas servie par le backend et ne doit plus être annoncée
comme une fonction active. Les fiches statiques ne remplacent pas la validation
des profils par le moteur du simulateur.
