"""Contrat de la refonte V2 : profils privés et plateaux exclusivement temporaires."""
from copy import deepcopy
from fractions import Fraction
import importlib
import os
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import Mock, patch

import test_unites_v2
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
import progression
import commandement
import catalogues


class ProgressionFinale(unittest.TestCase):
    def fiche(self, nature='stratege', **champs):
        return dict(dict(nature=nature, niveau=0, points_commandement=15, moral=0,
                         trait_inne='charismatique', evolutions_acquises=[],
                         evolution_apprise=None, etiquettes={}, etiquettes_permanentes=[]), **champs)

    def test_hybrides_gain_selon_statistique_apprise(self):
        for nature, evolution, recompense, pc, moral in (
                ('stratege_hybride', 202, ('force_caractere', 4), 19, 4),
                ('instinctif_hybride', 201, ('maitrise_commandement', 10), 25, 1)):
            fiche = self.fiche(nature, niveau=1, evolution_apprise=evolution)
            avant = deepcopy(fiche)
            apres, obtenu = progression.monter_niveau(fiche, Mock(randint=lambda a, b: b))
            self.assertEqual((obtenu, apres['points_commandement'], apres['moral']),
                             (recompense, pc, moral))
            self.assertIsNone(apres['evolution_apprise'])
            self.assertEqual(fiche, avant)

    def test_paliers_et_memoire_unite_conservee(self):
        for nature in progression.NATURES:
            fiche = self.fiche(nature, niveau=4, evolution_apprise=105)
            apres, recompense = progression.monter_niveau(fiche, random.Random(1))
            self.assertEqual(recompense[0], 'etiquette_permanente')
            self.assertEqual(apres['evolution_apprise'], 105)
            apres, recompense = progression.monter_niveau(apres, random.Random(2))
            self.assertEqual(recompense, 105)
            self.assertIsNone(apres['evolution_apprise'])
            self.assertNotIn(105, progression.evolutions_eligibles(apres))

    def test_natures_paliers_plafonds_et_roulette_apres_n10(self):
        for nature in progression.NATURES:
            stratege = nature.startswith('stratege')
            fiche = self.fiche(nature, etiquettes={'infanterie': 1} if stratege else {},
                               etiquettes_permanentes=['infanterie'] if stratege else [])
            for niveau in range(1, 21):
                precedent = fiche
                fiche, recompense = progression.monter_niveau(fiche, random.Random(niveau))
                palier = niveau in ((5, 10) if stratege else (5,))
                self.assertEqual(isinstance(recompense, tuple) and recompense[0] == 'etiquette_permanente', palier)
                self.assertLessEqual(len(fiche['etiquettes']), 3 if stratege else 1)
                self.assertLessEqual(fiche['moral'], 100)
                if stratege:
                    self.assertGreaterEqual(fiche['points_commandement'] - precedent['points_commandement'], 2)

    def test_pc_dernier_recours_repetable_sans_unite_en_double(self):
        fiche = self.fiche('instinctif', moral=100)
        fiche['evolutions_acquises'] = [i for i, e in progression.evolutions_eligibles(fiche).items()
                                      if e['categorie'] == 'unite']
        for _ in range(3):
            fiche, recompense = progression.monter_niveau(fiche, Mock(randint=lambda a, b: a))
            self.assertEqual(recompense, ('maitrise_commandement', 5))
        self.assertEqual(fiche['points_commandement'], 30)
        self.assertEqual(len(set(fiche['evolutions_acquises'])), len(fiche['evolutions_acquises']))

    def test_ecole_permanentes_limites_et_instinctif_avant_n5(self):
        f = self.fiche(etiquettes={'infanterie': 1}, etiquettes_permanentes=['infanterie'])
        with self.assertRaises(ValueError):
            progression.apprendre_etiquette(f, 'infanterie')
        f = progression.apprendre_etiquette(f, 'distance')
        with self.assertRaises(ValueError):
            progression.apprendre_etiquette(f, 'distance')
        f['niveau'] = 5
        f = progression.apprendre_etiquette(f, 'distance')
        self.assertEqual(f['etiquettes']['distance'], 2)
        f = progression.apprendre_etiquette(f, 'cavalerie')
        with self.assertRaises(ValueError):
            progression.apprendre_etiquette(f, 'orc')
        with self.assertRaises(ValueError):
            progression.apprendre_etiquette(self.fiche('instinctif'), 'orc')

    def test_coefficient_fixe_fraction_et_cibles(self):
        for niveau in (0, 5, 10, 15, 100):
            self.assertEqual(commandement.coefficient_niveau_general(niveau), Fraction(1, 2))
            f = self.fiche(niveau=niveau, etiquettes={'infanterie': 1, 'distance': 2, 'cruelle': 1})
            effets = commandement.effets_etiquettes_general(f, {'infanterie', 'distance'})
            self.assertEqual(effets[('valeur', 'infanterie')], Fraction(15, 2))
            self.assertEqual(effets[('valeur', 'distance')], 15)
            self.assertEqual(effets[('malus_moral_adverse', None)], Fraction(15, 2))
            self.assertNotIn(('valeur', 'distance'), commandement.effets_etiquettes_general(f, {'orc'}))

    def test_ids_ecole_stables(self):
        self.assertEqual(catalogues.ETIQUETTES_ECOLE, {
            2001: 'infanterie', 2002: 'distance', 2003: 'cavalerie', 2004: 'humain',
            2005: 'melee', 2006: 'orc', 2007: 'mort_vivant', 2008: 'noble',
            2009: 'armure_legere', 2010: 'lourde', 2011: 'chaman', 2012: 'cruelle'})


class IntegrationFinale(unittest.TestCase):
    setUp = test_unites_v2.UnitesV2.setUp
    activer = test_unites_v2.UnitesV2.activer
    general = test_unites_v2.UnitesV2.general
    creer = test_unites_v2.UnitesV2.creer
    infos = test_unites_v2.UnitesV2.infos
    modules = test_unites_v2.UnitesV2.modules
    speciale = test_unites_v2.UnitesV2.speciale

    def combattant(self, joueur='j1', numero=1, place='1', pc=20, etiquettes=None, **options):
        chemin = self.general(joueur, numero=numero, place=place, territoire='est_3', **options)
        g = dict(joueur=joueur, nom=chemin.name, chemin=chemin,
                 camp=self.profil['acteurs'][joueur]['camp'])
        profils = self.progression.charger()
        profils[f'{joueur}:{chemin.name}'] = ProgressionFinale().fiche(
            points_commandement=pc, etiquettes=etiquettes or {})
        self.progression.sauvegarder(profils)
        return g

    def contexte(self):
        return self.combats._contexte_qg_territorial(self.config.game_path / 'est_3', self.profil)

    def test_moral_sans_cruelle_reste_exact(self):
        g = self.creer(nombre=2)
        self.assertEqual(self.combats.supprimer_unites(self.infos(g), 0, g), [])

    def test_qg_absent_unique_double_et_deux_graphies(self):
        a = self.combattant(etiquettes={'infanterie': 1})
        b = self.combattant('j2', pc=200, place='2')
        with self.contexte():
            self.assertEqual(self.combats._effets_transmis(b), {})
        for nom in ('QG.txt', 'qg.txt'):
            (a['chemin'] / nom).touch()
        with self.contexte():
            self.assertEqual(self.combats._effets_transmis(a), {})
            self.assertEqual(self.combats._effets_transmis(b)[('valeur', 'infanterie')], 10)
        (b['chemin'] / 'qg.txt').touch()
        with self.contexte():
            self.assertEqual(self.combats._effets_transmis(b), {})
            self.assertEqual(self.combats._effets_transmis(a), {})

    def test_messager_cinq_places_zero_et_bonus_fige(self):
        a = self.combattant(etiquettes={'infanterie': 1}, nombre=10)
        b = self.combattant('j2', place='2', pc=99, nombre=10)
        self.speciale(a, 'messager_du_QG', bloc='arriere')
        self.speciale(b, 'messager_du_QG', bloc='arriere')
        self.assertEqual(self.unites.occupation({'avant': {'messager_du_QG': 2}}), 10)
        (a['chemin'] / 'QG.txt').touch()
        with self.contexte():
            self.assertEqual(self.combats._effets_transmis(b)[('valeur', 'infanterie')], Fraction(29, 2))
            self.assertEqual(self.combats._effets_transmis(a), {})
            profils = self.progression.charger()
            profils['j2:general1']['points_commandement'] = 999
            self.progression.sauvegarder(profils)
            with self.contexte():
                self.assertEqual(self.combats._effets_transmis(b)[('valeur', 'infanterie')], Fraction(29, 2))

    def test_manoeuvre_inverse_garde_soutien_du_bon_general(self):
        qg = self.combattant(numero=2, place='2', pc=200, etiquettes={'infanterie': 1})
        a = self.combattant(nombre=10)
        b = self.combattant('bot', nombre=10)
        (qg['chemin'] / 'QG.txt').touch()
        armee = {g['joueur']: self.generaux.lire_blocs_general(g['chemin']) for g in (a, b)}
        with self.contexte(), patch.object(self.combats, 'supprimer_unites', return_value=[]), \
                patch.object(self.unites, 'apres_confrontation'):
            jeton = self.combats._DUEL_IDENTITES.set((a, b))
            try:
                calcul = self.combats.combat_bloc
                with patch.object(self.combats, 'combat_bloc', wraps=calcul) as appel:
                    self.combats.attaque_ciblee(armee, b, a, 'avant', 'avant')
                    # Le soutien double la valeur des seuls alliés : 5 survivants alliés.
                    args, kwargs = appel.call_args
                    self.assertEqual(kwargs.get('general_1'), b)
                    self.assertEqual(kwargs.get('general_2'), a)
            finally:
                self.combats._DUEL_IDENTITES.reset(jeton)
        with self.contexte():
            self.assertEqual(calcul(armee['bot']['avant'], armee['j1']['avant'],
                fiche_1=self.progression.caracteristiques_general(b),
                fiche_2=self.progression.caracteristiques_general(a), general_1=b, general_2=a), (0, 5))

    def test_soutien_aux_anciens_profils_et_chaman_sans_profil_adverse(self):
        qg = self.combattant(numero=2, place='2', pc=100, etiquettes={'infanterie': 1, 'chaman': 1})
        a = self.combattant()
        b = self.combattant('bot')
        profils = self.progression.charger()
        del profils['j1:general1']
        self.progression.sauvegarder(profils)
        (qg['chemin'] / 'QG.txt').touch()
        with self.contexte():
            jeton = self.combats._DUEL_IDENTITES.set((a, b))
            try:
                self.assertEqual(self.combats._bonus_valeur_duel(None, 'archer', 0), 50)
                self.assertEqual(self.combats._malus_chaman_duel(None, 'orc_archer', 1), 50)
            finally:
                self.combats._DUEL_IDENTITES.reset(jeton)

    def test_qg_detruit_pas_de_releve_effets_adverses_conserves(self):
        a = self.combattant(etiquettes={'infanterie': 1, 'cruelle': 1})
        b = self.combattant('j2', place='2')
        ennemi = self.combattant('bot', etiquettes={'cruelle': 1})
        for g in (a, ennemi):
            (g['chemin'] / 'QG.txt').touch()
        with self.contexte():
            self.combats.supprimer_unites(self.infos(a), 0)
            self.generaux.supprimer_general_si_vide(a)
            self.combats._desactiver_qg_detruit(a)
            (b['chemin'] / 'QG.txt').touch()
            with self.contexte():
                self.assertEqual(self.combats._effets_transmis(b), {})
                self.assertEqual(self.combats._effets_transmis(ennemi, ennemi=True), {})
                self.assertEqual(self.combats._effets_transmis(b, ennemi=True)[('malus_moral_adverse', None)], 10)

    def test_liens_qg_refuses_meme_si_autre_graphie_valide(self):
        a = self.combattant()
        (a['chemin'] / 'QG.txt').touch()
        cible = self.racine / 'cible_qg'
        cible.touch()
        for physique in (False, True):
            lien = a['chemin'] / 'qg.txt'
            if physique:
                os.link(cible, lien)
            else:
                lien.symlink_to(cible)
            try:
                with self.assertRaises((ValueError, RuntimeError)), self.contexte():
                    pass
            finally:
                lien.unlink()

    def test_capture_refuse_qg_lie_avant_independance_des_inodes(self):
        cycle = importlib.import_module('cycle_linux')
        source = self.racine / 'QG.txt'
        source.touch()
        os.link(source, self.racine / 'autre')
        with self.assertRaises((ValueError, RuntimeError)):
            cycle.copier(source, self.racine / 'copie_qg')

    def test_ecole_lecture_prioritaire_et_rejeu_unique(self):
        g = self.creer(nature='stratege')
        profils = self.progression.charger()
        profils['j1:general1'].update(etiquettes={}, etiquettes_permanentes=[], niveau=5)
        self.progression.sauvegarder(profils)
        donnees = self.formation.charger()
        donnees['manuels']['allies'] = {'001': 2001, '002': None, '003': None}
        self.formation.sauvegarder(donnees)
        self.formation.commencer_sejour(1, g, 'ecole_officiers', 'allies', [1],
                                        ecrire='invalide', lire='a 001 2001')
        self.assertTrue(self.formation.valider_sejour(1, g, 'ecole_officiers', 'allies', [1], True))
        self.assertFalse(self.formation.valider_sejour(1, g, 'ecole_officiers', 'allies', [1], True))
        self.assertEqual(self.progression.caracteristiques_general(g)['etiquettes'], {'infanterie': 1})
        self.assertEqual(self.formation.charger()['manuels']['allies']['001'], 2001)

    def test_ecole_lecture_prioritaire_meme_si_ecriture_non_utf8(self):
        g = self.creer(nature='stratege', territoire='village', place='ecole_officiers/1')
        donnees = self.formation.charger()
        donnees['manuels']['allies'] = {'001': 105, '002': None, '003': None}
        self.formation.sauvegarder(donnees)
        self.formation.preparer(self.profil)
        (g['chemin'] / 'ecrire_ses_memoires.txt').write_bytes(b'\xff')
        (g['chemin'] / 'lire_les_memoires.txt').write_text('a 001 105')
        self.formation.ouvrir_tour(self.profil, 1)
        self.formation.clore_tour(self.profil, 1)
        self.formation.resoudre_tour(self.profil, 1)
        self.assertEqual(self.progression.caracteristiques_general(g)['evolution_apprise'], 105)

    def test_ecole_fichiers_invalides_sans_gain(self):
        g = self.creer(territoire='village', place='ecole_officiers/1')
        for tour, texte in enumerate((b'\xff', b'a 004 105', b'a 001 inconnu', b'a 001 ' + b'9' * 5000), 1):
            self.formation.preparer(self.profil)
            (g['chemin'] / 'lire_les_memoires.txt').write_bytes(texte)
            avant = self.progression.caracteristiques_general(g)
            self.formation.ouvrir_tour(self.profil, tour)
            self.formation.clore_tour(self.profil, tour)
            self.formation.resoudre_tour(self.profil, tour)
            self.assertEqual(self.progression.caracteristiques_general(g), avant)

    def test_bonus_personnel_et_qg_additionnes(self):
        qg = self.combattant(numero=2, place='2', pc=60, etiquettes={'infanterie': 1})
        allie = self.combattant(pc=20, etiquettes={'infanterie': 1}, nombre=10)
        ennemi = self.combattant('bot', nombre=10)
        (qg['chemin'] / 'QG.txt').touch()
        with self.contexte():
            bonus = self.combats._bonus_valeur_duel(self.progression.caracteristiques_general(allie),
                                                  'archer', 0, allie)
            self.assertEqual(bonus, 40)
            self.assertEqual(20 * (1 + bonus / 100), 28)
            self.assertEqual(self.combats.combat_bloc(self.infos(allie), self.infos(ennemi),
                fiche_1=self.progression.caracteristiques_general(allie), general_1=allie, general_2=ennemi), (3, 0))

    def test_malus_qg_personnels_non_amplifies_par_messager(self):
        qg = self.combattant(pc=20, etiquettes={'chaman': 1, 'cruelle': 1}, nombre=10)
        allie = self.combattant('j2', place='2', pc=100, nombre=10)
        ennemi = self.combattant('bot', nombre=10)
        self.speciale(allie, 'messager_du_QG')
        (qg['chemin'] / 'QG.txt').touch()
        with self.contexte():
            self.assertEqual(self.combats._malus_chaman_duel(
                self.progression.caracteristiques_general(qg), 'orc_archer', 0, ennemi, qg), 10)
            self.assertEqual(self.combats._malus_chaman_duel(
                self.progression.caracteristiques_general(allie), 'orc_archer', 0, ennemi, allie), 15)
            for adverse, attendu in ((qg, 10), (allie, 15)):
                with self.combats.effets_moral_duel(ennemi, adverse):
                    self.assertEqual(self.combats._MALUS_MORAL_DUEL.get()[('bot', 'general1')], attendu)

    def test_cruelle_fraction_sauvetages_sans_mutation_du_moral(self):
        g = self.creer(nombre=10)
        adversaire = self.combattant('bot', pc=15, etiquettes={'cruelle': 1})
        avant = self.progression.caracteristiques_general(g)
        with self.combats.effets_moral_duel(g, adversaire):
            pertes = self.combats.supprimer_unites(self.infos(g), 0, g)
        self.assertEqual(len(pertes), 1)  # floor(10 * 92,5 %) = 9 sauvetages
        self.assertEqual(self.progression.caracteristiques_general(g), avant)
        self.assertEqual(self.combats._MALUS_MORAL_DUEL.get(), {})

    def test_destruction_qg_au_choc_et_en_manoeuvre(self):
        for bloc in ('avant', 'arriere'):
            with self.subTest(bloc=bloc):
                numero = 1 if bloc == 'avant' else 2
                qg = self.combattant(numero=numero, pc=20, etiquettes={'cruelle': 1}, nombre=1)
                allie = self.combattant('j2', numero=numero, place='2', etiquettes={'infanterie': 1})
                ennemi = self.combattant('bot', numero=numero, nombre=20)
                if bloc == 'arriere':
                    unite = ennemi['chemin'] / 'avant/infanterie1'
                    for unite in list(unite.parent.iterdir()):
                        unite.rename(ennemi['chemin'] / 'arriere' / unite.name)
                (qg['chemin'] / 'QG.txt').touch()
                with self.contexte():
                    self.combats.combat_entre_generaux(qg, ennemi)
                    self.assertFalse(qg['chemin'].exists())
                    self.assertEqual(self.combats._effets_transmis(allie), {})
                    self.assertEqual(self.combats._effets_transmis(ennemi, ennemi=True), {})
                    self.assertEqual(self.combats._bonus_valeur_duel(
                        self.progression.caracteristiques_general(allie), 'archer', 0, allie), 10)
                # Isoler les deux scénarios sur le même plateau temporaire.
                import shutil
                for g in (allie, ennemi):
                    if g['chemin'].exists():
                        shutil.rmtree(g['chemin'])

    def test_cascade_un_seul_instantane_et_renfort_ulterieur_sans_releve(self):
        qg = self.combattant(pc=20, etiquettes={'infanterie': 1}, nombre=20, ordre=2)
        (qg['chemin'] / 'QG.txt').touch()
        for numero in range(1, 6):
            bot = self.combattant('bot', numero=numero, nombre=1, equipement='pique')
            if numero == 5:
                (bot['chemin'] / 'QG.txt').touch()
        with patch.object(commandement, 'instantane_qg_territorial',
                          wraps=commandement.instantane_qg_territorial) as calcul:
            resultat = self.survie.resoudre_cascade(self.config.game_path / 'est_3', self.profil)
        self.assertEqual(resultat['affrontements'], 2)
        self.assertEqual(calcul.call_count, 1)  # QG bot encore en attente au début.
        self.assertEqual(self.combats._EFFETS_TERRITOIRE.get(), {})

    def test_renfort_engage_recoit_instantane_initial_sans_apport_pc(self):
        qg = self.combattant(pc=20, etiquettes={'cruelle': 1}, nombre=10)
        allie = self.combattant('j2', pc=100, place='2', nombre=10)
        self.speciale(allie, 'messager_du_QG')
        for numero in range(1, 6):
            ennemi = self.combattant('bot', numero=numero, pc=900, nombre=1)
        (qg['chemin'] / 'QG.txt').touch()
        with self.contexte():
            forces = self.generaux.lire_forces_territoire(self.config.game_path / 'est_3', self.profil)
            premier = forces['bot']['1']
            self.combats.supprimer_unites(self.infos(premier), 0)
            self.generaux.supprimer_general_si_vide(premier)
            self.generaux.remonter_renforts_bot(self.config.game_path / 'est_3', self.profil)
            with self.contexte():
                self.assertEqual(self.combats._effets_transmis(ennemi, ennemi=True)[('malus_moral_adverse', None)], 15)

    def test_anciens_generaux_sans_recompense_retroactive(self):
        g = self.combattant(nombre=1)
        profils = self.progression.charger()
        del profils['j1:general1']
        self.progression.sauvegarder(profils)
        self.assertFalse(self.progression.valider_evenement(g, 'combat', 'ancien'))
        self.assertIsNone(self.progression.caracteristiques_general(g))
        with self.assertRaisesRegex(ValueError, 'migration'):
            self.progression.attribuer_niveau(g)
