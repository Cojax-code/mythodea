"""Écriture, formatage et affichage des rapports du tour."""
from pathlib import Path
import os
import grp
import json
import stat
import re
import uuid
import hashlib
from contextlib import contextmanager
from contextvars import ContextVar

import config
import etat


territoire_rapport_actuel = None
meteo_tour = None
_groupe_lecture = ContextVar('groupe_lecture_rapports', default=None)
_preparation = ContextVar('preparation_privee_rapports', default=None)
_vague = ContextVar('vague_rapports', default=None)
_tableaux = {}


@contextmanager
def preparation_privee(repertoire):
    """Les sorties d'une résolution ne deviennent visibles qu'à publication."""
    from cycle_linux import dossier_prive
    dossier_prive(repertoire)
    jeton = _preparation.set(repertoire)
    vague = _vague.set(None)
    try:
        yield
    finally:
        _preparation.reset(jeton)
        _vague.reset(vague)


def chemin_sortie(chemin):
    repertoire = _preparation.get()
    if repertoire and chemin == config.rapport_long_path:
        return repertoire / 'archives.log'
    return repertoire / chemin.relative_to(config.rapport_dir) if repertoire else chemin



def preparer_activites(configuration, tour):
    """Crée un rapport privé neuf pour chaque joueur dans la génération du tour."""
    for joueur in configuration['joueurs']:
        chemin = configuration['game_path'] / 'village' / joueur / 'hotel_de_ville/rapport_activites.txt'
        etat.ecrire_prive(chemin, f"=== RAPPORT D'ACTIVITÉS — VAGUE {tour + 1} (TOUR {tour}) ===\n\n")
        ancien = chemin.parent.parent / chemin.name
        from cycle_linux import sans_liens
        sans_liens(ancien)
        if ancien.exists():
            ancien.unlink()


def noter_activite(configuration, joueur, categorie, message):
    """Ajoute un résultat officiel au rapport de son seul propriétaire."""
    if joueur not in configuration['joueurs']:
        raise ValueError('Joueur inconnu pour le rapport personnel.')
    if not categorie or not message or any(c in categorie for c in '\n\r'):
        raise ValueError('Notification d’activité invalide.')
    chemin = configuration['game_path'] / 'village' / joueur / 'hotel_de_ville/rapport_activites.txt'
    from cycle_linux import sans_liens
    sans_liens(chemin)
    if not chemin.is_file() or chemin.stat().st_nlink != 1:
        raise RuntimeError('Rapport d’activités personnel absent ou invalide.')
    ligne = f"[{texte_notification(categorie)}] {texte_notification(message)}"
    if ligne in chemin.read_text(encoding='utf-8').splitlines():
        return
    fd = os.open(chemin, os.O_WRONLY | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0)
                 | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'a', encoding='utf-8') as fichier:
        infos = os.fstat(fichier.fileno())
        if not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1:
            raise RuntimeError('Rapport personnel non ordinaire ou lié.')
        fichier.write(f"[{texte_notification(categorie)}] {texte_notification(message)}\n\n")
    archiver_evenement(categorie, joueur=joueur, message=texte_notification(message))


def texte_notification(texte):
    """Aucun contrôle de terminal provenant d'un nom ou d'une demande joueur."""
    return ''.join(c if c.isprintable() else ' ' for c in str(texte))


def noter_resultat(joueur, categorie, message, configuration=None):
    """Sortie facultative des API communes, exclusivement pendant la résolution.

    Les appels isolés/classiques sans rapport préparé gardent leur comportement.
    Aucun événement ne modifie le dernier rapport publié pendant ACTIONS.
    """
    c = configuration if configuration is not None else dict(
        game_path=config.racine_metier(), joueurs=config.joueurs)
    if joueur not in c['joueurs']:
        return
    cycle = etat.charger_cycle_survie(c)
    if cycle is None and _preparation.get() is not None:
        archiver_evenement(categorie, joueur=joueur, message=texte_notification(message))
        return
    if not cycle or cycle['phase'] != 'resolution':
        return
    chemin = c['game_path'] / 'village' / joueur / 'hotel_de_ville/rapport_activites.txt'
    if chemin.exists():
        noter_activite(c, joueur, categorie, message)


def noter_progression(general, avant, apres, origine, recompense=None):
    details = [f"{general['nom']} : origine {origine}"]
    if origine in ('formation', 'combat'):
        import progression
        details.append(f"+1 point d'expérience (XP {origine}) ; progression {apres['progression_' + origine]}/{progression.SEUILS[origine]}")
    if apres['niveau'] != avant['niveau']:
        details.append(f"niveau {apres['niveau']} gagné ({avant['niveau']} → {apres['niveau']})")
        details.append(f"orientation {apres['nature']}")
    if apres.get('emplacements_etiquettes_actives', 1) > avant.get('emplacements_etiquettes_actives', 1):
        details.append(f"{apres['emplacements_etiquettes_actives']} emplacement(s) d’étiquettes actives débloqué(s)")
    if apres.get('niveau_etendard', 0) > avant.get('niveau_etendard', 0):
        details.append(decrire_recompense(('etendard', apres['niveau_etendard'])))
    bilan = apres.get('dernier_niveau') if apres['niveau'] != avant['niveau'] else None
    if bilan:
        gains = bilan['gains_naturels']
        details.append(f"gains naturels : PC +{gains['points_commandement']}, moral +{gains['moral']}")
    for cle, libelle in (('points_commandement', 'PC'), ('moral', 'moral')):
        gain = apres[cle] - avant[cle]
        if gain:
            details.append(f"total {libelle} {gain:+d} ({avant[cle]} → {apres[cle]})")
    for nom, rang in apres.get('etiquettes', {}).items():
        if rang != avant.get('etiquettes', {}).get(nom):
            details.append(f"étiquette {nom}, niveau {rang}")
    for evolution in apres['evolutions_acquises']:
        if evolution not in avant['evolutions_acquises']:
            details.append(f"évolution {evolution} obtenue")
    if bilan:
        details.append(f"récompense classique : {decrire_recompense(bilan['classique'])}")
        if bilan['supplementaire'] is not None:
            details.append(f"récompense supplémentaire : {decrire_recompense(bilan['supplementaire'])}")
        if bilan['basculement']:
            details.append(f"basculement automatique : {bilan['basculement']}")
    elif recompense:
        details.append(f"récompense {recompense[0]} : {recompense[1]}" if isinstance(recompense, (tuple, list))
                       else f"récompense évolution {recompense}")
    noter_resultat(general['joueur'], 'CASERNE MILITAIRE' if origine == 'formation'
                  else 'PROGRESSION', '; '.join(details) + '.')


def decrire_recompense(recompense):
    if not isinstance(recompense, (tuple, list)):
        return f'évolution {recompense}'
    nom, valeur = recompense
    if nom == 'etendard':
        return 'capacité étendard royal débloquée' if valeur == 2 else 'capacité étendard débloquée'
    if nom == 'emplacement_actif':
        return f'emplacement actif débloqué ({valeur} au total)'
    return f'{nom} : {valeur}'


def noter_incident_general(chemin, message):
    """Même convention de propriétaire que les profils des généraux du moteur."""
    joueurs = [j for j in config.joueurs if j in chemin.parts]
    if len(joueurs) == 1:
        noter_resultat(joueurs[0], 'INCIDENTS', f'{chemin.name} : {message}')


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
    fichiers = ['rapport_court.txt',
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
        reinitialiser_suivi(configuration, gid, precedent, plan)
        return  # Ne réinitialiser ni le point de départ ni le journal à la reprise.
    evenements = [f"=== TOUR {json.loads((generation / 'resultat.json').read_text())['tour']} ===\n"]
    prepares = [json.loads(ligne) for ligne in
                (source / 'evenements.jsonl').read_text(encoding='utf-8').splitlines()]
    combats = {ligne.split(']', 1)[0] for ligne in prepares if '--- Engagement ' in ligne}
    evenements.extend(ligne for ligne in prepares if ligne.split(']', 1)[0] in combats)
    duree = 0 if defaite else configuration['duree_consultation_secondes']
    intervalle = min(intervalle, duree / max(1, len(evenements) - 1))
    with ouvrir_suivi(configuration, gid) as fichier:
        infos = os.fstat(fichier.fileno())
        donnees = dict(generation=generation.name, debut=debut, intervalle=intervalle,
                       position=0, device=infos.st_dev, inode=infos.st_ino,
                       reinitialiser=True, evenements=evenements)
    # Le plan et son étape d'initialisation sont durables avant le premier append.
    # les octets déjà écrits font foi, même après une écriture partielle.
    etat.ecrire_prive(plan, json.dumps(donnees, ensure_ascii=False) + '\n')
    reinitialiser_suivi(configuration, gid, donnees, plan)


def reinitialiser_suivi(configuration, gid, donnees, plan):
    if donnees.get('reinitialiser'):
        # Le plan durable précède la troncature. Une interruption dans cette
        # étape peut la répéter : aucun événement n'est encore diffusé.
        with ouvrir_suivi(configuration, gid) as fichier:
            infos = os.fstat(fichier.fileno())
            if (infos.st_dev, infos.st_ino) != (donnees['device'], donnees['inode']):
                raise RuntimeError('Journal de combat remplacé : récupération requise.')
            fichier.truncate(0)
            fichier.flush()
            os.fsync(fichier.fileno())
        donnees['reinitialiser'] = False
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
    reinitialiser_suivi(configuration, gid, donnees, plan)
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
    technique = _preparation.get() is not None or chemin.name == 'archives.log'
    if gid is not None or technique:
        os.chown(chemin, 0, 0 if technique else gid)
        os.chmod(chemin, 0o600 if technique else 0o640)


def vider_rapport(chemin):
    """Garde l'inode pour les lecteurs tail ; privé dès la création."""
    chemin = chemin_sortie(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
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
                    sans_liens(generaux.chemin_info(general, 'fiche.txt'))
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


def archiver_evenement(categorie, **champs):
    """JSON par ligne : les valeurs et retours à la ligne restent délimitables."""
    donnees = dict(vague=_vague.get(), categorie=categorie, **champs)
    ajouter_ligne_fichier(config.rapport_long_path,
                         json.dumps(donnees, ensure_ascii=False))


def ecrire_rapport_long(texte):
    """API technique commune conservée pour les adaptateurs du simulateur."""
    for ligne in str(texte).split('\n'):
        archiver_evenement('TECHNIQUE', territoire=territoire_rapport_actuel, message=ligne)


def publier_archives(configuration, generation):
    """Valide un bloc entier par remplacement atomique sous le verrou du cycle.

    Le contenu déjà installé est le reçu : aucune fenêtre append/curseur.
    La reprise de la même génération est sans effet ; une divergence est refusée.
    """
    from cycle_linux import sans_liens
    resultat = json.loads((generation / 'resultat.json').read_text(encoding='utf-8'))
    if not resultat.get('resolution_terminee'):
        raise RuntimeError('Archives refusées : résolution incomplète.')
    vague = resultat['tour'] + 1
    source = generation / 'rapports/archives.log'
    sans_liens(source)
    lignes = source.read_text(encoding='utf-8').splitlines()
    for ligne in lignes:
        if json.loads(ligne)['vague'] != vague:
            raise RuntimeError('Vague incohérente dans les archives préparées.')
    debut, fin = f'=== VAGUE {vague} DEBUT ===\n', f'=== VAGUE {vague} FIN ===\n'
    bloc = (debut + json.dumps(dict(vague=vague, categorie='VALIDATION',
             generation=generation.name), ensure_ascii=False) + '\n'
             + '\n'.join(lignes) + '\n' + fin)
    destination = configuration['game_path'] / '.systeme/archives.log'
    sans_liens(destination)
    if destination.exists() and (not destination.is_file() or destination.stat().st_nlink != 1):
        raise RuntimeError('Archives non ordinaires ou liées.')
    ancien = destination.read_text(encoding='utf-8') if destination.exists() else ''
    if debut in ancien:
        present = debut + ancien.split(debut, 1)[1].split(fin, 1)[0] + fin
        if present != bloc or fin not in ancien:
            raise RuntimeError('Archives divergentes : récupération requise.')
        return
    etat.ecrire_prive(destination, ancien + bloc)


def migrer_anciens_rapports(configuration):
    """Seules références aux anciens fichiers : retrait lors d'une mise à jour."""
    from cycle_linux import sans_liens
    racine = configuration['game_path']
    ancien = racine / 'rapport/rapport_long.txt'
    sans_liens(ancien)
    if ancien.exists():
        if not ancien.is_file() or ancien.stat().st_nlink != 1 or ancien.stat().st_uid != 0:
            raise RuntimeError('Ancien journal technique non sûr : intervention requise.')
        contenu = ancien.read_text(encoding='utf-8')
        empreinte = hashlib.sha256(contenu.encode('utf-8')).hexdigest()
        destination = racine / '.systeme/archives.log'
        sans_liens(destination)
        precedent = destination.read_text(encoding='utf-8') if destination.exists() else ''
        marqueur = json.dumps(dict(vague=None, categorie='MIGRATION', sha256=empreinte), ensure_ascii=False)
        if marqueur not in precedent.splitlines():
            lignes = [json.dumps(dict(vague=None, categorie='TECHNIQUE_HISTORIQUE', message=ligne),
                                 ensure_ascii=False) for ligne in contenu.splitlines()
                      if not re.search(r'm[ée]t[ée]o', ligne, re.I)]
            etat.ecrire_prive(destination, precedent + marqueur + '\n' + '\n'.join(lignes) + '\n')
        ancien.unlink()
    for nom in ('etat_tour.txt', 'suivi_tour.log'):
        chemin = racine / 'village/clocher' / nom
        sans_liens(chemin)
        if chemin.exists():
            if not chemin.is_file() or chemin.stat().st_nlink != 1:
                raise RuntimeError('Ancien état du tour non ordinaire ou lié.')
            chemin.unlink()
    for joueur in configuration.get('joueurs', ()):
        ancien = racine / 'village' / joueur / 'rapport_activites.txt'
        sans_liens(ancien)
        if ancien.exists():
            destination = ancien.parent / 'hotel_de_ville' / ancien.name
            sans_liens(destination)
            if not ancien.is_file() or ancien.stat().st_nlink != 1:
                raise RuntimeError('Ancien rapport personnel non ordinaire ou lié.')
            if not destination.exists():
                etat.ecrire_prive(destination, ancien.read_text(encoding='utf-8'))
                gid = grp.getgrnam(configuration['acteurs'][joueur]['groupe_linux']).gr_gid
                os.chown(destination, 0, gid)
                os.chmod(destination, 0o640)
            ancien.unlink()
        # Les conseils déjà distribués gardent leurs textes, sauf les chemins
        # devenus inutilisables. Le modèle courant remplace ces seuls conseils.
        hotel = racine / 'village' / joueur / 'hotel_de_ville'
        for nom in ('journal_du_Toonitruand', 'journal_du_veteran'):
            for numero in (0, 2):
                document = hotel / nom / f'vague_{numero}.txt'
                sans_liens(document)
                if not document.exists():
                    continue
                contenu = document.read_text(encoding='utf-8')
                if not any(ancien in contenu for ancien in ('etat_tour.txt', 'suivi_tour.log')):
                    continue
                modele = Path(__file__).resolve().parent / 'textes' / nom / document.name
                public = configuration.get('game_public_path', config.game_public_path)
                texte = modele.read_text(encoding='utf-8').replace('{joueur}', joueur).replace('{game_path}', str(public))
                etat.ecrire_prive(document, '\n' + texte)
                gid = grp.getgrnam(configuration['acteurs'][joueur]['groupe_linux']).gr_gid
                os.chown(document, 0, gid)
                os.chmod(document, 0o640)


def archiver_etat_final(configuration, vague):
    photographie = lire_etat_exploration(configuration, vague)
    for territoire in photographie['territoires']:
        archiver_evenement('ETAT_FINAL', territoire=territoire['nom'], etat=territoire)


@contextmanager
def archives_classiques():
    """Prépare les sorties classiques avant de valider leur bloc administratif."""
    from cycle_linux import dossier_prive, sans_liens
    import fcntl
    systeme = config.game_path / '.systeme'
    dossier_prive(systeme)
    verrou = systeme / 'verrou_archives_classiques'
    sans_liens(verrou)
    fd = os.open(verrou, os.O_WRONLY | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        migrer_anciens_rapports(config.configuration_mode('classique'))
        archive = config.rapport_long_path
        sans_liens(archive)
        ancien = archive.read_text(encoding='utf-8') if archive.exists() else ''
        tour = max(map(int, re.findall(r'^=== VAGUE (\d+) FIN ===$', ancien, re.M)), default=0)
        generation = systeme / 'generations' / f'c{tour:06}-{uuid.uuid4().hex[:12]}'
        dossier_prive(generation.parent)
        dossier_prive(generation)
        with preparation_privee(generation / 'rapports'):
            _vague.set(tour + 1)
            yield
            archiver_etat_final(config.configuration_mode('classique'), tour + 1)
        etat.ecrire_prive(generation / 'resultat.json', json.dumps(dict(
            tour=tour, resolution_terminee=True)))
        for source in (generation / 'rapports').rglob('*.txt'):
            destination = config.rapport_dir / source.relative_to(generation / 'rapports')
            etat.ecrire_prive(destination, source.read_text(encoding='utf-8'))
            os.chmod(destination, 0o644)
        publier_archives(dict(game_path=config.game_path), generation)
    finally:
        os.close(fd)


def ecrire_rapport_court(texte):
    # Rapport contenant uniquement
    # les informations publiques.

    ajouter_ligne_fichier(
        config.rapport_court_path,
        texte
    )
    archiver_evenement('RESUME', message=str(texte))


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

    tableau = _tableaux.get(Path(territoire).name)
    if tableau and tableau['ouvert']:
        tableau['lignes'].append(texte)
        return
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
    # - les archives administratives ;
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
    # dans les archives administratives. Le rapport territorial est
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
    _tableaux[Path(territoire).name] = dict(ouvert=True, lignes=[],
        cellules=[(str(colonne_numero), str(camps[0]), '', str(camps[1]))])


def largeur_visible(texte):
    import unicodedata
    texte = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', str(texte))
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ('W', 'F')
               else 1 for c in texte)


def ecrire_fin_tableau_affrontements(territoire):
    tableau = _tableaux[Path(territoire).name]
    cellules = [tuple(re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', str(t)) for t in ligne)
                for ligne in tableau['cellules']]
    largeurs = [max(minimum, *(largeur_visible(l[i]) for l in cellules))
                for i, minimum in enumerate((4, 24, 3, 24))]
    bordure = '+' + '+'.join('-' * (n + 2) for n in largeurs) + '+'
    lignes = [bordure]
    for i, cellule in enumerate(cellules):
        lignes.append('| ' + ' | '.join(str(t) + ' ' * (n - largeur_visible(t))
                                         for t, n in zip(cellule, largeurs)) + ' |')
        if i == 0:
            lignes.append(bordure)
    lignes.append(bordure)
    tableau['lignes'] = lignes if len(cellules) > 1 else []
    tableau['ouvert'] = False


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

    tableau = _tableaux.get(Path(territoire).name)
    if tableau:
        tableau['cellules'].append((str(etiquette), gauche, '<->', droite))
    else:
        # API isolée : une ligne reste lisible sans ouvrir un tableau complet.
        ecrire_rapport_territoire(territoire, f'| {etiquette} | {gauche} | <-> | {droite} |')


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
    joueurs = (resultat["joueur_1"], resultat["joueur_2"])
    nom_1 = resultat.get("affichage_1", resultat["general_1"])
    nom_2 = resultat.get("affichage_2", resultat["general_2"])
    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(
        territoire,
        f"--- Engagement {etiquette} : "
        f"{joueurs[0]} {nom_1} <-> {joueurs[1]} {nom_2} ---"
    )
    ecrire_rapport_territoire(territoire,
        f"Forces initiales : {joueurs[0]} {resultat['initial_1']} | {joueurs[1]} {resultat['initial_2']}")
    archiver_evenement('COMBAT', territoire=Path(territoire).name,
                      engagement=etiquette, resultat=resultat)

    ecrire_rapport_territoire(territoire, "")
    ecrire_rapport_territoire(territoire, "CHOC INITIAL")
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
        tableau = _tableaux.pop(Path(territoire).name, None)
        if tableau:
            for ligne in tableau['lignes']:
                ecrire_rapport_territoire(territoire, ligne)
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
    tableau = _tableaux.pop(Path(territoire).name, None)
    if tableau:
        ecrire_rapport_territoire(territoire, 'RÉCAPITULATIF DES AFFRONTEMENTS')
        for ligne in tableau['lignes']:
            ecrire_rapport_territoire(territoire, ligne)


def preparer_rapports(configuration=None):
    """Renouvelle tous les rapports joueurs ; la météo reste strictement interne."""
    global meteo_tour, territoire_rapport_actuel
    territoire_rapport_actuel = None
    _tableaux.clear()
    cycle = etat.charger_cycle_survie(configuration) if configuration is not None else None
    if cycle:
        _vague.set(cycle['tour'] + 1)
    chemin_sortie(config.rapport_dir).mkdir(parents=True, exist_ok=True)
    chemin_sortie(config.rapports_territoires_dir).mkdir(parents=True, exist_ok=True)
    vider_rapport(config.rapport_court_path)
    # Ce fichier est un fragment privé ; le cumul n'est écrit qu'à validation.
    vider_rapport(config.rapport_long_path)
    if _preparation.get():
        etat.ecrire_prive(_preparation.get() / 'evenements.jsonl', '')
    territoires = config.territoires if configuration is None else configuration['territoires']
    for territoire in territoires:
        vider_rapport(chemin_rapport_territoire(territoire))
        ecrire_rapport_territoire(territoire, f"=== RAPPORT DE {territoire.name.upper()} ===")
        ecrire_rapport_territoire(territoire, '')
    meteo_tour = etat.choisir_meteo_tour()
    etat.sauvegarder_meteo(meteo_tour)
    ecrire_rapport_court('=== RÉSUMÉ DU TOUR ===')
    ecrire_rapport_court('')
    archiver_evenement('DEBUT_RESOLUTION')


def commandes_consultation(configuration):
    racine = configuration['game_path']
    hotel = f'{racine}/village/$USER/hotel_de_ville'
    return ("=== CONSULTATION DES RAPPORTS ===\n\n"
            "Rapports personnels :\n"
            f"Rapport court : cat {hotel}/rapport.txt\n"
            f"Activités : cat {hotel}/rapport_activites.txt\n"
            f"Exploration : cat {hotel}/rapport_exploration.txt\n\n"
            "Rapports de combat :\n"
            f"Combats détaillés : cat {racine}/rapport/territoires/est_1.txt\n"
            f"Lecture à la demande : replay {racine}/rapport/territoires/est_1.txt\n"
            f"Journal progressif : tail -f {racine}/rapport/suivi_combats.log\n\n"
            "État du tour :\n"
            f"État actuel : cat {racine}/village/clocher/etat_tour.log\n"
            f"Suivi : watch -n 1 cat {racine}/village/clocher/etat_tour.log")


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

    if configuration is not None and configuration['mode'] == 'survie':
        print(commandes_consultation(configuration))
    else:
        print(f"Combats détaillés : cat {config.rapports_territoires_dir / 'terrain1.txt'}")
        print(f"Liste des rapports : ls {config.rapports_territoires_dir}/")
    print()
