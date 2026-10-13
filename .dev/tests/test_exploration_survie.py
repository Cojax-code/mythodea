"""Photographie publiée du plateau : lecture passive et stabilité pendant ACTIONS."""
import copy
import importlib
import json
import unittest
from unittest.mock import call, patch

import test_cycle_survie
from support_cycle import GelSimule


class ExplorationSurvie(unittest.TestCase):
    setUp = test_cycle_survie.CycleSurvie.setUp
    general = test_cycle_survie.CycleSurvie.general
    activer = test_cycle_survie.CycleSurvie.activer
    photo = test_cycle_survie.CycleSurvie.photo

    def fichier(self, joueur='j1'):
        return self.config.game_path / 'village' / joueur / 'hotel_de_ville/rapport_exploration.txt'

    def texte(self, joueur='j1'):
        return self.fichier(joueur).read_text(encoding='utf-8')

    def section(self, texte, nom):
        separateur = '=' * 60
        return texte.split(f'{separateur}\n{nom.upper()}\n{separateur}\n', 1)[1].split(separateur, 1)[0]

    def gestion(self):
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        gestion.preparer()
        return gestion

    def scenario_exemple(self):
        self.general(territoire='village', nombre=5)
        self.general('j2', numero=2, territoire='village', reserve=True, nombre=3, equipement='pique')
        compose = self.general('j2', numero=3, territoire='est_1', nombre=0)
        for bloc, equipement, nombre in (('avant', 'cheval', 5), ('droite', 'pique', 3),
                                         ('gauche', 'pique', 3), ('arriere', 'arc', 3)):
            prefixe = 'cavalerie' if equipement == 'cheval' else 'infanterie'
            for n in range(1, nombre + 1):
                unite = compose / bloc / f'{prefixe}{n}'
                unite.mkdir()
                (unite / equipement).touch()
        self.general('bot', territoire='est_1', nombre=12)
        self.general(numero=4, territoire='repli', nombre=7)
        self.general(numero=9, territoire='home', nombre=20)

    def test_exemple_complet_composition_et_territoires(self):
        self.scenario_exemple()
        avant = self.photo()
        etat = self.rapports.lire_etat_exploration(self.profil, 4)
        texte = self.rapports.generer_rapport_exploration('j1', etat)
        self.assertEqual(self.photo(), avant)
        self.assertEqual([t['nom'] for t in etat['territoires']], ['village', 'est_1', 'est_2', 'est_3', 'repli'])
        est = self.section(texte, 'est_1')
        for fragment in ('Contrôle : contesté', 'general3 — 14 unités', 'general1_1 — 12 unités',
                         'avant   : 5 cavaliers', 'droite  : 3 piquiers', 'gauche  : 3 piquiers',
                         'arrière : 3 archers'):
            self.assertIn(fragment, est)
        vide = self.section(texte, 'est_2')
        self.assertIn('Contrôle : vide', vide)
        self.assertEqual(vide.count('aucune présence'), 3)
        village = self.section(texte, 'village')
        self.assertIn('Contrôle : allié', village)
        self.assertIn('Garnison :\n    1 : general1 — 5 unités', village)
        self.assertIn('4 : vide', village)
        self.assertIn('j2\n  Garnison :\n    1 : occupé par j1', village)
        self.assertIn('Réserve (hors combat) :\n    general2 — 3 unités', village)
        self.assertNotIn('Renforts', village)
        self.assertNotIn('5 :', village)
        self.assertIn('general4 — 7 unités', self.section(texte, 'repli'))
        for interdit in ('general9', '/home/', '.systeme', 'technique'):
            self.assertNotIn(interdit, texte)

    def test_lecture_ne_repare_ni_ne_nettoie_et_rendu_pur(self):
        chemin = self.general(territoire='village', reserve=True, nombre=21)
        (chemin / 'arriere').rmdir()
        (chemin / 'fiche.txt').unlink()
        invalide = chemin / 'avant/objet_invalide'
        invalide.mkdir()
        pique = chemin / 'avant/infanterie22'
        pique.mkdir()
        (pique / 'pique').touch()
        avant = self.photo()
        dossiers = sorted(str(p) for p in self.racine.rglob('*') if p.is_dir())
        with patch.object(self.generaux, 'lire_blocs_general', side_effect=AssertionError('Nettoyage interdit')), \
                patch.object(self.generaux, 'creer_general', side_effect=AssertionError('Réparation interdite')):
            etat = self.rapports.lire_etat_exploration(self.profil, 0)
        self.assertEqual(self.photo(), avant)
        self.assertEqual(sorted(str(p) for p in self.racine.rglob('*') if p.is_dir()), dossiers)
        copie = copy.deepcopy(etat)
        # Le rendu n'accède plus au disque ; un changement ultérieur est invisible.
        (chemin / 'avant/infanterie1/arc').unlink()
        texte = self.rapports.generer_rapport_exploration('j1', etat)
        self.assertEqual(etat, copie)
        self.assertIn('general1 — 22 unités', texte)
        self.assertIn('21 archers, 1 piquier', texte)
        self.assertIn('Contrôle : vide', self.section(texte, 'village'))

    def test_renforts_visibles_sans_controle_et_colonne_bot_au_village(self):
        self.general(territoire='est_2', place='5', nombre=4)
        bot = self.general('bot', territoire='village', nombre=2)
        bot.rename(self.config.game_path / 'village/bot/renforts/general1')
        texte = self.rapports.generer_rapport_exploration(
            'j1', self.rapports.lire_etat_exploration(self.profil, 0))
        est = self.section(texte, 'est_2')
        self.assertIn('Renforts (hors places actives)', est)
        self.assertIn('5 : general1 — 4 unités', est)
        self.assertIn('Contrôle : vide', est)
        village = self.section(texte, 'village')
        self.assertIn('Colonne en attente', village)
        self.assertIn('general1_1 — 2 unités', village)
        self.assertIn('Contrôle : vide', village)
        self.assertNotIn('5 :', village)

    def test_vague_zero_sous_gel_et_personnalisation(self):
        (self.config.game_path / '.systeme/cycle_survie.json').unlink()
        gestion = self.gestion()
        reel = self.rapports.lire_etat_exploration
        def lire(configuration, vague):
            self.assertTrue(gestion.backend.gele)
            self.assertEqual(vague, 0)
            return reel(configuration, vague)
        with patch.object(self.survie, 'creer_gestion', return_value=gestion), \
                patch.object(self.rapports, 'lire_etat_exploration', side_effect=lire):
            self.survie.ouvrir_tour_survie(self.profil)
        self.assertFalse(gestion.backend.gele)
        for joueur in ('j1', 'j2'):
            self.assertIn(f"RAPPORT D'EXPLORATION — {joueur}\nVague : 0", self.texte(joueur))
        self.assertEqual(self.texte().splitlines()[1:], self.texte('j2').splitlines()[1:])
        self.assertNotEqual(self.fichier().stat().st_ino, self.fichier('j2').stat().st_ino)

    def test_publication_puis_stabilite_actions_et_remplacement_vague_suivante(self):
        (self.config.game_path / '.systeme/cycle_survie.json').unlink()
        self.survie.ouvrir_tour_survie(self.profil)
        chemin = self.general(numero=2, territoire='village', nombre=2)
        ancien = self.fichier().read_bytes()
        gestion = self.gestion()
        resoudre = self.survie._resoudre_tour_capture
        publier = self.rapports.publier_rapports_exploration
        def tardif(prive, aleatoire):
            resultat = resoudre(prive, aleatoire)
            # Écriture sur le plateau vivant après la capture : elle ne fait
            # partie ni de la génération publiée ni de son rapport d'exploration.
            unite = chemin / 'avant/infanterie99'
            unite.mkdir()
            (unite / 'arc').touch()
            self.assertEqual(self.fichier().read_bytes(), ancien)
            return resultat
        def verifier(configuration, vague):
            self.assertTrue(gestion.backend.gele)
            self.assertEqual(configuration['game_path'], self.config.game_path)
            self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'publication')
            self.assertFalse((chemin / 'avant/infanterie99').exists())
            return publier(configuration, vague)
        with patch.object(self.survie, 'creer_vague_est', return_value=[]), \
                patch.object(self.survie, '_resoudre_tour_capture', side_effect=tardif), \
                patch.object(self.rapports, 'publier_rapports_exploration', side_effect=verifier):
            self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        self.assertIn('general2 — 2 unités', self.texte())
        self.assertIn('Vague : 1', self.texte())
        for joueur in ('j1', 'j2'):
            self.assertEqual((self.fichier(joueur).parent / 'rapport.txt').read_bytes(),
                             self.config.rapport_court_path.read_bytes())
        contenu = self.fichier().read_bytes()
        inode = self.fichier().stat().st_ino
        (chemin / 'avant/infanterie2/arc').unlink()
        gestion.permissions_actions()
        self.activer(1)
        self.survie.ouvrir_tour_survie(self.profil)
        self.assertEqual(self.fichier().read_bytes(), contenu)
        self.assertEqual(self.fichier().stat().st_ino, inode)
        with patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        self.assertIn('Vague : 2', self.texte())
        self.assertIn('general2 — 1 unité', self.texte())
        self.assertNotIn('Vague : 1', self.texte())
        self.assertNotIn('general2 — 2 unités', self.texte())
        self.assertEqual(self.texte().count("RAPPORT D'EXPLORATION"), 1)

    def test_rattrapage_conteste_sans_nouveau_combat(self):
        self.general(territoire='est_2', nombre=1, equipement='pique')
        self.general('j2', territoire='est_1', nombre=20, equipement='cheval')
        self.general('bot', territoire='est_2', nombre=20)
        with patch.object(self.survie, 'creer_vague_est', return_value=[]), \
                patch.object(self.survie, 'resoudre_cascade', wraps=self.survie.resoudre_cascade) as combat:
            resultat = self.survie.resoudre_tour_survie(self.profil, gestion=self.gestion())
        self.assertEqual([a.args[0].name for a in combat.call_args_list], ['est_2'])
        self.assertEqual(resultat['controle']['est_1'], 'conteste')
        for joueur in ('j1', 'j2'):
            est = self.section(self.texte(joueur), 'est_1')
            self.assertIn('Contrôle : contesté', est)
            self.assertIn('j2\n', est)
            self.assertIn('general1 — 20 unités', est)
            self.assertIn('BOT\n', est)
            self.assertIn('general1_1 —', est)

    def test_republication_apres_echec_exploration_sans_rejeu_metier(self):
        gestion = self.gestion()
        with patch.object(self.survie, 'creer_vague_est', return_value=[]), \
                patch.object(self.rapports, 'publier_rapports_exploration', side_effect=OSError('rapport indisponible')):
            with self.assertRaisesRegex(OSError, 'rapport indisponible'):
                self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        self.assertFalse(gestion.backend.gele)
        self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'recuperation')
        self.assertFalse(json.loads((gestion.generation / 'publication.json').read_text())['termine'])
        admin = importlib.import_module('survie_admin')
        with patch.object(admin.cycle_linux, 'Linux', return_value=GelSimule()), \
                patch.object(self.securite, 'verifier_tous_les_deplacements', side_effect=AssertionError('Audit rejoué')), \
                patch.object(self.survie, 'creer_vague_est', side_effect=AssertionError('Vague rejouée')):
            admin.republier(self.profil, gestion.generation.name)
        self.assertIn('Vague : 2', self.texte())
        self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'consultation')

    def test_permissions_simulees_par_joueur_a_chaque_ouverture(self):
        (self.config.game_path / '.systeme/cycle_survie.json').unlink()
        self.survie.ouvrir_tour_survie(self.profil)
        self.gestion().permissions_actions()
        for joueur in ('j1', 'j2'):
            fichier = self.fichier(joueur)
            gid = self.plateau.grp.getgrnam(joueur).gr_gid
            self.assertIn(call(fichier, 0, gid), self.chown.call_args_list)
            derniers = [c.args[1] for c in self.chmod.call_args_list if c.args[0] == fichier]
            self.assertEqual(derniers[-1], 0o640)


if __name__ == '__main__':
    unittest.main()
