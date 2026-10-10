"""Installation explicite des hooks officiels, à lancer par l'administrateur."""
import argparse
import os
from pathlib import Path
import shlex

import crypte
import config
import etat


def installer(c, destination, profil):
    if os.geteuid() != 0:
        raise PermissionError('Installation réservée à root.')
    config.verifier_structure_actuelle(dict(c, mode='survie', joueurs=('j1', 'j2')))
    etat.preparer_systeme_survie(dict(c, groupe_allie=c.get('groupe_allie', 'mythodea_allies')))
    from cycle_linux import sans_liens
    for p in (destination, profil.parent):
        sans_liens(p)
        p.mkdir(parents=True, exist_ok=True)
        os.chown(p, 0, 0)
        os.chmod(p, 0o755)
    source = Path(__file__).resolve().parents[1]
    marques = crypte.configuration(c)
    scanner = (source / 'bash/prototype_crypte_scan.sh').read_text(encoding='utf-8')
    scanner = scanner.replace('crypte_commence', marques['debut']).replace('crypte_fin', marques['fin'])
    contenu = (f'_crypte_client={shlex.quote(str(destination / "crypte_client.py"))}\n'
               f'_crypte_socket={shlex.quote(str(c["game_path"] / ".systeme/communication/crypte.sock"))}\n'
               + scanner + '\n' + (source / 'bash/crypte_transport.sh').read_text(encoding='utf-8'))
    for p, texte in ((destination / 'crypte_client.py', (source / 'python/crypte_client.py').read_text(encoding='utf-8')),
                     (destination / 'crypte.bash', contenu),
                     (profil, 'if [ -n "${BASH_VERSION-}" ]; then\n'
                      '  case $- in *i*) . ' + shlex.quote(str(destination / 'crypte.bash')) + ' ;; esac\nfi\n')):
        etat.ecrire_prive(p, texte)
        os.chmod(p, 0o644)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game', type=Path, default=Path('/home/game'))
    p.add_argument('--destination', type=Path, default=Path('/usr/local/lib/mythodea'))
    p.add_argument('--profil', type=Path, default=Path('/etc/profile.d/mythodea-crypte.sh'))
    a = p.parse_args()
    installer({'game_path': a.game}, a.destination, a.profil)


if __name__ == '__main__':
    main()
