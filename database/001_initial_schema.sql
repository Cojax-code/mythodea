-- Mythodea database foundation v0.1
-- PostgreSQL
--
-- Important: this schema does NOT replace the current Linux filesystem state.
-- /game and the engine files remain authoritative for the playable V2.0.
-- The database is introduced first for the web simulator, structured history,
-- statistics, and a future progressive migration.

BEGIN;

CREATE SCHEMA IF NOT EXISTS mythodea;
SET search_path TO mythodea, public;

CREATE TABLE unit_types (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    display_name    TEXT NOT NULL,
    category        TEXT NOT NULL,
    trainable       BOOLEAN NOT NULL DEFAULT TRUE,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_types (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    type_number     INTEGER NOT NULL,
    order_number    INTEGER NOT NULL,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,
    operational     BOOLEAN NOT NULL DEFAULT FALSE,
    description     TEXT,
    UNIQUE (type_number, order_number)
);

CREATE TABLE weather_types (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    display_name    TEXT NOT NULL,
    description     TEXT
);

CREATE TABLE terrain_types (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    display_name    TEXT NOT NULL,
    description     TEXT
);

CREATE TABLE games (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mode            TEXT NOT NULL CHECK (mode IN ('classique', 'survie', 'simulateur')),
    status          TEXT NOT NULL DEFAULT 'created'
                    CHECK (status IN ('created', 'active', 'finished', 'archived')),
    engine_version  TEXT,
    engine_commit   TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE actors (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    game_id         BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    code            TEXT NOT NULL,
    actor_type      TEXT NOT NULL CHECK (actor_type IN ('player', 'bot')),
    camp_code       TEXT NOT NULL,
    linux_owner     TEXT,
    linux_group     TEXT,
    display_name    TEXT,
    UNIQUE (game_id, code)
);

CREATE TABLE territories (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    game_id         BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    code            TEXT NOT NULL,
    display_name    TEXT,
    terrain_type_id BIGINT REFERENCES terrain_types(id),
    control_camp    TEXT,
    is_special_zone BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (game_id, code)
);

CREATE TABLE territory_connections (
    game_id         BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    territory_a_id  BIGINT NOT NULL REFERENCES territories(id) ON DELETE CASCADE,
    territory_b_id  BIGINT NOT NULL REFERENCES territories(id) ON DELETE CASCADE,
    PRIMARY KEY (game_id, territory_a_id, territory_b_id),
    CHECK (territory_a_id <> territory_b_id)
);

CREATE TABLE generals (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    game_id             BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    owner_actor_id      BIGINT NOT NULL REFERENCES actors(id) ON DELETE CASCADE,
    canonical_name      TEXT NOT NULL,
    display_name        TEXT,
    orientation         TEXT CHECK (orientation IN ('stratege', 'combattant', 'hybride')),
    strategy            INTEGER NOT NULL DEFAULT 0,
    force               INTEGER NOT NULL DEFAULT 0,
    experience          INTEGER NOT NULL DEFAULT 0,
    faction             TEXT,
    wave_number         INTEGER,
    source              TEXT NOT NULL DEFAULT 'normal',
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'reserve', 'reward', 'repli', 'destroyed')),
    territory_id        BIGINT REFERENCES territories(id),
    logical_position    INTEGER CHECK (logical_position BETWEEN 1 AND 20),
    fatigue             BOOLEAN NOT NULL DEFAULT FALSE,
    created_turn        INTEGER,
    destroyed_turn      INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (game_id, owner_actor_id, canonical_name)
);

CREATE TABLE general_blocks (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    general_id      BIGINT NOT NULL REFERENCES generals(id) ON DELETE CASCADE,
    position        TEXT NOT NULL CHECK (position IN ('avant', 'droite', 'gauche', 'arriere')),
    UNIQUE (general_id, position)
);

CREATE TABLE block_units (
    block_id        BIGINT NOT NULL REFERENCES general_blocks(id) ON DELETE CASCADE,
    unit_type_id    BIGINT NOT NULL REFERENCES unit_types(id),
    quantity        INTEGER NOT NULL CHECK (quantity >= 0),
    PRIMARY KEY (block_id, unit_type_id)
);

CREATE TABLE general_orders (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    general_id          BIGINT NOT NULL REFERENCES generals(id) ON DELETE CASCADE,
    order_type_id       BIGINT NOT NULL REFERENCES order_types(id),
    specification       INTEGER,
    raw_text            TEXT,
    sequence_number     INTEGER NOT NULL DEFAULT 1 CHECK (sequence_number > 0),
    UNIQUE (general_id, sequence_number)
);

CREATE TABLE turns (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    game_id         BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    turn_number     INTEGER NOT NULL CHECK (turn_number >= 0),
    phase           TEXT,
    weather_type_id BIGINT REFERENCES weather_types(id),
    started_at      TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    state_snapshot  JSONB,
    UNIQUE (game_id, turn_number)
);

-- Simulator records are intentionally separated from live-game state.
-- A simulation can be reproduced from engine_commit + random_seed + input_snapshot.
CREATE TABLE simulations (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    game_id             BIGINT REFERENCES games(id) ON DELETE SET NULL,
    engine_version      TEXT,
    engine_commit       TEXT,
    random_seed         BIGINT,
    terrain_type_id     BIGINT REFERENCES terrain_types(id),
    weather_type_id     BIGINT REFERENCES weather_types(id),
    status              TEXT NOT NULL DEFAULT 'created'
                        CHECK (status IN ('created', 'running', 'completed', 'failed')),
    input_snapshot      JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_snapshot     JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at        TIMESTAMPTZ
);

CREATE TABLE simulation_participants (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    simulation_id   BIGINT NOT NULL REFERENCES simulations(id) ON DELETE CASCADE,
    side_number     INTEGER NOT NULL CHECK (side_number IN (1, 2)),
    slot_number     INTEGER NOT NULL DEFAULT 1 CHECK (slot_number > 0),
    general_name    TEXT NOT NULL,
    orientation     TEXT CHECK (orientation IN ('stratege', 'combattant', 'hybride')),
    order_code      TEXT,
    order_specification INTEGER,
    UNIQUE (simulation_id, side_number, slot_number)
);

CREATE TABLE simulation_blocks (
    participant_id  BIGINT NOT NULL REFERENCES simulation_participants(id) ON DELETE CASCADE,
    position        TEXT NOT NULL CHECK (position IN ('avant', 'droite', 'gauche', 'arriere')),
    unit_type_id    BIGINT REFERENCES unit_types(id),
    quantity        INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    PRIMARY KEY (participant_id, position)
);

CREATE TABLE combat_events (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    simulation_id   BIGINT REFERENCES simulations(id) ON DELETE CASCADE,
    game_id         BIGINT REFERENCES games(id) ON DELETE CASCADE,
    turn_id         BIGINT REFERENCES turns(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
    phase           TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    territory_code  TEXT,
    message         TEXT,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        simulation_id IS NOT NULL
        OR game_id IS NOT NULL
        OR turn_id IS NOT NULL
    )
);

CREATE INDEX idx_generals_game ON generals(game_id);
CREATE INDEX idx_generals_territory ON generals(territory_id);
CREATE INDEX idx_turns_game ON turns(game_id, turn_number);
CREATE INDEX idx_simulations_created_at ON simulations(created_at DESC);
CREATE INDEX idx_combat_events_simulation ON combat_events(simulation_id, sequence_number);
CREATE INDEX idx_combat_events_turn ON combat_events(turn_id, sequence_number);

COMMIT;
