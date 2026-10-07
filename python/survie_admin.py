"""Diagnostic et récupération explicite ; aucun audit ni combat n'est rejoué."""
import argparse
import json
import os
from pathlib import Path
import re
import time

import config
import cycle_linux
import etat
import securite


def exiger_moteur_arrete(configuration):
    systeme = configuration['game_path'] / 'systeme'
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
    fichier = configuration['game_path'] / 'systeme/gel_survie.json'
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
    verrou = configuration['game_path'] / 'systeme/verrou_cycle_survie'
    if verrou.exists():
        verrou.unlink()
        cycle_linux.synchroniser_dossier(verrou.parent)


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
        gestion.generation = configuration['game_path'] / 'systeme/generations' / generation
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
    p.add_argument('operation', choices=('diagnostic', 'degeler', 'retirer-verrou', 'republier'))
    p.add_argument('--confirmer', action='store_true', help='administrateur : diagnostic vérifié')
    p.add_argument('--generation')
    args = p.parse_args(argv)
    if os.name != 'posix' or os.geteuid() != 0:
        p.error('Exécuter sous Linux avec root depuis le compte administrateur.')
    c = config.configuration_mode('survie')
    if args.operation == 'diagnostic':
        for nom in ('cycle_survie.json', 'verrou_cycle_survie', 'gel_survie.json'):
            fichier = c['game_path'] / 'systeme' / nom
            print(nom + ':\n' + (fichier.read_text() if fichier.exists() else 'absent'))
        return
    if not args.confirmer:
        p.error('--confirmer est requis après vérification administrative.')
    {'degeler': lambda: degeler(c), 'retirer-verrou': lambda: retirer_verrou(c),
     'republier': lambda: republier(c, args.generation)}[args.operation]()


if __name__ == '__main__':
    main()
