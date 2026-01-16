# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-16

### Added
- Initial public release
- Generic entity tracking with JSON Hybrid storage (SQLite + JSON columns)
- MCP server implementation with Tools, Resources, and Prompts
- Auto-discovery and auto-registration of entity types
- Self-documenting schema examples via MCP Resources
- CRUD operations via MCP Tools:
  - `track_event`: Insert or update tracking event
  - `query_events`: Query events with filters (entity_type, date range, entity_id)
  - `delete_event`: Delete event by ID
  - `list_entity_types`: List all registered entity types with schema examples
- Pre-seeded entity types: weight, scorecard, fitness, book
- Database schema with automatic timestamps (created_at, updated_at)
- Python >= 3.10 support
- Comprehensive README with SQL query examples
- MIT License

### Technical Stack
- Python 3.10+
- SQLite (JSON Hybrid approach)
- MCP SDK (mcp >= 1.7.1)
- aiosqlite for async database operations
- pytest for testing

### Architecture
- Schema-less design: track any entity type without ALTER TABLE
- JSON columns for flexible data structures
- Auto-registration: new entity types registered on first use
- Local-first: privacy-friendly, no external dependencies
- SQL-queryable: use json_extract() for advanced analytics

[1.0.0]: https://github.com/mariomosca/tracking-mcp/releases/tag/v1.0.0
