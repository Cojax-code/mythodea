"""Audit des généraux et validation des actions avant les combats."""
import pwd
import shutil
from pathlib import Path
from collections import Counter

import config
import etat
import generaux
import mouvements
import rapports


def cle_general_actions(chemin, joueur, configuration):
    home = next(z['chemin'] for z in generaux.zones_generaux(joueur, configuration)
                if z['position'] == 'home')
    if chemin.parent == home:
        return f'home/{joueur}/{chemin.name}'
    return 'game/' + chemin.relative_to(configuration['game_path']).as_posix()


def chemin_general_actions(cle, configuration):
    parties = Path(cle).parts
    if parties[0] == 'home':
        home = next(z['chemin'] for z in generaux.zones_generaux(parties[1], configuration)
                    if z['position'] == 'home')
        return home / parties[2]
    return configuration['game_path'].joinpath(*parties[1:])


def inventorier_unites_actions(configuration):
    """Identités du disque vivant, relevées sous gel avant toute copie."""
    from cycle_linux import sans_liens
    resultat = {}
    for joueur in configuration['joueurs']:
        for zone in generaux.zones_generaux(joueur, configuration):
            parent = zone['chemin']
            sans_liens(parent)
            if not parent.exists():
                continue
            for chemin in parent.iterdir():
                sans_liens(chemin)
                if not chemin.is_dir() or generaux.numero_general_depuis_nom(chemin.name) is None:
                    continue
                unites = {}
                for bloc in config.ordre_blocs:
                    dossier = chemin / bloc
                    sans_liens(dossier)
                    if not dossier.is_dir():
                        continue
                    for unite in dossier.iterdir():
                        sans_liens(unite)
                        if unite.is_dir():
                            for element in unite.iterdir():
                                sans_liens(element)
                        type_unite = generaux.identifier_unite(unite)
                        if type_unite == 'inconnu':
                            continue
                        equipement = unite / {'archer': 'arc', 'piquier': 'pique',
                                               'cavalier': 'cheval'}[type_unite]
                        dossier_stat, equipement_stat = unite.stat(), equipement.stat()
                        unites[unite.relative_to(chemin).as_posix()] = [
                            dossier_stat.st_dev, dossier_stat.st_ino,
                            equipement_stat.st_dev, equipement_stat.st_ino, type_unite]
                cle = cle_general_actions(chemin, joueur, configuration)
                resultat[cle] = {'identifiant': f'{joueur}:{chemin.name}',
                                'device': chemin.stat().st_dev,
                                'position': zone['position'],
                                'entrainement': zone['position'] == 'home' or (
                                    zone['position'] in configuration['villages']
                                    and parent.name == 'reserve'),
                                'unites': unites}
    return resultat


def memoriser_unites_actions(configuration, tour, nouveaux=()):
    """Référence publiée ; ajouter un général moteur ne revalide pas les autres."""
    reference = etat.charger_unites_actions(configuration)
    inventaire = inventorier_unites_actions(configuration)
    if nouveaux:
        if reference is None:
            raise RuntimeError('Référence des unités absente : récupération requise.')
        for cle, valeur in inventaire.items():
            if valeur['identifiant'] in nouveaux:
                reference['generaux'][cle] = valeur
        reference['tour'] = tour
    else:
        reference = {'tour': tour, 'generaux': inventaire}
    etat.sauvegarder_unites_actions(configuration, reference)


def auditer_entrainement(configuration, positions, punis):
    """Retire les ajouts interdits ; remet l'entraînement mobile à son origine."""
    if configuration['mode'] != 'survie':
        return
    reference = etat.charger_unites_actions(configuration)
    # L'API métier isolée reste utilisable sans cycle ; la capture réelle exige
    # toujours une référence et transmet les observations des inodes vivants.
    if reference is None:
        return
    observations = reference.get('capture')
    if observations is None:
        observations = inventorier_unites_actions(configuration)
    origines = {g['identifiant']: (cle, g) for cle, g in reference['generaux'].items()
                if positions.get(g['identifiant']) == g['position']}
    for cle, actuel in observations.items():
        identifiant = actuel['identifiant']
        if identifiant in punis or identifiant not in positions:
            continue
        chemin = chemin_general_actions(cle, configuration)
        joueur = identifiant.split(':')[0]
        if not chemin.exists() or joueur_proprietaire_chemin(chemin) != joueur:
            continue
        origine_cle, origine = origines.get(identifiant, (None, {}))
        anciennes = {tuple(u) for u in origine.get('unites', {}).values()}
        if origine and origine['device'] != actuel['device']:
            # mv entre /home et une partition /home/game copie les inodes.
            # Les unités d'un même type sont interchangeables pour le moteur :
            # conserver au plus les effectifs publiés, jamais un renfort net.
            disponibles = Counter(u[-1] for u in origine['unites'].values())
            nouvelles = []
            for relatif, unite in sorted(actuel['unites'].items()):
                if disponibles[unite[-1]]:
                    disponibles[unite[-1]] -= 1
                else:
                    nouvelles.append(chemin / relatif)
        else:
            nouvelles = [chemin / relatif for relatif, unite in actuel['unites'].items()
                         if tuple(unite) not in anciennes]
        if not nouvelles:
            continue
        deplacement, _, _ = mouvements.verifier_deplacement_general(
            joueur, positions[identifiant], actuel['position'],
            etat.charger_controle_territoires(configuration), configuration)
        if actuel['entrainement'] and (cle == origine_cle or (
                not origine.get('entrainement') and deplacement)):
            # Un rappel légal permet d'entraîner dans le home à l'arrivée.
            rapports.afficher_et_ecrire(
                f'{identifiant} : entraînement autorisé, {len(nouvelles)} unité(s) ; '
                'départ possible au tour suivant.')
        elif origine.get('entrainement'):
            destination = chemin_general_actions(origine_cle, configuration)
            if destination.exists():
                raise RuntimeError(f'Retour après entraînement impossible : {destination}')
            shutil.move(str(chemin), str(destination))
            rapports.afficher_et_ecrire(
                f'{identifiant} : déplacement refusé après entraînement ; '
                'retour à la zone de départ, attendre le tour suivant.')
        else:
            for unite in nouvelles:
                if unite.exists():
                    shutil.rmtree(unite)
            rapports.afficher_et_ecrire(
                f'{identifiant} : {len(nouvelles)} nouvelle(s) unité(s) supprimée(s), '
                'entraînement interdit hors home/réserve ; unités anciennes conservées.')


def controler_coherence_territoires(configuration):
    """Inspecte les présences sans réparer, sanctionner ni modifier les compteurs."""
    officielles = etat.charger_positions_generaux()
    identites = set()
    presences = {}
    for territoire in configuration["territoires"]:
        presences[territoire.name] = set()
        places = set()
        for joueur, acteur in configuration["acteurs"].items():
            for zone in generaux.zones_generaux_territoire(territoire, joueur, configuration):
                if not zone["chemin"].exists():
                    continue
                for chemin in zone["chemin"].iterdir():
                    if not chemin.is_dir():
                        continue
                    identifiant = f"{joueur}:{chemin.name}"
                    if (generaux.numero_general_depuis_nom(chemin.name) is None
                            or identifiant in identites
                            or officielles.get(identifiant) != territoire.name):
                        raise ValueError(f"Présence incohérente : {chemin}")
                    identites.add(identifiant)
                    place = zone.get("emplacement")
                    if place is not None:
                        cle = (acteur["camp"], place)
                        if cle in places:
                            raise ValueError(f"Collision non résolue : {territoire.name}/{cle}")
                        places.add(cle)
                    if place in configuration["emplacements"]:
                        if generaux.contient_unites(chemin):
                            presences[territoire.name].add(acteur["camp"])
    tactiques = {t.name for t in configuration["territoires"]}
    manquantes = {i for i, position in officielles.items()
                 if position in tactiques and i not in identites}
    if manquantes:
        raise ValueError(f"Identités absentes du plateau : {sorted(manquantes)}")
    return presences


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

    for joueur in config.joueurs:
        uid_joueur = pwd.getpwnam(joueur).pw_uid

        if uid_chemin == uid_joueur:
            return joueur

    return None


def securiser_generaux_mauvais_joueur(
    positions_avant, configuration=None
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

    if configuration is None:
        configuration = config.configuration_mode("classique")
    generaux_punis = set()

    for joueur_zone in configuration["joueurs"]:
        for zone in generaux.zones_generaux(joueur_zone, configuration):
            nom_zone = zone["position"]
            chemin_zone = zone["chemin"]

            if not chemin_zone.exists():
                continue

            for chemin_general in list(
                chemin_zone.iterdir()
            ):
                if not chemin_general.is_dir():
                    continue

                numero = generaux.numero_general_depuis_nom(
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

                if nom_zone == "home":
                    rapports.afficher_et_ecrire(
                        f"Avertissement dans le home : propriétaire incorrect pour "
                        f"{chemin_general}, aucune sanction.")
                    continue

                # Propriétaire Linux inconnu :
                # le dossier ne peut pas être considéré
                # comme un véritable général.
                if proprietaire_reel is None:
                    rapports.afficher_et_ecrire(
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

                rapports.afficher_et_ecrire(
                    f"{identifiant} placé dans "
                    f"l'arborescence de {joueur_zone} "
                    f"({nom_zone})."
                )

                dernier_numero = etat.lire_compteur_general(
                    proprietaire_reel
                )

                # Le dossier appartient bien à un joueur,
                # mais le général n'est pas officiellement actif.
                if (
                    numero < 1
                    or numero > dernier_numero
                    or identifiant not in positions_avant
                ):
                    rapports.afficher_et_ecrire(
                        f"Général non autorisé supprimé : "
                        f"{identifiant}"
                    )

                    shutil.rmtree(
                        chemin_general
                    )

                    continue

                occurrences_correctes = (
                    generaux.trouver_toutes_positions_general(
                        proprietaire_reel,
                        chemin_general.name,
                        configuration
                    )
                )
                occurrences_correctes = [o for o in occurrences_correctes
                                          if o["position"] != "home"]

                # --------------------------------------
                # Aucune autre occurrence
                # --------------------------------------

                if len(occurrences_correctes) == 0:
                    mouvements.envoyer_general_au_repli(
                        proprietaire_reel, chemin_general.name, chemin_general,
                        configuration, lieu_sanction=nom_zone)

                    generaux_punis.add(
                        identifiant
                    )

                    rapports.afficher_et_ecrire(
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

                rapports.afficher_et_ecrire(
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

                    mouvements.envoyer_general_au_repli(
                        proprietaire_reel,
                        chemin_general.name,
                        occurrence_reelle["chemin"],
                        configuration,
                        lieu_sanction=nom_zone,
                    )

                    generaux_punis.add(
                        identifiant
                    )

                    rapports.afficher_et_ecrire(
                        f"{identifiant} envoyé au repli "
                        f"pour placement chez "
                        f"{joueur_zone}."
                    )

    return generaux_punis


def supprimer_generaux_non_autorises(configuration=None):
    # Même contrôle d'identité dans toutes les zones, y compris les réserves.
    if configuration is None:
        configuration = config.configuration_mode("classique")
    positions = etat.charger_positions_generaux()
    for joueur in configuration["joueurs"]:
        dernier_numero = etat.lire_compteur_general(joueur)
        for zone in generaux.zones_generaux(joueur, configuration):
            chemin = zone["chemin"]
            if not chemin.exists():
                continue
            for element in list(chemin.iterdir()):
                if not element.is_dir() or not element.name.startswith("general"):
                    continue
                numero = generaux.numero_general_depuis_nom(element.name)
                if (numero is None or numero < 1 or numero > dernier_numero
                        or f"{joueur}:{element.name}" not in positions):
                    if zone["position"] == "home":
                        rapports.afficher_et_ecrire(
                            f"Avertissement dans le home : général non autorisé "
                            f"{joueur}:{element.name}, aucune sanction.")
                        continue
                    suffixe = ""
                    if zone["position"] not in ("home", "repli"):
                        suffixe = f" sur {zone['position']}"
                    rapports.afficher_et_ecrire(
                        f"Général non autorisé supprimé : {joueur} {element.name}{suffixe}"
                    )
                    shutil.rmtree(element)


def securiser_generaux_dupliques(positions_avant, configuration=None):
    # Détecte les généraux présents plusieurs fois.
    #
    # En cas de duplication :
    # - une seule copie est conservée ;
    # - les autres sont supprimées ;
    # - la copie conservée est envoyée au repli.
    #
    # La fonction retourne les identifiants punis.

    if configuration is None:
        configuration = config.configuration_mode("classique")
    generaux_punis = set()

    for joueur in configuration["joueurs"]:
        dernier_numero = etat.lire_compteur_general(joueur)

        for numero in range(
            1,
            dernier_numero + 1
        ):
            nom_general = f"general{numero}"
            identifiant = (
                f"{joueur}:{nom_general}"
            )

            occurrences = (
                generaux.trouver_toutes_positions_general(
                    joueur,
                    nom_general,
                    configuration
                )
            )

            if len(occurrences) <= 1:
                continue

            # Les copies du bac à sable restent intactes et ne sanctionnent
            # pas l'occurrence officielle sur la carte ou au repli.
            if any(o["position"] == "home" for o in occurrences):
                rapports.afficher_et_ecrire(
                    f"Avertissement dans le home : copie de {identifiant}, "
                    f"aucune sanction pour cette copie.")
                occurrences = [o for o in occurrences if o["position"] != "home"]
                if len(occurrences) <= 1:
                    continue

            rapports.afficher_et_ecrire(
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

                    rapports.afficher_et_ecrire(
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
                mouvements.envoyer_general_au_repli(
                    joueur,
                    nom_general,
                    chemin_garde,
                    configuration
                )
            else:
                rapports.afficher_et_ecrire(
                    f"Avertissement au repli : duplication de {identifiant}, "
                    f"délai conservé sans nouvelle sanction.")

            generaux_punis.add(
                identifiant
            )

            if copie_a_garder["position"] != "repli":
                rapports.afficher_et_ecrire(
                    f"{identifiant} envoyé au repli pour duplication."
                )

    return generaux_punis


def securiser_emplacements_generaux(configuration=None, territoire=None):
    """Sanctionne tous les occupants d'une position en collision.

    En classique, les positions sont propres à chaque joueur. En Survie,
    elles sont communes aux joueurs du même camp. La réserve est exclue.
    """
    if configuration is None:
        configuration = config.configuration_mode("classique")
    generaux_punis = set()
    territoires = configuration["territoires"] if territoire is None else [territoire]
    for territory in territoires:
        positions = {}
        for joueur in configuration["joueurs"]:
            camp = configuration["acteurs"][joueur]["camp"]
            groupe = camp if configuration["emplacements_partages"] else joueur
            for zone in generaux.zones_generaux_territoire(territory, joueur, configuration):
                if "emplacement" not in zone or not zone["chemin"].exists():
                    continue
                cle = (groupe, zone["emplacement"])
                occupants = positions.setdefault(cle, [])
                for element in zone["chemin"].iterdir():
                    if element.is_dir() and element.name.startswith("general"):
                        occupants.append((joueur, element))

        for (groupe, emplacement), occupants in positions.items():
            if len(occupants) <= 1:
                continue
            rapports.afficher_et_ecrire(
                f"Emplacement invalide : {territory.name} "
                f"{groupe}/{emplacement} contient plusieurs généraux."
            )
            for joueur, chemin_general in occupants:
                identifiant = f"{joueur}:{chemin_general.name}"
                mouvements.envoyer_general_au_repli(
                    joueur, chemin_general.name, chemin_general, configuration
                )
                generaux_punis.add(identifiant)
                rapports.afficher_et_ecrire(f"{identifiant} envoyé au repli.")
    return generaux_punis


def verifier_tous_les_deplacements(configuration=None):
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

    if configuration is None:
        configuration = config.configuration_mode("classique")
    config.verifier_structure_actuelle(configuration)

    rapports.afficher_et_ecrire(
        "\n=== Vérification des déplacements ==="
    )

    positions = etat.charger_positions_generaux()
    controle_avant = etat.charger_controle_territoires(configuration)
    attentes_avant = etat.charger_attentes_repli(configuration)

    # ------------------------------------------
    # Sécurité générale
    # ------------------------------------------

    punis_mauvais_joueur = (
        securiser_generaux_mauvais_joueur(
            positions, configuration
        )
    )

    supprimer_generaux_non_autorises(configuration)

    punis_duplication = (
        securiser_generaux_dupliques(
            positions, configuration
        )
    )

    import crypte
    punis_crypte = crypte.auditer_recuperations(configuration)

    auditer_entrainement(configuration, positions,
                        punis_mauvais_joueur | punis_duplication | punis_crypte)

    # Un général encore en attente ne peut pas entrer en combat ni occuper
    # une place alliée. Le retour forcé n'ajoute pas une nouvelle sanction.
    for identifiant in attentes_avant:
        if identifiant in punis_mauvais_joueur | punis_duplication:
            continue
        joueur, nom = identifiant.split(":", 1)
        if joueur not in configuration["joueurs"]:
            continue
        position, chemin = generaux.trouver_position_general(joueur, nom, configuration)
        if position == "home":
            continue
        if chemin is not None and position != "repli":
            mouvements.envoyer_general_au_repli(
                joueur, nom, chemin, configuration, appliquer_sanction=False)
        if chemin is not None:
            rapports.afficher_et_ecrire(
                f"{identifiant} : action interdite, attente au repli "
                f"({attentes_avant[identifiant]} tour(s)).")

    punis_emplacement = (
        securiser_emplacements_generaux(configuration)
    )

    generaux_deja_punis = (
        punis_mauvais_joueur
        | punis_duplication
        | punis_emplacement
        | punis_crypte
    )

    # ------------------------------------------
    # Fatigue du nouveau tour
    # ------------------------------------------

    generaux_fatigues = set()
    # Les acteurs pilotés par le moteur ne sont pas audités comme des joueurs.
    acteurs_automatiques = set(configuration["acteurs"]) - set(configuration["joueurs"])
    nouvelles_positions = {
        identifiant: position for identifiant, position in positions.items()
        if identifiant.split(":", 1)[0] in acteurs_automatiques
    }

    # Un général déplacé dans le home de l'autre joueur reste identifiable
    # par son propriétaire ; l'avertissement ne doit pas effacer son identité.
    generaux_home = {}
    for joueur in configuration["joueurs"]:
        home = next(z["chemin"] for z in generaux.zones_generaux(joueur, configuration)
                    if z["position"] == "home")
        if home.exists():
            for chemin in home.iterdir():
                if chemin.is_dir() and generaux.numero_general_depuis_nom(chemin.name) is not None:
                    proprietaire = joueur_proprietaire_chemin(chemin)
                    generaux_home[f"{proprietaire}:{chemin.name}"] = chemin

    # ------------------------------------------
    # Vérification individuelle
    # ------------------------------------------

    for joueur in configuration["joueurs"]:
        dernier_numero = (
            etat.lire_compteur_general(joueur)
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
                generaux.trouver_position_general(
                    joueur,
                    nom_general,
                    configuration
                )
            )

            # Général détruit ou absent.
            if position_actuelle is None:
                if identifiant in generaux_home:
                    position_actuelle = "home"
                else:
                    continue

            if position_actuelle == "home":
                if configuration['mode'] == 'survie' and positions.get(identifiant) != 'home':
                    origine = positions.get(identifiant)
                    autorise, _, raison = mouvements.verifier_deplacement_general(
                        joueur, origine, 'home', controle_avant, configuration)
                    proprietaire_correct = (chemin_actuel is not None
                        and joueur_proprietaire_chemin(chemin_actuel) == joueur)
                    if (origine is not None and autorise and proprietaire_correct
                            and identifiant not in attentes_avant
                            and identifiant not in generaux_deja_punis):
                        nouvelles_positions[identifiant] = 'home'
                        rapports.afficher_et_ecrire(f'{identifiant} : {origine} -> home [{raison}]')
                    elif origine is not None:
                        nouvelles_positions[identifiant] = origine
                        rapports.afficher_et_ecrire(
                            f'Avertissement dans le home : rappel refusé pour {identifiant}, '
                            'identité, propriétaire ou position de départ invalide.')
                        if origine == 'repli' and proprietaire_correct:
                            destination = configuration['repli_path'] / joueur / nom_general
                            if not destination.exists():
                                shutil.move(str(chemin_actuel), str(destination))
                            generaux_deja_punis.add(identifiant)
                    continue
                if positions.get(identifiant) != "home" or identifiant in attentes_avant:
                    rapports.afficher_et_ecrire(
                        f"Avertissement dans le home : position anormale de "
                        f"{identifiant}, aucune sanction.")
                # Ne pas autoriser implicitement une identité créée à la main.
                if identifiant in positions:
                    nouvelles_positions[identifiant] = "home"
                continue

            # Un général sanctionné pendant l'audit
            # doit maintenant se trouver au repli.
            if identifiant in generaux_deja_punis or identifiant in attentes_avant:
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
                rapports.afficher_et_ecrire(
                    f"Général sans position officielle supprimé : {identifiant}"
                )

                continue

            autorise, fatigue, raison = (
                mouvements.verifier_deplacement_general(
                    joueur,
                    origine,
                    position_actuelle,
                    controle_avant,
                    configuration
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

                    rapports.afficher_et_ecrire(
                        f"{identifiant} : "
                        f"{origine} -> "
                        f"{position_actuelle} "
                        f"[MARCHE FORCÉE - FATIGUE]"
                    )

                elif origine == position_actuelle:
                    rapports.afficher_et_ecrire(
                        f"{identifiant} : "
                        f"reste sur {origine}"
                    )

                else:
                    rapports.afficher_et_ecrire(
                        f"{identifiant} : "
                        f"{origine} -> "
                        f"{position_actuelle} "
                        f"[{raison}]"
                    )

                continue

            # --------------------------------------
            # Mouvement interdit
            # --------------------------------------

            rapports.afficher_et_ecrire(
                f"{identifiant} : "
                f"déplacement interdit "
                f"{origine} -> "
                f"{position_actuelle}"
            )

            rapports.afficher_et_ecrire(
                f"Raison : {raison}"
            )

            mouvements.envoyer_general_au_repli(
                joueur,
                nom_general,
                chemin_actuel,
                configuration
            )

            nouvelles_positions[
                identifiant
            ] = "repli"

            rapports.afficher_et_ecrire(
                f"{identifiant} envoyé au repli."
            )

    # ------------------------------------------
    # Sauvegarde
    # ------------------------------------------

    etat.sauvegarder_positions_generaux(
        nouvelles_positions
    )

    etat.sauvegarder_generaux_fatigues(
        generaux_fatigues
    )
    # Un appel d'audit valide les actions d'un tour. Seuls les délais déjà
    # présents à son début diminuent ; une sanction nouvelle garde sa durée.
    attentes = etat.charger_attentes_repli(configuration)
    for identifiant in attentes_avant:
        if identifiant not in nouvelles_positions:
            attentes.pop(identifiant, None)
        elif identifiant not in generaux_deja_punis and nouvelles_positions[identifiant] != "home":
            attentes[identifiant] = max(0, attentes_avant[identifiant] - 1)
    if attentes or attentes_avant:
        etat.sauvegarder_attentes_repli(attentes, configuration)
    generaux.scanner_ordres_surnombre(configuration)
