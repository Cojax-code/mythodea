"""Combats communs entre camps, sur des forces préparées sans vagues."""
import contextlib
import importlib
import random
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

from unittest.mock import patch


class CombatsCamps(unittest.TestCase):
    def setUp(self):
        self.contextes = contextlib.ExitStack()
        self.addCleanup(self.contextes.close)
        self.racine = Path(self.contextes.enter_context(tempfile.TemporaryDirectory()))
        self.contextes.enter_context(patch.object(sys, "path", [
            str(Path(__file__).resolve().parents[2] / 'python'), *sys.path,
        ]))
        self.contextes.enter_context(patch.dict(sys.modules, {
            "pwd": ModuleType("pwd"), "grp": ModuleType("grp"),
        }))
        noms = ("config", "etat", "rapports", "generaux", "mouvements",
                "securite", "combats", "plateau")
        for nom in noms:
            sys.modules.pop(nom, None)
        for nom in noms:
            setattr(self, nom, importlib.import_module(nom))
        self.contextes.enter_context(patch.object(self.etat.os, 'chown', create=True))
        self.config.game_path = self.racine / "game"
        self.config.territoires = [self.config.game_path / nom for nom in self.config.carte_territoires]
        for nom, relatif in {
            "positions_generaux_path": "systeme/positions_generaux.txt",
            "fatigue_generaux_path": "systeme/fatigue_generaux.txt",
            "controle_territoires_path": "systeme/controle_territoires.txt",
            "meteo_path": "systeme/meteo.txt", "repli_path": "repli",
            "rapport_dir": "rapport", "rapport_long_path": "rapport/rapport_long.txt",
            "rapport_court_path": "rapport/rapport_court.txt",
            "rapports_territoires_dir": "rapport/territoires",
        }.items():
            setattr(self.config, nom, self.config.game_path / relatif)
        (self.config.game_path / "systeme").mkdir(parents=True)
        self.profil = self.config.configuration_mode("survie")
        self.territoire = self.config.game_path / "est_1"
        self.territoire.mkdir()
        self.aleatoire = random.Random(12)
        self.combats.random = self.aleatoire
        self.generaux.random = self.aleatoire

    def general(self, joueur, nom="general1", place="1", blocs=None, ordre="", territoire=None, profil=None):
        territoire = self.territoire if territoire is None else territoire
        profil = self.profil if profil is None else profil
        zone = next(zone for zone in self.generaux.zones_generaux_territoire(territoire, joueur, profil)
                    if zone.get("emplacement") == place)
        zone["chemin"].mkdir(parents=True, exist_ok=True)
        chemin = zone["chemin"] / nom
        self.generaux.creer_general(chemin, nom)
        (chemin / "ordre.txt").write_text(ordre, encoding="utf-8")
        for bloc, (nombre, equipement) in (blocs or {}).items():
            prefixe = "cavalerie" if equipement == "cheval" else "infanterie"
            for numero in range(1, nombre + 1):
                unite = chemin / bloc / f"{prefixe}{numero}"
                unite.mkdir()
                (unite / equipement).touch()
        positions = self.etat.charger_positions_generaux()
        positions[f"{joueur}:{nom}"] = territoire.name
        self.etat.sauvegarder_positions_generaux(positions)
        self.etat.sauvegarder_compteur_general(joueur, max(
            self.etat.lire_compteur_general(joueur), self.generaux.numero_general_depuis_nom(nom)))
        return chemin

    def forces(self):
        return self.generaux.lire_forces_territoire(self.territoire, self.profil)

    def engagements(self):
        texte = self.config.rapport_long_path.read_text(encoding="utf-8")
        return [ligne for ligne in texte.splitlines() if ligne.startswith("Engagement :")]

    def duel_joueur_bot(self, joueur):
        joueur_path = self.general(joueur, blocs={"avant": (5, "arc")})
        bot_path = self.general("bot", blocs={"avant": (2, "pique")})
        self.combats.resoudre_combat_v15(self.territoire, self.profil)
        self.assertEqual(self.generaux.total_general_depuis_chemin(joueur_path), 4)
        self.assertFalse(bot_path.exists())
        self.assertEqual(self.generaux.controle_forces(self.forces()), "allies")
        self.assertEqual(self.etat.charger_positions_generaux(), {f"{joueur}:general1": "est_1"})

    def test_j1_seul_contre_bot(self):
        self.duel_joueur_bot("j1")

    def test_j2_seul_contre_bot(self):
        self.duel_joueur_bot("j2")

    def test_alliance_ordre_positions_et_relais_independant_du_proprietaire(self):
        for joueur, nom, place in (("j2", "general2", "1"), ("j1", "general2", "2"),
                                   ("j2", "general1", "3"), ("j1", "general1", "4")):
            self.general(joueur, nom, place, {"avant": (1, "arc")})
        bot = self.general("bot", blocs={"avant": (4, "arc")})
        self.combats.resoudre_combat_range(self.territoire, "OFF/OFF", self.profil)
        self.assertEqual(self.engagements(), [
            "Engagement : j2 general2 VS bot general1",
            "Engagement : j1 general2 VS bot general1",
            "Engagement : j2 general1 VS bot general1",
            "Engagement : j1 general1 VS bot general1",
        ])
        self.assertFalse(bot.exists())
        self.assertEqual(self.etat.charger_positions_generaux(), {})
        self.assertEqual(self.generaux.controle_forces(self.forces()), "neutre")

    def test_regroupement_conserve_objets_identites_fiches_ordres_et_unites(self):
        for joueur, nom, place in (("j1", "general1", "1"), ("j2", "general1", "2"),
                                   ("j1", "general2", "3"), ("j2", "general2", "4")):
            self.general(joueur, nom, place, {"avant": (2, "arc")}, "1-2")
        self.etat.sauvegarder_generaux_fatigues({"j2:general1"})
        lecture = self.generaux.lire_generaux_territoire(self.territoire, self.profil)
        forces = self.generaux.regrouper_forces_par_camp(lecture, self.profil)
        for joueur, place in (("j1", "1"), ("j2", "2"), ("j1", "3"), ("j2", "4")):
            general = forces["allies"][place]
            self.assertIs(general, lecture[joueur][place])
            self.assertEqual(general["joueur"], joueur)
            self.assertEqual(general["camp"], "allies")
            self.assertEqual(general["emplacement"], place)
            self.assertIn(joueur, general["chemin"].parts)
            self.assertEqual(general["fiche"]["nom"], general["nom"])
            self.assertEqual(general["ordres"][0]["identifiant"], "1-2")
            self.assertEqual(len(general["blocs"]["avant"]["unites"]), 2)
            self.assertEqual(self.etat.general_est_fatigue(general), place == "2")

    def test_fatigue_appliquee_au_bon_proprietaire_et_identite_survivante_intacte(self):
        for joueur, place in (("j1", "1"), ("j2", "2")):
            self.general(joueur, place=place, blocs={"avant": (5, "arc")})
        self.general("bot", blocs={"avant": (5, "arc")})
        self.etat.sauvegarder_generaux_fatigues({"j1:general1"})
        forces = self.forces()
        resultat = self.combats.combat_entre_generaux(forces["allies"]["1"], forces["bot"]["1"])
        self.assertEqual((resultat["final_1"], resultat["final_2"]), (0, 3))
        self.assertEqual((resultat["joueur_1"], resultat["camp_1"]), ("j1", "allies"))
        self.assertEqual(self.etat.charger_positions_generaux(), {
            "j2:general1": "est_1", "bot:general1": "est_1",
        })
        self.assertEqual(self.etat.lire_compteur_general("j1"), 1)
        forces = self.forces()
        self.assertFalse(self.etat.general_est_fatigue(forces["allies"]["2"]))
        resultat = self.combats.combat_entre_generaux(forces["allies"]["2"], forces["bot"]["1"])
        self.assertEqual((resultat["final_1"], resultat["final_2"]), (2, 0))
        self.assertEqual(self.etat.charger_positions_generaux(), {"j2:general1": "est_1"})

    def test_fatigue_j2_transmise_aux_manoeuvres(self):
        self.general("j2", blocs={"gauche": (5, "arc")})
        self.general("bot", blocs={"arriere": (5, "arc")})
        self.etat.sauvegarder_generaux_fatigues({"j2:general1"})
        forces = self.forces()
        resultat = self.combats.combat_entre_generaux(forces["allies"]["1"], forces["bot"]["1"])
        self.assertEqual(resultat["chocs"], [])
        self.assertEqual((resultat["final_1"], resultat["final_2"]), (0, 3))
        self.assertEqual(resultat["manoeuvres"][0]["joueur_attaquant"], "bot")
        self.assertEqual(resultat["manoeuvres"][0]["joueur_defenseur"], "j2")

    def test_controle_territorial_quatre_etats_et_sauvegarde(self):
        self.assertEqual(self.generaux.controle_forces(self.forces()), "neutre")
        j1 = self.general("j1", blocs={"avant": (1, "arc")})
        j2 = self.general("j2", place="2", blocs={"avant": (1, "arc")})
        self.assertEqual(self.generaux.controle_forces(self.forces()), "allies")
        self.general("bot", blocs={"avant": (1, "arc")})
        lecture = self.generaux.lire_generaux_territoire(self.territoire, self.profil)
        self.assertEqual(self.generaux.controle_territoire_generaux(lecture, self.profil), "conteste")
        for chemin in (j1, j2):
            (chemin / "avant/infanterie1/arc").unlink()
            (chemin / "avant/infanterie1").rmdir()
        self.assertEqual(self.generaux.controle_forces(self.forces()), "bot")
        self.plateau.sauvegarder_controle_territoires(self.profil)
        self.assertEqual(self.etat.charger_controle_territoires(self.profil)["est_1"], "bot")
        self.assertIn("est_1=bot", self.config.controle_territoires_path.read_text(encoding="utf-8"))

    def test_ordre_frontal_allie_declenche_duels_puis_range(self):
        self.general("j1", place="1", blocs={"avant": (5, "arc")})
        self.general("j2", place="2", blocs={"avant": (2, "pique")}, ordre="1-2")
        self.general("bot", place="1", blocs={"avant": (2, "pique")})
        self.general("bot", "general2", "2", {"avant": (5, "arc")})
        self.combats.resoudre_combat_v15(self.territoire, self.profil)
        self.assertEqual(self.engagements(), [
            "Engagement : j1 general1 VS bot general1",
            "Engagement : j2 general1 VS bot general2",
            "Engagement : j1 general1 VS bot general2",
        ])
        self.assertEqual(self.generaux.controle_forces(self.forces()), "neutre")
        rapport = (self.config.rapports_territoires_dir / "est_1.txt").read_text(encoding="utf-8")
        self.assertIn("allies", rapport)
        self.assertIn("j2 general1", rapport)
        self.assertIn("bot general2", rapport)
        self.assertIn("COMBAT RANGÉ", rapport)

    def test_off_def_camps_sans_priorite_de_proprietaire(self):
        self.general("j2", blocs={"avant": (5, "arc")})
        self.general("bot", blocs={"avant": (2, "pique")}, ordre="1-2")
        self.combats.resoudre_combat_off_def(self.territoire, "allies", self.profil)
        journal = self.config.rapport_long_path.read_text(encoding="utf-8")
        self.assertIn("Défenseur : allies | Attaquant : bot", journal)
        self.assertIn("Ordre frontal demandé par : bot", journal)
        self.assertEqual(self.generaux.controle_forces(self.forces()), "allies")

    def test_manoeuvre_cible_avantage_naturel_avant_cible_faible(self):
        self.general("j2", blocs={"avant": (5, "arc")})
        self.general("bot", blocs={"droite": (2, "pique"), "arriere": (1, "cheval")})
        forces = self.forces()
        resultat = self.combats.combat_entre_generaux(forces["allies"]["1"], forces["bot"]["1"])
        premiere = resultat["manoeuvres"][0]
        self.assertEqual((premiere["joueur_attaquant"], premiere["bloc_attaquant"], premiere["bloc_defenseur"]),
                         ("j2", "avant", "droite"))

    def test_noms_des_camps_et_adversaire_non_codes_en_dur(self):
        for joueur in ("j1", "j2"):
            self.profil["acteurs"][joueur]["camp"] = "defenseurs"
        self.profil["acteurs"]["pnj"] = self.profil["acteurs"].pop("bot")
        self.profil["acteurs"]["pnj"]["camp"] = "assaillants"
        self.general("j2", blocs={"gauche": (5, "arc")})
        self.general("pnj", blocs={"arriere": (2, "pique")})
        self.combats.resoudre_combat_v15(self.territoire, self.profil)
        self.assertEqual(self.generaux.controle_forces(self.forces()), "defenseurs")
        self.assertEqual(self.etat.charger_positions_generaux(), {"j2:general1": "est_1"})

    def test_refus_duel_allie_et_collision_non_resolue_sans_pertes(self):
        j1 = self.general("j1", blocs={"avant": (2, "arc")})
        j2 = self.general("j2", blocs={"avant": (2, "arc")})
        lecture = self.generaux.lire_generaux_territoire(self.territoire, self.profil)
        with self.assertRaises(ValueError):
            self.generaux.regrouper_forces_par_camp(lecture, self.profil)
        with self.assertRaises(ValueError):
            self.combats.combat_entre_generaux(lecture["j1"]["1"], lecture["j2"]["1"])
        self.assertEqual([self.generaux.total_general_depuis_chemin(p) for p in (j1, j2)], [2, 2])

    def test_garnison_village_contre_bot_reserve_exclue(self):
        self.territoire = self.config.game_path / "village"
        self.general("j2", blocs={"avant": (5, "arc")})
        self.general("bot", blocs={"avant": (2, "pique")})
        reserve = self.territoire / "j1/reserve/general1"
        reserve.parent.mkdir(parents=True)
        self.generaux.creer_general(reserve, "general1")
        self.assertIsNone(self.forces()["allies"]["2"])
        self.combats.resoudre_combat_v15(self.territoire, self.profil)
        self.assertTrue(reserve.is_dir())
        self.assertEqual(self.generaux.controle_forces(self.forces()), "allies")

    def test_classique_par_defaut_reste_j1_contre_j2(self):
        profil = self.config.configuration_mode("classique")
        territoire = self.config.game_path / "terrain1"
        j1 = self.general("j1", blocs={"avant": (5, "arc")}, territoire=territoire, profil=profil)
        j2 = self.general("j2", blocs={"avant": (2, "pique")}, territoire=territoire, profil=profil)
        self.combats.resoudre_combat_v15(territoire)
        self.assertEqual(self.generaux.total_general_depuis_chemin(j1), 4)
        self.assertFalse(j2.exists())
        self.assertEqual(self.generaux.controle_territoire_generaux(
            self.generaux.lire_generaux_territoire(territoire)), "j1")
        rapport = (self.config.rapports_territoires_dir / "terrain1.txt").read_text(encoding="utf-8")
        self.assertIn("j1 general1 <-> j2 general1", rapport)
        self.assertNotIn("allies", rapport)

    def test_reserve_armee_ne_conteste_pas_le_controle_du_bot(self):
        self.territoire = self.config.game_path / "village"
        general = self.general("j1", blocs={"avant": (5, "arc")}, ordre="1-2")
        reserve = self.territoire / "j1/reserve/general1"
        reserve.parent.mkdir(parents=True)
        general.rename(reserve)
        self.assertEqual(self.generaux.controle_forces(self.forces()), "neutre")

        bot = self.general("bot", blocs={"avant": (2, "pique")})
        positions = self.etat.charger_positions_generaux()
        self.combats.resoudre_combat_v15(self.territoire, self.profil)
        self.assertEqual(self.engagements(), [])
        self.assertEqual(self.generaux.total_general_depuis_chemin(reserve), 5)
        self.assertEqual(self.generaux.total_general_depuis_chemin(bot), 2)
        self.assertEqual(self.etat.charger_positions_generaux(), positions)
        self.plateau.sauvegarder_controle_territoires(self.profil)
        self.assertEqual(self.etat.charger_controle_territoires(self.profil)["village"], "bot")

    def test_bot_defenseur_et_rapport_manoeuvre_contre_j2(self):
        self.general("j2", blocs={"gauche": (5, "arc")})
        self.general("bot", blocs={"arriere": (5, "arc")})
        self.etat.sauvegarder_generaux_fatigues({"j2:general1"})
        self.combats.resoudre_combat_off_def(self.territoire, "bot", self.profil)
        journal = self.config.rapport_long_path.read_text(encoding="utf-8")
        self.assertIn("Défenseur : bot | Attaquant : allies", journal)
        self.assertEqual(self.generaux.controle_forces(self.forces()), "bot")
        rapport = (self.config.rapports_territoires_dir / "est_1.txt").read_text(encoding="utf-8")
        self.assertIn("j2 general1 <-> bot general1", rapport)
        self.assertIn("Bloc j2", rapport)
        self.assertIn("Bloc bot", rapport)
        self.assertIn("j2 (0) / bot (3)", rapport)
        manoeuvre = next(ligne for ligne in rapport.splitlines() if ligne.startswith("| M1"))
        self.assertIn("gauche", manoeuvre)
        self.assertIn("arriere", manoeuvre)
        self.assertIn("<-", manoeuvre)
        self.assertNotIn("j1", rapport)


if __name__ == "__main__":
    unittest.main()
