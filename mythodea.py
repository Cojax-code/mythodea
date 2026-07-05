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

carte_territoires = ["base1", "terrain1", "terrain2", "terrain3", "base2"]

ordre_blocs = ["avant", "droite", "gauche", "arriere"]
joueurs = ["j1", "j2"]

emplacements = ["1", "2", "3","4"]
generaux = ["general1", "general2", "general3", "general4", "general5"]
max_unites_par_general = 20
max_generaux_par_joueur = 5

orientations = ["stratege", "combattant"]
orientation_rare = "hybride"


rapport_path = game_path / "rapport" / "rapport_bataille.txt"

rapport_court_path = game_path / "rapport" / "rapport_court.txt"

unites_connues_path = game_path / "systeme" / "unites_connues.txt"




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


def verifier_doublons_unites():
    noms_vus = {}

    for territory in territoires:
        armee = lire_blocs(territory)

        for joueur in joueurs:
            for bloc in ordre_blocs:
                for unite in armee[joueur][bloc]["unites"]:
                    identifiant = identifiant_unite(joueur, unite)

                    if identifiant not in noms_vus:
                        noms_vus[identifiant] = []

                    noms_vus[identifiant].append(unite)

    for identifiant, unites in noms_vus.items():
        if len(unites) > 1:
            afficher_et_ecrire(
                f"Doublon d'unité détecté : {identifiant}. Toutes les copies sont supprimées."
            )

            for unite in unites:
                shutil.rmtree(unite)


def lire_blocs(territory):
    armee = {"j1": {}, "j2": {}}

    for joueur in armee:
        for bloc in ordre_blocs:
            armee[joueur][bloc] = {"type": "vide", "nombre": 0, "unites": []}

    for joueur_dir in territory.iterdir():
        if joueur_dir.is_dir():
            joueur = joueur_dir.name

            if joueur not in armee:
                continue

            for bloc_dir in joueur_dir.iterdir():
                if bloc_dir.is_dir():
                    bloc = bloc_dir.name

                    if bloc not in ordre_blocs:
                        shutil.rmtree(bloc_dir)
                        afficher_et_ecrire(
                            f"Dossier invalide supprimé : {joueur}/{bloc}"
                        )
                        continue

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

                    for unite in a_supprimer:
                        shutil.rmtree(unite)
                        afficher_et_ecrire(f"Unité invalide supprimée : {unite.name}")

                    if len(type_trouves) > 0:
                        armee[joueur][bloc]["type"] = type_trouves[0]
                        armee[joueur][bloc]["nombre"] = len(type_trouves)
                        armee[joueur][bloc]["unites"] = unites_trouvees

    return armee


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


def combat_bloc(infos_j1, infos_j2):
    type_j1 = infos_j1["type"]
    type_j2 = infos_j2["type"]

    nombre_j1 = infos_j1["nombre"]
    nombre_j2 = infos_j2["nombre"]

    valeur_j1 = multiplicateur(type_j1, type_j2)
    valeur_j2 = multiplicateur(type_j2, type_j1)

    degats_j1 = nombre_j1 * valeur_j1
    degats_j2 = nombre_j2 * valeur_j2

    pertes_j1 = degats_j2 // valeur_j1
    pertes_j2 = degats_j1 // valeur_j2

    survivants_j1 = max(0, nombre_j1 - pertes_j1)
    survivants_j2 = max(0, nombre_j2 - pertes_j2)

    if nombre_j1 == 0:
        gauche = "vide"
    else:
        gauche = f"{nombre_j1} {type_j1}"

    if nombre_j2 == 0:
        droite = "vide"
    else:
        droite = f"{nombre_j2} {type_j2}"

    afficher_et_ecrire(f"{gauche} VS {droite}")

    return survivants_j1, survivants_j2


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


def total_unites_joueur(armee, joueur):
    total = 0

    for bloc in ordre_blocs:
        total += armee[joueur][bloc]["nombre"]

    return total


def controle_territoire(armee):
    total_j1 = total_unites_joueur(armee, "j1")
    total_j2 = total_unites_joueur(armee, "j2")

    if total_j1 > 0 and total_j2 == 0:
        return "j1"

    elif total_j2 > 0 and total_j1 == 0:
        return "j2"

    elif total_j1 == 0 and total_j2 == 0:
        return "neutre"

    else:
        return "conteste"


def identifiant_unite(joueur, unite):
    return f"{joueur}:{unite.name}"


def charger_unites_connues():
    if not unites_connues_path.exists():
        return set()

    lignes = unites_connues_path.read_text(encoding="utf-8").splitlines()
    return set(lignes)


def sauvegarder_unites_connues(unites_connues):
    unites_connues_path.parent.mkdir(exist_ok=True)
    texte = "\n".join(sorted(unites_connues))
    unites_connues_path.write_text(texte, encoding="utf-8")


def verifier_renforts():
    controle = controle_des_territoires()
    unites_connues = charger_unites_connues()
    nouvelles_unites_connues = set()

    for territory in territoires:
        armee = lire_blocs(territory)

        for joueur in joueurs:
            ravitaille = territoire_relie(joueur, controle, territory.name)

            for bloc in ordre_blocs:
                infos = armee[joueur][bloc]

                for unite in infos["unites"]:
                    identifiant = identifiant_unite(joueur, unite)

                    if identifiant in unites_connues:
                        nouvelles_unites_connues.add(identifiant)
                        continue

                    if ravitaille:
                        afficher_et_ecrire(
                            f"Nouvelle unité acceptée : {joueur} {unite.name} sur {territory.name}"
                        )
                        nouvelles_unites_connues.add(identifiant)
                    else:
                        shutil.rmtree(unite)
                        afficher_et_ecrire(
                            f"Renfort illégal supprimé : {joueur} {unite.name} sur {territory.name} non ravitaillé"
                        )

    sauvegarder_unites_connues(nouvelles_unites_connues)


def territoire_relie(joueur, controle, territoire):
    if joueur == "j1":
        depart = "base1"
    else:
        depart = "base2"

    position_depart = carte_territoires.index(depart)
    position_territoire = carte_territoires.index(territoire)

    if joueur == "j1":
        chemin = carte_territoires[position_depart : position_territoire + 1]
    else:
        chemin = carte_territoires[position_territoire : position_depart + 1]

    for nom in chemin:
        if nom == depart:
            continue

        if controle[nom] != joueur:
            return False

    return True


def afficher_ravitaillement():
    controle = controle_des_territoires()

    afficher_et_ecrire("\n=== Ravitaillement ===")

    for joueur in joueurs:
        afficher_et_ecrire(f"\n{joueur} :")

        for nom_territoire in carte_territoires:
            if territoire_relie(joueur, controle, nom_territoire):
                afficher_et_ecrire(f"{nom_territoire} : ravitaillé")
            else:
                afficher_et_ecrire(f"{nom_territoire} : coupé")


def controle_des_territoires():
    resultat = {}

    for territory in territoires:
        armee = lire_blocs(territory)
        resultat[territory.name] = controle_territoire(armee)

    return resultat


def supprimer_unites(infos, survivants):
    nombre_actuel = infos["nombre"]
    pertes = nombre_actuel - survivants

    if pertes <= 0:
        return

    unites_a_supprimer = random.sample(infos["unites"], pertes)

    for unite in unites_a_supprimer:
        shutil.rmtree(unite)
        afficher_et_ecrire(f"Unité supprimée : {unite.name}")


def attaque_ciblee(armee, joueur_attaquant, bloc_attaquant, bloc_cible):
    joueur_ennemi = ennemi_de(joueur_attaquant)

    infos_attaquant = armee[joueur_attaquant][bloc_attaquant]
    infos_defenseur = armee[joueur_ennemi][bloc_cible]

    afficher_et_ecrire("\nAttaque ciblée :")
    afficher_et_ecrire(
        f"{joueur_attaquant} {bloc_attaquant} attaque {joueur_ennemi} {bloc_cible}"
    )

    survivants_attaquant, survivants_defenseur = combat_bloc(
        infos_attaquant, infos_defenseur
    )

    supprimer_unites(infos_attaquant, survivants_attaquant)
    supprimer_unites(infos_defenseur, survivants_defenseur)


def choisir_flanc_attaquant(armee, joueur):
    flancs = ["droite", "gauche"]

    droite_nombre = armee[joueur]["droite"]["nombre"]
    gauche_nombre = armee[joueur]["gauche"]["nombre"]

    if droite_nombre > gauche_nombre:
        return "droite"

    elif gauche_nombre > droite_nombre:
        return "gauche"

    elif droite_nombre > 0:
        return random.choice(flancs)

    else:
        return None

def ordre_attaque_manche_2(armee, joueur, initiative_avant):
    ordre = []
    avant_deja_utilise = False

    # 1. Avant-garde si bonus d'initiative
    if initiative_avant[joueur] and armee[joueur]["avant"]["nombre"] > 0:
        ordre.append("avant")
        avant_deja_utilise = True

    # 2. Arrière-garde
    if armee[joueur]["arriere"]["nombre"] > 0:
        ordre.append("arriere")

    # 3. Flanc le plus nombreux puis flanc le moins nombreux
    flancs = []

    for flanc in ["droite", "gauche"]:
        nombre = armee[joueur][flanc]["nombre"]

        if nombre > 0:
            flancs.append((flanc, nombre))

    if len(flancs) == 2 and flancs[0][1] == flancs[1][1]:
        random.shuffle(flancs)
    else:
        flancs.sort(key=lambda element: element[1], reverse=True)

    for flanc, nombre in flancs:
        ordre.append(flanc)

    # 4. Avant normal, seulement si pas déjà utilisé avec le bonus
    if not avant_deja_utilise and armee[joueur]["avant"]["nombre"] > 0:
        ordre.append("avant")

    return ordre

def choisir_cible(armee, joueur_attaquant, type_attaquant):
    joueur_ennemi = ennemi_de(joueur_attaquant)

    cible = trouver_cible_facile(armee, joueur_attaquant, type_attaquant)

    if cible is None:
        cible = trouver_cible_faible(armee, joueur_ennemi)

    return cible


def manche_2(territory, initiative_avant):
    afficher_et_ecrire("\n=== Manche 2 ===")

    armee = lire_blocs(territory)

    tour = 0

    while controle_territoire(armee) == "conteste" and tour < 5:
        tour += 1
        afficher_et_ecrire(f"\n--- Manche 2 / Tour {tour} ---")

        attaque_effectuee = False

        for joueur in ["j1", "j2"]:
            armee = lire_blocs(territory)

            if controle_territoire(armee) != "conteste":
                break

            ordre_attaques = ordre_attaque_manche_2(armee, joueur, initiative_avant)

            if len(ordre_attaques) == 0:
                continue

            afficher_et_ecrire(f"\nOrdre d'attaque de {joueur} : {', '.join(ordre_attaques)}")

            for bloc_attaquant in ordre_attaques:
                armee = lire_blocs(territory)

                if controle_territoire(armee) != "conteste":
                    break

                if armee[joueur][bloc_attaquant]["nombre"] <= 0:
                    continue

                type_attaquant = armee[joueur][bloc_attaquant]["type"]

                cible = choisir_cible(armee, joueur, type_attaquant)

                if cible is None:
                    continue

                attaque_ciblee(armee, joueur, bloc_attaquant, cible)
                attaque_effectuee = True

                armee = lire_blocs(territory)

        armee = lire_blocs(territory)

        if not attaque_effectuee and controle_territoire(armee) == "conteste":
            afficher_et_ecrire(
                "Aucune attaque possible. La bataille reste bloquée."
            )
            break

    armee = lire_blocs(territory)

    if tour >= 5 and controle_territoire(armee) == "conteste":
        afficher_et_ecrire(
            "Les forces restantes sont incapables de prendre l'avantage. "
            "La bataille s'achève dans un bain de sang. "
            "Le territoire reste contesté."
        )

def ecrire_rapport(texte):
    rapport_path.parent.mkdir(exist_ok=True)

    with open(rapport_path, "a", encoding="utf-8") as rapport:
        rapport.write(texte + "\n")


def afficher_et_ecrire(texte):
    ecrire_rapport(texte)


def preparer_rapport():
    rapport_path.parent.mkdir(exist_ok=True)
    rapport_path.write_text("", encoding="utf-8")


def lignes_blocs(armee, joueur):
    lignes = []

    for bloc in ordre_blocs:
        infos = armee[joueur][bloc]

        if infos["nombre"] > 0:
            lignes.append(f"{bloc} : {infos['nombre']} {infos['type']}")

    if len(lignes) == 0:
        lignes.append("aucune unité")

    return lignes


def territoire_a_combat(armee):
    total_j1 = total_unites_joueur(armee, "j1")
    total_j2 = total_unites_joueur(armee, "j2")

    return total_j1 > 0 and total_j2 > 0


def ecrire_rapport_court(territoires_combattus):
    lignes = []
    lignes.append("=== RAPPORT COURT ===")

    for territory in territoires:
        armee = lire_blocs(territory)
        controle = controle_territoire(armee)

        lignes.append(f"\n{territory.name}")
        lignes.append(f"Gagnant / contrôle : {controle}")

        if territory.name not in territoires_combattus:
            lignes.append("Aucun combat ce tour.")
            lignes.append("Unités non révélées.")
            continue

        lignes.append("\nj1 :")
        lignes.extend(lignes_blocs(armee, "j1"))

        lignes.append("\nj2 :")
        lignes.extend(lignes_blocs(armee, "j2"))

    rapport_court_path.parent.mkdir(exist_ok=True)
    rapport_court_path.write_text("\n".join(lignes), encoding="utf-8")


def lancer_bataille():
    territoires_combattus = set()

    verifier_renforts()
    verifier_doublons_unites()

    for territory in territoires:
        afficher_et_ecrire(f"\nTerritoire : {territory.name}")

        armee = lire_blocs(territory)

        combat_ce_tour = territoire_a_combat(armee)

        if combat_ce_tour:
            territoires_combattus.add(territory.name)

        initiative_avant = {
            "j1": False,
            "j2": False,
        }

        if armee["j1"]["avant"]["nombre"] > 0 and armee["j2"]["avant"]["nombre"] == 0:
            initiative_avant["j1"] = True

        if armee["j2"]["avant"]["nombre"] > 0 and armee["j1"]["avant"]["nombre"] == 0:
            initiative_avant["j2"] = True

        if combat_ce_tour:
            for joueur, blocs in armee.items():
                afficher_et_ecrire(f"\nJoueur : {joueur}")

                for nom_bloc, infos in blocs.items():

                    if infos["nombre"] == 0:
                        afficher_et_ecrire(f"{nom_bloc} : vide")
                    else:
                        afficher_et_ecrire(
                            f"{nom_bloc} : {infos['nombre']} {infos['type']}"
                        )
        else:
            afficher_et_ecrire("Aucun combat ce tour.")
            afficher_et_ecrire("Unités non révélées.")

        afficher_et_ecrire("\nResultat des combats :")

        for bloc in ordre_blocs:
            survivants_j1, survivants_j2 = combat_bloc(
                armee["j1"][bloc], armee["j2"][bloc]
            )

            afficher_et_ecrire(f"{bloc} :")
            afficher_et_ecrire(f" j1 survivants : {survivants_j1}")
            afficher_et_ecrire(f" j2 survivants : {survivants_j2}")

            supprimer_unites(armee["j1"][bloc], survivants_j1)
            supprimer_unites(armee["j2"][bloc], survivants_j2)

        armee = lire_blocs(territory)

        controle = controle_territoire(armee)

        afficher_et_ecrire(f"\nControle du territoire : {controle}")

        if controle == "conteste":
            manche_2(territory, initiative_avant)

            armee = lire_blocs(territory)
            controle = controle_territoire(armee)

            afficher_et_ecrire(f"\nControle final du territoire : {controle}")

    afficher_ravitaillement()
    ecrire_rapport_court(territoires_combattus)


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


def test_lecture_generaux():
    # Fonction temporaire pour vérifier que Python lit correctement
    # les généraux, les emplacements et les unités.
    #
    # Elle ne modifie pas le jeu.
    # Elle écrit seulement dans le rapport.

    afficher_et_ecrire("\n=== TEST LECTURE GENERAUX V1.5 ===")

    for territory in territoires:
        afficher_et_ecrire(f"\nTerritoire : {territory.name}")

        generaux_territoire = lire_generaux_territoire(territory)
        controle = controle_territoire_generaux(generaux_territoire)

        afficher_et_ecrire(f"Controle version generaux : {controle}")

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


def lancer_bataille_v15():
    # Première boucle de résolution V1.5.
    #
    # Pour l'instant, elle ne fait pas encore les combats.
    # Elle vérifie seulement :
    # - les généraux présents
    # - les unités présentes
    # - le contrôle du territoire
    # - si un combat doit être lancé

    afficher_et_ecrire("\n=== RESOLUTION MYTHODEA V1.5 ===")

    for territory in territoires:
        afficher_et_ecrire(f"\nTerritoire : {territory.name}")

        generaux_territoire = lire_generaux_territoire(territory)
        controle = controle_territoire_generaux(generaux_territoire)

        afficher_et_ecrire(f"Controle actuel : {controle}")

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

        if controle == "conteste":
            afficher_et_ecrire(
                "Combat détecté sur ce territoire. "
                "La résolution V1.5 du combat n'est pas encore codée."
            )

preparer_rapport()
reparer_structure()

vainqueur = verifier_victoire()

if vainqueur:
    rapport_court_path.write_text(f"🏆 VICTOIRE DE {vainqueur}\n", encoding="utf-8")

    afficher_et_ecrire(f"🏆 Victoire de {vainqueur} !")
    exit()

lancer_bataille_v15()
exit()

lancer_bataille()