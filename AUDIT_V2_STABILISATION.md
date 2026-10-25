# Audit et stabilisation V2 — clôture de la reprise

Audit initial sur `v2.0`, départ `84802b1`, corrections conservées dans
`eb5c302` (« verification codex »). Reprise et validation sur `feat/ordres-v2`
à partir de `0ad6ec6`. Aucun merge vers `v2.0`.

## Résultats vérifiés

- Le journal précédemment interrompu est complet : **558 tests en 191,454 s,
  aucun échec, un ignoré réservé à root** (`.dev/audit-tests-complets.txt`).
- La reprise, incluant les modules préparatoires des ordres, exécute
  **584 tests en 215,103 s, aucun échec, le même ignoré**
  (`.dev/ordres-v2-baseline.txt`). Les préparations enregistrées sur GitHub
  ont donc été testées sous Linux.
- Vérifications réelles Linux isolées sous root : **4 tests réussis en 9,128 s**,
  dont le test ignoré dans la suite ordinaire. Journal :
  `.dev/ordres-v2-permissions-linux.txt`.
- Total avant nouveaux effets : **587 tests distincts réussis**
  (583 ordinaires + 4 root). Aucun test root compté deux fois.
- Les nouveaux effets et leurs résultats sont suivis dans
  `docs/ordres-v2-reprise-codex.md`.

## Corrections conservées et revérifiées

- Boucliers séparés des unités ordinaires, disparition lorsqu'ils restent seuls,
  deux boucliers adverses ignorés par les unités ordinaires.
- Moral racial Orc borné, PC inchangés ; fractions de moral Chaman conservées.
- Ordres malformés, Unicode non numérique, nombres excessifs et UTF-8 invalide
  ignorés sans bloquer la résolution.
- Rapports calculés dans la génération privée ; publication sous gel ; journal
  progressif à inode stable, reprenant les écritures partielles sans doublon.
  Les détails techniques restent privés et les erreurs ne fuient plus au Clocher.
- Unités créées par le moteur : propriétaire du bloc, dossier `700`, fichiers
  `600`. Spore conserve identité et expérience ; surplus Zombie régulés en fin
  de territoire, sans sacrifier les soldats historiques.
- Trois parties déterministes jusqu'à la défaite, avec redémarrage entre tours :
  sans défense, un joueur, coopération. Capture/publication interrompues testées.

Les anciennes attentes incompatibles avec les décisions Orcs et commandement
ont été corrigées avec des régressions dédiées. Les tests d'épuisement des
récompenses utilisent les apprentissages effectivement disponibles.

## Portée de la clôture

L'audit automatisé repris est terminé et ses corrections sont conservées.
Ubuntu sous WSL, plateaux temporaires, jamais une partie réelle `/game`.
Les tests root emploient des UID isolés sans créer de comptes. Une recette
Raspberry Pi avec connexions SSH et gel réel des comptes reste à faire sur une
machine dédiée ; la simulation du gel ne la remplace pas.

Les décisions de gameplay ouvertes le restent : victoire finale en Survie,
autres fronts, ordres non intégrés. Bibliothèque et Crypte des plaines existent ;
elles ne confèrent aucun apprentissage personnel implicite.

La suite Windows initiale (529 tests, erreurs de dépendances Unix) ne mesure pas
la stabilité Linux. Les traces intermédiaires sont conservées sans les présenter
comme les résultats finaux.
