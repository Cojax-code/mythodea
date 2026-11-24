"""Déclarations de bloc et protections individuelles d'une guerre de territoire.

L'instantané reste en mémoire dans la résolution privée. Les fichiers joueurs
ne portent ni type, ni compteur de protection, ni capacité officielle.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import stat
import random

import catalogues
import config
import progression


_guerre = ContextVar('etendards_guerre', default=None)


def declaration_valide(chemin):
    if any(parent.is_symlink() for parent in chemin.parents):
        raise ValueError(f'Étendard sous un dossier lié interdit : {chemin}')
    try:
        info = chemin.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError(f'Étendard lié ou non ordinaire interdit : {chemin}')
    return True


def declaration(general):
    """Validation sans nettoyage ni lecture du contenu libre du marqueur."""
    chemin = general['chemin']
    if declaration_valide(chemin / 'etendard.txt'):
        raise ValueError('L’étendard doit être placé dans un bloc du général.')
    blocs = [bloc for bloc in config.ordre_blocs
             if declaration_valide(chemin / bloc / 'etendard.txt')]
    if len(blocs) > 1:
        raise ValueError('Un seul étendard est autorisé par général.')
    if not blocs:
        return None
    fiche = progression.charger().get(f"{general['joueur']}:{general['nom']}")
    niveau = fiche.get('niveau_etendard', 0) if fiche else 0
    if (not fiche or fiche.get('etat_zombie') or
            progression.orientation_principale(fiche) not in ('instinctif', 'hybride') or
            type(niveau) is not int or niveau not in (1, 2)):
        raise ValueError('Étendard sans capacité officielle compatible débloquée.')
    return blocs[0], niveau


@contextmanager
def guerre():
    """Imbriquer des phases ne renouvelle jamais les protections territoriales."""
    if _guerre.get() is not None:
        yield
        return
    jeton = _guerre.set({})
    try:
        yield
    finally:
        _guerre.reset(jeton)


def figer(general):
    contexte = _guerre.get()
    if contexte is None:
        return None
    identite = (general['joueur'], general['nom'])
    if identite not in contexte:
        import rapports
        contexte[identite] = None
        try:
            choix = declaration(general)
        except ValueError as erreur:
            message = f"{general['joueur']}/{general['nom']} : étendard refusé : {erreur}"
            rapports.afficher_et_ecrire(message)
            rapports.noter_resultat(general['joueur'], 'ÉTENDARD', message)
            return None
        if choix is not None:
            import generaux
            import soldats
            bloc, niveau = choix
            dossier = general['chemin'] / bloc
            unites = [u for u in dossier.iterdir() if generaux.identifier_unite(u) != 'inconnu']
            charges = catalogues.CHARGES_ETENDARDS[niveau]
            probabilite = catalogues.PROBABILITES_ETENDARDS[niveau]
            registre = soldats.charger()
            restantes = {}
            for unite in unites:
                identifiant = soldats.retrouver(unite, registre, config.dans_generation_privee())
                if identifiant is None:
                    identifiant = soldats.enregistrer(unite, registre, generaux.identifier_unite(unite))
                soldats.publier(unite, identifiant, registre[identifiant])
                restantes[identifiant] = charges
            soldats.sauvegarder(registre)
            contexte[identite] = dict(dossier=dossier, niveau=niveau,
                                      probabilite=probabilite, restantes=restantes, detruit=False)
            libelle = 'royal' if niveau == 2 else 'normal'
            message = (f"{general['joueur']}/{general['nom']}, bloc {bloc} : étendard {libelle}, "
                       f'{probabilite} % de sauvetage, {charges} charge(s) par unité pour cette guerre de territoire.')
            rapports.afficher_et_ecrire(message)
            rapports.noter_resultat(general['joueur'], 'ÉTENDARD', message)
    etendard = contexte[identite]
    if etendard is not None:
        # Un déplacement moteur conserve le bloc protégé et les identités,
        # sans relire la déclaration ni renouveler les charges.
        etendard['dossier'] = general['chemin'] / etendard['dossier'].name
    return etendard


def proteger(general, unite, type_unite, aleatoire=None, identifiant=None):
    """Appelé seulement après l'échec du sauvetage par le moral."""
    import unites
    if general is None or unites.etiquette(type_unite, 'mort_vivant'):
        return False
    etendard = figer(general)
    if not etendard or etendard['detruit'] or unite.parent != etendard['dossier']:
        return False
    if identifiant is None:
        import soldats
        identifiant = soldats.retrouver(unite, soldats.charger(), config.dans_generation_privee())
    cle = identifiant
    restant = etendard['restantes'].get(cle, 0)
    if restant <= 0:
        return False
    aleatoire = random if aleatoire is None else aleatoire
    if aleatoire.randint(1, 100) > etendard['probabilite']:
        return False
    etendard['restantes'][cle] = restant - 1
    import rapports
    rapports.afficher_et_ecrire(
        f"Étendard {general['joueur']}/{general['nom']}/{unite.parent.name} : "
        f'{unite.name} sauvé ; {restant - 1} charge(s) individuelle(s) restante(s).')
    return True


def detruire_si_bloc_vide(general):
    """Destruction immédiate, sans retirer le déblocage officiel du général."""
    import generaux
    import rapports
    etendard = figer(general)
    if not etendard or etendard['detruit']:
        return
    dossier = etendard['dossier']
    if dossier.is_dir() and any(generaux.identifier_unite(u) != 'inconnu' for u in dossier.iterdir()):
        return
    etendard['detruit'] = True
    marqueur = dossier / 'etendard.txt'
    if declaration_valide(marqueur):
        marqueur.unlink()
    message = f"Étendard {general['joueur']}/{general['nom']}/{dossier.name} détruit : bloc anéanti."
    rapports.afficher_et_ecrire(message)
    rapports.noter_resultat(general['joueur'], 'ÉTENDARD', message)
