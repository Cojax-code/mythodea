"""Écriture, formatage et affichage des rapports du tour."""
from pathlib import Path
import os
import grp
import json
import stat
from contextlib import contextmanager
from contextvars import ContextVar

import config
import etat


territoire_rapport_actuel = None
meteo_tour = None
_groupe_lecture = ContextVar('groupe_lecture_rapports', default=None)
_preparation = ContextVar('preparation_privee_rapports', default=None)


@contextmanager
def preparation_privee(repertoire):
    """Les sorties d'une résolution ne deviennent visibles qu'à publication."""
    from cycle_linux import dossier_prive
    dossier_prive(repertoire)
    jeton = _preparation.set(repertoire)
    try:
        yield
    finally:
        _preparation.reset(jeton)


def chemin_sortie(chemin):
    repertoire = _preparation.get()
    return repertoire / chemin.relative_to(config.rapport_dir) if repertoire else chemin


def ouvrir_suivi(configuration, gid):
    """Inode permanent, sans liens ; l'appelant sérialise les écritures."""
    from cycle_linux import sans_liens, synchroniser_dossier
    chemin = configuration['game_path'] / 'rapport/suivi_combats.log'
    sans_liens(chemin)
    fd = os.open(chemin, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        infos = os.fstat(fd)
        if not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1:
            raise RuntimeError('Journal de combat non ordinaire ou lié.')
        os.chown(chemin, 0, gid)
        os.chmod(chemin, 0o640)
        synchroniser_dossier(chemin.parent)
        return os.fdopen(fd, 'r+b')
    except BaseException:
        os.close(fd)
        raise


def publier_preparation(configuration, generation, gid, debut, defaite=False):
    """Installation sous gel ; une reprise réutilise les mêmes sorties privées."""
    from cycle_linux import sans_liens
    import minuterie
    intervalle = minuterie.valider_duree(configuration.get('delai_evenements_combats_secondes', 1))
    source = generation / 'rapports'
    fichiers = ['rapport_court.txt', 'rapport_long.txt',
                *(f'territoires/{t.name}.txt' for t in configuration['territoires'])]
    for relatif in fichiers:
        sans_liens(source / relatif)
        if not (source / relatif).is_file():
            raise RuntimeError('Rapports privés incomplets : récupération requise.')
    with droits_allies(gid):
        for relatif in fichiers:
            destination = configuration['game_path'] / 'rapport' / relatif
            etat.ecrire_prive(destination, (source / relatif).read_text(encoding='utf-8'))
            proteger_rapport(destination)
    plan = configuration['game_path'] / '.systeme/diffusion_rapports.json'
    precedent = json.loads(plan.read_text(encoding='utf-8')) if plan.exists() else None
    if precedent and precedent['generation'] == generation.name:
        return  # Ne réinitialiser ni le point de départ ni le journal à la reprise.
    if precedent:
        diffuser(configuration, gid, debut, terminer=True)
    evenements = [f"=== TOUR {json.loads((generation / 'resultat.json').read_text())['tour']} ===\n"]
    evenements.extend(json.loads(ligne) for ligne in
                      (source / 'evenements.jsonl').read_text(encoding='utf-8').splitlines())
    duree = 0 if defaite else configuration['duree_consultation_secondes']
    intervalle = min(intervalle, duree / max(1, len(evenements) - 1))
    with ouvrir_suivi(configuration, gid) as fichier:
        infos = os.fstat(fichier.fileno())
        donnees = dict(generation=generation.name, debut=debut, intervalle=intervalle,
                       position=infos.st_size, device=infos.st_dev, inode=infos.st_ino,
                       evenements=evenements)
    # Le plan immuable est durable AVANT le premier append. À la reprise,
    # les octets déjà écrits font foi, même après une écriture partielle.
    etat.ecrire_prive(plan, json.dumps(donnees, ensure_ascii=False) + '\n')


def diffuser(configuration, gid, maintenant, terminer=False):
    """Appelé par le minuteur de consultation, sans attente ni processus séparé.

    Le préfixe exact du flux permet de reprendre après append/fsync interrompu,
    sans fenêtre entre un curseur privé et les octets effectivement publiés.
    """
    plan = configuration['game_path'] / '.systeme/diffusion_rapports.json'
    if not plan.exists():
        return
    donnees = json.loads(plan.read_text(encoding='utf-8'))
    evenements = [texte.encode('utf-8') for texte in donnees['evenements']]
    intervalle = donnees['intervalle']
    nombre = len(evenements) if terminer or intervalle == 0 else min(
        len(evenements), max(0, int((maintenant - donnees['debut']) / intervalle) + 1))
    attendu = b''.join(evenements)
    voulu = sum(map(len, evenements[:nombre]))
    with ouvrir_suivi(configuration, gid) as fichier:
        infos = os.fstat(fichier.fileno())
        if ((infos.st_dev, infos.st_ino) != (donnees['device'], donnees['inode'])
                or infos.st_size < donnees['position']):
            raise RuntimeError('Journal de combat remplacé ou tronqué : récupération requise.')
        fichier.seek(donnees['position'])
        present = fichier.read()
        if not attendu.startswith(present):
            raise RuntimeError('Journal de combat divergent : récupération requise.')
        if len(present) < voulu:
            fichier.seek(0, os.SEEK_END)
            fichier.write(attendu[len(present):voulu])
            fichier.flush()
            os.fsync(fichier.fileno())


@contextmanager
def droits_allies(gid):
    jeton = _groupe_lecture.set(gid)
    try:
        yield
    finally:
        _groupe_lecture.reset(jeton)


def proteger_rapport(chemin):
    gid = _groupe_lecture.get()
    if gid is not None:
        technique = _preparation.get() is not None or chemin.name == config.rapport_long_path.name
        os.chown(chemin, 0, 0 if technique else gid)
        os.chmod(chemin, 0o600 if technique else 0o640)


def vider_rapport(chemin):
    """Garde l'inode pour les lecteurs tail ; privé dès la création."""
    chemin = chemin_sortie(chemin)
    mode = 0o600 if _groupe_lecture.get() is not None or _preparation.get() else 0o666
    fd = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), mode)
    try:
        proteger_rapport(chemin)
    finally:
        os.close(fd)


def nom_affichage_general(general):
    """Un libellé de vague ou de récompense ne remplace jamais generalN."""
    if general["joueur"] == "bot":
        return general.get("fiche", {}).get("nom_affichage", general["nom"])
    if general.get('fiche', {}).get('nom_affichage'):
        import crypte
        d = crypte.charger({'game_path': config.racine_metier(), 'joueurs': []})
        for attribution in d.get(general['joueur'], {}).get('attributions', []):
            if (attribution.get('source') == 'defi' and attribution['general'] == general['nom']
                    and attribution.get('nom_affichage') == general['fiche']['nom_affichage']):
                return attribution['nom_affichage']
            recette = crypte.RECETTES.get(attribution.get('recette', 'recette1'))
            if (attribution['general'] == general['nom'] and recette
                    and general['fiche']['nom_affichage'] == recette['nom']):
                return recette['nom']
    return general["nom"]


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

    return f"{nombre} {nom_type_unite(type_unite, nombre)}"


def lire_etat_exploration(configuration, vague):
    """Photographie en lecture seule ; appeler sur un plateau figé ou une copie privée.

    Les zones viennent du moteur commun. Seules les places actives contribuent
    au contrôle ; réserve, récompense, renforts et repli restent hors combat.
    """
    import generaux
    from cycle_linux import sans_liens
    photographie = {'vague': vague, 'territoires': []}
    for territoire in (*configuration['territoires'], configuration['repli_path']):
        repli = territoire == configuration['repli_path']
        village = territoire.name in configuration['villages']
        vue = {'nom': territoire.name, 'village': village, 'acteurs': {}}
        forces = {acteur['camp']: {place: {'total_unites': 0}
                  for place in configuration['emplacements']}
                  for acteur in configuration['acteurs'].values()}
        for joueur, acteur in configuration['acteurs'].items():
            zones = ([{'chemin': territoire / joueur}] if repli else
                     generaux.zones_generaux_territoire(territoire, joueur, configuration))
            groupes = {}
            for zone in zones:
                place = zone.get('emplacement')
                actif = not repli and place in configuration['emplacements']
                if repli:
                    libelle = 'Généraux en repli (hors combat)'
                elif actif:
                    libelle = 'Garnison' if village and joueur in configuration['joueurs'] else 'Positions actives'
                elif zone.get('crypte'):
                    libelle = 'Récompense Crypte (hors combat)'
                elif zone.get('batiment'):
                    libelle = {'hopital': 'Hôpital', 'ecole_officiers': 'École des officiers',
                                 'forge': 'Forge', 'crypte_des_plaines': 'Crypte des plaines'}[zone['batiment']] + ' (hors combat)'
                elif village and joueur in configuration['joueurs']:
                    libelle = 'Réserve (hors combat)'
                else:
                    libelle = 'Colonne en attente' if joueur == 'bot' else 'Renforts (hors places actives)'
                groupe = groupes.setdefault(libelle, {})
                entries = groupe.setdefault(place, [])
                chemin = zone['chemin']
                sans_liens(chemin)
                if not chemin.is_dir():
                    continue
                chemins = []
                for enfant in chemin.iterdir():
                    sans_liens(enfant)
                    if enfant.is_dir() and generaux.numero_general_depuis_nom(enfant.name) is not None:
                        chemins.append(enfant)
                chemins.sort(key=lambda p: generaux.numero_general_depuis_nom(p.name))
                for general in chemins:
                    sans_liens(general / 'fiche.txt')
                    blocs = generaux.lire_composition_general(general)
                    total = sum(sum(types.values()) for types in blocs.values())
                    infos = {'nom': general.name, 'joueur': joueur,
                             'fiche': generaux.lire_fiche_general(general)}
                    with config.racines_generation(configuration['game_path'], {}):
                        nom = nom_affichage_general(infos)
                    entries.append({'nom': nom, 'blocs': blocs, 'total_unites': total})
                    if actif:
                        forces[acteur['camp']][place]['total_unites'] += total
            vue['acteurs'][joueur] = groupes
        vue['controle'] = None if repli else generaux.controle_forces(forces)
        photographie['territoires'].append(vue)
    return photographie


def generer_rapport_exploration(joueur, etat_publie):
    """Rendu pur par destinataire ; point unique pour une future visibilité filtrée."""
    lignes = [f"RAPPORT D'EXPLORATION — {joueur}", f"Vague : {etat_publie['vague']}", '']
    controles = {'allies': 'allié', 'bot': 'bot', 'conteste': 'contesté',
                 'neutre': 'vide', None: 'hors combat (zone de sanction)'}
    for territoire in etat_publie['territoires']:
        occupants_garnison = {}
        for proprietaire, groupes in territoire['acteurs'].items():
            for place, presents in groupes.get('Garnison', {}).items():
                if presents:
                    occupants_garnison.setdefault(place, []).append(proprietaire)
        lignes.extend(['=' * 60, territoire['nom'].upper(), '=' * 60, '',
                       f"Contrôle : {controles[territoire['controle']]}", ''])
        for acteur, groupes in territoire['acteurs'].items():
            lignes.append('BOT' if acteur == 'bot' else acteur)
            garnison = territoire['village'] and 'Garnison' in groupes
            if not garnison and not any(gs for places in groupes.values() for gs in places.values()):
                lignes.extend(['  aucune présence', ''])
                continue
            for zone, places in groupes.items():
                presents = any(places.values())
                if not presents and zone not in ('Garnison', 'Réserve (hors combat)'):
                    continue
                lignes.append(f'  {zone} :')
                if not presents and zone != 'Garnison':
                    lignes.append('    aucune présence')
                for place, generaux_presents in places.items():
                    if not generaux_presents and zone == 'Garnison':
                        occupants = occupants_garnison.get(place, [])
                        situation = 'occupé par ' + ', '.join(occupants) if occupants else 'vide'
                        lignes.append(f'    {place} : {situation}')
                    for general in generaux_presents:
                        prefixe = f'{place} : ' if place is not None else ''
                        total = general['total_unites']
                        lignes.append(f"    {prefixe}{general['nom']} — {total} unité{'s' if total != 1 else ''}")
                        for bloc, types in general['blocs'].items():
                            if types:
                                composition = ', '.join(formater_force({'type': t, 'nombre': n})
                                                        for t, n in sorted(types.items()))
                                label = 'arrière' if bloc == 'arriere' else bloc
                                lignes.append(f'      {label:<7} : {composition}')
            lignes.append('')
    return '\n'.join(lignes).rstrip() + '\n'


def publier_rapports_exploration(configuration, vague):
    """Remplace les deux documents depuis un même état ; les joueurs doivent être gelés."""
    photographie = lire_etat_exploration(configuration, vague)
    for joueur in configuration['joueurs']:
        fichier = configuration['game_path'] / 'village' / joueur / 'hotel_de_ville/rapport_exploration.txt'
        texte = generer_rapport_exploration(joueur, photographie)
        etat.ecrire_prive(fichier, texte)
        gid = grp.getgrnam(configuration['acteurs'][joueur]['groupe_linux']).gr_gid
        os.chown(fichier, 0, gid)
        os.chmod(fichier, 0o640)


def formater_survivants(nombre, type_unite):
    # Présente le résultat d'un bloc après le combat.

    if nombre <= 0:
        return "aucune unité survivante"

    if nombre == 1:
        return f"1 {nom_type_unite(type_unite, nombre)} survivant"

    return f"{nombre} {nom_type_unite(type_unite, nombre)} survivants"


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


def ajouter_ligne_fichier(chemin, texte):
    # Ajoute une ligne dans un fichier de rapport.
    chemin = chemin_sortie(chemin)

    chemin.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        chemin,
        "a",
        encoding="utf-8"
    ) as fichier:
        proteger_rapport(chemin)
        fichier.write(
            str(texte) + "\n"
        )


def ecrire_rapport_long(texte):
    # Rapport complet réservé au développement,
    # aux tests et au futur système de renseignement.

    ajouter_ligne_fichier(
        config.rapport_long_path,
        texte
    )


def ecrire_rapport_court(texte):
    # Rapport contenant uniquement
    # les informations publiques.

    ajouter_ligne_fichier(
        config.rapport_court_path,
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
        config.rapports_territoires_dir
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
    repertoire = _preparation.get()
    if repertoire is not None:
        # Uniquement les événements déjà destinés aux alliés. Le journal
        # technique et les ordres personnels n'entrent jamais dans ce flux.
        fichier = repertoire / 'evenements.jsonl'
        with fichier.open('a', encoding='utf-8') as sortie:
            sortie.write(json.dumps(f'[{Path(territoire).name}] {texte}\n', ensure_ascii=False) + '\n')


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


def ecrire_entete_tableau_affrontements(
    territoire,
    colonne_numero,
    camps=("j1", "j2")
):
    bordure = "+------+--------------------------+-----+--------------------------+"

    ecrire_rapport_territoire(territoire, bordure)
    ecrire_rapport_territoire(
        territoire,
        f"| {colonne_numero:<4} | {camps[0]:<24} | {'':^3} | {camps[1]:<24} |"
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
    nom_1 = resultat.get("affichage_1", resultat["general_1"])
    nom_2 = resultat.get("affichage_2", resultat["general_2"])
    if resultat.get("camp_1", resultat["joueur_1"]) != resultat["joueur_1"]:
        nom_1 = f"{resultat['joueur_1']} {nom_1}"
    if resultat.get("camp_2", resultat["joueur_2"]) != resultat["joueur_2"]:
        nom_2 = f"{resultat['joueur_2']} {nom_2}"

    gauche = (
        f"{nom_1} {symbole_1} "
        f"{resultat['initial_1']} → {resultat['final_1']}"
    )
    droite = (
        f"{nom_2} {symbole_2} "
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
        "cavalerie_lourde": "cavalier lourd",
        "vide": "vide",
    }
    pluriel = {
        "archer": "archers",
        "piquier": "piquiers",
        "cavalier": "cavaliers",
        "cavalerie_lourde": "cavaliers lourds",
        "vide": "vide",
    }

    if nombre == 1:
        return singulier.get(type_unite, type_unite)
    return pluriel.get(type_unite, type_unite)


def formater_force_rapport(nombre, type_unite):
    return f"{nombre} {nom_type_unite(type_unite, nombre)}"


def ecrire_entete_detail_blocs(territoire, joueurs=("j1", "j2")):
    bordure = (
        "+--------+-----------+---------------+-----+-----------+---------------+----------------+"
    )
    ecrire_rapport_territoire(territoire, bordure)
    ecrire_rapport_territoire(
        territoire,
        f"| Moment | {('Bloc ' + joueurs[0]):<9} | {('Unités ' + joueurs[0]):<13} "
        f"|     | {('Bloc ' + joueurs[1]):<9} | {('Unités ' + joueurs[1]):<13} | Résultat       |"
    )
    ecrire_rapport_territoire(territoire, bordure)


def ecrire_fin_detail_blocs(territoire):
    ecrire_rapport_territoire(
        territoire,
        "+--------+-----------+---------------+-----+-----------+---------------+----------------+"
    )


def ecrire_detail_choc(territoire, detail, joueurs=("j1", "j2")):
    force_1 = formater_force_rapport(detail["initial_1"], detail["type_1"])
    force_2 = formater_force_rapport(detail["initial_2"], detail["type_2"])
    resultat = f"{joueurs[0]} ({detail['final_1']}) / {joueurs[1]} ({detail['final_2']})"

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
        f"{resultat_engagement['joueur_1']} ({normalise['final_1']}) / "
        f"{resultat_engagement['joueur_2']} ({normalise['final_2']})"
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
    import catalogues
    joueurs = (resultat["joueur_1"], resultat["joueur_2"])
    nom_1 = resultat.get("affichage_1", resultat["general_1"])
    nom_2 = resultat.get("affichage_2", resultat["general_2"])
    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(
        territoire,
        f"--- Engagement {etiquette} : "
        f"{joueurs[0]} {nom_1} <-> {joueurs[1]} {nom_2} ---"
    )

    ecrire_rapport_territoire(territoire, "")
    for decision in resultat.get('ordres_v2', ()):
        noms = ', '.join(catalogues.ORDRES[i]['nom'] for i in decision['retenus'])
        ecrire_rapport_territoire(territoire,
            f"Ordres {decision['categorie']} — {decision['joueur']} {decision['general']} : "
            + (noms if noms else 'aucun ordre retenu'))
        ecrire_rapport_long(f"Confrontation V2 : {decision}")
        if decision.get('motif'):
            ecrire_rapport_territoire(territoire, decision['motif'])
    charge = resultat.get('charge_suicidaire')
    if charge:
        for numero, (active, reussite, pertes) in enumerate(zip(
                charge['activations'], charge['reussites'], charge['pertes']), 1):
            if active:
                ecrire_rapport_territoire(
                    territoire,
                    f"Charge suicidaire — {joueurs[numero - 1]} : "
                    f"{pertes} pertes prises en compte, "
                    + ('général adverse détruit.' if reussite
                       else 'tentative sans destruction adverse.'))
    ecrire_rapport_territoire(territoire, "CHOC INITIAL")
    for fuite in resultat.get('fuites', ()):
        ecrire_rapport_territoire(territoire,
            f"Choca_fuite : {fuite['joueur']} {fuite['general']} se retire vers "
            f"{fuite['destination']}, position {fuite['position']}, après le choc initial.")
    for rafale in resultat.get('rafales', ()):
        ecrire_rapport_territoire(territoire,
            f"Rafale — {rafale['joueur']} {rafale['general']} : "
            f"{rafale['tirs']} tirs, {rafale['touches']} cibles, {rafale['pertes']} pertes après moral.")
    ecrire_rapport_territoire(territoire, "")

    if resultat["chocs"]:
        ecrire_entete_detail_blocs(territoire, joueurs)
        for detail in resultat["chocs"]:
            ecrire_detail_choc(territoire, detail, joueurs)
        ecrire_fin_detail_blocs(territoire)
    else:
        ecrire_rapport_territoire(territoire, "Aucun choc direct entre blocs.")

    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(territoire, "MANŒUVRE")
    ecrire_rapport_territoire(territoire, "")

    if resultat["manoeuvres"]:
        ecrire_entete_detail_blocs(territoire, joueurs)
        for detail in resultat["manoeuvres"]:
            ecrire_detail_manoeuvre(territoire, resultat, detail)
        ecrire_fin_detail_blocs(territoire)
    else:
        ecrire_rapport_territoire(territoire, "Aucune manœuvre.")

    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(
        territoire,
        f"Résultat : {joueurs[0]} {nom_1} "
        f"{resultat['initial_1']} → {resultat['final_1']} | "
        f"{joueurs[1]} {nom_2} "
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


def preparer_rapports(configuration=None):
    # Prépare tous les rapports du nouveau tour.
    #
    # Les rapports du tour précédent sont effacés.
    # Une nouvelle météo est ensuite générée.

    global meteo_tour
    global territoire_rapport_actuel

    territoire_rapport_actuel = None

    chemin_sortie(config.rapport_dir).mkdir(
        parents=True,
        exist_ok=True
    )

    chemin_sortie(config.rapports_territoires_dir).mkdir(
        parents=True,
        exist_ok=True
    )

    # Effacer les rapports généraux.
    vider_rapport(config.rapport_court_path)

    vider_rapport(config.rapport_long_path)

    # Préparer un rapport pour chaque territoire.
    territoires = config.territoires if configuration is None else configuration["territoires"]
    for territory in territoires:
        chemin = chemin_rapport_territoire(
            territory
        )

        vider_rapport(chemin)

    # Générer la météo commune au tour.
    meteo_tour = etat.choisir_meteo_tour()

    etat.sauvegarder_meteo(
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


def afficher_fin_de_tour(configuration=None):
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

    if config.rapport_court_path.exists():
        contenu = config.rapport_court_path.read_text(
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
        f"cat {config.rapport_long_path}"
    )

    print()

    print("Exemple de rapport territorial :")
    exemple = ('terrain1' if configuration is None or configuration['mode'] == 'classique'
               else configuration['territoires'][0].name)
    print(
        "cat "
        f"{config.rapports_territoires_dir / (exemple + '.txt')}"
    )

    print()

    print("Liste des rapports territoriaux :")
    print(
        f"ls {config.rapports_territoires_dir}/"
    )

    print()
