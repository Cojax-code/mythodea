"""Sélections territoriales et progression zombie, sur plateaux temporaires."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import test_stabilisation_finale as support
import commandement
import cycle_linux
import progression


class SelectionEtProgression(unittest.TestCase):
    fiche = support.ProgressionFinale.fiche

    def setUp(self):
        temporaire = tempfile.TemporaryDirectory(prefix='mythodea-selection-')
        self.addCleanup(temporaire.cleanup)
        self.chemin = Path(temporaire.name)
        self.selection = self.chemin / 'etiquettes_actives.txt'

    def test_syntaxe_absence_vide_et_connaissances_inchangees(self):
        fiche = self.fiche(etiquettes={'infanterie': 1, 'distance': 2, 'cruelle': 1})
        avant = deepcopy(fiche)
        self.assertEqual(progression.selection_etiquettes(fiche, self.chemin)['etiquettes_actives'],
                         list(fiche['etiquettes']))
        for contenu, attendu in (('', []), (' \n', []), ('distance\ninfanterie', ['distance', 'infanterie']),
                                 ('distance, infanterie\ncruelle', ['distance', 'infanterie', 'cruelle'])):
            with self.subTest(contenu=contenu):
                self.selection.write_text(contenu, encoding='utf-8')
                resultat = progression.selection_etiquettes(fiche, self.chemin)
                self.assertEqual(resultat['etiquettes_actives'], attendu)
                self.assertEqual(resultat['etiquettes'], fiche['etiquettes'])
        self.assertEqual(fiche, avant)

    def test_noms_exacts_doublons_et_non_apprises_refuses(self):
        fiche = self.fiche(etiquettes={'infanterie': 1})
        for texte in ('Infanterie', 'inconnue', 'distance', 'infanterie,infanterie', 'infanterie\ninfanterie'):
            with self.subTest(texte=texte):
                self.selection.write_text(texte, encoding='utf-8')
                with self.assertRaises(ValueError):
                    progression.selection_etiquettes(fiche, self.chemin)

    def test_limites_et_orientation_principale_des_hybrides(self):
        for nature in progression.NATURES:
            maximum = 3 if nature.startswith('stratege') else 1
            fiche = self.fiche(nature, etiquettes={'infanterie': 1, 'distance': 1, 'cruelle': 1, 'chaman': 1})
            for nombre in (maximum, maximum + 1):
                with self.subTest(nature=nature, nombre=nombre):
                    noms = list(fiche['etiquettes'])[:nombre]
                    self.selection.write_text(','.join(noms), encoding='utf-8')
                    if nombre > maximum:
                        with self.assertRaises(ValueError):
                            progression.selection_etiquettes(fiche, self.chemin)
                    else:
                        self.assertEqual(progression.selection_etiquettes(fiche, self.chemin)['etiquettes_actives'], noms)

    def test_aucun_bonus_ni_malus_non_selectionne(self):
        fiche = self.fiche(etiquettes={'infanterie': 2, 'chaman': 1, 'cruelle': 1})
        self.selection.write_text('infanterie', encoding='utf-8')
        choix = progression.selection_etiquettes(fiche, self.chemin)
        self.assertEqual(commandement.effets_etiquettes_general(choix, {'infanterie', 'orc'}),
                         {('valeur', 'infanterie'): 15})
        self.selection.write_text('', encoding='utf-8')
        self.assertEqual(commandement.effets_etiquettes_general(
            progression.selection_etiquettes(fiche, self.chemin), {'infanterie', 'orc'}), {})

    def test_liens_et_objets_non_ordinaires_refuses_en_lecture_et_capture(self):
        fiche = self.fiche(etiquettes={'infanterie': 1})
        cible = self.chemin / 'source'
        cible.write_text('infanterie', encoding='utf-8')
        for genre in ('symbolique', 'physique', 'dossier', 'fifo'):
            if genre == 'fifo' and not hasattr(os, 'mkfifo'):
                continue
            with self.subTest(genre=genre):
                if genre == 'symbolique':
                    self.selection.symlink_to(cible)
                elif genre == 'physique':
                    os.link(cible, self.selection)
                elif genre == 'dossier':
                    self.selection.mkdir()
                else:
                    os.mkfifo(self.selection)
                try:
                    with self.assertRaises(ValueError):
                        progression.selection_etiquettes(fiche, self.chemin)
                    with self.assertRaises(RuntimeError):
                        cycle_linux.copier(self.selection, self.chemin / 'copie')
                    self.assertFalse((self.chemin / 'copie').exists())
                    self.assertEqual(cible.read_text(encoding='utf-8'), 'infanterie')
                finally:
                    if genre == 'dossier':
                        self.selection.rmdir()
                    else:
                        self.selection.unlink()

    def test_lien_parent_et_lien_casse_refuses(self):
        fiche = self.fiche(etiquettes={'infanterie': 1})
        self.selection.symlink_to(self.chemin / 'absent')
        with self.assertRaises(ValueError):
            progression.selection_etiquettes(fiche, self.chemin)
        self.selection.unlink()
        vrai = self.chemin / 'vrai'
        vrai.mkdir()
        (vrai / self.selection.name).write_text('infanterie', encoding='utf-8')
        lie = self.chemin / 'lie'
        lie.symlink_to(vrai, target_is_directory=True)
        with self.assertRaises(ValueError):
            progression.selection_etiquettes(fiche, lie)

    def test_zombie_exactement_vingt_tirages_sur_cent_sans_recompense_ordinaire(self):
        for nature in progression.NATURES:
            fiche = self.fiche(nature, niveau=4, etat_zombie=True, niveaux_zombie=0,
                               etiquettes={'infanterie': 2}, evolution_apprise=105)
            avant = deepcopy(fiche)
            succes = 0
            for tirage in range(1, 101):
                aleatoire = Mock()
                aleatoire.randint.return_value = tirage
                apres, recompense = progression.monter_niveau(fiche, aleatoire)
                aleatoire.randint.assert_called_once_with(1, 100)
                succes += 'mort_vivant' in apres['etiquettes']
                self.assertEqual(progression.capacite_maximale(apres), 22)
                self.assertEqual(apres['niveau'], 5)
                for champ in ('points_commandement', 'moral', 'evolutions_acquises',
                              'evolution_apprise', 'etiquettes_permanentes'):
                    self.assertEqual(apres[champ], fiche[champ])
                self.assertEqual(apres['etiquettes']['infanterie'], 2)
                self.assertEqual(recompense, ('etiquette_zombie', 'mort_vivant') if tirage <= 20 else None)
                if tirage <= 20:
                    self.assertEqual(apres['etiquettes']['mort_vivant'], 1)
            self.assertEqual(succes, 20)
            self.assertEqual(fiche, avant)

    @unittest.skipUnless(os.name == 'posix', 'Ouverture Linux sans suivi de lien requise')
    def test_remplacement_entre_controle_et_ouverture_refuse(self):
        fiche = self.fiche(etiquettes={'infanterie': 1})
        cible = self.chemin / 'autre'
        cible.write_text('infanterie', encoding='utf-8')
        ouvrir = os.open
        for genre in ('symbolique', 'physique', 'fifo', 'ordinaire'):
            with self.subTest(genre=genre):
                self.selection.write_text('infanterie', encoding='utf-8')

                def remplacer(chemin, flags):
                    self.selection.unlink()
                    if genre == 'symbolique':
                        self.selection.symlink_to(cible)
                    elif genre == 'physique':
                        os.link(cible, self.selection)
                    elif genre == 'fifo':
                        os.mkfifo(self.selection)
                    else:
                        cible.rename(self.selection)
                    return ouvrir(chemin, flags)

                try:
                    with patch.object(os, 'open', side_effect=remplacer):
                        with self.assertRaises((ValueError, OSError)):
                            progression.selection_etiquettes(fiche, self.chemin)
                finally:
                    self.selection.unlink()

    def test_zombie_acquis_aucun_nouveau_tirage_ni_remplacement(self):
        fiche = self.fiche(etat_zombie=True, niveaux_zombie=2,
                           etiquettes={'infanterie': 2, 'mort_vivant': 3})
        aleatoire = Mock()
        aleatoire.randint.side_effect = AssertionError('Tirage après acquisition interdit')
        for _ in range(3):
            fiche, recompense = progression.monter_niveau(fiche, aleatoire)
            self.assertIsNone(recompense)
            self.assertEqual(fiche['etiquettes'], {'infanterie': 2, 'mort_vivant': 3})
        self.assertEqual(progression.capacite_maximale(fiche), 30)

    def test_emplacement_zombie_supplementaire_selectionnable(self):
        for nature in progression.NATURES:
            noms = ['infanterie', 'distance', 'cruelle'] if nature.startswith('stratege') else ['infanterie']
            fiche = self.fiche(nature, etat_zombie=True, etiquettes=dict.fromkeys([*noms, 'mort_vivant'], 1))
            for choix in (noms, [*noms, 'mort_vivant'], ['mort_vivant'], []):
                self.selection.write_text(','.join(choix), encoding='utf-8')
                self.assertEqual(progression.selection_etiquettes(fiche, self.chemin)['etiquettes_actives'], choix)


class BataillesEtSelections(unittest.TestCase):
    setUp = support.IntegrationFinale.setUp
    activer = support.IntegrationFinale.activer
    general = support.IntegrationFinale.general
    creer = support.IntegrationFinale.creer
    infos = support.IntegrationFinale.infos
    modules = support.IntegrationFinale.modules
    speciale = support.IntegrationFinale.speciale
    combattant = support.IntegrationFinale.combattant
    contexte = support.IntegrationFinale.contexte

    def choisir(self, general, texte):
        (general['chemin'] / 'etiquettes_actives.txt').write_text(texte, encoding='utf-8')

    def actives(self, general):
        return self.progression.caracteristiques_general(general)['etiquettes_actives']

    def test_selection_figee_reinitialisee_et_nettoyee_apres_exception(self):
        g = self.combattant(etiquettes={'infanterie': 1, 'distance': 1})
        self.choisir(g, 'infanterie')
        with self.assertRaisesRegex(RuntimeError, 'incident'), self.contexte():
            self.choisir(g, 'distance')
            with self.contexte():
                self.assertEqual(self.actives(g), ['infanterie'])
            raise RuntimeError('incident')
        self.assertIsNone(self.progression._SELECTIONS_TERRITORIALES.get())
        with self.contexte():
            self.assertEqual(self.actives(g), ['distance'])
            self.choisir(g, 'non_apprise')
            self.assertEqual(self.actives(g), ['distance'])
        with self.assertRaises(ValueError), self.contexte():
            pass
        self.assertIsNone(self.progression._SELECTIONS_TERRITORIALES.get())

    def test_fiche_publique_ne_permet_pas_apprentissage(self):
        g = self.combattant(etiquettes={'infanterie': 1})
        with (g['chemin'] / 'fiche.txt').open('a', encoding='utf-8') as fiche:
            fiche.write("\netiquettes={'distance': 99}\npoints_commandement=99999\n")
        self.choisir(g, 'distance')
        with self.assertRaises(ValueError):
            self.actives(g)
        self.choisir(g, 'infanterie')
        fiche = self.progression.caracteristiques_general(g)
        self.assertEqual(fiche['etiquettes'], {'infanterie': 1})
        self.assertEqual(fiche['points_commandement'], 20)

    def test_capacite_privee_ne_lit_ni_ne_fige_selection(self):
        g = self.combattant(nombre=22)
        profils = self.progression.charger()
        profils['j1:general1'].update(etat_zombie=True, niveaux_zombie=1)
        self.progression.sauvegarder(profils)
        self.choisir(g, 'non_apprise')
        self.generaux.verifier_limite_unites_general(g['chemin'])
        self.assertEqual(self.generaux.total_general_depuis_chemin(g['chemin']), 22)
        # Le même contrôle territorial retrouve la capacité normale sans zombie.
        profils['j1:general1']['etat_zombie'] = False
        self.progression.sauvegarder(profils)
        self.generaux.verifier_limite_unites_general(g['chemin'])
        self.assertEqual(self.generaux.total_general_depuis_chemin(g['chemin']), 20)

    def test_renfort_premier_engagement_pas_inventaire(self):
        qg = self.combattant(etiquettes={'infanterie': 1})
        (qg['chemin'] / 'QG.txt').touch()
        renfort = self.combattant('j2', place='5', pc=900, etiquettes={'distance': 1, 'infanterie': 1})
        self.choisir(renfort, 'distance')
        with self.contexte():
            self.generaux.verifier_limite_unites_general(renfort['chemin'])
            self.assertNotIn(('j2', 'general1'), self.progression._SELECTIONS_TERRITORIALES.get())
            self.choisir(renfort, 'infanterie')
            destination = self.config.game_path / 'est_3/j2/2/general1'
            destination.parent.mkdir(parents=True, exist_ok=True)
            renfort['chemin'].rename(destination)
            renfort['chemin'] = destination
            with self.contexte():
                self.assertEqual(self.actives(renfort), ['infanterie'])
                self.choisir(renfort, 'distance')
                self.assertEqual(self.actives(renfort), ['infanterie'])
                self.assertEqual(self.combats._effets_transmis(renfort)[('valeur', 'infanterie')], 10)

    def test_qg_transmet_seulement_selection_initiale_et_messager_initial(self):
        qg = self.combattant(etiquettes={'infanterie': 1, 'chaman': 1, 'cruelle': 1})
        allie = self.combattant('j2', place='2', pc=100)
        ennemi = self.combattant('bot')
        self.speciale(allie, 'messager_du_QG')
        (qg['chemin'] / 'QG.txt').touch()
        self.choisir(qg, 'infanterie')
        with self.contexte():
            self.choisir(qg, 'cruelle,chaman')
            with self.contexte():
                self.assertEqual(self.combats._effets_transmis(allie), {('valeur', 'infanterie'): 15})
                self.assertEqual(self.combats._effets_transmis(qg), {})
                self.assertEqual(self.combats._effets_transmis(ennemi, ennemi=True), {})
                self.assertEqual(self.combats._bonus_valeur_duel(
                    self.progression.caracteristiques_general(qg), 'archer', 0, qg), 10)
        with self.contexte():
            self.assertEqual(self.combats._effets_transmis(ennemi, ennemi=True),
                             {('malus_moral_adverse', None): 15, ('malus_valeur_adverse', 'orc'): 15})

    def test_home_reserve_batiment_et_renfort_exclus_de_instantane(self):
        qg = self.combattant(etiquettes={'infanterie': 1})
        (qg['chemin'] / 'QG.txt').touch()
        self.speciale(qg, 'messager_du_QG')
        for numero, position in enumerate((dict(territoire='home'), dict(territoire='village', reserve=True),
                                          dict(territoire='village', place='ecole_officiers/1'),
                                          dict(territoire='est_3', place='5')), 2):
            chemin = self.general(numero=numero, **position)
            profils = self.progression.charger()
            profils[f'j1:general{numero}'].update(points_commandement=1000)
            self.progression.sauvegarder(profils)
            (chemin / 'QG.txt').touch()
            (chemin / 'etiquettes_actives.txt').write_text('invalide', encoding='utf-8')
        with self.contexte():
            instantane = self.combats._EFFETS_TERRITOIRE.get()['instantanes']['allies']
            self.assertEqual((instantane['pc_global'], instantane['bonus_messager']), (20, 0))
            self.assertEqual(set(self.progression._SELECTIONS_TERRITORIALES.get()), {('j1', 'general1')})

    def test_cascade_reelle_selection_stable_entre_duels_et_phases(self):
        allie = self.combattant(nombre=20, ordre=2, etiquettes={'infanterie': 1, 'distance': 1})
        self.choisir(allie, 'infanterie')
        for numero in range(1, 6):
            self.combattant('bot', numero=numero, nombre=1, equipement='pique')
        calcul = self.combats.combat_bloc
        observations = []

        def observer(*args, **kwargs):
            observations.append(self.actives(allie))
            self.choisir(allie, 'distance')
            return calcul(*args, **kwargs)

        with patch.object(self.combats, 'combat_bloc', side_effect=observer):
            resultat = self.survie.resoudre_cascade(self.config.game_path / 'est_3', self.profil)
        self.assertEqual(resultat['affrontements'], 2)
        self.assertGreaterEqual(len(observations), 5)
        self.assertTrue(all(choix == ['infanterie'] for choix in observations))
        self.assertEqual(self.actives(allie), ['distance'])

    def test_zombie_persistance_et_rejeu_evenement(self):
        g = self.combattant(etiquettes={'infanterie': 2})
        profils = self.progression.charger()
        profils['j1:general1'].update(etat_zombie=True, niveaux_zombie=0, progression_combat=1)
        self.progression.sauvegarder(profils)
        aleatoire = Mock()
        aleatoire.randint.return_value = 20
        self.assertTrue(self.progression.valider_evenement(g, 'combat', 'territoire-1', aleatoire))
        aleatoire.randint.assert_called_once_with(1, 100)
        rechargee = self.progression.charger()['j1:general1']
        self.assertEqual(rechargee['etiquettes'], {'infanterie': 2, 'mort_vivant': 1})
        self.assertEqual(self.progression.capacite_maximale(rechargee), 22)
        self.assertFalse(self.progression.valider_evenement(g, 'combat', 'territoire-1', aleatoire))
        self.assertEqual(self.progression.charger()['j1:general1'], rechargee)
        self.progression.attribuer_niveau(g, aleatoire)
        aleatoire.randint.assert_called_once_with(1, 100)
        self.assertEqual(self.progression.capacite_maximale_general(g), 24)
        self.assertEqual(set(self.actives(g)), {'infanterie', 'mort_vivant'})

    def verifier_phases(self, mode):
        allie = self.combattant(nombre=20, etiquettes={'infanterie': 1, 'distance': 1})
        for unite in list((allie['chemin'] / 'avant').iterdir()):
            unite.rename(allie['chemin'] / 'arriere' / unite.name)
        for numero in (1, 2):
            self.combattant('bot', numero=numero, nombre=1, equipement='pique')
        self.choisir(allie, 'infanterie')
        # Exercer l'entrée frontale déjà existante, sans nouvelle configuration de jeu.
        profil = dict(self.profil, configurations_terrain={'est_3': {'attaque_frontale': True}})
        calcul = self.combats.combat_bloc
        choix = []

        def observer(*args, **kwargs):
            self.choisir(allie, 'distance')
            choix.append(self.actives(allie))
            return calcul(*args, **kwargs)

        with patch.object(self.combats, 'combat_bloc', side_effect=observer), \
                patch.object(self.combats, 'attaque_ciblee', wraps=self.combats.attaque_ciblee) as manoeuvre, \
                patch.object(self.combats, 'combat_entre_generaux', wraps=self.combats.combat_entre_generaux) as duels:
            self.combats.resoudre_combat_range(self.config.game_path / 'est_3', mode, profil)
        self.assertGreater(manoeuvre.call_count, 0)
        self.assertEqual(duels.call_count, 2)  # Un duel frontal, puis un duel rangé.
        self.assertTrue(choix)
        self.assertTrue(all(selection == ['infanterie'] for selection in choix))
        self.assertEqual(self.actives(allie), ['distance'])

    def test_selection_choc_manoeuvre_frontal_et_range_off_off(self):
        self.verifier_phases('OFF/OFF')

    def test_selection_choc_manoeuvre_frontal_et_range_off_def(self):
        self.verifier_phases('OFF/DEF')
