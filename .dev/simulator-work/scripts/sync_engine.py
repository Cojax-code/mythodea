"""Exporte le catalogue et les empreintes des blobs d'un commit officiel précis."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def sync(source, commit):
    source = source.resolve()
    commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', commit + '^{commit}'], text=True).strip()
    names = subprocess.check_output(['git', '-C', str(source), 'ls-tree', '--name-only', commit, 'python/'], text=True).splitlines()
    contents = {Path(name).name: subprocess.check_output(['git', '-C', str(source), 'show', f'{commit}:{name}'])
                for name in names if name.endswith('.py')}
    if not contents:
        raise SystemExit('Aucun module moteur dans ce commit.')
    with tempfile.TemporaryDirectory(prefix='mythodea-catalog-') as directory:
        for name, data in contents.items():
            (Path(directory) / name).write_bytes(data)
        export_catalog(Path(directory), commit, contents)


def export_catalog(source, commit, contents):
    sys.path.insert(0, str(source))
    import catalogues
    import config
    import progression
    lock_path = ROOT / 'backend/engine.lock.json'
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    lock['commit'] = commit
    lock['source_state'] = 'git'
    lock['files'] = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(contents.items())}
    lock['revision'] = commit[:7]
    lock.pop('snapshot', None)
    lock.pop('source_mode', None)
    catalog = lock['catalog']
    catalog.update(blocks=config.ordre_blocs, max_units=config.max_unites_par_general,
                   units=list(catalogues.UNITE_PAR_NOM),
                   unit_details={u['nom']: u for u in catalogues.UNITES.values()},
                   labels=catalogues.ETIQUETTES_COMBAT, natures=list(progression.NATURES),
                   traits=list(progression.TRAITS['hybride']),
                   nature_weights=progression.NATURES, trait_weights=progression.TRAITS,
                   reward_weights=progression.RECOMPENSES)
    catalog['banners'] = {niveau: dict(probability=taux, charges=catalogues.CHARGES_ETENDARDS[niveau])
                          for niveau, taux in catalogues.PROBABILITES_ETENDARDS.items()}
    catalog['label_rank_max'] = [progression.niveau_max_etiquette(n)
                                for n in range(catalog['limits']['level'] + 1)]
    catalog['active_limits'] = {'stratege': 3, 'instinctif': 1, 'hybride': 3}
    # Exporter les parcours officiels : le navigateur ne calcule aucune progression.
    class Branche:
        def __init__(self, haute):
            self.haute = haute

        def randint(self, minimum, maximum):
            return maximum if self.haute else minimum

    catalog['specific_states'] = {}
    catalog['extra_roulette_levels'] = {}
    for nature in progression.NATURES:
        possibles = {(1, 0)}
        niveaux = []
        extras = []
        for niveau in range(catalog['limits']['level'] + 1):
            if niveau and niveau % 5 == 0:
                suivants = set()
                for places, etendard in possibles:
                    for haute in (False, True):
                        fiche = dict(nature=nature, emplacements_etiquettes_actives=places,
                                     niveau_etendard=etendard)
                        recompense, _ = progression.progression_specifique(fiche, Branche(haute))
                        if recompense is None and niveau not in extras:
                            extras.append(niveau)
                        suivants.add((fiche['emplacements_etiquettes_actives'], fiche['niveau_etendard']))
                possibles = suivants
            niveaux.append(sorted(possibles))
        catalog['specific_states'][nature] = niveaux
        catalog['extra_roulette_levels'][nature] = extras
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Commit verrouillé : {commit} ({len(contents)} modules)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--commit', required=True, help='Commit validé à exporter, sans lire les modifications locales.')
    args = parser.parse_args()
    sync(args.source, args.commit)
