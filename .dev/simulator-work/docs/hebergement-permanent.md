# Simulateur Mythodea — rendre le service disponible 24 h/24

## Situation actuelle (20 octobre 2026)

Le simulateur n'est pas encore publié comme application web. Le site HTML peut
être hébergé statiquement, mais son bouton « Lancer le combat » appelle
`POST /api/simulator/run`, exécuté par le serveur Python Flask/Waitress.
`backend/app.py` écoute **uniquement sur 127.0.0.1:8080** et sa liste
`TRUSTED_HOSTS` n'accepte que localhost. Lancer la page sur GitHub Pages
ne suffit pas : GitHub Pages ne fait pas tourner Python ni Bubblewrap.

Le simulateur utilise un moteur Python officiel **figé** au commit décrit dans
`backend/engine.lock.json` (préparation par `scripts/prepare_engine.py`).
Le moteur `v2.0` actuel, comprenant Spore/Bouclier vivant, **n'est pas
automatiquement inclus** dans le simulateur hébergé, même si le site ou le jeu
sont mis à jour.

## Solution recommandée : hôte Linux permanent, HTTPS, proxy inverse

Un petit serveur Linux (VPS) ou un hébergement applicatif acceptant **Python,
Bubblewrap et les espaces de noms utilisateur** est nécessaire.

1. Choisir un hôte sous Linux disposant d'une connexion permanente et d'une
   adresse joignable depuis Internet. Les offres qui interdisent Bubblewrap ou
   les espaces de noms utilisateur ne sont pas compatibles avec ce moteur
   sécurisé. Ne jamais désactiver l'isolation pour contourner ce problème.
2. Installer Python 3.11+, Git, Bubblewrap et un environnement virtuel
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
6. Protéger la route `/api/simulator/run` par **limitation du débit**, quotas
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
préparation des modules et les schémas d'unités/ordres doivent être adaptés
ensemble. Une nouvelle version du moteur nécessite une nouvelle campagne de
tests et de comparaisons. Jusqu'à ce travail, afficher le simulateur comme une
version de référence limitée, non comme une simulation complète de toutes les
capacités de la V2.

## Fiches d'ordres

La page `fiches-ordres.html` fonctionne en statique, sans Python. Les
propositions sont enregistrées en `localStorage` dans le navigateur qui les a
créées, avec export/import JSON. **Elles ne sont pas synchronisées automatiquement
entre appareils ni ajoutées au moteur.** Sauvegarder régulièrement le JSON.
