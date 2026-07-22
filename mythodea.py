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


ordre_blocs = ["avant", "droite", "gauche", "arriere"]
joueurs = ["j1", "j2"]

emplacements = ["1", "2", "3","4"]
max_unites_par_general = 20
max_generaux_par_joueur = 5

orientations = ["stratege", "combattant"]
orientation_rare = "hybride"


rapport_path = game_path / "rapport" / "rapport_bataille.txt"

rapport_court_path = game_path / "rapport" / "rapport_court.txt"

controle_territoires_path = game_path / "systeme" / "controle_territoires.txt"

carte_territoires = {
    "base1": ["terrain1"],
    "terrain1": ["base1", "terrain2"],
    "terrain2": ["terrain1", "terrain3"],
    "terrain3": ["terrain2", "base2"],
    "base2": ["terrain3"],
}


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
        ordre.write_text("1-g-1\n2-g-1\n", encoding="utf-8")

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

    afficher_et_ecrire(
        f"Nouveau général apparu pour {joueur} : {nom_general}"
    )


def est_general_valide(chemin_general):
    # Un général doit être un dossier.
    if not chemin_general.is_dir():
        return False

    # Son nom doit commencer par "general".
    # Exemple : general1, general2, general6, etc.
    if not chemin_general.name.startswith("general"):
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
    # Lecture de ordre.txt.
    # Format prévu :
    # phase-qui-action
    #
    # Exemple :
    # 1-g-1
    # 2-g-1

    ordre_path = chemin_general / "ordre.txt"
    ordres = []

    if not ordre_path.exists():
        return ordres

    lignes = ordre_path.read_text(encoding="utf-8").splitlines()

    for ligne in lignes:
        ligne = ligne.strip()

        if ligne == "":
            continue

        morceaux = ligne.split("-")

        if len(morceaux) != 3:
            continue

        phase = morceaux[0]
        qui = morceaux[1]
        action = morceaux[2]

        ordres.append(
            {
                "phase": phase,
                "qui": qui,
                "action": action,
                "texte": ligne,
            }
        )

    return ordres

def lire_generaux_territoire(territory):
    # Lit les généraux présents sur un territoire.
    #
    # Structure attendue :
    # territoire/joueur/emplacement/generalX/
    #
    # Exemple :
    # /home/game/terrain1/j1/1/general1

    resultat = {}

    for joueur in joueurs:
        resultat[joueur] = {}

        for emplacement in emplacements:
            resultat[joueur][emplacement] = None

            emplacement_dir = territory / joueur / emplacement

            if not emplacement_dir.exists():
                continue

            generaux_trouves = []

            for element in emplacement_dir.iterdir():
                if element.is_dir() and element.name.startswith("general"):
                    generaux_trouves.append(element)

            if len(generaux_trouves) == 0:
                continue

            generaux_trouves = sorted(generaux_trouves)

            # Un seul général est autorisé par emplacement.
            # Le premier reste, les autres retournent dans le home du joueur.
            chemin_general = generaux_trouves[0]
            generaux_en_trop = generaux_trouves[1:]

            for general_en_trop in generaux_en_trop:
                destination = Path(f"/home/{joueur}") / general_en_trop.name

                if not destination.exists():
                    shutil.move(str(general_en_trop), str(destination))
                    afficher_et_ecrire(
                        f"Général en trop renvoyé au home : {joueur} {general_en_trop.name}"
                    )
                else:
                    shutil.rmtree(general_en_trop)
                    afficher_et_ecrire(
                        f"Général en trop supprimé : {joueur} {general_en_trop.name}, retour impossible"
                    )

            # On répare le général restant si fiche.txt ou ordre.txt manque.
            creer_general(chemin_general, chemin_general.name)

            if not est_general_valide(chemin_general):
                continue

            # On vérifie la limite de 20 unités par général.
            verifier_limite_unites_general(chemin_general)

            blocs_general = lire_blocs_general(chemin_general)

            resultat[joueur][emplacement] = {
                "chemin": chemin_general,
                "nom": chemin_general.name,
                "joueur": joueur,
                "emplacement": emplacement,
                "fiche": lire_fiche_general(chemin_general),
                "ordres": lire_ordres_general(chemin_general),
                "blocs": blocs_general,
                "total_unites": total_unites_general(blocs_general),
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
            blocs_general[bloc]["type"] = type_trouves[0]
            blocs_general[bloc]["nombre"] = len(type_trouves)
            blocs_general[bloc]["unites"] = unites_trouvees

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

    return True

def combat_poursuite_generaux(general_1, general_2):
    # Affrontement complet entre deux généraux.
    #
    # Cette fonction est utilisée pour OFF/OFF et OFF/DEF.
    #
    # Déroulement :
    # 1. Engagement initial entre les blocs placés face à face.
    # 2. Attaques d'initiative entre les blocs survivants.
    #
    # Les ordres des généraux sont laissés en suspens.
    # Ils serviront plus tard à choisir l'ordre des généraux
    # et leurs adversaires.

    joueur_1 = general_1["joueur"]
    joueur_2 = general_2["joueur"]

    chemin_1 = general_1["chemin"]
    chemin_2 = general_2["chemin"]

    afficher_et_ecrire(
        f"\nEngagement : "
        f"{joueur_1} {general_1['nom']} "
        f"VS "
        f"{joueur_2} {general_2['nom']}"
    )

    # --------------------------------------------------
    # Phase 1 : engagement initial
    # --------------------------------------------------

    initiative_avant = phase_engagement_initial(
        general_1,
        general_2
)

    # La phase 1 peut avoir détruit un général.
    if not chemin_1.exists() or not chemin_2.exists():
        return

    # --------------------------------------------------
    # Phase 2 : attaques d'initiative
    # --------------------------------------------------

    afficher_et_ecrire(
        "\n=== Phase 2 : attaques d'initiative ==="
    )

    tour = 0

    while tour < 10:
        tour += 1

        if not chemin_1.exists() or not chemin_2.exists():
            break

        armee = {
            joueur_1: lire_blocs_general(chemin_1),
            joueur_2: lire_blocs_general(chemin_2),
        }

        total_1 = total_unites_general(armee[joueur_1])
        total_2 = total_unites_general(armee[joueur_2])

        if total_1 == 0 or total_2 == 0:
            break

        afficher_et_ecrire(
            f"\n--- Tour d'initiative {tour} ---"
        )

        attaque_effectuee = False

        # Pour le moment, joueur_1 agit avant joueur_2.
        # La priorité sera retravaillée avec les ordres
        # et les transitions des généraux.
        for joueur_attaquant in [joueur_1, joueur_2]:

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

            ordre_attaques = ordre_attaques_initiative(
                armee,
                joueur_attaquant,
                initiative_avant
            )

            afficher_et_ecrire(
                f"\nOrdre d'initiative de {joueur_attaquant} : "
                f"{', '.join(ordre_attaques)}"
            )

            for bloc_attaquant in ordre_attaques:

                if not chemin_1.exists() or not chemin_2.exists():
                    break

                # Relire les unités avant chaque attaque,
                # car le combat précédent peut avoir provoqué des pertes.
                armee = {
                    joueur_1: lire_blocs_general(chemin_1),
                    joueur_2: lire_blocs_general(chemin_2),
                }

                if total_unites_general(armee[joueur_1]) == 0:
                    break

                if total_unites_general(armee[joueur_2]) == 0:
                    break

                infos_attaquant = armee[joueur_attaquant][bloc_attaquant]

                # Le bloc pouvait contenir des unités au début du tour,
                # mais avoir été détruit entre-temps.
                if infos_attaquant["nombre"] <= 0:
                    continue

                type_attaquant = infos_attaquant["type"]

                cible = choisir_cible(
                    armee,
                    joueur_attaquant,
                    type_attaquant
                )

                if cible is None:
                    continue

                if joueur_attaquant == joueur_1:
                    general_attaquant = general_1
                    general_defenseur = general_2
                else:
                    general_attaquant = general_2
                    general_defenseur = general_1

                attaque_ciblee(
                    armee,
                    general_attaquant,
                    general_defenseur,
                    bloc_attaquant,
                    cible
                )

                attaque_effectuee = True

        if not attaque_effectuee:
            afficher_et_ecrire(
                "Aucune attaque d'initiative possible. "
                "L'affrontement est bloqué."
            )
            break

    # Supprimer les généraux qui n'ont plus d'unités.
    if chemin_1.exists():
        supprimer_general_si_vide(general_1)

    if chemin_2.exists():
        supprimer_general_si_vide(general_2)

def resoudre_poursuite_generaux(territory, mode_combat):
    # Moteur commun de poursuite.
    #
    # Sert à OFF/OFF et OFF/DEF.
    # Règle actuelle :
    # - premier général actif de j1 contre premier général actif de j2
    # - le gagnant continue
    # - le combat continue jusqu'à disparition d'un camp

    round_combat = 0

    while round_combat < 20:
        round_combat += 1

        generaux_territoire = lire_generaux_territoire(territory)
        controle = controle_territoire_generaux(generaux_territoire)

        if controle != "conteste":
            afficher_et_ecrire(f"Fin du combat. Controle final : {controle}")
            return

        actifs_j1 = generaux_actifs_joueur(generaux_territoire, "j1")
        actifs_j2 = generaux_actifs_joueur(generaux_territoire, "j2")

        if len(actifs_j1) == 0 or len(actifs_j2) == 0:
            controle = controle_territoire_generaux(generaux_territoire)
            afficher_et_ecrire(f"Fin du combat. Controle final : {controle}")
            return

        general_j1 = actifs_j1[0]
        general_j2 = actifs_j2[0]

        afficher_et_ecrire(f"\n--- Round {mode_combat} {round_combat} ---")

        combat_poursuite_generaux(general_j1, general_j2)

    generaux_territoire = lire_generaux_territoire(territory)
    controle = controle_territoire_generaux(generaux_territoire)

    afficher_et_ecrire(
        f"Limite de rounds atteinte sur {territory.name}. Controle actuel : {controle}"
    )


def resoudre_combat_v15(territory):
    # Résolution OFF/OFF.

    afficher_et_ecrire(
        f"\n=== Combat OFF/OFF sur {territory.name} ==="
    )

    resoudre_poursuite_generaux(
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

def general_demande_frontal(general):
    # Vérifie si un général a donné un ordre frontal.
    #
    # Format accepté pour l'instant dans ordre.txt :
    # 1-g-frontal
    #
    # Plus tard, on pourra préciser :
    # 1-avant-frontal
    # 1-g-defensif
    # etc.

    for ordre in general["ordres"]:
        if ordre["action"] == "frontal":
            return True

    return False




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

    resoudre_poursuite_generaux(territory, "OFF/DEF")


def lancer_bataille_v15():
    # Boucle de résolution V1.5.
    #
    # Elle décide :
    # - OFF/OFF si le territoire était neutre ou contesté avant
    # - OFF/DEF si le territoire appartenait à un joueur avant

    afficher_et_ecrire("\n=== RESOLUTION MYTHODEA V1.5 ===")

    controle_avant_resolution = charger_controle_territoires()

    for territory in territoires:
        afficher_et_ecrire(f"\nTerritoire : {territory.name}")

        generaux_territoire = lire_generaux_territoire(territory)
        controle_actuel = controle_territoire_generaux(generaux_territoire)

        afficher_et_ecrire(f"Controle actuel : {controle_actuel}")

        for joueur in joueurs:
            afficher_et_ecrire(f"\n{joueur} :")

            for emplacement in emplacements:
                general = generaux_territoire[joueur][emplacement]

                if general is None:
                    afficher_et_ecrire(f"emplacement {emplacement} : vide")
                    continue

                afficher_et_ecrire(
                    f"emplacement {emplacement} : "
                    f"{general['nom']} "
                    f"({general['total_unites']} unités)"
                )

        if controle_actuel == "conteste":
            ancien_controle = controle_avant_resolution.get(
                territory.name,
                "neutre"
            )

            if ancien_controle in joueurs:
                afficher_et_ecrire(
                    f"Combat détecté : OFF/DEF. "
                    f"{ancien_controle} défend."
                )
                resoudre_combat_off_def(territory, ancien_controle)
            else:
                afficher_et_ecrire(
                    "Combat détecté : OFF/OFF."
                )
                resoudre_combat_v15(territory)

    sauvegarder_controle_territoires()


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

def combat_bloc(infos_1, infos_2):
    # Calcule le résultat d'un combat entre deux blocs.
    #
    # Cette fonction n'écrit rien dans le rapport.
    # Elle retourne seulement le nombre de survivants.

    type_1 = infos_1["type"]
    type_2 = infos_2["type"]

    nombre_1 = infos_1["nombre"]
    nombre_2 = infos_2["nombre"]

    valeur_1 = multiplicateur(type_1, type_2)
    valeur_2 = multiplicateur(type_2, type_1)

    degats_1 = nombre_1 * valeur_1
    degats_2 = nombre_2 * valeur_2

    pertes_1 = degats_2 // valeur_1
    pertes_2 = degats_1 // valeur_2

    survivants_1 = max(0, nombre_1 - pertes_1)
    survivants_2 = max(0, nombre_2 - pertes_2)

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
    # Résout une confrontation entre deux blocs placés face à face.

    joueur_1 = general_1["joueur"]
    joueur_2 = general_2["joueur"]

    nom_1 = f"{joueur_1} {general_1['nom']}"
    nom_2 = f"{joueur_2} {general_2['nom']}"

    infos_1 = armee[joueur_1][bloc]
    infos_2 = armee[joueur_2][bloc]

    if infos_1["nombre"] == 0 or infos_2["nombre"] == 0:
        return False

    afficher_et_ecrire("\n" + "-" * 60)
    afficher_et_ecrire(f"Confrontation directe : {bloc}")
    afficher_et_ecrire("")

    afficher_et_ecrire(
        f"{nom_1} : {formater_force(infos_1)}"
    )
    afficher_et_ecrire(
        f"{nom_2} : {formater_force(infos_2)}"
    )

    survivants_1, survivants_2 = combat_bloc(
        infos_1,
        infos_2
    )

    afficher_et_ecrire("\nRésultat :")
    afficher_et_ecrire(
        f"{nom_1} : "
        f"{formater_survivants(survivants_1, infos_1['type'])}"
    )
    afficher_et_ecrire(
        f"{nom_2} : "
        f"{formater_survivants(survivants_2, infos_2['type'])}"
    )

    pertes_1 = supprimer_unites(
        infos_1,
        survivants_1
    )

    pertes_2 = supprimer_unites(
        infos_2,
        survivants_2
    )

    afficher_tableau_pertes(
        pertes_1,
        pertes_2,
        nom_1,
        nom_2
    )

    return True

def phase_engagement_initial(general_1, general_2):
    joueur_1 = general_1["joueur"]
    joueur_2 = general_2["joueur"]

    chemin_1 = general_1["chemin"]
    chemin_2 = general_2["chemin"]

    afficher_et_ecrire("\n=== Phase 1 : engagement initial ===")

    armee_depart = {
        joueur_1: lire_blocs_general(chemin_1),
        joueur_2: lire_blocs_general(chemin_2),
    }

    initiative_avant = {
        joueur_1: False,
        joueur_2: False,
    }

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
        return initiative_avant

    afficher_et_ecrire("\nCombats prévus :")

    for bloc in combats_prevus:
        infos_1 = armee_depart[joueur_1][bloc]
        infos_2 = armee_depart[joueur_2][bloc]

        afficher_et_ecrire(
            f"- {bloc} : "
            f"{joueur_1} {general_1['nom']} "
            f"{formater_force(infos_1)} "
            f"VS "
            f"{joueur_2} {general_2['nom']} "
            f"{formater_force(infos_2)}"
        )


    afficher_et_ecrire("\n--- Résolution des engagements ---")

    for bloc in combats_prevus:
        if not chemin_1.exists() or not chemin_2.exists():
            break

        armee = {
            joueur_1: lire_blocs_general(chemin_1),
            joueur_2: lire_blocs_general(chemin_2),
        }

        confrontation_directe(
            armee,
            general_1,
            general_2,
            bloc
        )

        if chemin_1.exists():
            supprimer_general_si_vide(general_1)

        if chemin_2.exists():
            supprimer_general_si_vide(general_2)

    return initiative_avant

def attaque_ciblee(
    armee,
    general_attaquant,
    general_defenseur,
    bloc_attaquant,
    bloc_cible
):
    # Résout une attaque d'initiative contre un bloc ennemi.

    joueur_attaquant = general_attaquant["joueur"]
    joueur_ennemi = general_defenseur["joueur"]

    nom_attaquant = (
        f"{joueur_attaquant} {general_attaquant['nom']}"
    )

    nom_defenseur = (
        f"{joueur_ennemi} {general_defenseur['nom']}"
    )

    infos_attaquant = armee[joueur_attaquant][bloc_attaquant]
    infos_defenseur = armee[joueur_ennemi][bloc_cible]

    afficher_et_ecrire("\n" + "-" * 60)
    afficher_et_ecrire("Attaque d'initiative")
    afficher_et_ecrire("")

    afficher_et_ecrire(
        f"{nom_attaquant} {bloc_attaquant} "
        f"attaque {nom_defenseur} {bloc_cible}"
    )

    afficher_et_ecrire("\nForces engagées :")
    afficher_et_ecrire(
        f"{nom_attaquant} {bloc_attaquant} : "
        f"{formater_force(infos_attaquant)}"
    )
    afficher_et_ecrire(
        f"{nom_defenseur} {bloc_cible} : "
        f"{formater_force(infos_defenseur)}"
    )

    survivants_attaquant, survivants_defenseur = combat_bloc(
        infos_attaquant,
        infos_defenseur
    )

    resultat_attaquant = formater_survivants(
        survivants_attaquant,
        infos_attaquant["type"]
    )

    resultat_defenseur = formater_survivants(
        survivants_defenseur,
        infos_defenseur["type"]
    )

    afficher_et_ecrire("\nRésultat :")
    afficher_et_ecrire(
        f"{nom_attaquant} {bloc_attaquant} : "
        f"{resultat_attaquant}"
    )
    afficher_et_ecrire(
        f"{nom_defenseur} {bloc_cible} : "
        f"{resultat_defenseur}"
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


def ecrire_rapport(texte):
    rapport_path.parent.mkdir(exist_ok=True)

    with open(rapport_path, "a", encoding="utf-8") as rapport:
        rapport.write(texte + "\n")


def afficher_et_ecrire(texte):
    ecrire_rapport(texte)


def preparer_rapport():
    rapport_path.parent.mkdir(exist_ok=True)
    rapport_path.write_text("", encoding="utf-8")





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



preparer_rapport()
reparer_structure()

vainqueur = verifier_victoire()

if vainqueur:
    rapport_court_path.write_text(f"🏆 VICTOIRE DE {vainqueur}\n", encoding="utf-8")

    afficher_et_ecrire(f"🏆 Victoire de {vainqueur} !")
    exit()

lancer_bataille_v15()