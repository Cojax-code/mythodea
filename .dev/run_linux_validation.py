"""Exécute une copie des sources sur le disque Linux, dans un dossier jetable."""
from pathlib import Path
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent.parent
kind = sys.argv[1]
with tempfile.TemporaryDirectory(prefix='mythodea-validation-') as directory:
    work = Path(directory)
    if kind in ('engine', 'permissions'):
        for name in ('python', 'bash', '.dev/tests', '.dev/exemples'):
            shutil.copytree(root/name, work/name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for path in root.iterdir():
            if path.is_file():
                shutil.copy2(path, work/path.name)
        cwd = work
        tests = '.dev/tests' if kind == 'engine' else 'python/tests_linux'
        env = os.environ.copy()
        for path in (work / 'python').rglob('*.py'):
            py_compile.compile(str(path), doraise=True)
    else:
        source = root.parent/'Mythodea_web' if kind == 'web' else root/'.dev/simulator-work'
        shutil.copytree(source, work/'simulator', ignore=shutil.ignore_patterns('.runtime', '.venv', '__pycache__', '*.pyc', 'test-results'))
        import json
        lock = json.loads((source/'backend/engine.lock.json').read_text())
        revision = (lock.get('revision') or lock['snapshot']) if kind == 'web' else lock['snapshot'][:7]
        engine = '.runtime/engine-' + revision
        shutil.copytree(source/engine, work/'simulator'/engine)
        shutil.copytree(source/'.runtime/deps', work/'simulator/.runtime/deps', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        cwd, tests, env = work/'simulator', 'tests', dict(os.environ, PYTHONPATH=str(work/'simulator/.runtime/deps'))
    with (root/f'.dev/validation-{kind}.log').open('w') as log:
        commande = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', tests, '-v']
        if kind == 'permissions':
            # Les tests "reels" exigent une VM jetable et creent des comptes.
            # Les tests isoles changent seulement l'UID des processus enfants sous /tmp.
            commande += ['-p', '*isole*.py']
        result = subprocess.run(commande, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
    print((root/f'.dev/validation-{kind}.log').read_text()[-4500:])
    sys.exit(result.returncode)
