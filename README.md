# Tracking MCP

![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Version](https://img.shields.io/badge/version-1.0.0-orange.svg)

**Generic MCP server for tracking any entity type with schema-less JSON Hybrid storage.**

Track body weight, daily scorecards, fitness sessions, books, or any custom entity without defining rigid schemas. Auto-discovery, self-documenting, and SQL-queryable.

## Features

- **Schema-less Design**: Track any entity type (weight, scorecard, fitness, books, custom) without ALTER TABLE
- **Auto-Discovery**: Entity types automatically registered on first use
- **Self-Documenting**: MCP Resources expose schema examples and usage guides
- **SQL-Queryable**: Use `json_extract()` for advanced analytics
- **Local-First**: Privacy-friendly, zero external dependencies
- **Hybrid Storage**: SQLite with JSON columns for flexibility + performance
- **CRUD Operations**: Insert, update, query, delete via MCP Tools
- **Built-in Prompts**: Pre-configured templates for common tracking scenarios

## Installation

### From PyPI (when published)

```bash
pip install tracking-mcp
```

### From Source

```bash
git clone https://github.com/mariomosca/tracking-mcp.git
cd tracking-mcp
pip install -e .
```

### Initialize Database

```bash
# Database will be auto-created in data/tracking.db
# Or manually initialize:
cd data
sqlite3 tracking.db < schema.sql
```

## Quick Start

### Claude Desktop Configuration

Add to your Claude Desktop MCP settings (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "tracking": {
      "command": "tracking-mcp",
      "env": {
        "DB_PATH": "/path/to/your/data/tracking.db"
      }
    }
  }
}
```

### Basic Usage

From Claude Desktop, you can now:

```
Track my weight: 72.5kg today
```

```
Show me my weight trend for the last 30 days
```

```
Log workout: HYROX for 45 minutes today
```

## MCP Server Specification

### Tools (4)

#### 1. `track_event`
Insert or update tracking event for any entity type.

**Parameters**:
- `entity_type` (string, required): Entity type (e.g., 'weight', 'scorecard', 'fitness', 'book', or custom)
- `date` (string, required): Event date in YYYY-MM-DD format
- `data` (object, required): Entity-specific data (schema-free JSON)
- `entity_id` (string, optional): Unique ID for entity instance (e.g., 'book_atomic_habits')

**Example**:
```python
track_event(
    entity_type="weight",
    date="2026-01-14",
    data={"weight_kg": 72.8, "day_type": "MAR", "source": "manual"}
)
```

#### 2. `query_events`
Query tracking events with filters.

**Parameters**:
- `entity_type` (string, optional): Filter by entity type
- `entity_id` (string, optional): Filter by entity ID
- `start_date` (string, optional): Start date (inclusive)
- `end_date` (string, optional): End date (inclusive)
- `limit` (integer, optional): Maximum results (default: 100)

**Example**:
```python
query_events(
    entity_type="weight",
    start_date="2025-12-15",
    end_date="2026-01-14",
    limit=30
)
```

#### 3. `delete_event`
Delete tracking event by ID.

**Parameters**:
- `event_id` (integer, required): Event ID to delete

#### 4. `list_entity_types`
Get all registered entity types with schema examples.

**Returns**: JSON array of entity types with descriptions and schema examples.

### Resources (3)

#### 1. `tracking://schema/entity_types`
List of all registered entity types with schema examples (JSON).

#### 2. `tracking://docs/usage`
Usage guide for tracking new entity types dynamically (Markdown).

#### 3. `tracking://stats/summary`
Current statistics: total events, entity types, date range, events by type (JSON).

### Prompts (3)

#### 1. `track-weight`
Template for tracking body weight.

**Arguments**: `weight_kg`, `date`

#### 2. `track-workout`
Template for logging workout session.

**Arguments**: `workout_type`, `duration_min`, `date`

#### 3. `query-trend`
Get trend data for entity type over date range.

**Arguments**: `entity_type`, `days` (default: 30)

## Database Schema

### `tracking_events` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `entity_type` | TEXT | Entity type ('weight', 'scorecard', etc.) |
| `entity_id` | TEXT | Optional unique ID for entity instances |
| `date` | DATE | Event date (YYYY-MM-DD) |
| `data` | JSON | Schema-free JSON data |
| `created_at` | TIMESTAMP | Auto-generated creation timestamp |
| `updated_at` | TIMESTAMP | Auto-updated modification timestamp |

**Indexes**: `entity_type`, `date`, `entity_id`

### `entity_types` Table

| Column | Type | Description |
|--------|------|-------------|
| `entity_type` | TEXT PRIMARY KEY | Entity type name |
| `description` | TEXT | Human-readable description |
| `schema_example` | JSON | Example JSON schema |
| `created_at` | TIMESTAMP | Registration timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

**Pre-seeded entity types**: `weight`, `scorecard`, `fitness`, `book`

## Advanced Usage Examples

### Track Custom Entity Type

```python
# Sleep quality tracking (auto-registered)
track_event(
    entity_type="sleep_quality",
    date="2026-01-14",
    data={
        "hours": 7.5,
        "quality_score": 8,
        "dreams": True,
        "interruptions": 2,
        "notes": "Felt refreshed"
    }
)
```

### Track Entity with Unique ID

```python
# Reading progress for specific book
track_event(
    entity_type="book",
    entity_id="book_atomic_habits",
    date="2026-01-14",
    data={
        "title": "Atomic Habits",
        "author": "James Clear",
        "current_page": 150,
        "total_pages": 320,
        "rating": 5
    }
)
```

### Query with Filters

```python
# Get all weight entries for January 2026
query_events(
    entity_type="weight",
    start_date="2026-01-01",
    end_date="2026-01-31"
)

# Get all entries for specific book
query_events(
    entity_type="book",
    entity_id="book_atomic_habits"
)
```

### Update Existing Event

To update an event, call `track_event()` with the same `entity_type` + `date` (+ `entity_id` if used). The tool will automatically UPDATE instead of INSERT.

## SQL Analytics

Since data is stored in SQLite with JSON columns, you can run advanced analytics:

### Weight Trend (Last 30 Days)

```sql
SELECT
    date,
    json_extract(data, '$.weight_kg') as weight,
    json_extract(data, '$.delta_kg') as delta
FROM tracking_events
WHERE entity_type = 'weight'
AND date >= date('now', '-30 days')
ORDER BY date DESC;
```

### Scorecard Weekly Average

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

### Fitness Volume by Workout Type (This Month)

```sql
SELECT
    json_extract(data, '$.workout_type') as type,
    COUNT(*) as sessions,
    SUM(CAST(json_extract(data, '$.duration_min') AS INTEGER)) as total_minutes,
    AVG(CAST(json_extract(data, '$.duration_min') AS INTEGER)) as avg_minutes
FROM tracking_events
WHERE entity_type = 'fitness'
AND date >= date('now', 'start of month')
GROUP BY type;
```

## Project Structure

```
tracking-mcp/
├── data/
│   ├── tracking.db         # SQLite database
│   └── schema.sql          # Database schema
├── tracking_mcp/
│   ├── tracking_server.py  # MCP server implementation
│   └── __init__.py
├── tests/
│   └── test_server.py
├── pyproject.toml
├── LICENSE
├── CHANGELOG.md
└── README.md
```

## Architecture Decisions

### Why JSON Hybrid (SQLite + JSON)?
- ✅ **Flexibility**: Add new entity types without schema migrations
- ✅ **Performance**: SQLite indexes + `json_extract()` for fast queries
- ✅ **SQL-queryable**: Standard SQL for analytics
- ❌ **EAV alternative**: Too many JOINs, poor performance for analytics

### Why Custom MCP vs Official SQLite MCP?
- ✅ **Auto-discovery**: New entity types registered automatically
- ✅ **Self-documenting**: Resources expose schemas and usage
- ✅ **Dynamic**: No rigid schema required
- ❌ **Official SQLite MCP**: Requires predefined schema

### Why SQLite vs PostgreSQL?
- ✅ **Zero setup**: File-based, no server required
- ✅ **Local-first**: Privacy-friendly for personal tracking
- ✅ **Sufficient**: Perfect for single-user personal use
- ❌ **PostgreSQL**: Unnecessary overhead for personal tracking

## Development

### Run Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black mcp_server/

# Lint
ruff check mcp_server/
```

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

## Version History

See [CHANGELOG.md](CHANGELOG.md) for version history.

**Current version**: 1.0.0 (Initial public release)

## Related Projects

- **[viz-mcp](https://github.com/mariomosca/viz-mcp)**: Companion MCP server for auto-generating data visualizations from tracking data
- **work-hub**: Personal productivity system using tracking-mcp for daily scorecard and habit tracking

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

**Mario Mosca** - [GitHub](https://github.com/mariomosca)

## Contributing

Contributions welcome! Please open an issue or pull request.

## Support

For issues, questions, or feature requests, please open an issue on GitHub:
https://github.com/mariomosca/tracking-mcp/issues
