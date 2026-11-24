"""Verrouille les sources locales et exporte leur catalogue sans dupliquer les règles."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def sync(source):
    source = source.resolve()
    sys.path.insert(0, str(source / 'python'))
    import catalogues
    import config
    import progression
    lock_path = ROOT / 'backend/engine.lock.json'
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    lock['commit'] = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    lock['source_mode'] = 'working-tree'
    lock['files'] = {p.name: hashlib.sha256(p.read_text(encoding='utf-8').encode()).hexdigest()
                     for p in sorted((source / 'python').glob('*.py'))}
    lock['snapshot'] = hashlib.sha256(json.dumps(lock['files'], sort_keys=True).encode()).hexdigest()
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
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Sources locales verrouillées : {lock['snapshot']}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    sync(parser.parse_args().source)
