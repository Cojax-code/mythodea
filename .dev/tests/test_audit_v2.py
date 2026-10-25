"""Régressions de l'audit V2 sur plateaux temporaires, sans partie réelle."""
import importlib
import random
import unittest
from unittest.mock import patch

import test_unites_v2


class AuditUnites(unittest.TestCase):
    setUp = test_unites_v2.UnitesV2.setUp
    activer = test_unites_v2.UnitesV2.activer
    general = test_unites_v2.UnitesV2.general
    creer = test_unites_v2.UnitesV2.creer
    infos = test_unites_v2.UnitesV2.infos
    modules = test_unites_v2.UnitesV2.modules
    speciale = test_unites_v2.UnitesV2.speciale

    def test_ordres_malformes_ne_bloquent_pas_le_tour(self):
        g = self.creer(nombre=0)
        ordre = g['chemin'] / 'ordre.txt'
        for texte in ('²-2', '1-' + '9' * 5000, '1-2-²', '1-2\n\udcff'):
            with self.subTest(texte=texte[:20]):
                ordre.write_bytes(texte.encode('utf-8', errors='surrogateescape'))
                self.generaux.lire_ordres_general(g['chemin'])

    def test_cible_duel_est_une_position_pas_un_numero_general(self):
        g = self.creer(numero=12, nombre=0)
        (g['chemin'] / 'ordre.txt').write_text('2-1-3\n')
        ordre = self.generaux.lire_ordres_general(g['chemin'])[0]
        self.assertEqual(ordre['specification'], 3)
        self.assertFalse(self.combats.catalogues.ORDRES[1003]['disponible'])

    def test_orcs_zero_a_vingt_moral_borne_pc_constants(self):
        for moral in (0, 5, 50, 95, 100):
            for nombre in range(21):
                with self.subTest(moral=moral, orcs=nombre):
                    fiche = dict(moral=moral, points_commandement=37)
                    composition = dict(avant={'orc_assaillant': nombre // 3},
                        droite={'orc_archer': nombre // 3},
                        arriere={'orc_chaman': nombre - 2 * (nombre // 3)})
                    resultat = self.unites.caracteristiques_armee(fiche, composition)
                    self.assertEqual(resultat['points_commandement'], 37)
                    self.assertEqual(resultat['moral'],
                                     min(100, max(0, moral + (nombre - 10 if nombre else 0))))
                    self.assertEqual(fiche, dict(moral=moral, points_commandement=37))

    def test_trois_orcs_instinctifs_exception_hybride(self):
        for nature in ('stratege', 'instinctif', 'stratege_hybride', 'instinctif_hybride'):
            fiche = self.progression.nouvelles_caracteristiques(random.Random(1))
            fiche['nature'] = nature
            for apprentissage in (False, True):
                eligibles = self.progression.evolutions_eligibles(fiche, apprentissage=apprentissage)
                attendu = nature.startswith('instinctif') or (apprentissage and nature.endswith('_hybride'))
                self.assertEqual({107, 108, 109} <= eligibles.keys(), attendu)

    def adversaire_zombie(self, nombre=1, bouclier=True):
        chemin = self.general('bot', numero=1, territoire='est_3', nombre=0)
        g = dict(joueur='bot', nom=chemin.name, chemin=chemin)
        for n in range(nombre):
            self.speciale(g, 'zombie', n, 'arriere')
        if bouclier:
            self.speciale(g, 'Trop_gros_zombie', bloc='avant')
        return g

    def test_deux_boucliers_isoles_laissent_combattre_les_zombies(self):
        g = self.creer(nombre=0)
        self.speciale(g, 'Trop_gros_zombie', bloc='avant')
        for n in range(5):
            self.speciale(g, 'zombie', n, 'arriere')
        ennemi = self.adversaire_zombie()
        with self.soldats.bataille_complete('audit:boucliers', self.profil):
            resultat = self.combats.combat_entre_generaux(g, ennemi)
        self.assertEqual(resultat['final_1'], 5)  # 4 Zombies + leur bouclier
        self.assertEqual(resultat['final_2'], 0)
        self.assertFalse(ennemi['chemin'].exists())
        for choc in resultat['chocs']:
            self.assertNotIn('Trop_gros_zombie', (choc['type_1'], choc['type_2']))
        self.assertFalse(self.unites.charger_capacites().get('spores'))
        self.assertFalse(self.unites.charger_capacites().get('propagations'))

    def test_bouclier_seul_disparait_meme_face_a_un_bouclier(self):
        g = self.creer(nombre=0)
        self.speciale(g, 'Trop_gros_zombie')
        ennemi = self.adversaire_zombie()
        resultat = self.combats.combat_entre_generaux(g, ennemi)
        self.assertEqual((resultat['final_1'], resultat['final_2']), (0, 2))

    def test_spore_ne_convertit_aucun_zombie(self):
        g = self.creer(nombre=0)
        self.speciale(g, 'zombie')
        ennemi = self.adversaire_zombie()
        bouclier = importlib.import_module('bouclier_vivant')
        for bloc in ('avant', 'arriere'):
            self.assertIsNone(bouclier.convertir_spore(g, ennemi, bloc, 'audit:' + bloc))
        self.assertEqual(self.generaux.total_general_depuis_chemin(ennemi['chemin']), 2)

    def test_bouclier_disparait_apres_destruction_mutuelle_des_zombies(self):
        g = self.creer(nombre=0)
        self.speciale(g, 'Trop_gros_zombie', bloc='avant')
        self.speciale(g, 'zombie', bloc='arriere')
        ennemi = self.adversaire_zombie(bouclier=False)
        resultat = self.combats.combat_entre_generaux(g, ennemi)
        self.assertEqual((resultat['final_1'], resultat['final_2']), (0, 0))

    def test_chaman_fraction_de_moral_utilisable_pour_les_pertes(self):
        g = self.creer(nombre=0)
        for n in range(5):
            self.speciale(g, 'orc_assaillant', n)
        self.speciale(g, 'orc_chaman', bloc='arriere')
        fiches = self.progression.charger()
        fiches['j1:general1']['moral'] = 50
        self.progression.sauvegarder(fiches)
        # Moral = (50 - 4) * 1,02 = 46,92 ; 5 pertes -> 2 sauvetages.
        pertes = self.combats.supprimer_unites(self.infos(g), 0, g)
        self.assertEqual(len(pertes), 3)
        self.assertEqual(self.infos(g)['nombre'], 2)

    def test_surplus_zombie_conserve_jusqua_cloture_sans_perdre_historiques(self):
        g = self.creer(nombre=0)
        historiques = {self.speciale(g, 'zombie', n)[1] for n in range(20)}
        evenement = 'audit:surplus'
        with self.soldats.bataille_complete(evenement, self.profil):
            self.unites.propager(g, 'avant', 5, 20, 'audit:propagation', 'duel')
            self.generaux.verifier_limite_unites_general(g['chemin'])
            self.assertEqual(self.generaux.total_general_depuis_chemin(g['chemin']), 23)
            self.assertEqual(self.unites.terminer_territoire(
                self.config.game_path / 'est_3', evenement, self.profil), 3)
        self.assertEqual({self.soldats.marqueur(u) for u in self.infos(g)['unites']}, historiques)

    def test_resistance_deux_vrais_duels_puis_nouveau_territoire(self):
        bouclier = importlib.import_module('bouclier_vivant')
        g = self.creer(nombre=0)
        self.speciale(g, 'Trop_gros_zombie')
        self.speciale(g, 'zombie', bloc='arriere')
        with self.soldats.bataille_complete('audit:usure', self.profil):
            for numero, resistance in ((1, 247.5), (2, 245)):
                chemin = self.general('bot', numero=numero, territoire='est_3',
                                      place=str(numero), nombre=1, equipement='pique')
                ennemi = dict(joueur='bot', nom=chemin.name, chemin=chemin)
                self.combats.combat_entre_generaux(g, ennemi)
                self.assertEqual(bouclier._lire_resistance(g), resistance)
            self.unites.terminer_territoire(self.config.game_path / 'est_3', 'audit:usure', self.profil)
            self.assertEqual(bouclier._lire_resistance(g), 250)


class AuditParties(unittest.TestCase):
    setUp = test_unites_v2.UnitesV2.setUp
    activer = test_unites_v2.UnitesV2.activer
    general = test_unites_v2.UnitesV2.general
    modules = test_unites_v2.UnitesV2.modules

    def partie(self, joueurs, graine):
        import contextlib
        import io
        self.profil.update(duree_phase_action_secondes=0, duree_consultation_secondes=0,
                           delai_evenements_combats_secondes=0)
        self.etat.sauvegarder_cycle_survie(dict(tour=0, phase='a_preparer'), self.profil)
        for place, joueur in enumerate(joueurs, 1):
            self.general(joueur, territoire='village', place=str(place), nombre=20, equipement='pique')
        with patch.object(self.combats, 'random', random.Random(graine)), \
                patch.object(self.vagues, 'random', random.Random(graine)), \
                patch.object(self.generaux, 'aleatoire_caracteristiques', random.Random(graine)), \
                patch.object(self.progression, 'aleatoire_progression', random.Random(graine)), \
                patch.object(self.morgue, 'aleatoire_resurrection', random.Random(graine)), \
                contextlib.redirect_stdout(io.StringIO()):
            premier = self.survie.lancer_partie_survie(self.profil, 1, lambda: 100)
            suite = self.survie.lancer_partie_survie(self.profil, 15, lambda: 100)
            resultats = premier + suite
            self.assertTrue(resultats[-1]['defaite'])
            self.assertEqual(resultats[-1]['controle']['village'], 'bot')
            self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'defaite')
            self.assertEqual([r['tour'] for r in resultats], list(range(len(resultats))))
            self.assertEqual(self.survie.lancer_partie_survie(self.profil, 1, lambda: 100), [])
        self.assertIn('DÉFAITE', self.config.rapport_court_path.read_text())

    def test_partie_sans_defense_jusqua_defaite_et_reprise(self):
        self.partie((), 7)

    def test_partie_une_defense_jusqua_defaite_et_reprise(self):
        self.partie(('j1',), 17)

    def test_partie_cooperative_jusqua_defaite_et_reprise(self):
        self.partie(('j1', 'j2'), 31)


if __name__ == '__main__':
    unittest.main()
