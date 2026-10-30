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
import progression


aleatoire_caracteristiques = random.Random()


def choisir_orientation_general():
    chance = random.randint(1, 100)

    if chance == 1:
        return config.orientation_rare

    return random.choice(config.orientations)


def creer_general(chemin_general, nom_general):
    nouveau = not chemin_general.exists()
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

    if nouveau:
        caracteristiques = progression.nouvelles_caracteristiques(aleatoire_caracteristiques)
        # Les racines des acteurs existent dans les homes et dans les générations.
        joueur = next((p.name for p in chemin_general.parents
                       if p.name in (*config.joueurs, 'bot')), None)
        if joueur is not None:
            caracteristiques = progression.enregistrer_creation(joueur, nom_general, caracteristiques)
        progression.publier_fiche(chemin_general, caracteristiques)

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


def home_contient_general(joueur, configuration=None):
    # Vérifie si le home du joueur contient déjà un général.
    #
    # Règle V1.5 :
    # si un général est déjà dans le home, aucun nouveau général n'apparaît.

    home_joueur = (config.home_generation(joueur)
                   or (configuration or {}).get('homes', {}).get(joueur)
                   or Path(f"/home/{joueur}"))

    if not home_joueur.exists():
        return False

    for element in home_joueur.iterdir():
        if element.is_dir() and element.name.startswith("general"):
            return True

    return False


def faire_apparaitre_general_si_possible(joueur, configuration=None):
    # Fait apparaître un seul général dans le home du joueur si possible.
    #
    # Règles :
    # - si le home contient déjà un général : rien n'apparaît
    # - si le joueur a déjà atteint la limite : rien n'apparaît
    # - sinon, le prochain generalX apparaît dans /home/joueur/

    if home_contient_general(joueur, configuration):
        rapports.afficher_et_ecrire(
            f"{joueur} a déjà un général dans son home. Aucun nouveau général."
        )
        return

    dernier_numero = etat.lire_compteur_general(joueur)
    survie = configuration is not None and configuration['mode'] == 'survie'
    creations_normales = etat.initialiser_quota_normal(joueur) if survie else dernier_numero
    if creations_normales >= config.max_generaux_par_joueur:
        rapports.afficher_et_ecrire(
            f"{joueur} a déjà atteint la limite de {config.max_generaux_par_joueur} généraux."
        )
        return

    nouveau_numero = dernier_numero + 1
    nom_general = f"general{nouveau_numero}"
    home = (config.home_generation(joueur)
            or (configuration or {}).get('homes', {}).get(joueur)
            or Path(f"/home/{joueur}"))
    chemin_general = home / nom_general

    creer_general(chemin_general, nom_general)
    proprietaire = joueur if configuration is None else configuration['acteurs'][joueur]['proprietaire_linux']
    donner_permissions_general(chemin_general, proprietaire)
    etat.sauvegarder_compteur_general(joueur, nouveau_numero)
    if survie:
        etat.sauvegarder_quota_normal(joueur, creations_normales + 1)

    etat.enregistrer_position_nouveau_general(
    joueur,
    nom_general
)

    rapports.afficher_et_ecrire(
        f"Nouveau général apparu pour {joueur} : {nom_general}"
    )
    return f'{joueur}:{nom_general}'


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


def assurer_ordre_surnombre(chemin_general, joueur, position, configuration):
    """Crée seulement le fichier manquant, selon la position au moment du scan."""
    if configuration["mode"] != "survie" or joueur not in configuration["joueurs"]:
        return None
    chemin = chemin_general / "ordre_surnombre.txt"
    if not chemin.exists():
        valeur = 2 if position in configuration["villages"] else 1
        chemin.write_text(f"{valeur}\n", encoding="utf-8")
        acteur = configuration["acteurs"][joueur]
        os.chown(chemin, pwd.getpwnam(acteur["proprietaire_linux"]).pw_uid,
                 grp.getgrnam(acteur["groupe_linux"]).gr_gid)
        os.chmod(chemin, 0o600)
    return chemin


def lire_ordre_surnombre(general, position, configuration):
    chemin = assurer_ordre_surnombre(
        general["chemin"], general["joueur"], position, configuration)
    if chemin is None:
        raise ValueError("L'ordre de surnombre appartient aux joueurs du mode Survie.")
    texte = chemin.read_text(encoding="utf-8").strip()
    if texte not in ("1", "2"):
        valeur = 2 if position in configuration["villages"] else 1
        rapports.afficher_et_ecrire(
            f"Ordre de surnombre invalide : {chemin}. Défaut du lieu utilisé : {valeur}."
        )
        return valeur
    return int(texte)


def scanner_ordres_surnombre(configuration):
    """Complète les généraux joueurs officiels, y compris home, réserve et repli."""
    if configuration["mode"] != "survie":
        return
    for identifiant in etat.charger_positions_generaux():
        joueur, nom = identifiant.split(":", 1)
        if joueur not in configuration["joueurs"] or numero_general_depuis_nom(nom) is None:
            continue
        position, chemin = trouver_position_general(joueur, nom, configuration)
        if chemin is not None:
            assurer_ordre_surnombre(chemin, joueur, position, configuration)


def lire_declaration_qg(chemin_general):
    """Lit le choix du joueur sans créer de fichier ni réparer de bloc.

    Même frontière de sécurité que ordre.txt : fichier ordinaire, borné,
    sans lien, dans le général capturé par le moteur.
    """
    import stat
    from cycle_linux import sans_liens
    chemin = chemin_general / 'qg.txt'
    try:
        sans_liens(chemin)
        infos = chemin.lstat()
        if not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1:
            return None
        with chemin.open('rb') as fichier:
            contenu = fichier.read(65537)
        if len(contenu) > 65536:
            return None
        lignes = [ligne.strip() for ligne in contenu.decode('utf-8').splitlines()
                  if ligne.strip()]
        if not lignes:
            return None
        # Premier champ : bloc physique du QG ; lignes suivantes : globaux.
        bloc = lignes[0]
        if bloc not in config.ordre_blocs:
            return None
        composition = lire_composition_general(chemin_general)
        return bloc if sum(composition[bloc].values()) > 0 else None
    except (OSError, ValueError, RuntimeError):
        return None


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

    import stat
    from cycle_linux import sans_liens
    try:
        sans_liens(ordre_path)
        infos = ordre_path.lstat()
        if not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1:
            raise ValueError('Fichier non ordinaire.')
        with ordre_path.open('rb') as fichier:
            contenu = fichier.read(65537)
        if len(contenu) > 65536:
            raise ValueError('Fichier trop volumineux.')
        lignes = contenu.decode('utf-8').splitlines()
    except (OSError, ValueError, RuntimeError):
        rapports.afficher_et_ecrire(f'Ordres ignorés pour {chemin_general.name} : [fichier invalide]')
        return ordres

    for ligne in lignes:
        ligne = ligne.strip()

        if ligne == "":
            continue

        morceaux = ligne.split("-")

        # Gros_poisson désigne les positions du bénéficiaire et du prêteur.
        if len(morceaux) not in [2, 3, 4]:
            rapports.afficher_et_ecrire(
                f"Ordre ignoré pour "
                f"{chemin_general.name} : "
                f"[format invalide]"
            )

            continue

        # Dernière charge utilise un flanc G/D, pas un emplacement numérique.
        flanc_derniere_charge = (
            len(morceaux) == 3 and morceaux[:2] == ['2', '8']
            and morceaux[2] in ('G', 'D', 'g', 'd'))
        if not flanc_derniere_charge and not all(
            morceau.isascii() and morceau.isdecimal()
            for morceau in morceaux
        ):
            rapports.afficher_et_ecrire(
                f"Ordre ignoré pour "
                f"{chemin_general.name} : "
                f"[valeur non numérique]"
            )

            continue

        try:
            type_ordre = int(morceaux[0])
            numero_ordre = int(morceaux[1])
            if len(morceaux) == 4:
                if (type_ordre, numero_ordre) != (2, 6):
                    rapports.afficher_et_ecrire(f'Ordre ignoré pour {chemin_general.name} : [format invalide]')
                    continue
                specification = (int(morceaux[2]), int(morceaux[3]))
            else:
                specification = (morceaux[2].upper() if flanc_derniere_charge
                                 else int(morceaux[2]) if len(morceaux) == 3 else None)
        except ValueError:
            rapports.afficher_et_ecrire(f'Ordre ignoré pour {chemin_general.name} : [nombre invalide]')
            continue

        identifiant = (
            f"{type_ordre}-"
            f"{numero_ordre}"
        )

        # L'ordre doit exister dans la légende.
        if identifiant not in config.legende_ordres:
            rapports.afficher_et_ecrire(
                f"Ordre ignoré pour "
                f"{chemin_general.name} : "
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



def lire_ordres_qg(chemin_general):
    """Ordres émis par le général en chef dans son propre qg.txt.

    Première ligne : bloc du QG ; suivantes : jetons globaux, avec troisième
    plage éventuelle pour désigner un emplacement.
    """
    if lire_declaration_qg(chemin_general) is None:
        return []
    chemin = chemin_general / 'qg.txt'
    try:
        lignes = chemin.read_text(encoding='utf-8').splitlines()[1:]
    except (OSError, UnicodeError):
        return []
    import catalogues
    catalogue = {fiche['jeton']: (identifiant, fiche)
                 for identifiant, fiche in catalogues.ORDRES.items()
                 }
    resultat = []
    for ligne in lignes:
        morceau = ligne.strip().split('-')
        if len(morceau) not in (2, 3, 4):
            continue
        flanc = (morceau[:2] == ['2', '8'] and len(morceau) == 3
                 and morceau[2] in ('G', 'D', 'g', 'd'))
        if not flanc and not all(
                valeur.isascii() and valeur.isdecimal() for valeur in morceau):
            continue
        jeton = '-'.join(morceau[:2])
        if jeton not in catalogue:
            continue
        identifiant, fiche = catalogue[jeton]
        if len(morceau) == 4:
            if identifiant != 1017:
                continue
            specification = (int(morceau[2]), int(morceau[3]))
        else:
            specification = (morceau[2].upper() if flanc else
                             int(morceau[2]) if len(morceau) == 3 else None)
        if identifiant == 1017:
            if (not isinstance(specification, tuple)
                    or any(position <= 0 for position in specification)):
                continue
        elif identifiant == 1025:
            if specification is None or not 1 <= specification <= 20:
                continue
        elif identifiant == 1026:
            if specification not in ('G', 'D'):
                continue
        elif specification is not None:
            continue
        resultat.append(dict(identifiant=jeton, texte=ligne.strip(),
                            type=int(morceau[0]), numero=int(morceau[1]),
                            specification=specification, nom=fiche['nom'],
                            categorie=fiche['categorie']))
    return resultat



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

    if general.get('chemin'):
        import catalogues
        ordre_id = next((i for i, o in catalogues.ORDRES.items()
                         if o['jeton'] == identifiant_ordre), None)
        if not progression.ordre_autorise(progression.caracteristiques_general(general), ordre_id):
            return False

    for ordre in general.get("ordres", []):
        if (
            ordre["identifiant"]
            == identifiant_ordre
        ):
            return True

    return False


def zones_generaux_territoire(territory, joueur, configuration=None):
    """Décrit les zones militaires, sans lire ni modifier le disque.

    La réserve et la garnison ont la même position logique. Seules les zones
    actives participent aux combats. Les renforts numérotés sont aussi audités.
    """
    if configuration is None:
        configuration = config.configuration_mode("classique")
    joueur_dir = territory / joueur
    village = (territory.name in configuration["villages"]
               and joueur in configuration["joueurs"])
    garnison = joueur_dir / "garnison" if village else joueur_dir
    zones = [
        {"position": territory.name, "chemin": garnison / emplacement,
         "emplacement": emplacement}
        for emplacement in configuration["emplacements"]
    ]
    if village:
        zones.append({"position": territory.name, "chemin": joueur_dir / "reserve"})
        zones.extend({'position': territory.name, 'chemin': joueur_dir / 'hopital' / place,
                      'emplacement': f'hopital/{place}', 'batiment': 'hopital'}
                     for place in configuration['emplacements_hopital'])
        for batiment, places in (('ecole_officiers', configuration['emplacements_ecole']),
                                 ('forge', ('1',))):
            zones.extend({'position': territory.name, 'chemin': territory / batiment / place / joueur,
                          'emplacement': f'{batiment}/{place}', 'batiment': batiment,
                          'commun': True}
                         for place in places)
        if configuration['mode'] == 'survie':
            zones.append({'position': territory.name,
                          'chemin': joueur_dir / 'hopital/morgue/generaux', 'morgue': True})
            zones.append({'position': territory.name, 'chemin': joueur_dir / 'crypte/recompense',
                          'crypte': True})
    if configuration["mode"] == "survie" and joueur in configuration["joueurs"] and not village:
        if territory.name == 'est_1':
            zones.append({'position': territory.name,
                          'chemin': territory / 'crypte_des_plaines/1' / joueur,
                          'emplacement': 'crypte_des_plaines/1', 'batiment': 'crypte_des_plaines',
                          'commun': True})
        zones.extend(
            {"position": territory.name, "chemin": joueur_dir / "renforts" / place,
             "emplacement": place}
            for place in configuration["positions_renforts_allies"]
        )
    if configuration["mode"] == "survie" and joueur == "bot":
        zones.append({"position": territory.name, "chemin": joueur_dir / "renforts"})
    return zones


def lire_renforts_bot(territoire):
    """Queue physique des renforts dans leur ordre d'arrivée, sans mutation."""
    dossier = territoire / "bot" / "renforts"
    if not dossier.exists():
        return []
    presents = {chemin.name: chemin for chemin in dossier.iterdir()
                if chemin.is_dir() and numero_general_depuis_nom(chemin.name) is not None}
    ordre = dossier / "ordre_arrivee.txt"
    noms = ordre.read_text(encoding="utf-8").splitlines() if ordre.exists() else []
    resultat = []
    for nom in noms:
        if nom in presents:
            resultat.append(presents.pop(nom))
    # Compatibilité avec les forces préparées avant l'enregistrement de la queue.
    resultat.extend(sorted(presents.values(), key=lambda p: numero_general_depuis_nom(p.name)))
    return resultat


def sauvegarder_ordre_renforts_bot(territoire, chemins, configuration):
    """Un nom canonique par ligne ; le fichier reste privé au compte du bot."""
    ordre = territoire / "bot" / "renforts" / "ordre_arrivee.txt"
    ordre.write_text("".join(f"{chemin.name}\n" for chemin in chemins), encoding="utf-8")
    acteur = configuration["acteurs"]["bot"]
    os.chown(ordre, pwd.getpwnam(acteur["proprietaire_linux"]).pw_uid,
             grp.getgrnam(acteur["groupe_linux"]).gr_gid)
    os.chmod(ordre, 0o600)


def remonter_renforts_bot(territoire, configuration=None):
    """Remplit les places libres après un affrontement, sans lancer de combat.

    Les survivants actifs gardent leur place. Les premiers renforts vivants
    occupent les trous dans l'ordre 1 à 4. Aucun déplacement territorial.
    """
    if configuration is None or configuration["mode"] != "survie":
        return []
    if "bot" not in configuration["acteurs"]:
        return []
    renforts = lire_renforts_bot(territoire)
    if not renforts:
        return []
    vivants = []
    for chemin in renforts:
        general = {"chemin": chemin, "nom": chemin.name, "joueur": "bot",
                   "fiche": lire_fiche_general(chemin)}
        if not supprimer_general_si_vide(general):
            vivants.append(chemin)
    promus = []
    for zone in zones_generaux_territoire(territoire, "bot", configuration):
        if "emplacement" not in zone or not vivants:
            continue
        zone["chemin"].mkdir(mode=0o700, exist_ok=True)
        if any(zone["chemin"].iterdir()):
            continue
        chemin = vivants.pop(0)
        destination = zone["chemin"] / chemin.name
        chemin.rename(destination)
        promus.append(destination)
    sauvegarder_ordre_renforts_bot(territoire, vivants, configuration)
    return promus


def zones_generaux(joueur, configuration=None):
    """Liste commune pour recherche, identité, propriétaires et duplication."""
    if configuration is None:
        configuration = config.configuration_mode("classique")
    zones = [
        {"position": "home", "chemin": (config.home_generation(joueur)
            or configuration.get('homes', {}).get(joueur) or Path(f"/home/{joueur}"))},
        {"position": "repli", "chemin": configuration["repli_path"] / joueur},
    ]
    for territory in configuration["territoires"]:
        zones.extend(zones_generaux_territoire(territory, joueur, configuration))
    return zones


def lire_generaux_territoire(territory, configuration=None):
    # Lit les généraux présents sur un territoire.
    #
    # Structure attendue :
    # territoire/joueur/emplacement/generalX/
    #
    # Exemple :
    # /game/terrain1/j1/1/general1
    #
    # Cette fonction ne sanctionne rien et ne déplace rien.
    # Les anomalies sont traitées auparavant par les
    # fonctions de sécurisation des mouvements.

    if configuration is None:
        configuration = config.configuration_mode("classique")
    resultat = {}

    for joueur in configuration["acteurs"]:
        resultat[joueur] = {}

        for zone in zones_generaux_territoire(territory, joueur, configuration):
            if zone.get("emplacement") not in configuration["emplacements"]:
                continue  # Réserve et renforts ne sont pas des forces engagées.
            emplacement = zone["emplacement"]
            resultat[joueur][emplacement] = None

            emplacement_dir = zone["chemin"]

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

            exclus = configuration.get("generaux_hors_combat", set())
            generaux_trouves = [p for p in generaux_trouves
                               if f"{joueur}:{p.name}" not in exclus]
            if not generaux_trouves:
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
                "camp": configuration["acteurs"][joueur]["camp"],
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


def regrouper_forces_par_camp(generaux_territoire, configuration=None):
    """Regroupe les références aux généraux sans remplacer leur propriétaire.

    Les collisions doivent avoir été traitées par la sécurité avant cet appel.
    Aucun général ne doit être écrasé silencieusement lors du regroupement.
    """
    if configuration is None:
        configuration = config.configuration_mode("classique")
    forces = {
        acteur["camp"]: {place: None for place in configuration["emplacements"]}
        for acteur in configuration["acteurs"].values()
    }
    for joueur, emplacements_joueur in generaux_territoire.items():
        camp = configuration["acteurs"][joueur]["camp"]
        for place in configuration["emplacements"]:
            general = emplacements_joueur.get(place)
            if general is None:
                continue
            if forces[camp][place] is not None:
                raise ValueError(f"Collision non résolue : {camp}/{place}")
            forces[camp][place] = general
    return forces


def contient_unites(chemin):
    """Présence vivante sans nettoyage, réparation ni effets de lecture."""
    for bloc in config.ordre_blocs:
        dossier = chemin / bloc
        if dossier.exists() and any(identifier_unite(u) != 'inconnu' for u in dossier.iterdir()):
            return True
    return False


def lire_forces_territoire(territory, configuration=None):
    return regrouper_forces_par_camp(
        lire_generaux_territoire(territory, configuration), configuration
    )


def controle_forces(forces):
    """Contrôle d'une collection de forces déjà regroupées par camp."""
    presents = [camp for camp in forces if total_unites_joueur_generaux(forces, camp) > 0]
    if not presents:
        return "neutre"
    if len(presents) == 1:
        return presents[0]
    return "conteste"


def lire_composition_general(chemin_general):
    """Compte les types réellement présents, sans réparer ni nettoyer les blocs."""
    from cycle_linux import sans_liens
    composition = {}
    for bloc in config.ordre_blocs:
        dossier = chemin_general / bloc
        sans_liens(dossier)
        effectifs = {}
        if dossier.is_dir():
            for unite in dossier.iterdir():
                sans_liens(unite)
                type_unite = identifier_unite(unite)
                if type_unite != 'inconnu':
                    effectifs[type_unite] = effectifs.get(type_unite, 0) + 1
        composition[bloc] = effectifs
    return composition


def lire_blocs_general(chemin_general, *, lecture_seule=False):
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

        if lecture_seule:
            from cycle_linux import sans_liens
            sans_liens(bloc_dir)
            if not bloc_dir.exists():
                continue
        # Si le bloc manque, on le recrée.
        # Ça évite qu'un général soit cassé par erreur.
        if not lecture_seule:
            bloc_dir.mkdir(exist_ok=True)

        type_trouves = []
        unites_trouvees = []
        a_supprimer = []

        for unite in bloc_dir.iterdir():
            if lecture_seule:
                sans_liens(unite)
            type_unite = identifier_unite(unite)

            if type_unite == "inconnu":
                a_supprimer.append(unite)
                continue

            type_trouves.append(type_unite)
            unites_trouvees.append(unite)

        # Supprimer les unités invalides.
        if lecture_seule and a_supprimer:
            raise ValueError('Bloc invalide : lecture seule sans nettoyage.')
        for unite in a_supprimer:
            if unite.is_dir():
                shutil.rmtree(unite)
            else:
                unite.unlink()

            rapports.afficher_et_ecrire(f"Unité invalide supprimée : {unite.name}")

        import unites as capacites
        soutiens = [u for u, t in zip(unites_trouvees, type_trouves)
                    if capacites.etiquette(t, 'non_combattant')]
        boucliers = [u for u, t in zip(unites_trouvees, type_trouves)
                     if t == 'Trop_gros_zombie']
        if len(soutiens) < len(unites_trouvees):
            combattants = [(u, t) for u, t in zip(unites_trouvees, type_trouves)
                          if u not in soutiens and u not in boucliers]
            unites_trouvees = [u for u, _ in combattants]
            type_trouves = [t for _, t in combattants]
            if soutiens:
                blocs_general[bloc]['soutiens'] = soutiens
            if boucliers:
                blocs_general[bloc]['boucliers'] = boucliers

        if len(type_trouves) > 0:
            effectifs = {}
            for type_unite in type_trouves:
                effectifs[type_unite] = effectifs.get(type_unite, 0) + 1

            maximum = max(effectifs.values())
            if lecture_seule and len(effectifs) > 1:
                raise ValueError('Bloc mixte : lecture seule sans suppression.')
            types_majoritaires = [
                type_unite for type_unite, nombre in effectifs.items()
                if nombre == maximum
            ]

            # Une égalité en tête rend le bloc invalide : tout supprimer.
            if len(types_majoritaires) > 1:
                for unite in unites_trouvees:
                    shutil.rmtree(unite)
                for unite in soutiens:
                    shutil.rmtree(unite)
                blocs_general[bloc].pop('soutiens', None)
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

    return {bloc: infos_bloc_valide(chemins_bloc(infos))
            for bloc, infos in blocs_general.items()}


def chemins_bloc(infos):
    """Tous les soldats du bloc, soutiens et boucliers compris, une seule fois."""
    return [*infos['unites'], *infos.get('soutiens', ()), *infos.get('boucliers', ())]


def infos_bloc_valide(chemins):
    """Lit une sélection déjà validée, sans nettoyer ni déplacer ses soldats."""
    import unites as capacites
    chemins = list(chemins)
    types = {u: identifier_unite(u) for u in chemins}
    if 'inconnu' in types.values():
        raise ValueError('Bloc invalide : aucune suppression implicite.')
    soutiens = [u for u in chemins if capacites.etiquette(types[u], 'non_combattant')]
    boucliers = [u for u in chemins if types[u] == 'Trop_gros_zombie']
    combattants = [u for u in chemins if u not in soutiens and u not in boucliers]
    # Un bloc exclusivement non combattant garde son comportement historique.
    if len(soutiens) == len(chemins):
        combattants, soutiens = soutiens, []
    types_combat = {types[u] for u in combattants}
    if len(types_combat) > 1:
        raise ValueError('Bloc mixte ou invalide : aucune suppression implicite.')
    infos = dict(type=next(iter(types_combat), 'vide'), nombre=len(combattants), unites=combattants)
    if soutiens:
        infos['soutiens'] = soutiens
    if boucliers:
        infos['boucliers'] = boucliers
    return infos


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
        total += (blocs_general[bloc]["nombre"] + len(blocs_general[bloc].get('soutiens', ()))
                  + len(blocs_general[bloc].get('boucliers', ())))

    return total


def total_unites_joueur_generaux(generaux_territoire, joueur):
    # Accepte aussi une force regroupée par camp, sans modifier les généraux.
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


def controle_territoire_generaux(generaux_territoire, configuration=None):
    return controle_forces(regrouper_forces_par_camp(generaux_territoire, configuration))


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


def trouver_position_general(joueur, nom_general, configuration=None):
    # Une copie dans le bac à sable ne doit pas masquer le général sur la carte.
    zones = sorted(zones_generaux(joueur, configuration),
                   key=lambda zone: zone["position"] == "home")
    for zone in zones:
        chemin = zone["chemin"] / nom_general
        if chemin.is_dir():
            return zone["position"], chemin
    return None, None


def trouver_toutes_positions_general(joueur, nom_general, configuration=None):
    positions = []
    for zone in zones_generaux(joueur, configuration):
        chemin = zone["chemin"] / nom_general
        if chemin.is_dir():
            occurrence = dict(zone)
            occurrence["chemin"] = chemin
            positions.append(occurrence)
    return positions


def general_a_des_unites(general):
    # Vérifie si un général existe et possède encore des unités.

    if general is None:
        return False

    return general["total_unites"] > 0


def generaux_actifs_joueur(generaux_territoire, joueur):
    # La clé peut être un propriétaire ou un camp ; l'ordre reste 1 -> 4.
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
    # Une force de camp réutilise cette même recherche d'ordre parmi ses généraux.
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

    # Un bouclier reste hors des confrontations ordinaires, même seul dans
    # son bloc. Sans combattant ordinaire, il disparaît et le général est vaincu.
    import bouclier_vivant
    if bouclier_vivant.seulement_bouclier(lire_composition_general(chemin_general)):
        bouclier_vivant.retirer_bouclier(general)
        total = 0

    if total > 0:
        return False

    rapports.afficher_et_ecrire(
        f"{general['joueur']} {rapports.nom_affichage_general(general)} "
        f"n'a plus d'unités. Général supprimé."
    )

    import soldats
    soldats.mort_general(general)
    shutil.rmtree(chemin_general)

    # Retirer l'identité dès la destruction, avant le prochain tour.
    # Le compteur reste inchangé : ce numéro ne doit jamais être réutilisé.
    positions = etat.charger_positions_generaux()
    positions.pop(f"{general['joueur']}:{general['nom']}", None)
    etat.sauvegarder_positions_generaux(positions)

    return True



def detruire_general_et_armee(general):
    """Élimine définitivement un général et ses soldats (Charge suicidaire).

    Ne passe pas par supprimer_general_si_vide : ce cas concerne précisément
    un général qui peut posséder encore des unités. Garder les UUID historiques.
    À appeler après fermeture des participations temporaires du duel.
    """
    if general is None or not general['chemin'].is_dir():
        return False
    import soldats
    donnees = soldats.charger()
    for bloc in config.ordre_blocs:
        dossier = general['chemin'] / bloc
        if not dossier.is_dir():
            continue
        for unite in dossier.iterdir():
            if not unite.is_dir():
                continue
            identifiant = soldats.retrouver(
                unite, donnees, config.dans_generation_privee())
            if identifiant is not None and identifiant in donnees:
                donnees[identifiant]['detruit'] = True
    soldats.sauvegarder(donnees)
    soldats.mort_general(general)
    shutil.rmtree(general['chemin'])
    positions = etat.charger_positions_generaux()
    positions.pop(f"{general['joueur']}:{general['nom']}", None)
    etat.sauvegarder_positions_generaux(positions)
    import ordres_pipeline
    ordres_pipeline.verifier_qg()
    rapports.afficher_et_ecrire(
        f"Charge suicidaire : {general['joueur']} "
        f"{rapports.nom_affichage_general(general)} et toute son armée éliminés.")
    return True


def verifier_limite_unites_general(chemin_general):
    # Vérifie qu'un général ne dépasse pas la limite d'unités autorisée.
    #
    # Règle actuelle :
    # un général peut avoir maximum 20 unités au total,
    # réparties librement entre avant, droite, gauche, arriere.

    blocs_general = lire_blocs_general(chemin_general)
    import unites
    total = unites.occupation(lire_composition_general(chemin_general))

    import progression
    # Le nom du propriétaire se trouve dans le chemin, y compris à la Morgue.
    joueurs = [j for j in config.joueurs if j in chemin_general.parts]
    fiche = (progression.caracteristiques_general(
        {'joueur': joueurs[0], 'nom': chemin_general.name}) if len(joueurs) == 1
        else None)
    limite = progression.capacite_maximale(fiche)
    if total <= limite:
        return

    surplus = total - limite

    # Pendant une bataille territoriale, les zombies engendrés par Spore et
    # Propagation ne sont régulés qu'après le dernier affrontement du territoire.
    # L'exception n'autorise pas un dépassement d'origine inconnue.
    import soldats
    contexte = soldats._bataille.get()
    if contexte and contexte[0]:
        registre = soldats.charger()
        recents = 0
        for bloc in config.ordre_blocs:
            for soldat in (chemin_general / bloc).iterdir():
                if identifier_unite(soldat) != 'zombie':
                    continue
                identifiant = soldats.retrouver(soldat, registre, config.dans_generation_privee())
                origine = registre.get(identifiant, {}).get('origine_officielle', {})
                if (origine.get('territoire') == contexte[0]
                        and ('propagation' in origine or 'spore' in origine)):
                    recents += 1
        if recents >= surplus:
            return

    rapports.afficher_et_ecrire(
        f"{chemin_general.name} dépasse la limite : "
        f"{total}/{limite} unités. "
        f"{surplus} unité(s) supprimée(s)."
    )

    # On supprime les unités en trop en partant de l'arrière vers l'avant.
    ordre_suppression = ["arriere", "gauche", "droite", "avant"]

    for bloc in ordre_suppression:
        if surplus <= 0:
            break

        blocs_general = lire_blocs_general(chemin_general)
        infos = blocs_general[bloc]

        for unite in [*infos["unites"], *infos.get('soutiens', ()), *infos.get('boucliers', ())]:
            if surplus <= 0:
                break

            places = unites.definition(identifier_unite(unite))['places']
            shutil.rmtree(unite)
            rapports.afficher_et_ecrire(
                f"Unité supprimée pour limite de général : {unite.name}"
            )
            surplus -= places



def reguler_surnombre_ralliement(general, aleatoire=None):
    """Régule les soldats du QG après Ralliement, sans perdre leur historique.

    Priorité aux soldats sans bataille survivante ; tirage aléatoire à
    priorité égale. Cette régulation est distincte de la limite historique.
    """
    import soldats
    import unites
    if aleatoire is None:
        aleatoire = random
    chemin = general['chemin']
    if not chemin.is_dir():
        return ()
    fiche = progression.caracteristiques_general(general)
    limite = progression.capacite_maximale(fiche)
    registre = soldats.charger()
    candidats = []
    occupation = 0
    for bloc in config.ordre_blocs:
        for unite in (chemin / bloc).iterdir():
            type_unite = identifier_unite(unite)
            if type_unite == 'inconnu':
                continue
            places = unites.definition(type_unite)['places']
            occupation += places
            identifiant = soldats.retrouver(
                unite, registre, config.dans_generation_privee())
            # Le registre constitue la source officielle d'expérience.
            if identifiant is None or identifiant not in registre:
                raise RuntimeError('Ralliement : soldat sans identité officielle.')
            experience = registre[identifiant]['batailles']
            candidats.append((experience, aleatoire.random(), unite, identifiant, places))
    if occupation <= limite:
        return ()
    # Aucun tri sur les blocs : les soldats inexpérimentés passent d'abord,
    # puis le hasard départage les candidats de même expérience.
    candidats.sort(key=lambda item: (item[0] != 0, item[1]))
    retires = []
    for _experience, _tirage, unite, identifiant, places in candidats:
        if occupation <= limite:
            break
        shutil.rmtree(unite)
        registre[identifiant]['detruit'] = True
        retires.append(identifiant)
        occupation -= places
    soldats.sauvegarder(registre)
    rapports.afficher_et_ecrire(
        f"Ralliement : {len(retires)} soldat(s) retiré(s) pour respecter "
        f"la capacité du général {general['nom']} ({occupation}/{limite} places).")
    return tuple(retires)


def identifier_unite(unite):
    if not unite.is_dir():
        return "inconnu"

    nom_unite = unite.name
    contenu = [element.name for element in unite.iterdir() if element.is_file()]

    prefixe_lourd, equipements_lourds = config.unites_equipements['cavalerie_lourde']
    if nom_unite.startswith(prefixe_lourd):
        # Le préfixe réservé ne doit pas retomber sur le cavalier ordinaire.
        return 'cavalerie_lourde' if all(e in contenu for e in equipements_lourds) else 'inconnu'

    resultats = []

    for type_unite, (nom_base, equipements) in config.unites_equipements.items():
        if nom_unite.startswith(nom_base) and all(e in contenu for e in equipements):
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
