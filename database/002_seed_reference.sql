-- Mythodea reference data v0.1
-- Values below come from the current V2.0 engine configuration.
BEGIN;

SET search_path TO mythodea, public;

INSERT INTO unit_types (code, display_name, category, trainable, description)
VALUES
    ('archer', 'Archer', 'infanterie', TRUE, 'Unité à arc.'),
    ('piquier', 'Piquier', 'infanterie', TRUE, 'Unité à pique.'),
    ('cavalier', 'Cavalier', 'cavalerie', TRUE, 'Unité à cheval.'),
    ('cavalerie_lourde', 'Cavalier lourd', 'cavalerie', FALSE, 'Unité spéciale actuellement réservée aux récompenses.')
ON CONFLICT (code) DO NOTHING;

INSERT INTO order_types
    (code, type_number, order_number, name, category, operational, description)
VALUES
    ('1-1', 1, 1, 'retraite_apres_premiere_manche', 'armee', FALSE, NULL),
    ('1-2', 1, 2, 'attaque_frontale', 'armee', TRUE, 'Ordre actuellement utilisé par le moteur.'),
    ('2-1', 2, 1, 'attaque_chirurgicale', 'formation', FALSE, NULL),
    ('2-2', 2, 2, 'pluie_de_fleches', 'formation', FALSE, NULL),
    ('3-1', 3, 1, 'fuir_avant_la_mort', 'intrinseque', FALSE, NULL)
ON CONFLICT (code) DO NOTHING;

INSERT INTO weather_types (code, display_name)
VALUES
    ('clair', 'Clair'),
    ('pluie', 'Pluie'),
    ('brouillard', 'Brouillard'),
    ('vent', 'Vent'),
    ('orage', 'Orage'),
    ('neige', 'Neige')
ON CONFLICT (code) DO NOTHING;

COMMIT;
