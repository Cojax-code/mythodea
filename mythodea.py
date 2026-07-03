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

rapport_path = game_path / "rapport" / "rapport_bataille.txt"

rapport_court_path = game_path / "rapport" / "rapport_court.txt"

unites_connues_path = game_path / "systeme" / "unites_connues.txt"


def reparer_structure():
    for territory in territoires:
        for joueur in joueurs:
            joueur_dir = territory / joueur
            joueur_dir.mkdir(exist_ok=True)

            uid = pwd.getpwnam(joueur).pw_uid
            gid = grp.getgrnam(joueur).gr_gid

            os.chown(joueur_dir, uid, gid)
            os.chmod(joueur_dir, 0o700)

            for bloc in ordre_blocs:
                bloc_dir = joueur_dir / bloc
                bloc_dir.mkdir(exist_ok=True)

                os.chown(bloc_dir, uid, gid)
                os.chmod(bloc_dir, 0o700)


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


preparer_rapport()
reparer_structure()


vainqueur = verifier_victoire()

if vainqueur:
    rapport_court_path.write_text(f"🏆 VICTOIRE DE {vainqueur}\n", encoding="utf-8")

    afficher_et_ecrire(f"🏆 Victoire de {vainqueur} !")
    exit()

lancer_bataille()
