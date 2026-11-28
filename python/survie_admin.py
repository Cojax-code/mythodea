"""Diagnostic et récupération explicite ; aucun audit ni combat n'est rejoué."""
import argparse
import json
import os
from pathlib import Path
import re
import time
import stat
import uuid

import config
import cycle_linux
import etat
import securite
import generaux


def plan_rollback(configuration):
    """Diagnostic en lecture seule ; aucune restauration conjecturale."""
    cycle = etat.charger_cycle_survie(configuration)
    if not cycle or cycle['phase'] not in ('capture', 'resolution', 'recuperation'):
        raise RuntimeError('Rollback réservé à une capture/résolution interrompue non publiée.')
    nom = cycle.get('generation', '')
    if not re.fullmatch(r'g[0-9]{6,}-[0-9a-f]{12}', nom):
        raise RuntimeError('Génération interrompue absente ou invalide.')
    if nom == cycle.get('generation_active'):
        raise RuntimeError('Génération déjà validée : ne jamais rejouer ce tour.')
    generation = configuration['game_path'] / '.systeme/generations' / nom
    cycle_linux.sans_liens(generation)
    if not generation.is_dir():
        raise RuntimeError('Génération de diagnostic absente.')
    for dossier in (generation.parent.parent, generation.parent, generation):
        infos = dossier.stat()
        if not stat.S_ISDIR(infos.st_mode) or infos.st_uid != 0 or infos.st_mode & 0o022:
            raise RuntimeError('Dossier administratif modifiable : diagnostic non fiable.')
    if (generation / 'resultat.json').exists() or (generation / 'resultat.json').is_symlink():
        raise RuntimeError('Résultat présent : utiliser republier, sans rejouer la résolution.')
    # Refuser aussi les traces d'une republication administrative interrompue.
    if any(generation.glob('publication*')):
        raise RuntimeError('Publication commencée ou ambiguë : rollback automatique refusé.')
    stage = configuration.get('publication_homes_path', Path('/home/.mythodea-publication'))
    if stage.exists() and any(stage.glob(nom + '*')):
        raise RuntimeError('Staging de publication présent : vérifier la republication.')
    reference = etat.charger_unites_actions(configuration)
    if not reference or reference.get('tour') != cycle['tour']:
        raise RuntimeError('Référence ACTIONS incohérente : aucune reprise sûre.')
    systeme = configuration['game_path'] / '.systeme'
    for nom_etat in config.ETATS_METIER:
        fichier = systeme / nom_etat
        cycle_linux.sans_liens(fichier)
        if fichier.exists():
            infos = fichier.stat()
            if (not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1
                    or infos.st_uid != 0 or infos.st_mode & 0o077):
                raise RuntimeError(f'État privé non sûr : {fichier}')
            if fichier.suffix == '.json':
                if not isinstance(json.loads(fichier.read_text(encoding='utf-8')), dict):
                    raise RuntimeError(f'État privé invalide : {fichier}')
    # Les déplacements ACTIONS ne sont pas encore audités : ne pas les sanctionner
    # ni remplacer leurs positions officielles par celles constatées maintenant.
    inventaire = securite.inventorier_unites_actions(configuration)
    identites = [g['identifiant'] for g in inventaire.values()]
    if len(identites) != len(set(identites)):
        raise RuntimeError('Généraux dupliqués : examen manuel nécessaire.')
    positions = etat.charger_positions_generaux()
    profils = systeme / 'progression.json'
    if profils.exists():
        for fiche in json.loads(profils.read_text(encoding='utf-8')).values():
            if not isinstance(fiche, dict):
                raise RuntimeError('Profil privé invalide.')
            if any(cle.startswith((f"formation:{cycle['tour']}:", f"combat:survie:{cycle['tour']}:"))
                   for cle in fiche.get('progressions_validees', {})):
                raise RuntimeError('Progression de ce tour déjà validée sur le plateau : rollback refusé.')
    for identite in identites:
        joueur, general = identite.split(':')
        if not generaux.identite_officielle(joueur, general, configuration):
            raise RuntimeError('Identités/compteurs incohérents : examen manuel nécessaire.')
    return {'tour': cycle['tour'], 'generation': generation.name,
            'operation': 'reouvrir_actions_sans_restaurer',
            'conserves': ['plateau actuel et déplacements', 'profils, unités, bâtiments',
                         'états privés, compteurs et reçus', 'archives', 'génération interrompue'],
            'restaures': [],
            'pertes': ['tentatives Crypte inachevées déjà closes ; ateliers déjà nettoyés par la capture'],
            'note': 'Nouvelle fenêtre ACTIONS du même tour ; contrôles répétés sous gel. Aucun gain rejoué.'}


@cycle_linux.interruption_differee()
def rollback(configuration, dry_run=False, gestion=None):
    if not dry_run:
        print('[1/5] Vérification des données et du verrou...', flush=True)
    exiger_moteur_arrete(configuration)
    for nom in ('gel_survie.json', 'verrou_cycle_survie'):
        if (configuration['game_path'] / '.systeme' / nom).exists():
            raise RuntimeError(f'{nom} présent : diagnostic puis dégel/retrait explicite requis.')
    plan = plan_rollback(configuration)
    if dry_run:
        return plan
    with etat.verrou_cycle_survie(configuration):
        gestion = gestion or cycle_linux.Generations(configuration)
        # Pas de preparer() : aucune migration avant la sauvegarde de diagnostic.
        gestion.backend.preparer()
        print(f'=== RÉCUPÉRATION DU TOUR {plan["tour"]} ===\n[2/5] Gel sécurisé des joueurs...', flush=True)
        gestion.backend.geler()
        try:
            gestion.backend.verifier_gel()
            plan = plan_rollback(configuration)
            print('[3/5] Sauvegarde de diagnostic...', flush=True)
            generation = configuration['game_path'] / '.systeme/generations' / plan['generation']
            sauvegarde = generation / ('recuperation-' + uuid.uuid4().hex)
            cycle_linux.dossier_prive(sauvegarde)
            cycle_linux.ecrire_json(sauvegarde / 'plan.json', plan)
            cycle_linux.dossier_prive(sauvegarde / 'game')
            cycle_linux.dossier_prive(sauvegarde / 'homes')
            for source in (*configuration['territoires'], configuration['repli_path']):
                if source.exists():
                    cycle_linux.copier(source, sauvegarde / 'game' / source.name, gestion.backend.verifier_gel)
            cycle_linux.dossier_prive(sauvegarde / 'game/.systeme')
            for nom in (*config.ETATS_METIER, 'cycle_survie.json'):
                source = configuration['game_path'] / '.systeme' / nom
                if source.exists():
                    cycle_linux.copier(source, sauvegarde / 'game/.systeme' / nom, gestion.backend.verifier_gel)
            for joueur, home in gestion.homes.items():
                cycle_linux.dossier_prive(sauvegarde / 'homes' / joueur)
                for source in cycle_linux.entrees_home(home):
                    cycle_linux.copier(source, sauvegarde / 'homes' / joueur / source.name, gestion.backend.verifier_gel)
            cycle_linux.ecrire_json(sauvegarde / 'prete.json', {'complete': True})
            precedent = etat.charger_cycle_survie(configuration)
            reprise = {'tour': plan['tour'], 'phase': 'actions',
                       'echeance': time.time() + configuration['duree_phase_action_secondes'],
                       'recuperation_de': plan['generation']}
            if 'generation_active' in precedent:
                reprise['generation_active'] = precedent['generation_active']
            gestion.backend.verifier_gel()
            print('[4/5] Validation de la reprise...', flush=True)
            # Point de validation unique. Avant : recommencer la récupération.
            # Après : reprendre ACTIONS, sans nouvelle attribution de général.
            etat.sauvegarder_cycle_survie(reprise, configuration)
        finally:
            print('[5/5] Dégel des joueurs...', flush=True)
            gestion.backend.degeler()
    print(f'Récupération terminée. Le tour {plan["tour"]} peut reprendre en phase ACTIONS.', flush=True)
    return plan


def exiger_moteur_arrete(configuration):
    config.verifier_structure_actuelle(configuration)
    systeme = configuration['game_path'] / '.systeme'
    for fichier, json_pid in ((systeme / 'verrou_cycle_survie', False), (systeme / 'gel_survie.json', True)):
        cycle_linux.sans_liens(fichier)
        if fichier.exists():
            pid = int(json.loads(fichier.read_text())['pid'] if json_pid else fichier.read_text().strip())
            if pid <= 0:
                raise RuntimeError('PID invalide : examen manuel nécessaire.')
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                continue
            raise RuntimeError(f'PID {pid} encore présent : aucune récupération autorisée.')


def degeler(configuration):
    exiger_moteur_arrete(configuration)
    fichier = configuration['game_path'] / '.systeme/gel_survie.json'
    if not fichier.exists():
        return
    donnees = json.loads(fichier.read_text())
    backend = cycle_linux.Linux(configuration)
    if not set(donnees['groupes']) <= {str(p) for p in backend.groupes}:
        raise RuntimeError('Journal de gel incompatible avec les comptes configurés.')
    for groupe in map(Path, donnees['groupes']):
        if groupe.exists():
            (groupe / 'cgroup.freeze').write_text('0')
    fichier.unlink()
    cycle = etat.charger_cycle_survie(configuration)
    if cycle and cycle['phase'] not in ('actions', 'consultation', 'defaite'):
        cycle['phase'] = 'recuperation'
        cycle['erreur'] = 'Dégel de secours ; état métier à vérifier.'
        etat.sauvegarder_cycle_survie(cycle, configuration)


def retirer_verrou(configuration):
    exiger_moteur_arrete(configuration)
    verrou = configuration['game_path'] / '.systeme/verrou_cycle_survie'
    if verrou.exists():
        verrou.unlink()
        cycle_linux.synchroniser_dossier(verrou.parent)


def plan_residus(configuration):
    """Inspection complète en lecture seule ; toute ambiguïté est bloquante."""
    systeme = configuration['game_path'] / '.systeme'
    fichiers = {nom: systeme / nom for nom in
                ('verrou_cycle_survie', 'gel_survie.json', 'communication/crypte.sock')}
    signatures = {}
    for nom, fichier in fichiers.items():
        cycle_linux.sans_liens(fichier)
        if not fichier.exists():
            continue
        infos = fichier.lstat()
        attendu = stat.S_ISSOCK if nom.endswith('.sock') else stat.S_ISREG
        if not attendu(infos.st_mode) or infos.st_uid != 0 or infos.st_nlink != 1:
            raise RuntimeError(f'Résidu de type ou propriétaire inattendu : {fichier}')
        if not nom.endswith('.sock') and infos.st_mode & 0o077:
            raise RuntimeError(f'Résidu privé accessible à un tiers : {fichier}')
        signatures[nom] = [infos.st_dev, infos.st_ino, infos.st_mtime_ns]
    exiger_moteur_arrete(configuration)
    # Un moteur ayant perdu son verrou doit également bloquer la maintenance.
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal() or int(proc.name) == os.getpid():
            continue
        try:
            arguments = (proc / 'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError, ProcessLookupError):
            continue
        if any(Path(os.fsdecode(a)).name in ('mythodea_v_1_5.py', 'survie_admin.py') for a in arguments):
            raise RuntimeError(f'Moteur ou administration encore actif : PID {proc.name}.')
    socket = fichiers['communication/crypte.sock']
    # La table du noyau détecte aussi une socket liée mais pas encore en écoute.
    for ligne in Path('/proc/net/unix').read_text().splitlines()[1:]:
        champs = ligne.split(maxsplit=7)
        if len(champs) == 8 and champs[7] == str(socket):
            raise RuntimeError('Socket Crypte active : nettoyage refusé.')
    gel = fichiers['gel_survie.json']
    if gel.exists():
        donnees = json.loads(gel.read_text())
        backend = cycle_linux.Linux(configuration)
        groupes = donnees.get('groupes')
        if (not isinstance(groupes, list) or len(groupes) != len(set(groupes))
                or not set(groupes) <= {str(p) for p in backend.groupes}):
            raise RuntimeError('Journal de gel incompatible : aucun dégel autorisé.')
        verrou = fichiers['verrou_cycle_survie']
        if verrou.exists() and int(verrou.read_text()) != donnees['pid']:
            raise RuntimeError('PID du gel différent du verrou : examen manuel nécessaire.')
        # Sans identité durable du cgroup, un ancien journal ne prouve pas que
        # le gel actuel nous appartient. Conserver les commandes individuelles.
        if any((Path(g) / 'cgroup.freeze').exists() and
               (Path(g) / 'cgroup.freeze').read_text().strip() != '0' for g in groupes):
            raise RuntimeError('Groupes encore gelés : vérifier leur origine puis utiliser degeler explicitement.')
    return {'operations': list(signatures), 'signatures': signatures,
            'note': 'Retrait des seuls résidus inactifs ; aucun changement du cycle ni rollback.'}


@cycle_linux.interruption_differee()
def nettoyer_residus(configuration, dry_run=False):
    plan = plan_residus(configuration)
    if dry_run:
        return plan
    systeme = configuration['game_path'] / '.systeme'
    # Revalider toutes les conditions avant le premier retrait.
    if plan_residus(configuration) != plan:
        raise RuntimeError('Résidus modifiés pendant le diagnostic.')
    verrou = systeme / 'verrou_cycle_survie'
    if 'verrou_cycle_survie' in plan['signatures']:
        verrou.unlink()
    with etat.verrou_cycle_survie(configuration):
        for nom, signature in plan['signatures'].items():
            if nom == 'verrou_cycle_survie':
                continue
            fichier = systeme / nom
            cycle_linux.sans_liens(fichier)
            infos = fichier.lstat()
            if [infos.st_dev, infos.st_ino, infos.st_mtime_ns] != signature:
                raise RuntimeError(f'Résidu modifié : {fichier}')
            fichier.unlink()
            cycle_linux.synchroniser_dossier(fichier.parent)
    return plan


@cycle_linux.interruption_differee()
def republier(configuration, generation):
    if not re.fullmatch(r'g[0-9]{6,}-[0-9a-f]{12}', generation or ''):
        raise ValueError('Identifiant de génération invalide.')
    exiger_moteur_arrete(configuration)
    with etat.verrou_cycle_survie(configuration):
        cycle = etat.charger_cycle_survie(configuration)
        if (not cycle or cycle['phase'] not in ('publication', 'recuperation')
                or cycle.get('generation') != generation):
            raise RuntimeError('Seule la génération interrompue peut être republiée après vérification.')
        gestion = cycle_linux.Generations(configuration)
        gestion.preparer()
        gestion.generation = configuration['game_path'] / '.systeme/generations' / generation
        cycle_linux.sans_liens(gestion.generation)
        resultat = json.loads((gestion.generation / 'resultat.json').read_text())
        if not resultat.get('resolution_terminee'):
            raise RuntimeError('Résolution incomplète : aucune republication possible.')
        travail = gestion.generation / 'travail'
        prive = dict(configuration, game_path=travail / 'game',
                     territoires=[travail / 'game' / p.name for p in configuration['territoires']],
                     repli_path=travail / 'game/repli')
        with config.racines_generation(prive['game_path'],
                                      {j: travail / 'homes' / j for j in configuration['joueurs']}):
            securite.controler_coherence_territoires(prive)
        # Garder tous les journaux/anciens dossiers pour l'examen administratif.
        suffixe = f'.interrompu-{time.time_ns()}'
        for p in (gestion.generation / 'publication', gestion.generation / 'publication.json',
                  gestion.home_stage / generation):
            if p.exists():
                p.rename(p.with_name(p.name + suffixe))
        public, stage = gestion.preparer_publication()
        try:
            gestion.publier(resultat['tour'], public, stage, resultat['defaite'])
        except BaseException as erreur:
            gestion.erreur(resultat['tour'], erreur)
            raise


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=('diagnostic', 'degeler', 'retirer-verrou', 'republier', 'rollback', 'nettoyer-residus'))
    p.add_argument('--confirmer', action='store_true', help='administrateur : diagnostic vérifié')
    p.add_argument('--generation')
    p.add_argument('--dry-run', action='store_true', help='diagnostic rollback sans aucune écriture')
    args = p.parse_args(argv)
    if os.name != 'posix' or os.geteuid() != 0:
        p.error('Exécuter sous Linux avec root depuis le compte administrateur.')
    c = config.configuration_mode('survie')
    if args.operation == 'diagnostic':
        config.verifier_structure_actuelle(c)
        for nom in ('cycle_survie.json', 'verrou_cycle_survie', 'gel_survie.json'):
            fichier = c['game_path'] / '.systeme' / nom
            print(nom + ':\n' + (fichier.read_text() if fichier.exists() else 'absent'))
        try:
            print(json.dumps(plan_residus(c), ensure_ascii=False, indent=2))
        except (RuntimeError, ValueError, OSError) as erreur:
            print('Résidus : ' + str(erreur))
        try:
            print(json.dumps(rollback(c, dry_run=True), ensure_ascii=False, indent=2))
        except (RuntimeError, ValueError, OSError) as erreur:
            print('Rollback : ' + str(erreur))
        return
    if args.dry_run:
        if args.operation not in ('rollback', 'nettoyer-residus'):
            p.error('--dry-run est réservé à rollback et nettoyer-residus.')
        operation = rollback if args.operation == 'rollback' else nettoyer_residus
        print(json.dumps(operation(c, dry_run=True), ensure_ascii=False, indent=2))
        return
    if not args.confirmer:
        p.error('--confirmer est requis après vérification administrative.')
    {'degeler': lambda: degeler(c), 'retirer-verrou': lambda: retirer_verrou(c),
     'nettoyer-residus': lambda: print(json.dumps(nettoyer_residus(c), ensure_ascii=False, indent=2)),
     'rollback': lambda: print(json.dumps(rollback(c), ensure_ascii=False, indent=2)),
     'republier': lambda: republier(c, args.generation)}[args.operation]()


if __name__ == '__main__':
    main()
