"""Exécute une copie des sources sur le disque Linux, dans un dossier jetable."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parent.parent
kind = sys.argv[1]
with tempfile.TemporaryDirectory(prefix='mythodea-validation-') as directory:
    work = Path(directory)
    if kind == 'engine':
        for name in ('python', 'bash', '.dev/tests', '.dev/exemples'):
            shutil.copytree(root/name, work/name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for path in root.iterdir():
            if path.is_file():
                shutil.copy2(path, work/path.name)
        cwd, tests, env = work, '.dev/tests', os.environ.copy()
    else:
        source = root/'.dev/simulator-work'
        shutil.copytree(source, work/'simulator', ignore=shutil.ignore_patterns('.runtime', '.venv', '__pycache__', '*.pyc', 'test-results'))
        import json
        lock = json.loads((source/'backend/engine.lock.json').read_text())
        engine = '.runtime/engine-' + lock['snapshot'][:7]
        shutil.copytree(source/engine, work/'simulator'/engine)
        shutil.copytree(source/'.runtime/deps', work/'simulator/.runtime/deps', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        cwd, tests, env = work/'simulator', 'tests', dict(os.environ, PYTHONPATH=str(work/'simulator/.runtime/deps'))
    with (root/f'.dev/validation-{kind}.log').open('w') as log:
        result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', tests, '-v'], cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
    print((root/f'.dev/validation-{kind}.log').read_text()[-4500:])
    sys.exit(result.returncode)
