"""Exécution obligatoire dans un conteneur rootless Bubblewrap, sans repli non isolé."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import stat

from .schema import LOCK, validate, validate_generation, InvalidConfiguration

ROOT = Path(__file__).resolve().parents[1]


class SimulationUnavailable(RuntimeError):
    pass


class SimulationTimeout(RuntimeError):
    pass


class Runner:
    def __init__(self, engine=None, timeout=10):
        default_engine = ROOT / '.runtime' / f"engine-{LOCK['commit'][:7]}"
        self.engine = Path(engine or os.environ.get("MYTHODEA_ENGINE_PATH", default_engine)).absolute()
        self.timeout = timeout

    def verify_engine(self):
        if sys.platform != "linux" or not shutil.which("bwrap"):
            raise SimulationUnavailable("Le simulateur exige Linux et Bubblewrap ; aucune exécution non isolée n'est autorisée.")
        if os.getuid() == 0:
            raise SimulationUnavailable("Lancer le serveur avec un utilisateur Linux non root.")
        # Les seules sources montées sont les modules officiels vérifiés.
        # Refuser aussi les liens et fichiers supplémentaires (p. ex. sitecustomize.py).
        if any(p.is_symlink() for p in (self.engine, *self.engine.parents)) or not self.engine.is_dir():
            raise SimulationUnavailable("Moteur absent. Exécuter scripts/prepare_engine.py.")
        if set(p.name for p in self.engine.iterdir()) != set(LOCK["files"]):
            raise SimulationUnavailable("Le dossier moteur ne correspond pas aux sources verrouillées.")
        contents = {}
        for name, digest in LOCK["files"].items():
            path = self.engine / name
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise SimulationUnavailable(f"Source moteur modifiée ou invalide : {name}.")
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, 'rb') as stream:
                opened = os.fstat(stream.fileno())
                if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or
                        (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)):
                    raise SimulationUnavailable('Source remplacée pendant sa vérification.')
                data = stream.read(1024 * 1024 + 1)
            if hashlib.sha256(data).hexdigest() != digest:
                raise SimulationUnavailable(f"Source moteur modifiée ou invalide : {name}.")
            contents[name] = data
        return contents

    def command(self, operation, engine_path):
        if operation not in ("simulate", "generate", "probe", "timeout-probe"):
            raise ValueError("Opération interne inconnue.")
        args = [shutil.which("bwrap"), "--unshare-all", "--unshare-user", "--unshare-pid", "--unshare-net",
                "--uid", "0", "--gid", "0", "--die-with-parent", "--new-session", "--cap-drop", "ALL",
                "--clearenv", "--setenv", "PATH", "/usr/bin", "--setenv", "LANG", "C.UTF-8",
                "--ro-bind", "/usr", "/usr"]
        for name in ("lib", "lib64", "bin"):
            path = Path("/") / name
            if path.is_symlink():
                args += ["--symlink", os.readlink(path), str(path)]
            elif path.is_dir():
                args += ["--ro-bind", str(path), str(path)]
        args += ["--proc", "/proc", "--dev", "/dev", "--dir", "/home",
                 "--size", str(16 * 1024 * 1024), "--tmpfs", "/game",
                 "--size", str(8 * 1024 * 1024), "--tmpfs", "/tmp",
                 "--ro-bind", str(engine_path), "/engine",
                 "--ro-bind", str(ROOT / "backend"), "/app/backend",
                 "--remount-ro", "/", "--chdir", "/app",
                 "--", "/usr/bin/python3", "-I", "-B", "/app/backend/worker.py", operation]
        return args

    def execute(self, operation, payload):
        contents = self.verify_engine()
        # Snapshot des sources vérifiées : aucun accès au dépôt moteur d'origine.
        with tempfile.TemporaryDirectory(prefix="mythodea-engine-") as directory, tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            for name, data in contents.items():
                (Path(directory) / name).write_bytes(data)
            try:
                process = subprocess.Popen(self.command(operation, directory), stdin=subprocess.PIPE,
                                           stdout=output, stderr=errors, start_new_session=True,
                                           env={"PATH": "/usr/bin:/bin"})
            except OSError as exc:
                raise SimulationUnavailable("Impossible de démarrer l'environnement isolé.") from exc
            try:
                process.communicate(json.dumps(payload).encode(), timeout=self.timeout)
            except subprocess.TimeoutExpired as exc:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Le worker a terminé entre le timeout et son arrêt.
                process.communicate()
                raise SimulationTimeout("La simulation a dépassé le délai autorisé ; son environnement a été détruit.") from exc
            if process.returncode:
                errors.seek(0)
                diagnostic = errors.read(4096).decode(errors="replace")
                raise SimulationUnavailable(f"Échec de l'exécution isolée (code {process.returncode}). {diagnostic}")
            output.seek(0)
            data = output.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024:
                raise SimulationUnavailable("Rapport trop volumineux.")
            try:
                return json.loads(data)
            except (ValueError, UnicodeError) as exc:
                raise SimulationUnavailable("Réponse du moteur illisible.") from exc

    def run(self, payload):
        result = self.execute("simulate", validate(payload))
        if 'invalid_configuration' in result:
            raise InvalidConfiguration(result['invalid_configuration'])
        return result

    def generate(self, payload):
        return self.execute('generate', validate_generation(payload))
