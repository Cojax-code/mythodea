"""Contrôleur de gel injecté ; aucune permission ou attente Linux prétendue réelle."""
class GelSimule:
    def __init__(self):
        self.gele = False
        self.evenements = []

    def preparer(self):
        pass

    def annoncer(self, message):
        self.evenements.append(('annonce', message))

    def geler(self):
        self.gele = True
        self.evenements.append(('gel', None))

    def verifier_gel(self):
        assert self.gele

    def degeler(self):
        self.gele = False
        self.evenements.append(('degel', None))
