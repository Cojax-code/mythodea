"""Transport non privilégié du scanner : aucun accès aux états privés."""
import argparse
import json
import socket
import sys


def envoyer(chemin, message):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connexion:
        connexion.settimeout(3)
        connexion.connect(chemin)
        connexion.sendall((json.dumps(message) + '\n').encode())
        with connexion.makefile('rb') as fichier:
            return json.loads(fichier.readline(16385))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--socket', required=True)
    p.add_argument('--session', type=int, required=True)
    p.add_argument('--token', default='')
    p.add_argument('--seq', type=int, default=0)
    p.add_argument('champs', nargs=7)
    args = p.parse_args()
    message = dict(zip(('event', 'line', 'command', 'status', 'cwd', 'history', 'kind'), args.champs))
    message.update(session=args.session, token=args.token, seq=args.seq)
    try:
        resultat = envoyer(args.socket, message)
        if not resultat['ok']:
            print('Crypte : ' + resultat['erreur'], file=sys.stderr)
            return 1
        if resultat.get('resultat'):
            print(resultat['resultat'])
        return 0
    except (OSError, ValueError, KeyError) as erreur:
        print(f'Crypte indisponible : {erreur}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
