"""Déclarations QG et retraites réelles, sans partie ni comptes système réels."""
import copy
import os
import random
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
import test_ordres_effets_v2 as aides
import commandement
import ordres_calculs_v2
import ordres_pipeline


class QgRetraites(unittest.TestCase):
    setUp = aides.EffetsOrdres.setUp
    activer = aides.EffetsOrdres.activer
    general = aides.EffetsOrdres.general
    creer = aides.EffetsOrdres.creer
    infos = aides.EffetsOrdres.infos
    modules = aides.EffetsOrdres.modules
    speciale = aides.EffetsOrdres.speciale
    troupe = aides.EffetsOrdres.troupe
    ordres = aides.EffetsOrdres.ordres

    def declarer(self, g, bloc='avant'):
        (g['chemin'] / 'qg.txt').write_text(bloc, encoding='utf-8')

    def test_declaration_libre_sans_creation_ni_reparation(self):
        g = self.troupe('j1', 'piquier')
        lire = self.combats.generaux.lire_declaration_qg
        self.assertIsNone(lire(g['chemin']))
        for contenu in ('avant', 'avant\n', ' avant\r\n'):
            self.declarer(g, contenu)
            self.assertEqual(lire(g['chemin']), 'avant')
        for contenu in ('', 'droite', 'AVANT', '../avant', 'avant\narriere', 'a'*65):
            self.declarer(g, contenu)
            self.assertIsNone(lire(g['chemin']))
        (g['chemin'] / 'gauche').rmdir()
        self.declarer(g, 'gauche')
        self.assertIsNone(lire(g['chemin']))
        self.assertFalse((g['chemin'] / 'gauche').exists())

    def test_declaration_refuse_liens_et_fichiers_non_ordinaires(self):
        g = self.troupe('j1', 'piquier')
        f = g['chemin'] / 'qg.txt'
        autre = g['chemin'] / 'autre.txt'
        autre.write_text('avant')
        f.symlink_to(autre)
        self.assertIsNone(self.combats.generaux.lire_declaration_qg(g['chemin']))
        f.unlink()
        os.link(autre, f)
        self.assertIsNone(self.combats.generaux.lire_declaration_qg(g['chemin']))
        f.unlink()
        f.mkdir()
        self.assertIsNone(self.combats.generaux.lire_declaration_qg(g['chemin']))

    def test_selection_multiple_annule_meme_pc_inegaux_et_instinctif_admis(self):
        a = dict(nature='instinctif', qg='avant', effectif_bloc_qg=1, points_commandement=1)
        b = dict(nature='stratege', qg='arriere', effectif_bloc_qg=1, points_commandement=100)
        calcul = Mock(side_effect=AssertionError('Les PC ne départagent plus les QG.'))
        self.assertIs(commandement.selectionner_qg([a], calcul), a)
        self.assertIsNone(commandement.selectionner_qg([a, b], calcul))
        calcul.assert_not_called()

    def test_bataille_cooperative_qg_annules_sans_reselection(self):
        a = self.troupe('j1', 'piquier')
        b = self.troupe('j2', 'archer', place='2')
        self.declarer(a); self.declarer(b)
        territoire = self.config.game_path / 'est_3'
        with ordres_pipeline.bataille(territoire, self.profil) as contexte:
            quartier = contexte['quartiers']['allies']
            self.assertIsNone(quartier.general)
            (b['chemin'] / 'qg.txt').unlink()
            with ordres_pipeline.bataille(territoire, self.profil) as imbrique:
                self.assertIs(imbrique, contexte)
                self.assertIsNone(quartier.general)
        with ordres_pipeline.bataille(territoire, self.profil) as suivant:
            self.assertEqual(suivant['quartiers']['allies'].general['joueur'], 'j1')

    def test_destruction_qg_memorisee_avant_repeuplement_et_exception(self):
        a = self.troupe('j1', 'piquier', 1)
        self.speciale(a, 'archer', 8, 'arriere')
        self.ordres(a)
        self.declarer(a)
        with self.assertRaisesRegex(RuntimeError, 'arrêt'):
            with ordres_pipeline.bataille(self.config.game_path / 'est_3', self.profil) as contexte:
                self.combats.supprimer_unites(self.infos(a), 0, a)
                self.assertTrue(contexte['quartiers']['allies'].detruit)
                self.speciale(a, 'piquier', 9)
                ordres_pipeline.verifier_qg()
                self.assertTrue(contexte['quartiers']['allies'].detruit)
                raise RuntimeError('arrêt')
        self.assertIsNone(ordres_pipeline._bataille.get())

    def preparer_fuite(self, joueur='j1', territoire='est_3', adversaire=4):
        chemin = self.general(joueur, territoire=territoire, nombre=0)
        a = dict(joueur=joueur, nom=chemin.name, chemin=chemin, emplacement='1')
        for n in range(8):
            self.speciale(a, 'piquier', n)
        self.ordres(a, [1011], moral=100)
        self.general('bot', numero=99, territoire=territoire, nombre=adversaire, equipement='pique')
        return a

    def test_choca_fuite_deux_joueurs_sans_manoeuvre_ni_perte_identites(self):
        for joueur in ('j1', 'j2'):
            with self.subTest(joueur=joueur):
                a = self.preparer_fuite(joueur)
                avant = {self.soldats.marqueur(u): copy.deepcopy(self.soldats.charger()[self.soldats.marqueur(u)])
                         for u in self.infos(a)['unites']}
                captures = []
                original = self.combats.combat_entre_generaux
                def observer(g1, g2):
                    r = original(g1, g2)
                    captures.append(r)
                    return r
                with patch.object(self.combats, 'combat_entre_generaux', side_effect=observer):
                    r = self.survie.resoudre_cascade(self.config.game_path / 'est_3', self.profil)
                self.assertEqual(len(captures), 1)
                self.assertEqual(captures[0]['manoeuvres'], [])
                self.assertEqual(captures[0]['fuites'][0]['destination'], 'est_2')
                destination = r['retraites'][0]['chemin']
                self.assertTrue(destination.is_dir())
                self.assertFalse(a['chemin'].exists())
                apres = self.soldats.charger()
                for identifiant, fiche in avant.items():
                    for champ in ('type', 'batailles'):
                        self.assertEqual(apres[identifiant][champ], fiche[champ])
                self.assertEqual(sum(apres[i]['blessures'] for i in avant), 4)
                self.assertEqual({self.soldats.marqueur(u) for u in (destination / 'avant').iterdir()}, set(avant))

    def test_choca_fuite_village_ne_teleporte_pas(self):
        a = self.preparer_fuite(territoire='village', adversaire=20)
        self.rapports.preparer_rapports(self.profil)
        r = self.survie.resoudre_cascade(self.config.game_path / 'village', self.profil)
        self.assertEqual(r['retraites'], [])
        # La retraite refusée n'arrête pas le combat : les 8 piquiers blessés
        # au choc perdent ensuite contre les 12 ennemis encore présents.
        self.assertFalse(a['chemin'].is_dir())
        self.assertIn('aucune retraite automatique',
                      (self.config.rapports_territoires_dir / 'village.txt').read_text())

    def test_choca_fuite_bot_sur_destination_refuse_retraite(self):
        self.preparer_fuite(adversaire=20)
        self.general('bot', numero=100, territoire='est_2', nombre=4, equipement='pique')
        r = self.survie.resoudre_cascade(self.config.game_path / 'est_3', self.profil)
        self.assertEqual(r['retraites'], [])

    def test_charge_deux_tirages_independants_et_graine(self):
        tirer = ordres_calculs_v2.tirages_charges_suicidaires
        hasard = Mock(randrange=Mock(side_effect=[0, 0]))
        self.assertEqual(tirer(4, 4, True, True, hasard), (True, True))
        self.assertEqual(hasard.randrange.call_count, 2)
        hasard = Mock(randrange=Mock(side_effect=[25, 24]))
        self.assertEqual(tirer(100, 100, True, True, hasard), (False, True))
        self.assertEqual(tirer(3, 3, True, True, random.Random(1)), (False, False))
        self.assertEqual(tirer(200, 200, True, True, random.Random(12)),
                         tirer(200, 200, True, True, random.Random(12)))
        hasard = Mock()
        self.assertEqual(tirer(400, 400, False, False, hasard), (False, False))
        hasard.randrange.assert_not_called()

    def preparer_tour(self):
        a = self.preparer_fuite(adversaire=20)
        self.declarer(a)
        self.activer(0)
        self.rapports.preparer_rapports(self.profil)
        self.rapports.ecrire_rapport_court('TOUR PUBLIC INITIAL')
        return a, {p: p.read_bytes() for p in self.config.rapport_dir.rglob('*') if p.is_file()}

    def test_tour_fuite_qg_publication_identites_blessures_xp(self):
        a, rapports_avant = self.preparer_tour()
        ids = {self.soldats.marqueur(u) for u in self.infos(a)['unites']}
        original = ordres_pipeline.fuir_apres_choc
        executions = []
        def observer(generaux):
            resultat = original(generaux)
            if resultat:
                executions.append(resultat)
                self.assertEqual({p: p.read_bytes() for p in rapports_avant}, rapports_avant)
            return resultat
        with patch.object(ordres_pipeline, 'fuir_apres_choc', side_effect=observer), \
                patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, random.Random(21))
        self.assertEqual(len(executions), 1)
        position, chemin = self.generaux.trouver_position_general('j1', a['nom'], self.profil)
        self.assertEqual(position, 'est_2')
        self.assertEqual((chemin / 'qg.txt').read_text(), 'avant')
        self.assertEqual({self.soldats.marqueur(u) for u in (chemin / 'avant').iterdir()}, ids)
        registre = self.soldats.charger()
        self.assertEqual({registre[i]['batailles'] for i in ids}, {1})
        self.assertEqual({registre[i]['blessures'] for i in ids}, {1})
        texte = (self.config.rapports_territoires_dir / 'est_3.txt').read_text()
        self.assertIn('QG allies : j1 general1', texte)
        self.assertIn('Choca_fuite', texte)
        self.assertIsNone(ordres_pipeline._bataille.get())
        self.assertIsNone(ordres_pipeline._retraite.get())

    def test_interruption_reservation_ne_transfere_pas_et_reprise_sans_rejeu(self):
        a, rapports_avant = self.preparer_tour()
        soldats_avant = copy.deepcopy(self.soldats.charger())
        original = ordres_pipeline.fuir_apres_choc
        def interrompre(generaux):
            resultat = original(generaux)
            if resultat:
                raise RuntimeError('interruption après réservation Choca_fuite')
            return resultat
        with patch.object(ordres_pipeline, 'fuir_apres_choc', side_effect=interrompre), \
                patch.object(self.survie, 'creer_vague_est', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'interruption après réservation'):
                self.survie.resoudre_tour_survie(self.profil, random.Random(21))
        self.assertEqual({p: p.read_bytes() for p in rapports_avant}, rapports_avant)
        self.assertEqual(self.soldats.charger(), soldats_avant)
        self.assertTrue(a['chemin'].is_dir())
        self.assertIsNone(ordres_pipeline._bataille.get())
        self.assertIsNone(ordres_pipeline._retraite.get())
        self.assertIsNone(ordres_pipeline._duel.get())
        with patch.object(ordres_pipeline, 'fuir_apres_choc') as effet:
            with self.assertRaises(RuntimeError):
                self.survie.resoudre_tour_survie(self.profil, random.Random(21))
            effet.assert_not_called()

    def test_choca_fuite_non_appris_ou_hors_survie_ignore(self):
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'cavalier')
        self.ordres(a, [1011]); self.ordres(b)
        with ordres_pipeline.duel(a, b) as decisions:
            self.assertEqual(decisions, [])
        self.ordres(a, texte='2-5')
        with ordres_pipeline.retraites_apres_choc(Mock()) as contexte:
            with ordres_pipeline.duel(a, b) as decisions:
                self.assertEqual(decisions, [])

    def test_fuite_acceptee_ne_combat_pas_de_nouveau_apres_frontal(self):
        a = self.preparer_fuite(adversaire=20)
        self.ordres(a, [1011], texte='1-2\n2-5', moral=100)
        captures = []
        original = self.combats.combat_entre_generaux
        def observer(g1, g2):
            captures.append((g1['nom'], g2['nom']))
            return original(g1, g2)
        with patch.object(self.combats, 'combat_entre_generaux', side_effect=observer):
            r = self.survie.resoudre_cascade(self.config.game_path / 'est_3', self.profil)
        self.assertEqual(len(captures), 1)
        self.assertEqual(len(r['retraites']), 1)
