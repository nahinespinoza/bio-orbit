-- Base de conocimiento del agente. Se regenera completa con: uv run python -m ingestion.build_db
-- Los datos de origen (knowledge/structured/*.json) tienen claves en español; aquí se guardan en inglés.

CREATE TABLE sources (
    source_id     INTEGER PRIMARY KEY,
    title         TEXT NOT NULL,
    reliability   TEXT,              -- texto de la ficha (p. ej. "alta", "baja: NO es evidencia")
    reliability_level TEXT NOT NULL, -- high | medium | low (normalizado)
    region        TEXT,
    url           TEXT,
    accessed_on   TEXT
);

CREATE TABLE crops (
    crop_id              TEXT PRIMARY KEY,   -- identificador de datos (papa, haba, ...): se mantiene en español
    name                 TEXT NOT NULL,
    family               TEXT,
    crop_type            TEXT NOT NULL,      -- commercial | non_commercial
    tags_json            TEXT NOT NULL,      -- ["starter","follower","ender"]
    source5_only         INTEGER NOT NULL DEFAULT 0,
    -- suelo
    soil_texture_text    TEXT,
    soil_ph_min          REAL,
    soil_ph_max          REAL,
    soil_drainage_text   TEXT,
    soil_drainage_required TEXT,             -- good | NULL
    soil_min_depth_cm    REAL,
    soil_fertility_demand TEXT,              -- high | medium | low | NULL
    -- clima
    altitude_min_masl    REAL,
    altitude_max_masl    REAL,
    requires_irrigation  INTEGER,            -- 1 | 0 | NULL
    temperature_text     TEXT,
    rainfall_text        TEXT,
    -- ciclo
    cycle_months_min     REAL,
    cycle_months_max     REAL,
    -- sanidad y rotación
    pests_json           TEXT NOT NULL DEFAULT '[]',
    diseases_json        TEXT NOT NULL DEFAULT '[]',
    fixes_nitrogen       INTEGER NOT NULL DEFAULT 0,
    depletes_soil        TEXT,               -- high | medium | low | NULL
    host_of_json         TEXT NOT NULL DEFAULT '[]',
    breaks_cycles_of_json TEXT NOT NULL DEFAULT '[]',
    improves_structure   INTEGER,
    -- mano de obra y facilidad
    labor_level          INTEGER,            -- 1 (muy poca) .. 5 (muchísima)
    labor_days_per_ha    REAL,
    labor_mechanizable   TEXT,               -- yes | partial | no | NULL
    labor_data_type      TEXT,               -- source | inference
    ease_level           INTEGER,            -- 1 (muy difícil) .. 5 (muy fácil)
    -- mercado
    market_level         INTEGER,            -- 1..5 (inferencia; ver market_json)
    market_price         REAL,
    market_unit          TEXT,
    market_date          TEXT,
    market_volatility    TEXT,               -- high | medium | low | NULL
    market_confidence    TEXT,
    market_source_ids_json TEXT NOT NULL DEFAULT '[]',
    -- metadatos
    geographic_scope     TEXT,
    confidence           TEXT NOT NULL,      -- high | medium | low
    gaps_json            TEXT NOT NULL DEFAULT '[]',
    sources_json         TEXT NOT NULL DEFAULT '[]', -- [{source_id, location, detail}]
    profile_json         TEXT NOT NULL       -- ficha original completa (español), para mostrar
);

CREATE TABLE transitions (
    from_crop   TEXT NOT NULL REFERENCES crops(crop_id),
    to_crop     TEXT NOT NULL REFERENCES crops(crop_id),
    kind        TEXT NOT NULL,               -- source | general | inferred | source5
    source_note TEXT NOT NULL,
    PRIMARY KEY (from_crop, to_crop)
);

-- Fragmentos para RAG (fuente del BM25Retriever, que se arma en memoria al iniciar la API).
-- Los vectores los guarda SQLiteVec de langchain-community en sus propias tablas
-- (chunk_vectors y chunk_vectors_vec), solo si la ingesta corrió con embeddings.
CREATE TABLE chunks (
    chunk_id      INTEGER PRIMARY KEY,
    text          TEXT NOT NULL,
    metadata_json TEXT NOT NULL  -- source_id, title, doc_kind, reliability_level, page, page_label, section, crops
);

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
