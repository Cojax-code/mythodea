from pathlib import Path
import shutil
import random
import os
import pwd
import grp

game_path = Path("/home/game")

territoires = [
    game_path / "base1",
    game_path / "terrain1",
    game_path / "terrain2",
    game_path / "terrain3",
    game_path / "base2",
]

carte_territoires = {
    "base1": ["terrain1"],
    "terrain1": ["base1", "terrain2"],
    "terrain2": ["terrain1", "terrain3"],
    "terrain3": ["terrain2", "base2"],
    "base2": ["terrain3"],
}

bases_joueurs = {
    "j1": "base1",
    "j2": "base2",
}

positions_generaux_path = (
    game_path / "systeme" / "positions_generaux.txt"
)

fatigue_generaux_path = (
    game_path / "systeme" / "fatigue_generaux.txt"
)

repli_path = game_path / "repli"


ordre_blocs = ["avant", "droite", "gauche", "arriere"]
joueurs = ["j1", "j2"]

emplacements = ["1", "2", "3","4"]
max_unites_par_general = 20
max_generaux_par_joueur = 5

orientations = ["stratege", "combattant"]
orientation_rare = "hybride"

# ==================================================
# ORDRES DES GÉNÉRAUX
# ==================================================
#
# Format dans ordre.txt :
#
# type-numero
#
# ou, si l'ordre demande une précision :
#
# type-numero-specification
#
# Exemples :
#
# 1-1
# 2-2
# 2-2-1
#
# Un ordre inconnu, mal écrit ou non applicable
# est simplement ignoré.

legende_ordres = {
    "1-1": {
        "type": 1,
        "numero": 1,
        "nom": "retraite_apres_premiere_manche",
        "categorie": "armee",
    },

    "1-2": {
        "type": 1,
        "numero": 2,
        "nom": "attaque_frontale",
        "categorie": "armee",
    },

    "2-1": {
        "type": 2,
        "numero": 1,
        "nom": "attaque_chirurgicale",
        "categorie": "formation",
    },

    "2-2": {
        "type": 2,
        "numero": 2,
        "nom": "pluie_de_fleches",
        "categorie": "formation",
    },

    "3-1": {
        "type": 3,
        "numero": 1,
        "nom": "fuir_avant_la_mort",
        "categorie": "intrinseque",
    },
}


rapport_dir = game_path / "rapport"

rapport_court_path = (
    rapport_dir
    / "rapport_court.txt"
)

rapport_long_path = (
    rapport_dir
    / "rapport_long.txt"
)

rapports_territoires_dir = (
    rapport_dir
    / "territoires"
)

meteo_path = (
    game_path
    / "systeme"
    / "meteo.txt"
)

meteos_possibles = [
    "clair",
    "pluie",
    "brouillard",
    "vent",
    "orage",
    "neige",
]

# Territoire dont les événements sont actuellement
# en cours de résolution.
#
# Lorsque cette variable vaut None, les messages
# sont seulement envoyés vers le rapport long.
territoire_rapport_actuel = None

# Météo choisie une seule fois pour le tour.
meteo_tour = None
controle_territoires_path = game_path / "systeme" / "controle_territoires.txt"


def territoires_adjacents(territoire_depart, territoire_arrivee):
    voisins = carte_territoires.get(territoire_depart, [])
    return territoire_arrivee in voisins

def territoires_ravitailles(joueur, controle_territoires):
    if joueur == "j1":
        base = "base1"
    else:
        base = "base2"

    ravitailles = set()
    a_explorer = [base]

    while a_explorer:
        territoire_actuel = a_explorer.pop()

        if territoire_actuel in ravitailles:
            continue

        if controle_territoires.get(territoire_actuel) != joueur:
            continue

        ravitailles.add(territoire_actuel)

        for voisin in carte_territoires.get(territoire_actuel, []):
            if voisin not in ravitailles:
                a_explorer.append(voisin)

    return ravitailles

def choisir_orientation_general():
    chance = random.randint(1, 100)

    if chance == 1:
        return orientation_rare

    return random.choice(orientations)

def creer_general(chemin_general, nom_general):
    chemin_general.mkdir(exist_ok=True)

    for bloc in ordre_blocs:
        bloc_dir = chemin_general / bloc
        bloc_dir.mkdir(exist_ok=True)

    fiche = chemin_general / "fiche.txt"

    if not fiche.exists():
        orientation = choisir_orientation_general()

        texte = [
            f"nom={nom_general}",
            f"orientation={orientation}",
            "strategie=0",
            "force=0",
            "experience=0",
        ]

        fiche.write_text("\n".join(texte), encoding="utf-8")

    ordre = chemin_general / "ordre.txt"

    if not ordre.exists():
        ordre.write_text(
            "1-2\n",
            encoding="utf-8"
        )

def donner_permissions_general(chemin_general, joueur):
    # Donne les bonnes permissions à un général.
    # Le général appartient au joueur et reste privé.

    uid = pwd.getpwnam(joueur).pw_uid
    gid = grp.getgrnam(joueur).gr_gid

    os.chown(chemin_general, uid, gid)
    os.chmod(chemin_general, 0o700)

    for element in chemin_general.rglob("*"):
        os.chown(element, uid, gid)

        if element.is_dir():
            os.chmod(element, 0o700)
        else:
            os.chmod(element, 0o600)


def home_contient_general(joueur):
    # Vérifie si le home du joueur contient déjà un général.
    #
    # Règle V1.5 :
    # si un général est déjà dans le home, aucun nouveau général n'apparaît.

    home_joueur = Path(f"/home/{joueur}")

    if not home_joueur.exists():
        return False

    for element in home_joueur.iterdir():
        if element.is_dir() and element.name.startswith("general"):
            return True

    return False


def lire_compteur_general(joueur):
    # Lit le compteur de génération des généraux.
    #
    # Exemple :
    # /home/game/systeme/compteur_general_j1.txt contient 2
    # donc le prochain général sera general3.

    compteur_path = game_path / "systeme" / f"compteur_general_{joueur}.txt"

    if not compteur_path.exists():
        return 0

    texte = compteur_path.read_text(encoding="utf-8").strip()

    if texte == "":
        return 0

    return int(texte)


def sauvegarder_compteur_general(joueur, numero):
    # Sauvegarde le dernier numéro de général créé.

    compteur_path = game_path / "systeme" / f"compteur_general_{joueur}.txt"
    compteur_path.parent.mkdir(exist_ok=True)
    compteur_path.write_text(str(numero), encoding="utf-8")


def faire_apparaitre_general_si_possible(joueur):
    # Fait apparaître un seul général dans le home du joueur si possible.
    #
    # Règles :
    # - si le home contient déjà un général : rien n'apparaît
    # - si le joueur a déjà atteint la limite : rien n'apparaît
    # - sinon, le prochain generalX apparaît dans /home/joueur/

    if home_contient_general(joueur):
        afficher_et_ecrire(
            f"{joueur} a déjà un général dans son home. Aucun nouveau général."
        )
        return

    dernier_numero = lire_compteur_general(joueur)

    if dernier_numero >= max_generaux_par_joueur:
        afficher_et_ecrire(
            f"{joueur} a déjà atteint la limite de {max_generaux_par_joueur} généraux."
        )
        return

    nouveau_numero = dernier_numero + 1
    nom_general = f"general{nouveau_numero}"
    chemin_general = Path(f"/home/{joueur}") / nom_general

    creer_general(chemin_general, nom_general)
    donner_permissions_general(chemin_general, joueur)
    sauvegarder_compteur_general(joueur, nouveau_numero)

    enregistrer_position_nouveau_general(
    joueur,
    nom_general
)

    afficher_et_ecrire(
        f"Nouveau général apparu pour {joueur} : {nom_general}"
    )


def est_general_valide(chemin_general):
    # Un général doit être un dossier.
    if not chemin_general.is_dir():
        return False

    # Une seule écriture est autorisée pour chaque identité.
    if numero_general_depuis_nom(chemin_general.name) is None:
        return False

    # Un général doit contenir les quatre blocs militaires.
    for bloc in ordre_blocs:
        if not (chemin_general / bloc).is_dir():
            return False

    # La fiche est importante pour les futures statistiques.
    if not (chemin_general / "fiche.txt").is_file():
        return False

    # L'ordre est important pour les futures décisions tactiques.
    if not (chemin_general / "ordre.txt").is_file():
        return False

    return True

def lire_fiche_general(chemin_general):
    # Lecture simple de fiche.txt sous forme de dictionnaire.
    # Exemple :
    # nom=general1
    # orientation=stratege
    # strategie=0
    # force=0
    # experience=0

    fiche_path = chemin_general / "fiche.txt"
    fiche = {}

    if not fiche_path.exists():
        return fiche

    lignes = fiche_path.read_text(encoding="utf-8").splitlines()

    for ligne in lignes:
        if "=" not in ligne:
            continue

        cle, valeur = ligne.split("=", 1)
        fiche[cle.strip()] = valeur.strip()

    return fiche

def lire_ordres_general(chemin_general):
    # Lit et valide les ordres présents dans ordre.txt.
    #
    # Formats acceptés :
    #
    # type-numero
    #
    # type-numero-specification
    #
    # Exemples :
    #
    # 1-1
    # 1-2
    # 2-1
    # 2-2
    # 3-1
    # 2-2-1
    #
    # Un ordre mal écrit ou inconnu est ignoré.

    ordre_path = chemin_general / "ordre.txt"
    ordres = []

    if not ordre_path.exists():
        return ordres

    lignes = ordre_path.read_text(
        encoding="utf-8"
    ).splitlines()

    for ligne in lignes:
        ligne = ligne.strip()

        if ligne == "":
            continue

        morceaux = ligne.split("-")

        # Un ordre contient deux ou trois nombres.
        if len(morceaux) not in [2, 3]:
            afficher_et_ecrire(
                f"Ordre ignoré pour "
                f"{chemin_general.name} : "
                f"{ligne} "
                f"[format invalide]"
            )

            continue

        # Tous les éléments doivent être numériques.
        if not all(
            morceau.isdigit()
            for morceau in morceaux
        ):
            afficher_et_ecrire(
                f"Ordre ignoré pour "
                f"{chemin_general.name} : "
                f"{ligne} "
                f"[valeur non numérique]"
            )

            continue

        type_ordre = int(morceaux[0])
        numero_ordre = int(morceaux[1])

        specification = None

        if len(morceaux) == 3:
            specification = int(morceaux[2])

        identifiant = (
            f"{type_ordre}-"
            f"{numero_ordre}"
        )

        # L'ordre doit exister dans la légende.
        if identifiant not in legende_ordres:
            afficher_et_ecrire(
                f"Ordre ignoré pour "
                f"{chemin_general.name} : "
                f"{ligne} "
                f"[ordre inconnu]"
            )

            continue

        fiche_ordre = legende_ordres[
            identifiant
        ]

        ordres.append(
            {
                "identifiant": identifiant,
                "texte": ligne,
                "type": type_ordre,
                "numero": numero_ordre,
                "specification": specification,
                "nom": fiche_ordre["nom"],
                "categorie": fiche_ordre[
                    "categorie"
                ],
            }
        )

    return ordres

def general_possede_ordre(
    general,
    identifiant_ordre
):
    # Vérifie si un général possède un ordre précis.
    #
    # Exemple :
    #
    # general_possede_ordre(general, "2-2")
    #
    # retourne True si le général possède
    # l'ordre pluie de flèches.

    if general is None:
        return False

    for ordre in general.get("ordres", []):
        if (
            ordre["identifiant"]
            == identifiant_ordre
        ):
            return True

    return False



def lire_generaux_territoire(territory):
    # Lit les généraux présents sur un territoire.
    #
    # Structure attendue :
    # territoire/joueur/emplacement/generalX/
    #
    # Exemple :
    # /home/game/terrain1/j1/1/general1
    #
    # Cette fonction ne sanctionne rien et ne déplace rien.
    # Les anomalies sont traitées auparavant par les
    # fonctions de sécurisation des mouvements.

    resultat = {}

    for joueur in joueurs:
        resultat[joueur] = {}

        for emplacement in emplacements:
            resultat[joueur][emplacement] = None

            emplacement_dir = (
                territory
                / joueur
                / emplacement
            )

            if not emplacement_dir.exists():
                continue

            generaux_trouves = []

            for element in emplacement_dir.iterdir():
                if (
                    element.is_dir()
                    and numero_general_depuis_nom(
                        element.name
                    ) is not None
                ):
                    generaux_trouves.append(element)

            if len(generaux_trouves) == 0:
                continue

            generaux_trouves = sorted(
                generaux_trouves,
                key=lambda chemin: (
                    numero_general_depuis_nom(
                        chemin.name
                    )
                )
            )

            # Normalement, après la sécurisation,
            # il ne doit rester qu'un seul général.
            #
            # Cette fonction se contente de lire
            # le premier dossier valide trouvé.
            chemin_general = generaux_trouves[0]

            # Répare la structure interne du général
            # si un bloc, fiche.txt ou ordre.txt manque.
            creer_general(
                chemin_general,
                chemin_general.name
            )

            if not est_general_valide(
                chemin_general
            ):
                afficher_et_ecrire(
                    f"Général invalide ignoré : "
                    f"{joueur} "
                    f"{chemin_general.name} "
                    f"sur {territory.name}/"
                    f"{emplacement}"
                )

                continue

            # Vérifie la limite de 20 unités.
            verifier_limite_unites_general(
                chemin_general
            )

            blocs_general = lire_blocs_general(
                chemin_general
            )

            resultat[joueur][emplacement] = {
                "chemin": chemin_general,
                "nom": chemin_general.name,
                "joueur": joueur,
                "emplacement": emplacement,
                "fiche": lire_fiche_general(
                    chemin_general
                ),
                "ordres": lire_ordres_general(
                    chemin_general
                ),
                "blocs": blocs_general,
                "total_unites": total_unites_general(
                    blocs_general
                ),
            }

    return resultat


def lire_blocs_general(chemin_general):
    # Lit les unités d'un seul général.
    #
    # Structure attendue :
    # generalX/avant/infanterie1
    # generalX/droite/cavalerie1
    # generalX/gauche/...
    # generalX/arriere/...

    blocs_general = {}

    # On prépare les quatre blocs, même s'ils sont vides.
    for bloc in ordre_blocs:
        blocs_general[bloc] = {
            "type": "vide",
            "nombre": 0,
            "unites": [],
        }

    for bloc in ordre_blocs:
        bloc_dir = chemin_general / bloc

        # Si le bloc manque, on le recrée.
        # Ça évite qu'un général soit cassé par erreur.
        bloc_dir.mkdir(exist_ok=True)

        type_trouves = []
        unites_trouvees = []
        a_supprimer = []

        for unite in bloc_dir.iterdir():
            type_unite = identifier_unite(unite)

            if type_unite == "inconnu":
                a_supprimer.append(unite)
                continue

            type_trouves.append(type_unite)
            unites_trouvees.append(unite)

        # Supprimer les unités invalides.
        for unite in a_supprimer:
            if unite.is_dir():
                shutil.rmtree(unite)
            else:
                unite.unlink()

            afficher_et_ecrire(f"Unité invalide supprimée : {unite.name}")

        if len(type_trouves) > 0:
            effectifs = {}
            for type_unite in type_trouves:
                effectifs[type_unite] = effectifs.get(type_unite, 0) + 1

            maximum = max(effectifs.values())
            types_majoritaires = [
                type_unite for type_unite, nombre in effectifs.items()
                if nombre == maximum
            ]

            # Une égalité en tête rend le bloc invalide : tout supprimer.
            if len(types_majoritaires) > 1:
                for unite in unites_trouvees:
                    shutil.rmtree(unite)
                afficher_et_ecrire(
                    f"Bloc mixte invalide (égalité) : {bloc_dir}. "
                    f"{len(unites_trouvees)} unité(s) supprimée(s)."
                )
                continue

            type_majoritaire = types_majoritaires[0]
            unites_conservees = []
            for unite, type_unite in zip(unites_trouvees, type_trouves):
                if type_unite == type_majoritaire:
                    unites_conservees.append(unite)
                else:
                    shutil.rmtree(unite)
                    afficher_et_ecrire(
                        f"Unité non cohérente supprimée : {unite} "
                        f"({type_unite}, bloc {type_majoritaire})."
                    )

            blocs_general[bloc]["type"] = type_majoritaire
            blocs_general[bloc]["nombre"] = len(unites_conservees)
            blocs_general[bloc]["unites"] = unites_conservees

    return blocs_general

def total_unites_general(blocs_general):
    # Calcule le nombre total d'unités dans un général.
    #
    # Exemple :
    # avant   : 5 unités
    # droite  : 3 unités
    # gauche  : 2 unités
    # arriere : 0 unité
    # total   : 10 unités

    total = 0

    for bloc in ordre_blocs:
        total += blocs_general[bloc]["nombre"]

    return total

def total_unites_joueur_generaux(generaux_territoire, joueur):
    # Calcule le nombre total d'unités d'un joueur sur un territoire,
    # en utilisant le nouveau système des généraux.
    #
    # Exemple :
    # j1 emplacement 1 : general1 avec 10 unités
    # j1 emplacement 2 : general2 avec 5 unités
    # total j1 sur le territoire = 15 unités

    total = 0

    for emplacement in emplacements:
        general = generaux_territoire[joueur][emplacement]

        if general is None:
            continue

        total += general["total_unites"]

    return total

def controle_territoire_generaux(generaux_territoire):
    # Détermine qui contrôle un territoire avec le système des généraux.
    #
    # Pour l'instant, règle simple :
    # - si j1 a des unités et j2 non : j1 contrôle
    # - si j2 a des unités et j1 non : j2 contrôle
    # - si personne n'a d'unités : neutre
    # - si les deux ont des unités : contesté

    total_j1 = total_unites_joueur_generaux(generaux_territoire, "j1")
    total_j2 = total_unites_joueur_generaux(generaux_territoire, "j2")

    if total_j1 > 0 and total_j2 == 0:
        return "j1"

    elif total_j2 > 0 and total_j1 == 0:
        return "j2"

    elif total_j1 == 0 and total_j2 == 0:
        return "neutre"

    else:
        return "conteste"
    
def charger_controle_territoires():
    # Charge le contrôle des territoires au tour précédent.
    #
    # Exemple du fichier :
    # base1=j1
    # terrain1=neutre
    # terrain2=j2

    controle = {}

    # Par défaut, tous les territoires sont neutres.
    for territory in territoires:
        controle[territory.name] = "neutre"

    if not controle_territoires_path.exists():
        return controle

    lignes = controle_territoires_path.read_text(encoding="utf-8").splitlines()

    for ligne in lignes:
        if "=" not in ligne:
            continue

        nom_territoire, valeur = ligne.split("=", 1)
        controle[nom_territoire.strip()] = valeur.strip()

    return controle


def sauvegarder_controle_territoires():
    # Sauvegarde le contrôle des territoires après la résolution.
    #
    # Ce fichier servira au prochain tour pour savoir
    # qui défend un territoire.

    lignes = []

    for territory in territoires:
        generaux_territoire = lire_generaux_territoire(territory)
        controle = controle_territoire_generaux(generaux_territoire)

        lignes.append(f"{territory.name}={controle}")

    controle_territoires_path.parent.mkdir(exist_ok=True)
    controle_territoires_path.write_text("\n".join(lignes), encoding="utf-8")


def charger_positions_generaux():
    positions = {}

    if not positions_generaux_path.exists():
        return positions

    lignes = positions_generaux_path.read_text(
        encoding="utf-8"
    ).splitlines()

    for ligne in lignes:
        if "=" not in ligne:
            continue

        identifiant, position = ligne.split("=", 1)
        positions[identifiant.strip()] = position.strip()

    return positions


def sauvegarder_positions_generaux(positions):
    lignes = []

    for identifiant in sorted(positions):
        lignes.append(
            f"{identifiant}={positions[identifiant]}"
        )

    positions_generaux_path.parent.mkdir(exist_ok=True)

    positions_generaux_path.write_text(
        "\n".join(lignes),
        encoding="utf-8"
    )

def numero_general_depuis_nom(nom_general):
    # Vérifie que le nom est exactement du type :
    # general1
    # general2
    # general15
    #
    # Pas de zéro initial ni de chiffre Unicode : general01 est invalide.

    prefixe = "general"

    if not nom_general.startswith(prefixe):
        return None

    numero_texte = nom_general[len(prefixe):]

    if (
        not numero_texte.isascii()
        or not numero_texte.isdecimal()
        or numero_texte.startswith("0")
    ):
        return None

    try:
        return int(numero_texte)
    except ValueError:
        return None

def trouver_position_general(joueur, nom_general):
    # 1. Home
    chemin_home = Path(f"/home/{joueur}") / nom_general

    if chemin_home.is_dir():
        return "home", chemin_home

    # 2. Zone de repli
    chemin_repli = repli_path / joueur / nom_general

    if chemin_repli.is_dir():
        return "repli", chemin_repli

    # 3. Territoires
    for territory in territoires:
        for emplacement in emplacements:
            chemin = (
                territory
                / joueur
                / emplacement
                / nom_general
            )

            if chemin.is_dir():
                return territory.name, chemin

    return None, None

def trouver_toutes_positions_general(joueur, nom_general):
    # Recherche toutes les occurrences du même général.
    #
    # Normalement cette liste doit contenir exactement
    # un seul élément.

    positions = []

    # ------------------------------------------
    # Home
    # ------------------------------------------

    chemin_home = (
        Path(f"/home/{joueur}")
        / nom_general
    )

    if chemin_home.is_dir():
        positions.append(
            {
                "position": "home",
                "chemin": chemin_home,
            }
        )

    # ------------------------------------------
    # Repli
    # ------------------------------------------

    chemin_repli = (
        repli_path
        / joueur
        / nom_general
    )

    if chemin_repli.is_dir():
        positions.append(
            {
                "position": "repli",
                "chemin": chemin_repli,
            }
        )

    # ------------------------------------------
    # Territoires
    # ------------------------------------------

    for territory in territoires:
        for emplacement in emplacements:

            chemin = (
                territory
                / joueur
                / emplacement
                / nom_general
            )

            if chemin.is_dir():
                positions.append(
                    {
                        "position": territory.name,
                        "chemin": chemin,
                        "emplacement": emplacement,
                    }
                )

    return positions

def joueur_proprietaire_chemin(chemin):
    # Retrouve le joueur propriétaire d'un dossier
    # à partir de son UID Linux.
    #
    # Retourne :
    # "j1", "j2" ou None si le propriétaire
    # ne correspond à aucun joueur connu.

    try:
        uid_chemin = chemin.stat().st_uid
    except FileNotFoundError:
        return None

    for joueur in joueurs:
        uid_joueur = pwd.getpwnam(joueur).pw_uid

        if uid_chemin == uid_joueur:
            return joueur

    return None

def securiser_generaux_mauvais_joueur(
    positions_avant
):
    # Vérifie qu'un général se trouve bien dans
    # l'arborescence de son véritable propriétaire.
    #
    # L'identité du propriétaire est déterminée
    # grâce à l'UID Linux du dossier.
    #
    # Exemple interdit :
    # un dossier appartenant à j1 placé dans :
    # terrain2/j2/1/general1
    #
    # La fonction retourne les identifiants punis.

    generaux_punis = set()

    for joueur_zone in joueurs:

        zones = [
            (
                "home",
                Path(f"/home/{joueur_zone}")
            ),
            (
                "repli",
                repli_path / joueur_zone
            ),
        ]

        for territory in territoires:
            for emplacement in emplacements:
                zones.append(
                    (
                        territory.name,
                        territory
                        / joueur_zone
                        / emplacement
                    )
                )

        for nom_zone, chemin_zone in zones:

            if not chemin_zone.exists():
                continue

            for chemin_general in list(
                chemin_zone.iterdir()
            ):
                if not chemin_general.is_dir():
                    continue

                numero = numero_general_depuis_nom(
                    chemin_general.name
                )

                if numero is None:
                    continue

                proprietaire_reel = (
                    joueur_proprietaire_chemin(
                        chemin_general
                    )
                )

                # Le propriétaire est correct.
                if proprietaire_reel == joueur_zone:
                    continue

                # Propriétaire Linux inconnu :
                # le dossier ne peut pas être considéré
                # comme un véritable général.
                if proprietaire_reel is None:
                    afficher_et_ecrire(
                        f"Général au propriétaire inconnu "
                        f"supprimé : "
                        f"{chemin_general}"
                    )

                    shutil.rmtree(
                        chemin_general
                    )

                    continue

                identifiant = (
                    f"{proprietaire_reel}:"
                    f"{chemin_general.name}"
                )

                afficher_et_ecrire(
                    f"{identifiant} placé dans "
                    f"l'arborescence de {joueur_zone} "
                    f"({nom_zone})."
                )

                dernier_numero = lire_compteur_general(
                    proprietaire_reel
                )

                # Le dossier appartient bien à un joueur,
                # mais le général n'est pas officiellement actif.
                if (
                    numero < 1
                    or numero > dernier_numero
                    or identifiant not in positions_avant
                ):
                    afficher_et_ecrire(
                        f"Général non autorisé supprimé : "
                        f"{identifiant}"
                    )

                    shutil.rmtree(
                        chemin_general
                    )

                    continue

                occurrences_correctes = (
                    trouver_toutes_positions_general(
                        proprietaire_reel,
                        chemin_general.name
                    )
                )

                # --------------------------------------
                # Aucune autre occurrence
                # --------------------------------------

                if len(occurrences_correctes) == 0:
                    destination = (
                        repli_path
                        / proprietaire_reel
                        / chemin_general.name
                    )

                    destination.parent.mkdir(
                        parents=True,
                        exist_ok=True
                    )

                    # Il ne devrait normalement pas déjà
                    # exister de destination puisque
                    # occurrences_correctes est vide.
                    if destination.exists():
                        shutil.rmtree(
                            destination
                        )

                    shutil.move(
                        str(chemin_general),
                        str(destination)
                    )

                    donner_permissions_general(
                        destination,
                        proprietaire_reel
                    )

                    generaux_punis.add(
                        identifiant
                    )

                    afficher_et_ecrire(
                        f"{identifiant} envoyé au repli "
                        f"de {proprietaire_reel}."
                    )

                    continue

                # --------------------------------------
                # Une occurrence correcte existe déjà
                # --------------------------------------

                shutil.rmtree(
                    chemin_general
                )

                afficher_et_ecrire(
                    f"Copie située chez {joueur_zone} "
                    f"supprimée : {identifiant}"
                )

                # S'il n'existe qu'une occurrence correcte,
                # elle reçoit immédiatement la sanction.
                #
                # S'il y en a plusieurs, la fonction
                # securiser_generaux_dupliques()
                # traitera ensuite la duplication.
                if len(occurrences_correctes) == 1:
                    occurrence_reelle = (
                        occurrences_correctes[0]
                    )

                    if (
                        occurrence_reelle["position"]
                        != "repli"
                    ):
                        envoyer_general_au_repli(
                            proprietaire_reel,
                            chemin_general.name,
                            occurrence_reelle["chemin"]
                        )

                    generaux_punis.add(
                        identifiant
                    )

                    afficher_et_ecrire(
                        f"{identifiant} envoyé au repli "
                        f"pour placement chez "
                        f"{joueur_zone}."
                    )

    return generaux_punis

def supprimer_generaux_non_autorises():
    # Supprime les dossiers generalX qui ne correspondent
    # à aucun général généré et encore officiellement actif.

    positions = charger_positions_generaux()

    for joueur in joueurs:
        dernier_numero = lire_compteur_general(joueur)

        # ------------------------------------------
        # Home
        # ------------------------------------------

        zones_a_verifier = [
            Path(f"/home/{joueur}"),
            repli_path / joueur,
        ]

        for zone in zones_a_verifier:

            if not zone.exists():
                continue

            for element in list(zone.iterdir()):

                if not element.is_dir():
                    continue

                if not element.name.startswith("general"):
                    continue

                numero = numero_general_depuis_nom(
                    element.name
                )

                if (
                    numero is None
                    or numero < 1
                    or numero > dernier_numero
                    or f"{joueur}:{element.name}" not in positions
                ):
                    afficher_et_ecrire(
                        f"Général non autorisé supprimé : "
                        f"{joueur} {element.name}"
                    )

                    shutil.rmtree(element)

        # ------------------------------------------
        # Territoires
        # ------------------------------------------

        for territory in territoires:
            for emplacement in emplacements:

                emplacement_dir = (
                    territory
                    / joueur
                    / emplacement
                )

                if not emplacement_dir.exists():
                    continue

                for element in list(
                    emplacement_dir.iterdir()
                ):

                    if not element.is_dir():
                        continue

                    if not element.name.startswith(
                        "general"
                    ):
                        continue

                    numero = numero_general_depuis_nom(
                        element.name
                    )

                    if (
                        numero is None
                        or numero < 1
                        or numero > dernier_numero
                        or f"{joueur}:{element.name}" not in positions
                    ):
                        afficher_et_ecrire(
                            f"Général non autorisé supprimé : "
                            f"{joueur} {element.name} "
                            f"sur {territory.name}"
                        )

                        shutil.rmtree(element)


def securiser_generaux_dupliques(positions_avant):
    # Détecte les généraux présents plusieurs fois.
    #
    # En cas de duplication :
    # - une seule copie est conservée ;
    # - les autres sont supprimées ;
    # - la copie conservée est envoyée au repli.
    #
    # La fonction retourne les identifiants punis.

    generaux_punis = set()

    for joueur in joueurs:
        dernier_numero = lire_compteur_general(joueur)

        for numero in range(
            1,
            dernier_numero + 1
        ):
            nom_general = f"general{numero}"
            identifiant = (
                f"{joueur}:{nom_general}"
            )

            occurrences = (
                trouver_toutes_positions_general(
                    joueur,
                    nom_general
                )
            )

            if len(occurrences) <= 1:
                continue

            afficher_et_ecrire(
                f"{identifiant} est présent "
                f"{len(occurrences)} fois."
            )

            ancienne_position = (
                positions_avant.get(identifiant)
            )

            copie_a_garder = None

            # Si possible, conserver la copie située
            # à la position officielle du tour précédent.
            for occurrence in occurrences:

                if (
                    occurrence["position"]
                    == ancienne_position
                ):
                    copie_a_garder = occurrence
                    break

            # Si aucune copie n'est à l'ancienne position,
            # on en choisit une de manière déterministe.
            if copie_a_garder is None:
                occurrences = sorted(
                    occurrences,
                    key=lambda x: str(x["chemin"])
                )

                copie_a_garder = occurrences[0]

            # Supprimer toutes les autres copies.
            for occurrence in occurrences:

                if occurrence is copie_a_garder:
                    continue

                chemin = occurrence["chemin"]

                if chemin.exists():
                    shutil.rmtree(chemin)

                    afficher_et_ecrire(
                        f"Copie illégale supprimée : "
                        f"{identifiant} "
                        f"({occurrence['position']})"
                    )

            # La copie réelle reçoit malgré tout
            # la sanction de repli.
            chemin_garde = (
                copie_a_garder["chemin"]
            )

            if (
                copie_a_garder["position"]
                != "repli"
            ):
                envoyer_general_au_repli(
                    joueur,
                    nom_general,
                    chemin_garde
                )

            generaux_punis.add(
                identifiant
            )

            afficher_et_ecrire(
                f"{identifiant} envoyé au repli "
                f"pour duplication."
            )

    return generaux_punis


def securiser_emplacements_generaux():
    # Un emplacement ne peut contenir qu'un général.
    #
    # Si plusieurs généraux sont placés dans le même
    # emplacement, tous sont envoyés au repli.
    #
    # Cela empêche de choisir arbitrairement lequel
    # serait autorisé à rester.

    generaux_punis = set()

    for territory in territoires:
        for joueur in joueurs:
            for emplacement in emplacements:

                emplacement_dir = (
                    territory
                    / joueur
                    / emplacement
                )

                if not emplacement_dir.exists():
                    continue

                generaux_trouves = []

                for element in (
                    emplacement_dir.iterdir()
                ):
                    if (
                        element.is_dir()
                        and element.name.startswith(
                            "general"
                        )
                    ):
                        generaux_trouves.append(
                            element
                        )

                if len(generaux_trouves) <= 1:
                    continue

                afficher_et_ecrire(
                    f"Emplacement invalide : "
                    f"{territory.name} "
                    f"{joueur}/{emplacement} "
                    f"contient plusieurs généraux."
                )

                for chemin_general in (
                    generaux_trouves
                ):
                    identifiant = (
                        f"{joueur}:"
                        f"{chemin_general.name}"
                    )

                    envoyer_general_au_repli(
                        joueur,
                        chemin_general.name,
                        chemin_general
                    )

                    generaux_punis.add(
                        identifiant
                    )

                    afficher_et_ecrire(
                        f"{identifiant} envoyé "
                        f"au repli."
                    )

    return generaux_punis


def verifier_tous_les_deplacements():
    # Vérifie et sécurise tous les déplacements
    # avant la résolution des combats.
    #
    # Ordre :
    # 1. détecter les généraux placés chez
    #    le mauvais joueur ;
    # 2. supprimer les faux généraux ;
    # 3. détecter les duplications ;
    # 4. détecter les conflits d'emplacement ;
    # 5. vérifier les déplacements ;
    # 6. enregistrer les marches forcées.

    afficher_et_ecrire(
        "\n=== Vérification des déplacements ==="
    )

    positions = charger_positions_generaux()
    controle_avant = charger_controle_territoires()

    # ------------------------------------------
    # Sécurité générale
    # ------------------------------------------

    punis_mauvais_joueur = (
        securiser_generaux_mauvais_joueur(
            positions
        )
    )

    supprimer_generaux_non_autorises()

    punis_duplication = (
        securiser_generaux_dupliques(
            positions
        )
    )

    punis_emplacement = (
        securiser_emplacements_generaux()
    )

    generaux_deja_punis = (
        punis_mauvais_joueur
        | punis_duplication
        | punis_emplacement
    )

    # ------------------------------------------
    # Fatigue du nouveau tour
    # ------------------------------------------

    generaux_fatigues = set()
    nouvelles_positions = {}

    # ------------------------------------------
    # Vérification individuelle
    # ------------------------------------------

    for joueur in joueurs:
        dernier_numero = (
            lire_compteur_general(joueur)
        )

        for numero in range(
            1,
            dernier_numero + 1
        ):
            nom_general = f"general{numero}"

            identifiant = (
                f"{joueur}:{nom_general}"
            )

            position_actuelle, chemin_actuel = (
                trouver_position_general(
                    joueur,
                    nom_general
                )
            )

            # Général détruit ou absent.
            if position_actuelle is None:
                continue

            # Un général sanctionné pendant l'audit
            # doit maintenant se trouver au repli.
            if identifiant in generaux_deja_punis:
                nouvelles_positions[
                    identifiant
                ] = "repli"

                continue

            origine = positions.get(
                identifiant
            )

            # Aucun enregistrement implicite : seul le moteur peut
            # autoriser une nouvelle identité lors de sa génération.
            if origine is None:
                shutil.rmtree(chemin_actuel)
                afficher_et_ecrire(
                    f"Général sans position officielle supprimé : {identifiant}"
                )

                continue

            autorise, fatigue, raison = (
                verifier_deplacement_general(
                    joueur,
                    origine,
                    position_actuelle,
                    controle_avant
                )
            )

            # --------------------------------------
            # Mouvement valide
            # --------------------------------------

            if autorise:
                nouvelles_positions[
                    identifiant
                ] = position_actuelle

                if fatigue:
                    generaux_fatigues.add(
                        identifiant
                    )

                    afficher_et_ecrire(
                        f"{identifiant} : "
                        f"{origine} -> "
                        f"{position_actuelle} "
                        f"[MARCHE FORCÉE - FATIGUE]"
                    )

                elif origine == position_actuelle:
                    afficher_et_ecrire(
                        f"{identifiant} : "
                        f"reste sur {origine}"
                    )

                else:
                    afficher_et_ecrire(
                        f"{identifiant} : "
                        f"{origine} -> "
                        f"{position_actuelle} "
                        f"[{raison}]"
                    )

                continue

            # --------------------------------------
            # Mouvement interdit
            # --------------------------------------

            afficher_et_ecrire(
                f"{identifiant} : "
                f"déplacement interdit "
                f"{origine} -> "
                f"{position_actuelle}"
            )

            afficher_et_ecrire(
                f"Raison : {raison}"
            )

            envoyer_general_au_repli(
                joueur,
                nom_general,
                chemin_actuel
            )

            nouvelles_positions[
                identifiant
            ] = "repli"

            afficher_et_ecrire(
                f"{identifiant} envoyé au repli."
            )

    # ------------------------------------------
    # Sauvegarde
    # ------------------------------------------

    sauvegarder_positions_generaux(
        nouvelles_positions
    )

    sauvegarder_generaux_fatigues(
        generaux_fatigues
    )


def enregistrer_position_nouveau_general(joueur, nom_general):
    positions = charger_positions_generaux()

    identifiant = f"{joueur}:{nom_general}"
    positions[identifiant] = "home"

    sauvegarder_positions_generaux(positions)

def chemin_deux_territoires(
    origine,
    destination
):
    # Cherche un territoire intermédiaire permettant :
    # origine -> intermédiaire -> destination.

    for intermediaire in carte_territoires.get(
        origine,
        []
    ):
        if destination in carte_territoires.get(
            intermediaire,
            []
        ):
            return intermediaire

    return None

def verifier_deplacement_general(
    joueur,
    origine,
    destination,
    controle_avant
):
    base = bases_joueurs[joueur]

    # Aucun déplacement.
    if origine == destination:
        return True, False, "immobile"

    # Première apparition :
    # home -> propre base uniquement.
    if origine == "home":
        if destination == base:
            return True, False, "deploiement"

        return False, False, "sortie du home interdite"

    # Depuis le repli :
    # uniquement vers sa propre base.
    if origine == "repli":
        if destination == base:
            return True, False, "retour de repli"

        return False, False, "sortie du repli interdite"

    # Destination spéciale interdite.
    if destination in ["home", "repli"]:
        return False, False, "destination interdite"

    # Déplacement normal : 1 territoire.
    if destination in carte_territoires.get(
        origine,
        []
    ):
        return True, False, "deplacement normal"

    # Marche forcée : 2 territoires.
    intermediaire = chemin_deux_territoires(
        origine,
        destination
    )

    if intermediaire is None:
        return False, False, "destination trop éloignée"

    # Le territoire intermédiaire peut être :
    # - allié ;
    # - neutre.
    #
    # Le passage est interdit uniquement s'il est
    # contrôlé par l'ennemi.

    controle_intermediaire = controle_avant.get(
        intermediaire,
        "neutre"
    )

    joueur_ennemi = ennemi_de(joueur)

    if controle_intermediaire == joueur_ennemi:
        return (
            False,
            False,
            f"{intermediaire} est contrôlé par {joueur_ennemi}"
        )

    return True, True, "marche forcee"

def sauvegarder_generaux_fatigues(generaux_fatigues):
    fatigue_generaux_path.parent.mkdir(exist_ok=True)

    fatigue_generaux_path.write_text(
        "\n".join(sorted(generaux_fatigues)),
        encoding="utf-8"
    )


def charger_generaux_fatigues():
    if not fatigue_generaux_path.exists():
        return set()

    return set(
        ligne.strip()
        for ligne in fatigue_generaux_path.read_text(
            encoding="utf-8"
        ).splitlines()
        if ligne.strip()
    )


def general_est_fatigue(general):
    # Vérifie si un général est fatigué à cause
    # d'une marche forcée effectuée pendant ce tour.

    generaux_fatigues = charger_generaux_fatigues()

    identifiant = (
        f"{general['joueur']}:{general['nom']}"
    )

    return identifiant in generaux_fatigues

def envoyer_general_au_repli(
    joueur,
    nom_general,
    chemin_actuel
):
    # Envoie le général et toutes ses unités
    # dans sa zone de repli.
    #
    # La fonction refuse d'écraser un général
    # déjà présent dans le repli.

    destination = (
        repli_path
        / joueur
        / nom_general
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Le général est déjà au repli.
    if chemin_actuel == destination:
        donner_permissions_general(
            destination,
            joueur
        )

        return destination

    # Une autre occurrence existe déjà au repli.
    # On ne supprime aucun dossier ici :
    # les fonctions de sécurisation doivent
    # résoudre la duplication auparavant.
    if destination.exists():
        afficher_et_ecrire(
            f"Impossible d'envoyer "
            f"{joueur}:{nom_general} au repli : "
            f"une occurrence existe déjà."
        )

        return None

    shutil.move(
        str(chemin_actuel),
        str(destination)
    )

    donner_permissions_general(
        destination,
        joueur
    )

    return destination
def general_a_des_unites(general):
    # Vérifie si un général existe et possède encore des unités.

    if general is None:
        return False

    return general["total_unites"] > 0


def generaux_actifs_joueur(generaux_territoire, joueur):
    # Retourne la liste des généraux d'un joueur qui ont encore des unités.
    #
    # Un général vide n'est pas considéré comme actif.

    actifs = []

    for emplacement in emplacements:
        general = generaux_territoire[joueur][emplacement]

        if general_a_des_unites(general):
            actifs.append(general)

    return actifs

def joueur_possede_ordre_armee(
    generaux_territoire,
    joueur,
    identifiant_ordre
):
    # Vérifie si au moins un général actif du joueur
    # possède l'ordre d'armée demandé.

    for emplacement in emplacements:
        general = (
            generaux_territoire[
                joueur
            ][
                emplacement
            ]
        )

        if not general_a_des_unites(general):
            continue

        if general_possede_ordre(
            general,
            identifiant_ordre
        ):
            return True

    return False

def supprimer_general_si_vide(general):
    # Supprime du plateau un général qui n'a plus aucune unité.

    if general is None:
        return False

    chemin_general = general["chemin"]

    if not chemin_general.exists():
        return False

    blocs_general = lire_blocs_general(chemin_general)
    total = total_unites_general(blocs_general)

    if total > 0:
        return False

    afficher_et_ecrire(
        f"{general['joueur']} {general['nom']} "
        f"n'a plus d'unités. Général supprimé."
    )

    shutil.rmtree(chemin_general)

    # Retirer l'identité dès la destruction, avant le prochain tour.
    # Le compteur reste inchangé : ce numéro ne doit jamais être réutilisé.
    positions = charger_positions_generaux()
    positions.pop(f"{general['joueur']}:{general['nom']}", None)
    sauvegarder_positions_generaux(positions)

    return True

def combat_entre_generaux(general_1, general_2):
    # Affrontement complet entre deux généraux.
    #
    # Déroulement :
    # 1. Choc initial entre les blocs placés face à face.
    # 2. Manœuvres entre les blocs survivants.

    joueur_1 = general_1["joueur"]
    joueur_2 = general_2["joueur"]

    chemin_1 = general_1["chemin"]
    chemin_2 = general_2["chemin"]

    initial_1 = total_general_depuis_chemin(chemin_1)
    initial_2 = total_general_depuis_chemin(chemin_2)

    afficher_et_ecrire(
        f"\nEngagement : "
        f"{joueur_1} {general_1['nom']} VS "
        f"{joueur_2} {general_2['nom']}"
    )

    initiative_avant, details_choc = phase_engagement_initial(
        general_1,
        general_2
    )

    details_manoeuvre = []

    # Le choc initial peut avoir détruit un général.
    if not chemin_1.exists() or not chemin_2.exists():
        return {
            "joueur_1": joueur_1,
            "general_1": general_1["nom"],
            "initial_1": initial_1,
            "final_1": total_general_depuis_chemin(chemin_1),
            "joueur_2": joueur_2,
            "general_2": general_2["nom"],
            "initial_2": initial_2,
            "final_2": total_general_depuis_chemin(chemin_2),
            "chocs": details_choc,
            "manoeuvres": details_manoeuvre,
        }

    afficher_et_ecrire("\n=== MANŒUVRE ===")

    tour = 0
    numero_manoeuvre = 0

    while tour < 10:
        tour += 1

        if not chemin_1.exists() or not chemin_2.exists():
            break

        armee = {
            joueur_1: lire_blocs_general(chemin_1),
            joueur_2: lire_blocs_general(chemin_2),
        }

        if (
            total_unites_general(armee[joueur_1]) == 0
            or total_unites_general(armee[joueur_2]) == 0
        ):
            break

        afficher_et_ecrire(f"\n--- Tour de manœuvre {tour} ---")
        attaque_effectuee = False

        actions = ordre_actions_manoeuvre(armee, initiative_avant)
        afficher_et_ecrire(
            "\nOrdre global de manœuvre : "
            + ", ".join(f"{joueur} {bloc}" for joueur, bloc in actions)
        )

        for joueur_attaquant, bloc_attaquant in actions:
            if not chemin_1.exists() or not chemin_2.exists():
                break

            armee = {
                joueur_1: lire_blocs_general(chemin_1),
                joueur_2: lire_blocs_general(chemin_2),
            }

            if total_unites_general(armee[joueur_1]) == 0:
                break
            if total_unites_general(armee[joueur_2]) == 0:
                break

            # Les pertes d'une action précédente peuvent avoir détruit ce bloc.
            infos_attaquant = armee[joueur_attaquant][bloc_attaquant]
            if infos_attaquant["nombre"] <= 0:
                continue

            cible = choisir_cible(
                armee,
                joueur_attaquant,
                infos_attaquant["type"]
            )

            if cible is None:
                continue

            if joueur_attaquant == joueur_1:
                general_attaquant = general_1
                general_defenseur = general_2
            else:
                general_attaquant = general_2
                general_defenseur = general_1

            detail = attaque_ciblee(
                armee,
                general_attaquant,
                general_defenseur,
                bloc_attaquant,
                cible
            )

            numero_manoeuvre += 1
            detail["numero"] = numero_manoeuvre
            detail["tour"] = tour
            details_manoeuvre.append(detail)
            attaque_effectuee = True

        if not attaque_effectuee:
            afficher_et_ecrire(
                "Aucune manœuvre possible. L'affrontement est bloqué."
            )
            break

    if chemin_1.exists():
        supprimer_general_si_vide(general_1)
    if chemin_2.exists():
        supprimer_general_si_vide(general_2)

    return {
        "joueur_1": joueur_1,
        "general_1": general_1["nom"],
        "initial_1": initial_1,
        "final_1": total_general_depuis_chemin(chemin_1),
        "joueur_2": joueur_2,
        "general_2": general_2["nom"],
        "initial_2": initial_2,
        "final_2": total_general_depuis_chemin(chemin_2),
        "chocs": details_choc,
        "manoeuvres": details_manoeuvre,
    }

def resoudre_attaque_frontale(
    territory,
    mode_combat
):
    # Ordre 1-2 : attaque frontale.
    #
    # Les généraux placés dans les mêmes
    # emplacements s'affrontent d'abord :
    #
    # 1 contre 1
    # 2 contre 2
    # 3 contre 3
    # 4 contre 4
    #
    # Après cette phase, les survivants seront
    # pris en charge par le combat rangé.

    afficher_et_ecrire(
        "\n=== ORDRE 1-2 : ATTAQUE FRONTALE ==="
    )

    engagement_effectue = False
    resultats = []

    for emplacement in emplacements:

        # Relire entièrement le territoire avant
        # chaque duel, car le duel précédent peut
        # avoir supprimé un général.
        generaux_territoire = (
            lire_generaux_territoire(
                territory
            )
        )

        general_j1 = (
            generaux_territoire[
                "j1"
            ][
                emplacement
            ]
        )

        general_j2 = (
            generaux_territoire[
                "j2"
            ][
                emplacement
            ]
        )

        # Il faut un général actif dans les deux camps
        # au même emplacement.
        if not general_a_des_unites(
            general_j1
        ):
            afficher_et_ecrire(
                f"Emplacement {emplacement} : "
                f"aucun général actif pour j1."
            )

            continue

        if not general_a_des_unites(
            general_j2
        ):
            afficher_et_ecrire(
                f"Emplacement {emplacement} : "
                f"aucun général actif pour j2."
            )

            continue

        engagement_effectue = True

        afficher_et_ecrire(
            f"\n--- Duel frontal "
            f"{mode_combat} : "
            f"emplacement {emplacement} ---"
        )

        afficher_et_ecrire(
            f"{general_j1['nom']} "
            f"contre "
            f"{general_j2['nom']}"
        )

        resultat_duel = combat_entre_generaux(
            general_j1,
            general_j2
        )

        ecrire_ligne_affrontement_territoire(
            territory,
            emplacement,
            resultat_duel
        )
        resultats.append((emplacement, resultat_duel))

    if not engagement_effectue:
        afficher_et_ecrire(
            "Ordre 1-2 sans effet : "
            "aucun couple de généraux correspondants."
        )

    return resultats

def resoudre_combat_range(
    territory,
    mode_combat
):
    # Moteur commun de résolution.
    #
    # Première étape éventuelle :
    # - ordre 1-2 : affrontements par emplacement.
    #
    # Deuxième étape :
    # - combat rangé entre les premiers
    #   généraux encore actifs ;
    # - le survivant continue ;
    # - le combat s'arrête lorsqu'un camp disparaît.

    generaux_depart = (
        lire_generaux_territoire(
            territory
        )
    )

    ordre_frontal_j1 = (
        joueur_possede_ordre_armee(
            generaux_depart,
            "j1",
            "1-2"
        )
    )

    ordre_frontal_j2 = (
        joueur_possede_ordre_armee(
            generaux_depart,
            "j2",
            "1-2"
        )
    )

    # Pour cette première version,
    # un seul des deux camps suffit pour provoquer
    # l'organisation frontale du combat.
    if ordre_frontal_j1 or ordre_frontal_j2:

        camps = []

        if ordre_frontal_j1:
            camps.append("j1")

        if ordre_frontal_j2:
            camps.append("j2")

        afficher_et_ecrire(
            "Ordre frontal demandé par : "
            + ", ".join(camps)
        )

        ecrire_rapport_territoire(
            territory,
            ""
        )
        ecrire_rapport_territoire(
            territory,
            "================ ENGAGEMENT FRONTAL ================"
        )
        ecrire_rapport_territoire(
            territory,
            ""
        )
        ecrire_entete_tableau_affrontements(
            territory,
            "Pos"
        )

        engagements_frontaux = resoudre_attaque_frontale(
            territory,
            mode_combat
        )

        ecrire_fin_tableau_affrontements(
            territory
        )

        ecrire_details_engagements(
            territory,
            engagements_frontaux
        )

    # --------------------------------------------------
    # Combat rangé
    # --------------------------------------------------

    round_combat = 0
    tableau_combat_range_ouvert = False
    engagements_combat_range = []

    while round_combat < 20:
        round_combat += 1

        generaux_territoire = (
            lire_generaux_territoire(
                territory
            )
        )

        controle = (
            controle_territoire_generaux(
                generaux_territoire
            )
        )

        if controle != "conteste":
            if tableau_combat_range_ouvert:
                ecrire_fin_tableau_affrontements(
                    territory
                )
                ecrire_details_engagements(
                    territory,
                    engagements_combat_range
                )
            else:
                ecrire_rapport_territoire(territory, "")
                ecrire_rapport_territoire(
                    territory,
                    "=================== COMBAT RANGÉ ==================="
                )
                ecrire_rapport_territoire(
                    territory,
                    "Aucun combat rangé."
                )

            afficher_et_ecrire(
                f"Fin du combat. "
                f"Controle final : {controle}"
            )

            return

        actifs_j1 = generaux_actifs_joueur(
            generaux_territoire,
            "j1"
        )

        actifs_j2 = generaux_actifs_joueur(
            generaux_territoire,
            "j2"
        )

        if (
            len(actifs_j1) == 0
            or len(actifs_j2) == 0
        ):
            controle = (
                controle_territoire_generaux(
                    generaux_territoire
                )
            )

            if tableau_combat_range_ouvert:
                ecrire_fin_tableau_affrontements(
                    territory
                )
                ecrire_details_engagements(
                    territory,
                    engagements_combat_range
                )
            else:
                ecrire_rapport_territoire(territory, "")
                ecrire_rapport_territoire(
                    territory,
                    "=================== COMBAT RANGÉ ==================="
                )
                ecrire_rapport_territoire(
                    territory,
                    "Aucun combat rangé."
                )

            afficher_et_ecrire(
                f"Fin du combat. "
                f"Controle final : {controle}"
            )

            return

        general_j1 = actifs_j1[0]
        general_j2 = actifs_j2[0]

        afficher_et_ecrire(
            f"\n--- Combat rangé "
            f"{mode_combat} "
            f"{round_combat} ---"
        )

        resultat_combat_range = combat_entre_generaux(
            general_j1,
            general_j2
        )

        if round_combat == 1:
            ecrire_rapport_territoire(
                territory,
                ""
            )
            ecrire_rapport_territoire(
                territory,
                "=================== COMBAT RANGÉ ==================="
            )
            ecrire_rapport_territoire(
                territory,
                ""
            )
            ecrire_entete_tableau_affrontements(
                territory,
                "Tour"
            )
            tableau_combat_range_ouvert = True

        ecrire_ligne_affrontement_territoire(
            territory,
            round_combat,
            resultat_combat_range
        )
        engagements_combat_range.append(
            (round_combat, resultat_combat_range)
        )

    if tableau_combat_range_ouvert:
        ecrire_fin_tableau_affrontements(
            territory
        )
        ecrire_details_engagements(
            territory,
            engagements_combat_range
        )
    else:
        ecrire_rapport_territoire(territory, "")
        ecrire_rapport_territoire(
            territory,
            "=================== COMBAT RANGÉ ==================="
        )
        ecrire_rapport_territoire(
            territory,
            "Aucun combat rangé."
        )

    generaux_territoire = (
        lire_generaux_territoire(
            territory
        )
    )

    controle = (
        controle_territoire_generaux(
            generaux_territoire
        )
    )

    afficher_et_ecrire(
        f"Limite de rounds atteinte "
        f"sur {territory.name}. "
        f"Controle actuel : {controle}"
    )

def resoudre_combat_v15(territory):
    # Résolution OFF/OFF.

    afficher_et_ecrire(
        f"\n=== Combat OFF/OFF sur {territory.name} ==="
    )

    resoudre_combat_range(
        territory,
        "OFF/OFF"
    )


    # ==================================================
# ORDRES DES GENERAUX : FONCTIONS EN SUSPENS
#
# Elles seront utilisées plus tard lors du travail
# sur la transition et la sélection des généraux.
# Elles ne doivent pas intervenir dans la résolution
# interne d'un engagement pour le moment.
# ==================================================




def resoudre_combat_off_def(territory, defenseur):
    # Résolution OFF/DEF.
    #
    # Pour l'instant, le moteur de combat est le même que OFF/OFF.
    # Mais on garde la distinction défenseur / attaquant pour les règles futures :
    # terrain, fortification, ravitaillement, avant-poste, brouillard de guerre, etc.

    attaquant = ennemi_de(defenseur)

    afficher_et_ecrire(
        f"\n=== Combat OFF/DEF sur {territory.name} ==="
    )
    afficher_et_ecrire(
        f"Défenseur : {defenseur} | Attaquant : {attaquant}"
    )

    resoudre_combat_range(territory, "OFF/DEF")


def lancer_bataille_v15():
    # Boucle de résolution V1.5.
    #
    # Elle décide :
    # - OFF/OFF si le territoire était neutre
    #   ou contesté avant ;
    # - OFF/DEF si le territoire appartenait
    #   à un joueur avant.
    #
    # Le rapport court ne reçoit que les
    # informations publiques.
    #
    # Le rapport long et le rapport territorial
    # reçoivent les informations détaillées.

    afficher_et_ecrire(
        "\n=== RÉSOLUTION MYTHODEA V1.5 ==="
    )

    controle_avant_resolution = (
        charger_controle_territoires()
    )

    for territory in territoires:
        definir_territoire_rapport(
            territory
        )

        ancien_controle = (
            controle_avant_resolution.get(
                territory.name,
                "neutre"
            )
        )

        afficher_et_ecrire("")
        afficher_et_ecrire("")

        afficher_et_ecrire(
            f"=== TERRITOIRE : "
            f"{territory.name.upper()} ==="
        )

        afficher_et_ecrire("")

        afficher_et_ecrire(
            f"Contrôle avant le tour : "
            f"{ancien_controle}"
        )

        generaux_territoire = (
            lire_generaux_territoire(
                territory
            )
        )

        controle_avant_combat = (
            controle_territoire_generaux(
                generaux_territoire
            )
        )

        afficher_et_ecrire(
            f"Contrôle après les déplacements : "
            f"{controle_avant_combat}"
        )

        total_initial_j1 = total_unites_joueur_generaux(
            generaux_territoire,
            "j1"
        )
        total_initial_j2 = total_unites_joueur_generaux(
            generaux_territoire,
            "j2"
        )

        # Rapport territorial lisible.
        chemin_rapport_territoire(
            territory
        ).write_text(
            "",
            encoding="utf-8"
        )

        ecrire_rapport_territoire(
            territory,
            "=" * 56
        )
        ecrire_rapport_territoire(
            territory,
            f"{territory.name.upper()} — RAPPORT DE BATAILLE"
        )
        ecrire_rapport_territoire(
            territory,
            "=" * 56
        )
        ecrire_rapport_territoire(
            territory,
            ""
        )
        ecrire_rapport_territoire(
            territory,
            f"Météo            : {meteo_tour}"
        )
        ecrire_rapport_territoire(
            territory,
            f"Contrôle initial : {ancien_controle}"
        )
        generaux_initiaux_j1 = len(generaux_actifs_joueur(generaux_territoire, "j1"))
        generaux_initiaux_j2 = len(generaux_actifs_joueur(generaux_territoire, "j2"))

        ecrire_rapport_territoire(
            territory,
            f"Forces initiales : j1 = {total_initial_j1} | j2 = {total_initial_j2}"
        )
        ecrire_rapport_territoire(
            territory,
            f"Généraux engagés: j1 = {generaux_initiaux_j1} | j2 = {generaux_initiaux_j2}"
        )
        ecrire_rapport_territoire(
            territory,
            ""
        )
        ecrire_rapport_territoire(
            territory,
            "Légende : ○ survivant | × détruit | effectif initial → effectif final"
        )

        # --------------------------------------
        # Présence initiale
        # --------------------------------------

        afficher_et_ecrire(
            "\n--- Présence avant combat ---"
        )

        for joueur in joueurs:
            afficher_et_ecrire(
                f"\n{joueur} :"
            )

            for emplacement in emplacements:
                general = (
                    generaux_territoire[
                        joueur
                    ][
                        emplacement
                    ]
                )

                if general is None:
                    afficher_et_ecrire(
                        f"emplacement "
                        f"{emplacement} : vide"
                    )

                    continue

                afficher_et_ecrire(
                    f"emplacement "
                    f"{emplacement} : "
                    f"{general['nom']} "
                    f"({general['total_unites']} unités)"
                )

                # Informations de niveau renseignement.
                # Elles sont visibles dans le rapport long
                # et territorial pendant la V1.5.
                fiche = general["fiche"]

                afficher_et_ecrire(
                    f"  orientation : "
                    f"{fiche.get('orientation', 'inconnue')}"
                )

                afficher_et_ecrire(
                    f"  stratégie : "
                    f"{fiche.get('strategie', 'inconnue')}"
                )

                afficher_et_ecrire(
                    f"  force : "
                    f"{fiche.get('force', 'inconnue')}"
                )

                afficher_et_ecrire(
                    f"  expérience : "
                    f"{fiche.get('experience', 'inconnue')}"
                )

                if general_est_fatigue(general):
                    afficher_et_ecrire(
                        "  fatigue : oui"
                    )
                else:
                    afficher_et_ecrire(
                        "  fatigue : non"
                    )

                if len(general["ordres"]) == 0:
                    afficher_et_ecrire(
                        "  ordres : aucun ordre valide"
                    )
                else:
                    textes_ordres = [
                        ordre["texte"]
                        for ordre
                        in general["ordres"]
                    ]

                    afficher_et_ecrire(
                        "  ordres : "
                        + ", ".join(
                            textes_ordres
                        )
                    )

        # --------------------------------------
        # Combat
        # --------------------------------------

        combat_declenche = False
        mode_combat = None

        if controle_avant_combat == "conteste":
            combat_declenche = True

            if ancien_controle in joueurs:
                mode_combat = "OFF/DEF"

                ecrire_rapport_territoire(
                    territory,
                    f"Mode de combat   : {mode_combat} ({ancien_controle} défend)"
                )

                afficher_et_ecrire(
                    f"\nCombat détecté : "
                    f"OFF/DEF. "
                    f"{ancien_controle} défend."
                )

                resoudre_combat_off_def(
                    territory,
                    ancien_controle
                )

            else:
                mode_combat = "OFF/OFF"

                ecrire_rapport_territoire(
                    territory,
                    f"Mode de combat   : {mode_combat}"
                )

                afficher_et_ecrire(
                    "\nCombat détecté : OFF/OFF."
                )

                resoudre_combat_v15(
                    territory
                )

        else:
            afficher_et_ecrire(
                "\nAucun combat sur ce territoire."
            )

        # --------------------------------------
        # Situation finale
        # --------------------------------------

        generaux_finaux = (
            lire_generaux_territoire(
                territory
            )
        )

        controle_final = (
            controle_territoire_generaux(
                generaux_finaux
            )
        )

        afficher_et_ecrire(
            f"\nContrôle final : "
            f"{controle_final}"
        )

        afficher_et_ecrire(
            "\n--- Forces survivantes ---"
        )

        totaux_finaux = {}

        for joueur in joueurs:
            total_joueur = (
                total_unites_joueur_generaux(
                    generaux_finaux,
                    joueur
                )
            )
            totaux_finaux[joueur] = total_joueur

            afficher_et_ecrire(
                f"{joueur} : "
                f"{total_joueur} unité(s)"
            )

        ecrire_rapport_territoire(
            territory,
            ""
        )
        generaux_survivants_j1 = len(
            generaux_actifs_joueur(generaux_finaux, "j1")
        )
        generaux_survivants_j2 = len(
            generaux_actifs_joueur(generaux_finaux, "j2")
        )

        pertes_j1 = total_initial_j1 - totaux_finaux["j1"]
        pertes_j2 = total_initial_j2 - totaux_finaux["j2"]

        generaux_detruits_j1 = max(
            0,
            generaux_initiaux_j1 - generaux_survivants_j1
        )
        generaux_detruits_j2 = max(
            0,
            generaux_initiaux_j2 - generaux_survivants_j2
        )

        ecrire_rapport_territoire(
            territory,
            "===================== BILAN ====================="
        )
        ecrire_rapport_territoire(territory, "")

        bordure_bilan = "+----------------------+--------+--------+"
        ecrire_rapport_territoire(territory, bordure_bilan)
        ecrire_rapport_territoire(
            territory,
            f"| {'':<20} | {'j1':<6} | {'j2':<6} |"
        )
        ecrire_rapport_territoire(territory, bordure_bilan)

        lignes_bilan = [
            ("Forces initiales", total_initial_j1, total_initial_j2),
            ("Forces restantes", totaux_finaux["j1"], totaux_finaux["j2"]),
            ("Pertes", pertes_j1, pertes_j2),
            ("Généraux engagés", generaux_initiaux_j1, generaux_initiaux_j2),
            ("Généraux survivants", generaux_survivants_j1, generaux_survivants_j2),
            ("Généraux détruits", generaux_detruits_j1, generaux_detruits_j2),
        ]

        for libelle, valeur_j1, valeur_j2 in lignes_bilan:
            ecrire_rapport_territoire(
                territory,
                f"| {libelle:<20} | {str(valeur_j1):<6} | {str(valeur_j2):<6} |"
            )

        ecrire_rapport_territoire(territory, bordure_bilan)
        ecrire_rapport_territoire(territory, "")
        ecrire_rapport_territoire(
            territory,
            f"Contrôle final : {controle_final}"
        )

        # --------------------------------------
        # Informations publiques
        # --------------------------------------

        if combat_declenche:
            ecrire_rapport_court(
                f"{territory.name} : "
                f"combat {mode_combat}"
            )

            ecrire_rapport_court(
                f"{territory.name} : "
                f"contrôle final = "
                f"{controle_final}"
            )

        elif ancien_controle != controle_final:
            # Changement de contrôle sans combat,
            # par exemple occupation d'un territoire vide.
            ecrire_rapport_court(
                f"{territory.name} : "
                f"changement de contrôle "
                f"{ancien_controle} -> "
                f"{controle_final}"
            )

        definir_territoire_rapport(
            None
        )

    sauvegarder_controle_territoires()

    # ------------------------------------------
    # Contrôle public final de la carte
    # ------------------------------------------

    ecrire_rapport_court("")

    ecrire_rapport_court(
        "CONTRÔLE FINAL"
    )

    controle_final_carte = (
        charger_controle_territoires()
    )

    for territory in territoires:
        controle = controle_final_carte.get(
            territory.name,
            "neutre"
        )

        ecrire_rapport_court(
            f"{territory.name} : {controle}"
        )

def verifier_limite_unites_general(chemin_general):
    # Vérifie qu'un général ne dépasse pas la limite d'unités autorisée.
    #
    # Règle actuelle :
    # un général peut avoir maximum 20 unités au total,
    # réparties librement entre avant, droite, gauche, arriere.

    blocs_general = lire_blocs_general(chemin_general)
    total = total_unites_general(blocs_general)

    if total <= max_unites_par_general:
        return

    surplus = total - max_unites_par_general

    afficher_et_ecrire(
        f"{chemin_general.name} dépasse la limite : "
        f"{total}/{max_unites_par_general} unités. "
        f"{surplus} unité(s) supprimée(s)."
    )

    # On supprime les unités en trop en partant de l'arrière vers l'avant.
    ordre_suppression = ["arriere", "gauche", "droite", "avant"]

    for bloc in ordre_suppression:
        if surplus <= 0:
            break

        blocs_general = lire_blocs_general(chemin_general)
        infos = blocs_general[bloc]

        for unite in infos["unites"]:
            if surplus <= 0:
                break

            shutil.rmtree(unite)
            afficher_et_ecrire(
                f"Unité supprimée pour limite de général : {unite.name}"
            )
            surplus -= 1


def reparer_structure():
    # 1. Créer les emplacements dans les territoires
    for territory in territoires:
        for joueur in joueurs:
            joueur_dir = territory / joueur
            joueur_dir.mkdir(exist_ok=True)

            uid = pwd.getpwnam(joueur).pw_uid
            gid = grp.getgrnam(joueur).gr_gid

            os.chown(joueur_dir, uid, gid)
            os.chmod(joueur_dir, 0o700)

            for emplacement in emplacements:
                emplacement_dir = joueur_dir / emplacement
                emplacement_dir.mkdir(exist_ok=True)

                os.chown(emplacement_dir, uid, gid)
                os.chmod(emplacement_dir, 0o700)

        # Créer les zones de repli.
    for joueur in joueurs:
        repli_joueur = repli_path / joueur
        repli_joueur.mkdir(parents=True, exist_ok=True)

        uid = pwd.getpwnam(joueur).pw_uid
        gid = grp.getgrnam(joueur).gr_gid

        os.chown(repli_joueur, uid, gid)
        os.chmod(repli_joueur, 0o700)



    # 2. Faire apparaître un général par joueur si possible.
    for joueur in joueurs:
        faire_apparaitre_general_si_possible(joueur)


def lire_fichier(chemin):
    if chemin.exists():
        return chemin.read_text().strip()
    return ""


def identifier_unite(unite):
    if not unite.is_dir():
        return "inconnu"

    nom_unite = unite.name
    contenu = [element.name for element in unite.iterdir() if element.is_file()]

    types_unites = {
        ("infanterie", "arc"): "archer",
        ("infanterie", "pique"): "piquier",
        ("cavalerie", "cheval"): "cavalier",
    }

    resultats = []

    for (nom_base, equipement), type_unite in types_unites.items():
        if nom_unite.startswith(nom_base) and equipement in contenu:
            resultats.append(type_unite)

    if len(resultats) == 1:
        return resultats[0]

    return "inconnu"



def cible_facile(type_unite):
    if type_unite == "archer":
        return "piquier"

    if type_unite == "piquier":
        return "cavalier"

    if type_unite == "cavalier":
        return "archer"

    return None


def multiplicateur(type_attaquant, type_defenseur):
    if cible_facile(type_attaquant) == type_defenseur:
        return 2

    return 1



def formater_force(infos):
    # Transforme les informations d'un bloc en texte lisible.
    #
    # Exemples :
    # 0 unité  → "aucune unité"
    # 1 archer → "1 archer"
    # 4 archer → "4 archers"

    nombre = infos["nombre"]
    type_unite = infos["type"]

    if nombre <= 0:
        return "aucune unité"

    if nombre == 1:
        return f"1 {type_unite}"

    return f"{nombre} {type_unite}s"

def formater_survivants(nombre, type_unite):
    # Présente le résultat d'un bloc après le combat.

    if nombre <= 0:
        return "aucune unité survivante"

    if nombre == 1:
        return f"1 {type_unite} survivant"

    return f"{nombre} {type_unite}s survivants"

def combat_bloc(
    infos_1,
    infos_2,
    fatigue_1=False,
    fatigue_2=False
):
    # Calcule le résultat d'un combat entre deux blocs.
    #
    # Règle de fatigue :
    # si les deux unités sont normalement équivalentes,
    # l'unité non fatiguée obtient l'avantage sur l'unité fatiguée.
    #
    # La fatigue ne modifie pas les avantages naturels
    # entre types différents.

    type_1 = infos_1["type"]
    type_2 = infos_2["type"]

    nombre_1 = infos_1["nombre"]
    nombre_2 = infos_2["nombre"]

    valeur_1 = multiplicateur(
        type_1,
        type_2
    )

    valeur_2 = multiplicateur(
        type_2,
        type_1
    )

    # ------------------------------------------
    # Fatigue
    # ------------------------------------------

    if type_1 == type_2:

        # Général 1 fatigué, général 2 frais.
        if fatigue_1 and not fatigue_2:
            valeur_2 = 2

        # Général 2 fatigué, général 1 frais.
        elif fatigue_2 and not fatigue_1:
            valeur_1 = 2

    degats_1 = nombre_1 * valeur_1
    degats_2 = nombre_2 * valeur_2

    pertes_1 = degats_2 // valeur_1
    pertes_2 = degats_1 // valeur_2

    survivants_1 = max(
        0,
        nombre_1 - pertes_1
    )

    survivants_2 = max(
        0,
        nombre_2 - pertes_2
    )

    return survivants_1, survivants_2
def ennemi_de(joueur):
    if joueur == "j1":
        return "j2"

    if joueur == "j2":
        return "j1"

    return None


def trouver_cible_facile(armee, joueur_attaquant, type_attaquant):
    joueur_ennemi = ennemi_de(joueur_attaquant)
    type_cible = cible_facile(type_attaquant)

    for bloc in ordre_blocs:
        infos_ennemi = armee[joueur_ennemi][bloc]

        if infos_ennemi["type"] == type_cible and infos_ennemi["nombre"] > 0:
            return bloc

    return None


def trouver_cible_faible(armee, joueur_ennemi):
    cible = None
    plus_petit_nombre = None

    for bloc in ordre_blocs:
        infos = armee[joueur_ennemi][bloc]

        if infos["nombre"] > 0:
            if plus_petit_nombre is None or infos["nombre"] < plus_petit_nombre:
                plus_petit_nombre = infos["nombre"]
                cible = bloc

    return cible





def supprimer_unites(infos, survivants):
    nombre_actuel = infos["nombre"]
    pertes = nombre_actuel - survivants

    unites_supprimees = []

    if pertes <= 0:
        return unites_supprimees

    type_unite = infos["type"]

    unites_a_supprimer = random.sample(infos["unites"], pertes)

    for unite in unites_a_supprimer:
        unites_supprimees.append(f"{unite.name} ({type_unite})")
        shutil.rmtree(unite)

    return unites_supprimees

def afficher_tableau_pertes(pertes_joueur_1, pertes_joueur_2, nom_joueur_1, nom_joueur_2):
    if len(pertes_joueur_1) == 0 and len(pertes_joueur_2) == 0:
        afficher_et_ecrire("Aucune perte.")
        return

    afficher_et_ecrire("\nPertes :")
    afficher_et_ecrire(f"{nom_joueur_1:<35} | {nom_joueur_2:<35}")
    afficher_et_ecrire("-" * 35 + "-+-" + "-" * 35)

    longueur = max(len(pertes_joueur_1), len(pertes_joueur_2))

    for i in range(longueur):
        if i < len(pertes_joueur_1):
            gauche = pertes_joueur_1[i]
        else:
            gauche = ""

        if i < len(pertes_joueur_2):
            droite = pertes_joueur_2[i]
        else:
            droite = ""

        afficher_et_ecrire(f"{gauche:<35} | {droite:<35}")

def confrontation_directe(
    armee,
    general_1,
    general_2,
    bloc
):
    # Résout le choc initial entre deux blocs placés face à face.
    # Retourne aussi les données structurées utilisées par le rapport de bataille.

    joueur_1 = general_1["joueur"]
    joueur_2 = general_2["joueur"]

    nom_1 = f"{joueur_1} {general_1['nom']}"
    nom_2 = f"{joueur_2} {general_2['nom']}"

    infos_1 = armee[joueur_1][bloc]
    infos_2 = armee[joueur_2][bloc]

    if infos_1["nombre"] == 0 or infos_2["nombre"] == 0:
        return None

    initial_1 = infos_1["nombre"]
    initial_2 = infos_2["nombre"]
    type_1 = infos_1["type"]
    type_2 = infos_2["type"]

    fatigue_1 = general_est_fatigue(general_1)
    fatigue_2 = general_est_fatigue(general_2)

    afficher_et_ecrire("\n" + "-" * 60)
    afficher_et_ecrire(f"Choc initial : {bloc}")
    afficher_et_ecrire("")

    if fatigue_1:
        afficher_et_ecrire(f"{nom_1} : FATIGUÉ")

    if fatigue_2:
        afficher_et_ecrire(f"{nom_2} : FATIGUÉ")

    afficher_et_ecrire(f"{nom_1} : {formater_force(infos_1)}")
    afficher_et_ecrire(f"{nom_2} : {formater_force(infos_2)}")

    survivants_1, survivants_2 = combat_bloc(
        infos_1,
        infos_2,
        fatigue_1,
        fatigue_2
    )

    afficher_et_ecrire("\nRésultat :")
    afficher_et_ecrire(
        f"{nom_1} : {formater_survivants(survivants_1, type_1)}"
    )
    afficher_et_ecrire(
        f"{nom_2} : {formater_survivants(survivants_2, type_2)}"
    )

    pertes_1 = supprimer_unites(infos_1, survivants_1)
    pertes_2 = supprimer_unites(infos_2, survivants_2)

    afficher_tableau_pertes(pertes_1, pertes_2, nom_1, nom_2)

    return {
        "moment": "Choc",
        "bloc_1": bloc,
        "type_1": type_1,
        "initial_1": initial_1,
        "final_1": survivants_1,
        "bloc_2": bloc,
        "type_2": type_2,
        "initial_2": initial_2,
        "final_2": survivants_2,
    }

def phase_engagement_initial(general_1, general_2):
    joueur_1 = general_1["joueur"]
    joueur_2 = general_2["joueur"]

    chemin_1 = general_1["chemin"]
    chemin_2 = general_2["chemin"]

    afficher_et_ecrire("\n=== CHOC INITIAL ===")

    armee_depart = {
        joueur_1: lire_blocs_general(chemin_1),
        joueur_2: lire_blocs_general(chemin_2),
    }

    initiative_avant = {
        joueur_1: False,
        joueur_2: False,
    }

    details_choc = []

    infos_avant_1 = armee_depart[joueur_1]["avant"]
    infos_avant_2 = armee_depart[joueur_2]["avant"]

    if infos_avant_1["nombre"] > 0 and infos_avant_2["nombre"] == 0:
        initiative_avant[joueur_1] = True

    if infos_avant_2["nombre"] > 0 and infos_avant_1["nombre"] == 0:
        initiative_avant[joueur_2] = True

    combats_prevus = []

    for bloc in ordre_blocs:
        infos_1 = armee_depart[joueur_1][bloc]
        infos_2 = armee_depart[joueur_2][bloc]

        if infos_1["nombre"] > 0 and infos_2["nombre"] > 0:
            combats_prevus.append(bloc)

    if len(combats_prevus) == 0:
        afficher_et_ecrire("Aucune confrontation directe prévue.")
        return initiative_avant, details_choc

    afficher_et_ecrire("\nCombats prévus :")

    for bloc in combats_prevus:
        infos_1 = armee_depart[joueur_1][bloc]
        infos_2 = armee_depart[joueur_2][bloc]

        afficher_et_ecrire(
            f"- {bloc} : "
            f"{joueur_1} {general_1['nom']} {formater_force(infos_1)} "
            f"VS "
            f"{joueur_2} {general_2['nom']} {formater_force(infos_2)}"
        )

    afficher_et_ecrire("\n--- Résolution du choc initial ---")

    for bloc in combats_prevus:
        if not chemin_1.exists() or not chemin_2.exists():
            break

        armee = {
            joueur_1: lire_blocs_general(chemin_1),
            joueur_2: lire_blocs_general(chemin_2),
        }

        detail = confrontation_directe(
            armee,
            general_1,
            general_2,
            bloc
        )

        if detail is not None:
            details_choc.append(detail)

        if chemin_1.exists():
            supprimer_general_si_vide(general_1)

        if chemin_2.exists():
            supprimer_general_si_vide(general_2)

    return initiative_avant, details_choc

def attaque_ciblee(
    armee,
    general_attaquant,
    general_defenseur,
    bloc_attaquant,
    bloc_cible
):
    # Résout une manœuvre contre un bloc ennemi.
    # Retourne les données nécessaires au rapport de bataille.

    joueur_attaquant = general_attaquant["joueur"]
    joueur_ennemi = general_defenseur["joueur"]

    nom_attaquant = f"{joueur_attaquant} {general_attaquant['nom']}"
    nom_defenseur = f"{joueur_ennemi} {general_defenseur['nom']}"

    infos_attaquant = armee[joueur_attaquant][bloc_attaquant]
    infos_defenseur = armee[joueur_ennemi][bloc_cible]

    initial_attaquant = infos_attaquant["nombre"]
    initial_defenseur = infos_defenseur["nombre"]
    type_attaquant = infos_attaquant["type"]
    type_defenseur = infos_defenseur["type"]

    fatigue_attaquant = general_est_fatigue(general_attaquant)
    fatigue_defenseur = general_est_fatigue(general_defenseur)

    afficher_et_ecrire("\n" + "-" * 60)
    afficher_et_ecrire("Manœuvre")
    afficher_et_ecrire("")

    afficher_et_ecrire(
        f"{nom_attaquant} {bloc_attaquant} "
        f"attaque {nom_defenseur} {bloc_cible}"
    )

    if fatigue_attaquant:
        afficher_et_ecrire(f"{nom_attaquant} : FATIGUÉ")

    if fatigue_defenseur:
        afficher_et_ecrire(f"{nom_defenseur} : FATIGUÉ")

    afficher_et_ecrire("\nForces engagées :")
    afficher_et_ecrire(
        f"{nom_attaquant} {bloc_attaquant} : {formater_force(infos_attaquant)}"
    )
    afficher_et_ecrire(
        f"{nom_defenseur} {bloc_cible} : {formater_force(infos_defenseur)}"
    )

    survivants_attaquant, survivants_defenseur = combat_bloc(
        infos_attaquant,
        infos_defenseur,
        fatigue_attaquant,
        fatigue_defenseur
    )

    afficher_et_ecrire("\nRésultat :")
    afficher_et_ecrire(
        f"{nom_attaquant} {bloc_attaquant} : "
        f"{formater_survivants(survivants_attaquant, type_attaquant)}"
    )
    afficher_et_ecrire(
        f"{nom_defenseur} {bloc_cible} : "
        f"{formater_survivants(survivants_defenseur, type_defenseur)}"
    )

    pertes_attaquant = supprimer_unites(
        infos_attaquant,
        survivants_attaquant
    )
    pertes_defenseur = supprimer_unites(
        infos_defenseur,
        survivants_defenseur
    )

    afficher_tableau_pertes(
        pertes_attaquant,
        pertes_defenseur,
        nom_attaquant,
        nom_defenseur
    )

    return {
        "joueur_attaquant": joueur_attaquant,
        "bloc_attaquant": bloc_attaquant,
        "type_attaquant": type_attaquant,
        "initial_attaquant": initial_attaquant,
        "final_attaquant": survivants_attaquant,
        "joueur_defenseur": joueur_ennemi,
        "bloc_defenseur": bloc_cible,
        "type_defenseur": type_defenseur,
        "initial_defenseur": initial_defenseur,
        "final_defenseur": survivants_defenseur,
    }

def choisir_flanc_attaquant(armee, joueur):
    # Choisit le flanc qui doit agir en premier.
    #
    # Règles :
    # - le flanc le plus nombreux agit en premier ;
    # - en cas d'égalité, le choix est aléatoire ;
    # - si les deux flancs sont vides, retourne None.

    nombre_droite = armee[joueur]["droite"]["nombre"]
    nombre_gauche = armee[joueur]["gauche"]["nombre"]

    if nombre_droite == 0 and nombre_gauche == 0:
        return None

    if nombre_droite > nombre_gauche:
        return "droite"

    if nombre_gauche > nombre_droite:
        return "gauche"

    return random.choice(["droite", "gauche"])


def choisir_cible(armee, joueur_attaquant, type_attaquant):
    joueur_ennemi = ennemi_de(joueur_attaquant)

    cible = trouver_cible_facile(armee, joueur_attaquant, type_attaquant)

    if cible is None:
        cible = trouver_cible_faible(armee, joueur_ennemi)

    return cible


def ordre_attaques_initiative(armee, joueur, initiative_avant):
    # Ordre :
    # 1. avant-garde si elle n'a pas été engagée en phase 1
    # 2. arrière-garde
    # 3. flanc le plus nombreux
    # 4. second flanc
    # 5. avant-garde si elle n'a pas déjà agi

    ordre = []
    avant_deja_ajoute = False

    if (
        initiative_avant[joueur]
        and armee[joueur]["avant"]["nombre"] > 0
    ):
        ordre.append("avant")
        avant_deja_ajoute = True

    if armee[joueur]["arriere"]["nombre"] > 0:
        ordre.append("arriere")

    premier_flanc = choisir_flanc_attaquant(armee, joueur)

    if premier_flanc is not None:
        ordre.append(premier_flanc)

        if premier_flanc == "droite":
            second_flanc = "gauche"
        else:
            second_flanc = "droite"

        if armee[joueur][second_flanc]["nombre"] > 0:
            ordre.append(second_flanc)

    if (
        not avant_deja_ajoute
        and armee[joueur]["avant"]["nombre"] > 0
    ):
        ordre.append("avant")

    return ordre


def ordre_actions_manoeuvre(armee, initiative_avant):
    # Réunit les deux camps par priorité de bloc, sans tour réservé à un joueur.
    # Après le choc, les blocs survivants n'ont plus de vis-à-vis direct :
    # il ne reste au plus qu'un arrière et un avant (libre ou engagé).
    priorites = [[], [], [], []]

    for joueur in armee:
        for bloc in ordre_attaques_initiative(armee, joueur, initiative_avant):
            if bloc == "avant":
                rang = 0 if initiative_avant[joueur] else 3
            elif bloc == "arriere":
                rang = 1
            else:
                rang = 2
            priorites[rang].append((joueur, bloc))

    # Le tri stable après mélange départage seulement les flancs égaux au hasard.
    flancs = priorites[2]
    if len(flancs) > 1:
        random.shuffle(flancs)
        flancs.sort(key=lambda action: -armee[action[0]][action[1]]["nombre"])

    return [action for groupe in priorites for action in groupe]


def ajouter_ligne_fichier(chemin, texte):
    # Ajoute une ligne dans un fichier de rapport.

    chemin.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        chemin,
        "a",
        encoding="utf-8"
    ) as fichier:
        fichier.write(
            str(texte) + "\n"
        )


def ecrire_rapport_long(texte):
    # Rapport complet réservé au développement,
    # aux tests et au futur système de renseignement.

    ajouter_ligne_fichier(
        rapport_long_path,
        texte
    )


def ecrire_rapport_court(texte):
    # Rapport contenant uniquement
    # les informations publiques.

    ajouter_ligne_fichier(
        rapport_court_path,
        texte
    )


def chemin_rapport_territoire(territoire):
    # Accepte soit :
    # - un objet Path représentant un territoire ;
    # - directement son nom sous forme de texte.

    if isinstance(territoire, Path):
        nom_territoire = territoire.name
    else:
        nom_territoire = str(territoire)

    return (
        rapports_territoires_dir
        / f"{nom_territoire}.txt"
    )


def ecrire_rapport_territoire(
    territoire,
    texte
):
    # Écrit une information dans le rapport
    # détaillé d'un territoire.

    chemin = chemin_rapport_territoire(
        territoire
    )

    ajouter_ligne_fichier(
        chemin,
        texte
    )


def definir_territoire_rapport(territoire):
    # Définit le territoire actuellement résolu.
    #
    # À partir de cet instant, afficher_et_ecrire()
    # écrit à la fois dans :
    # - rapport_long.txt ;
    # - le rapport du territoire concerné.

    global territoire_rapport_actuel

    if territoire is None:
        territoire_rapport_actuel = None
        return

    if isinstance(territoire, Path):
        territoire_rapport_actuel = (
            territoire.name
        )
    else:
        territoire_rapport_actuel = (
            str(territoire)
        )


def afficher_et_ecrire(texte):
    # Journal technique complet.
    #
    # Les détails du moteur sont conservés uniquement
    # dans rapport_long.txt. Le rapport territorial est
    # alimenté séparément avec des informations synthétiques.

    ecrire_rapport_long(texte)


def symbole_survie(nombre_unites):
    # Symbole utilisé dans le rapport territorial lisible.

    if nombre_unites > 0:
        return "○"

    return "×"


def total_general_depuis_chemin(chemin_general):
    # Retourne le nombre d'unités encore présentes.
    # Un général supprimé vaut automatiquement zéro.

    if not chemin_general.exists():
        return 0

    return total_unites_general(
        lire_blocs_general(chemin_general)
    )


def ecrire_entete_tableau_affrontements(
    territoire,
    colonne_numero
):
    bordure = "+------+--------------------------+-----+--------------------------+"

    ecrire_rapport_territoire(territoire, bordure)
    ecrire_rapport_territoire(
        territoire,
        f"| {colonne_numero:<4} | {'j1':<24} | {'':^3} | {'j2':<24} |"
    )
    ecrire_rapport_territoire(territoire, bordure)


def ecrire_fin_tableau_affrontements(territoire):
    ecrire_rapport_territoire(
        territoire,
        "+------+--------------------------+-----+--------------------------+"
    )


def ecrire_ligne_affrontement_territoire(
    territoire,
    etiquette,
    resultat
):
    symbole_1 = symbole_survie(resultat["final_1"])
    symbole_2 = symbole_survie(resultat["final_2"])

    gauche = (
        f"{resultat['general_1']} {symbole_1} "
        f"{resultat['initial_1']} → {resultat['final_1']}"
    )
    droite = (
        f"{resultat['general_2']} {symbole_2} "
        f"{resultat['initial_2']} → {resultat['final_2']}"
    )

    ecrire_rapport_territoire(
        territoire,
        f"| {str(etiquette):<4} | {gauche:<24} | {'<->':^3} | {droite:<24} |"
    )


def nom_type_unite(type_unite, nombre):
    singulier = {
        "archer": "archer",
        "piquier": "piquier",
        "cavalier": "cavalier",
        "vide": "vide",
    }
    pluriel = {
        "archer": "archers",
        "piquier": "piquiers",
        "cavalier": "cavaliers",
        "vide": "vide",
    }

    if nombre == 1:
        return singulier.get(type_unite, type_unite)
    return pluriel.get(type_unite, type_unite)


def formater_force_rapport(nombre, type_unite):
    return f"{nombre} {nom_type_unite(type_unite, nombre)}"


def ecrire_entete_detail_blocs(territoire):
    bordure = (
        "+--------+-----------+---------------+-----+-----------+---------------+----------------+"
    )
    ecrire_rapport_territoire(territoire, bordure)
    ecrire_rapport_territoire(
        territoire,
        "| Moment | Bloc j1   | Unités j1     |     | Bloc j2   | Unités j2     | Résultat       |"
    )
    ecrire_rapport_territoire(territoire, bordure)


def ecrire_fin_detail_blocs(territoire):
    ecrire_rapport_territoire(
        territoire,
        "+--------+-----------+---------------+-----+-----------+---------------+----------------+"
    )


def ecrire_detail_choc(territoire, detail):
    force_1 = formater_force_rapport(detail["initial_1"], detail["type_1"])
    force_2 = formater_force_rapport(detail["initial_2"], detail["type_2"])
    resultat = f"j1 ({detail['final_1']}) / j2 ({detail['final_2']})"

    ecrire_rapport_territoire(
        territoire,
        f"| {'Choc':<6} | {detail['bloc_1']:<9} | {force_1:<13} "
        f"| {'<->':^3} | {detail['bloc_2']:<9} | {force_2:<13} | {resultat:<14} |"
    )


def normaliser_manoeuvre(detail, joueur_1):
    if detail["joueur_attaquant"] == joueur_1:
        return {
            "bloc_1": detail["bloc_attaquant"],
            "type_1": detail["type_attaquant"],
            "initial_1": detail["initial_attaquant"],
            "final_1": detail["final_attaquant"],
            "bloc_2": detail["bloc_defenseur"],
            "type_2": detail["type_defenseur"],
            "initial_2": detail["initial_defenseur"],
            "final_2": detail["final_defenseur"],
            "fleche": "->",
        }

    return {
        "bloc_1": detail["bloc_defenseur"],
        "type_1": detail["type_defenseur"],
        "initial_1": detail["initial_defenseur"],
        "final_1": detail["final_defenseur"],
        "bloc_2": detail["bloc_attaquant"],
        "type_2": detail["type_attaquant"],
        "initial_2": detail["initial_attaquant"],
        "final_2": detail["final_attaquant"],
        "fleche": "<-",
    }


def ecrire_detail_manoeuvre(territoire, resultat_engagement, detail):
    normalise = normaliser_manoeuvre(
        detail,
        resultat_engagement["joueur_1"]
    )

    force_1 = formater_force_rapport(
        normalise["initial_1"],
        normalise["type_1"]
    )
    force_2 = formater_force_rapport(
        normalise["initial_2"],
        normalise["type_2"]
    )
    resultat = (
        f"j1 ({normalise['final_1']}) / "
        f"j2 ({normalise['final_2']})"
    )

    ecrire_rapport_territoire(
        territoire,
        f"| {('M' + str(detail['numero'])):<6} "
        f"| {normalise['bloc_1']:<9} | {force_1:<13} "
        f"| {normalise['fleche']:^3} "
        f"| {normalise['bloc_2']:<9} | {force_2:<13} "
        f"| {resultat:<14} |"
    )


def ecrire_detail_engagement(territoire, etiquette, resultat):
    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(
        territoire,
        f"--- Engagement {etiquette} : "
        f"j1 {resultat['general_1']} <-> j2 {resultat['general_2']} ---"
    )

    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(territoire, "CHOC INITIAL")
    ecrire_rapport_territoire(territoire, "")

    if resultat["chocs"]:
        ecrire_entete_detail_blocs(territoire)
        for detail in resultat["chocs"]:
            ecrire_detail_choc(territoire, detail)
        ecrire_fin_detail_blocs(territoire)
    else:
        ecrire_rapport_territoire(territoire, "Aucun choc direct entre blocs.")

    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(territoire, "MANŒUVRE")
    ecrire_rapport_territoire(territoire, "")

    if resultat["manoeuvres"]:
        ecrire_entete_detail_blocs(territoire)
        for detail in resultat["manoeuvres"]:
            ecrire_detail_manoeuvre(territoire, resultat, detail)
        ecrire_fin_detail_blocs(territoire)
    else:
        ecrire_rapport_territoire(territoire, "Aucune manœuvre.")

    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(
        territoire,
        f"Résultat : j1 {resultat['general_1']} "
        f"{resultat['initial_1']} → {resultat['final_1']} | "
        f"j2 {resultat['general_2']} "
        f"{resultat['initial_2']} → {resultat['final_2']}"
    )


def ecrire_details_engagements(territoire, engagements):
    if not engagements:
        return

    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(
        territoire,
        "================ DÉTAIL DES AFFRONTEMENTS ================"
    )

    for etiquette, resultat in engagements:
        ecrire_detail_engagement(
            territoire,
            etiquette,
            resultat
        )


def choisir_meteo_tour():
    # Choisit une météo aléatoire.
    #
    # La météo est commune à toute la carte
    # et n'a encore aucun effet sur le jeu.

    return random.choice(
        meteos_possibles
    )


def sauvegarder_meteo(meteo):
    # Conserve la météo du tour dans le système.

    meteo_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    meteo_path.write_text(
        meteo,
        encoding="utf-8"
    )


def charger_meteo():
    # Permet aux futures fonctions du jeu
    # de consulter la météo choisie.

    if not meteo_path.exists():
        return None

    meteo = meteo_path.read_text(
        encoding="utf-8"
    ).strip()

    if meteo == "":
        return None

    return meteo


def preparer_rapports():
    # Prépare tous les rapports du nouveau tour.
    #
    # Les rapports du tour précédent sont effacés.
    # Une nouvelle météo est ensuite générée.

    global meteo_tour
    global territoire_rapport_actuel

    territoire_rapport_actuel = None

    rapport_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    rapports_territoires_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # Effacer les rapports généraux.
    rapport_court_path.write_text(
        "",
        encoding="utf-8"
    )

    rapport_long_path.write_text(
        "",
        encoding="utf-8"
    )

    # Préparer un rapport pour chaque territoire.
    for territory in territoires:
        chemin = chemin_rapport_territoire(
            territory
        )

        chemin.write_text(
            "",
            encoding="utf-8"
        )

    # Générer la météo commune au tour.
    meteo_tour = choisir_meteo_tour()

    sauvegarder_meteo(
        meteo_tour
    )

    # ------------------------------------------
    # Rapport court public
    # ------------------------------------------

    ecrire_rapport_court(
        "=== RÉSUMÉ DU TOUR ==="
    )

    ecrire_rapport_court("")

    ecrire_rapport_court(
        f"MÉTÉO : {meteo_tour}"
    )

    ecrire_rapport_court("")

    # ------------------------------------------
    # Rapport long complet
    # ------------------------------------------

    ecrire_rapport_long(
        "=== RAPPORT LONG DU TOUR ==="
    )

    ecrire_rapport_long("")

    ecrire_rapport_long(
        f"Météo du tour : {meteo_tour}"
    )

    ecrire_rapport_long(
        "Effet actuel de la météo : aucun"
    )

    ecrire_rapport_long("")

    # ------------------------------------------
    # Rapports territoriaux
    # ------------------------------------------

    for territory in territoires:
        ecrire_rapport_territoire(
            territory,
            (
                f"=== RAPPORT DE "
                f"{territory.name.upper()} ==="
            )
        )

        ecrire_rapport_territoire(
            territory,
            ""
        )

        ecrire_rapport_territoire(
            territory,
            f"Météo : {meteo_tour}"
        )

        ecrire_rapport_territoire(
            territory,
            ""
        )


def afficher_fin_de_tour():
    # Affiche automatiquement le rapport court
    # dans le terminal.
    #
    # Pour les autres rapports, affiche seulement
    # des commandes prêtes à copier-coller.

    print()
    print("=" * 48)
    print("                 RAPPORT COURT")
    print("=" * 48)
    print()

    if rapport_court_path.exists():
        contenu = rapport_court_path.read_text(
            encoding="utf-8"
        ).strip()

        if contenu:
            print(contenu)
        else:
            print("Le rapport court est vide.")
    else:
        print("Le rapport court est introuvable.")

    print()
    print("=" * 48)
    print("            CONSULTER LES RAPPORTS")
    print("=" * 48)
    print()

    print("Rapport long complet :")
    print(
        f"cat {rapport_long_path}"
    )

    print()

    print("Exemple de rapport territorial :")
    print(
        "cat "
        f"{rapports_territoires_dir / 'terrain1.txt'}"
    )

    print()

    print("Liste des rapports territoriaux :")
    print(
        f"ls {rapports_territoires_dir}/"
    )

    print()

def vider_fichier(chemin):
    chemin.write_text("", encoding="utf-8")


def verifier_victoire():
    objectif_base1 = lire_fichier(game_path / "base1" / "objectif.txt")
    objectif_base2 = lire_fichier(game_path / "base2" / "objectif.txt")

    tentative_j1 = lire_fichier(game_path / "base2" / "tentative_j1.txt")
    tentative_j2 = lire_fichier(game_path / "base1" / "tentative_j2.txt")

    if tentative_j1 == objectif_base2 and tentative_j1 != "":
        return "j1"

    if tentative_j2 == objectif_base1 and tentative_j2 != "":
        return "j2"

    if tentative_j1 != "":
        afficher_et_ecrire("Tentative de victoire de j1 échouée")
        vider_fichier(game_path / "base2" / "tentative_j1.txt")

    if tentative_j2 != "":
        afficher_et_ecrire("Tentative de victoire de j2 échouée")
        vider_fichier(game_path / "base1" / "tentative_j2.txt")

    return None



preparer_rapports()
reparer_structure()

verifier_tous_les_deplacements()

vainqueur = verifier_victoire()

if vainqueur:
    ecrire_rapport_court("")

    ecrire_rapport_court(
        f"VICTOIRE DE {vainqueur}"
    )

    ecrire_rapport_long(
        f"Victoire de {vainqueur}."
    )

else:
    lancer_bataille_v15()

afficher_fin_de_tour()
