# Reprise du moteur Mythodea V2 — Bouclier vivant, Spore, progression

**Branche :** `v2.0` (aucune nouvelle branche créée).
**Date :** 20 octobre 2026.
**Statut :** implémentation initiale raccordée au moteur ; validation d'intégration et tests Raspberry Pi / Linux à effectuer avant une partie réelle.

## Réalisé

- Catalogue `Trop_gros_zombie` : résistance initiale / valeur 250, dix places, étiquette `spore`.
- Nouveau module `python/bouclier_vivant.py` : calcul en fractions, cible Spore par expérience minimale, conversion avec identité préservée et journal privé anti-rejeu, choix du bloc zombie destinataire, priorité contre chaque bloc adverse, attaque des Zombies ordinaires entre deux passages, retour aux phases classiques si le bouclier meurt.
- Un seul Gros zombie par général : contrôle lors du rituel, puis validation de la composition lors du duel.
- Le bouclier seul sans Zombies ordinaires provoque la défaite du général.
- Valeur restante du bouclier stockée par bataille territoriale dans `capacites_unites.json` ; remise à 250 après l'ensemble des combats territoriaux.
- Propagation et Spore autorisées à dépasser temporairement la capacité ; les Zombies issus de cette bataille sont supprimés en priorité à la clôture territoriale, pas après chaque duel. Les lectures intermédiaires des forces ne détruisent plus ces créations.
- Général zombie : +2 places définitives par niveau **gagné après résurrection**, sans autre récompense. La résurrection à 5 % et l'ouverture de la Morgue étaient déjà configurées.
- Rapports : la phase Bouclier et les attaques ordinaires disposent d'entrées structurées et les colonnes sont réordonnées selon les camps.
- Tests unitaires purs et scénarios d'intégration ajoutés/ajustés dans `.dev/tests/test_bouclier_vivant.py` et `.dev/tests/test_unites_v2.py`.

## À vérifier avant utilisation

1. **Tests non exécutés dans cette session :** le dépôt privé GitHub est accessible via le connecteur, mais les sources ne sont pas montées dans un interpréteur Python de la session. Exécuter impérativement la suite.
2. Le rapport détaillé doit représenter correctement la phase prioritaire, en particulier si le général zombie est second dans le duel.
3. Vérifier sur Linux réel les changements de propriété/permissions des dossiers de soldats convertis par Spore, les identifiants et la publication des générations privées.
4. Vérifier interruption à chaque point d'écriture de Spore, Propagation et résistance : la reprise doit refuser le rejeu partiel et ne publier aucun état incomplet.
5. Vérifier plusieurs duels contre différents généraux dans une **même** bataille territoriale, puis une seconde bataille où la résistance repart à 250.
6. Vérifier les effets du moral, fatigue, ordres actuellement existants, fuite, autres unités et rapport progressif.
7. **Décision validée :** deux Boucliers vivants adverses s'ignorent, les Zombies ordinaires combattent normalement ; aucune Spore ni Propagation ne s'applique entre Zombies. Vérifier toutefois que les boucliers sont bien exclus de toutes les confrontations ordinaires.
8. Lorsque plusieurs blocs sont favorables aux Zombies ordinaires, le code utilise l'ordre de parcours des blocs actuel ; vérifier avec le joueur s'il souhaite un autre départage.
9. Vérifier que le bouclier détruit n'est jamais traité à tort comme une unité ordinaire de valeur 250 dans les autres fonctions de combat.

## Tests à lancer

```bash
python3 -B -m unittest discover -s .dev/tests -p 'test_bouclier_vivant.py' -v
python3 -B -m unittest discover -s .dev/tests -p 'test_unites_v2.py' -v
python3 -B -m unittest discover -s .dev/tests -v
python3 -m py_compile python/bouclier_vivant.py python/combats.py python/unites.py python/progression.py python/morgue.py python/survie.py python/generaux.py
```

Puis tests d'intégration sous Linux / Raspberry Pi, dans une partie de test **isolée** et jamais sur la vraie partition de production.

## Consignes de revue du dimanche 25 octobre 2026

Examiner le diff des commits V2 du 20 octobre, rechercher les interactions oubliées entre `bouclier_vivant.py`, `combats.py`, `unites.py`, `generaux.py`, `soldats.py`, `morgue.py` et `survie.py`.
Ne pas inventer de nouvelles règles. Corriger les bugs démontrés par tests et signaler les ambiguïtés. Ne pas créer de branche, ne pas faire de commit ni de push sans instruction.
