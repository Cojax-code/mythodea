"""API et pages statiques explicitement autorisées, sans exposition du dépôt."""
import logging
from pathlib import Path
import threading

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge, UnsupportedMediaType

from .runner import Runner, SimulationTimeout, SimulationUnavailable
from .schema import CATALOG, LOCK, InvalidConfiguration, validate, validate_generation

ROOT = Path(__file__).resolve().parents[1]


def create_app(runner=None):
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 8192
    app.config["TRUSTED_HOSTS"] = ["localhost", "127.0.0.1", "[::1]"]
    engine = runner or Runner()
    slot = threading.BoundedSemaphore(1)

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/simulator/catalog")
    def catalog():
        return jsonify(**CATALOG, engine_commit=LOCK["commit"], max_generals_per_camp=4, modes=["OFF/OFF", "OFF/DEF"],
                       conditions={"mode": "OFF/OFF", "fatigue": False, "orders": [],
                                   'reinforcements': False, 'retreats': False, 'value_floor_percent': 1})

    @app.post("/api/simulator/run")
    @app.post("/api/simulator/generate")
    def run():
        if request.headers.get("Sec-Fetch-Site") == "cross-site":
            return jsonify(error="Requête intersite refusée."), 403
        try:
            generation = request.path.endswith('/generate')
            payload = (validate_generation if generation else validate)(request.get_json())
        except (InvalidConfiguration, BadRequest, UnsupportedMediaType) as exc:
            message = str(exc) if isinstance(exc, InvalidConfiguration) else "Un corps JSON valide est requis."
            return jsonify(error=message), 400
        if not slot.acquire(blocking=False):
            return jsonify(error="Une simulation est en cours. Réessayez dans quelques secondes."), 429
        try:
            return jsonify(engine.generate(payload) if generation else engine.run(payload))
        except InvalidConfiguration as exc:
            return jsonify(error=str(exc)), 400
        except SimulationTimeout as exc:
            return jsonify(error=str(exc)), 504
        except SimulationUnavailable:
            logging.exception("Échec du moteur isolé")
            return jsonify(error="Le moteur isolé est indisponible. Vérifiez sa préparation et les journaux du serveur."), 503
        finally:
            slot.release()

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        return jsonify(error="Configuration trop volumineuse (8 Kio maximum)."), 413

    allowed = {"index.html", "simulateur.html", "regles.html", "aide.html", "telechargement.html",
               "fiches-unites.html", "etiquettes.html", "batiments.html", "bestiaire.html",
               "carte.html", "chemins.html", "quetes.html",
               "css/style.css", "js/main.js", "js/simulateur.js"}

    @app.get("/")
    @app.get("/<path:name>")
    def page(name="index.html"):
        if name not in allowed:
            return "Page introuvable", 404
        return send_from_directory(ROOT, name)

    return app


if __name__ == "__main__":
    from waitress import serve
    print("Simulateur : http://127.0.0.1:8080/simulateur.html", flush=True)
    serve(create_app(), host="127.0.0.1", port=8080, threads=4, max_request_body_size=8192)
