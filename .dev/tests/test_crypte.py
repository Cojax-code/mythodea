"""Crypte : collecte privée, attribution, audit et publication sur partie isolée."""
import importlib
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_generations_survie

CHMOD_REEL = os.chmod


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

    def test_pdf_racine_publique_configurable(self):
        for identifiant in self.crypte.RECETTES:
            pdf = self.crypte.recette_pdf({'debut': 'crypte_commence', 'fin': 'crypte_fin'},
                                         identifiant, Path('/plateau-public'))
            self.assertIn(b'/plateau-public/village/j1/crypte/', pdf)
            self.assertNotIn(b'/game/', pdf)

    def test_installateur_racine_configuree_et_socket(self):
        installateur = importlib.import_module('crypte_installer')
        with patch.object(installateur, 'installer') as installer, \
                patch.object(installateur, 'installer_bashrc'), \
                patch.object(self.config, 'verifier_partition_plateau') as verifier, \
                patch.object(sys, 'argv', ['crypte_installer.py']):
            installateur.main()
        self.assertEqual(installer.call_args.args[0]['game_path'], self.config.game_path)
        verifier.assert_called_once_with()
        destination = self.racine / 'application'
        with patch.object(installateur.os, 'geteuid', return_value=0, create=True):
            installateur.installer(self.profil, destination, self.racine / 'profil.sh')
        hooks = (destination / 'crypte.bash').read_text(encoding='utf-8')
        self.assertIn(str(self.profil['game_path'] / '.systeme/communication/crypte.sock'), hooks)

    def commande(self, ligne, j='j1', retour='0'):
        self.message('before', j, line=ligne, command=ligne, kind='file', history='1/1')
        atelier = self.crypte.zone(self.profil, j) / 'atelier'
        if ligne == 'mkdir appel' and retour == '0':
            (atelier / 'appel').mkdir()
        elif ligne == 'touch appel/cavalerie':
            (atelier / 'appel/cavalerie').touch()
        elif ligne == 'cp appel/cavalerie appel/offrande':
            shutil.copyfile(atelier / 'appel/cavalerie', atelier / 'appel/offrande')
        elif ligne == 'mv appel/offrande appel/poulin':
            (atelier / 'appel/offrande').rename(atelier / 'appel/poulin')
        self.message('after', j, status=retour)

    def reussir(self, j='j1'):
        self.message('start', j)
        for ligne in self.crypte.RECETTE:
            self.commande(ligne, j)
        # L'ouverture par descripteur Unix est exercée dans les tests Linux.
        with patch.object(self.crypte, 'verifier_offrande'):
            self.message('end', j)

    def creer(self, tour=3):
        with self.config.racines_generation(self.config.game_path,
                {j: self.racine / 'home' / j for j in self.profil['joueurs']}):
            self.crypte.materialiser(self.profil, tour)

    def etapes_archers(self):
        self.message('start')
        for i, ligne in enumerate(self.crypte.RECETTE2):
            commandes = ('cat a.txt', 'grep "NAME"') if i == 2 else (ligne,)
            for k, commande in enumerate(commandes):
                self.message('component' if k else 'before', line=ligne, command=commande,
                             kind='file', history=f'{i + 1}/1')
            self.message('after', status='0', command='0 0' if i == 2 else '0')

    def reussir_archers(self):
        self.etapes_archers()
        with patch.object(self.crypte, 'verifier_lecture'):
            self.message('end')

    def test_archers_composition_quota_et_affichage(self):
        self.etat.sauvegarder_compteur_general('j1', 5)
        self.etat.sauvegarder_quota_normal('j1', 5)
        self.reussir_archers()
        self.creer()
        p = self.crypte.zone(self.profil, 'j1') / 'recompense/har_chez_moi1'
        self.assertEqual([len(list((p / b).iterdir())) for b in self.config.ordre_blocs], [0, 0, 0, 20])
        self.assertEqual(len(list(p.glob('arriere/infanterie*/arc'))), 20)
        self.assertFalse(list(p.glob('*/cavalerie*')))
        self.assertFalse(list(p.glob('*/*/pique')))
        self.assertEqual(self.etat.initialiser_quota_normal('j1'), 5)
        fiche = self.generaux.lire_fiche_general(p)
        self.assertEqual(fiche['nom'], 'har_chez_moi1')
        self.assertEqual(fiche['nom_affichage'], 'har-chez-moi')
        general = {'joueur': 'j1', 'nom': 'har_chez_moi1', 'fiche': fiche}
        self.assertEqual(self.rapports.nom_affichage_general(general), 'har-chez-moi')
        fiche['nom_affichage'] = self.crypte.NOM
        self.assertEqual(self.rapports.nom_affichage_general(general), 'har_chez_moi1')

    def test_cooldowns_independants_et_limite_par_tour(self):
        self.reussir()
        p = self.crypte.zone(self.profil, 'j1') / 'recompense'
        (p / 'amelie_poulin1').rename(self.config.game_path / 'village/j1/caserne_militaire/amelie_poulin1')
        with self.assertRaisesRegex(ValueError, 'par tour'):
            self.message('start')
        self.activer(4)
        self.reussir_archers()
        self.assertEqual(self.crypte.charger(self.profil)['j1']['derniers_tours'],
                         {'recette1': 3, 'recette2': 4, 'recette3': None})
        self.activer(8)
        with self.assertRaisesRegex(ValueError, 'attente'):
            self.message('start')
        (p / 'har_chez_moi1').rename(self.config.game_path / 'village/j1/caserne_militaire/har_chez_moi1')
        self.reussir()
        self.assertTrue((p / 'amelie_poulin2').is_dir())

    def test_attribution_historique_sans_recette(self):
        d = self.crypte.charger(self.profil)
        d['j1'].pop('derniers_tours')
        d['j1']['dernier_tour'] = 3
        d['j1']['a_creer'] = {'id': 'historique', 'tour': 3}
        self.crypte.sauver(self.profil, d)
        self.assertEqual(self.crypte.charger(self.profil)['j1']['derniers_tours'],
                         dict.fromkeys(self.crypte.RECETTES, 3))
        self.creer()
        p = self.crypte.zone(self.profil, 'j1') / 'recompense/amelie_poulin1'
        self.assertEqual(len(list(p.glob('*/cavalerie*/cheval'))), 20)

    def test_pipeline_incomplet_ou_echec_masque(self):
        for composants, codes in ((1, '0 0'), (2, '1 0'), (2, '0 1'), (2, ''), (3, '0 0 0')):
            with self.subTest(composants=composants, codes=codes):
                self.message('start')
                for ligne in self.crypte.RECETTE2[:2]:
                    self.message('before', line=ligne, command=ligne, kind='file', history='1/1')
                    self.message('after', status='0')
                for i in range(composants):
                    self.message('before' if i == 0 else 'component', line=self.crypte.RECETTE2[2],
                                 command='cat a.txt' if i == 0 else 'grep "NAME"', kind='file', history='2/1')
                self.message('after', status='0', command=codes)
                with self.assertRaises(ValueError):
                    self.message('end')
                self.assertIsNone(self.crypte.charger(self.profil)['j1']['dernier_tour'])

    @unittest.skipUnless(sys.platform == 'linux', 'Bash et descripteurs Linux requis')
    def test_bash_reel_deux_recettes_et_fichiers(self):
        from test_crypte_scanner import BashSession
        for j, lignes in (('j1', self.crypte.RECETTE), ('j2', self.crypte.RECETTE2)):
            with self.subTest(joueur=j), tempfile.TemporaryDirectory() as tmp:
                atelier = self.crypte.zone(self.profil, j) / 'atelier'
                shell = BashSession(Path(tmp), atelier=atelier, uid=os.getuid(), gid=os.getgid())
                try:
                    self.message('start', j)
                    shell.command('crypte_commence')
                    sorties = [shell.command(ligne) for ligne in lignes]
                    if j == 'j2':
                        # La commande tapee ne suffit pas : le tableau doit etre affiche.
                        for sortie in sorties[1:]:
                            self.assertRegex(sortie, r'NAME\s+MAJ:MIN')
                    shell.command('crypte_fin')
                    evenements = shell.events()
                    self.assertEqual(sum(e['event'] == 'after' for e in evenements), 4)
                    for e in evenements:
                        if e['event'] == 'start':
                            continue
                        self.message(e['event'], j, **{k: e[k] for k in
                                     ('line', 'command', 'status', 'history', 'kind')})
                    self.assertEqual(len(self.crypte.charger(self.profil)[j]['attributions']), 1)
                finally:
                    shell.close()

    @unittest.skipUnless(sys.platform == 'linux', 'Bash et descripteurs Linux requis')
    def test_bash_reel_variantes_refusees(self):
        from test_crypte_scanner import BashSession
        r1, r2 = self.crypte.RECETTE, self.crypte.RECETTE2
        variantes = [
            (r1, 0, 'mkdir autre'), (r1, 1, 'touch appel/autre'),
            (r1, 2, 'cp appel/cavalerie appel/autre'),
            (r1, 3, 'mv appel/offrande appel/autre'),
            (r1, 0, r1[1]), (r1, 2, 'chmod 600 appel/cavalerie'),
            (r1, 4, 'ls'), (r2, 0, 'lsblk >> a.txt'),
            (r2, 0, 'lsblk > b.txt'), (r2, 1, 'cat b.txt'),
            (r2, 2, 'cat a.txt | grep "name"'),
            (r2, 2, 'cat a.txt | grep NAME'),
            (r2, 2, 'cat a.txt | grep "NAME" | cat'),
            (r2, 2, 'cat a.txt; grep "NAME" a.txt'),
            (r2, 3, 'grep "OTHER" a.txt'), (r2, 3, 'grep "NAME" b.txt'),
            (r2, 1, r2[3]), (r2, 4, 'ls'),
            (r2, 2, 'cat a.txt | grep "NAME"; true'),
        ]
        for recette, index, mauvaise in variantes:
            with self.subTest(ligne=mauvaise, etape=index), tempfile.TemporaryDirectory() as tmp:
                self.crypte.nettoyer(self.profil, 'j1')
                atelier = self.crypte.zone(self.profil, 'j1') / 'atelier'
                shell = BashSession(Path(tmp), atelier=atelier, uid=os.getuid(), gid=os.getgid())
                try:
                    self.message('start')
                    shell.command('crypte_commence')
                    lignes = list(recette)
                    if index == 4:
                        lignes.append(mauvaise)
                    else:
                        lignes[index] = mauvaise
                    for ligne in lignes:
                        shell.command(ligne)
                    shell.command('crypte_fin')
                    for e in shell.events():
                        if e['event'] == 'start':
                            continue
                        champs = {k: e[k] for k in ('line', 'command', 'status', 'history', 'kind')}
                        if e['event'] == 'end':
                            with self.assertRaises(ValueError):
                                self.message('end', **champs)
                        else:
                            self.message(e['event'], **champs)
                    self.assertIsNone(self.crypte.charger(self.profil)['j1']['dernier_tour'])
                finally:
                    shell.close()

    @unittest.skipUnless(os.name == 'posix', 'Descripteurs Unix requis')
    def test_contenu_final_archers_incorrect(self):
        for contenu in (b'', b'aucun entete\n'):
            self.etapes_archers()
            (self.crypte.zone(self.profil, 'j1') / 'atelier/a.txt').write_bytes(contenu)
            with self.assertRaisesRegex(ValueError, 'NAME'):
                self.message('end')
            self.assertIsNone(self.crypte.charger(self.profil)['j1']['dernier_tour'])

    def test_reussite_persistante_avec_creation_immediate(self):
        self.reussir()
        donnees = self.crypte.charger(self.profil)['j1']
        self.assertEqual(donnees['dernier_tour'], 3)
        self.assertEqual(donnees['attributions'][0]['id'], self.tokens['j1'])
        self.assertEqual([p.name for p in (self.crypte.zone(self.profil, 'j1') / 'recompense').iterdir()], ['amelie_poulin1'])
        self.assertEqual(self.etat.lire_compteur_general('j1'), 0)
        nouveau = self.crypte.Collecteur(self.profil, horloge=lambda: 1)
        self.assertEqual(self.crypte.charger(nouveau.c), self.crypte.charger(self.profil))

    def test_composition_identite_affichage_zone_inactive(self):
        self.reussir()
        self.creer()
        p = self.crypte.zone(self.profil, 'j1') / 'recompense/amelie_poulin1'
        self.assertTrue(self.generaux.est_general_valide(p))
        self.assertEqual([len(list((p / b).iterdir())) for b in self.config.ordre_blocs], [10, 5, 5, 0])
        self.assertEqual(len(list(p.glob('*/cavalerie*/cheval'))), 20)
        fiche = self.generaux.lire_fiche_general(p)
        self.assertEqual(fiche['nom'], 'amelie_poulin1')
        self.assertEqual(fiche['nom_affichage'], self.crypte.NOM)
        self.assertEqual(self.rapports.nom_affichage_general({'joueur': 'j1', 'nom': 'amelie_poulin1', 'fiche': fiche}), self.crypte.NOM)
        forces = self.generaux.lire_forces_territoire(self.config.game_path / 'village', self.profil)
        self.assertEqual(self.generaux.controle_forces(forces), 'neutre')
        self.assertEqual(self.etat.charger_positions_generaux()['j1:amelie_poulin1'], 'village')

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
        self.assertEqual(len(self.crypte.charger(self.profil)['j1']['attributions']), 1)

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
        (self.crypte.zone(self.profil, 'j1') / 'recompense/amelie_poulin1').rename(
            self.config.game_path / 'village/j1/caserne_militaire/amelie_poulin1')
        self.activer(4)
        self.reussir('j2')
        self.creer(4)
        (self.crypte.zone(self.profil, 'j2') / 'recompense/amelie_poulin1').rename(
            self.config.game_path / 'village/j2/caserne_militaire/amelie_poulin1')
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.activer(7)
        self.message('start', 'j1')
        self.commande(self.crypte.RECETTE[0], 'j1')
        with self.assertRaisesRegex(ValueError, 'tour 8'):
            self.message('end', 'j1')
        self.activer(8)
        self.reussir('j1')
        self.message('start', 'j2')
        self.commande(self.crypte.RECETTE[0], 'j2')
        with self.assertRaisesRegex(ValueError, 'tour 9'):
            self.message('end', 'j2')
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
        self.assertEqual(self.crypte.charger(self.profil)['j1']['en_attente'], 'amelie_poulin1')
        self.assertEqual(self.etat.initialiser_quota_normal('j1'), 5)
        self.generaux.faire_apparaitre_general_si_possible('j1', self.profil)
        self.assertEqual(self.etat.lire_compteur_general('j1'), 5)

    def test_bonus_ne_consomme_pas_creation_normale(self):
        self.reussir()
        self.creer()
        self.generaux.faire_apparaitre_general_si_possible('j1', self.profil)
        self.assertEqual(self.etat.initialiser_quota_normal('j1'), 1)
        self.assertEqual(self.etat.lire_compteur_general('j1'), 1)
        self.assertTrue((self.racine / 'home/j1/general1').exists())

    def test_rapport_activites_par_joueur_et_remplacement(self):
        import rapports
        rapports.preparer_activites(self.profil, 3)
        rapports.noter_activite(self.profil, 'j1', 'CASERNE MILITAIRE',
                               'amelie_poulin1 : +1 formation')
        premier = self.profil['game_path'] / 'village/j1/hotel_de_ville/rapport_activites.txt'
        autre = self.profil['game_path'] / 'village/j2/hotel_de_ville/rapport_activites.txt'
        self.assertIn('+1 formation', premier.read_text(encoding='utf-8'))
        self.assertNotIn('+1 formation', autre.read_text(encoding='utf-8'))
        rapports.preparer_activites(self.profil, 4)
        self.assertIn('TOUR 4', premier.read_text(encoding='utf-8'))
        self.assertNotIn('+1 formation', premier.read_text(encoding='utf-8'))

    def test_generation_privee_publication_sans_rejeu(self):
        self.reussir()
        g = self.gestion()
        original = self.crypte.materialiser
        racines = []
        def mater(c, tour):
            self.assertNotEqual(c['game_path'], self.config.game_path)
            self.assertTrue(list((self.crypte.zone(self.profil, 'j1') / 'recompense').iterdir()))
            racines.append(c['game_path'])
            original(c, tour)
        with patch.object(self.crypte, 'materialiser', side_effect=mater):
            self.survie.resoudre_tour_survie(self.profil, random.Random(4), g)
        self.assertEqual(len(racines), 1)
        self.assertTrue((self.crypte.zone(self.profil, 'j1') / 'recompense/amelie_poulin1').exists())
        self.assertEqual(len(self.crypte.charger(self.profil)['j1']['attributions']), 1)
        with self.assertRaises(RuntimeError):
            self.survie.resoudre_tour_survie(self.profil, gestion=g)

    @unittest.skipUnless(os.name == 'posix', 'Permissions Linux requises')
    def test_permissions_recompense_consultation_puis_actions(self):
        self.reussir()
        self.creer()
        gestion = self.gestion()
        parent = self.crypte.zone(self.profil, 'j1') / 'recompense'
        general = parent / 'amelie_poulin1'
        destination = self.config.game_path / 'village/j1/garnison/1'
        # Ce scénario vérifie les modes réels ; le fixture général simule chmod.
        self.contextes.enter_context(patch.object(os, 'chmod', side_effect=CHMOD_REEL))
        for chemin in (parent, general, destination):
            CHMOD_REEL(chemin, 0o700)
        gestion.permissions_consultation()
        for chemin in (parent, general, destination):
            self.assertEqual(chemin.stat().st_mode & 0o700, 0o500)
        gestion.permissions_actions()
        for chemin in (parent, general, destination):
            self.assertEqual(chemin.stat().st_mode & 0o700, 0o700)
        self.assertTrue(general.exists())

    def test_rapport_attribution_composition_recuperation_sans_doublon(self):
        self.reussir()
        self.etat.sauvegarder_cycle_survie(dict(tour=3, phase='resolution'), self.profil)
        self.rapports.preparer_activites(self.profil, 3)
        self.creer()
        rapport = self.config.game_path / 'village/j1/hotel_de_ville/rapport_activites.txt'
        self.assertIn('20 unités de type cavalerie', rapport.read_text())
        self.assertIn('10/5/5/0', rapport.read_text())
        source = self.crypte.zone(self.profil, 'j1') / 'recompense/amelie_poulin1'
        source.rename(self.config.game_path / 'village/j1/garnison/1/amelie_poulin1')
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertEqual(rapport.read_text().count('récupération constatée'), 1)
        self.assertNotIn('amelie_poulin1', (self.config.game_path / 'village/j2/hotel_de_ville/rapport_activites.txt').read_text())

    def test_recuperation_mv_puis_retour_interdit(self):
        self.reussir()
        self.creer()
        source = self.crypte.zone(self.profil, 'j1') / 'recompense/amelie_poulin1'
        cible = self.config.game_path / 'village/j1/garnison/1/amelie_poulin1'
        source.rename(cible)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertEqual(self.etat.charger_positions_generaux()['j1:amelie_poulin1'], 'village')
        self.assertIsNone(self.crypte.charger(self.profil)['j1']['en_attente'])
        cible.rename(source)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertFalse(source.exists())
        self.assertEqual(self.etat.charger_positions_generaux()['j1:amelie_poulin1'], 'repli')

    def test_trois_pdf(self):
        for j in ('j1', 'j2'):
            grimoire = self.crypte.zone(self.profil, j) / 'grimoire'
            self.assertEqual(sorted(p.name for p in grimoire.iterdir()),
                             ['recette1.txt', 'recette2.txt', 'recette3.txt'])
            for identifiant, recette in self.crypte.RECETTES.items():
                contenu = (grimoire / f'{identifiant}.txt').read_bytes()
                self.assertTrue(contenu.startswith(b'MYTHODEA'))
                for ligne in recette['lignes']:
                    self.assertIn(ligne.encode(), contenu)
            self.assertNotIn(b'chmod', (grimoire / 'recette1.txt').read_bytes())

    def test_echeance_refusee_sans_consommation(self):
        self.collecteur.horloge = lambda: 100
        with self.assertRaisesRegex(ValueError, 'fermée'):
            self.message('start')
        self.assertIsNone(self.crypte.charger(self.profil)['j1']['dernier_tour'])

    def test_collecteur_defaillant_interdit_resolution(self):
        self.collecteur.erreur = 'nettoyage interrompu'
        with patch.dict(self.crypte.SERVICES, {str(self.profil['game_path']): self.collecteur}):
            with patch.object(self.securite, 'verifier_tous_les_deplacements') as audit:
                with self.assertRaisesRegex(RuntimeError, 'Collecteur Crypte'):
                    self.survie.resoudre_tour_survie(self.profil, gestion=self.gestion())
                audit.assert_not_called()
        self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'recuperation')

    def test_nom_affichage_non_attribue_reste_technique(self):
        general = {'joueur': 'j1', 'nom': 'general9', 'fiche': {'nom_affichage': self.crypte.NOM}}
        self.assertEqual(self.rapports.nom_affichage_general(general), 'general9')

    def test_marqueurs_configures_et_pdf_actualise(self):
        self.etat.ecrire_prive(self.profil['game_path'] / '.systeme/crypte_config.json',
                               json.dumps({'debut': 'crypte_ouvre', 'fin': 'crypte_ferme'}))
        self.crypte.preparer(self.profil)
        pdf = self.crypte.zone(self.profil, 'j1') / 'grimoire/recette1.txt'
        self.assertIn(b'crypte_ouvre', pdf.read_bytes())
        self.assertIn(b'crypte_ferme', pdf.read_bytes())
        self.assertNotIn(b'crypte_commence', pdf.read_bytes())

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
