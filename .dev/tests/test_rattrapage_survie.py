"""Identités des forces autorisées à avancer, sur un plateau temporaire."""
import unittest
from unittest.mock import patch

import test_cycle_survie


class ProgressionSurvie(unittest.TestCase):
    setUp = test_cycle_survie.CycleSurvie.setUp
    general = test_cycle_survie.CycleSurvie.general
    colonne = test_cycle_survie.CycleSurvie.colonne
    activer = test_cycle_survie.CycleSurvie.activer
    resoudre = test_cycle_survie.CycleSurvie.resoudre

    def test_force_bloquee_sur_origine_et_colonne_conservee(self):
        self.general(territoire='est_2', nombre=1)
        self.colonne(6, 'est_2')
        bloques = {}
        self.assertEqual(self.survie.avancer_ennemis(self.profil, bloques), [])
        self.assertEqual(bloques, {f'general{i}': 'est_2' for i in range(1, 7)})
        self.assertEqual(len(self.survie.inventorier_ennemis(
            self.config.game_path / 'est_2', self.profil)), 6)

    def test_force_avancee_pas_dans_les_bloquees(self):
        self.colonne(1, 'est_3')
        self.general(territoire='est_2', nombre=1)
        bloques = {}
        mouvements = self.survie.avancer_ennemis(self.profil, bloques)
        self.assertEqual(bloques, {})
        self.assertEqual([(m['origine'], m['destination']) for m in mouvements], [('est_3', 'est_2')])

    def test_arrivants_derriere_colonne_bloquee_sans_double_avance(self):
        self.general(territoire='est_2', nombre=1)
        self.colonne(5, 'est_2')
        self.colonne(2, 'est_3', numeros=[6, 7])
        bloques = {}
        mouvements = self.survie.avancer_ennemis(self.profil, bloques)
        self.assertEqual([m['nom'] for m in mouvements], ['general6', 'general7'])
        self.assertEqual(len(bloques), 5)
        self.assertEqual([g['nom'] for g in self.survie.inventorier_ennemis(
            self.config.game_path / 'est_2', self.profil)], [f'general{i}' for i in range(1, 8)])

    def test_general_vide_ne_bloque_pas(self):
        self.general(territoire='est_2', nombre=0)
        self.colonne(1, 'est_2')
        bloques = {}
        mouvements = self.survie.avancer_ennemis(self.profil, bloques)
        self.assertEqual(bloques, {})
        self.assertEqual(mouvements[0]['destination'], 'est_1')

    def test_avance_normale_puis_victoire_sans_rattrapage(self):
        self.general(territoire='est_2', nombre=1, equipement='pique')
        self.general('bot', territoire='est_3', nombre=20)
        resultat = self.resoudre(False)
        self.assertEqual(resultat['rattrapages'], [])
        self.assertEqual(self.etat.charger_positions_generaux()['bot:general1'], 'est_2')

    def test_bloque_perd_sans_rattrapage(self):
        self.general(territoire='est_2', nombre=20)
        self.general('bot', territoire='est_2', nombre=1, equipement='pique')
        resultat = self.resoudre(False)
        self.assertEqual(resultat['deplacements'], [])
        self.assertEqual(resultat['rattrapages'], [])
        self.assertNotIn('bot:general1', self.etat.charger_positions_generaux())

    def test_bloque_gagne_rattrape(self):
        self.general(territoire='est_2', nombre=1, equipement='pique')
        self.general('bot', territoire='est_2', nombre=20)
        resultat = self.resoudre(False)
        self.assertEqual(resultat['deplacements'], [])
        self.assertEqual([(m['nom'], m['origine'], m['destination']) for m in resultat['rattrapages']],
                         [('general1', 'est_2', 'est_1')])
        self.assertEqual(resultat['controle']['est_1'], 'bot')

    def test_plusieurs_territoires_pas_de_double_deplacement(self):
        for numero, nom in enumerate(('est_2', 'est_3'), 1):
            self.general(numero=numero, territoire=nom, nombre=1, equipement='pique')
            self.general('bot', numero=numero, territoire=nom, nombre=20)
        self.general('bot', numero=3, territoire='est_1', nombre=20)
        resultat = self.resoudre(False)
        mouvements = resultat['deplacements'] + resultat['rattrapages']
        self.assertEqual(len(mouvements), 3)
        self.assertEqual(len({m['nom'] for m in mouvements}), 3)
        self.assertEqual({k: v for k, v in self.etat.charger_positions_generaux().items()
                          if k.startswith('bot:')},
                         {'bot:general1': 'est_1', 'bot:general2': 'est_2', 'bot:general3': 'village'})

    def test_nouvelle_vague_et_force_deja_avancee_exclues_du_rattrapage(self):
        self.general(territoire='est_2', nombre=1, equipement='pique')
        self.general('bot', territoire='est_2', nombre=20)
        self.general('bot', numero=2, territoire='est_3', nombre=20)
        def apparition(*args):
            return [self.general('bot', numero=3, territoire='est_2', nombre=20)]
        with patch.object(self.survie, 'creer_vague_est', side_effect=apparition), \
                patch.object(self.survie, 'resoudre_cascade', wraps=self.survie.resoudre_cascade) as combat:
            resultat = self.resoudre()
        self.assertEqual(combat.call_count, 1)
        self.assertEqual([m['nom'] for m in resultat['rattrapages']], ['general1'])
        positions = self.etat.charger_positions_generaux()
        self.assertEqual([positions[f'bot:general{i}'] for i in (1, 2, 3)], ['est_1', 'est_2', 'est_2'])

    def test_destination_contestee_sans_second_combat_puis_cycle_normal(self):
        self.general(territoire='est_2', nombre=1, equipement='pique')
        defenseur = self.general('j2', territoire='est_1', nombre=20, equipement='cheval')
        self.general('bot', territoire='est_2', nombre=20)
        with patch.object(self.survie, 'resoudre_cascade', wraps=self.survie.resoudre_cascade) as combat:
            resultat = self.resoudre(False)
        self.assertEqual([a.args[0].name for a in combat.call_args_list], ['est_2'])
        self.assertEqual(resultat['controle']['est_1'], 'conteste')
        self.assertEqual(self.generaux.total_general_depuis_chemin(defenseur), 20)
        self.activer(2)
        suivant = self.resoudre(False)
        self.assertIn('est_1', suivant['batailles'])
        self.assertEqual(suivant['controle']['est_1'], 'allies')

    def test_blocage_non_leve_pas_de_rattrapage(self):
        self.general(territoire='est_2', nombre=1, equipement='pique')
        self.general('bot', territoire='est_2', nombre=20)
        with patch.object(self.survie, 'resoudre_cascade', return_value={'controle': 'conteste'}):
            resultat = self.resoudre(False)
        self.assertEqual(resultat['rattrapages'], [])
        self.assertEqual(resultat['controle']['est_2'], 'conteste')
