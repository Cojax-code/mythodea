"""Exécute les cinq parcours Chrome, conserve chaque résultat et chaque diagnostic."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('browser_hybride_etendards', 'browser_configuration',
         'browser_progression_audit', 'browser_modes', 'browser_smoke')


if __name__ == '__main__':
    results = ROOT / 'test-results'
    results.mkdir(exist_ok=True)
    failures = []
    for name in (sys.argv[1:] or NAMES):
        if name not in NAMES:
            raise SystemExit('Parcours inconnu : ' + name)
        print(name + ' : en cours', flush=True)
        with (results / (name + '.log')).open('w', encoding='utf-8') as log:
            run = subprocess.run([sys.executable, '-B', str(ROOT / 'tests' / (name + '.py'))],
                                 cwd=ROOT, env=dict(os.environ, PYTHONIOENCODING='utf-8'),
                                 stdout=log, stderr=subprocess.STDOUT)
        print(name + (' : OK' if run.returncode == 0 else ' : ÉCHEC'), flush=True)
        if run.returncode:
            failures.append(name)
            print((results / (name + '.log')).read_text(encoding='utf-8')[-4000:], flush=True)
    sys.exit(bool(failures))
