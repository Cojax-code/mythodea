"""Décisions v2.0 : roulette, connaissances, valeurs nulles et retraite du QG."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import Mock, patch

import test_stabilisation_finale as support
import progression
import catalogues


class ProgressionEtape2(unittest.TestCase):
    fiche = support.ProgressionFinale.fiche

    def test_neuf_distributions_exactes_dans_la_montee_reelle(self):
        attendus = {
            'stratege': [(50, 0, 15, 35), (45, 0, 15, 40), (25, 0, 40, 35)],
            'instinctif': [(10, 55, 20, 15), (10, 50, 20, 20), (10, 35, 40, 15)],
            'hybride': [(30, 30, 15, 25), (25, 30, 15, 30), (20, 20, 35, 25)],
        }
        categories = ('commandement', 'moral', 'unite', 'etiquette')
        for nature in progression.NATURES:
            famille = 'hybride' if nature.endswith('_hybride') else nature
            for trait, poids in zip(('charismatique', 'leader', 'inventeur'), attendus[famille]):
                with self.subTest(nature=nature, trait=trait):
                    self.assertEqual(progression.RECOMPENSES[famille][trait], dict(zip(categories, poids)))
                    compte = Counter()
                    fiche = self.fiche(nature, trait_inne=trait)
                    for tirage in range(1, 101):
                        rng = Mock(randint=lambda a, b: tirage if (a, b) == (1, 100) else a)
                        apres, gain = progression.monter_niveau(fiche, rng)
                        categorie = ('unite' if isinstance(gain, int) else
                                     {'maitrise_commandement': 'commandement',
                                      'force_caractere': 'moral', 'etiquette': 'etiquette'}[gain[0]])
                        compte[categorie] += 1
                        self.assertEqual(apres['nature'], nature)
                    self.assertEqual(dict(compte), {c: p for c, p in zip(categories, poids) if p})

    def test_instinctif_pc_roulette_sans_gain_naturel(self):
        for gain in (5, 10):
            rng = Mock(randint=lambda a, b: gain if (a, b) == (5, 10) else a)
            apres, recompense = progression.monter_niveau(self.fiche('instinctif', points_commandement=0), rng)
            self.assertEqual((apres['points_commandement'], recompense), (gain, ('maitrise_commandement', gain)))
            self.assertEqual(apres['moral'], 0)

    def test_gains_naturels_des_quatre_natures_et_plafond_moral(self):
        # Une mémoire d'unité isole les gains naturels de toute statistique de roulette.
        for nature in progression.NATURES:
            for niveau in (0, 1, 5, 6):
                for gain in (2, 4):
                    fiche = self.fiche(nature, niveau=niveau, moral=99, evolution_apprise=105)
                    avant = deepcopy(fiche)
                    apres, recompense = progression.monter_niveau(fiche, Mock(randint=lambda a, b: gain))
                    pc = gain if nature != 'instinctif' else 0
                    moral = 1 if nature != 'stratege' and (niveau + 1) % 2 == 0 else 0
                    self.assertEqual((apres['points_commandement'], apres['moral']), (15 + pc, 99 + moral))
                    self.assertEqual(recompense, 105)
                    self.assertEqual(fiche, avant)
                    plafonnee = dict(fiche, moral=100)
                    self.assertEqual(progression.monter_niveau(plafonnee, Mock(randint=lambda a, b: gain))[0]['moral'], 100)

    def test_roulette_apprend_sans_plafond_ni_amelioration_de_rang(self):
        for nature in progression.NATURES:
            fiche = self.fiche(nature, niveau=20)
            for _ in catalogues.ETIQUETTES_COMBAT:
                precedentes = dict(fiche['etiquettes'])
                fiche, recompense = progression.monter_niveau(fiche, Mock(randint=lambda a, b: b))
                self.assertEqual(recompense[0], 'etiquette')
                self.assertNotIn(recompense[1], precedentes)
                self.assertEqual(fiche['etiquettes'][recompense[1]], 1)
                self.assertTrue(all(fiche['etiquettes'][nom] == rang for nom, rang in precedentes.items()))
                self.assertNotIn('etiquettes_permanentes', fiche)
            self.assertEqual(set(fiche['etiquettes']), set(catalogues.ETIQUETTES_COMBAT))
            avant = dict(fiche['etiquettes'])
            fiche, recompense = progression.monter_niveau(fiche, Mock(randint=lambda a, b: b))
            self.assertEqual(fiche['etiquettes'], avant)
            self.assertIsInstance(recompense, int)  # La catégorie unité reste disponible.

    def test_redistribution_proportionnelle_categories_epuisees(self):
        fiche = self.fiche('instinctif', moral=100,
                           etiquettes=dict.fromkeys(catalogues.ETIQUETTES_COMBAT, 3))
        # Moral et étiquettes retirés : 10 PC / 20 unité, soit 1/3 et 2/3.
        compte = Counter()
        for tirage in range(1, 31):
            rng = Mock(randint=lambda a, b: tirage if (a, b) == (1, 30) else a)
            apres, recompense = progression.monter_niveau(fiche, rng)
            compte['unite' if isinstance(recompense, int) else recompense[0]] += 1
            self.assertEqual(apres['etiquettes'], fiche['etiquettes'])
        self.assertEqual(compte, {'maitrise_commandement': 10, 'unite': 20})
        fiche['evolutions_acquises'] = [i for i, e in catalogues.EVOLUTIONS.items() if e['categorie'] == 'unite']
        for _ in range(3):
            fiche, gain = progression.monter_niveau(fiche, Mock(randint=lambda a, b: b))
            self.assertEqual(gain, ('maitrise_commandement', 10))

    def test_paliers_garantis_meme_si_limite_activation_atteinte(self):
        for nature in progression.NATURES:
            for niveau in ((4, 9) if nature.startswith('stratege') else (4,)):
                fiche = self.fiche(nature, niveau=niveau, evolution_apprise=105,
                                   etiquettes=dict.fromkeys(('infanterie', 'distance', 'melee', 'orc'), 1))
                apres, gain = progression.monter_niveau(fiche, random.Random(13))
                self.assertEqual(gain[0], 'etiquette')
                self.assertEqual(len(apres['etiquettes']), 5)
                self.assertNotIn('etiquettes_permanentes', apres)
                self.assertEqual(apres['etiquettes'][gain[1]], 1)
                self.assertEqual(apres['evolution_apprise'], 105)

    def test_ecole_conserve_rangs_et_capacite_scolaire_sans_plafond_total_par_nature(self):
        for nature in progression.NATURES:
            fiche = self.fiche(nature, niveau=50, etiquettes=dict.fromkeys(list(catalogues.ETIQUETTES_COMBAT)[:5], 1))
            apres = progression.apprendre_etiquette(fiche, 'cruelle')
            self.assertEqual(len(apres['etiquettes']), 6)
            apres = progression.apprendre_etiquette(apres, 'cruelle')
            self.assertEqual(apres['etiquettes']['cruelle'], 2)

    def test_palier_catalogue_etiquettes_epuise_conserve_rangs_et_utilise_memoire(self):
        fiche = self.fiche(niveau=4, evolution_apprise=201,
                           etiquettes=dict.fromkeys(catalogues.ETIQUETTES_COMBAT, 2))
        apres, recompense = progression.monter_niveau(fiche, Mock(randint=lambda a, b: a))
        self.assertEqual(recompense, ('maitrise_commandement', 5))
        self.assertEqual(apres['etiquettes'], fiche['etiquettes'])
        self.assertNotIn('etiquettes_permanentes', apres)
        self.assertIsNone(apres['evolution_apprise'])

    def test_graine_fixe_reproduit_profils_et_recompenses(self):
        def parcours(graine):
            rng = random.Random(graine)
            resultats = []
            for nature in progression.NATURES:
                for trait in ('charismatique', 'leader', 'inventeur'):
                    fiche = self.fiche(nature, trait_inne=trait)
                    for _ in range(40):
                        fiche, gain = progression.monter_niveau(fiche, rng)
                        resultats.append((fiche, gain))
            return resultats
        self.assertEqual(parcours(137), parcours(137))
        self.assertNotEqual(parcours(137), parcours(138))

    def test_emplacement_zombie_exclusif_mort_vivant_et_selection_par_defaut(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier)
            selection = chemin / 'etiquettes_actives.txt'
            for nature in progression.NATURES:
                maximum = 3 if nature.startswith('stratege') else 1
                ordinaires = ['infanterie', 'distance', 'melee', 'cruelle'][:maximum + 1]
                for connue in (False, True):
                    # mort_vivant en premier doit laisser toutes les places ordinaires libres.
                    noms = (['mort_vivant'] if connue else []) + ordinaires
                    fiche = self.fiche(nature, etat_zombie=True, etiquettes=dict.fromkeys(noms, 1))
                    for choisies in (ordinaires, (['mort_vivant'] if connue else []) + ordinaires):
                        selection.write_text(','.join(choisies), encoding='utf-8')
                        with self.assertRaises(ValueError):
                            progression.selection_etiquettes(fiche, chemin)
                    for choisies in ([], ordinaires[:maximum],
                                     (['mort_vivant'] if connue else []) + ordinaires[:maximum]):
                        selection.write_text(','.join(choisies), encoding='utf-8')
                        self.assertEqual(progression.selection_etiquettes(fiche, chemin)['etiquettes_actives'], choisies)
                    selection.unlink()
                    self.assertEqual(progression.selection_etiquettes(fiche, chemin)['etiquettes_actives'],
                                     (['mort_vivant'] if connue else []) + ordinaires[:maximum])
                    if connue:
                        fiche['etat_zombie'] = False
                        self.assertEqual(len(progression.selection_etiquettes(fiche, chemin)['etiquettes_actives']), maximum)


class CombatsEtape2(unittest.TestCase):
    setUp = support.IntegrationFinale.setUp
    activer = support.IntegrationFinale.activer
    general = support.IntegrationFinale.general
    creer = support.IntegrationFinale.creer
    infos = support.IntegrationFinale.infos
    modules = support.IntegrationFinale.modules
    speciale = support.IntegrationFinale.speciale
    combattant = support.IntegrationFinale.combattant
    contexte = support.IntegrationFinale.contexte

    def test_zero_contre_positif_positif_contre_zero_et_zero_contre_zero(self):
        a, b = dict(type='orc_archer', nombre=10), dict(type='orc_archer', nombre=7)
        for pc in (200, 201, 1000):
            chaman = dict(points_commandement=pc, etiquettes={'chaman': 1})
            self.assertEqual(self.combats.combat_bloc(a, b, fiche_2=chaman), (0, 7))
            self.assertEqual(self.combats.combat_bloc(a, b, fiche_1=chaman), (10, 0))
            for fatigue in ((False, False), (True, False), (False, True)):
                self.assertEqual(self.combats.combat_bloc(a, b, *fatigue, fiche_1=chaman, fiche_2=chaman), (10, 7))

    def test_fraction_positive_sous_un_pourcent_sans_arrondi(self):
        a, b = dict(type='orc_archer', nombre=1000), dict(type='orc_archer', nombre=1)
        # 99,5 % de malus : valeur 0,03 ; 6 / 0,03 = 200 pertes.
        chaman = dict(points_commandement=199, etiquettes={'chaman': 1})
        self.assertEqual(self.combats.combat_bloc(a, b, fiche_2=chaman), (800, 0))

    def test_malus_cumules_et_bonus_additifs_au_seuil_zero(self):
        qg = self.combattant(pc=120, etiquettes={'chaman': 1})
        allie = self.combattant('j2', place='2', pc=80, etiquettes={'chaman': 1})
        adverse = self.combattant('bot')
        (qg['chemin'] / 'QG.txt').touch()
        a, b = dict(type='orc_archer', nombre=10), dict(type='orc_archer', nombre=10)
        with self.contexte():
            fiche = self.progression.caracteristiques_general(allie)
            self.assertEqual(self.combats._malus_chaman_duel(fiche, 'orc_archer', 1, adverse, allie), 100)
            self.assertEqual(self.combats.combat_bloc(a, b, fiche_1=fiche,
                general_1=allie, general_2=adverse), (10, 0))
            # +50 % personnels et -100 % cumulés : la valeur reste à 50 %.
            self.assertEqual(self.combats.combat_bloc(a, b, fiche_1=fiche,
                fiche_2=dict(points_commandement=100, etiquettes={'orc': 1}),
                general_1=allie, general_2=adverse), (5, 0))

    def test_zero_conserve_sauvetages_et_rapports_sans_pertes_artificielles(self):
        a = self.combattant(nombre=0)
        b = self.combattant('bot', nombre=1, pc=200, etiquettes={'chaman': 1})
        for n in range(10):
            self.speciale(a, 'orc_archer', n)
        profils = self.progression.charger()
        profils['j1:general1'].update(nature='instinctif', moral=100)
        self.progression.sauvegarder(profils)
        armee = {g['joueur']: self.generaux.lire_blocs_general(g['chemin']) for g in (a, b)}
        # Le traitement racial/moral existant reste seul responsable du sauvetage.
        with self.contexte():
            detail = self.combats.confrontation_directe(armee, a, b, 'avant')
        self.assertEqual((detail['final_1'], detail['final_2']), (10, 1))
        self.assertTrue(all(int((u / 'blessures.txt').read_text()) == 1 for u in self.infos(a)['unites']))

    def test_zero_zero_resolution_bornee_sans_pertes(self):
        a = self.combattant(nombre=0, pc=200, etiquettes={'chaman': 1})
        b = self.combattant('bot', nombre=0, pc=200, etiquettes={'chaman': 1})
        for g in (a, b):
            self.speciale(g, 'orc_archer')
        with self.contexte():
            resultat = self.combats.combat_entre_generaux(a, b)
        self.assertEqual((resultat['final_1'], resultat['final_2']), (1, 1))
        self.assertEqual(resultat['manoeuvres'], [])
        self.assertEqual((self.infos(a)['nombre'], self.infos(b)['nombre']), (1, 1))
        with patch.object(self.combats, 'combat_entre_generaux',
                          wraps=self.combats.combat_entre_generaux) as duels:
            self.combats.resoudre_combat_range(self.config.game_path / 'est_3', 'OFF/OFF', self.profil)
        self.assertEqual(duels.call_count, 0)  # Impasse détectable avant tout engagement inutile.
        self.assertEqual((self.infos(a)['nombre'], self.infos(b)['nombre']), (1, 1))

    def paire_nulle(self):
        a = self.combattant(nombre=0, pc=200, etiquettes={'chaman': 1})
        b = self.combattant('bot', nombre=0, pc=200, etiquettes={'chaman': 1})
        for g in (a, b):
            self.speciale(g, 'orc_archer')
        return a, b

    def test_choc_nul_autre_bloc_positif_continue(self):
        a, b = self.paire_nulle()
        self.speciale(a, 'archer', bloc='arriere')
        with self.contexte():
            resultat = self.combats.combat_entre_generaux(a, b)
        self.assertEqual(resultat['final_2'], 0)
        self.assertTrue(resultat['manoeuvres'])

    def test_premiers_generaux_nuls_autre_general_continue(self):
        a, b = self.paire_nulle()
        renfort = self.combattant(numero=2, place='2', nombre=2)
        with patch.object(self.combats, 'combat_entre_generaux',
                          wraps=self.combats.combat_entre_generaux) as duels:
            self.combats.resoudre_combat_range(self.config.game_path / 'est_3', 'OFF/OFF', self.profil)
        self.assertEqual(duels.call_count, 1)
        self.assertEqual(duels.call_args.args[0]['nom'], renfort['nom'])
        self.assertEqual(self.infos(a)['nombre'], 1)
        self.assertFalse(b['chemin'].exists())

    def test_impasse_off_def_conserve_defenseur_sans_inventer_retraite_bot(self):
        a, b = self.paire_nulle()
        bilan = {}
        self.combats.resoudre_combat_off_def(self.config.game_path / 'est_3', 'allies', self.profil, bilan=bilan)
        self.assertEqual(bilan['camps_retraite'], ['bot'])
        self.assertEqual(bilan['controle'], 'conteste')
        self.assertTrue(a['chemin'].exists() and b['chemin'].exists())

    def test_impasse_survie_off_off_retraite_alliee_bot_non_resolu(self):
        a, b = self.paire_nulle()
        resultat = self.survie.resoudre_cascade(self.config.game_path / 'est_3', self.profil)
        self.assertEqual(len(resultat['retraites']), 1)
        self.assertTrue(resultat['retraites'][0]['chemin'].is_relative_to(self.config.game_path / 'est_2'))
        self.assertEqual(resultat['impasse']['retraites_non_resolues'], ['bot:general1'])
        self.assertEqual(resultat['controle'], 'bot')  # Occupant réel, pas territoire libéré.
        self.assertFalse(a['chemin'].exists())
        self.assertTrue(b['chemin'].exists())

    def test_impasse_retraite_differee_qg_desactive_avant_deplacement(self):
        a, b = self.paire_nulle()
        (a['chemin'] / 'QG.txt').touch()
        reservations = []
        with self.contexte():
            resultat = self.survie.resoudre_cascade(self.config.game_path / 'est_3', self.profil,
                                                   'OFF/DEF', reservations, defenseur='bot')
            self.assertIn('allies', self.combats._EFFETS_TERRITOIRE.get()['qg_inactifs'])
        self.assertEqual(len(reservations), 1)
        self.assertTrue(a['chemin'].exists())
        self.assertEqual(resultat['impasse']['retraites_non_resolues'], [])
        self.survie.mouvements.appliquer_retraites_surnombre(reservations, self.profil)
        self.assertFalse(a['chemin'].exists())

    def test_impasse_retraite_bloquee_par_bot_conserve_territoire_conteste(self):
        a, b = self.paire_nulle()
        self.general('bot', numero=2, territoire='est_2', nombre=1)
        resultat = self.survie.resoudre_cascade(self.config.game_path / 'est_3', self.profil,
                                               'OFF/DEF', defenseur='bot')
        self.assertEqual(resultat['retraites'], [])
        self.assertEqual(resultat['controle'], 'conteste')
        self.assertEqual(resultat['impasse']['retraites_non_resolues'], ['j1:general1'])

    def test_impasse_sans_route_signalee_sans_exception_ni_deplacement(self):
        a, b = self.paire_nulle()
        profil = dict(self.profil, carte_territoires={})
        resultat = self.survie.resoudre_cascade(self.config.game_path / 'est_3', profil,
                                               'OFF/DEF', defenseur='bot')
        self.assertEqual(resultat['controle'], 'conteste')
        self.assertEqual(resultat['retraites'], [])
        self.assertEqual(resultat['impasse']['retraites_non_resolues'], ['j1:general1'])
        self.assertTrue(a['chemin'].exists() and b['chemin'].exists())

    def test_impasse_off_def_sans_defenseur_ne_choisit_pas_un_camp(self):
        a, b = self.paire_nulle()
        resultat = self.survie.resoudre_cascade(self.config.game_path / 'est_3', self.profil, 'OFF/DEF')
        self.assertEqual(resultat['controle'], 'conteste')
        self.assertEqual(resultat['retraites'], [])
        self.assertEqual(resultat['impasse']['camps_retraite'], [])
        self.assertTrue(a['chemin'].exists() and b['chemin'].exists())

    def test_renfort_promu_apres_duel_frontal_reprend_avant_impasse(self):
        a, b = self.paire_nulle()
        (a['chemin'] / 'ordre_surnombre.txt').write_text('2', encoding='utf-8')
        self.combattant(numero=2, place='2', nombre=1)
        self.combattant('bot', numero=2, nombre=1)
        for numero in (3, 4):
            g = self.combattant('bot', numero=numero, nombre=0, pc=200, etiquettes={'chaman': 1})
            self.speciale(g, 'orc_archer')
        self.combattant('bot', numero=5, nombre=2)
        profil = dict(self.profil, configurations_terrain={'est_3': {'attaque_frontale': True}})
        resultat = self.survie.resoudre_cascade(self.config.game_path / 'est_3', profil)
        self.assertEqual(resultat['affrontements'], 2)
        self.assertEqual(resultat['retraites'], [])
        self.assertEqual(resultat['controle'], 'bot')

    def test_etiquette_roulette_persiste_rejeu_ne_redonne_rien_selection_preservee(self):
        g = self.combattant(etiquettes={'infanterie': 1})
        (g['chemin'] / 'etiquettes_actives.txt').write_text('infanterie', encoding='utf-8')
        profils = self.progression.charger()
        profils['j1:general1'].update(progression_combat=1)
        self.progression.sauvegarder(profils)
        rng = Mock(randint=lambda a, b: b)
        self.assertTrue(self.progression.valider_evenement(g, 'combat', 'etape2', rng))
        apres = self.progression.charger()['j1:general1']
        self.assertEqual(apres['etiquettes'], {'infanterie': 1, 'cruelle': 1})
        self.assertEqual(apres['progressions_validees']['combat:etape2']['recompense'], ['etiquette', 'cruelle'])
        self.assertEqual(self.progression.caracteristiques_general(g)['etiquettes_actives'], ['infanterie'])
        self.assertFalse(self.progression.valider_evenement(g, 'combat', 'etape2', rng))
        self.assertEqual(self.progression.charger()['j1:general1'], apres)

    def test_retraite_non_qg_conserve_instantane_messager_initial(self):
        qg = self.combattant(etiquettes={'infanterie': 1})
        allie = self.combattant('j2', place='2', nombre=10, pc=100)
        self.speciale(allie, 'messager_du_QG', bloc='arriere')
        (qg['chemin'] / 'QG.txt').touch()
        with self.contexte():
            self.combats.desactiver_qg_retraite(allie)
            self.assertEqual(self.combats._effets_transmis(allie), {('valeur', 'infanterie'): 15})
            self.assertEqual(self.combats._EFFETS_TERRITOIRE.get()['qg'], {('j1', 'general1')})

    def test_retraite_qg_messager_renforts_sans_releve_et_effets_personnels_conserves(self):
        qg = self.combattant(etiquettes={'infanterie': 1, 'chaman': 1, 'cruelle': 1})
        allie = self.combattant('j2', place='2', nombre=10, pc=100, etiquettes={'infanterie': 1})
        adverse = self.combattant('bot', etiquettes={'cruelle': 1})
        renfort = self.combattant('j2', numero=2, place='5', pc=900)
        self.speciale(allie, 'messager_du_QG', bloc='arriere')
        for g in (qg, adverse, renfort):
            (g['chemin'] / 'QG.txt').touch()
        with self.contexte():
            self.assertEqual(self.combats._effets_transmis(allie)[('valeur', 'infanterie')], 15)
            self.assertEqual(self.combats._effets_transmis(adverse, ennemi=True)[('malus_moral_adverse', None)], 15)
            self.combats.desactiver_qg_retraite(qg)
            self.assertTrue(qg['chemin'].exists())
            destination = self.config.game_path / 'est_3/j2/3/general2'
            destination.parent.mkdir(parents=True, exist_ok=True)
            renfort['chemin'].rename(destination)
            renfort['chemin'] = destination
            with self.contexte():
                for g in (allie, renfort):
                    self.assertEqual(self.combats._effets_transmis(g), {})
                    self.assertEqual(self.combats._effets_transmis(g, ennemi=True), {('malus_moral_adverse', None): 10})
                self.assertEqual(self.combats._effets_transmis(adverse, ennemi=True), {})
                self.assertEqual(self.combats._bonus_valeur_duel(
                    self.progression.caracteristiques_general(allie), 'archer', 0, allie), 50)
                self.assertNotIn(('j2', 'general2'), self.combats._EFFETS_TERRITOIRE.get()['qg'])
            self.combats.desactiver_qg_retraite(qg)  # Idempotence.
            self.assertEqual(self.combats._effets_transmis(allie), {})
        self.assertEqual(self.combats._EFFETS_TERRITOIRE.get(), {})

    def cascade_qg(self, differee, refus=False):
        qg = self.combattant(nombre=20, ordre=1, etiquettes={'infanterie': 1, 'chaman': 1, 'cruelle': 1})
        allie = self.combattant('j2', place='2', nombre=10, ordre=2, pc=100,
                               etiquettes={'infanterie': 1})
        self.speciale(allie, 'messager_du_QG', bloc='arriere')
        (qg['chemin'] / 'QG.txt').touch()
        for numero in range(1, 6):
            self.combattant('bot', numero=numero, nombre=1, equipement='pique')
        if refus:
            self.general('bot', numero=6, territoire='est_2', nombre=1)
        reservations = [] if differee else None
        resoudre = self.combats.resoudre_combat_range
        observations = []

        def observer(*args, **kwargs):
            observations.append(dict(self.combats._effets_transmis(allie)))
            if len(observations) == 2:
                self.assertEqual(qg['chemin'].exists(), differee)
                self.assertEqual(bool(reservations), differee and not refus)
            return resoudre(*args, **kwargs)

        appliquer = self.survie.mouvements.appliquer_retraites_surnombre

        def deplacer(destinations, configuration):
            if destinations:
                self.assertEqual(self.combats._effets_transmis(allie), {})
                self.assertTrue(qg['chemin'].exists())
            return appliquer(destinations, configuration)

        with patch.object(self.combats, 'resoudre_combat_range', side_effect=observer), \
                patch.object(self.survie.mouvements, 'appliquer_retraites_surnombre', side_effect=deplacer):
            resultat = self.survie.resoudre_cascade(self.config.game_path / 'est_3', self.profil,
                                                   en_cours_de_fuite=reservations)
        self.assertEqual(resultat['affrontements'], 2)
        self.assertEqual(observations[0][('valeur', 'infanterie')], 15)
        self.assertEqual(observations[1], observations[0] if refus else {})
        self.assertEqual(len(resultat['retraites']), 0 if refus else 1)

    def test_cascade_reelle_retraite_differee_desactive_entre_affrontements(self):
        self.cascade_qg(True)

    def test_cascade_reelle_retraite_immediate_desactive_avant_deplacement(self):
        self.cascade_qg(False)

    def test_cascade_reelle_retraite_refusee_garde_soutien(self):
        self.cascade_qg(True, refus=True)


if __name__ == '__main__':
    unittest.main()
