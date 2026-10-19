# Généraux, blessures et formation

Les nouveaux généraux reçoivent un niveau 0, une nature et un trait permanent.
Leurs champs apparaissent dans `fiche.txt`. Les anciennes fiches sont conservées.
Les natures sont stratège (45 %), instinctif (45 %), stratège hybride (5 %) et
instinctif hybride (5 %). Les hybrides gardent les traits et récompenses ordinaires
de leur orientation principale, et peuvent apprendre ceux de l'autre à l'École.
La référence de fabrication des trois unités ordinaires vaut 5 ; les recettes
et la valeur collective de combat ne changent pas.

Les soldats survivant à la résolution complète d'un territoire gagnent une
bataille. À 5 batailles ils deviennent vétérans, à 10 héroïques. Le moral d'un
instinctif peut sauver des pertes en leur donnant une blessure ; leurs limites
sont respectivement 1, 2 et 3 blessures. Un nouveau général a un moral nul.

## Aller à l'hôpital

Depuis le village, déplacer le dossier complet dans une place libre :

```bash
mv /game/village/j1/garnison/1/general1 /game/village/j1/hopital/1/
```

Les places `1..20` sont disponibles par défaut. Chaque numéro est partagé
logiquement entre j1 et j2 : ne pas occuper une place déjà prise par un allié.
Tous les généraux ayant passé un tour complet à l'hôpital sont soignés ensemble.
Les blessures reviennent à zéro ; batailles, expérience et statuts sont conservés.
Consulter `formation_resultat.txt` dans le dossier du général après publication.

Une entrée pendant ACTIONS commence son séjour complet au début du tour suivant.
Une sortie, même suivie d'un retour, annule le séjour. Les passages entre réserve,
garnison et bâtiments restent des réorganisations internes au village sans coût
de mouvement ; les déplacements entre territoires gardent leurs règles.

Le contrôle de présence est conservateur : changer le général de place ou
réorganiser les unités pendant les soins peut invalider la preuve de séjour.
Pour garantir sa validation, garder les dossiers à leur place pendant ce tour.

## Apprendre ou écrire à l'École

L'École possède six places physiques communes : `/game/village/ecole_officiers/1`
à `6`. Déposer le général dans le sous-dossier privé `j1/` ou `j2/` de la place.
Un seul général peut occuper chaque numéro, tous joueurs confondus.
Le manuel commun possède seulement trois emplacements, `001`, `002`, `003` :

```bash
cat /game/village/ecole_officiers/memoire_des_generaux.txt
```

Dans le dossier du général, préparer **une seule demande** avant le début du
tour complet de présence :

```bash
# Apprendre l'évolution 201 actuellement inscrite en 001 :
printf '%s\n' 'a 001 201' > lire_les_memoires.txt
: > ecrire_ses_memoires.txt

# Ou écrire une évolution 201 déjà acquise dans l'emplacement 001 :
printf '%s\n' 'e 001 201' > ecrire_ses_memoires.txt
: > lire_les_memoires.txt
```

`A` et `E` sont également acceptés. Un ID de lecture différent de celui du manuel
est refusé. Les anciennes demandes sans lettre restent compatibles.
Les demandes sont figées au début du tour : les modifier ensuite ne raccourcit
pas l'attente. Toutes les lectures se déroulent avant les écritures du même tour.
Ainsi, apprendre et remplacer simultanément la même entrée conserve l'ancien ID
sur la fiche de l'élève. Le manuel reste disponible aux autres généraux.

Consulter `formation_resultat.txt`, puis vider la demande après traitement si
aucun nouveau séjour n'est souhaité. Deux écritures concurrentes de la même entrée
sont refusées ensemble. Un apprentissage déjà en attente n'est pas écrasé.

## Transformer des cavaliers à la Forge

La Forge accueille un seul général, dans `/game/village/forge/1/j1/` ou le
compartiment `j2/`. Il doit être instinctif ou instinctif hybride et posséder
la technologie 104 dans ses évolutions acquises.

Avant son tour complet, équiper les cavaliers existants avec les quatre fichiers
`cuirasse`, `armure`, `casque`, `bouclier`, en conservant `cheval`. Après validation,
le moteur renomme les dossiers en `cavalerie_LN`. Blessures, batailles et statuts
sont conservés. Une recette incomplète laisse le cavalier intact. La conversion
est annoncée dans le rapport du tour. Après une conversion partielle, séparer les
types de cavalerie en blocs homogènes avant de les engager au combat.

## Déplacements et retraites

Depuis home, le passage par le village est obligatoire, à tous les tours. Les
places et bâtiments autorisés du village sont accessibles sans coût territorial,
y compris aux nouveaux généraux. Aucun déplacement direct vers `est_1` ni aucune
marche forcée ne permet de sauter cette étape. Les délais d'entraînement et de
rappel restent applicables ; les restrictions du tour 0 sont conservées.
Une récompense peut effectuer un déplacement normal dès sa publication.
Un fuyard arrivant au village rejoint la réserve si la garnison ne peut l'accueillir,
avec toutes ses unités et ses données.

## Ce qui attend encore une décision

- Les conditions de gain de niveaux : batailles, caserne et barèmes. Le moteur
  possède les fonctions de progression, mais ne donne aucun niveau automatiquement.
- Les autres ordres et unités à gagner. Commandement 201, moral 202, technologie
  de Forge 104 et attaque frontale 1002 sont disponibles comme évolutions.
- La matérialisation des QG et le raccordement de leurs priorités aux effets des
  ordres historiques. Les calculs et la sélection sont testés, sans nouvelle
  tactique activée dans les parties.
- Le départage de deux écritures simultanées et le remplacement d'un apprentissage
  en attente ; actuellement ces cas sont refusés explicitement.
- La migration des caractéristiques des généraux déjà existants. Aucun tirage
  rétroactif ni gain d'expérience antérieure n'est appliqué.

## Sauvegardes et transferts

Conserver ensemble les dossiers des unités et `.systeme/progression.json`,
`.systeme/soldats.json`, `.systeme/formation.json`. Les fichiers visibles de
blessures sont des copies : les éditer ne guérit pas les soldats. Le manuel
validé est également contrôlé par le moteur.

Déplacer un dossier d'unité complet conserve ses métadonnées. Cela n'ajoute
aucun droit de transfert : bloc homogène, noms sans collision, permissions,
plafonds d'effectifs et audit d'entraînement restent applicables. Un déplacement
entre systèmes de fichiers doit conserver `identifiant_soldat.txt`.

Les détails techniques et les tables de progression figurent dans la section 22
de `MYTHODEA_SPEC.md` ; les bâtiments sont actuellement raccordés au village Survie.

## Vérifier le moteur

Depuis la racine du dépôt, sous Linux :

```bash
python3 -B -m unittest discover -s .dev/tests -v
```

`test_progression.py` couvre les catalogues, probabilités, niveaux et QG.
`test_soldats_formation.py` couvre les pertes, compteurs, transferts, soins,
mémoires, séjours incomplets et publication privée. `test_complements_moteur.py`
couvre les hybrides, la Forge, les bâtiments partagés et les nouveaux déplacements.
Les tests temporaires n'utilisent
pas une vraie partie. Le test `python/tests_linux/test_progression_isolee.py`
vérifie séparément les droits Linux avec root et des UID de processus, sans créer
de comptes. Une validation sur Raspberry Pi reste à réaliser.
