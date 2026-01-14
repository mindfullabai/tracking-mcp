# Tracking MCP

Generic MCP server for tracking any entity type with schema-less JSON Hybrid storage.

## Overview

Tracking MCP è un server MCP (Model Context Protocol) che permette di tracciare **qualsiasi tipo di entità** senza dover definire uno schema rigido. Utilizza SQLite con JSON columns per massima flessibilità.

### Features

- **Schema-less**: Traccia peso, scorecard, fitness, libri o qualsiasi entità futura senza ALTER TABLE
- **Auto-discovery**: Entity types registrati automaticamente al primo insert
- **Self-documenting**: Resources MCP espongono schema examples e usage guide
- **Query SQL**: Usa json_extract() per analisi avanzate
- **Local-first**: Privacy-friendly, zero external dependencies

### Stack

- **Database**: SQLite con JSON columns (JSON Hybrid approach)
- **MCP Server**: Python con official MCP SDK
- **Tools**: CRUD operations (track_event, query_events, delete_event, list_entity_types)

## Project Structure

```
tracking-mcp/
├── data/
│   ├── tracking.db         # SQLite database
│   └── schema.sql          # Database schema
├── mcp_server/
│   ├── tracking_server.py  # MCP server implementation
│   └── __init__.py
├── tests/
│   └── test_server.py
├── pyproject.toml
└── README.md
```

## Installation

### 1. Setup Virtual Environment

```bash
cd tracking-mcp
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -e .
```

### 3. Initialize Database (if not already done)

```bash
cd data
sqlite3 tracking.db < schema.sql
```

## Database Schema

### Main Tables

**tracking_events** - Generic event storage:
- `id`: Auto-increment primary key
- `entity_type`: Entity type ('weight', 'scorecard', 'fitness', 'book', custom)
- `entity_id`: Optional unique ID for entity instances (e.g., 'book_open')
- `date`: Event date
- `data`: JSON column with schema-free data
- `created_at`, `updated_at`: Timestamps

**entity_types** - Metadata registry:
- `entity_type`: Primary key
- `description`: Human-readable description
- `schema_example`: JSON schema template
- `created_at`, `updated_at`: Timestamps

### Pre-seeded Entity Types

- **weight**: Body weight tracking
- **scorecard**: Daily +1% scorecard
- **fitness**: Workout sessions
- **book**: Reading progress

## Usage Examples

### Query Examples (SQL)

**Get weight last 30 days:**
```sql
SELECT
    date,
    json_extract(data, '$.weight_kg') as peso,
    json_extract(data, '$.delta_kg') as delta
FROM tracking_events
WHERE entity_type = 'weight'
AND date >= date('now', '-30 days')
ORDER BY date DESC;
```

**Get scorecard current week average:**
```sql
SELECT
    strftime('%Y-W%W', date) as week,
    AVG(CAST(json_extract(data, '$.total_score') AS INTEGER)) as avg_score,
    COUNT(*) as days
FROM tracking_events
WHERE entity_type = 'scorecard'
AND date >= date('now', 'weekday 0', '-7 days')
GROUP BY week;
```

**Get fitness volume by workout type this month:**
```sql
SELECT
    json_extract(data, '$.workout_type') as tipo,
    COUNT(*) as sessioni,
    SUM(CAST(json_extract(data, '$.duration_min') AS INTEGER)) as tot_min
FROM tracking_events
WHERE entity_type = 'fitness'
AND date >= date('now', 'start of month')
GROUP BY tipo;
```

### MCP Server Usage (coming in Phase 2)

Once the MCP server is implemented, you'll be able to use it from Claude Code:

```python
# Track event
await tracking_mcp.track_event(
    entity_type="weight",
    date="2026-01-14",
    data={"weight_kg": 72.8, "day_type": "MAR", "source": "manual"}
)

# Query events
result = await tracking_mcp.query_events(
    entity_type="weight",
    start_date="2025-12-15",
    end_date="2026-01-14"
)

# List entity types
entity_types = await tracking_mcp.list_entity_types()
```

## Development Status

**Phase 1: Project Setup + Schema** ✅ COMPLETED
- [x] Directory structure
- [x] Schema SQL
- [x] Database initialization
- [x] pyproject.toml
- [x] README.md

**Phase 2: Custom MCP Server** 🚧 TODO
- [ ] MCP server base (Tools CRUD)
- [ ] Resources (docs, schema registry)
- [ ] Prompts (track templates)
- [ ] MCP config + test

**Phase 3: work-hub Integration** 🚧 TODO
- [ ] Sync script .md → tracking-mcp DB
- [ ] MCP config in work-hub
- [ ] Test query/insert workflows
- [ ] Export CSV/JSON utilities

## Architecture Decisions

### JSON Hybrid vs EAV
- ✅ JSON Hybrid: Flessibilità + performance + query SQL standard
- ❌ EAV: Troppi JOIN, performance issues per analytics

### Custom MCP vs Official SQLite MCP
- ✅ Custom: Auto-discovery, self-documenting, dynamic schema
- ❌ Official: Richiede schema rigido, no auto-registration

### SQLite vs PostgreSQL
- ✅ SQLite: Setup zero, file-based, sufficiente personal use
- ❌ PostgreSQL: Overhead inutile per single-user tracking

## License

MIT

## Related Projects

- **viz-mcp**: Auto-visualization MCP server (companion project)
- **work-hub**: Personal productivity system that uses tracking-mcp
