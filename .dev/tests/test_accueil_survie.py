"""Accueil, publication et refus des anciens plateaux, en isolation."""
import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
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
            self.assertTrue(texte.startswith('\n'), 'Une ligne vide doit précéder le titre')
            self.assertIn(f'ls -l /home/{j}', texte)
            self.assertIn('village/clocher/etat_tour.log', texte)
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
            self.assertIn('déroulement du jeu petit à petit',
                          next(ligne for ligne in textes[0].splitlines() if ligne.strip()))
            self.assertLess(textes[0].index('À chaque nouvelle vague'), textes[0].index('CONSEIL'))
            for bloc, unite, equipement in (('arriere', 'infanterie1', 'arc'),
                                             ('droite', 'infanterie2', 'pique'),
                                             ('avant', 'cavalerie1', 'cheval')):
                chemin = f'/home/{joueur}/general1/{bloc}/{unite}'
                self.assertIn(f'mkdir {chemin}\ntouch {chemin}/{equipement}', textes[0])
            self.assertIn(f'/game/village/{joueur}/garnison/1/', textes[0])
            self.assertIn('ses fichiers enfants, comme arc, suivent automatiquement', textes[1])
            self.assertIn('Ce rattrapage ne déclenche jamais un deuxième combat', textes[2])
            self.assertIn('Vague 5 - Combats avec plusieurs généraux', textes[5])
            self.assertNotIn('crypte', textes[5].lower())
            self.assertIn('Vague 6 - Découvrir la Crypte', textes[6])
            self.assertIn(f'scp {joueur}@Mythodea.local:/game/village/{joueur}/crypte/', textes[6])
            self.assertIn('Une double boucle combine deux répétitions.', textes[10])

    def test_journaux_racine_publique_injectee(self):
        self.profil['game_public_path'] = self.config.Path('/plateau-public')
        self.plateau.preparer_accueil(self.profil, 0)
        for nom in self.journaux:
            texte = (self.hotel('j1') / nom / 'vague_0.txt').read_text(encoding='utf-8')
            self.assertIn('/plateau-public/village/j1', texte)
            self.assertNotIn('{game_path}', texte)
            self.assertNotIn('/game/', texte)

    def test_veteran_textes_valides_et_personnalises(self):
        # Empreintes des conseils validés, corrigés après les essais Raspberry Pi.
        # Seules les lignes vides de mise en page sont ignorées. Les espaces,
        # accents, guillemets, accolades Bash et antislashs restent significatifs.
        empreintes_valides = (
            'b73a50d4340d964ab576bb4f69bebd44f77a507b260c6aa8b18fa8614aaa167d',
            '7d37b50ac0f44bc14c38458c7a55728c579ff6843b037792da0b1ca107198a6c',
            'df7ffdbdef2408e529e016eae508d368cc533d60379d3ed526652ebfecb75d4b',
            'f6c13c8950e90f2a83216eefa890a12c64b76d4a1e104191c7fc222d7c279066',
            '834a4c6dd06d830781b66d130a7f32419f565e0028653480afd429210b0e5aca',
            '7d3b1eca970b2d094b5c3cdc94a114d96b7ad4a757950778027b7cd6056f20d5',
            'dd3ceeb5cb21f247722c543236c984bc873e15a6a4fafd72071eee40e9c0f56a',
            '2295098f4f227d574be0ac9001cba6fed824ed24a3db361539ffb379c36ad87a',
            '17bd5af19ac38e806af50fa0cf0d9018ab6be4286dd6288527af5341680de91c',
            '9e6e55b3b216076347acba740bc891204df6c32efd4d385c68c79e1053565759',
            '02ff5327f95c92fa600b5f8c48febf84a1dd06b5aee8d52996b8432610d40108',
        )
        self.plateau.preparer_accueil(self.profil, 10)
        self.verifier_journal(10)
        for joueur, autre in (('j1', 'j2'), ('j2', 'j1')):
            for numero, empreinte in enumerate(empreintes_valides):
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
                    self.assertNotIn('/reserve', texte)
                    # Normalisation historique conservée pour les conseils inchangés.
                    # Le texte courant, et non le Word d'origine, fait référence.
                    historique = (texte.replace('/game/', '/home/game/').replace(joueur, 'j1')
                                  .replace('/caserne_militaire', '/reserve'))
                    normalise = '\n'.join(ligne for ligne in historique.splitlines()
                                          if ligne.strip())
                    self.assertEqual(hashlib.sha256(normalise.encode('utf-8')).hexdigest(), empreinte)

    @unittest.skipUnless(shutil.which('bash'), 'Commandes pédagogiques Bash requises')
    def test_commandes_journaux_recettes_et_surnombre(self):
        self.plateau.preparer_accueil(self.profil, 10)
        for nom in self.journaux:
            journal = self.hotel() / nom
            for fichier in journal.glob('vague_*.txt'):
                self.assertNotIn('ordre.txt', fichier.read_text(encoding='utf-8'))
            for vague in (8, 9, 10):
                with self.subTest(journal=nom, vague=vague), tempfile.TemporaryDirectory() as dossier:
                    racine = Path(dossier)
                    general = racine / 'village/j1/garnison/1/general1'
                    for bloc in ('avant', 'arriere', 'droite', 'gauche', 'info'):
                        (general / bloc).mkdir(parents=True)
                    choix = general / 'info/ordre_surnombre.txt'
                    choix.write_text('2\n')
                    texte = (journal / f'vague_{vague}.txt').read_text(encoding='utf-8')
                    commandes = re.findall(r'>>> COMMANDE[^\n]*\n\n(.*?)\n\nNOTE :', texte, re.S)
                    self.assertTrue(commandes)
                    for commande in commandes:
                        subprocess.run(['bash', '-eu', '-o', 'pipefail', '-c',
                                        commande.replace('/game/', str(racine) + '/')],
                                       cwd=general, check=True, capture_output=True, text=True)
                    if vague == 8:
                        self.assertEqual(choix.read_text(), '1\n')
                        self.assertEqual(self.generaux.lire_ordre_surnombre(
                            dict(chemin=general, joueur='j1'), 'est_1', self.profil), 1)
                    else:
                        unites = [p for bloc in ('avant', 'arriere', 'droite', 'gauche')
                                  for p in (general / bloc).iterdir()]
                        attendu = 'archer' if vague == 9 else 'piquier'
                        self.assertEqual(len(unites), 5 if vague == 9 else 6)
                        for unite in unites:
                            self.assertEqual(self.generaux.identifier_unite(unite), attendu)

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
        log = self.config.game_path / 'village/clocher/etat_tour.log'
        self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        self.assertIn("CONSULTATION", log.read_text())
        self.assertFalse((gestion.generation / 'capture/game/village/clocher').exists())
        for j in self.profil['joueurs']:
            self.assertEqual((self.hotel(j) / 'rapport.txt').read_bytes(),
                             self.config.rapport_court_path.read_bytes())
            texte = (self.hotel(j) / 'journal_du_Toonitruand/vague_2.txt').read_text(encoding='utf-8')
            self.assertNotIn('generations', texte)
            self.assertNotIn(str(self.racine), texte)
            self.assertIn(f'/game/village/{j}/garnison/1', texte)
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
        with (chemin / 'info/fiche.txt').open('a') as f:
            f.write('\nposition_surnombre=5\n')
        general = {'chemin': chemin, 'nom': chemin.name, 'joueur': 'j1', 'emplacement': '1'}
        self.assertEqual(self.mouvements.preparer_retraites_surnombre(
            [general], self.config.game_path / 'est_1', self.profil),
            [(general, self.config.game_path / 'village/j1/caserne_militaire/general1')])
        self.assertTrue(chemin.exists())
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {})

    def test_annonce_apres_preparation_uniquement_au_demarrage(self):
        (self.config.game_path / '.systeme/cycle_survie.json').unlink()
        self.profil.update(duree_phase_action_secondes=0, duree_consultation_secondes=0)
        def verifier(gestion):
            self.verifier_journal(0)
            self.assertTrue((gestion.game / 'village/clocher/etat_tour.log').exists())
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
