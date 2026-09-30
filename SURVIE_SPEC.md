# Mythodea V2.0 — Mode Survie

Ce document prépare le développement du mode Survie.

Il complète `MYTHODEA_SPEC.md`, qui reste la référence du moteur commun hérité de
la V1.5. Les règles non définies ici ne doivent pas être inventées.

---

## 1. Objectif de la V2.0

La V2.0 introduit le **mode Survie**.

Le mode Survie doit réutiliser au maximum le moteur commun de la V1.5 :

- généraux ;
- unités et blocs ;
- mouvements ;
- combats ;
- sécurité ;
- fatigue ;
- rapports ;
- règles Linux communes.

Le but n'est pas de créer un deuxième moteur séparé.

---

## 2. Rôle du mode Survie dans le développement

Le mode Survie servira aussi d'environnement d'intégration et de jeu pour éprouver
le moteur commun.

Les tests automatiques existants restent conservés. Les validations réelles liées
aux comptes Linux, UID/GID, propriétaires, `chmod` et `chown` seront également
effectuées sur Raspberry Pi lorsque l'environnement sera disponible.

Un bug découvert en Survie dans une règle commune doit être corrigé dans le moteur
commun lorsque cela est approprié, et non contourné uniquement dans le mode Survie.

---

## 3. Objectifs Linux aléatoires

Le mode Survie introduira de petits objectifs Linux inspirés d'un niveau débutant
de Bandit.

Principes déjà décidés :

- plusieurs patterns simples seront disponibles ;
- un pattern pourra être choisi aléatoirement pour une partie ;
- les défis doivent apprendre ou faire pratiquer de vraies commandes Linux ;
- ils doivent rester courts et accessibles ;
- la réussite donne une récompense ou permet une progression dans le jeu ;
- ils ne doivent pas demander de contourner la sécurité réelle du serveur.

Exemples de familles envisagées :

- fichier caché ;
- recherche avec `find` ;
- recherche de contenu avec `grep` ;
- encodage simple comme Base64.

Les détails exacts, récompenses et conditions de déclenchement restent à définir.

---

## 4. Ordres

La V2.0 ne suppose pas que tous les ordres imaginés soient déjà finalisés.

Les ordres supplémentaires seront introduits progressivement après observation du
gameplay réel.

Point de design important à résoudre :

- plusieurs ordres alliés et adverses doivent pouvoir coexister lorsqu'ils ne se
  contredisent pas ;
- une simple priorité globale fondée sur une statistique ne doit pas être imposée
  sans validation de gameplay ;
- les règles de chevauchement, contradiction et résolution devront être définies
  avant implémentation.

---

## 5. Hors périmètre actuel

Les éléments suivants ne doivent pas être ajoutés automatiquement à la V2.0 sans
nouvelle décision de design :

- nouvelle carte multijoueur V3 ;
- tailles de carte 1v1, 2v2 et 3v3 ;
- nouvelle victoire par maintien de la base adverse ;
- événements neutres liés à la future carte V3 ;
- système complet d'argent ;
- bâtiments ;
- nouvelles statistiques avancées ;
- moral complet ;
- nouvelles unités avancées.

Ces éléments appartiennent à des étapes ultérieures sauf décision explicite contraire.

---

## 6. Questions à définir avant le premier gameplay Survie

Les points suivants restent volontairement ouverts :

1. structure exacte d'une partie de Survie ;
2. condition de défaite ;
3. apparition et comportement des ennemis ;
4. système de vagues ou autre progression ;
5. ressources initiales du joueur ;
6. création et remplacement des unités ;
7. place exacte des objectifs Linux dans la progression ;
8. récompenses des objectifs Linux ;
9. organisation des fichiers et dossiers propres au mode Survie.

Ces décisions doivent être prises avant de figer l'architecture spécifique du mode.
