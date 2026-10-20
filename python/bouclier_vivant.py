"""Calculs purs pour le Bouclier vivant V2.

Aucun changement de disque ici : le résolveur territorial effectuera ensuite
les conversions, les combats et les écritures officielles.
"""
from fractions import Fraction
import random

RESISTANCE_INITIALE = Fraction(250)
TYPE_BOUCLIER = "Trop_gros_zombie"


def resistance_apres_choc(resistance, puissance_adverse):
    """Compare avant usure. L'égalité détruit le bouclier.

    Renvoie (survit, résistance restante), sans arrondi.
    """
    r, p = Fraction(resistance), Fraction(puissance_adverse)
    if r <= 0 or p < 0:
        raise ValueError("Résistance positive et puissance adverse non négative requises.")
    if p >= r:
        return False, Fraction(0)
    return True, r - p / 4


def choisir_spore(soldats_adverses, rng=None):
    """Un soldat ayant le moins de batailles ; tirage en cas d'égalité.

    Les victimes possibles sont les soldats réellement présents dans le bloc.
    La mutation et la persistance relèvent du résolveur officiel.
    """
    if not soldats_adverses:
        return None
    minimum = min(s["batailles"] for s in soldats_adverses)
    candidats = [s for s in soldats_adverses if s["batailles"] == minimum]
    return (rng or random).choice(candidats)


def bloc_destination_spore(effectifs_par_bloc, blocs_eligibles, rng=None):
    """Destination parmi les blocs compatibles, le plus rempli d'abord."""
    possibles = [b for b in blocs_eligibles if b in effectifs_par_bloc]
    if not possibles:
        return None
    maxi = max(effectifs_par_bloc[b] for b in possibles)
    return (rng or random).choice([b for b in possibles if effectifs_par_bloc[b] == maxi])


def choisir_bloc_favorable(blocs_adverses, potentiel, rng=None):
    """Sélectionne uniquement une cible gagnable ; None sinon.

    potentiel(bloc) retourne True si la confrontation ordinaire serait gagnante.
    Le moteur principal reste responsable du calcul des rapports de force.
    """
    candidats = [b for b in blocs_adverses if potentiel(b)]
    return (rng or random).choice(candidats) if candidats else None


def seulement_bouclier(composition):
    """Un général sans autre unité combattante perd automatiquement."""
    boucliers = sum(bloc.get(TYPE_BOUCLIER, 0) for bloc in composition.values())
    ordinaires = sum(n for bloc in composition.values()
                    for type_unite, n in bloc.items()
                    if type_unite != TYPE_BOUCLIER and type_unite != "messager_du_QG")
    return boucliers > 0 and ordinaires == 0


def verifier_un_seul_bouclier(composition):
    nombre = sum(bloc.get(TYPE_BOUCLIER, 0) for bloc in composition.values())
    if nombre > 1:
        raise ValueError("Un seul Trop gros zombie autorisé par général.")
    return nombre



def _cle_resistance(general):
    import soldats
    bataille = soldats._bataille.get()
    if bataille is None or not bataille[0]:
        return None
    return f"{bataille[0]}:{general['joueur']}:{general['nom']}"


def _lire_resistance(general):
    import unites
    cle = _cle_resistance(general)
    if cle is None:
        return RESISTANCE_INITIALE
    valeur = unites.charger_capacites().get('resistances_boucliers', {}).get(cle)
    return RESISTANCE_INITIALE if valeur is None else Fraction(valeur)


def _sauver_resistance(general, resistance):
    import unites
    cle = _cle_resistance(general)
    if cle is not None:
        donnees = unites.charger_capacites()
        donnees.setdefault('resistances_boucliers', {})[cle] = str(Fraction(resistance))
        unites.sauver_capacites(donnees)


def presence_bouclier(general):
    """Repérage sans lecture destructive des blocs."""
    import generaux
    composition = generaux.lire_composition_general(general['chemin'])
    return verifier_un_seul_bouclier(composition) == 1


def retirer_bouclier(general):
    """Supprime l'unité officielle et son entrée d'historique, sans la soigner."""
    import config
    import generaux
    import shutil
    import soldats
    registre = soldats.charger()
    nombre = 0
    for bloc in config.ordre_blocs:
        dossier = general['chemin'] / bloc
        if not dossier.is_dir():
            continue
        for unite in dossier.iterdir():
            if generaux.identifier_unite(unite) != TYPE_BOUCLIER:
                continue
            identifiant = soldats.retrouver(unite, registre, config.dans_generation_privee())
            if identifiant in registre:
                registre[identifiant]['detruit'] = True
            shutil.rmtree(unite)
            nombre += 1
    soldats.sauvegarder(registre)
    return nombre


def convertir_spore(general_zombie, adversaire, bloc_adverse, evenement, rng=None):
    """Change de camp un soldat réel, avec son identité et son expérience.

    L'événement est réservé avant écriture. Une mutation interrompue exige une
    récupération de la génération privée ; elle ne peut jamais être rejouée.
    """
    import config
    import generaux
    import shutil
    import soldats
    import unites
    if bloc_adverse not in config.ordre_blocs:
        raise ValueError("Bloc adverse inconnu.")
    donnees = unites.charger_capacites()
    preuves = donnees.setdefault('spores', {})
    if evenement in preuves:
        if not preuves[evenement]['terminee']:
            raise RuntimeError('Spore interrompue : récupération administrative requise, sans rejeu.')
        return None
    registre = soldats.charger()
    dossier = adversaire['chemin'] / bloc_adverse
    candidats = []
    for chemin in dossier.iterdir():
        if generaux.identifier_unite(chemin) in ('inconnu', 'Trop_gros_zombie'):
            continue
        identifiant = soldats.retrouver(chemin, registre, config.dans_generation_privee())
        if identifiant and not registre[identifiant].get('detruit'):
            candidats.append(dict(id=identifiant, batailles=registre[identifiant]['batailles'],
                                  chemin=chemin))
    victime = choisir_spore(candidats, rng)
    if victime is None:
        return None
    composition = generaux.lire_composition_general(general_zombie['chemin'])
    # Spore rejoint prioritairement les blocs contenant des Zombies ordinaires,
    # jamais un bloc comportant un autre type combattant.
    eligibles = [bloc for bloc in config.ordre_blocs
                 if all(t in ('zombie', TYPE_BOUCLIER, 'messager_du_QG')
                        for t in composition[bloc])]
    tailles = {bloc: sum(composition[bloc].values()) for bloc in eligibles}
    destination_bloc = bloc_destination_spore(tailles, eligibles, rng)
    if destination_bloc is None:
        raise RuntimeError('Aucun bloc zombie compatible pour Spore.')
    identifiant = victime['id']
    destination = general_zombie['chemin'] / destination_bloc / ('zombi_' + identifiant)
    if destination.exists():
        raise RuntimeError('Spore : destination déjà occupée.')
    contexte = soldats._bataille.get()
    territoire = contexte[0] if contexte else None
    preuves[evenement] = dict(victime=identifiant, bloc=destination_bloc,
                             territoire=territoire, terminee=False)
    unites.sauver_capacites(donnees)
    # Nouveau dossier sans ancien équipement ; identité historique conservée.
    shutil.rmtree(victime['chemin'])
    destination.mkdir()
    infos = destination.stat()
    valeur = registre[identifiant]
    valeur.update(type='zombie', chemin=soldats.cle(destination),
                  device=infos.st_dev, inode=infos.st_ino, blessures=0,
                  origine_officielle={'spore': evenement, 'territoire': territoire})
    soldats.sauvegarder(registre)
    soldats.publier(destination, identifiant, valeur)
    preuves[evenement]['terminee'] = True
    unites.sauver_capacites(donnees)
    return identifiant


def _infos(general):
    import generaux
    return generaux.lire_blocs_general(general['chemin'])


def _zombies_vivants(general):
    import generaux
    composition = generaux.lire_composition_general(general['chemin'])
    return sum(bloc.get('zombie', 0) for bloc in composition.values())


def _puissance_bloc_adverse(infos, bloc):
    import combats
    return (infos['nombre'] * combats.valeur_base_bloc(infos, bloc) *
            combats.multiplicateur(infos['type'], TYPE_BOUCLIER))


def _cible_zombie(general_zombie, adversaire):
    """Une cible gagnable d'abord ; sinon le bloc équivalent, ou un bloc vivant.

    L'égalité de puissance est une chance d'affrontement et non une victoire
    garantie. Les valeurs réelles sont recalculées au moment de l'attaque.
    """
    import combats
    import config
    zombies, ennemis = _infos(general_zombie), _infos(adversaire)
    candidats = [(b, zombies[b]) for b in config.ordre_blocs
                 if zombies[b]['type'] == 'zombie' and zombies[b]['nombre'] > 0]
    for bloc, infos in candidats:
        valeur_z = combats.valeur_base_bloc(infos, bloc)
        for cible in config.ordre_blocs:
            defense = ennemis[cible]
            if defense['nombre'] <= 0 or defense['type'] in ('vide', TYPE_BOUCLIER):
                continue
            attaque = infos['nombre'] * valeur_z * combats.multiplicateur('zombie', defense['type'])
            riposte = (defense['nombre'] * combats.valeur_base_bloc(defense, cible)
                       * combats.multiplicateur(defense['type'], 'zombie'))
            if attaque >= riposte:
                return bloc, cible
    for bloc, infos in candidats:
        if ennemis[bloc]['nombre'] > 0:
            return bloc, bloc
    for bloc, _ in candidats:
        for cible in config.ordre_blocs:
            if ennemis[cible]['nombre'] > 0:
                return bloc, cible
    return None


def resoudre_priorite(general_zombie, adversaire):
    """Joue Bouclier -> blocs adverses -> Zombies -> Bouclier (survivants).

    Retourne (combat_termine, détails). Si le bouclier meurt, renvoie False :
    le moteur reprend alors ses phases classiques sans rejouer cette priorité.
    """
    import combats
    import config
    import generaux
    import rapports
    import soldats
    import unites
    if not presence_bouclier(general_zombie):
        return False, []
    if presence_bouclier(adversaire):
        raise ValueError('Deux généraux opposés possèdent Bouclier vivant : règle de priorité mutuelle non validée.')
    contexte = unites._duel.get()
    if contexte is None:
        raise RuntimeError('Bouclier vivant hors duel officiel.')
    details = []
    resistance = _lire_resistance(general_zombie)
    if _zombies_vivants(general_zombie) == 0:
        retirer_bouclier(general_zombie)
        generaux.supprimer_general_si_vide(general_zombie)
        rapports.afficher_et_ecrire('Bouclier vivant seul : défaite du général zombie.')
        return True, details
    # Chaque cycle comprend tous les blocs ennemis, puis une attaque zombie.
    # Le plafond est un garde-fou : aucune boucle non terminante publiée.
    for cycle in range(1, 101):
        if not general_zombie['chemin'].is_dir() or not adversaire['chemin'].is_dir():
            return True, details
        if _zombies_vivants(general_zombie) == 0:
            retirer_bouclier(general_zombie)
            generaux.supprimer_general_si_vide(general_zombie)
            rapports.afficher_et_ecrire('Plus aucun Zombie ordinaire : Bouclier vivant disparaît.')
            return True, details
        if not presence_bouclier(general_zombie):
            return False, details
        ennemis = _infos(adversaire)
        for bloc in config.ordre_blocs:
            infos = ennemis[bloc]
            if infos['nombre'] <= 0 or infos['type'] in ('vide', 'messager_du_QG'):
                continue
            force = _puissance_bloc_adverse(infos, bloc)
            avant = resistance
            survit, resistance = resistance_apres_choc(resistance, force)
            _sauver_resistance(general_zombie, resistance)
            soldats.affrontement(general_zombie, adversaire)
            contexte['confrontation'] += 1
            evenement = (f"spore:{contexte['id']}:{contexte['confrontation']}:"
                         f"{general_zombie['joueur']}:{general_zombie['nom']}")
            contamine = convertir_spore(general_zombie, adversaire, bloc, evenement)
            rapports.afficher_et_ecrire(
                f'Bouclier vivant contre {bloc} : {avant} contre {force} ; '
                f'{"résiste (" + str(resistance) + ")" if survit else "détruit"} ; '
                f'Spore : {"1 conversion" if contamine else "aucune cible"}')
            details.append(dict(moment='Bouclier vivant', bloc_1='bouclier',
                                type_1=TYPE_BOUCLIER, initial_1=1,
                                final_1=int(survit), bloc_2=bloc,
                                type_2=infos['type'], initial_2=infos['nombre'],
                                final_2=max(0, infos['nombre'] - int(bool(contamine)))))
            if not survit:
                retirer_bouclier(general_zombie)
                if _zombies_vivants(general_zombie) == 0:
                    generaux.supprimer_general_si_vide(general_zombie)
                    return True, details
                rapports.afficher_et_ecrire('Bouclier détruit : reprise du combat normal.')
                return False, details
            if not adversaire['chemin'].is_dir():
                return True, details
        generaux.supprimer_general_si_vide(adversaire)
        if not adversaire['chemin'].is_dir():
            return True, details
        if _zombies_vivants(general_zombie) == 0:
            retirer_bouclier(general_zombie)
            generaux.supprimer_general_si_vide(general_zombie)
            return True, details
        cible = _cible_zombie(general_zombie, adversaire)
        if cible is None:
            # Aucun ennemi ordinaire et pas de cible : terminaison contrôlée.
            return True, details
        bloc_zombie, bloc_adverse = cible
        armee = {
            general_zombie['joueur']: _infos(general_zombie),
            adversaire['joueur']: _infos(adversaire),
        }
        detail = combats.attaque_ciblee(armee, general_zombie, adversaire,
                                       bloc_zombie, bloc_adverse)
        details.append(dict(moment='Zombies ordinaires',
                            bloc_1=bloc_zombie, type_1=detail['type_attaquant'],
                            initial_1=detail['initial_attaquant'],
                            final_1=detail['final_attaquant'],
                            bloc_2=bloc_adverse, type_2=detail['type_defenseur'],
                            initial_2=detail['initial_defenseur'],
                            final_2=detail['final_defenseur']))
        generaux.supprimer_general_si_vide(adversaire)
        if not adversaire['chemin'].is_dir():
            return True, details
    raise RuntimeError('Bouclier vivant : limite de cycles atteinte ; ne pas publier un combat incomplet.')
