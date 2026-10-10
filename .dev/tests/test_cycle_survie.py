"""Cycle Est réel sur plateau temporaire ; horloge simulée, aucune attente."""
import importlib
import random
import unittest
from unittest.mock import call, patch

import test_surnombre
from support_cycle import GelSimule


class CycleSurvie(unittest.TestCase):
    def setUp(self):
        test_surnombre.Surnombre.setUp(self)
        for nom, relatif in {"rapport_dir": "rapport", "rapport_court_path": "rapport/rapport_court.txt",
                             "meteo_path": "systeme/meteo.txt"}.items():
            setattr(self.config, nom, self.config.game_path / relatif)
        for joueur in self.profil["joueurs"]:
            (self.racine / "home" / joueur).mkdir(parents=True, exist_ok=True)
        self.minuterie = importlib.import_module("minuterie")
        self.contextes.enter_context(patch.object(self.minuterie.time, "sleep",
                                                side_effect=AssertionError("Attente réelle interdite")))
        self.activer(1)
        self.profil['duree_gel_secondes'] = 0
        self.profil['collecteur_crypte'] = False  # Le socket réel a sa suite Linux dédiée.
        self.profil['publication_homes_path'] = self.racine / 'staging_homes'
        self.contextes.enter_context(patch.object(self.survie, 'creer_gestion',
            lambda c, horloge=None, dormir=None: self.cycle_linux.Generations(
                c, GelSimule(), horloge=horloge, dormir=dormir)))

    general = test_surnombre.Surnombre.general
    colonne = test_surnombre.Surnombre.colonne
    preference = test_surnombre.Surnombre.preference

    def activer(self, tour):
        self.etat.sauvegarder_cycle_survie({"tour": tour, "phase": "actions", "echeance": 100}, self.profil)

    def resoudre(self, apparitions=True):
        # Ces régressions éprouvent le moteur sur leur plateau isolé. L'enveloppe
        # capture/publication est exercée séparément par test_generations_survie.
        with self.etat.verrou_cycle_survie(self.profil):
            if apparitions:
                return self.survie._resoudre_tour_capture(self.profil, random.Random(5))
            with patch.object(self.survie, "creer_vague_est", return_value=[]):
                return self.survie._resoudre_tour_capture(self.profil, random.Random(5))

    def photo(self):
        return {str(p.relative_to(self.racine)): p.read_bytes()
                for p in self.racine.rglob("*") if p.is_file()}

    def test_tour_zero_cree_vague_un_sans_deplacer_nouveaux(self):
        self.activer(0)
        resultat = self.resoudre()
        self.assertEqual((resultat["tour"], resultat["vague"]), (0, 1))
        self.assertEqual(resultat["deplacements"], [])
        self.assertEqual([self.etat.charger_positions_generaux()[f"bot:general{i}"] for i in (1, 2, 3)],
                         ["est_1", "est_2", "est_3"])
        self.assertEqual(self.etat.charger_cycle_survie(self.profil), {"tour": 1, "phase": "a_preparer"})

    def test_tour_un_deplace_vague_un_puis_cree_vague_deux(self):
        self.activer(0)
        self.resoudre()
        self.activer(1)
        resultat = self.resoudre()
        self.assertEqual(len(resultat["deplacements"]), 3)
        self.assertEqual(self.etat.charger_positions_generaux(), {
            "bot:general1": "village", "bot:general2": "est_1",
            "bot:general3": "est_2", "bot:general4": "est_3"})
        self.assertTrue(resultat["defaite"])

    def test_plan_deplacement_sans_mutation_et_independant_scan(self):
        self.colonne(6, "village", numeros=range(20, 26))
        self.colonne(7, "est_1", numeros=range(1, 8))
        self.colonne(3, "est_2", numeros=range(10, 13))
        avant = self.photo()
        premier = self.survie.preparer_deplacements_ennemis(self.profil)
        profil = dict(self.profil, territoires=list(reversed(self.profil["territoires"])))
        self.assertEqual(self.survie.preparer_deplacements_ennemis(profil), premier)
        self.assertEqual(self.photo(), avant)
        resultat = self.survie.appliquer_deplacements_ennemis(premier, self.profil)
        self.assertEqual(len(resultat), 10)
        self.assertEqual(len({g["nom"] for g in resultat}), 10)
        self.assertEqual([g["nom"] for g in self.survie.inventorier_ennemis(
            self.config.game_path / "village", self.profil)],
            [f"general{i}" for i in [*range(20, 26), *range(1, 8)]])
        self.assertEqual([g["nom"] for g in self.survie.inventorier_ennemis(
            self.config.game_path / "est_1", self.profil)], [f"general{i}" for i in range(10, 13)])

    def test_materialisation_inverse_sans_changer_compositions_ni_affichages(self):
        attendus = self.vagues.composer_vague_est(5, random.Random(4))
        reel = self.generaux.creer_general
        ordre = []
        def tracer(chemin, nom):
            ordre.append(next(t for t in self.survie.ORDRE_APPARITION_EST if t in chemin.parts))
            return reel(chemin, nom)
        with patch.object(self.generaux, "creer_general", side_effect=tracer):
            crees = self.survie.creer_vague_est(5, self.profil, random.Random(4))
        self.assertEqual(ordre, ["est_3", "est_3", "est_2", "est_2", "est_1", "est_1"])
        for chemin, composition in zip(crees, attendus):
            self.assertIn(composition["territoire"], chemin.parts)
            self.assertEqual(self.generaux.lire_fiche_general(chemin)["nom_affichage"], composition["nom_affichage"])
            blocs = self.generaux.lire_blocs_general(chemin)
            for bloc, attendu in composition["blocs"].items():
                self.assertEqual(blocs[bloc]["nombre"], attendu["nombre"])
                if attendu["nombre"]:
                    self.assertEqual(blocs[bloc]["type"], attendu["type"])

    def test_deplacement_et_toutes_apparitions_avant_combats(self):
        self.activer(4)  # vague Boss 5 sur trois territoires
        for index, nom in enumerate(self.survie.ORDRE_RESOLUTION_EST, 1):
            self.general(numero=index, territoire=nom, nombre=1)
        self.colonne(1, "est_1")
        reel = self.survie.resoudre_cascade
        ordre = []
        def verifier(territoire, *args):
            ordre.append(territoire.name)
            self.assertEqual(self.etat.lire_compteur_general("bot"), 7)
            if len(ordre) == 1:
                self.assertEqual(self.etat.charger_positions_generaux()["bot:general1"], "village")
                for nom in self.survie.ORDRE_APPARITION_EST:
                    self.assertEqual(len(self.survie.inventorier_ennemis(self.config.game_path / nom, self.profil)), 2)
            return reel(territoire, *args)
        with patch.object(self.survie, "resoudre_cascade", side_effect=verifier):
            self.resoudre()
        self.assertEqual(ordre, ["village", "est_1", "est_2", "est_3"])

    def test_combat_simple_controle_sauve_bot_detruit_pas_defaite(self):
        self.general(territoire="village")
        self.colonne(1, "est_1")
        resultat = self.resoudre(False)
        self.assertEqual(resultat["batailles"]["village"]["affrontements"], 1)
        self.assertFalse(resultat["defaite"])
        self.assertEqual(self.etat.charger_controle_territoires(self.profil), resultat["controle"])
        self.assertEqual(resultat["controle"]["village"], "allies")

    def test_bot_gagne_village_apres_combat_defaite_persistante(self):
        self.general(territoire="village", nombre=1, equipement="pique")
        self.general("bot", territoire="est_1", nombre=20, equipement="arc")
        resultat = self.resoudre(False)
        self.assertTrue(resultat["defaite"])
        self.assertEqual(resultat["controle"]["village"], "bot")
        self.assertEqual(self.etat.charger_cycle_survie(self.profil)["phase"], "defaite")
        with self.assertRaises(RuntimeError):
            self.resoudre()
        self.assertIn("DÉFAITE", self.config.rapport_court_path.read_text(encoding="utf-8"))

    def test_cascade_continue_pertes_persistantes(self):
        allie = self.general(territoire="est_2", ordre=2)
        self.colonne(10, "est_3")
        resultat = self.resoudre(False)
        self.assertEqual(resultat["batailles"]["est_2"]["affrontements"], 3)
        self.assertEqual(self.generaux.total_general_depuis_chemin(allie), 10)

    def test_retraite_reservee_dossier_deplace_apres_tous_combats(self):
        fuyard = self.general(territoire="est_2", ordre=1)
        self.general("j2", territoire="est_2", place="2", ordre=2)
        self.colonne(10, "est_3")
        appliquer = self.mouvements.appliquer_retraites_surnombre
        def verifier(destinations, profil):
            self.assertTrue(fuyard.exists())
            self.assertEqual(len(destinations), 1)
            self.assertFalse(destinations[0][1].exists())
            self.assertEqual(self.generaux.total_general_depuis_chemin(fuyard), 17)
            return appliquer(destinations, profil)
        with patch.object(self.mouvements, "appliquer_retraites_surnombre", side_effect=verifier):
            resultat = self.resoudre(False)
        self.assertEqual(resultat["batailles"]["est_2"]["affrontements"], 3)
        self.assertFalse(fuyard.exists())
        self.assertEqual(self.generaux.total_general_depuis_chemin(resultat["retraites"][0][1]), 17)
        self.assertNotIn("conteste", resultat["controle"].values())

    def test_destination_bot_interdit_fuite_et_general_continue(self):
        allie = self.general(territoire="est_1", ordre=1)
        self.colonne(1, "village", numeros=(20,))
        self.colonne(5, "est_2")
        resultat = self.resoudre(False)
        self.assertEqual(resultat["retraites"], [])
        self.assertEqual(resultat["batailles"]["est_1"]["affrontements"], 2)
        self.assertEqual(self.generaux.total_general_depuis_chemin(allie), 15)
        self.assertTrue(resultat["defaite"])
        self.assertEqual(resultat["controle"]["village"], "bot")

    def test_place_indisponible_reste_engage_autre_general_peut_fuir(self):
        bloque = self.general(territoire="est_2", ordre=1)
        libre = self.general("j2", territoire="est_2", place="2", ordre=1)
        self.preference(bloque, 20)
        self.general(numero=2, territoire="est_1", place="20")
        self.colonne(5, "est_3")
        resultat = self.resoudre(False)
        self.assertEqual(len(resultat["retraites"]), 1)
        self.assertEqual(resultat["retraites"][0][0]["joueur"], "j2")
        self.assertTrue(bloque.exists())
        self.assertFalse(libre.exists())
        self.assertEqual(resultat["batailles"]["est_2"]["affrontements"], 2)

    def test_reservations_successives_preferences_egales_pas_de_collision(self):
        a = self.general("j2", territoire="est_2", place="1", ordre=1)
        b = self.general(territoire="est_2", place="3", ordre=2)
        self.preference(a, 5)
        self.preference(b, 5)
        self.colonne(10, "est_3")
        reel = self.combats.resoudre_combat_range
        compteur = 0
        def changer(*args):
            nonlocal compteur
            resultat = reel(*args)
            compteur += 1
            if compteur == 2:
                (b / "ordre_surnombre.txt").write_text("1\n", encoding="utf-8")
            return resultat
        with patch.object(self.combats, "resoudre_combat_range", side_effect=changer):
            resultat = self.resoudre(False)
        self.assertEqual([p.parent.name for _, p in resultat["retraites"]], ["5", "6"])
        self.assertTrue(all(p.is_dir() for _, p in resultat["retraites"]))

    def test_audit_unique_attente_decremente_une_fois_fatigue_conservee(self):
        self.general(territoire="repli")
        self.etat.sauvegarder_attentes_repli({"j1:general1": 2}, self.profil)
        mobile = self.general("j2", territoire="village")
        mobile.rename(self.config.game_path / "est_2/j2/1/general1")
        with patch.object(self.securite, "verifier_tous_les_deplacements",
                          wraps=self.securite.verifier_tous_les_deplacements) as audit:
            self.resoudre(False)
        self.assertEqual(audit.call_count, 1)
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {"j1:general1": 1})
        self.assertEqual(self.etat.charger_generaux_fatigues(), {"j2:general1"})

    def test_controles_sans_mutation_y_compris_sur_anomalie(self):
        allie = self.general(territoire="village")
        (allie / "avant/invalide").mkdir()
        (allie / "ordre.txt").unlink()
        self.etat.sauvegarder_attentes_repli({"j1:general1": 2}, self.profil)
        avant = self.photo()
        self.securite.controler_coherence_territoires(self.profil)
        self.assertEqual(self.photo(), avant)
        self.general("j2", territoire="village")
        avant = self.photo()
        with self.assertRaisesRegex(ValueError, "Collision"):
            self.securite.controler_coherence_territoires(self.profil)
        self.assertEqual(self.photo(), avant)

    def test_tour_zero_deploiement_valide_et_sortie_village_refusee(self):
        self.activer(0)
        a = self.general(territoire="home")
        a.rename(self.config.game_path / "village/j1/garnison/1/general1")
        b = self.general("j2", territoire="village")
        b.rename(self.config.game_path / "est_1/j2/1/general1")
        self.resoudre(False)
        self.assertEqual(self.etat.charger_positions_generaux(), {"j1:general1": "village", "j2:general1": "repli"})

    def test_ouvrir_tour_idempotent_generation_et_echeance_privees(self):
        self.etat.sauvegarder_cycle_survie({"tour": 0, "phase": "a_preparer"}, self.profil)
        premier = self.survie.ouvrir_tour_survie(self.profil, lambda: 1000)
        self.assertEqual(premier, {"tour": 0, "phase": "actions", "echeance": 1120})
        self.assertEqual(self.survie.ouvrir_tour_survie(self.profil, lambda: 1090), premier)
        self.assertEqual(self.etat.lire_compteur_general("j1"), 1)
        self.assertTrue((self.racine / "home/j1/general1").is_dir())
        prive = self.config.game_path / "systeme/cycle_survie.tmp"
        self.assertIn(call(prive, 0, 0), self.chown.call_args_list)
        self.assertIn(call(prive, 0o600), self.chmod.call_args_list)

    def test_resolution_interrompue_ne_rejoue_pas_audit_ni_vague(self):
        with patch.object(self.survie, "creer_vague_est", side_effect=RuntimeError("interruption")):
            with self.assertRaisesRegex(RuntimeError, "interruption"):
                self.resoudre()
        with patch.object(self.securite, "verifier_tous_les_deplacements") as audit:
            with self.assertRaises(RuntimeError):
                self.resoudre()
            with self.assertRaises(RuntimeError):
                self.survie.ouvrir_tour_survie(self.profil)
        audit.assert_not_called()

    def test_timer_meme_duree_tour_zero_et_suivant_sans_attente_reelle(self):
        self.etat.sauvegarder_cycle_survie({"tour": 0, "phase": "a_preparer"}, self.profil)
        maintenant = [500.0]
        attentes = []
        def dormir(duree):
            attentes.append(duree)
            maintenant[0] += duree
        with patch.object(self.survie, "creer_vague_est", return_value=[]):
            resultats = self.survie.lancer_partie_survie(self.profil, 2, lambda: maintenant[0], dormir)
        self.assertEqual([r["tour"] for r in resultats], [0, 1])
        self.assertEqual(sum(attentes), 300)  # 120 + consultation 60 + 120
        cycle = self.etat.charger_cycle_survie(self.profil)
        self.assertEqual((cycle['tour'], cycle['phase'], cycle['echeance']), (1, 'consultation', 860))

    def test_timer_zero_et_reprise_apres_expiration_sans_sleep(self):
        self.minuterie.attendre_jusqua(100, lambda: 100)
        self.minuterie.attendre_jusqua(100, lambda: 150)
        for valeur in (-1, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                self.minuterie.valider_duree(valeur)
        self.profil["duree_phase_action_secondes"] = 0
        self.etat.sauvegarder_cycle_survie({"tour": 0, "phase": "a_preparer"}, self.profil)
        resultats = self.survie.lancer_partie_survie(self.profil, 1, lambda: 100)
        self.assertEqual(resultats[0]["vague"], 1)

    def test_verrou_refuse_deux_resolveurs_sans_rejouer_audit(self):
        with self.etat.verrou_cycle_survie(self.profil):
            with patch.object(self.securite, "verifier_tous_les_deplacements") as audit:
                with self.assertRaisesRegex(RuntimeError, "verrouillé"):
                    self.resoudre()
                with self.assertRaisesRegex(RuntimeError, "verrouillé"):
                    self.survie.lancer_partie_survie(self.profil, 1)
            audit.assert_not_called()
        self.assertFalse((self.config.game_path / "systeme/verrou_cycle_survie").exists())

    def test_interruption_timer_preserve_echeance_et_libere_verrou(self):
        self.activer(0)
        avant = self.etat.charger_cycle_survie(self.profil)
        def interrompre(duree):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.survie.lancer_partie_survie(self.profil, 1, lambda: 90, interrompre)
        self.assertEqual(self.etat.charger_cycle_survie(self.profil), avant)
        self.assertEqual(self.etat.lire_compteur_general("bot"), 0)
        self.assertFalse((self.config.game_path / "systeme/verrou_cycle_survie").exists())

    def test_reprise_timer_attend_seulement_temps_restant(self):
        self.activer(0)
        maintenant = [97.0]
        attentes = []
        def attendre(duree):
            attentes.append(duree)
            maintenant[0] += duree
        with patch.object(self.survie, "creer_vague_est", return_value=[]):
            self.survie.lancer_partie_survie(self.profil, 1, lambda: maintenant[0], attendre)
        self.assertEqual(sum(attentes), 3)


if __name__ == "__main__":
    unittest.main()
