"""Crypte : collecte privée, attribution, audit et publication sur partie isolée."""
import importlib
import json
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

import test_generations_survie


class Crypte(unittest.TestCase):
    gestion = test_generations_survie.GenerationsSurvie.gestion
    general = test_generations_survie.GenerationsSurvie.general
    activer = test_generations_survie.GenerationsSurvie.activer

    def setUp(self):
        test_generations_survie.GenerationsSurvie.setUp(self)
        self.crypte = self.survie.crypte
        self.crypte.preparer(self.profil)
        self.collecteur = self.crypte.Collecteur(self.profil, horloge=lambda: 1)
        self.tokens = {}
        self.seq = {}
        self.activer(3)

    def message(self, op, j='j1', **champs):
        if op == 'start':
            self.seq[j] = 0
        else:
            self.seq[j] += 1
        m = dict(event=op, token=self.tokens.get(j), seq=self.seq[j],
                 cwd=str(self.crypte.zone(self.profil, j) / 'atelier'), **champs)
        resultat = self.collecteur.evenement(1001 if j == 'j1' else 1002, (123, 'session'), m)
        if op == 'start':
            self.tokens[j] = resultat
        return resultat

    def commande(self, ligne, j='j1', retour='0'):
        self.message('before', j, line=ligne, command=ligne, kind='file', history='1/1')
        atelier = self.crypte.zone(self.profil, j) / 'atelier'
        if ligne == 'mkdir appel' and retour == '0':
            (atelier / 'appel').mkdir()
        elif ligne == 'touch appel/cavalerie':
            (atelier / 'appel/cavalerie').touch()
        elif ligne == 'chmod 600 appel/cavalerie':
            # Les fixtures historiques simulent os.chmod ; ici stat réel est vérifié.
            (atelier / 'appel/cavalerie').write_bytes(b'')
        elif ligne == 'mv appel/cavalerie appel/offrande':
            (atelier / 'appel/cavalerie').rename(atelier / 'appel/offrande')
        self.message('after', j, status=retour)

    def reussir(self, j='j1'):
        self.message('start', j)
        for ligne in self.crypte.RECETTE:
            self.commande(ligne, j)
        # Le test du vrai chmod est dans la suite Linux, pas simulé ici.
        with patch.object(self.crypte, 'verifier_offrande'):
            self.message('end', j)

    def creer(self, tour=3):
        with self.config.racines_generation(self.config.game_path,
                {j: self.racine / 'home' / j for j in self.profil['joueurs']}):
            self.crypte.materialiser(self.profil, tour)

    def test_reussite_persistante_sans_creation_vivante(self):
        self.reussir()
        donnees = self.crypte.charger(self.profil)['j1']
        self.assertEqual(donnees['dernier_tour'], 3)
        self.assertEqual(donnees['a_creer']['id'], self.tokens['j1'])
        self.assertEqual(list((self.crypte.zone(self.profil, 'j1') / 'recompense').iterdir()), [])
        self.assertEqual(self.etat.lire_compteur_general('j1'), 0)
        nouveau = self.crypte.Collecteur(self.profil, horloge=lambda: 1)
        self.assertEqual(self.crypte.charger(nouveau.c), self.crypte.charger(self.profil))

    def test_composition_identite_affichage_zone_inactive(self):
        self.reussir()
        self.creer()
        p = self.crypte.zone(self.profil, 'j1') / 'recompense/general1'
        self.assertTrue(self.generaux.est_general_valide(p))
        self.assertEqual([len(list((p / b).iterdir())) for b in self.config.ordre_blocs], [10, 5, 5, 0])
        self.assertEqual(len(list(p.glob('*/cavalerie*/cheval'))), 20)
        fiche = self.generaux.lire_fiche_general(p)
        self.assertEqual(fiche['nom'], 'general1')
        self.assertEqual(fiche['nom_affichage'], self.crypte.NOM)
        self.assertEqual(self.rapports.nom_affichage_general({'joueur': 'j1', 'nom': 'general1', 'fiche': fiche}), self.crypte.NOM)
        forces = self.generaux.lire_forces_territoire(self.config.game_path / 'village', self.profil)
        self.assertEqual(self.generaux.controle_forces(forces), 'neutre')
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general1'], 'village')

    def test_mauvais_ordre_commande_extra_et_echec(self):
        for ligne, retour in [('touch appel/cavalerie', '0'), ('ls', '0'), ('mkdir appel', '1')]:
            with self.subTest(ligne=ligne):
                self.message('start')
                self.message('before', line=ligne, command=ligne, kind='file', history='1/1')
                self.message('after', status=retour)
                with self.assertRaises(ValueError):
                    self.message('end')
                self.assertIsNone(self.crypte.charger(self.profil)['j1']['dernier_tour'])

    def test_rejeu_evenement_et_reussite_refuse(self):
        self.message('start')
        self.commande('mkdir appel')
        self.seq['j1'] -= 1
        with self.assertRaisesRegex(ValueError, 'rejoué'):
            self.message('after', status='0')
        self.reussir()
        with self.assertRaises(ValueError):
            self.message('end')
        self.assertEqual(len(self.crypte.charger(self.profil)['j1']['attributions']), 0)

    def test_reconnexion_ne_reprend_pas_ancienne_tentative(self):
        self.message('start')
        ancien = self.tokens['j1']
        self.message('start')
        self.assertNotEqual(ancien, self.tokens['j1'])
        self.tokens['j1'] = ancien
        with self.assertRaises(ValueError):
            self.commande('mkdir appel')

    def test_deconnexion_nettoie_sans_cooldown(self):
        self.message('start')
        self.commande('mkdir appel')
        with patch.object(self.crypte, 'identite_processus', side_effect=FileNotFoundError):
            self.collecteur.surveiller_sessions()
        self.assertFalse(self.collecteur.tentatives)
        self.assertFalse(list((self.crypte.zone(self.profil, 'j1') / 'atelier').iterdir()))
        self.assertIsNone(self.crypte.charger(self.profil)['j1']['dernier_tour'])

    def test_cloture_invalide_et_nettoie(self):
        self.message('start')
        self.commande('mkdir appel')
        with patch.dict(self.crypte.SERVICES, {str(self.profil['game_path']): self.collecteur}):
            self.gestion().capturer(3)
        self.assertFalse(self.collecteur.tentatives)
        self.assertFalse(list((self.crypte.zone(self.profil, 'j1') / 'atelier').iterdir()))
        self.assertIsNone(self.crypte.charger(self.profil)['j1']['dernier_tour'])

    def test_cooldown_exact_et_independance(self):
        self.reussir('j1')
        self.creer(3)
        (self.crypte.zone(self.profil, 'j1') / 'recompense/general1').rename(
            self.config.game_path / 'village/j1/reserve/general1')
        self.activer(4)
        self.reussir('j2')
        self.creer(4)
        (self.crypte.zone(self.profil, 'j2') / 'recompense/general1').rename(
            self.config.game_path / 'village/j2/reserve/general1')
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.activer(7)
        with self.assertRaisesRegex(ValueError, 'tour 8'):
            self.message('start', 'j1')
        self.activer(8)
        self.reussir('j1')
        with self.assertRaisesRegex(ValueError, 'tour 9'):
            self.message('start', 'j2')
        self.activer(9)
        self.reussir('j2')

    def test_une_recompense_en_attente_refus_sans_consommation(self):
        self.reussir()
        self.creer()
        self.activer(8)
        with self.assertRaisesRegex(ValueError, 'attente'):
            self.message('start')
        self.assertEqual(self.crypte.charger(self.profil)['j1']['dernier_tour'], 3)

    def test_bonus_apres_cinq_normaux_compteur_non_reutilise(self):
        self.etat.sauvegarder_compteur_general('j1', 5)
        self.etat.sauvegarder_quota_normal('j1', 5)
        self.reussir()
        self.creer()
        self.assertEqual(self.crypte.charger(self.profil)['j1']['en_attente'], 'general6')
        self.assertEqual(self.etat.initialiser_quota_normal('j1'), 5)
        self.generaux.faire_apparaitre_general_si_possible('j1', self.profil)
        self.assertEqual(self.etat.lire_compteur_general('j1'), 6)

    def test_bonus_ne_consomme_pas_creation_normale(self):
        self.reussir()
        self.creer()
        self.generaux.faire_apparaitre_general_si_possible('j1', self.profil)
        self.assertEqual(self.etat.initialiser_quota_normal('j1'), 1)
        self.assertEqual(self.etat.lire_compteur_general('j1'), 2)
        self.assertTrue((self.racine / 'home/j1/general2').exists())

    def test_generation_privee_publication_sans_rejeu(self):
        self.reussir()
        g = self.gestion()
        original = self.crypte.materialiser
        racines = []
        def mater(c, tour):
            self.assertNotEqual(c['game_path'], self.config.game_path)
            self.assertFalse(list((self.crypte.zone(self.profil, 'j1') / 'recompense').iterdir()))
            racines.append(c['game_path'])
            original(c, tour)
        with patch.object(self.crypte, 'materialiser', side_effect=mater):
            self.survie.resoudre_tour_survie(self.profil, random.Random(4), g)
        self.assertEqual(len(racines), 1)
        self.assertTrue((self.crypte.zone(self.profil, 'j1') / 'recompense/general1').exists())
        self.assertEqual(len(self.crypte.charger(self.profil)['j1']['attributions']), 1)
        with self.assertRaises(RuntimeError):
            self.survie.resoudre_tour_survie(self.profil, gestion=g)

    def test_recuperation_mv_puis_retour_interdit(self):
        self.reussir()
        self.creer()
        source = self.crypte.zone(self.profil, 'j1') / 'recompense/general1'
        cible = self.config.game_path / 'village/j1/garnison/1/general1'
        source.rename(cible)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general1'], 'village')
        self.assertIsNone(self.crypte.charger(self.profil)['j1']['en_attente'])
        cible.rename(source)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertFalse(source.exists())
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general1'], 'repli')

    def test_pdf_unique(self):
        for j in ('j1', 'j2'):
            grimoire = self.crypte.zone(self.profil, j) / 'grimoire'
            self.assertEqual([p.name for p in grimoire.iterdir()], ['recette1.pdf'])
            self.assertTrue((grimoire / 'recette1.pdf').read_bytes().startswith(b'%PDF-1.4'))

    @unittest.skipUnless(os.name == 'posix', 'Liens réels Unix requis')
    def test_nettoyage_liens_ne_touche_pas_exterieur(self):
        atelier = self.crypte.zone(self.profil, 'j1') / 'atelier'
        exterieur = self.racine / 'personnel'
        exterieur.mkdir()
        (exterieur / 'important').write_text('conserver')
        (atelier / 'lien').symlink_to(exterieur, target_is_directory=True)
        self.crypte.nettoyer(self.profil, 'j1')
        self.assertEqual((exterieur / 'important').read_text(), 'conserver')
        self.assertFalse(list(atelier.iterdir()))


if __name__ == '__main__':
    unittest.main()
