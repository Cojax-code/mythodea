"""Transmission du QG, effets globaux et durée exacte d'un duel."""
import copy
import random
import unittest
from unittest.mock import patch

import test_qg_retraites_v2 as aides
import ordres_pipeline


class EffetsQG(unittest.TestCase):
    setUp = aides.QgRetraites.setUp
    activer = aides.QgRetraites.activer
    general = aides.QgRetraites.general
    creer = aides.QgRetraites.creer
    infos = aides.QgRetraites.infos
    modules = aides.QgRetraites.modules
    speciale = aides.QgRetraites.speciale
    troupe = aides.QgRetraites.troupe
    ordres = aides.QgRetraites.ordres
    declarer = aides.QgRetraites.declarer

    def bataille(self):
        profil = dict(self.profil)
        profil['acteurs'] = {j: dict(profil['acteurs'][j], camp=j) for j in ('j1', 'j2')}
        return ordres_pipeline.bataille(self.config.game_path / 'est_3', profil)

    def qg(self, joueur, ids, pc=40, nature='stratege', type_unite='piquier', nombre=2,
           etat_zombie=False):
        g = self.troupe(joueur, type_unite, nombre, numero=2, place='2')
        self.ordres(g, ids, pc=pc, etat_zombie=etat_zombie)
        registre = self.progression.charger()
        registre[f'{joueur}:general2']['nature'] = nature
        self.progression.sauvegarder(registre)
        self.declarer(g)
        return g

    def test_transmission_deux_camps_pc_du_donneur_et_priorite_personnelle(self):
        for joueur, adverse in (('j1', 'j2'), ('j2', 'j1')):
            a = self.troupe(joueur, 'sauvageon', 4, numero=3, place='3')
            b = self.troupe(adverse, 'piquier', 4, numero=3, place='3')
            self.ordres(a, pc=1); self.ordres(b, [1010], pc=20)
            qg = self.qg(joueur, [1008], nature='instinctif')
            with self.bataille():
                with ordres_pipeline.duel(a, b) as decisions:
                    self.assertTrue(ordres_pipeline.effet(a, 'orc_un_jour_orc_toujour'))
                    self.assertEqual(decisions[0]['pc'], 40)
                    self.assertEqual(decisions[0]['donneur_general'], 'general2')
                self.ordres(a, [1010], pc=1)
                with ordres_pipeline.duel(a, b) as decisions:
                    self.assertFalse(ordres_pipeline.effet(a, 'orc_un_jour_orc_toujour'))
                    self.assertEqual(decisions[0]['pc'], 1)
                    self.assertEqual(decisions[0]['donneur_general'], 'general3')
            (qg['chemin'] / 'qg.txt').unlink()

    def test_cruelle_compte_les_unites_du_qg_et_non_du_beneficiaire(self):
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'piquier')
        self.ordres(a); self.ordres(b, moral=50)
        self.qg('j1', [1010], type_unite='sauvageon', nombre=10)
        with self.bataille(), ordres_pipeline.duel(a, b):
            self.assertEqual(ordres_pipeline.moral(b, 50), 45)

    def test_zombie_reception_qg_limitee_avant_comparaison_dans_les_deux_camps(self):
        for joueur, adverse in (('j1', 'j2'), ('j2', 'j1')):
            a = self.troupe(joueur, 'zombie', 4, numero=3, place='3')
            b = self.troupe(adverse, 'sauvageon', 4, numero=4, place='4')
            self.ordres(a, etat_zombie=True)
            self.ordres(b, [1008], pc=1)
            qg = self.qg(joueur, [1008, 1012, 1014], pc=40, etat_zombie=True)
            # La fiche fournie par l'appelant ne remplace jamais le profil privé.
            a['caracteristiques'] = dict(etat_zombie=False)
            avant = copy.deepcopy(self.progression.charger())
            with self.bataille(), ordres_pipeline.duel(a, b) as decisions:
                self.assertTrue(ordres_pipeline.effet(a, 'propagafion'))
                self.assertFalse(ordres_pipeline.effet(a, 'etincellant'))
                self.assertFalse(ordres_pipeline.effet(a, 'orc_un_jour_orc_toujour'))
                self.assertTrue(ordres_pipeline.effet(b, 'orc_un_jour_orc_toujour'))
                demandes_a = [i for d in decisions if d['joueur'] == joueur for i in d['demandes']]
                self.assertEqual(demandes_a, [1012])
            self.assertEqual(self.progression.charger(), avant)
            # Les soldats Zombies d'un général ordinaire ne l'interdisent pas.
            self.ordres(a, etat_zombie=False)
            self.ordres(qg, [1008, 1014], pc=40, etat_zombie=False)
            profils = self.progression.charger()
            profils[f'{joueur}:general2']['nature'] = 'stratege'
            self.progression.sauvegarder(profils)
            with self.bataille(), ordres_pipeline.duel(a, b):
                self.assertTrue(ordres_pipeline.effet(a, 'etincellant'))
                self.assertTrue(ordres_pipeline.effet(a, 'orc_un_jour_orc_toujour'))
            (qg['chemin'] / 'qg.txt').unlink()

    def test_destruction_pendant_duel_preserve_transmis_et_interdit_suivant(self):
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'piquier')
        self.ordres(a); self.ordres(b)
        qg = self.qg('j1', [1008, 1014])
        with self.bataille():
            with ordres_pipeline.duel(a, b):
                self.combats.supprimer_unites(self.infos(qg), 0, qg)
                self.assertTrue(ordres_pipeline.effet(a, 'orc_un_jour_orc_toujour'))
                self.assertTrue(ordres_pipeline.effet(a, 'etincellant'))
            self.speciale(qg, 'piquier', 9)
            with ordres_pipeline.duel(a, b) as decisions:
                self.assertEqual(decisions, [])
                self.assertFalse(ordres_pipeline.effet(a, 'etincellant'))

    def test_qg_multiple_non_appris_et_nature_ne_donnent_aucun_global(self):
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'piquier')
        self.ordres(a); self.ordres(b)
        qg = self.qg('j1', [1014], nature='instinctif')
        with self.bataille(), ordres_pipeline.duel(a, b):
            self.assertFalse(ordres_pipeline.effet(a, 'etincellant'))
        self.ordres(qg, texte='1-5')
        with self.bataille(), ordres_pipeline.duel(a, b):
            self.assertFalse(ordres_pipeline.effet(a, 'etincellant'))
        self.declarer(a)
        with self.bataille(), ordres_pipeline.duel(a, b):
            self.assertFalse(ordres_pipeline.effet(a, 'etincellant'))

    def test_global_formule_egalite_normaux_et_contre_ordre(self):
        a, b = self.troupe('j1', 'piquier'), self.troupe('j2', 'piquier')
        self.ordres(a); self.ordres(b)
        q1 = self.qg('j1', [1014], pc=40)
        q2 = self.qg('j2', [1012], pc=40, etat_zombie=True)
        with self.bataille(), ordres_pipeline.duel(a, b) as decisions:
            self.assertEqual([d['pc'] for d in decisions], [40, 40])
            self.assertEqual([d['retenus'] for d in decisions], [[], []])
        (q2['chemin'] / 'ordre.txt').write_text('1-4')
        registre = self.progression.charger()
        registre['j2:general2']['evolutions_acquises'] = [1013]
        registre['j2:general2']['etat_zombie'] = False
        self.progression.sauvegarder(registre)
        with self.bataille(), ordres_pipeline.duel(a, b):
            self.assertTrue(ordres_pipeline.effet(a, 'etincellant'))
            self.assertTrue(ordres_pipeline.effet(b, 'confinement'))

    def test_confinement_neutralise_conversion_reelle_et_preserve_soldats(self):
        a = self.troupe('j1', 'zombie', 1, 'arriere')
        self.speciale(a, 'Trop_gros_zombie', 1)
        b = self.troupe('j2', 'piquier', 4)
        self.ordres(a); self.ordres(b)
        self.qg('j2', [1013])
        avant = copy.deepcopy(self.soldats.charger())
        with self.bataille(), ordres_pipeline.duel(a, b):
            self.assertIsNone(self.combats.bouclier_vivant.convertir_spore(
                a, b, 'avant', 'bloquee', random.Random(1)))
        self.assertEqual(self.soldats.charger(), avant)
        self.assertIsNotNone(self.combats.bouclier_vivant.convertir_spore(
            a, b, 'avant', 'normale', random.Random(1)))

    def test_propagafion_duel_reel_ajoute_deux_zombies(self):
        a, b = self.troupe('j1', 'zombie', 16), self.troupe('j2', 'piquier', 4)
        self.ordres(a); self.ordres(b)
        self.qg('j1', [1012], nature='instinctif', etat_zombie=True)
        with self.bataille():
            r = self.combats.combat_entre_generaux(a, b)
        self.assertEqual((r['final_1'], r['final_2']), (12, 0))
        nouveaux = [v for v in self.soldats.charger().values()
                    if 'propagation' in v.get('origine_officielle', {})]
        self.assertEqual(len(nouveaux), 4)

    def test_propagafion_zombie_toutes_natures_qg_acquisition_et_profil_prive(self):
        a, b = self.troupe('j1', 'zombie', 4), self.troupe('j2', 'piquier', 4)
        self.ordres(a); self.ordres(b)
        qg = self.qg('j1', [1012, 1018], etat_zombie=True)
        for nature in self.progression.NATURES:
            registre = self.progression.charger()
            registre['j1:general2']['nature'] = nature
            self.progression.sauvegarder(registre)
            avant = copy.deepcopy(registre)
            with self.bataille(), ordres_pipeline.duel(a, b):
                self.assertTrue(ordres_pipeline.effet(a, 'propagafion'))
                self.assertFalse(ordres_pipeline.effet(a, 'spora_adicte'))
            self.assertEqual(self.progression.charger(), avant)
        # Une fiche publique ou une mémoire ne donne pas le droit d'émettre.
        self.ordres(qg, texte='1-3', etat_zombie=True, evolution_apprise=1012)
        qg['caracteristiques'] = dict(etat_zombie=True, evolutions_acquises=[1012])
        with self.bataille(), ordres_pipeline.duel(a, b):
            self.assertFalse(ordres_pipeline.effet(a, 'propagafion'))
        self.ordres(qg, [1012], etat_zombie=False)
        with self.bataille(), ordres_pipeline.duel(a, b):
            self.assertFalse(ordres_pipeline.effet(a, 'propagafion'))
        self.ordres(qg, [1012], etat_zombie=True)
        (qg['chemin'] / 'qg.txt').unlink()
        with self.bataille(), ordres_pipeline.duel(a, b):
            self.assertFalse(ordres_pipeline.effet(a, 'propagafion'))

    def test_etincellant_manoeuvre_reelle_avant_arriere_adverse(self):
        a = self.troupe('j1', 'chevalier_clinquant', 8, 'droite')
        b = self.troupe('j2', 'archer', 3, 'arriere')
        self.ordres(a); self.ordres(b)
        self.qg('j1', [1014])
        with self.bataille():
            r = self.combats.combat_entre_generaux(a, b)
        self.assertFalse(r['chocs'])
        self.assertEqual((r['manoeuvres'][0]['joueur_attaquant'],
                          r['manoeuvres'][0]['bloc_attaquant']), ('j1', 'droite'))
        self.assertEqual(len(r['manoeuvres']), 1)

    def test_interruption_effet_global_libere_contextes(self):
        a, b = self.troupe('j1', 'zombie', 16), self.troupe('j2', 'piquier', 4)
        self.ordres(a); self.ordres(b)
        self.qg('j1', [1012], etat_zombie=True)
        original = self.unites.propager
        def interrompre(*args):
            original(*args)
            raise RuntimeError('après propagation')
        with self.assertRaisesRegex(RuntimeError, 'après propagation'):
            with self.bataille(), patch.object(self.unites, 'propager', side_effect=interrompre):
                self.combats.combat_entre_generaux(a, b)
        self.assertIsNone(ordres_pipeline._duel.get())
        self.assertIsNone(ordres_pipeline._bataille.get())

    def preparer_tour_global(self):
        a = self.troupe('j1', 'zombie', 16)
        self.ordres(a)
        self.qg('j1', [1012], etat_zombie=True)
        self.general('bot', numero=99, territoire='est_3', nombre=4, equipement='pique')
        self.activer(0)
        self.rapports.preparer_rapports(self.profil)
        return {p: p.read_bytes() for p in self.config.rapport_dir.rglob('*') if p.is_file()}

    def test_tour_global_et_transmission_prives_jusqua_publication(self):
        avant = self.preparer_tour_global()
        origine = self.unites.propager
        executions = []
        def observer(*args):
            nombre = origine(*args)
            executions.append(nombre)
            self.assertEqual({p: p.read_bytes() for p in avant}, avant)
            return nombre
        with patch.object(self.unites, 'propager', side_effect=observer), \
                patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, random.Random(17))
        self.assertEqual(executions, [4])
        rapport = (self.config.rapports_territoires_dir / 'est_3.txt').read_text()
        self.assertIn('propagafion', rapport)
        self.assertNotIn('orc_un_jour_orc_toujour', rapport)
        self.assertNotIn('donneur_general', rapport)
        self.assertIn("'donneur_general': 'general2'", self.config.rapport_long_path.read_text())

    def test_interruption_global_generation_publique_intacte_et_reprise_bloquee(self):
        avant = self.preparer_tour_global()
        soldats_avant = copy.deepcopy(self.soldats.charger())
        origine = self.unites.propager
        def interrompre(*args):
            origine(*args)
            raise RuntimeError('interruption globale privée')
        with patch.object(self.unites, 'propager', side_effect=interrompre), \
                patch.object(self.survie, 'creer_vague_est', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'interruption globale privée'):
                self.survie.resoudre_tour_survie(self.profil, random.Random(17))
        self.assertEqual(self.soldats.charger(), soldats_avant)
        self.assertEqual({p: p.read_bytes() for p in avant}, avant)
        with patch.object(self.unites, 'propager') as effet:
            with self.assertRaises(RuntimeError):
                self.survie.resoudre_tour_survie(self.profil, random.Random(17))
            effet.assert_not_called()
