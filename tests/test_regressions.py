"""Tests isolés : aucun accès au plateau réel, aucun changement de droits Linux.

Le moteur exécute encore un tour à l'import. On charge donc uniquement ses
déclarations par AST, sans changer son point d'entrée dans ce correctif.
"""
import ast
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "mythodea_v_1_5.py"


class Regressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mythodea_test_")
        self.addCleanup(self.temp.cleanup)
        racine = Path(self.temp.name)

        class CheminTest(type(Path())):
            @staticmethod
            def rediriger(args):
                if args and isinstance(args[0], str):
                    if args[0] == "/home" or args[0].startswith("/home/"):
                        args = (str(racine / args[0].lstrip("/")), *args[1:])
                return args

            def __new__(cls, *args, **kwargs):
                return super().__new__(cls, *cls.rediriger(args), **kwargs)

            def __init__(self, *args, **kwargs):
                if sys.version_info >= (3, 12):
                    super().__init__(*self.rediriger(args), **kwargs)

        arbre = ast.parse(SOURCE.read_text(encoding="utf-8"))
        declarations = []
        for noeud in arbre.body:
            if isinstance(noeud, ast.Expr) and isinstance(noeud.value, ast.Call):
                break  # preparer_rapports() : début du vrai tour
            if isinstance(noeud, ast.Import):
                if any(alias.name in {"pwd", "grp"} for alias in noeud.names):
                    continue
            declarations.append(noeud)
        self.m = {}
        exec(compile(ast.Module(body=declarations, type_ignores=[]), str(SOURCE), "exec"), self.m)
        self.m["Path"] = CheminTest
        jeu = CheminTest("/home/game")
        self.assertTrue(jeu.is_relative_to(racine))
        self.assertTrue(CheminTest("/home/j1").is_relative_to(racine))
        self.m["game_path"] = jeu
        self.m["territoires"] = [jeu / nom for nom in self.m["carte_territoires"]]
        for nom, relatif in {
            "positions_generaux_path": "systeme/positions_generaux.txt",
            "fatigue_generaux_path": "systeme/fatigue_generaux.txt",
            "controle_territoires_path": "systeme/controle_territoires.txt",
            "meteo_path": "systeme/meteo.txt",
            "repli_path": "repli",
            "rapport_dir": "rapport",
            "rapport_court_path": "rapport/rapport_court.txt",
            "rapport_long_path": "rapport/rapport_long.txt",
            "rapports_territoires_dir": "rapport/territoires",
        }.items():
            self.m[nom] = jeu / relatif
        (jeu / "systeme").mkdir(parents=True)
        for joueur in self.m["joueurs"]:
            CheminTest(f"/home/{joueur}").mkdir(parents=True)
            (jeu / "repli" / joueur).mkdir(parents=True)
            for territoire in self.m["territoires"]:
                for emplacement in self.m["emplacements"]:
                    (territoire / joueur / emplacement).mkdir(parents=True)
        self.m["donner_permissions_general"] = lambda *args: None
        self.m["joueur_proprietaire_chemin"] = lambda chemin: next(
            joueur for joueur in self.m["joueurs"] if joueur in chemin.parts
        )
        self.m["random"] = random.Random(12)

    def general(self, joueur="j1", nom="general1", territoire="base1", emplacement="1"):
        chemin = self.m["game_path"] / territoire / joueur / emplacement / nom
        self.m["creer_general"](chemin, nom)
        return chemin

    def autoriser(self, joueur="j1", nom="general1", position="base1", compteur=1):
        self.m["sauvegarder_compteur_general"](joueur, compteur)
        positions = self.m["charger_positions_generaux"]()
        positions[f"{joueur}:{nom}"] = position
        self.m["sauvegarder_positions_generaux"](positions)

    def unite(self, general, bloc, nom, equipement):
        unite = general / bloc / nom
        unite.mkdir()
        (unite / equipement).touch()
        return unite

    def armee_manoeuvre(self, effectifs):
        return {
            joueur: {
                bloc: {"type": "archer" if nombres.get(bloc, 0) else "vide",
                       "nombre": nombres.get(bloc, 0), "unites": []}
                for bloc in self.m["ordre_blocs"]
            }
            for joueur, nombres in effectifs.items()
        }

    def test_sequence_globale_exemple_priorite_blocs(self):
        armee = self.armee_manoeuvre({
            "j1": {"avant": 3, "gauche": 4},
            "j2": {"avant": 2, "droite": 3, "arriere": 2},
        })
        actions = self.m["ordre_actions_manoeuvre"](armee, {"j1": False, "j2": False})
        self.assertEqual(actions[:3], [("j2", "arriere"), ("j1", "gauche"), ("j2", "droite")])
        self.assertEqual(set(actions[3:]), {("j1", "avant"), ("j2", "avant")})
        self.assertEqual(len(actions), len(set(actions)))

    def test_avant_libre_prioritaire_et_jamais_ajoute_deux_fois(self):
        armee = self.armee_manoeuvre({
            "j1": {"arriere": 10, "gauche": 4},
            "j2": {"avant": 1, "droite": 3},
        })
        actions = self.m["ordre_actions_manoeuvre"](armee, {"j1": False, "j2": True})
        self.assertEqual(actions, [("j2", "avant"), ("j1", "arriere"), ("j1", "gauche"), ("j2", "droite")])

    def test_flancs_ordonnes_par_effectifs_entre_les_deux_camps(self):
        armee = self.armee_manoeuvre({
            "j1": {"droite": 2, "gauche": 5},
            "j2": {"droite": 4, "gauche": 3},
        })
        actions = self.m["ordre_actions_manoeuvre"](armee, {"j1": False, "j2": False})
        self.assertEqual(actions, [("j1", "gauche"), ("j2", "droite"), ("j2", "gauche"), ("j1", "droite")])

    def test_flancs_egaux_sans_priorite_permanente_j1(self):
        armee = self.armee_manoeuvre({"j1": {"gauche": 3}, "j2": {"droite": 3}})
        premiers = set()
        for graine in range(20):
            self.m["random"].seed(graine)
            actions = self.m["ordre_actions_manoeuvre"](armee, {"j1": False, "j2": False})
            self.assertEqual(set(actions), {("j1", "gauche"), ("j2", "droite")})
            premiers.add(actions[0][0])
        self.assertEqual(premiers, {"j1", "j2"})

    def test_choc_initial_ne_laisse_pas_de_vis_a_vis(self):
        # Vérifie le fondement de la règle, avec les effectifs et fatigues possibles.
        for type_1 in ["archer", "piquier", "cavalier"]:
            for type_2 in ["archer", "piquier", "cavalier"]:
                for n1 in range(1, 21):
                    for n2 in range(1, 21):
                        for fatigue_1, fatigue_2 in [(False, False), (True, False), (False, True), (True, True)]:
                            survivants = self.m["combat_bloc"](
                                {"type": type_1, "nombre": n1},
                                {"type": type_2, "nombre": n2},
                                fatigue_1, fatigue_2,
                            )
                            self.assertIn(0, survivants)

    def test_bataille_j2_arriere_prioritaire_et_bloc_detruit_ignore(self):
        j1 = self.general(territoire="terrain1")
        j2 = self.general("j2", territoire="terrain1")
        for joueur in ["j1", "j2"]:
            self.autoriser(joueur, position="terrain1")
        for general, bloc, nombre, prefixe, equipement in [
            (j1, "gauche", 3, "infanterie", "arc"),
            (j1, "droite", 2, "infanterie", "pique"),
            (j2, "arriere", 5, "cavalerie", "cheval"),
        ]:
            for n in range(nombre):
                self.unite(general, bloc, f"{prefixe}{n}", equipement)
        self.m["preparer_rapports"]()
        self.m["verifier_tous_les_deplacements"]()
        self.m["lancer_bataille_v15"]()
        rapport = (self.m["rapports_territoires_dir"] / "terrain1.txt").read_text(encoding="utf-8")
        manoeuvres = [ligne for ligne in rapport.splitlines() if ligne.startswith(("| M1 ", "| M2 ", "| M3 "))]
        self.assertEqual(len(manoeuvres), 2)
        self.assertIn("M1", manoeuvres[0])
        self.assertIn("arriere", manoeuvres[0])
        self.assertIn("gauche", manoeuvres[0])
        self.assertIn("<-", manoeuvres[0])
        self.assertIn("droite", manoeuvres[1])
        self.assertIn("->", manoeuvres[1])
        self.assertIn("4 cavaliers", manoeuvres[1])
        self.assertFalse(j1.exists())
        self.assertFalse(j2.exists())
        journal = self.m["rapport_long_path"].read_text(encoding="utf-8")
        self.assertIn("Ordre global de manœuvre : j2 arriere, j1 gauche, j1 droite", journal)

    def test_detection_avant_libre_j2_et_priorite_reelle(self):
        j1 = self.general(territoire="terrain1")
        j2 = self.general("j2", territoire="terrain1")
        for joueur in ["j1", "j2"]:
            self.autoriser(joueur, position="terrain1")
        for n in range(3):
            self.unite(j1, "arriere", f"infanterie{n}", "arc")
        for n in range(5):
            self.unite(j2, "avant", f"cavalerie{n}", "cheval")
        generaux = self.m["lire_generaux_territoire"](self.m["game_path"] / "terrain1")
        resultat = self.m["combat_entre_generaux"](generaux["j1"]["1"], generaux["j2"]["1"])
        self.assertEqual(resultat["chocs"], [])
        self.assertEqual(len(resultat["manoeuvres"]), 1)
        action = resultat["manoeuvres"][0]
        self.assertEqual((action["joueur_attaquant"], action["bloc_attaquant"]), ("j2", "avant"))
        self.assertEqual((resultat["final_1"], resultat["final_2"]), (0, 4))

    def test_avant_engage_survivant_ne_devient_pas_avant_libre(self):
        j1 = self.general(territoire="terrain1")
        j2 = self.general("j2", territoire="terrain1")
        for joueur in ["j1", "j2"]:
            self.autoriser(joueur, position="terrain1")
        for general, bloc, nombre, prefixe, equipement in [
            (j1, "avant", 5, "infanterie", "arc"),
            (j2, "avant", 3, "infanterie", "pique"),
            (j2, "arriere", 3, "cavalerie", "cheval"),
        ]:
            for n in range(nombre):
                self.unite(general, bloc, f"{prefixe}{n}", equipement)
        generaux = self.m["lire_generaux_territoire"](self.m["game_path"] / "terrain1")
        resultat = self.m["combat_entre_generaux"](generaux["j1"]["1"], generaux["j2"]["1"])
        self.assertEqual(len(resultat["chocs"]), 1)
        self.assertEqual(resultat["chocs"][0]["final_1"], 4)
        action = resultat["manoeuvres"][0]
        self.assertEqual((action["joueur_attaquant"], action["bloc_attaquant"]), ("j2", "arriere"))
        self.assertEqual((resultat["final_1"], resultat["final_2"]), (0, 1))

    def tour_sans_generation(self):
        """Résout les armées préparées, sans créer de nouveaux généraux."""
        self.m["preparer_rapports"]()
        self.m["verifier_tous_les_deplacements"]()
        self.m["lancer_bataille_v15"]()
        self.assertNotIn("conteste", self.m["charger_controle_territoires"]().values())
        for identifiant, position in self.m["charger_positions_generaux"]().items():
            joueur, nom = identifiant.split(":")
            position_reelle, chemin = self.m["trouver_position_general"](joueur, nom)
            self.assertEqual(position_reelle, position)
            self.assertTrue(chemin.is_dir())

    def engagements_journal(self):
        return [
            ligne for ligne in self.m["rapport_long_path"].read_text(encoding="utf-8").splitlines()
            if ligne.startswith("Engagement :")
        ]

    def test_selection_range_par_emplacement_et_relais_apres_destruction(self):
        # Les numéros des généraux sont volontairement dans le désordre.
        scenario = [
            ("j1", "general2", "1", 0),  # vide : ne doit pas être sélectionné
            ("j1", "general3", "2", 2),
            ("j1", "general1", "4", 6),
            ("j2", "general2", "1", 4),
            ("j2", "general1", "3", 1),
        ]
        for joueur, nom, emplacement, nombre in scenario:
            general = self.general(joueur, nom, "terrain1", emplacement)
            self.autoriser(joueur, nom, "terrain1", compteur=3)
            (general / "ordre.txt").write_text("", encoding="utf-8")
            for n in range(nombre):
                self.unite(general, "avant", f"infanterie{n}", "arc")
        self.tour_sans_generation()
        self.assertEqual(self.engagements_journal(), [
            "Engagement : j1 general3 VS j2 general2",
            "Engagement : j1 general1 VS j2 general2",
            "Engagement : j1 general1 VS j2 general1",
        ])
        survivant = self.m["game_path"] / "terrain1/j1/4/general1"
        self.assertEqual(self.m["total_general_depuis_chemin"](survivant), 3)
        self.assertEqual(self.m["charger_controle_territoires"]()["terrain1"], "j1")

    def test_transition_frontal_vers_range_avec_survivants_des_deux_camps(self):
        for joueur, nom, emplacement, nombre, equipement in [
            ("j1", "general1", "1", 5, "arc"),
            ("j2", "general1", "1", 2, "pique"),
            ("j1", "general2", "2", 2, "pique"),
            ("j2", "general2", "2", 5, "arc"),
        ]:
            general = self.general(joueur, nom, "terrain1", emplacement)
            self.autoriser(joueur, nom, "terrain1", compteur=2)
            for n in range(nombre):
                self.unite(general, "avant", f"infanterie{n}", equipement)
        self.tour_sans_generation()
        self.assertEqual(self.engagements_journal(), [
            "Engagement : j1 general1 VS j2 general1",
            "Engagement : j1 general2 VS j2 general2",
            "Engagement : j1 general1 VS j2 general2",
        ])
        self.assertEqual(self.m["charger_positions_generaux"](), {})
        self.assertEqual(self.m["charger_controle_territoires"]()["terrain1"], "neutre")
        rapport = (self.m["rapports_territoires_dir"] / "terrain1.txt").read_text(encoding="utf-8")
        self.assertIn("COMBAT RANGÉ", rapport)
        self.assertIn("4 → 0", rapport)
        self.assertNotIn("Aucun combat rangé.", rapport)

    def test_frontal_termine_sans_range_si_un_camp_disparait(self):
        for joueur, nombre in [("j1", 5), ("j2", 2)]:
            general = self.general(joueur, territoire="terrain1")
            self.autoriser(joueur, position="terrain1")
            for n in range(nombre):
                self.unite(general, "avant", f"infanterie{n}", "arc")
        self.tour_sans_generation()
        self.assertEqual(len(self.engagements_journal()), 1)
        rapport = (self.m["rapports_territoires_dir"] / "terrain1.txt").read_text(encoding="utf-8")
        self.assertIn("Aucun combat rangé.", rapport)

    def test_regles_deplacement_symetriques_pour_les_deux_joueurs(self):
        for joueur, base, voisin, deux, loin, intermediaire, ennemi in [
            ("j1", "base1", "terrain1", "terrain2", "terrain3", "terrain1", "j2"),
            ("j2", "base2", "terrain3", "terrain2", "terrain1", "terrain3", "j1"),
        ]:
            cas = [
                (base, base, {}, True, False),
                (base, voisin, {}, True, False),
                (base, deux, {intermediaire: "neutre"}, True, True),
                (base, deux, {intermediaire: joueur}, True, True),
                (base, deux, {intermediaire: ennemi}, False, False),
                (base, loin, {}, False, False),
                ("home", base, {}, True, False),
                ("home", voisin, {}, False, False),
                ("repli", base, {}, True, False),
                ("repli", voisin, {}, False, False),
                (base, "home", {}, False, False),
                (base, "repli", {}, False, False),
            ]
            for origine, destination, controle, valide, fatigue in cas:
                with self.subTest(joueur=joueur, origine=origine, destination=destination, controle=controle):
                    resultat = self.m["verifier_deplacement_general"](joueur, origine, destination, controle)
                    self.assertEqual(resultat[:2], (valide, fatigue))

    def test_deplacement_trop_long_repli_puis_retour_base(self):
        general = self.general()
        self.autoriser()
        self.unite(general, "avant", "infanterie1", "arc")
        destination = self.m["game_path"] / "terrain3/j1/1/general1"
        general.rename(destination)
        self.tour_sans_generation()
        repli = self.m["repli_path"] / "j1/general1"
        self.assertFalse(destination.exists())
        self.assertTrue((repli / "avant/infanterie1/arc").is_file())
        self.assertEqual(self.m["charger_positions_generaux"](), {"j1:general1": "repli"})
        self.assertEqual(self.m["charger_generaux_fatigues"](), set())
        repli.rename(general)
        self.tour_sans_generation()
        self.assertEqual(self.m["charger_positions_generaux"](), {"j1:general1": "base1"})
        self.assertEqual(self.m["charger_controle_territoires"]()["base1"], "j1")

    def test_marche_forcee_intermediaire_ennemi_sanctionnee(self):
        general = self.general()
        self.autoriser()
        self.unite(general, "avant", "infanterie1", "arc")
        self.m["controle_territoires_path"].write_text("terrain1=j2", encoding="utf-8")
        destination = self.m["game_path"] / "terrain2/j1/1/general1"
        general.rename(destination)
        self.tour_sans_generation()
        self.assertFalse(destination.exists())
        self.assertEqual(self.m["charger_positions_generaux"]()["j1:general1"], "repli")
        self.assertEqual(self.m["charger_generaux_fatigues"](), set())
        self.assertIn("terrain1 est contrôlé par j2", self.m["rapport_long_path"].read_text(encoding="utf-8"))

    def test_marche_forcee_fatigue_recuperation_et_positions_sur_trois_tours(self):
        general = self.general()
        self.autoriser()
        self.unite(general, "avant", "infanterie1", "arc")
        self.tour_sans_generation()
        destination = self.m["game_path"] / "terrain2/j1/1/general1"
        general.rename(destination)
        self.tour_sans_generation()
        self.assertEqual(self.m["charger_generaux_fatigues"](), {"j1:general1"})
        self.assertEqual(self.m["charger_positions_generaux"]()["j1:general1"], "terrain2")
        controle = self.m["charger_controle_territoires"]()
        self.assertEqual((controle["base1"], controle["terrain2"]), ("neutre", "j1"))
        self.assertIn("MARCHE FORCÉE", self.m["rapport_long_path"].read_text(encoding="utf-8"))
        self.tour_sans_generation()  # immobile : fatigue effacée au tour suivant
        self.assertEqual(self.m["charger_generaux_fatigues"](), set())
        self.assertEqual(self.m["charger_positions_generaux"]()["j1:general1"], "terrain2")
        self.assertEqual(self.m["total_general_depuis_chemin"](destination), 1)

    def test_fatigue_de_marche_forcee_transmise_au_combat(self):
        j1 = self.general()
        j2 = self.general("j2", territoire="terrain2")
        self.autoriser()
        self.autoriser("j2", position="terrain2")
        for general in [j1, j2]:
            for n in range(5):
                self.unite(general, "avant", f"infanterie{n}", "arc")
        self.m["controle_territoires_path"].write_text("terrain2=j2", encoding="utf-8")
        destination = self.m["game_path"] / "terrain2/j1/1/general1"
        j1.rename(destination)
        self.tour_sans_generation()
        # Même type et même effectif : le camp frais garde 3 unités.
        self.assertFalse(destination.exists())
        self.assertEqual(self.m["total_general_depuis_chemin"](j2), 3)
        self.assertEqual(self.m["charger_positions_generaux"](), {"j2:general1": "terrain2"})
        rapport = (self.m["rapports_territoires_dir"] / "terrain2.txt").read_text(encoding="utf-8")
        self.assertIn("OFF/DEF (j2 défend)", rapport)
        self.assertIn("5 → 3", rapport)
        self.tour_sans_generation()
        self.assertEqual(self.m["charger_generaux_fatigues"](), set())
        self.assertEqual(self.m["total_general_depuis_chemin"](j2), 3)

    def test_conflit_emplacement_envoie_tous_les_generaux_au_repli(self):
        for numero in [1, 2]:
            nom = f"general{numero}"
            general = self.general(nom=nom)
            self.autoriser(nom=nom, compteur=2)
            self.unite(general, "avant", "infanterie1", "arc")
        self.tour_sans_generation()
        self.assertEqual(self.m["charger_positions_generaux"](), {
            "j1:general1": "repli", "j1:general2": "repli",
        })
        for numero in [1, 2]:
            self.assertTrue((self.m["repli_path"] / f"j1/general{numero}/avant/infanterie1/arc").is_file())
        self.assertEqual(self.m["charger_controle_territoires"]()["base1"], "neutre")

    def test_surplus_reel_supprime_arriere_puis_gauche(self):
        general = self.general()
        self.autoriser()
        for bloc, nombre in [("avant", 10), ("droite", 7), ("gauche", 5), ("arriere", 3)]:
            for n in range(nombre):
                self.unite(general, bloc, f"infanterie{n}", "arc")
        self.tour_sans_generation()
        blocs = self.m["lire_blocs_general"](general)
        self.assertEqual({bloc: infos["nombre"] for bloc, infos in blocs.items()}, {
            "avant": 10, "droite": 7, "gauche": 3, "arriere": 0,
        })
        self.assertEqual(self.m["total_unites_general"](blocs), 20)
        self.assertIn("25/20", self.m["rapport_long_path"].read_text(encoding="utf-8"))
        self.tour_sans_generation()
        self.assertEqual(self.m["total_general_depuis_chemin"](general), 20)

    def test_noms_canoniques(self):
        for nom in ["general01", "general001", "general0", "general", "general-1", "general١", "general²"]:
            with self.subTest(nom=nom):
                self.assertIsNone(self.m["numero_general_depuis_nom"](nom))
                self.assertFalse(self.m["est_general_valide"](self.general(nom=nom)))
        self.assertEqual(self.m["numero_general_depuis_nom"]("general1"), 1)
        self.assertEqual(self.m["numero_general_depuis_nom"]("general15"), 15)

    def test_alias_supprimes_dans_toutes_les_zones(self):
        self.autoriser()
        vrai = self.general()
        faux = [self.general(nom="general01", emplacement="2")]
        for zone in [self.m["Path"]("/home/j1"), self.m["repli_path"] / "j1"]:
            chemin = zone / "general001"
            self.m["creer_general"](chemin, chemin.name)
            faux.append(chemin)
        self.m["supprimer_generaux_non_autorises"]()
        self.assertTrue(vrai.exists())
        self.assertTrue(all(not chemin.exists() for chemin in faux))

    def test_general_detruit_ne_revient_pas_au_tour_suivant(self):
        self.autoriser()
        self.autoriser(joueur="j2", position="base2")
        chemin = self.general()
        self.assertTrue(self.m["supprimer_general_si_vide"]({"chemin": chemin, "joueur": "j1", "nom": "general1"}))
        positions = self.m["charger_positions_generaux"]()
        self.assertNotIn("j1:general1", positions)
        self.assertIn("j2:general1", positions)
        self.assertEqual(self.m["lire_compteur_general"]("j1"), 1)
        copie = self.general(territoire="terrain3")
        self.m["verifier_tous_les_deplacements"]()
        self.assertFalse(copie.exists())
        self.assertNotIn("j1:general1", self.m["charger_positions_generaux"]())

    def test_sans_position_officielle_refuse(self):
        self.m["sauvegarder_compteur_general"]("j1", 1)
        copie = self.general(territoire="terrain3")
        self.m["verifier_tous_les_deplacements"]()
        self.assertFalse(copie.exists())

    def test_resurrection_chez_adversaire_refusee_avant_sanction(self):
        self.m["sauvegarder_compteur_general"]("j1", 1)
        copie = self.general(joueur="j2")
        with patch.dict(self.m, {"joueur_proprietaire_chemin": lambda chemin: "j1"}):
            self.m["verifier_tous_les_deplacements"]()
        self.assertFalse(copie.exists())
        self.assertFalse((self.m["repli_path"] / "j1" / "general1").exists())

    def test_generation_et_deploiement_restent_valides(self):
        self.m["faire_apparaitre_general_si_possible"]("j1")
        home = self.m["Path"]("/home/j1/general1")
        self.assertTrue(home.exists())
        self.assertEqual(self.m["charger_positions_generaux"]()["j1:general1"], "home")
        destination = self.m["game_path"] / "base1/j1/1/general1"
        home.rename(destination)
        self.m["verifier_tous_les_deplacements"]()
        self.assertTrue(destination.exists())
        self.assertEqual(self.m["charger_positions_generaux"]()["j1:general1"], "base1")
        self.m["faire_apparaitre_general_si_possible"]("j1")
        self.assertTrue(self.m["Path"]("/home/j1/general2").exists())

    def test_duplication_et_repli_conservent_identite(self):
        self.autoriser()
        self.general()
        self.general(territoire="terrain1")
        self.m["verifier_tous_les_deplacements"]()
        repli = self.m["repli_path"] / "j1/general1"
        self.assertTrue(repli.exists())
        self.assertEqual(self.m["charger_positions_generaux"]()["j1:general1"], "repli")
        destination = self.m["game_path"] / "base1/j1/1/general1"
        repli.rename(destination)
        self.m["verifier_tous_les_deplacements"]()
        self.assertTrue(destination.exists())

    def test_general_vivant_conserve_sa_position(self):
        self.autoriser()
        chemin = self.general()
        self.unite(chemin, "avant", "infanterie1", "arc")
        self.assertFalse(self.m["supprimer_general_si_vide"]({"chemin": chemin, "joueur": "j1", "nom": "general1"}))
        self.assertEqual(self.m["charger_positions_generaux"]()["j1:general1"], "base1")

    def test_bataille_4v4_manoeuvres_et_identites(self):
        for numero in range(1, 5):
            for joueur, bloc, nombre, equipement in [
                ("j1", "avant", 5, "arc"),
                ("j2", "droite", 3, "pique"),
            ]:
                nom = f"general{numero}"
                general = self.general(joueur, nom, "terrain1", str(numero))
                self.autoriser(joueur, nom, "terrain1", compteur=4)
                for n in range(nombre):
                    self.unite(general, bloc, f"infanterie{n + 1}", equipement)
        self.m["preparer_rapports"]()
        self.m["verifier_tous_les_deplacements"]()
        self.m["lancer_bataille_v15"]()
        rapport = (self.m["rapports_territoires_dir"] / "terrain1.txt").read_text(encoding="utf-8")
        self.assertIn("OFF/OFF", rapport)
        self.assertIn("| M1", rapport)
        generaux = self.m["lire_generaux_territoire"](self.m["game_path"] / "terrain1")
        self.assertEqual(self.m["total_unites_joueur_generaux"](generaux, "j1"), 16)
        self.assertEqual(self.m["total_unites_joueur_generaux"](generaux, "j2"), 0)
        self.assertEqual(set(self.m["charger_positions_generaux"]()), {f"j1:general{n}" for n in range(1, 5)})
        self.assertEqual(self.m["charger_controle_territoires"]()["terrain1"], "j1")

    def test_combat_range_off_def_et_general_survivant(self):
        general = self.general(territoire="terrain1")
        self.autoriser(position="terrain1")
        for n in range(10):
            self.unite(general, "avant", f"infanterie{n + 1}", "arc")
        for numero, emplacement in [(1, "3"), (2, "4")]:
            nom = f"general{numero}"
            adversaire = self.general("j2", nom, "terrain1", emplacement)
            self.autoriser("j2", nom, "terrain1", compteur=2)
            for n in range(2):
                self.unite(adversaire, "avant", f"infanterie{n + 1}", "pique")
        self.m["controle_territoires_path"].write_text("terrain1=j1", encoding="utf-8")
        self.m["preparer_rapports"]()
        self.m["verifier_tous_les_deplacements"]()
        self.m["lancer_bataille_v15"]()
        rapport = (self.m["rapports_territoires_dir"] / "terrain1.txt").read_text(encoding="utf-8")
        self.assertIn("OFF/DEF", rapport)
        self.assertIn("--- Engagement 2", rapport)
        self.assertIn("9 → 8", rapport)
        self.assertNotIn("Aucun combat rangé.", rapport)
        self.assertEqual(self.m["total_general_depuis_chemin"](general), 8)
        self.assertEqual(self.m["charger_positions_generaux"](), {"j1:general1": "terrain1"})

    def test_bloc_mixte_majoritaire_independant_ordre_lecture(self):
        general = self.general()
        minoritaire = self.unite(general, "avant", "infanterie1", "arc")
        majoritaires = [self.unite(general, "avant", f"cavalerie{n}", "cheval") for n in range(1, 5)]
        bloc = self.m["lire_blocs_general"](general)["avant"]
        self.assertEqual((bloc["type"], bloc["nombre"]), ("cavalier", 4))
        self.assertEqual(set(bloc["unites"]), set(majoritaires))
        self.assertFalse(minoritaire.exists())
        self.assertEqual(self.m["lire_blocs_general"](general)["avant"], bloc)

    def test_egalite_en_tete_vide_tout_le_bloc(self):
        general = self.general()
        for bloc, effectifs in [("avant", (2, 2, 1)), ("droite", (1, 1, 1))]:
            for equipement, nombre in zip(["arc", "pique", "cheval"], effectifs):
                prefixe = "cavalerie" if equipement == "cheval" else "infanterie"
                for n in range(nombre):
                    self.unite(general, bloc, f"{prefixe}_{equipement}{n}", equipement)
        intacte = self.unite(general, "gauche", "infanterie1", "arc")
        blocs = self.m["lire_blocs_general"](general)
        for bloc in ["avant", "droite"]:
            self.assertEqual(blocs[bloc], {"type": "vide", "nombre": 0, "unites": []})
            self.assertEqual(list((general / bloc).iterdir()), [])
        self.assertTrue(intacte.exists())
        self.assertIn("égalité", self.m["rapport_long_path"].read_text(encoding="utf-8"))

    def test_nettoyage_mixte_avant_limite_de_20(self):
        general = self.general()
        for n in range(15):
            self.unite(general, "avant", f"infanterie{n}", "arc")
        for n in range(7):
            self.unite(general, "avant", f"cavalerie{n}", "cheval")
        for n in range(5):
            self.unite(general, "arriere", f"infanterie{n}", "pique")
        (general / "avant" / "invalide").touch()
        self.m["verifier_limite_unites_general"](general)
        blocs = self.m["lire_blocs_general"](general)
        self.assertEqual(blocs["avant"]["nombre"], 15)
        self.assertEqual(blocs["arriere"]["nombre"], 5)
        self.assertEqual(self.m["total_unites_general"](blocs), 20)

    def test_bataille_bloc_mixte_rapport_compte_uniquement_majorite(self):
        general = self.general(territoire="terrain1")
        self.autoriser(position="terrain1")
        self.unite(general, "avant", "cavalerie1", "cheval")
        for n in range(5):
            self.unite(general, "avant", f"infanterie{n}", "arc")
        adversaire = self.general("j2", territoire="terrain1")
        self.autoriser("j2", position="terrain1")
        for n in range(3):
            self.unite(adversaire, "avant", f"infanterie{n}", "pique")
        self.m["preparer_rapports"]()
        self.m["verifier_tous_les_deplacements"]()
        self.m["lancer_bataille_v15"]()
        rapport = (self.m["rapports_territoires_dir"] / "terrain1.txt").read_text(encoding="utf-8")
        self.assertIn("Forces initiales : j1 = 5 | j2 = 3", rapport)
        self.assertIn("5 → 4", rapport)
        self.assertEqual(self.m["total_general_depuis_chemin"](general), 4)
        self.assertFalse(adversaire.exists())
        self.assertIn("non cohérente", self.m["rapport_long_path"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
