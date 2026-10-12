"""Accueil, publication et refus des anciens plateaux, en isolation."""
import hashlib
import unittest
from unittest.mock import call, patch

import test_cycle_survie
from support_cycle import GelSimule


class AccueilSurvie(unittest.TestCase):
    journaux = ('journal_du_Toonitruand', 'journal_du_veteran')
    setUp = test_cycle_survie.CycleSurvie.setUp
    activer = test_cycle_survie.CycleSurvie.activer
    general = test_cycle_survie.CycleSurvie.general

    def hotel(self, joueur='j1'):
        return self.config.game_path / 'village' / joueur / 'hotel_de_ville'

    def verifier_journal(self, vague):
        for joueur in self.profil['joueurs']:
            for nom in self.journaux:
                journal = self.hotel(joueur) / nom
                self.assertEqual({p.name for p in journal.iterdir()},
                                 {f'vague_{n}.txt' for n in range(vague + 1)})

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
        self.verifier_journal(10)

    def test_nouvelle_partie_et_publication_premiere_vague(self):
        (self.config.game_path / '.systeme/cycle_survie.json').unlink()
        self.survie.ouvrir_tour_survie(self.profil)
        self.verifier_journal(0)
        avant = (self.hotel() / 'journal_du_Toonitruand/vague_0.txt').read_bytes()
        self.survie.resoudre_tour_survie(self.profil)
        self.verifier_journal(1)
        self.assertEqual((self.hotel() / 'journal_du_Toonitruand/vague_0.txt').read_bytes(), avant)

    def test_passage_vague_cinq_et_conservation_des_acquis(self):
        self.plateau.preparer_accueil(self.profil, 1)
        self.plateau.preparer_accueil(self.profil, 5)
        self.verifier_journal(5)
        self.plateau.preparer_accueil(self.profil, 2)
        self.verifier_journal(5)

    def test_reprise_directe_vague_quatre_sans_rejouer_la_preparation(self):
        self.activer(4)
        avant = self.etat.charger_cycle_survie(self.profil)
        with patch.object(self.generaux, 'faire_apparaitre_general_si_possible') as apparition:
            self.assertEqual(self.survie.ouvrir_tour_survie(self.profil), avant)
            apparition.assert_not_called()
        self.verifier_journal(4)
        self.assertEqual(self.etat.charger_cycle_survie(self.profil), avant)

    def test_pilote_complete_le_journal_avant_attente_de_reprise(self):
        for phase, tour in (('actions', 4), ('consultation', 3)):
            with self.subTest(phase=phase):
                self.etat.sauvegarder_cycle_survie(
                    {'tour': tour, 'phase': phase, 'echeance': 100}, self.profil)
                for joueur in self.profil['joueurs']:
                    for nom in self.journaux:
                        journal = self.hotel(joueur) / nom
                        for fichier in journal.glob('vague_*.txt'):
                            fichier.unlink()
                def verifier(gestion, cycle):
                    self.verifier_journal(4)
                    raise KeyboardInterrupt
                with patch.object(self.cycle_linux.Generations, 'attendre', autospec=True,
                                  side_effect=verifier), \
                        patch.object(self.plateau, 'preparer_accueil') as accueil:
                    with self.assertRaises(KeyboardInterrupt):
                        self.survie.lancer_partie_survie(self.profil, 1)
                    accueil.assert_not_called()

    def test_idempotence_et_reparation_d_un_conseil_manquant(self):
        self.plateau.preparer_accueil(self.profil, 4)
        fichiers = [p for j in self.profil['joueurs'] for nom in self.journaux
                    for p in (self.hotel(j) / nom).iterdir()]
        # Un ancien texte déjà débloqué ne doit pas être remplacé par le modèle.
        fichiers[0].write_text('Conseil historique conservé.\n', encoding='utf-8')
        avant = {p: (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_ino) for p in fichiers}
        self.plateau.preparer_accueil(self.profil, 4)
        self.verifier_journal(4)
        self.assertEqual(avant, {p: (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_ino)
                                for p in fichiers})
        for nom in self.journaux:
            manquant = self.hotel('j2') / nom / 'vague_2.txt'
            contenu = manquant.read_bytes()
            manquant.unlink()
            self.plateau.preparer_accueil(self.profil, 4)
            self.assertEqual(manquant.read_bytes(), contenu)
        self.verifier_journal(4)

    def test_textes_personnalises_introduction_et_contenu_valide(self):
        self.plateau.preparer_accueil(self.profil, 10)
        for joueur, autre in (('j1', 'j2'), ('j2', 'j1')):
            journal = self.hotel(joueur) / 'journal_du_Toonitruand'
            textes = [(journal / f'vague_{n}.txt').read_text(encoding='utf-8') for n in range(11)]
            for texte in textes:
                self.assertIn('----------------------------------------------------------\n', texte)
                self.assertIn('CONSEIL\n', texte)
                self.assertIn('>>> COMMANDE\n', texte)
                self.assertIn('NOTE :', texte)
                for absent in (autre, '{joueur}', '/chemin/vers/', 'À expliquer librement',
                               'crypte_commence', 'crypte_fin', 'mkdir appel', 'chmod 660 rempart'):
                    self.assertNotIn(absent, texte)
            self.assertIn('déroulement du jeu petit à petit', textes[0].splitlines()[0])
            self.assertLess(textes[0].index('À chaque nouvelle vague'), textes[0].index('CONSEIL'))
            for bloc, unite, equipement in (('arriere', 'infanterie1', 'arc'),
                                             ('droite', 'infanterie2', 'pique'),
                                             ('avant', 'cavalerie1', 'cheval')):
                chemin = f'/home/{joueur}/general1/{bloc}/{unite}'
                self.assertIn(f'mkdir {chemin}\ntouch {chemin}/{equipement}', textes[0])
            self.assertIn(f'/home/game/village/{joueur}/garnison/1/', textes[0])
            self.assertIn('ses fichiers enfants, comme arc, suivent automatiquement', textes[1])
            self.assertIn('Ce rattrapage ne déclenche jamais un deuxième combat', textes[2])
            self.assertIn('Vague 5 - Combats avec plusieurs généraux', textes[5])
            self.assertNotIn('crypte', textes[5].lower())
            self.assertIn('Vague 6 - Découvrir la Crypte', textes[6])
            self.assertIn(f'scp {joueur}@Mythodea.local:/home/game/village/{joueur}/crypte/', textes[6])
            self.assertIn('Une double boucle combine deux répétitions.', textes[10])

    def test_veteran_fidele_au_word_et_personnalise(self):
        # Empreintes des sections 0..10 extraites de Journal_du_Veteran.docx.
        # Seules les lignes vides de mise en page sont ignorées. Les espaces,
        # accents, guillemets, accolades Bash et antislashs restent significatifs.
        empreintes_word = (
            'ef005c2c6adcaa12a03fdc0da67668dc40a4c783faae1a97672ac583501caa01',
            '61296835cc6f0e26e18c4aab88256a55ae75148bc39d0915db9e91d00b772484',
            'd7b1120717de57793c899369ed837870bc6a3beea2a8901e10cdbf62741c3f13',
            'f6c13c8950e90f2a83216eefa890a12c64b76d4a1e104191c7fc222d7c279066',
            '834a4c6dd06d830781b66d130a7f32419f565e0028653480afd429210b0e5aca',
            '7d3b1eca970b2d094b5c3cdc94a114d96b7ad4a757950778027b7cd6056f20d5',
            'e7cbe2553e852261a8c404d60b9a1294ad0e6fec219a132aa2ebe43f4d73fb49',
            '2295098f4f227d574be0ac9001cba6fed824ed24a3db361539ffb379c36ad87a',
            '9d7def71326d5da8ddb4781cef9180c37981742f824f13d633cd6cc9eade44f5',
            '45bbb0845a31ad0ca2c351dcc5777b0c5d4e17a3bcc50ee6c92b9363ec86d04e',
            '6ed6a30b7924da7262f09fb16491cc4def8653b9f16d68ae4c40885f7aa3be0d',
        )
        self.plateau.preparer_accueil(self.profil, 10)
        self.verifier_journal(10)
        for joueur, autre in (('j1', 'j2'), ('j2', 'j1')):
            for numero, empreinte in enumerate(empreintes_word):
                with self.subTest(joueur=joueur, vague=numero):
                    texte = (self.hotel(joueur) / 'journal_du_veteran' /
                             f'vague_{numero}.txt').read_text(encoding='utf-8')
                    self.assertIn('----------------------------------------------------------\n', texte)
                    self.assertIn('CONSEIL\n', texte)
                    self.assertIn('>>> COMMANDE VÉTÉRAN\n', texte)
                    self.assertIn('NOTE :', texte)
                    self.assertNotIn(autre, texte)
                    self.assertNotIn('{joueur}', texte)
                    self.assertNotIn(str(self.racine), texte)
                    normalise = '\n'.join(ligne for ligne in texte.replace(joueur, 'j1').splitlines()
                                          if ligne.strip())
                    self.assertEqual(hashlib.sha256(normalise.encode('utf-8')).hexdigest(), empreinte)

    def test_ajout_veteran_preserve_journal_toonitruand_existant(self):
        self.plateau.preparer_accueil(self.profil, 4)
        anciens = {}
        for joueur in self.profil['joueurs']:
            veteran = self.hotel(joueur) / 'journal_du_veteran'
            for fichier in veteran.iterdir():
                fichier.unlink()
            veteran.rmdir()
            toonitruand = self.hotel(joueur) / 'journal_du_Toonitruand'
            for fichier in toonitruand.iterdir():
                anciens[fichier] = (fichier.read_bytes(), fichier.stat().st_mtime_ns)
        self.activer(4)
        self.survie.ouvrir_tour_survie(self.profil)
        self.verifier_journal(4)
        for fichier, avant in anciens.items():
            self.assertEqual((fichier.read_bytes(), fichier.stat().st_mtime_ns), avant)

    def test_permissions_du_journal_et_aucune_vague_en_avance(self):
        self.activer(0)
        self.plateau.preparer_accueil(self.profil)
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        gestion.permissions_actions()
        self.verifier_journal(0)
        for joueur in self.profil['joueurs']:
            gid = self.plateau.grp.getgrnam(self.profil['acteurs'][joueur]['groupe_linux']).gr_gid
            for nom in self.journaux:
                journal = self.hotel(joueur) / nom
                self.assertIn(call(journal, 0, gid), self.chown.call_args_list)
                self.assertIn(call(journal, 0o750), self.chmod.call_args_list)
                self.assertIn(call(journal / 'vague_0.txt', 0, gid), self.chown.call_args_list)
                self.assertIn(call(journal / 'vague_0.txt', 0o640), self.chmod.call_args_list)
        self.etat.sauvegarder_cycle_survie(
            {'tour': 0, 'phase': 'consultation', 'echeance': 100}, self.profil)
        gestion.permissions_actions()
        self.verifier_journal(1)

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
            self.assertNotIn(str(self.racine), texte)
            self.assertIn(f'/home/game/village/{j}/garnison/1', texte)
            veteran = (self.hotel(j) / 'journal_du_veteran/vague_2.txt').read_text(encoding='utf-8')
            self.assertNotIn(str(self.racine), veteran)
            self.assertIn(f'find /home/{j}', veteran)
        self.verifier_journal(2)
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
            self.verifier_journal(0)
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
