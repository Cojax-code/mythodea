"""Configuration des modes et préservation du cycle classique, en isolation."""
import contextlib
import importlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, call, patch


PYTHON_DIR = Path(__file__).resolve().parents[1]


class Modes(unittest.TestCase):
    def setUp(self):
        self.contextes = contextlib.ExitStack()
        self.addCleanup(self.contextes.close)
        self.racine = Path(self.contextes.enter_context(tempfile.TemporaryDirectory()))
        self.contextes.enter_context(patch.object(sys, "path", [str(PYTHON_DIR), *sys.path]))
        self.contextes.enter_context(patch.dict(sys.modules))
        for nom in (
            "config", "etat", "rapports", "generaux", "mouvements",
            "securite", "combats", "plateau", "victoire", "mythodea_v_1_5",
        ):
            sys.modules.pop(nom, None)
        self.config = importlib.import_module("config")
        self.entree = importlib.import_module("mythodea_v_1_5")

    def test_profil_classique_conserve_carte_bases_et_proprietaires(self):
        profil = self.config.configuration_mode("classique")
        self.assertEqual(profil["carte_territoires"], {
            "base1": ["terrain1"], "terrain1": ["base1", "terrain2"],
            "terrain2": ["terrain1", "terrain3"],
            "terrain3": ["terrain2", "base2"], "base2": ["terrain3"],
        })
        self.assertEqual(profil["bases_joueurs"], {"j1": "base1", "j2": "base2"})
        self.assertEqual(profil["game_path"], Path("/home/game"))
        self.assertFalse(profil["emplacements_partages"])
        self.assertIsNone(profil["duree_phase_action_secondes"])
        for joueur in ("j1", "j2"):
            self.assertEqual(profil["acteurs"][joueur], {
                "proprietaire_linux": joueur, "groupe_linux": joueur, "camp": joueur,
            })
        self.assertNotIn("bot", profil["acteurs"])

    def test_survie_est_et_repli_special(self):
        profil = self.config.configuration_mode("survie")
        self.assertEqual(profil["carte_territoires"], {
            "repli": ["village"], "village": ["repli", "est_1"],
            "est_1": ["village", "est_2"], "est_2": ["est_1", "est_3"],
            "est_3": ["est_2"],
        })
        self.assertEqual([p.name for p in profil["territoires"]],
                         ["village", "est_1", "est_2", "est_3"])
        self.assertIn("repli", profil["zones_speciales"])
        self.assertEqual(profil["repli_path"], Path("/home/game/repli"))
        self.assertEqual(profil["bases_joueurs"], {"j1": "village", "j2": "village"})
        self.assertEqual(profil["duree_phase_action_secondes"], 120)
        self.assertEqual(profil["emplacements"], ["1", "2", "3", "4"])
        self.assertTrue(profil["emplacements_partages"])

    def test_alliance_ne_change_pas_les_proprietaires_linux(self):
        profil = self.config.configuration_mode("survie")
        self.assertEqual(profil["joueurs"], ["j1", "j2"])
        for joueur in profil["joueurs"]:
            self.assertEqual(profil["acteurs"][joueur], {
                "proprietaire_linux": joueur, "groupe_linux": joueur, "camp": "allies",
            })
        self.assertEqual(profil["acteurs"]["bot"], {
            "proprietaire_linux": "root", "groupe_linux": "root", "camp": "bot",
        })
        self.assertEqual(profil["permissions_generaux"], {"dossiers": 0o700, "fichiers": 0o600})

    def test_profils_independants_sans_activation_globale(self):
        classique = self.config.configuration_mode("classique")
        classique["carte_territoires"]["base1"].clear()
        classique["bases_joueurs"]["j1"] = "village"
        classique["territoires"].clear()
        survie = self.config.configuration_mode("survie")
        survie["acteurs"]["bot"]["proprietaire_linux"] = "j1"
        survie["joueurs"].append("bot")
        survie["emplacements"].clear()
        self.assertEqual(self.config.carte_territoires["base1"], ["terrain1"])
        self.assertEqual(self.config.bases_joueurs["j1"], "base1")
        self.assertEqual(len(self.config.territoires), 5)
        self.assertEqual(self.config.joueurs, ["j1", "j2"])
        self.assertEqual(self.config.emplacements, ["1", "2", "3", "4"])
        self.assertEqual(self.config.configuration_mode("survie")["acteurs"]["bot"]["proprietaire_linux"], "root")

    def test_mode_inconnu_refuse(self):
        with self.assertRaises(ValueError):
            self.config.configuration_mode("inconnu")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as erreur:
            self.entree.main(["--mode", "inconnu"])
        self.assertEqual(erreur.exception.code, 2)

    def test_selection_classique_implicite_et_explicite(self):
        with patch.object(self.entree, "resoudre_tour_classique") as resoudre:
            self.entree.main([])
            self.entree.main(["--mode", "classique"])
        self.assertEqual(resoudre.call_count, 2)

    def test_configuration_consultable_sans_lancer_de_tour(self):
        for mode in self.config.modes_disponibles:
            with self.subTest(mode=mode):
                sortie = io.StringIO()
                with contextlib.redirect_stdout(sortie), patch.object(self.entree, "resoudre_tour_classique") as resoudre:
                    self.entree.main(["--mode", mode, "--afficher-configuration"])
                self.assertEqual(json.loads(sortie.getvalue())["mode"], mode)
                resoudre.assert_not_called()
                self.assertNotIn("plateau", sys.modules)

    def test_survie_non_jouable_ne_lance_pas_le_moteur_classique(self):
        sortie = io.StringIO()
        with contextlib.redirect_stderr(sortie), patch.object(self.entree, "resoudre_tour_classique") as resoudre:
            with self.assertRaises(SystemExit) as erreur:
                self.entree.main(["--mode", "survie"])
        self.assertEqual(erreur.exception.code, 2)
        self.assertIn("n'est pas encore jouable", sortie.getvalue())
        resoudre.assert_not_called()
        self.assertNotIn("plateau", sys.modules)

    def modules_cycle_simules(self, vainqueur=None):
        journal = Mock()
        fonctions = {
            "rapports": ["preparer_rapports", "ecrire_rapport_court", "ecrire_rapport_long", "afficher_fin_de_tour"],
            "plateau": ["reparer_structure", "lancer_bataille_v15"],
            "generaux": ["faire_apparaitre_general_si_possible"],
            "securite": ["verifier_tous_les_deplacements"],
            "victoire": ["verifier_victoire"],
        }
        for nom, noms_fonctions in fonctions.items():
            module = ModuleType(nom)
            sys.modules[nom] = module
            for fonction in noms_fonctions:
                simulation = Mock()
                setattr(module, fonction, simulation)
                journal.attach_mock(simulation, fonction)
        sys.modules["victoire"].verifier_victoire.return_value = vainqueur
        return journal

    def test_cycle_classique_garde_generation_et_ordre_des_phases(self):
        journal = self.modules_cycle_simules()
        self.entree.main([])
        self.assertEqual(journal.mock_calls, [
            call.preparer_rapports(), call.reparer_structure(),
            call.faire_apparaitre_general_si_possible("j1"),
            call.faire_apparaitre_general_si_possible("j2"),
            call.verifier_tous_les_deplacements(), call.verifier_victoire(),
            call.lancer_bataille_v15(), call.afficher_fin_de_tour(),
        ])

    def test_victoire_classique_conserve_rapports_et_absence_de_bataille(self):
        journal = self.modules_cycle_simules(vainqueur="j2")
        self.entree.main(["--mode", "classique"])
        self.assertEqual(journal.mock_calls[6:], [
            call.ecrire_rapport_court(""), call.ecrire_rapport_court("VICTOIRE DE j2"),
            call.ecrire_rapport_long("Victoire de j2."), call.afficher_fin_de_tour(),
        ])

    def test_reparations_repetees_sans_generation_et_droits_classiques_conserves(self):
        self.contextes.enter_context(patch.dict(sys.modules, {
            "pwd": SimpleNamespace(getpwnam=lambda joueur: SimpleNamespace(pw_uid={"j1": 1001, "j2": 1002}[joueur])),
            "grp": SimpleNamespace(getgrnam=lambda joueur: SimpleNamespace(gr_gid={"j1": 1001, "j2": 1002}[joueur])),
        }))
        plateau = importlib.import_module("plateau")
        generaux = importlib.import_module("generaux")
        self.config.territoires = [self.racine / nom for nom in self.config.carte_territoires]
        self.config.repli_path = self.racine / "repli"
        for territoire in self.config.territoires:
            territoire.mkdir()
        with patch.object(plateau.os, "chown", create=True) as chown, patch.object(plateau.os, "chmod") as chmod, patch.object(generaux, "faire_apparaitre_general_si_possible") as generer:
            plateau.reparer_structure()
            plateau.reparer_structure()
        generer.assert_not_called()
        attendus = []
        for territoire in self.config.territoires:
            for joueur in self.config.joueurs:
                attendus.append((territoire / joueur, joueur))
                attendus.extend((territoire / joueur / place, joueur) for place in self.config.emplacements)
        attendus.extend((self.config.repli_path / joueur, joueur) for joueur in self.config.joueurs)
        for chemin, joueur in attendus:
            self.assertTrue(chemin.is_dir())
            identifiant = {"j1": 1001, "j2": 1002}[joueur]
            self.assertEqual(chown.call_args_list.count(call(chemin, identifiant, identifiant)), 2)
            self.assertEqual(chmod.call_args_list.count(call(chemin, 0o700)), 2)
        self.assertEqual(list(self.racine.rglob("general*")), [])
        self.assertEqual(list(self.racine.rglob("compteur*")), [])


if __name__ == "__main__":
    unittest.main()
