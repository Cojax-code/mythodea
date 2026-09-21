"""Généraux, ordres, unités, identité et permissions."""
from pathlib import Path
import grp
import os
import pwd
import random
import shutil

import config
import etat
import rapports


def choisir_orientation_general():
    chance = random.randint(1, 100)

    if chance == 1:
        return config.orientation_rare

    return random.choice(config.orientations)


def creer_general(chemin_general, nom_general):
    chemin_general.mkdir(exist_ok=True)

    for bloc in config.ordre_blocs:
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


def faire_apparaitre_general_si_possible(joueur):
    # Fait apparaître un seul général dans le home du joueur si possible.
    #
    # Règles :
    # - si le home contient déjà un général : rien n'apparaît
    # - si le joueur a déjà atteint la limite : rien n'apparaît
    # - sinon, le prochain generalX apparaît dans /home/joueur/

    if home_contient_general(joueur):
        rapports.afficher_et_ecrire(
            f"{joueur} a déjà un général dans son home. Aucun nouveau général."
        )
        return

    dernier_numero = etat.lire_compteur_general(joueur)

    if dernier_numero >= config.max_generaux_par_joueur:
        rapports.afficher_et_ecrire(
            f"{joueur} a déjà atteint la limite de {config.max_generaux_par_joueur} généraux."
        )
        return

    nouveau_numero = dernier_numero + 1
    nom_general = f"general{nouveau_numero}"
    chemin_general = Path(f"/home/{joueur}") / nom_general

    creer_general(chemin_general, nom_general)
    donner_permissions_general(chemin_general, joueur)
    etat.sauvegarder_compteur_general(joueur, nouveau_numero)

    etat.enregistrer_position_nouveau_general(
    joueur,
    nom_general
)

    rapports.afficher_et_ecrire(
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
    for bloc in config.ordre_blocs:
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
            rapports.afficher_et_ecrire(
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
            rapports.afficher_et_ecrire(
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
        if identifiant not in config.legende_ordres:
            rapports.afficher_et_ecrire(
                f"Ordre ignoré pour "
                f"{chemin_general.name} : "
                f"{ligne} "
                f"[ordre inconnu]"
            )

            continue

        fiche_ordre = config.legende_ordres[
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

    for joueur in config.joueurs:
        resultat[joueur] = {}

        for emplacement in config.emplacements:
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
                rapports.afficher_et_ecrire(
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
    for bloc in config.ordre_blocs:
        blocs_general[bloc] = {
            "type": "vide",
            "nombre": 0,
            "unites": [],
        }

    for bloc in config.ordre_blocs:
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

            rapports.afficher_et_ecrire(f"Unité invalide supprimée : {unite.name}")

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
                rapports.afficher_et_ecrire(
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
                    rapports.afficher_et_ecrire(
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

    for bloc in config.ordre_blocs:
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

    for emplacement in config.emplacements:
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
    chemin_repli = config.repli_path / joueur / nom_general

    if chemin_repli.is_dir():
        return "repli", chemin_repli

    # 3. Territoires
    for territory in config.territoires:
        for emplacement in config.emplacements:
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
        config.repli_path
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

    for territory in config.territoires:
        for emplacement in config.emplacements:

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

    for emplacement in config.emplacements:
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

    for emplacement in config.emplacements:
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

    rapports.afficher_et_ecrire(
        f"{general['joueur']} {general['nom']} "
        f"n'a plus d'unités. Général supprimé."
    )

    shutil.rmtree(chemin_general)

    # Retirer l'identité dès la destruction, avant le prochain tour.
    # Le compteur reste inchangé : ce numéro ne doit jamais être réutilisé.
    positions = etat.charger_positions_generaux()
    positions.pop(f"{general['joueur']}:{general['nom']}", None)
    etat.sauvegarder_positions_generaux(positions)

    return True


def verifier_limite_unites_general(chemin_general):
    # Vérifie qu'un général ne dépasse pas la limite d'unités autorisée.
    #
    # Règle actuelle :
    # un général peut avoir maximum 20 unités au total,
    # réparties librement entre avant, droite, gauche, arriere.

    blocs_general = lire_blocs_general(chemin_general)
    total = total_unites_general(blocs_general)

    if total <= config.max_unites_par_general:
        return

    surplus = total - config.max_unites_par_general

    rapports.afficher_et_ecrire(
        f"{chemin_general.name} dépasse la limite : "
        f"{total}/{config.max_unites_par_general} unités. "
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
            rapports.afficher_et_ecrire(
                f"Unité supprimée pour limite de général : {unite.name}"
            )
            surplus -= 1


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


def total_general_depuis_chemin(chemin_general):
    # Retourne le nombre d'unités encore présentes.
    # Un général supprimé vaut automatiquement zéro.

    if not chemin_general.exists():
        return 0

    return total_unites_general(
        lire_blocs_general(chemin_general)
    )
