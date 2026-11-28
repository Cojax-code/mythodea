"""Installation explicite des hooks officiels, à lancer par l'administrateur."""
import argparse
import os
from pathlib import Path
import shlex
import pwd
import stat

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
    scanner = (source / 'bash/.interne/prototype_crypte_scan.sh').read_text(encoding='utf-8')
    scanner = scanner.replace('crypte_commence', marques['debut']).replace('crypte_fin', marques['fin'])
    contenu = ('. ' + shlex.quote(str(destination / 'terminal.sh')) + '\n'
               f'_crypte_client={shlex.quote(str(destination / "crypte_client.py"))}\n'
               f'_crypte_socket={shlex.quote(str(c["game_path"] / ".systeme/communication/crypte.sock"))}\n'
               + scanner + '\n' + (source / 'bash/.interne/crypte_transport.sh').read_text(encoding='utf-8'))
    joueurs = c.get('joueurs', config.configuration_mode('survie')['joueurs'])
    comptes = [c.get('acteurs', {}).get(j, {}).get('proprietaire_linux', j) for j in joueurs]
    selection = '|'.join(shlex.quote(j) for j in comptes)
    for p, texte in ((destination / 'crypte_client.py', (source / 'python/crypte_client.py').read_text(encoding='utf-8')),
                     (destination / 'terminal.sh', (source / 'bash/.interne/terminal.sh').read_text(encoding='utf-8')),
                     (destination / 'replay.bash', (source / 'bash/.interne/replay.sh').read_text(encoding='utf-8')),
                     (destination / 'crypte.bash', contenu),
                     (profil, 'if [ -n "${BASH_VERSION-}" ]; then\n'
                      '  case $- in *i*)\n'
                      '    case "$(id -un)" in ' + selection + ')\n'
                      '      . ' + shlex.quote(str(destination / 'terminal.sh')) + '\n'
                      '      . ' + shlex.quote(str(destination / 'crypte.bash')) + '\n'
                      '      . ' + shlex.quote(str(destination / 'replay.bash')) + '\n'
                      '      _mythodea_installer_prompt\n'
                      '    ;; esac\n  ;; esac\nfi\n')):
        etat.ecrire_prive(p, texte)
        os.chmod(p, 0o644)


def installer_bashrc(c, profil):
    """Ajouter un seul chargement après la configuration personnelle, sans l'écraser."""
    from cycle_linux import sans_liens
    for joueur in c['joueurs']:
        compte = pwd.getpwnam(c['acteurs'][joueur]['proprietaire_linux'])
        home = c.get('homes', {}).get(joueur, Path(compte.pw_dir))
        chemin = home / '.bashrc'
        sans_liens(chemin)
        if home.stat().st_uid != compte.pw_uid:
            raise RuntimeError(f'Home inattendu : {home}')
        marqueur = '# Mythodea : hooks joueurs (installation administrative)'
        fd = os.open(chemin, os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'r+', encoding='utf-8') as fichier:
            infos = os.fstat(fichier.fileno())
            if (not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1
                    or infos.st_uid not in (0, compte.pw_uid) or infos.st_size > 1024 * 1024):
                raise RuntimeError(f'.bashrc non ordinaire : {chemin}')
            contenu = fichier.read()
            if marqueur not in contenu:
                fichier.write('\n' + marqueur + '\n'
                              + '[ ! -r ' + shlex.quote(str(profil)) + ' ] || . '
                              + shlex.quote(str(profil)) + '\n')
                fichier.flush()
                os.fsync(fichier.fileno())
            if infos.st_size == 0:
                os.fchown(fichier.fileno(), compte.pw_uid, compte.pw_gid)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game', type=Path, default=config.game_path)
    p.add_argument('--destination', type=Path, default=Path('/usr/local/lib/mythodea'))
    p.add_argument('--profil', type=Path, default=Path('/etc/profile.d/mythodea-crypte.sh'))
    a = p.parse_args()
    if a.game == config.game_path:
        config.verifier_partition_plateau()
    c = dict(config.configuration_mode('survie'), game_path=a.game)
    installer(c, a.destination, a.profil)
    installer_bashrc(c, a.profil)


if __name__ == '__main__':
    main()
