"""Valide une copie sur le disque Linux ; ne touche ni au moteur ni à une partie."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve', action='store_true', help='Serveur local pour les tests navigateur (Ctrl+C pour arrêter).')
    args = parser.parse_args()
    if sys.platform != 'linux' or os.getuid() == 0 or not shutil.which('bwrap'):
        parser.error('Linux, utilisateur non root et Bubblewrap requis.')
    lock = json.loads((ROOT / 'backend/engine.lock.json').read_text())
    with tempfile.TemporaryDirectory(prefix='mythodea-web-validation-') as directory:
        work = Path(directory)
        for folder in ('backend', 'tests', 'scripts', 'js', 'css', 'docs'):
            shutil.copytree(ROOT / folder, work / folder,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for path in ROOT.glob('*.html'):
            shutil.copyfile(path, work / path.name)
        engine = '.runtime/engine-' + lock['revision']
        shutil.copytree(ROOT / engine, work / engine)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', MYTHODEA_ENGINE_PATH=str(work / engine))
        if (ROOT / '.runtime/deps').is_dir():
            env['PYTHONPATH'] = str(ROOT / '.runtime/deps')
        command = [sys.executable, '-B', '-m']
        if args.serve:
            print(f'Sources navigateur : {work}', flush=True)
            try:
                return subprocess.call(command + ['backend.app'], cwd=work, env=env)
            except KeyboardInterrupt:
                return 0
        results = ROOT / 'test-results'
        results.mkdir(exist_ok=True)
        with (results / 'python-linux.log').open('w') as log:
            result = subprocess.run(command + ['unittest', 'discover', '-s', 'tests', '-v'],
                                    cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT)
        print((results / 'python-linux.log').read_text()[-7000:])
        return result.returncode


if __name__ == '__main__':
    sys.exit(main())
