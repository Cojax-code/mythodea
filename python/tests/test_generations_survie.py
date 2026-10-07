"""Générations sur disque isolé ; noyau simulé ici, testé séparément sous Linux."""
import json
import builtins
import contextlib
import io
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

import test_cycle_survie
from support_cycle import GelSimule


class GenerationsSurvie(unittest.TestCase):
    setUp = test_cycle_survie.CycleSurvie.setUp
    general = test_cycle_survie.CycleSurvie.general
    colonne = test_cycle_survie.CycleSurvie.colonne
    preference = test_cycle_survie.CycleSurvie.preference
    activer = test_cycle_survie.CycleSurvie.activer

    def gestion(self, **kwargs):
        self.gel = GelSimule()
        g = self.cycle_linux.Generations(self.profil, self.gel, **kwargs)
        g.preparer()
        return g

    @unittest.skipIf(os.name == 'nt', 'Windows interdit de renommer cet inode ouvert ; exécuté sous Linux')
    def test_ancien_fd_ne_modifie_ni_capture_ni_publication(self):
        general = self.general(territoire='home')
        ordre = general / 'ordre.txt'
        ancien = ordre.open('r+b')
        self.addCleanup(ancien.close)
        g = self.gestion()
        original = self.survie._resoudre_tour_capture
        def resoudre(prive, aleatoire):
            self.assertFalse(self.gel.gele)
            ancien.seek(0)
            ancien.write(b'2-2\n')
            ancien.flush()
            self.assertEqual((self.config.home_generation('j1') / 'general1/ordre.txt').read_text(), '1-2\n')
            return original(prive, aleatoire)
        with patch.object(self.survie, '_resoudre_tour_capture', side_effect=resoudre):
            self.survie.resoudre_tour_survie(self.profil, random.Random(4), g)
        self.assertEqual(ordre.read_text(), '1-2\n')
        ancien.seek(0)
        ancien.write(b'3-1\n')
        ancien.flush()
        self.assertEqual(ordre.read_text(), '1-2\n')
        self.assertIsNone(self.config.home_generation('j1'))

    def test_capture_liste_blanche_et_homes_personnels_intacts(self):
        self.general(territoire='home')
        home = self.racine / 'home/j1'
        (home / '.ssh').mkdir()
        (home / '.ssh/authorized_keys').write_text('cle personnelle')
        (self.config.game_path / 'systeme/recuperation.txt').write_text('hors capture')
        g = self.gestion()
        prive, homes = g.capturer(1)
        fichiers = {p.name for p in (prive['game_path'] / 'systeme').iterdir()}
        self.assertTrue(fichiers <= set(self.config.ETATS_METIER))
        self.assertFalse((homes['j1'] / '.ssh').exists())
        self.assertEqual((home / '.ssh/authorized_keys').read_text(), 'cle personnelle')
        self.assertTrue((g.generation / 'manifeste.json').exists())

    def test_capture_conserve_uid_gid_constates(self):
        chemin = self.general()
        infos = chemin.stat()
        g = self.gestion()
        prive, _ = g.capturer(1)
        copie = prive['game_path'] / 'est_3/j1/1/general1'
        self.assertIn((copie, infos.st_uid, infos.st_gid), [c.args for c in self.chown.call_args_list])

    def test_fichiers_reels_independants_et_pas_de_recursion_generations(self):
        self.general()
        g = self.gestion()
        g.capturer(1)
        capture = g.generation / 'capture/game/est_3/j1/1/general1/ordre.txt'
        travail = g.generation / 'travail/game/est_3/j1/1/general1/ordre.txt'
        travail.write_text('change')
        self.assertEqual(capture.read_text(), '1-2\n')
        self.assertFalse(list((g.generation / 'capture').rglob('generations')))

    def test_interruption_resolution_privee_ne_publie_ni_rejoue(self):
        self.general()
        g = self.gestion()
        avant = (self.config.game_path / 'est_3/j1/1/general1/ordre.txt').read_bytes()
        with patch.object(self.survie, 'creer_vague_est', side_effect=RuntimeError('panne')):
            with self.assertRaisesRegex(RuntimeError, 'panne'):
                self.survie.resoudre_tour_survie(self.profil, gestion=g)
        self.assertFalse(self.gel.gele)
        self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'recuperation')
        self.assertEqual((self.config.game_path / 'est_3/j1/1/general1/ordre.txt').read_bytes(), avant)
        with patch.object(self.securite, 'verifier_tous_les_deplacements') as audit:
            with self.assertRaises(RuntimeError):
                self.survie.resoudre_tour_survie(self.profil, gestion=g)
            audit.assert_not_called()

    def test_prolongation_et_minimum_du_gel_observables(self):
        self.profil['duree_gel_secondes'] = 10
        temps = [0.0]
        attentes = []
        def attendre(n):
            self.assertTrue(self.gel.gele)
            attentes.append(n)
            temps[0] += n
        g = self.gestion(monotone=lambda: temps[0], dormir=attendre)
        g.capturer(1)
        self.assertEqual(sum(attentes), 10)
        self.assertFalse(self.gel.gele)
        self.assertEqual(self.gel.evenements[0][0], 'annonce')
        self.assertEqual([e[0] for e in self.gel.evenements][-2:], ['gel', 'degel'])

    def test_capture_lente_signalee_avant_degel(self):
        self.profil['duree_gel_secondes'] = 10
        temps = [0.0]
        g = self.gestion(monotone=lambda: temps[0])
        original = self.cycle_linux.copier
        def lent(source, destination, verifier=lambda: None):
            if self.gel.gele:
                temps[0] = 11
            return original(source, destination, verifier)
        with patch.object(self.cycle_linux, 'copier', side_effect=lent):
            g.capturer(1)
        self.assertIn('PROLONGATION TECHNIQUE', (self.config.game_path / 'clocher/suivi_tour.log').read_text())
        self.assertFalse(self.gel.gele)

    def test_seuil_capture_provoque_recuperation(self):
        temps = [0.0]
        g = self.gestion(monotone=lambda: temps[0])
        original = self.cycle_linux.copier
        def trop_lent(source, destination, verifier=lambda: None):
            temps[0] = 121
            return original(source, destination, verifier)
        with patch.object(self.cycle_linux, 'copier', side_effect=trop_lent):
            with self.assertRaises(TimeoutError):
                self.survie.resoudre_tour_survie(self.profil, gestion=g)
        self.assertFalse(self.gel.gele)
        self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'recuperation')

    def test_interruption_publication_journalisee_sans_validation(self):
        self.general()
        g = self.gestion()
        original = self.cycle_linux.ecrire_json
        def panne(chemin, valeur):
            if chemin.name == 'publication.json' and any(o['etat'] == 'ancien_retire' for o in valeur['operations']):
                raise RuntimeError('publication interrompue')
            return original(chemin, valeur)
        with patch.object(self.cycle_linux, 'ecrire_json', side_effect=panne):
            with self.assertRaisesRegex(RuntimeError, 'publication interrompue'):
                self.survie.resoudre_tour_survie(self.profil, gestion=g)
        self.assertFalse(self.gel.gele)
        journal = json.loads((g.generation / 'publication.json').read_text())
        self.assertFalse(journal['termine'])
        self.assertTrue(journal['operations'])
        self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'recuperation')

    def test_clocher_log_append_et_photographie_courante(self):
        g = self.gestion()
        g.afficher(3, 'actions', 94)
        log = self.config.game_path / 'clocher/suivi_tour.log'
        with log.open('r', encoding='utf-8') as lecteur:
            lecteur.read()
            g.afficher(3, 'consultation', 52)
            self.assertIn('CONSULTATION', lecteur.read())
        courant = (log.parent / 'etat_tour.txt').read_text()
        self.assertIn('00:52', courant)
        self.assertNotIn('ACTIONS', courant)

    def test_contexte_prive_retabli_meme_sur_exception(self):
        ancien = self.config.chemin_etat('positions_generaux_path')
        with self.assertRaises(RuntimeError):
            with self.config.racines_generation(self.racine / 'prive', {'j1': self.racine / 'h'}):
                self.assertNotEqual(self.config.chemin_etat('positions_generaux_path'), ancien)
                raise RuntimeError()
        self.assertEqual(self.config.chemin_etat('positions_generaux_path'), ancien)

    def test_nouvelle_generation_consultation_et_rapport_prive(self):
        g = self.gestion()
        resultat = self.survie.resoudre_tour_survie(self.profil, random.Random(4), g)
        cycle = self.etat.charger_cycle_survie(self.profil)
        self.assertEqual(cycle['phase'], 'consultation')
        self.assertEqual(cycle['generation_active'], g.generation.name)
        self.assertEqual(resultat['vague'], 2)
        self.assertIn((self.config.rapport_long_path, 0o600), [c.args for c in self.chmod.call_args_list])
        self.assertIn((self.config.rapport_court_path, 0o640), [c.args for c in self.chmod.call_args_list])

    def test_verrou_ancien_non_supprime(self):
        verrou = self.config.game_path / 'systeme/verrou_cycle_survie'
        verrou.write_text('999999\n')
        with self.assertRaises(RuntimeError):
            self.survie.resoudre_tour_survie(self.profil)
        self.assertEqual(verrou.read_text(), '999999\n')

    def test_resolution_ne_lit_aucune_entree_metier_vivante(self):
        self.general()
        g = self.gestion()
        racines = [*self.profil['territoires'], self.profil['repli_path'], *g.homes.values()]
        etats = {self.config.game_path / 'systeme' / nom for nom in self.config.ETATS_METIER}
        original = self.survie._resoudre_tour_capture
        def garder(ouvrir):
            def controle(chemin, *args, **kwargs):
                if not isinstance(chemin, int):
                    p = Path(chemin)
                    self.assertNotIn(p, etats, 'lecture métier vivante')
                    self.assertFalse(any(p == r or r in p.parents for r in racines), p)
                return ouvrir(chemin, *args, **kwargs)
            return controle
        def resoudre(prive, aleatoire):
            with patch.object(builtins, 'open', garder(builtins.open)), patch.object(io, 'open', garder(io.open)):
                return original(prive, aleatoire)
        with patch.object(self.survie, '_resoudre_tour_capture', side_effect=resoudre):
            self.survie.resoudre_tour_survie(self.profil, random.Random(4), g)

    def test_partie_survie_sans_territoire_classique_dans_sorties_et_fichiers(self):
        self.general(territoire='village')
        self.profil.update(duree_phase_action_secondes=0, duree_consultation_secondes=0)
        self.etat.sauvegarder_cycle_survie({'tour': 0, 'phase': 'a_preparer'}, self.profil)
        sortie = io.StringIO()
        with contextlib.redirect_stdout(sortie):
            resultats = self.survie.lancer_partie_survie(self.profil, 2, lambda: 100)
        self.assertEqual([r['tour'] for r in resultats], [0, 1])
        self.assertTrue(resultats[1]['batailles'])
        interdits = ('terrain1', 'terrain2', 'terrain3', 'base1', 'base2')
        for nom in interdits:
            self.assertNotIn(nom, sortie.getvalue().lower())
        for chemin in self.racine.rglob('*'):
            for nom in interdits:
                self.assertNotIn(nom, str(chemin.relative_to(self.racine)).lower())
                if chemin.is_file():
                    self.assertNotIn(nom, chemin.read_text(encoding='utf-8').lower(), str(chemin))
        self.assertEqual({p.stem for p in self.config.rapports_territoires_dir.glob('*.txt')},
                         {'village', 'est_1', 'est_2', 'est_3'})
        for nom in ('etat_tour.txt', 'suivi_tour.log'):
            self.assertTrue((self.config.game_path / 'clocher' / nom).is_file())

    def test_plateau_ou_rapports_classiques_refuses_sans_modification(self):
        for nom in ('terrain1', 'terrain2', 'terrain3', 'base1', 'base2'):
            for ancien in (self.config.game_path / nom,
                           self.config.rapports_territoires_dir / (nom + '.txt')):
                ancien.parent.mkdir(parents=True, exist_ok=True)
                if ancien.suffix:
                    ancien.write_text('partie à conserver', encoding='utf-8')
                else:
                    ancien.mkdir()
                try:
                    for lancer in (self.survie.ouvrir_tour_survie,
                                   self.survie.resoudre_tour_survie,
                                   self.survie.lancer_partie_survie):
                        with self.subTest(ancien=ancien, api=lancer.__name__):
                            avant = test_cycle_survie.CycleSurvie.photo(self)
                            with self.assertRaisesRegex(RuntimeError, 'plateau dédié'):
                                lancer(self.profil)
                            self.assertEqual(test_cycle_survie.CycleSurvie.photo(self), avant)
                            self.assertTrue(ancien.exists())
                finally:
                    ancien.unlink() if ancien.is_file() else ancien.rmdir()

    def test_exemple_fin_de_tour_classique_inchange(self):
        sortie = io.StringIO()
        with contextlib.redirect_stdout(sortie):
            self.rapports.afficher_fin_de_tour()
        self.assertIn(str(self.config.rapports_territoires_dir / 'terrain1.txt'), sortie.getvalue())


if __name__ == '__main__':
    unittest.main()
