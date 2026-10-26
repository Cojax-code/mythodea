"""État privé des soldats et copies lisibles dans leurs dossiers individuels."""
import json
import os
from pathlib import Path
import random
import stat
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from fractions import Fraction
from dataclasses import dataclass


_participants = ContextVar('soldats_bataille_complete', default=None)
_generaux_engages = ContextVar('generaux_bataille_complete', default=None)
_bataille = ContextVar('identite_bataille_complete', default=None)
_prets = ContextVar('soldats_participation_temporaire', default=frozenset())


@dataclass(frozen=True)
class SoldatParticipant:
    """Référence au soldat réel, jamais une copie de ses blessures ou de son XP."""
    identifiant: str
    joueur: str
    general: str
    bloc: str
    chemin: Path
    type_unite: str
    device: int
    inode: int


def _controler_dossier_participant(chemin):
    # API interne à utiliser sous gel ou dans la génération privée. Comme les
    # autres lectures métier, ce contrôle n'est pas un verrou contre un écrivain.
    for parent in (chemin, *chemin.parents):
        if parent.is_symlink():
            raise RuntimeError('Lien interdit dans une participation temporaire.')
    if not chemin.is_dir():
        raise RuntimeError('Dossier de soldat absent ou non ordinaire.')
    for enfant in chemin.rglob('*'):
        infos = enfant.lstat()
        if not (stat.S_ISDIR(infos.st_mode) or
                (stat.S_ISREG(infos.st_mode) and infos.st_nlink == 1)):
            raise RuntimeError('Objet lié ou non ordinaire dans un soldat participant.')
    return chemin.stat()


class GroupeTemporaire:
    """Vue interne de soldats explicitement sélectionnés, sans politique tactique.

    Les dossiers restent chez leur général d'origine. Les pertes/blessures
    réelles passent par le moteur existant ; fermer la vue ne les restaure pas.
    Cette classe ne sélectionne ni donneur, camp, phase, victime, moral ou fatigue.
    """
    def __init__(self, participants, racine):
        self.participants = tuple(participants)
        self._racine = racine
        self._ouvert = True

    def bilan(self):
        """Relit les états réels, regroupés par (joueur, général, bloc d'origine).

        Un disparu sans décès officiel ou un soldat remplacé déclenche une
        erreur ; aucune restitution ne crée implicitement un nouveau soldat.
        """
        import config
        import generaux
        if not self._ouvert or config.racine_metier() != self._racine:
            raise RuntimeError('Participation temporaire fermée ou hors génération.')
        registre = charger()
        resultat = {}
        for p in self.participants:
            valeur = registre.get(p.identifiant)
            if valeur is None or valeur['chemin'] != cle(p.chemin):
                raise RuntimeError('Origine officielle du participant modifiée ou absente.')
            groupe = resultat.setdefault((p.joueur, p.general, p.bloc),
                                         dict(survivants=[], pertes=[]))
            if valeur.get('detruit'):
                if p.chemin.exists() or p.chemin.is_symlink():
                    raise RuntimeError('Un soldat détruit possède encore un dossier.')
                groupe['pertes'].append(p)
                continue
            infos = _controler_dossier_participant(p.chemin)
            if ((infos.st_dev, infos.st_ino) != (p.device, p.inode)
                    or retrouver(p.chemin, registre, config.dans_generation_privee()) != p.identifiant
                    or valeur['type'] != p.type_unite
                    or generaux.identifier_unite(p.chemin) != p.type_unite):
                raise RuntimeError('Identité ou type du participant modifié.')
            groupe['survivants'].append(p)
        return {origine: {etat: tuple(soldats) for etat, soldats in groupe.items()}
                for origine, groupe in resultat.items()}

    def bloc(self, identifiants=None):
        """Fournit une vue homogène de la sélection explicite encore vivante.

        Aucun type majoritaire, plafonnement ou partage des pertes n'est choisi.
        Le résultat est compatible avec soldats.pertes ; son moral et ses pertes
        doivent être décidés par une règle validée, hors de cette API préparatoire.
        """
        bilan = self.bilan()
        selection = tuple(p.identifiant for p in self.participants) if identifiants is None else tuple(identifiants)
        connus = {p.identifiant for p in self.participants}
        if len(set(selection)) != len(selection) or not set(selection) <= connus:
            raise ValueError('Sélection dupliquée ou étrangère au groupe temporaire.')
        vivants = {p.identifiant: p for groupe in bilan.values() for p in groupe['survivants']}
        presents = [vivants[i] for i in selection if i in vivants]
        types = {p.type_unite for p in presents}
        if len(types) > 1:
            raise ValueError('Composition mixte : aucune règle de fusion implicite.')
        return dict(type=next(iter(types), 'vide'), nombre=len(presents),
                    unites=[p.chemin for p in presents])


@contextmanager
def participation_temporaire(contributions):
    """Prépare une vue depuis (général, bloc, chemins des soldats) explicites.

    Exige des soldats déjà authentifiés par la synchronisation commune. Une
    référence ne traverse pas une publication. Aucune unité, identité, copie de
    fiche, permission, compteur ou donnée persistante n'est créée/modifiée ici.
    Les droits tactiques et les limites de chaque ordre restent à l'appelant.
    Aucun ordre désactivé n'appelle cette API.
    """
    import config
    import generaux
    racine = config.racine_metier()
    registre = charger()
    participants, identifiants = [], set()
    for general, bloc, chemins in contributions:
        origine = general['chemin']
        if (bloc not in config.ordre_blocs or not origine.is_absolute()
                or '..' in origine.parts or not origine.is_relative_to(racine)
                or origine.name != general['nom']
                or generaux.numero_general_depuis_nom(origine.name) is None
                or general['joueur'] not in origine.relative_to(racine).parts[:-1]):
            raise ValueError('Origine de contribution invalide.')
        for chemin in chemins:
            if '..' in chemin.parts or chemin.parent != origine / bloc:
                raise ValueError('Soldat extérieur au bloc déclaré.')
            infos = _controler_dossier_participant(chemin)
            identifiant = retrouver(chemin, registre, config.dans_generation_privee())
            valeur = registre.get(identifiant)
            if (valeur is None or valeur['chemin'] != cle(chemin)
                    or valeur['type'] != generaux.identifier_unite(chemin)):
                raise RuntimeError('Soldat non authentifié à son origine officielle.')
            if identifiant in identifiants or identifiant in _prets.get():
                raise ValueError('Un soldat ne peut participer deux fois simultanément.')
            identifiants.add(identifiant)
            participants.append(SoldatParticipant(identifiant, general['joueur'],
                general['nom'], bloc, chemin, valeur['type'], infos.st_dev, infos.st_ino))
    groupe = GroupeTemporaire(participants, racine)
    jeton = _prets.set(_prets.get() | identifiants)
    try:
        yield groupe
    finally:
        groupe._ouvert = False
        _prets.reset(jeton)


@contextmanager
def bataille_complete(identifiant=None, configuration=None):
    """Une résolution territoriale ; les duels n'incrémentent aucun compteur."""
    participants = set()
    jeton = _participants.set(participants)
    engages = {}
    jeton_generaux = _generaux_engages.set(engages)
    jeton_bataille = _bataille.set((identifiant, configuration))
    try:
        yield
        identifiant = identifiant or 'classique:' + uuid.uuid4().hex
        if participants:
            terminer_bataille(participants, identifiant)
        import generaux
        import progression
        import etat
        for cle in sorted(engages):
            general = engages[cle]
            if (not general['chemin'].is_dir() and configuration is not None
                    and general['joueur'] in configuration['joueurs']):
                officielle = etat.charger_positions_generaux().get(':'.join(cle))
                if officielle in configuration['villages'] or officielle in {
                        t.name for t in configuration['territoires']}:
                    position, chemin = generaux.trouver_position_general(*cle, configuration)
                    if chemin is not None and position == officielle:
                        general = dict(general, chemin=chemin)
            if (general['chemin'].is_dir() and
                    any(sum(bloc.values()) for bloc in
                        generaux.lire_composition_general(general['chemin']).values())):
                progression.valider_evenement(general, 'combat', identifiant)
    finally:
        _bataille.reset(jeton_bataille)
        _generaux_engages.reset(jeton_generaux)
        _participants.reset(jeton)


def mort_general(general):
    contexte = _bataille.get()
    if contexte and contexte[1] is not None:
        import morgue
        morgue.enregistrer_mort(contexte[1], general, contexte[0])


def affrontement(general_1, general_2):
    """Appelé uniquement pour deux blocs adverses effectivement confrontés."""
    engages = _generaux_engages.get()
    if engages is not None:
        for general in (general_1, general_2):
            engages[(general['joueur'], general['nom'])] = dict(general)


def participer(general):
    import generaux
    participants = _participants.get()
    if participants is not None:
        for bloc in generaux.lire_blocs_general(general['chemin']).values():
            participants.update(bloc['unites'])
            participants.update(bloc.get('soutiens', ()))
            participants.update(bloc.get('boucliers', ()))


def limite_blessures(batailles):
    return 3 if batailles >= 10 else 2 if batailles >= 5 else 1


def charger():
    import config
    chemin = config.racine_metier() / '.systeme/soldats.json'
    return json.loads(chemin.read_text(encoding='utf-8')) if chemin.exists() else {}


def sauvegarder(donnees):
    import config
    import etat
    etat.ecrire_prive(config.racine_metier() / '.systeme/soldats.json',
                      json.dumps(donnees, ensure_ascii=False) + '\n')


def creer_dossier_unite(chemin):
    """Une création moteur appartient au propriétaire du bloc destinataire."""
    for parent in chemin.parents:
        if parent.is_symlink():
            raise RuntimeError(f'Bloc lié interdit : {chemin.parent}')
    proprietaire = chemin.parent.stat()
    chemin.mkdir(mode=0o700)
    os.chown(chemin, proprietaire.st_uid, proprietaire.st_gid)
    os.chmod(chemin, 0o700)


def ecrire_copie(chemin, texte):
    """Copie de consultation, jamais l'autorité des blessures ou des soins."""
    for p in (chemin, *chemin.parents):
        if p.is_symlink():
            raise RuntimeError(f'Métadonnée de soldat liée : {chemin}')
    if chemin.exists() and (not stat.S_ISREG(chemin.stat().st_mode) or chemin.stat().st_nlink != 1):
        raise RuntimeError(f'Métadonnée de soldat non ordinaire : {chemin}')
    parent = chemin.parent.stat()
    fd = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as fichier:
        fichier.write(texte)
    os.chown(chemin, parent.st_uid, parent.st_gid)
    os.chmod(chemin, 0o600)


def publier(unite, identifiant, donnees):
    ecrire_copie(unite / 'identifiant_soldat.txt', identifiant + '\n')
    ecrire_copie(unite / 'batailles_survecues.txt', str(donnees['batailles']) + '\n')
    ecrire_copie(unite / 'blessures.txt', str(donnees['blessures']) + '\n')
    for nom, seuil in (('veteran', 5), ('heroique', 10)):
        marqueur = unite / nom
        if donnees['batailles'] >= seuil:
            ecrire_copie(marqueur, '')
        elif marqueur.exists() or marqueur.is_symlink():
            if marqueur.is_dir() and not marqueur.is_symlink():
                raise RuntimeError(f'Marqueur de statut non ordinaire : {marqueur}')
            marqueur.unlink()


def marqueur(unite):
    chemin = unite / 'identifiant_soldat.txt'
    if chemin.is_symlink():
        raise RuntimeError('Identifiant de soldat lié interdit.')
    return chemin.read_text(encoding='utf-8').strip() if chemin.is_file() else None


def cle(unite):
    import config
    root = config.racine_metier()
    if unite.is_relative_to(root):
        return 'game/' + unite.relative_to(root).as_posix()
    for joueur in config.joueurs:
        home = config.home_generation(joueur) or Path('/home') / joueur
        if unite.is_relative_to(home):
            return f'home/{joueur}/' + unite.relative_to(home).as_posix()
    # API isolées : leur chemin absolu demeure privé dans le registre de test.
    return unite.as_posix()


def enregistrer(unite, donnees, type_unite):
    infos = unite.stat()
    identifiant = uuid.uuid4().hex
    donnees[identifiant] = dict(batailles=0, blessures=0, derniere_bataille=None, batailles_comptees=[],
                               type=type_unite, chemin=cle(unite), device=infos.st_dev, inode=infos.st_ino)
    return identifiant


def retrouver(unite, donnees, generation_privee=False):
    infos = unite.stat()
    for identifiant, valeur in donnees.items():
        if not valeur.get('detruit') and (valeur['device'], valeur['inode']) == (infos.st_dev, infos.st_ino):
            return identifiant
    # Pendant les calculs, la capture a déjà vérifié les identités originales.
    if generation_privee:
        identifiant = marqueur(unite)
        if identifiant in donnees and not donnees[identifiant].get('detruit'):
            return identifiant
    return None


def synchroniser(configuration, publication=False):
    """Sous gel : authentifie les métadonnées avant copie, ou lie les nouveaux inodes.

    Le bit publication n'est destiné qu'à la copie terminée et contrôlée par le
    moteur. Les fichiers utilisateur ne peuvent jamais déclarer ce contexte.
    """
    import config
    import generaux
    import etat
    from cycle_linux import sans_liens
    donnees = charger()
    reference = etat.charger_unites_actions(configuration) or {'generaux': {}}
    validees = {(u[0], u[1], u[-1]) for g in reference['generaux'].values()
                for u in g['unites'].values()}
    presents = set()
    observations = []
    for joueur in configuration['acteurs']:
        for zone in generaux.zones_generaux(joueur, configuration):
            parent = zone['chemin']
            if not parent.is_dir():
                continue
            for general in parent.iterdir():
                if not general.is_dir() or generaux.numero_general_depuis_nom(general.name) is None:
                    continue
                for bloc in config.ordre_blocs:
                    if not (general / bloc).is_dir():
                        continue
                    for unite in (general / bloc).iterdir():
                        sans_liens(unite)
                        type_unite = generaux.identifier_unite(unite)
                        if type_unite == 'inconnu':
                            continue
                        observations.append((unite, type_unite,
                                             retrouver(unite, donnees, publication)))
    # Les identités reconnues par inode passent avant les copies revendiquant le
    # même marqueur : une copie ne peut jamais guérir l'original ou lui voler son état.
    observations.sort(key=lambda observation: observation[2] is None)
    for unite, type_unite, identifiant in observations:
        candidat = marqueur(unite)
        infos = unite.stat()
        if identifiant is None:
            ancien = donnees.get(candidat)
            if (ancien and not ancien.get('detruit') and candidat not in presents
                    and ancien['device'] != infos.st_dev and ancien['type'] == type_unite):
                identifiant = candidat
            elif ancien:
                # Une copie ne reçoit aucun statut de l'original. Les effectifs,
                # identités de généraux et sanctions restent soumis à l'audit commun.
                identifiant = enregistrer(unite, donnees, type_unite)
        if identifiant in presents:
            identifiant = enregistrer(unite, donnees, type_unite)
        if identifiant is None:
            # Les mêmes generalN existent chez plusieurs joueurs : le nom seul
            # ne permet jamais de conclure à un déplacement entre systèmes de fichiers.
            identite_general = unite.parent.parent.name
            joueur = next((p.name for p in unite.parents if p.name in configuration['acteurs']), None)
            if any(i not in presents and not v.get('detruit') and v['type'] == type_unite and
                   v['device'] != infos.st_dev and identite_general in Path(v['chemin']).parts
                   and joueur in Path(v['chemin']).parts
                   for i, v in donnees.items()):
                raise RuntimeError('Transfert sans identité de soldat : récupération explicite requise.')
            if publication or (infos.st_dev, infos.st_ino, type_unite) in validees:
                identifiant = enregistrer(unite, donnees, type_unite)
            else:
                continue
        presents.add(identifiant)
        valeur = donnees[identifiant]
        infos = unite.stat()
        valeur.update(chemin=cle(unite), device=infos.st_dev, inode=infos.st_ino)
        publier(unite, identifiant, valeur)
    # Garder les soldats absents pour ne jamais accepter un ancien état comme neuf.
    sauvegarder(donnees)


def pertes(infos, survivants, moral=0, aleatoire=None):
    """Sélection collective puis sauvetages distincts, sans réattribuer un échec."""
    import config
    import generaux
    import shutil
    import unites
    aleatoire = random if aleatoire is None else aleatoire
    if (type(moral) is not int and not isinstance(moral, Fraction)) or not 0 <= moral <= 100:
        raise ValueError('Moral entier de 0 à 100 requis.')
    nombre_pertes = infos['nombre'] - survivants
    if nombre_pertes <= 0:
        return []
    perdus = aleatoire.sample(infos['unites'], nombre_pertes)
    tentatives = aleatoire.sample(perdus, nombre_pertes * moral // 100) if moral else []
    donnees = charger()
    supprimes = []
    for unite in perdus:
        identifiant = retrouver(unite, donnees, config.dans_generation_privee())
        if identifiant is None and unite in tentatives:
            identifiant = enregistrer(unite, donnees, generaux.identifier_unite(unite))
        valeur = donnees.get(identifiant)
        if (unite in tentatives and valeur['blessures'] <
                unites.blessures_max(valeur['type'], valeur['batailles'])):
            valeur['blessures'] += 1
            publier(unite, identifiant, valeur)
        else:
            supprimes.append(f"{unite.name} ({infos['type']})")
            shutil.rmtree(unite)
            if valeur is not None:
                valeur['detruit'] = True
    infos['unites'] = [u for u in infos['unites'] if u.exists()]
    infos['nombre'] = len(infos['unites'])
    if infos['nombre'] == 0 and not any(u.exists() for u in infos.get('boucliers', ())):
        for unite in infos.get('soutiens', ()):
            identifiant = retrouver(unite, donnees, config.dans_generation_privee())
            if unite.exists():
                shutil.rmtree(unite)
            if identifiant in donnees:
                donnees[identifiant]['detruit'] = True
            supprimes.append(f'{unite.name} (messager_du_QG)')
        if 'soutiens' in infos:
            infos['soutiens'] = []
    if donnees:
        sauvegarder(donnees)
    return supprimes


def terminer_bataille(unites, identifiant_bataille):
    """Le pilote fournit une identité de bataille complète, stable à la reprise."""
    import config
    import generaux
    if not identifiant_bataille:
        raise ValueError('Identifiant de bataille complète requis.')
    donnees = charger()
    for unite in set(unites):
        if not unite.is_dir():
            continue
        identifiant = retrouver(unite, donnees, config.dans_generation_privee())
        if identifiant is None:
            identifiant = enregistrer(unite, donnees, generaux.identifier_unite(unite))
        valeur = donnees[identifiant]
        if identifiant_bataille not in valeur.setdefault('batailles_comptees', []):
            valeur['batailles'] += 1
            valeur['derniere_bataille'] = identifiant_bataille
            valeur['batailles_comptees'].append(identifiant_bataille)
        publier(unite, identifiant, valeur)
    sauvegarder(donnees)
