"""Découverte SSH simulée et écritures sur PTY isolés, jamais sur une partie."""
import os
import subprocess
import unittest
from unittest.mock import patch

import test_cycle_survie
from support_cycle import GelSimule


class NotificationsSurvie(unittest.TestCase):
    def setUp(self):
        test_cycle_survie.CycleSurvie.setUp(self)
        self.linux = object.__new__(self.cycle_linux.Linux)
        self.linux.configuration = self.profil
        self.linux.uids = [1001, 1002]
        self.linux.geles = []

    activer = test_cycle_survie.CycleSurvie.activer

    def decouvrir(self, sessions, enfants=None):
        enfants = enfants or {}
        def commande(args, **kwargs):
            if args[1] == 'list-sessions':
                texte = '\n'.join(f'{s} {i["User"]} {i["Name"]}' for s, i in sessions.items())
            elif args[1] == 'show-session':
                texte = '\n'.join(f'{k}={v}' for k, v in sessions[args[2]].items())
            else:
                self.assertEqual(args[:2], ['ps', '--ppid'])
                texte = enfants.get(args[2], '')
            return subprocess.CompletedProcess(args, 0, texte, '')
        with patch.object(self.cycle_linux.subprocess, 'run', side_effect=commande):
            return self.linux.terminaux_ssh()

    @staticmethod
    def session(uid='1001', nom='j1', tty='', leader='200', **autres):
        return dict(User=uid, Name=nom, Service='sshd', State='active',
                    TTY=tty, Leader=leader, **autres)

    def test_pi_tty_vide_leader_root_et_toutes_sessions(self):
        sessions = {'1': self.session(), '2': self.session('1002', 'j2', leader='300'),
                    '3': self.session(leader='400')}
        enfants = {'200': '1001 sshd-session: j1@pts/1\n',
                   '300': '1002 sshd-session: j2@pts/2\n',
                   '400': '1001 sshd-session: j1@pts/3\n'}
        self.assertEqual(self.decouvrir(sessions, enfants),
                         [(1001, 'pts/1'), (1001, 'pts/3'), (1002, 'pts/2')])

    def test_tty_logind_et_ancien_sshd_sans_doublon(self):
        sessions = {'1': self.session(tty='pts/1'), '2': self.session(tty='/dev/pts/1'),
                    '3': self.session()}
        self.assertEqual(self.decouvrir(sessions, {'200': '1001 sshd: j1@pts/2'}),
                         [(1001, 'pts/1'), (1001, 'pts/2')])

    def test_ignore_autre_compte_service_session_fermee_et_nom_incoherent(self):
        sessions = {'1': self.session('999', 'admin', 'pts/0'),
                    '2': dict(self.session(tty='pts/1'), Service='login'),
                    '3': dict(self.session(tty='pts/2'), State='closing'),
                    '4': self.session(nom='admin', tty='pts/3'),
                    '5': dict(self.session(tty='pts/4'), State='online')}
        self.assertEqual(self.decouvrir(sessions), [(1001, 'pts/4')])

    def test_ignore_enfant_mauvais_uid_nom_et_session_sans_terminal(self):
        enfants = {'200': '0 sshd-session: j1@pts/1\n'
                   '1001 sshd-session: j2@pts/2\n'
                   '1001 bash j1@pts/3\n'
                   '1001 sshd-session: j1@notty\n'
                   '1001 sshd-session: j1@pts/../../tmp/message\n'}
        self.assertEqual(self.decouvrir({'1': self.session()}, enfants), [])

    def test_absence_session_et_deconnexion(self):
        self.assertEqual(self.decouvrir({}), [])
        resultats = [subprocess.CompletedProcess([], 0, '1 1001 j1\n', ''),
                     subprocess.CompletedProcess([], 1, '', 'Session disparue')]
        with patch.object(self.cycle_linux.subprocess, 'run', side_effect=resultats), self.assertLogs():
            self.assertEqual(self.linux.terminaux_ssh(), [])

    def test_echec_logind_non_masque(self):
        with patch.object(self.cycle_linux.subprocess, 'run', side_effect=OSError('logind absent')):
            with self.assertRaises(OSError):
                self.linux.annoncer('FIN DU TOUR')

    def test_envoi_complet_avant_retour_et_pause_avant_gel(self):
        evenements = []
        with patch.object(self.linux, 'terminaux_ssh', return_value=[
                (1001, 'pts/1'), (1001, 'pts/1'), (1002, 'pts/2')]), \
                patch.object(self.linux, 'ecrire_terminal',
                             side_effect=lambda *a: evenements.append(a) or True), \
                patch.object(self.cycle_linux.time, 'sleep',
                             side_effect=lambda n: evenements.append(('attente', n))):
            self.linux.annoncer('FIN')
            evenements.append(('gel',))
        self.assertEqual(evenements, [(1001, 'pts/1', 'FIN'), (1002, 'pts/2', 'FIN'),
                                      ('attente', 0.2), ('gel',)])

    def test_echec_ecriture_tente_aussi_les_autres_terminaux(self):
        with patch.object(self.linux, 'terminaux_ssh', return_value=[(1001, 'pts/1'), (1002, 'pts/2')]), \
                patch.object(self.linux, 'ecrire_terminal', side_effect=[BlockingIOError(), True]) as ecrire:
            with self.assertRaisesRegex(RuntimeError, 'Annonce incomplète'):
                self.linux.annoncer('FIN')
            self.assertEqual(ecrire.call_count, 2)

    def test_annonce_apres_gel_refusee(self):
        self.linux.geles = ['slice']
        with patch.object(self.linux, 'terminaux_ssh') as chercher:
            with self.assertRaisesRegex(RuntimeError, 'précéder le gel'):
                self.linux.annoncer('FIN')
            chercher.assert_not_called()

    def test_capture_et_publication_ecrivent_avant_chaque_gel(self):
        gel = GelSimule()
        gestion = self.cycle_linux.Generations(self.profil, gel)
        evenements = []
        def ecrire(*args):
            self.assertFalse(gel.gele)
            evenements.append('ecriture')
            return True
        geler = gel.geler
        def gel_apres_envoi():
            evenements.append('gel')
            geler()
        with patch.object(gel, 'annoncer', side_effect=self.linux.annoncer), \
                patch.object(gel, 'geler', side_effect=gel_apres_envoi), \
                patch.object(self.linux, 'terminaux_ssh', return_value=[(1001, 'pts/1'), (1002, 'pts/2')]), \
                patch.object(self.linux, 'ecrire_terminal', side_effect=ecrire), \
                patch.object(self.cycle_linux.time, 'sleep'):
            self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        self.assertEqual(evenements, ['ecriture', 'ecriture', 'gel'] * 2)

    def test_echec_annonce_empeche_le_gel(self):
        gel = GelSimule()
        gestion = self.cycle_linux.Generations(self.profil, gel)
        with patch.object(gel, 'annoncer', side_effect=self.linux.annoncer), \
                patch.object(self.linux, 'terminaux_ssh', return_value=[(1001, 'pts/1')]), \
                patch.object(self.linux, 'ecrire_terminal', side_effect=OSError('TTY bloqué')):
            with self.assertRaisesRegex(RuntimeError, 'Annonce incomplète'):
                self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        self.assertNotIn(('gel', None), gel.evenements)

    @unittest.skipUnless(os.name == 'posix', 'PTY Linux requis')
    def test_ecriture_reelle_pty_et_proprietaire(self):
        maitre, esclave = os.openpty()
        self.addCleanup(os.close, maitre)
        self.addCleanup(os.close, esclave)
        tty = os.ttyname(esclave).removeprefix('/dev/')
        uid = os.fstat(esclave).st_uid
        with self.assertLogs(), patch.object(self.cycle_linux.os, 'write') as ecrire:
            self.assertFalse(self.linux.ecrire_terminal(uid + 1, tty, 'INTERDIT'))
            ecrire.assert_not_called()
        self.assertTrue(self.linux.ecrire_terminal(uid, tty, 'RÉSOLUTION EN COURS'))
        os.set_blocking(maitre, False)
        self.assertIn('RÉSOLUTION EN COURS'.encode(), os.read(maitre, 4096))

    @unittest.skipUnless(os.name == 'posix', 'PTY Linux requis')
    def test_proprietaire_change_apres_ouverture_refuse(self):
        maitre, esclave = os.openpty()
        self.addCleanup(os.close, maitre)
        self.addCleanup(os.close, esclave)
        tty = os.ttyname(esclave).removeprefix('/dev/')
        infos = list(os.fstat(esclave))
        uid = infos[4]
        infos[4] = uid + 1
        with patch.object(self.cycle_linux.os, 'fstat', return_value=os.stat_result(infos)), \
                patch.object(self.cycle_linux.os, 'write') as ecrire, self.assertLogs():
            self.assertFalse(self.linux.ecrire_terminal(uid, tty, 'INTERDIT'))
            ecrire.assert_not_called()

    @unittest.skipUnless(os.name == 'posix', 'Drapeaux Linux requis')
    def test_fichier_ordinaire_et_lien_refuses(self):
        fichier = self.racine / 'ordinaire'
        fichier.write_text('intact')
        lien = self.racine / 'lien'
        lien.symlink_to(fichier)
        for chemin in (fichier, lien):
            infos = chemin.lstat()
            with patch.object(self.cycle_linux.Path, 'lstat', return_value=infos), \
                    patch.object(self.cycle_linux.os, 'open') as ouvrir, self.assertLogs():
                self.assertFalse(self.linux.ecrire_terminal(infos.st_uid, 'pts/1', 'INTERDIT'))
                ouvrir.assert_not_called()
        self.assertEqual(fichier.read_text(), 'intact')

    def test_chemin_hors_pts_refuse(self):
        for tty in ('../tmp/message', '/dev/pts/1', 'pts/1/../../null'):
            with self.assertRaises(ValueError):
                self.linux.ecrire_terminal(1001, tty, 'INTERDIT')


if __name__ == '__main__':
    unittest.main()
