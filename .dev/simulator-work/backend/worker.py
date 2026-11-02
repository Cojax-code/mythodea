"""Point d'entrée interne. Toujours appelé par Bubblewrap, jamais par HTTP."""
import json
import os
from pathlib import Path
import resource
import sys


def protect():
    mounts = Path("/proc/self/mountinfo").read_text().splitlines()
    for target in ("/", "/game", "/tmp"):
        if not any(line.split()[4] == target and " - tmpfs " in line for line in mounts):
            raise RuntimeError("Exécution refusée hors du conteneur jetable.")
    if os.getuid() != 0 or not os.statvfs("/engine").f_flag & os.ST_RDONLY:
        raise RuntimeError("Isolation ou montage moteur incorrect.")
    for kind, limit in ((resource.RLIMIT_AS, 256 * 1024 * 1024), (resource.RLIMIT_CPU, 5),
                        (resource.RLIMIT_FSIZE, 1024 * 1024), (resource.RLIMIT_NOFILE, 64),
                        (resource.RLIMIT_CORE, 0), (resource.RLIMIT_NPROC, 16)):
        resource.setrlimit(kind, (limit, limit))


def probe(payload):
    """Diagnostic interne utilisé par les tests Linux (non exposé dans l'API)."""
    import socket
    import signal
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    path = Path("/game/probe")
    path.write_text("privé")
    os.chown(path, 0, 0)
    checks = {"uid": os.getuid(), "private_write": path.read_text() == "privé",
              "interfaces": socket.if_nameindex(), "limits": {}, "host_hidden": True}
    for target in payload.get("host_paths", []):
        if Path(target).exists():
            checks["host_hidden"] = False
    try:
        Path(payload["host_paths"][0]).write_text("écriture interdite")
        checks["host_write_blocked"] = False
    except OSError:
        checks["host_write_blocked"] = True
    try:
        Path("/engine/config.py").write_text("interdit")
        checks["engine_readonly"] = False
    except OSError:
        checks["engine_readonly"] = True
    try:
        socket.create_connection(("127.0.0.1", payload["host_port"]), timeout=0.5).close()
        checks["network_isolated"] = False
    except OSError:
        checks["network_isolated"] = True
    try:
        bytearray(512 * 1024 * 1024)
        checks["memory_limited"] = False
    except MemoryError:
        checks["memory_limited"] = True
    try:
        with Path("/game/oversize").open("wb") as stream:
            stream.write(b"x" * (2 * 1024 * 1024))
        checks["file_limited"] = False
    except OSError:
        checks["file_limited"] = True
    for name, kind in (("cpu", resource.RLIMIT_CPU), ("memory", resource.RLIMIT_AS), ("files", resource.RLIMIT_NOFILE)):
        checks["limits"][name] = resource.getrlimit(kind)
    stat = os.statvfs("/game")
    checks["scratch_bytes"] = stat.f_blocks * stat.f_frsize
    return checks


if __name__ == "__main__":
    protect()
    sys.path.insert(0, "/app")
    payload = json.loads(sys.stdin.buffer.read(8193))
    if sys.argv[1] == "simulate":
        from backend.engine_adapter import simulate
        from backend.schema import InvalidConfiguration
        try:
            result = simulate(payload)
        except InvalidConfiguration as exc:
            result = {'invalid_configuration': str(exc)}
    elif sys.argv[1] == 'generate':
        from backend.profiles import generate
        result = generate(payload)
    elif sys.argv[1] == "probe":
        result = probe(payload)
    elif sys.argv[1] == "timeout-probe":
        import time
        time.sleep(60)
        result = {}
    else:
        raise ValueError("Opération interne inconnue.")
    print(json.dumps(result, ensure_ascii=False))
