"""Attente jusqu'à une échéance ; aucune dépendance au moteur du jeu."""
import math
import time


def valider_duree(duree):
    if not math.isfinite(duree) or duree < 0:
        raise ValueError("La durée doit être finie et positive ou nulle.")
    return duree


def attendre_jusqua(echeance, horloge=None, dormir=None, observer=None):
    """Horloge et attente injectables pour ne jamais attendre dans les tests."""
    if not math.isfinite(echeance):
        raise ValueError("Échéance invalide.")
    horloge = time.time if horloge is None else horloge
    dormir = time.sleep if dormir is None else dormir
    while True:
        restant = echeance - horloge()
        if observer is not None:
            observer(max(0, restant))
        if restant <= 0:
            return
        dormir(min(restant, 1.0))
