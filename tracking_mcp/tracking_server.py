#!/usr/bin/env python3
"""
Tracking MCP Server

Generic MCP server for tracking any entity type with JSON Hybrid storage.
Uses SQLite with JSON columns for maximum flexibility.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Optional

from mcp.server import Server
from mcp.types import Resource, Tool, TextContent, Prompt, GetPromptResult, PromptMessage
import mcp.server.stdio


# Database path from environment or default
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "../data/tracking.db"))

# Initialize MCP server
app = Server("tracking-mcp")


def get_db_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def auto_register_entity_type(entity_type: str, data: dict):
    """Auto-register new entity type if not exists."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO entity_types (entity_type, description, schema_example)
        VALUES (?, ?, ?)
        """,
        (
            entity_type,
            f"Auto-registered: {entity_type}",
            json.dumps(data)
        )
    )

    conn.commit()
    conn.close()


# ============================================================================
# TOOLS
# ============================================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="track_event",
            description="Insert or update tracking event for any entity type",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Entity type (e.g., 'weight', 'scorecard', 'fitness', 'book', or custom)"
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "Event date in YYYY-MM-DD format"
                    },
                    "data": {
                        "type": "object",
                        "description": "Entity-specific data (schema-free JSON)"
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Optional: unique ID for entity instance (e.g., 'book_atomic_habits')"
                    }
                },
                "required": ["entity_type", "date", "data"]
            }
        ),
        Tool(
            name="query_events",
            description="Query tracking events with filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Filter by entity type (optional)"
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Filter by entity ID (optional)"
                    },
                    "start_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Start date (inclusive, optional)"
                    },
                    "end_date": {
                        "type": "string",
                        "format": "date",
                        "description": "End date (inclusive, optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 100,
                        "description": "Maximum number of results (default: 100)"
                    }
                }
            }
        ),
        Tool(
            name="delete_event",
            description="Delete tracking event by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "Event ID to delete"
                    }
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="list_entity_types",
            description="Get all registered entity types with schema examples",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""

    if name == "track_event":
        return await track_event(
            entity_type=arguments["entity_type"],
            date=arguments["date"],
            data=arguments["data"],
            entity_id=arguments.get("entity_id")
        )

    elif name == "query_events":
        return await query_events(
            entity_type=arguments.get("entity_type"),
            entity_id=arguments.get("entity_id"),
            start_date=arguments.get("start_date"),
            end_date=arguments.get("end_date"),
            limit=arguments.get("limit", 100)
        )

    elif name == "delete_event":
        return await delete_event(event_id=arguments["event_id"])

    elif name == "list_entity_types":
        return await list_entity_types_impl()

    else:
        raise ValueError(f"Unknown tool: {name}")


async def track_event(
    entity_type: str,
    date: str,
    data: dict,
    entity_id: Optional[str] = None
) -> list[TextContent]:
    """Track event (insert or update)."""

    # Auto-register entity type
    auto_register_entity_type(entity_type, data)

    conn = get_db_connection()
    cursor = conn.cursor()

    # UPSERT logic: Handle duplicates for entity_id = NULL case
    # First, try to find existing event
    if entity_id is None:
        cursor.execute(
            """
            SELECT id FROM tracking_events
            WHERE entity_type = ? AND date = ? AND entity_id IS NULL
            """,
            (entity_type, date)
        )
    else:
        cursor.execute(
            """
            SELECT id FROM tracking_events
            WHERE entity_type = ? AND entity_id = ? AND date = ?
            """,
            (entity_type, entity_id, date)
        )

    existing = cursor.fetchone()

    if existing:
        # Update existing event
        cursor.execute(
            """
            UPDATE tracking_events
            SET data = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (json.dumps(data), existing["id"])
        )
        event_id = existing["id"]
        action = "updated"
    else:
        # Insert new event
        cursor.execute(
            """
            INSERT INTO tracking_events (entity_type, entity_id, date, data)
            VALUES (?, ?, ?, ?)
            """,
            (entity_type, entity_id, date, json.dumps(data))
        )
        event_id = cursor.lastrowid
        action = "created"

    conn.commit()
    conn.close()

    return [
        TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "action": action,
                "event_id": event_id,
                "message": f"Event {action}: {entity_type} on {date}",
                "entity_type": entity_type,
                "date": date
            }, indent=2)
        )
    ]


async def query_events(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
) -> list[TextContent]:
    """Query events with filters."""

    conn = get_db_connection()
    cursor = conn.cursor()

    # Build query dynamically
    query = "SELECT id, entity_type, entity_id, date, data, created_at, updated_at FROM tracking_events WHERE 1=1"
    params = []

    if entity_type:
        query += " AND entity_type = ?"
        params.append(entity_type)

    if entity_id:
        query += " AND entity_id = ?"
        params.append(entity_id)

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Convert to list of dicts
    events = []
    for row in rows:
        events.append({
            "id": row["id"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "date": row["date"],
            "data": json.loads(row["data"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        })

    conn.close()

    return [
        TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "count": len(events),
                "events": events,
                "filters": {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit
                }
            }, indent=2)
        )
    ]


async def delete_event(event_id: int) -> list[TextContent]:
    """Delete event by ID."""

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if event exists
    cursor.execute("SELECT entity_type, date FROM tracking_events WHERE id = ?", (event_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "message": f"Event {event_id} not found"
                }, indent=2)
            )
        ]

    # Delete event
    cursor.execute("DELETE FROM tracking_events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

    return [
        TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "message": f"Event {event_id} deleted ({row['entity_type']} on {row['date']})"
            }, indent=2)
        )
    ]


async def list_entity_types_impl() -> list[TextContent]:
    """List all registered entity types."""

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT entity_type, description, schema_example, created_at
        FROM entity_types
        ORDER BY entity_type
        """
    )
    rows = cursor.fetchall()

    entity_types = []
    for row in rows:
        entity_types.append({
            "entity_type": row["entity_type"],
            "description": row["description"],
            "schema_example": json.loads(row["schema_example"]),
            "created_at": row["created_at"]
        })

    conn.close()

    return [
        TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "count": len(entity_types),
                "entity_types": entity_types
            }, indent=2)
        )
    ]


# ============================================================================
# RESOURCES
# ============================================================================

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="tracking://schema/entity_types",
            name="Entity Types Registry",
            description="List of all registered entity types with schema examples",
            mimeType="application/json"
        ),
        Resource(
            uri="tracking://docs/usage",
            name="Usage Guide",
            description="How to track new entity types dynamically",
            mimeType="text/markdown"
        ),
        Resource(
            uri="tracking://stats/summary",
            name="Tracking Summary",
            description="Current statistics (total events, entity types, date range)",
            mimeType="application/json"
        )
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content."""

    if uri == "tracking://schema/entity_types":
        # Return entity types registry
        result = await list_entity_types_impl()
        return result[0].text

    elif uri == "tracking://docs/usage":
        return """# Dynamic Tracking Usage

## Track New Entity Type

1. Choose entity_type name (snake_case, e.g., 'sleep_quality')
2. Define data schema (JSON, any fields)
3. Call track_event()

Example:
```python
track_event(
    entity_type="sleep_quality",
    date="2026-01-14",
    data={
        "hours": 7.5,
        "quality_score": 8,
        "dreams": True,
        "interruptions": 2
    }
)
```

Schema is auto-registered in `entity_types` table.

## Query Data

```python
query_events(
    entity_type="sleep_quality",
    start_date="2026-01-01",
    end_date="2026-01-31"
)
```

Returns JSON array with all events.

## Entity with Unique ID

For entities with multiple instances (e.g., books):

```python
track_event(
    entity_type="book",
    entity_id="book_atomic_habits",
    date="2026-01-14",
    data={
        "title": "Atomic Habits",
        "current_page": 50,
        "total_pages": 320
    }
)
```

## Update Event

To update an event, call track_event() with same entity_type + date (+ entity_id if used).
The tool will automatically UPDATE instead of INSERT.
"""

    elif uri == "tracking://stats/summary":
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total events
        cursor.execute("SELECT COUNT(*) as count FROM tracking_events")
        total_events = cursor.fetchone()["count"]

        # Entity types count
        cursor.execute("SELECT COUNT(*) as count FROM entity_types")
        total_types = cursor.fetchone()["count"]

        # Date range
        cursor.execute("SELECT MIN(date) as min_date, MAX(date) as max_date FROM tracking_events")
        date_range = cursor.fetchone()

        # Events by type
        cursor.execute("""
            SELECT entity_type, COUNT(*) as count
            FROM tracking_events
            GROUP BY entity_type
            ORDER BY count DESC
        """)
        events_by_type = [{"entity_type": row["entity_type"], "count": row["count"]} for row in cursor.fetchall()]

        conn.close()

        return json.dumps({
            "total_events": total_events,
            "total_entity_types": total_types,
            "date_range": {
                "min": date_range["min_date"],
                "max": date_range["max_date"]
            },
            "events_by_type": events_by_type
        }, indent=2)

    else:
        raise ValueError(f"Unknown resource: {uri}")


# ============================================================================
# PROMPTS
# ============================================================================

@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompts."""
    return [
        Prompt(
            name="track-weight",
            description="Template for tracking body weight",
            arguments=[
                {"name": "weight_kg", "description": "Weight in kilograms", "required": True},
                {"name": "date", "description": "Measurement date (YYYY-MM-DD)", "required": True}
            ]
        ),
        Prompt(
            name="track-workout",
            description="Template for logging workout session",
            arguments=[
                {"name": "workout_type", "description": "Workout type (e.g., HYROX, RUNNING, HIIT)", "required": True},
                {"name": "duration_min", "description": "Duration in minutes", "required": True},
                {"name": "date", "description": "Workout date (YYYY-MM-DD)", "required": True}
            ]
        ),
        Prompt(
            name="query-trend",
            description="Get trend data for entity type over date range",
            arguments=[
                {"name": "entity_type", "description": "Entity to analyze", "required": True},
                {"name": "days", "description": "Number of days back (default: 30)", "required": False}
            ]
        )
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
    """Get prompt content."""

    if name == "track-weight":
        weight_kg = arguments.get("weight_kg") if arguments else None
        date = arguments.get("date") if arguments else None

        return GetPromptResult(
            description="Track body weight",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"Track my weight: {weight_kg}kg on {date}"
                    )
                )
            ]
        )

    elif name == "track-workout":
        workout_type = arguments.get("workout_type") if arguments else None
        duration_min = arguments.get("duration_min") if arguments else None
        date = arguments.get("date") if arguments else None

        return GetPromptResult(
            description="Log workout session",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"Log workout: {workout_type} for {duration_min} minutes on {date}"
                    )
                )
            ]
        )

    elif name == "query-trend":
        entity_type = arguments.get("entity_type") if arguments else None
        days = arguments.get("days", "30") if arguments else "30"

        return GetPromptResult(
            description="Query trend data",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"Show me {entity_type} trend for the last {days} days"
                    )
                )
            ]
        )

    else:
        raise ValueError(f"Unknown prompt: {name}")


# ============================================================================
# MAIN
# ============================================================================

async def async_main():
    """Run MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


def main():
    """Entry point for the MCP server."""
    import anyio
    anyio.run(async_main)


if __name__ == "__main__":
    main()
