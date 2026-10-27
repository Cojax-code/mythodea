"""Cabane, flags, récompense unique et cavalerie lourde sur plateau isolé."""
import importlib
import os
from pathlib import Path
import random
import shutil
import unittest
from unittest.mock import call, patch

import test_cycle_survie
from support_cycle import GelSimule


class DefisSurvie(unittest.TestCase):
    activer = test_cycle_survie.CycleSurvie.activer
    general = test_cycle_survie.CycleSurvie.general
    photo = test_cycle_survie.CycleSurvie.photo

    def setUp(self):
        test_cycle_survie.CycleSurvie.setUp(self)
        self.defis = importlib.import_module('defis')
        self.contextes.enter_context(patch.object(os, 'fchown', create=True))
        self.contextes.enter_context(patch.object(os, 'fchmod', create=True))
        self.plateau.preparer_accueil(self.profil)
        self.survie.crypte.preparer(self.profil)

    def hotel(self, j='j1'):
        return self.config.game_path / 'village' / j / 'hotel_de_ville'

    def donnees(self):
        return self.defis.charger(self.profil)

    def defi(self, j='j1'):
        return self.donnees()['joueurs'][j][self.defis.DEFI]

    def flag(self):
        return self.donnees()['flags'][self.defis.DEFI]

    def envoyer(self, contenu=None, j='j1'):
        p = self.hotel(j) / 'courrier/envoie_message.txt'
        ancien = p.stat().st_mtime_ns
        p.write_text(contenu if contenu is not None else 'FLAG ' + self.flag() + '\n', encoding='utf-8')
        os.utime(p, ns=(ancien + 10000000, ancien + 10000000))

    def scanner(self):
        self.defis.scanner(self.profil, lambda: 1)

    def reponse(self, j='j1'):
        return (self.hotel(j) / 'courrier/reception_message.txt').read_text(encoding='utf-8')

    def materialiser(self):
        # Résolveur privé simulé, sans copie ni publication dans ces tests unitaires.
        self.defis.materialiser(self.profil, 1)

    def recompense(self, j='j1'):
        return self.config.game_path / 'village' / j / 'crypte/recompense' / self.defi(j)['general']

    def resoudre(self):
        g = self.cycle_linux.Generations(self.profil, GelSimule())
        with patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, random.Random(3), g)
        return g

    def valider(self, j='j1'):
        self.envoyer(j=j)
        self.scanner()

    def test_cabane_documents_archives_et_secret_uniquement_dans_archives(self):
        cabane = self.config.game_path / 'est_2/cabane_mysterieuse'
        self.assertEqual({p.relative_to(cabane).as_posix() for p in cabane.rglob('*') if p.is_file()}, {
            'readme.txt', 'coffre/.sceau', 'archives/registre1.txt', 'archives/registre2.txt',
            'archives/registre3.txt', 'notes/note1.txt', 'notes/note2.txt'})
        self.assertEqual((cabane / 'coffre/.sceau').read_text(), 'SCEAU=NOIR-17\n')
        for p in (cabane / 'archives').iterdir():
            self.assertTrue(30 <= len(p.read_text(encoding='utf-8').splitlines()) <= 50)
        occurrences = [ligne for p in (cabane / 'archives').iterdir()
                       for ligne in p.read_text(encoding='utf-8').splitlines() if 'NOIR-17' in ligne]
        self.assertEqual(occurrences, ['NOIR-17 ' + self.flag()])
        for p in cabane.rglob('*.txt'):
            if p.parent.name != 'archives':
                self.assertNotIn(self.flag(), p.read_text(encoding='utf-8'))
        for nom in ('note1.txt', 'note2.txt'):
            texte = (cabane / 'notes' / nom).read_text(encoding='utf-8')
            self.assertTrue(5 <= len(texte.splitlines()) <= 8)
        for commande in ('ls -la', 'cat ', 'grep '):
            self.assertNotIn(commande, (cabane / 'readme.txt').read_text(encoding='utf-8'))
        self.assertNotIn(self.flag(), self.reponse())
        self.assertFalse((self.hotel() / 'bestiaire/cavalerie_lourde.txt').exists())

    def test_preparation_idempotente_et_permissions(self):
        avant = self.photo()
        self.defis.preparer(self.profil)
        self.assertEqual(self.photo(), avant)
        sceau = self.config.game_path / 'est_2/cabane_mysterieuse/coffre/.sceau'
        self.assertIn(call(sceau, 0, 0), self.chown.call_args_list)
        self.assertIn(call(sceau, 0o600), self.chmod.call_args_list)
        prive = self.config.game_path / '.systeme/defis.tmp'
        self.assertIn(call(prive, 0, 0), self.chown.call_args_list)
        self.assertIn(call(prive, 0o600), self.chmod.call_args_list)

    def test_acces_cabane_selon_camp_publie_et_non_joueur(self):
        cabane = self.config.game_path / 'est_2/cabane_mysterieuse'
        for camp, gid, dossier, fichier in (
                ('allies', 1003, 0o750, 0o640), ('bot', 0, 0o700, 0o600),
                ('neutre', 0, 0o700, 0o600), ('conteste', 0, 0o700, 0o600),
                ('j1', 0, 0o700, 0o600), ('j2', 0, 0o700, 0o600)):
            with self.subTest(camp=camp):
                self.config.controle_territoires_path.write_text('est_2=' + camp)
                self.chmod.reset_mock()
                self.chown.reset_mock()
                self.defis.publier_acces(self.profil)
                for p in [cabane, *cabane.rglob('*')]:
                    self.chown.assert_any_call(p, 0, gid)
                    self.chmod.assert_any_call(p, dossier if p.is_dir() else fichier)
        # Un autre camp configuré passe par son groupe Unix, sans test j1/j2.
        self.profil['groupes_camps'] = {'equipe_verte': 'mythodea_allies'}
        self.config.controle_territoires_path.write_text('est_2=equipe_verte')
        self.defis.publier_acces(self.profil)
        self.assertEqual(self.chown.call_args_list[-1].args[2], 1003)
        self.assertEqual({self.profil['acteurs'][j]['camp'] for j in ('j1', 'j2')}, {'allies'})

    def test_acces_stable_pendant_actions_et_recalcule_en_publication(self):
        self.config.controle_territoires_path.write_text('est_2=allies')
        with patch.object(self.defis, 'publier_acces', wraps=self.defis.publier_acces) as acces:
            self.defis.preparer(self.profil)
            self.scanner()
            acces.assert_not_called()
            self.resoudre()  # Aucun général sur EST_2 : état publié neutre.
            acces.assert_called_once_with(self.profil)
        self.assertEqual(self.etat.charger_controle_territoires(self.profil)['est_2'], 'neutre')
        self.chmod.assert_any_call(self.config.game_path / 'est_2/cabane_mysterieuse', 0o700)

    def test_messages_multiples_et_reponses_existantes_conserves(self):
        reception = self.hotel() / 'courrier/reception_message.txt'
        reception.write_text('Réponse antérieure sans saut', encoding='utf-8')
        contenu = 'Bonjour\nFLAG faux\nFLAG ' + self.flag() + '\nFLAG ' + self.flag() + '\nAutre demande\n'
        self.envoyer(contenu)
        self.scanner()
        self.assertEqual((self.hotel() / 'courrier/envoie_message.txt').read_text(encoding='utf-8'), contenu)
        self.assertTrue(self.reponse().startswith('Réponse antérieure sans saut\n'))
        self.assertEqual(self.reponse().count('Flag valide.'), 1)
        self.assertIn('Ce défi a déjà été validé.', self.reponse())
        self.materialiser()
        self.assertEqual(self.etat.lire_compteur_general('j1'), 1)

    @unittest.skipUnless(os.name == 'posix', 'Liens et descripteurs Unix requis')
    def test_courrier_refuse_liens_et_ne_touche_pas_leur_cible(self):
        cible = self.racine / 'cible.txt'
        cible.write_text('FLAG ' + self.flag(), encoding='utf-8')
        for nom in ('envoie_message.txt', 'reception_message.txt'):
            chemin = self.hotel() / 'courrier' / nom
            sauvegarde = chemin.read_bytes()
            for lien in ('symbolique', 'dur'):
                with self.subTest(nom=nom, lien=lien):
                    chemin.unlink()
                    if lien == 'symbolique':
                        chemin.symlink_to(cible)
                    else:
                        os.link(cible, chemin)
                    avant = cible.read_bytes()
                    with self.assertRaises((OSError, RuntimeError)):
                        if nom == 'envoie_message.txt':
                            self.scanner()
                        else:
                            self.defis.repondre(self.profil, 'j1', 'Réponse')
                    self.assertEqual(cible.read_bytes(), avant)
                    self.assertFalse(self.defi()['termine'])
                    chemin.unlink()
                    chemin.write_bytes(sauvegarde)

    def test_flag_invalide_et_syntaxe_stricte(self):
        for contenu in ('FLAG faux', 'FLAG', 'FLAG ' + self.flag() + ' suite'):
            self.envoyer(contenu)
            self.scanner()
            self.assertFalse(self.defi()['termine'])
            self.assertFalse(self.defi()['recompense_recue'])
            self.assertEqual(self.etat.lire_compteur_general('j1'), 0)
            self.assertIn('Flag invalide.', self.reponse())

    def test_flag_valide_fiche_immediate_et_general_differe(self):
        self.valider()
        self.assertTrue(self.defi()['termine'])
        self.assertFalse(self.defi()['recompense_recue'])
        self.assertEqual(self.etat.lire_compteur_general('j1'), 0)
        fiche = self.hotel() / 'bestiaire/cavalerie_lourde.txt'
        self.assertEqual(fiche.read_text(encoding='utf-8'), self.defis.FICHE)
        exemple = Path(__file__).resolve().parents[1] / 'exemples/bestiaire_cavalerie_lourde.txt'
        self.assertEqual(exemple.read_text(encoding='utf-8'), self.defis.FICHE)
        self.assertIn('Construction :\nVerrouillée', self.defis.FICHE)
        self.assertIn('Flag valide.', self.reponse())
        self.assertNotIn(self.flag(), self.reponse())
        if os.name == 'posix':
            self.assertEqual(os.fchown.call_args.args[1:], (0, 1001))
            self.assertEqual(os.fchmod.call_args.args[1:], (0o640,))
        else:
            self.assertIn(call(fiche, 0, 1001), self.chown.call_args_list)
            self.assertIn(call(fiche, 0o640), self.chmod.call_args_list)

    def test_relecture_identique_ne_reecrit_rien_et_reenvoi_est_deja_valide(self):
        self.valider()
        avant = self.photo()
        with patch.object(self.defis, 'sauver') as sauver, patch.object(self.defis, 'repondre') as repondre:
            self.scanner()
        sauver.assert_not_called()
        repondre.assert_not_called()
        self.assertEqual(self.photo(), avant)
        self.envoyer()
        self.scanner()
        self.assertIn('Ce défi a déjà été validé.', self.reponse())
        self.materialiser()
        self.materialiser()
        self.assertEqual(self.etat.lire_compteur_general('j1'), 1)

    def test_progressions_j1_j2_independantes(self):
        self.valider()
        self.assertFalse(self.defi('j2')['termine'])
        self.assertFalse((self.hotel('j2') / 'bestiaire/cavalerie_lourde.txt').exists())
        self.valider('j2')
        self.materialiser()
        self.assertTrue(self.recompense().exists())
        self.assertTrue(self.recompense('j2').exists())

    def test_recompense_hors_quota_composition_identite_et_rapport(self):
        self.etat.sauvegarder_compteur_general('j1', 5)
        self.etat.sauvegarder_quota_normal('j1', 5)
        self.valider()
        self.materialiser()
        chemin = self.recompense()
        self.assertEqual(chemin.name, 'general6')
        self.assertEqual(self.etat.initialiser_quota_normal('j1'), 5)
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general6'], 'village')
        blocs = self.generaux.lire_blocs_general(chemin)
        self.assertEqual([blocs[b]['nombre'] for b in self.config.ordre_blocs], [20, 0, 0, 0])
        self.assertEqual({p.name for p in (chemin / 'avant').iterdir()},
                         {f'cavalerie_L{i}' for i in range(1, 21)})
        for p in (chemin / 'avant').iterdir():
            self.assertEqual({e.name for e in p.iterdir()},
                             {'cheval', 'armure', 'cuirasse', 'bouclier', 'casque'})
            self.assertTrue(all(e.is_file() for e in p.iterdir()))
        self.assertFalse(list(chemin.glob('*/cavalerie_lourde*')))
        self.assertEqual(blocs['avant']['type'], 'cavalerie_lourde')
        self.assertTrue(all(self.generaux.identifier_unite(p) == 'cavalerie_lourde'
                            for p in (chemin / 'avant').iterdir()))
        fiche = self.generaux.lire_fiche_general(chemin)
        self.assertEqual(self.rapports.nom_affichage_general(
            {'joueur': 'j1', 'nom': chemin.name, 'fiche': fiche}), 'cavalier_noir')
        self.assertEqual(self.rapports.formater_force(blocs['avant']), '20 cavaliers lourds')
        self.assertEqual(fiche['force'], '0')

    def test_crypte_occupee_differe_sans_perdre_ni_dupliquer_defi(self):
        c = self.survie.crypte
        d = c.charger(self.profil)
        d['j1']['a_creer'] = {'id': 'recette-test', 'tour': 1, 'recette': 'recette1'}
        c.sauver(self.profil, d)
        self.valider()
        c.materialiser(self.profil, 1)
        ancienne = self.config.game_path / 'village/j1/crypte/recompense/general1'
        self.materialiser()
        self.assertFalse(self.defi()['recompense_recue'])
        self.assertEqual(self.etat.lire_compteur_general('j1'), 1)
        self.securite.memoriser_unites_actions(self.profil, 1)
        ancienne.rename(self.config.game_path / 'village/j1/reserve/general1')
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.materialiser()
        self.assertEqual(self.defi()['general'], 'general2')
        self.assertEqual(self.etat.initialiser_quota_normal('j1'), 0)
        self.assertEqual(len(c.charger(self.profil)['j1']['attributions']), 2)

    def test_messages_ordinaires_intacts_et_scanner_limite_a_actions(self):
        self.envoyer('Bonjour, demande de renforts.\n')
        avant = self.photo()
        self.scanner()
        self.assertEqual(self.photo(), avant)
        self.envoyer()
        self.etat.sauvegarder_cycle_survie({'tour': 1, 'phase': 'consultation', 'echeance': 100}, self.profil)
        avant = self.photo()
        self.scanner()
        self.assertEqual(self.photo(), avant)
        self.activer(1)
        self.defis.scanner(self.profil, lambda: 101)
        self.assertFalse(self.defi()['termine'])

    def test_scanner_periodique_dix_secondes_sans_thread_ni_attente_reelle(self):
        temps = [0.0]
        g = self.cycle_linux.Generations(self.profil, GelSimule(), horloge=lambda: temps[0],
                                      dormir=lambda n: temps.__setitem__(0, temps[0] + n))
        g.preparer()
        with patch.object(self.defis, 'scanner') as scan:
            g.attendre({'tour': 1, 'phase': 'actions', 'echeance': 25})
        self.assertEqual(scan.call_count, 3)
        self.assertEqual(temps[0], 25)
        with patch.object(self.defis, 'scanner') as scan:
            g.attendre({'tour': 1, 'phase': 'consultation', 'echeance': 40})
        scan.assert_not_called()

    def test_reponse_interrompue_reprise_sans_seconde_validation(self):
        self.envoyer()
        with patch.object(self.defis, 'repondre', side_effect=OSError('panne réponse')):
            with self.assertRaisesRegex(OSError, 'panne réponse'):
                self.scanner()
        self.assertTrue(self.defi()['termine'])
        self.assertIsNotNone(self.donnees()['joueurs']['j1']['courrier']['a_repondre'])
        self.scanner()
        self.assertEqual(self.reponse().count('Flag valide.'), 1)
        self.materialiser()
        self.assertEqual(self.etat.lire_compteur_general('j1'), 1)

    def test_flag_arrive_en_fin_actions_capture_et_publication_uniques(self):
        self.envoyer()
        self.resoudre()  # dernier relevé sous gel, même sans passage périodique préalable
        self.assertTrue(self.defi()['recompense_recue'])
        self.assertTrue(self.recompense().exists())
        self.assertIn('20 cavaliers lourds', (self.hotel() / 'rapport_exploration.txt').read_text(encoding='utf-8'))
        self.etat.sauvegarder_cycle_survie({'tour': 2, 'phase': 'actions', 'echeance': 100}, self.profil)
        avant = self.photo()
        self.scanner()
        self.assertEqual(self.photo(), avant)
        self.resoudre()
        self.assertEqual(self.etat.lire_compteur_general('j1'), 1)

    def test_republication_sans_rejouer_ni_attribuer_deux_fois(self):
        self.envoyer()
        with patch.object(self.rapports, 'publier_rapports_exploration', side_effect=OSError('panne')):
            with self.assertRaisesRegex(OSError, 'panne'):
                self.resoudre()
        cycle = self.etat.charger_cycle_survie(self.profil)
        admin = importlib.import_module('survie_admin')
        with patch.object(admin.cycle_linux, 'Linux', return_value=GelSimule()), \
                patch.object(self.defis, 'materialiser', side_effect=AssertionError('rejeu')):
            admin.republier(self.profil, cycle['generation'])
        self.assertTrue(self.recompense().exists())
        self.assertEqual(self.etat.lire_compteur_general('j1'), 1)
        self.assertEqual(len(self.survie.crypte.charger(self.profil)['j1']['attributions']), 1)

    def test_construction_lourde_interdite_home_reserve_front_et_repli(self):
        for n, territoire, reserve in ((1, 'home', False), (2, 'village', True),
                                      (3, 'est_1', False), (4, 'repli', False)):
            chemin = self.general(numero=n, territoire=territoire, reserve=reserve, nombre=2)
            faux = chemin / 'avant/cavalerie_L1'
            faux.mkdir()
            for nom in ('cheval', 'armure', 'cuirasse', 'bouclier', 'casque'):
                (faux / nom).touch()
            self.securite.verifier_tous_les_deplacements(self.profil)
            self.assertFalse(faux.exists())
            self.assertEqual(self.generaux.total_general_depuis_chemin(chemin), 2)

    def test_copie_lourde_refusee_ancienne_renommee_preservee(self):
        self.valider()
        self.resoudre()
        chemin = self.recompense()
        original = chemin / 'avant/cavalerie_L1'
        original.rename(chemin / 'gauche/cavalerie_L77')
        copie = chemin / 'avant/cavalerie_L99'
        shutil.copytree(chemin / 'avant/cavalerie_L2', copie)
        # Aller au home ne débloque aucune recette d'entraînement lourde.
        home = self.racine / 'home/j1' / chemin.name
        chemin.rename(home)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertFalse((home / 'avant/cavalerie_L99').exists())
        self.assertTrue((home / 'gauche/cavalerie_L77').exists())
        self.assertEqual(self.generaux.total_general_depuis_chemin(home), 20)

    def test_reconnaissance_lourde_exige_les_cinq_fichiers(self):
        unite = self.racine / 'cavalerie_L1'
        unite.mkdir()
        equipements = ('cheval', 'armure', 'cuirasse', 'bouclier', 'casque')
        for nom in equipements:
            (unite / nom).touch()
        self.assertEqual(self.generaux.identifier_unite(unite), 'cavalerie_lourde')
        for nom in equipements:
            with self.subTest(equipement=nom):
                fichier = unite / nom
                fichier.unlink()
                self.assertEqual(self.generaux.identifier_unite(unite), 'inconnu')
                fichier.mkdir()  # Un dossier ne remplace pas un équipement fichier.
                self.assertEqual(self.generaux.identifier_unite(unite), 'inconnu')
                fichier.rmdir()
                fichier.touch()
                self.assertEqual(self.generaux.identifier_unite(unite), 'cavalerie_lourde')

    def test_ancien_format_invalide_et_cavalier_ordinaire_inchange(self):
        ancienne = self.racine / 'cavalerie_lourde1'
        ancienne.mkdir()
        (ancienne / 'armure').touch()
        self.assertEqual(self.generaux.identifier_unite(ancienne), 'inconnu')
        ordinaire = self.racine / 'cavalerie1'
        ordinaire.mkdir()
        for nom in ('cheval', 'armure', 'cuirasse', 'bouclier', 'casque'):
            (ordinaire / nom).touch()
        self.assertEqual(self.generaux.identifier_unite(ordinaire), 'cavalier')

    def test_audit_suit_chacun_des_cinq_equipements_lourds(self):
        self.valider()
        self.resoudre()
        chemin = self.recompense()
        for numero, nom in enumerate(('cheval', 'armure', 'cuirasse', 'bouclier', 'casque'), 1):
            unite = chemin / 'avant' / f'cavalerie_L{numero}'
            # Conserver l'ancien inode ailleurs empêche sa réutilisation par le FS.
            (unite / nom).rename(self.racine / f'ancien_{nom}')
            (unite / nom).touch()
            self.securite.verifier_tous_les_deplacements(self.profil)
            self.assertFalse(unite.exists(), nom)
        self.assertEqual(self.generaux.total_general_depuis_chemin(chemin), 15)

    def test_bonus_formation_et_avantages_sans_statistique_permanente(self):
        c = self.combats
        for adversaire in ('archer', 'cavalier'):
            self.assertEqual(c.multiplicateur('cavalerie_lourde', adversaire), 2)
            self.assertEqual(c.multiplicateur(adversaire, 'cavalerie_lourde'), 1)
        self.assertEqual(c.multiplicateur('piquier', 'cavalerie_lourde'), 2)
        self.assertEqual(c.multiplicateur('cavalerie_lourde', 'piquier'), 1)
        for nombre in (1, 14, 15, 20):
            infos = {'type': 'cavalerie_lourde', 'nombre': nombre}
            self.assertEqual(c.valeur_base_bloc(infos, 'avant'), 10 if nombre >= 15 else 5)
            for bloc in ('droite', 'gauche', 'arriere', None):
                self.assertEqual(c.valeur_base_bloc(infos, bloc), 5)
        lourd = {'type': 'cavalerie_lourde', 'nombre': 15}
        archer = {'type': 'archer', 'nombre': 20}
        self.assertEqual(c.valeur_base_bloc(lourd, 'avant') * c.multiplicateur(lourd['type'], archer['type']), 20)
        self.assertEqual(c.combat_bloc(lourd, archer, bloc_1='avant', bloc_2='avant'), (10, 0))
        self.assertEqual(c.combat_bloc(lourd, archer, bloc_1='gauche', bloc_2='avant'), (5, 0))
        lourd['nombre'] = 14
        self.assertEqual(c.combat_bloc(lourd, archer, bloc_1='avant', bloc_2='avant'), (4, 0))
        self.assertEqual(set(lourd), {'type', 'nombre'})

    def test_choc_et_manoeuvre_transmettent_les_blocs_reels(self):
        self.valider()
        self.materialiser()
        chemin = self.recompense()
        adverse = self.general('bot', territoire='est_1', nombre=20)
        g1 = {'joueur': 'j1', 'nom': chemin.name, 'chemin': chemin,
              'fiche': self.generaux.lire_fiche_general(chemin)}
        g2 = {'joueur': 'bot', 'nom': adverse.name, 'chemin': adverse,
              'fiche': self.generaux.lire_fiche_general(adverse)}
        armee = {'j1': self.generaux.lire_blocs_general(chemin),
                 'bot': self.generaux.lire_blocs_general(adverse)}
        original = self.combats.combat_bloc
        def simuler_pertes(infos, survivants, general=None, *, participants=None):
            # Les effectifs après pertes incluent désormais les sauvetages.
            # Simuler leur actualisation sans modifier les dossiers de ce test.
            infos['nombre'] = survivants
            infos['unites'] = infos['unites'][:survivants]
            return []
        with patch.object(self.combats, 'supprimer_unites', side_effect=simuler_pertes), \
                patch.object(self.combats, 'combat_bloc', wraps=original) as calcul:
            choc = self.combats.confrontation_directe(armee, g1, g2, 'avant')
            armee = {'j1': self.generaux.lire_blocs_general(chemin),
                     'bot': self.generaux.lire_blocs_general(adverse)}
            manoeuvre = self.combats.attaque_ciblee(armee, g1, g2, 'avant', 'avant')
        self.assertEqual(choc['final_1'], 15)
        self.assertEqual(manoeuvre['final_attaquant'], 15)
        self.assertEqual([a.args[-2:] for a in calcul.call_args_list], [('avant', 'avant')] * 2)

    def test_ciblage_avantageux_garde_ordre_des_blocs(self):
        armee = {'j1': {}, 'bot': {b: {'type': 'vide', 'nombre': 0} for b in self.config.ordre_blocs}}
        armee['bot']['droite'] = {'type': 'cavalier', 'nombre': 2}
        armee['bot']['gauche'] = {'type': 'archer', 'nombre': 2}
        self.assertEqual(self.combats.trouver_cible_facile(armee, 'j1', 'cavalerie_lourde'), 'droite')


if __name__ == '__main__':
    unittest.main()
