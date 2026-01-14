-- Tracking MCP: JSON Hybrid Database Schema
-- Schema-less storage for dynamic entity tracking

-- Main tracking events table (JSON Hybrid approach)
CREATE TABLE IF NOT EXISTS tracking_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,       -- 'weight', 'scorecard', 'fitness', 'book', etc.
    entity_id TEXT,                  -- Optional: unique ID per entity (e.g., 'book_open')
    date DATE NOT NULL,              -- Event date
    data JSON NOT NULL,              -- Schema-free JSON data for entity_type

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint: one event per entity_type + entity_id + date
    UNIQUE(entity_type, entity_id, date)
        ON CONFLICT REPLACE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_entity_type ON tracking_events(entity_type);
CREATE INDEX IF NOT EXISTS idx_date ON tracking_events(date DESC);
CREATE INDEX IF NOT EXISTS idx_entity_date ON tracking_events(entity_type, date);

-- Entity types registry (metadata table)
CREATE TABLE IF NOT EXISTS entity_types (
    entity_type TEXT PRIMARY KEY,
    description TEXT,
    schema_example JSON,           -- JSON schema template
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger: auto-update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_tracking_events_timestamp
AFTER UPDATE ON tracking_events
BEGIN
    UPDATE tracking_events
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_entity_types_timestamp
AFTER UPDATE ON entity_types
BEGIN
    UPDATE entity_types
    SET updated_at = CURRENT_TIMESTAMP
    WHERE entity_type = NEW.entity_type;
END;

-- Seed entity types (common use cases)
INSERT OR IGNORE INTO entity_types (entity_type, description, schema_example) VALUES
('weight', 'Body weight tracking', '{"weight_kg": "float", "day_type": "string", "source": "string", "delta_kg": "float"}'),
('scorecard', 'Daily +1% scorecard', '{"total_score": "int", "streak_day": "int", "foundation": "object", "whoop": "object"}'),
('fitness', 'Workout sessions', '{"workout_type": "string", "duration_min": "int", "strain": "float", "avg_hr": "int", "max_hr": "int"}'),
('book', 'Reading progress', '{"title": "string", "author": "string", "current_page": "int", "total_pages": "int", "session_duration_min": "int"}');

-- Example queries (commented for reference)
--
-- 1. Get weight last 30 days:
-- SELECT
--     date,
--     json_extract(data, '$.weight_kg') as peso,
--     json_extract(data, '$.delta_kg') as delta
-- FROM tracking_events
-- WHERE entity_type = 'weight'
-- AND date >= date('now', '-30 days')
-- ORDER BY date DESC;
--
-- 2. Get scorecard current week average:
-- SELECT
--     strftime('%Y-W%W', date) as week,
--     AVG(CAST(json_extract(data, '$.total_score') AS INTEGER)) as avg_score,
--     COUNT(*) as days
-- FROM tracking_events
-- WHERE entity_type = 'scorecard'
-- AND date >= date('now', 'weekday 0', '-7 days')
-- GROUP BY week;
--
-- 3. Get fitness volume by workout type this month:
-- SELECT
--     json_extract(data, '$.workout_type') as tipo,
--     COUNT(*) as sessioni,
--     SUM(CAST(json_extract(data, '$.duration_min') AS INTEGER)) as tot_min
-- FROM tracking_events
-- WHERE entity_type = 'fitness'
-- AND date >= date('now', 'start of month')
-- GROUP BY tipo;
--
-- 4. Get books reading progress:
-- SELECT
--     entity_id,
--     json_extract(data, '$.title') as titolo,
--     json_extract(data, '$.current_page') as pag_corrente,
--     json_extract(data, '$.total_pages') as pag_totali,
--     ROUND(
--         CAST(json_extract(data, '$.current_page') AS REAL) /
--         CAST(json_extract(data, '$.total_pages') AS REAL) * 100, 1
--     ) as progress_pct
-- FROM tracking_events
-- WHERE entity_type = 'book'
-- AND date = (
--     SELECT MAX(date) FROM tracking_events t2
--     WHERE t2.entity_type = 'book' AND t2.entity_id = tracking_events.entity_id
-- )
-- ORDER BY progress_pct DESC;
