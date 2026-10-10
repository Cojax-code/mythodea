"""Accueil, publication et refus des anciens plateaux, en isolation."""
import unittest
from unittest.mock import patch

import test_cycle_survie
from support_cycle import GelSimule


class AccueilSurvie(unittest.TestCase):
    setUp = test_cycle_survie.CycleSurvie.setUp
    activer = test_cycle_survie.CycleSurvie.activer
    general = test_cycle_survie.CycleSurvie.general

    def hotel(self, joueur='j1'):
        return self.config.game_path / 'village' / joueur / 'hotel_de_ville'

    def test_journal_progressif_passif_personnalise(self):
        self.plateau.preparer_accueil(self.profil)
        for j in self.profil['joueurs']:
            journal = self.hotel(j) / 'journal_du_Toonitruand'
            self.assertEqual([p.name for p in journal.iterdir()], ['vague_0.txt'])
            texte = (journal / 'vague_0.txt').read_text(encoding='utf-8')
            self.assertIn(f'ls -l /home/{j}', texte)
            self.assertIn('village/clocher/etat_tour.txt', texte)
        self.plateau.preparer_accueil(self.profil, 1)
        journal = self.hotel() / 'journal_du_Toonitruand'
        self.assertEqual({p.name for p in journal.iterdir()}, {'vague_0.txt', 'vague_1.txt'})
        self.plateau.preparer_accueil(self.profil, 20)
        self.assertEqual(len(list(journal.iterdir())), 3)

    def test_courrier_brouillon_preserve_sans_traitement(self):
        self.plateau.preparer_accueil(self.profil)
        envoi = self.hotel() / 'courrier/envoie_message.txt'
        envoi.write_text('OUI\n')
        self.plateau.preparer_accueil(self.profil, 1)
        self.assertEqual(envoi.read_text(), 'OUI\n')
        self.assertIn('aucune requête traitée',
                      (envoi.parent / 'reception_message.txt').read_text(encoding='utf-8'))
        self.assertEqual({p.name for p in envoi.parent.iterdir()},
                         {'envoie_message.txt', 'reception_message.txt', 'liste_requetes.txt'})

    def test_publication_rapport_journal_et_clocher_vivant(self):
        gel = GelSimule()
        gestion = self.cycle_linux.Generations(self.profil, gel)
        gestion.preparer()
        gestion.afficher(1, 'actions', 0)
        log = self.config.game_path / 'village/clocher/suivi_tour.log'
        inode = log.stat().st_ino
        self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        self.assertEqual(log.stat().st_ino, inode)
        self.assertFalse((gestion.generation / 'capture/game/village/clocher').exists())
        for j in self.profil['joueurs']:
            self.assertEqual((self.hotel(j) / 'rapport.txt').read_bytes(),
                             self.config.rapport_court_path.read_bytes())
            texte = (self.hotel(j) / 'journal_du_Toonitruand/vague_2.txt').read_text(encoding='utf-8')
            self.assertNotIn('generations', texte)
            self.assertIn(str(self.config.game_path), texte)
        gestion.permissions_actions()
        self.assertEqual((self.hotel() / 'rapport.txt').read_bytes(), self.config.rapport_court_path.read_bytes())

    def test_anciens_chemins_refuses_avant_ecriture(self):
        for nom in ('systeme', 'clocher', 'communication', 'village/j1/poste',
                    'village/j2/clocher', 'village/j1/renforts'):
            with self.subTest(nom=nom):
                ancien = self.config.game_path / nom
                ancien.mkdir(parents=True)
                souvenir = ancien / 'a_conserver.txt'
                souvenir.write_text('partie historique')
                with self.assertRaisesRegex(RuntimeError, 'Ancienne structure incompatible'):
                    self.survie.ouvrir_tour_survie(self.profil)
                with self.assertRaisesRegex(RuntimeError, 'Ancienne structure incompatible'):
                    self.securite.verifier_tous_les_deplacements(self.profil)
                self.assertEqual(souvenir.read_text(), 'partie historique')
                souvenir.unlink()
                ancien.rmdir()

    def test_preference_5_ne_deborde_pas_au_village(self):
        chemin = self.general(territoire='est_1')
        with (chemin / 'fiche.txt').open('a') as f:
            f.write('\nposition_surnombre=5\n')
        general = {'chemin': chemin, 'nom': chemin.name, 'joueur': 'j1', 'emplacement': '1'}
        self.assertEqual(self.mouvements.preparer_retraites_surnombre(
            [general], self.config.game_path / 'est_1', self.profil), [])
        self.assertTrue(chemin.exists())
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {})

    def test_annonce_apres_preparation_uniquement_au_demarrage(self):
        (self.config.game_path / '.systeme/cycle_survie.json').unlink()
        self.profil.update(duree_phase_action_secondes=0, duree_consultation_secondes=0)
        def verifier(gestion):
            self.assertTrue((self.hotel() / 'journal_du_Toonitruand/vague_0.txt').exists())
            self.assertTrue((gestion.game / 'village/clocher/etat_tour.txt').exists())
        with patch.object(self.cycle_linux.Generations, 'annoncer_debut', autospec=True,
                          side_effect=verifier) as annonce:
            self.survie.lancer_partie_survie(self.profil, 1)
            self.survie.lancer_partie_survie(self.profil, 1)
            self.assertEqual(annonce.call_count, 1)

    def test_preparation_echouee_sans_annonce(self):
        (self.config.game_path / '.systeme/cycle_survie.json').unlink()
        with patch.object(self.plateau, 'reparer_structure', side_effect=OSError('plateau indisponible')), \
                patch.object(self.cycle_linux.Generations, 'annoncer_debut') as annonce:
            with self.assertRaises(OSError):
                self.survie.lancer_partie_survie(self.profil, 1)
            annonce.assert_not_called()
