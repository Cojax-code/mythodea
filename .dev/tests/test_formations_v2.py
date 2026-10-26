"""Compatibilités et placements dans les batailles réelles, sur plateau isolé."""
import copy
from itertools import combinations
import random
import unittest
from unittest.mock import patch

import test_qg_effets_v2 as aides
import commandement
import ordres_pipeline


class MatriceFormations(unittest.TestCase):
    def test_toutes_les_paires_interdites_annulent_les_deux_ordres(self):
        for paire in (('on_melange', 'attaque_frontale'),
                      ('on_melange', 'reserve_strategique'),
                      ('on_melange', 'retrait_tactique'),
                      ('attaque_frontale', 'reserve_strategique'),
                      ('attaque_frontale', 'muraille_humaine'),
                      ('muraille_humaine', 'retrait_tactique')):
            with self.subTest(paire=paire):
                d = commandement.compatibilite_formations(paire)
                self.assertEqual(d['annules'], set(paire))
                self.assertEqual(len(d['incompatibles']), 1)
                self.assertEqual(d['non_definies'], [])

    def test_toutes_les_paires_compatibles_et_unique_paire_ouverte(self):
        compatibles = {
            frozenset(p) for p in (
                ('muraille_humaine', 'on_melange'),
                ('muraille_humaine', 'reserve_strategique'),
                ('muraille_humaine', 'qg_nommade'),
                ('retrait_tactique', 'reserve_strategique'),
                ('qg_nommade', 'retrait_tactique'),
                ('qg_nommade', 'reserve_strategique'),
                ('qg_nommade', 'on_melange'),
                ('qg_nommade', 'attaque_frontale'))}
        for paire in combinations(sorted(commandement.FORMATIONS), 2):
            d = commandement.compatibilite_formations(paire)
            if frozenset(paire) in compatibles:
                self.assertEqual((d['annules'], d['non_definies']), (set(), []))
            elif not d['annules']:
                self.assertEqual(set(paire), {'attaque_frontale', 'retrait_tactique'})
                self.assertEqual(d['non_definies'], [paire])

    def test_conflits_multiples_sans_annulation_sequentielle(self):
        ordres = ['on_melange', 'attaque_frontale', 'reserve_strategique',
                  'muraille_humaine', 'qg_nommade', 'herisson']
        d = commandement.compatibilite_formations(ordres)
        self.assertEqual(d['annules'], set(ordres[:4]))
        self.assertEqual(len(d['incompatibles']), 4)
        self.assertEqual(d, commandement.compatibilite_formations(reversed(ordres)))

    def test_pour_l_honneur_sans_exception_implicite(self):
        self.assertEqual(commandement.compatibilite_formations(
            ['pour_l_honneur', 'herisson', 'qg_nommade'])['annules'],
            {'pour_l_honneur', 'herisson', 'qg_nommade'})

    def test_priorite_qg_retrait_et_places_vacantes(self):
        placer = commandement.sequence_formation
        self.assertEqual(placer(['1', '3', '4'], ['on_melange', 'qg_nommade'], '3'),
                         ['4', '1', '3'])
        self.assertEqual(placer(['1', '2', '4'], ['retrait_tactique', 'qg_nommade'], '2', '1'),
                         ['4', '1', '2'])
        for ordres in (['on_melange', 'attaque_frontale'],
                       ['attaque_frontale', 'retrait_tactique']):
            with self.assertRaises(ValueError):
                placer(['1', '2'], ordres)


class FormationsEnBataille(unittest.TestCase):
    setUp = aides.EffetsQG.setUp
    activer = aides.EffetsQG.activer
    general = aides.EffetsQG.general
    creer = aides.EffetsQG.creer
    infos = aides.EffetsQG.infos
    modules = aides.EffetsQG.modules
    speciale = aides.EffetsQG.speciale
    troupe = aides.EffetsQG.troupe
    ordres = aides.EffetsQG.ordres
    declarer = aides.EffetsQG.declarer
    qg = aides.EffetsQG.qg
    bataille = aides.EffetsQG.bataille

    def forces(self):
        return self.generaux.lire_forces_territoire(
            self.config.game_path / 'est_3', ordres_pipeline._bataille.get()['configuration'])

    def ordre_effectif(self, camp):
        forces = self.forces()
        actifs = self.generaux.generaux_actifs_joueur(forces, camp)
        formations = ordres_pipeline.formations_retenues(forces)
        return [g['emplacement'] for g in
                ordres_pipeline.generaux_en_formation(actifs, formations.get(camp))]

    def preparer(self, ids, joueur='j1'):
        for place in (1, 3, 4):
            g = self.troupe(joueur, 'piquier', numero=place, place=str(place))
            self.ordres(g)
        return self.qg(joueur, ids)

    def test_placement_deux_camps_et_cumul_qg_melange(self):
        for joueur in ('j1', 'j2'):
            qg = self.preparer([1015, 1016], joueur)
            with self.bataille():
                self.assertEqual(self.ordre_effectif(joueur), ['4', '3', '1', '2'])
            (qg['chemin'] / 'qg.txt').unlink()

    def test_annulation_frontal_autre_allie_garde_qg_et_individuel(self):
        a = self.troupe('j1', 'piquier')
        self.ordres(a, [1006], texte='1-2\n3-2')
        qg = self.qg('j2', [1015, 1016])
        ennemi = self.general('bot', numero=99, territoire='est_3', nombre=20)
        b = dict(joueur='bot', nom='general99', chemin=ennemi)
        with ordres_pipeline.bataille(self.config.game_path / 'est_3', self.profil):
            self.assertFalse(ordres_pipeline.frontal_autorise('allies'))
            self.assertEqual(self.ordre_effectif('allies'), ['1', '2'])
            with ordres_pipeline.duel(a, b):
                self.assertTrue(ordres_pipeline.effet(a, 'herisson'))
                self.assertTrue(ordres_pipeline.effet(a, 'qg_nommade'))
                self.assertFalse(ordres_pipeline.effet(a, 'on_melange'))
            # Les annulations ne disparaissent pas quand le porteur de 1-2 disparaît.
            self.combats.supprimer_unites(self.infos(a), 0, a)
            self.assertFalse(ordres_pipeline.frontal_autorise('allies'))
            with ordres_pipeline.bataille(self.config.game_path / 'est_3', self.profil):
                self.assertEqual(ordres_pipeline._bataille.get()['annules']['allies'],
                                 {'on_melange', 'attaque_frontale'})
        texte = (self.config.rapports_territoires_dir / 'est_3.txt').read_text()
        self.assertEqual(texte.count('annulés mutuellement'), 1)
        self.assertIn('attaque_frontale et on_melange', texte)
        self.assertIn('combinaison incompatible', texte)

    def test_annulation_avant_pc_adverses(self):
        q1 = self.preparer([1015])
        (q1['chemin'] / 'ordre.txt').write_text('1-6\n1-2')
        q2 = self.qg('j2', [1016], pc=1)
        with self.bataille():
            formations = ordres_pipeline.formations_retenues(self.forces())
            self.assertNotIn('j1', formations)
            self.assertEqual(formations['j2']['ordres'], {'qg_nommade'})
            self.assertFalse(ordres_pipeline.frontal_autorise('j1'))

    def test_pc_egalite_et_contre_ordre(self):
        self.preparer([1015])
        q2 = self.qg('j2', [1016], pc=13)
        with self.bataille():
            self.assertEqual(self.ordre_effectif('j1'), ['1', '2', '3', '4'])
            self.assertTrue(all(not f['ordres'] for f in
                                ordres_pipeline.formations_retenues(self.forces()).values()))
        self.ordres(q2, [1013], pc=1)
        registre = self.progression.charger()
        registre['j2:general2']['nature'] = 'stratege'
        self.progression.sauvegarder(registre)
        with self.bataille():
            self.assertEqual(self.ordre_effectif('j1'), ['4', '3', '2', '1'])

    def test_nature_apprentissage_et_parametre_invalides_ne_suppriment_pas_frontal(self):
        qg = self.preparer([1015])
        for nature, acquis, texte in (
                ('instinctif', [1015], '1-2\n1-6'),
                ('stratege', [], '1-2\n1-6'),
                ('stratege', [1015], '1-2\n1-6-1')):
            self.ordres(qg, acquis, texte=texte)
            registre = self.progression.charger()
            registre['j1:general2']['nature'] = nature
            self.progression.sauvegarder(registre)
            with self.bataille():
                self.assertTrue(ordres_pipeline.frontal_autorise('j1'))
                self.assertEqual(self.ordre_effectif('j1'), ['1', '2', '3', '4'])

    def test_qg_detruit_ne_transmet_plus_meme_repeuple(self):
        qg = self.preparer([1015, 1016])
        with self.bataille():
            self.assertEqual(self.ordre_effectif('j1'), ['4', '3', '1', '2'])
            self.combats.supprimer_unites(self.infos(qg), 0, qg)
            self.speciale(qg, 'piquier', 99)
            self.assertEqual(self.ordre_effectif('j1'), ['1', '2', '3', '4'])

    def resoudre_et_observer(self, ids, frontal=False):
        qg = self.preparer(ids)
        if frontal:
            with (qg['chemin'] / 'ordre.txt').open('a') as f:
                f.write('\n1-2')
        for place in (1, 2, 3, 4):
            bot = self.general('bot', numero=90 + place, territoire='est_3',
                               place=str(place), nombre=20, equipement='pique')
            (bot / 'ordre.txt').write_text('')
        trace = []
        original = self.combats.combat_entre_generaux
        def observer(a, b):
            trace.append((a['emplacement'], b['emplacement']))
            return original(a, b)
        with patch.object(self.combats, 'combat_entre_generaux', side_effect=observer):
            self.combats.resoudre_affrontement_actif(
                self.config.game_path / 'est_3', 'OFF/OFF', self.profil)
        return trace

    def test_bataille_reelle_inverse_puis_qg_dernier(self):
        self.assertEqual(self.resoudre_et_observer([1015, 1016]),
                         [('4', '1'), ('3', '1'), ('1', '1'), ('2', '1')])

    def test_frontal_qg_exclu_sans_combler_sa_place(self):
        trace = self.resoudre_et_observer([1016], frontal=True)
        self.assertEqual(trace[:3], [('1', '1'), ('3', '3'), ('4', '4')])
        self.assertEqual(trace[3:], [('2', '1')])

    def test_annulation_frontal_reel_garde_qg(self):
        self.assertEqual(self.resoudre_et_observer([1015, 1016], frontal=True),
                         [('1', '1'), ('3', '1'), ('4', '1'), ('2', '1')])

    def opposition(self, pc_frontal, pc_melange, conflit_interne=False):
        q1 = self.preparer([1002, 1015] if conflit_interne else [1002], 'j1')
        q2 = self.preparer([1015, 1016], 'j2')
        registre = self.progression.charger()
        registre['j1:general2']['points_commandement'] = pc_frontal
        registre['j2:general2']['points_commandement'] = pc_melange
        self.progression.sauvegarder(registre)
        return q1, q2

    def verifier_opposition_reelle(self, pc_1, pc_2, frontal, melange):
        self.opposition(pc_1, pc_2)
        trace = []
        original = self.combats.combat_entre_generaux
        def observer(a, b):
            r = original(a, b)
            trace.append((a['emplacement'], b['emplacement'], r))
            return r
        with self.bataille() as contexte:
            self.assertEqual(ordres_pipeline.frontal_autorise('j1'), frontal)
            self.assertEqual('on_melange' not in contexte['annules']['j2'], melange)
            with patch.object(self.combats, 'combat_entre_generaux', side_effect=observer):
                self.combats.resoudre_affrontement_actif(self.config.game_path / 'est_3',
                    'OFF/DEF', contexte['configuration'])
        texte = (self.config.rapports_territoires_dir / 'est_3.txt').read_text()
        self.assertEqual('ENGAGEMENT FRONTAL' in texte, frontal)
        self.assertIn('attaque_frontale ' + ('retenu' if frontal else 'annulé'), texte)
        self.assertIn('on_melange ' + ('retenu' if melange else 'annulé'), texte)
        self.assertNotIn('PC globaux', texte)
        self.assertEqual(trace[0][:2], ('1', '4') if melange else ('1', '1'))

    def test_frontal_gagne_aux_pc_globaux(self):
        self.verifier_opposition_reelle(90, 30, True, False)

    def test_melange_gagne_aux_pc_globaux(self):
        self.verifier_opposition_reelle(30, 90, False, True)

    def test_egalite_annule_les_deux_schemas(self):
        self.verifier_opposition_reelle(60, 60, False, False)

    def test_conflit_interne_avant_opposition_ne_neutralise_pas_adversaire(self):
        self.opposition(90, 30, conflit_interne=True)
        with self.bataille():
            self.assertFalse(ordres_pipeline.frontal_autorise('j1'))
            self.assertEqual(self.ordre_effectif('j2'), ['4', '3', '1', '2'])
        texte = (self.config.rapports_territoires_dir / 'est_3.txt').read_text()
        self.assertIn('annulés mutuellement', texte)
        self.assertNotIn('confrontation globale Attaque frontale / On_melange', texte)

    def test_schema_retenu_garde_qg_et_ordres_individuels(self):
        self.opposition(30, 90)
        with self.bataille():
            forces = self.forces()
            a, b = forces['j1']['1'], forces['j2']['4']
            self.ordres(a, [1006])
            with ordres_pipeline.duel(a, b):
                self.assertTrue(ordres_pipeline.effet(a, 'herisson'))
                self.assertTrue(ordres_pipeline.effet(b, 'on_melange'))
                self.assertTrue(ordres_pipeline.effet(b, 'qg_nommade'))

    def test_frontal_non_transmis_par_qg_ne_contourne_pas_confrontation(self):
        q1, q2 = self.opposition(90, 30)
        (q1['chemin'] / 'qg.txt').unlink()
        with self.bataille():
            self.assertFalse(ordres_pipeline.frontal_autorise('j1'))
            self.assertEqual(self.ordre_effectif('j2'), ['4', '3', '1', '2'])

    def test_frontal_seul_historique_sans_qg_conserve(self):
        a = self.troupe('j1', 'piquier')
        self.ordres(a, texte='1-2')
        with self.bataille():
            self.assertTrue(ordres_pipeline.frontal_autorise('j1'))

    def preparer_tour(self):
        self.preparer([1015, 1016])
        bot = self.general('bot', numero=99, territoire='est_3', nombre=20, equipement='pique')
        (bot / 'ordre.txt').write_text('')
        self.activer(0)
        self.rapports.preparer_rapports(self.profil)
        return {p: p.read_bytes() for p in self.config.rapport_dir.rglob('*') if p.is_file()}

    def test_publication_privee_et_rapport_des_effets(self):
        avant = self.preparer_tour()
        original = self.combats.combat_entre_generaux
        trace = []
        def observer(a, b):
            self.assertEqual({p: p.read_bytes() for p in avant}, avant)
            trace.append(a['emplacement'])
            return original(a, b)
        with patch.object(self.combats, 'combat_entre_generaux', side_effect=observer), \
                patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, random.Random(17))
        self.assertEqual(trace, ['4', '3', '1', '2'])
        rapport = (self.config.rapports_territoires_dir / 'est_3.txt').read_text()
        self.assertIn('on_melange', rapport)
        self.assertIn('qg_nommade', rapport)
        self.assertNotIn('donneur_general', rapport)

    def test_interruption_ne_publie_pas_et_reprise_sans_rejeu(self):
        avant = self.preparer_tour()
        soldats_avant = copy.deepcopy(self.soldats.charger())
        original = self.combats.combat_entre_generaux
        def interrompre(a, b):
            original(a, b)
            raise RuntimeError('interruption formation')
        with patch.object(self.combats, 'combat_entre_generaux', side_effect=interrompre), \
                patch.object(self.survie, 'creer_vague_est', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'interruption formation'):
                self.survie.resoudre_tour_survie(self.profil, random.Random(17))
        self.assertEqual({p: p.read_bytes() for p in avant}, avant)
        self.assertEqual(self.soldats.charger(), soldats_avant)
        self.assertIsNone(ordres_pipeline._bataille.get())
        self.assertIsNone(ordres_pipeline._duel.get())
        with patch.object(self.combats, 'combat_entre_generaux') as combat:
            with self.assertRaises(RuntimeError):
                self.survie.resoudre_tour_survie(self.profil, random.Random(17))
            combat.assert_not_called()
